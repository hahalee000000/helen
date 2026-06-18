"""Semantic analyzer for the Helen language.

Walks the AST (as a Visitor[None]) performing semantic checks:
- Variable declaration and resolution
- Duplicate declaration detection
- Type compatibility (annotation mode)
- Agent parameter validation
- break/continue position checking
- const assignment protection
- LLM/async usage validation
- match/llm-if default branch completeness
- catch type validation
- import path verification
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

from helen.core.ast import (
    ASTNode,
    AccessNode,
    AgentDeclNode,
    AgentParamNode,
    AsyncCallStmtNode,
    BinaryOpNode,
    BreakStmtNode,
    CallArgNode,
    CallNode,
    CaseNode,
    CatchAllNode,
    CatchClauseNode,
    ContinueStmtNode,
    DeclarationNode,
    ExprStmtNode,
    ExpressionNode,
    FinallyBlockNode,
    FnBlockNode,
    ForStmtNode,
    FunctionDeclNode,
    GroupingNode,
    IfStmtNode,
    ImportStmtNode,
    IndexNode,
    ListLiteralNode,
    LiteralNode,
    LiteralTypeNode,
    LlmActExprNode,
    LlmBranchNode,
    LlmIfStmtNode,
    LlmStreamStmtNode,
    MainBlockNode,
    MapEntryNode,
    MapLiteralNode,
    MatchStmtNode,
    OptionalTypeNode,
    ProgramNode,
    PromptDefNode,
    ReturnStmtNode,
    StatementNode,
    TemplateRefNode,
    ThrowStmtNode,
    TryStmtNode,
    TypeNode,
    UnaryOpNode,
    UnionTypeNode,
    VarDeclNode,
    VariableNode,
    Visitor,
    WhileStmtNode,
)
from helen.core.errors import ErrorCode, ErrorReporter
from helen.semantic.symbols import Symbol, SymbolTable
from helen.semantic.types import (
    AnyType,
    LiteralType,
    NullType,
    OptionalType,
    UnionType,
    type_compatible,
    type_of_literal,
)

if TYPE_CHECKING:
    pass


# Predefined exception type names (HLD 3.6.4)
_PREDEFINED_EXCEPTIONS = frozenset({
    "AnyError",
    "LLMError",
    "TimeoutError",
    "ModelError",
    "ToolError",
    "RuntimeError",
    "AggregateError",
})


class SemanticAnalyzer(Visitor[None]):
    """AST visitor that performs semantic analysis.

    Collects errors in the provided ErrorReporter without stopping on
    the first error — the analyzer continues to find as many issues as
    possible in a single pass.
    """

    def __init__(self, errors: ErrorReporter, base_dir: str = ".") -> None:
        self.errors = errors
        self.symbols = SymbolTable()
        self.base_dir = base_dir
        self._in_loop = 0  # nesting depth of for/while loops
        self._in_function = 0  # nesting depth of fn blocks
        self._current_return_type = None  # expected return type for current function
        self._agent_names: dict[str, ASTNode] = {}  # global agent registry
        self._imported_paths: set[str] = set()  # validated import paths
        self._function_param_types: dict[str, list] = {}  # function name -> list of TypeNode
        # Register stdlib builtins in global scope (HLD M15)
        self._register_stdlib()

    def _register_stdlib(self) -> None:
        """Inject stdlib function names into the global symbol table."""
        from helen.stdlib import stdlib  # noqa: PLC0415
        from helen.semantic.symbols import Symbol  # noqa: PLC0415
        for name in stdlib.names:
            sym = Symbol(name, kind="builtin", is_const=True)
            self.symbols.define(name, sym)

    def analyze(self, program: "ProgramNode") -> None:
        """Run semantic analysis on a full program."""
        # Reset transient state for REPL safety
        self._in_loop = 0
        self._in_function = 0
        program.accept(self)

    def reset(self) -> None:
        """Reset all state for REPL :reset command."""
        self.symbols = SymbolTable()
        self._in_loop = 0
        self._in_function = 0
        self._current_return_type = None
        self._agent_names.clear()
        self._imported_paths.clear()
        self._function_param_types.clear()
        self._register_stdlib()

    def undefine(self, name: str) -> bool:
        """Remove a symbol from the global scope. Returns True if it existed."""
        removed = self.symbols.global_scope.undefine(name) is not None
        # Also remove from agent registry if it was an agent
        if name in self._agent_names:
            del self._agent_names[name]
            removed = True
        # Also remove from function param types if it was a function
        if name in self._function_param_types:
            del self._function_param_types[name]
            removed = True
        return removed

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _visit_stmts(self, stmts: list[StatementNode]) -> None:
        """Visit a list of statements."""
        for stmt in stmts:
            stmt.accept(self)

    def _check_break_continue_position(self, node: StatementNode, kind: str) -> None:
        """Report error if break/continue is used outside a loop."""
        if self._in_loop == 0:
            code = ErrorCode.BREAK_OUTSIDE_LOOP if kind == "break" else ErrorCode.CONTINUE_OUTSIDE_LOOP
            self.errors.error(code, f"{kind} can only be used inside a loop", node.span)

    def _check_const_assignment(self, name: str, span) -> None:
        """Report error if assigning to a const variable."""
        sym = self.symbols.resolve(name)
        if sym is not None and sym.is_const:
            self.errors.error(
                ErrorCode.CONST_ASSIGNMENT,
                f"cannot assign to const variable '{name}'",
                span,
            )

    def _check_llm_usage(self) -> None:
        """Validate llm statement usage (handled in specific visit methods)."""

    def _check_async_usage(self, node: AsyncCallStmtNode) -> None:
        """Validate async is only used on call statements."""
        # AsyncCallStmtNode is only created for 'async call', so this is
        # already validated by the parser. Semantic check: the callee
        # must be a valid agent or function.
        pass

    def _check_branch_completeness(self, has_default: bool, span, stmt_type: str) -> None:
        """Report error if llm-if or match has no default branch."""
        if not has_default:
            code = ErrorCode.LLM_IF_NO_DEFAULT if stmt_type == "llm_if" else ErrorCode.MATCH_NO_DEFAULT
            self.errors.error(code, f"{stmt_type} must have a default branch", span)

    def _check_match_completeness(self, node: MatchStmtNode) -> None:
        """Validate that match has a default branch."""
        self._check_branch_completeness(bool(node.default), node.span, "match")

    def _type_from_typenode(self, type_node: TypeNode | None) -> AnyType | LiteralType | UnionType | OptionalType | NullType:
        """Convert an AST TypeNode to a semantic Type."""
        if type_node is None:
            return AnyType()

        # Handle composite type nodes (OptionalTypeNode, UnionTypeNode, LiteralTypeNode)
        if isinstance(type_node, OptionalTypeNode):
            from helen.semantic.types import OptionalType
            return OptionalType(self._type_from_typenode(type_node.inner))
        if isinstance(type_node, UnionTypeNode):
            from helen.semantic.types import UnionType
            return UnionType([self._type_from_typenode(m) for m in type_node.members])
        if isinstance(type_node, LiteralTypeNode):
            from helen.semantic.types import LiteralType
            return LiteralType(type_node.values)

        name = type_node.name.lower()
        if name == "int" or name == "integer":
            from helen.semantic.types import IntType
            return IntType()
        if name == "float" or name == "double":
            from helen.semantic.types import FloatType
            return FloatType()
        if name == "str" or name == "string":
            from helen.semantic.types import StringType
            return StringType()
        if name == "bool" or name == "boolean":
            from helen.semantic.types import BoolType
            return BoolType()
        if name == "null":
            return NullType()
        if name == "any":
            return AnyType()
        if name == "list":
            from helen.semantic.types import ListType
            return ListType(AnyType())
        if name == "map":
            from helen.semantic.types import MapType
            return MapType(AnyType(), AnyType())
        # Unknown type names → AnyType (v1 lenient)
        return AnyType()

    # ------------------------------------------------------------------
    # Program & blocks
    # ------------------------------------------------------------------

    def visit_program(self, node: ProgramNode) -> None:
        for stmt in node.statements:
            stmt.accept(self)

    def visit_main_block(self, node: MainBlockNode) -> None:
        self.symbols.enter_scope("main", "block")
        try:
            self._visit_stmts(node.body)
        finally:
            self.symbols.exit_scope()

    # ------------------------------------------------------------------
    # Variable declarations & references
    # ------------------------------------------------------------------

    def visit_var_decl(self, node: VarDeclNode) -> None:
        # Evaluate initializer first
        if node.initializer is not None:
            node.initializer.accept(self)

        # Type check v1: if both annotation and initializer exist
        if node.type_annotation is not None and node.initializer is not None:
            expected = self._type_from_typenode(node.type_annotation)
            actual = self._infer_type(node.initializer)
            if not type_compatible(actual, expected):
                self.errors.error(
                    ErrorCode.SEMANTIC_TYPE_ERROR,
                    f"cannot assign {actual.name} to '{node.name}' of type {expected.name}",
                    node.span,
                )

        # Define symbol
        symbol = Symbol(
            name=node.name,
            kind="variable",
            type_node=node.type_annotation,
            is_const=not node.mutable,
        )
        existing = self.symbols.define(node.name, symbol)
        if existing is not None:
            # Allow shadowing stdlib builtins (e.g. `let len = ...` shadows `len()`)
            if existing.kind == "builtin":
                pass  # shadowing allowed
            else:
                self.errors.error(
                    ErrorCode.DUPLICATE_SYMBOL,
                    f"duplicate declaration of '{node.name}'",
                    node.span,
                )

    def visit_variable(self, node: VariableNode) -> None:
        sym = self.symbols.resolve(node.name)
        if sym is None:
            self.errors.error(
                ErrorCode.UNDECLARED_VARIABLE,
                f"undeclared variable '{node.name}'",
                node.span,
            )

    # ------------------------------------------------------------------
    # Control flow
    # ------------------------------------------------------------------

    def visit_if_stmt(self, node: IfStmtNode) -> None:
        node.condition.accept(self)
        # then branch: avoid double-scope if already a MainBlockNode
        # MainBlockNode creates its own scope in visit_main_block
        if isinstance(node.then_branch, MainBlockNode):
            node.then_branch.accept(self)
        else:
            self.symbols.enter_scope("if-then", "block")
            try:
                node.then_branch.accept(self)
            finally:
                self.symbols.exit_scope()

        if node.else_branch is not None:
            if isinstance(node.else_branch, MainBlockNode):
                node.else_branch.accept(self)
            else:
                self.symbols.enter_scope("if-else", "block")
                try:
                    node.else_branch.accept(self)
                finally:
                    self.symbols.exit_scope()

    def visit_for_stmt(self, node: ForStmtNode) -> None:
        node.iterable.accept(self)
        self._in_loop += 1
        self.symbols.enter_scope("for", "block")
        try:
            if node.iterator is not None:
                # The loop variable is declared in this scope
                sym = Symbol(name=node.iterator.name, kind="variable")
                self.symbols.define(node.iterator.name, sym)
            node.body.accept(self)
        finally:
            self.symbols.exit_scope()
            self._in_loop -= 1

    def visit_while_stmt(self, node: WhileStmtNode) -> None:
        node.condition.accept(self)
        self._in_loop += 1
        self.symbols.enter_scope("while", "block")
        try:
            node.body.accept(self)
        finally:
            self.symbols.exit_scope()
            self._in_loop -= 1

    def visit_break_stmt(self, node: BreakStmtNode) -> None:
        self._check_break_continue_position(node, "break")

    def visit_continue_stmt(self, node: ContinueStmtNode) -> None:
        self._check_break_continue_position(node, "continue")

    def visit_return_stmt(self, node: ReturnStmtNode) -> None:
        if self._in_function == 0:
            self.errors.error(
                ErrorCode.RETURN_OUTSIDE_FUNCTION,
                "return can only be used inside a function",
                node.span,
            )
        if node.value is not None:
            node.value.accept(self)
            # Check return type compatibility if function has a declared return type
            if self._current_return_type is not None:
                from helen.semantic.types import AnyType
                actual_type = self._infer_type(node.value)
                # Only check if we can infer a concrete type (not AnyType)
                if not isinstance(actual_type, AnyType):
                    if not type_compatible(actual_type, self._current_return_type):
                        self.errors.error(
                            ErrorCode.TYPE_MISMATCH,
                            f"return type '{actual_type.name}' is not compatible with declared return type '{self._current_return_type.name}'",
                            node.span,
                        )

    # ------------------------------------------------------------------
    # Expressions
    # ------------------------------------------------------------------

    def visit_literal(self, node: LiteralNode) -> None:
        pass  # literals are always valid

    def visit_binary_op(self, node: BinaryOpNode) -> None:
        node.left.accept(self)
        node.right.accept(self)

        # Const assignment protection: x = value where x is const
        from helen.core.tokens import TokenType
        if node.operator.type == TokenType.ASSIGN:
            if isinstance(node.left, VariableNode):
                self._check_const_assignment(node.left.name, node.span)
                # Type check on reassignment: declared type must be compatible with new value
                sym = self.symbols.resolve(node.left.name)
                if sym is not None and sym.type_node is not None:
                    expected = self._type_from_typenode(sym.type_node)
                    actual = self._infer_type(node.right)
                    if not type_compatible(actual, expected):
                        self.errors.error(
                            ErrorCode.SEMANTIC_TYPE_ERROR,
                            f"cannot assign {actual.name} to '{node.left.name}' of type {expected.name}",
                            node.span,
                        )

    def visit_unary_op(self, node: UnaryOpNode) -> None:
        node.operand.accept(self)

    def visit_grouping(self, node: GroupingNode) -> None:
        node.expression.accept(self)

    def visit_call(self, node: CallNode) -> None:
        # If callee is a known agent, skip variable resolution (agents are not in symbol table)
        if isinstance(node.callee, VariableNode):
            callee_name = node.callee.name
            if callee_name not in self._agent_names:
                node.callee.accept(self)
        else:
            node.callee.accept(self)
        for arg in node.arguments:
            arg.accept(self)

        # Check parameter types for function calls (compile-time check for literals)
        if isinstance(node.callee, VariableNode):
            callee_name = node.callee.name
            # Check if it's a known function with parameter type info
            if callee_name in self._function_param_types:
                param_types = self._function_param_types[callee_name]
                for i, arg in enumerate(node.arguments):
                    if i < len(param_types) and param_types[i] is not None:
                        expected_type = self._type_from_typenode(param_types[i])
                        # Only check if argument is a literal
                        if isinstance(arg.value, LiteralNode):
                            actual_type = type_of_literal(arg.value.value)
                            if not type_compatible(actual_type, expected_type):
                                self.errors.error(
                                    ErrorCode.TYPE_MISMATCH,
                                    f"argument {i+1} type '{actual_type.name}' is not compatible with parameter type '{expected_type.name}'",
                                    arg.value.span,
                                )

        # AGENT_PARAM_MISMATCH: if callee is a known agent, validate args
        if isinstance(node.callee, VariableNode):
            callee_name = node.callee.name
            if callee_name in self._agent_names:
                agent_node = self._agent_names[callee_name]
                if hasattr(agent_node, "params"):
                    agent_params = agent_node.params
                    param_names = {p.name for p in agent_params}
                    # Check each call arg
                    call_arg_names = set()
                    for arg in node.arguments:
                        if arg.name is not None:
                            if arg.name not in param_names:
                                self.errors.error(
                                    ErrorCode.AGENT_PARAM_MISMATCH,
                                    f"agent '{callee_name}' has no parameter named '{arg.name}'",
                                    arg.value.span if hasattr(arg.value, 'span') else node.span,
                                )
                            call_arg_names.add(arg.name)
                    # Soft check: required params without defaults — Helen allows partial args

    def visit_call_arg(self, node: CallArgNode) -> None:
        node.value.accept(self)

    def visit_index(self, node: IndexNode) -> None:
        node.target.accept(self)
        node.index.accept(self)

    def visit_access(self, node: AccessNode) -> None:
        node.target.accept(self)

    def visit_expr_stmt(self, node: ExprStmtNode) -> None:
        node.expression.accept(self)

    # ------------------------------------------------------------------
    # Lists, maps, templates
    # ------------------------------------------------------------------

    def visit_list_literal(self, node: ListLiteralNode) -> None:
        for elem in node.elements:
            elem.accept(self)

    def visit_map_entry(self, node: MapEntryNode) -> None:
        node.key.accept(self)
        node.value.accept(self)

    def visit_map_literal(self, node: MapLiteralNode) -> None:
        for entry in node.entries:
            entry.accept(self)

    def visit_template_ref(self, node: TemplateRefNode) -> None:
        node.expression.accept(self)

    # ------------------------------------------------------------------
    # Types
    # ------------------------------------------------------------------

    def visit_type(self, node: TypeNode) -> None:
        pass  # type references are validated during usage

    def visit_optional_type(self, node: OptionalTypeNode) -> None:
        node.inner.accept(self)

    def visit_union_type(self, node: UnionTypeNode) -> None:
        for member in node.members:
            member.accept(self)

    def visit_literal_type(self, node: LiteralTypeNode) -> None:
        for value in node.values:
            value.accept(self)

    # ------------------------------------------------------------------
    # Agent declaration & parameters
    # ------------------------------------------------------------------

    def visit_agent_decl(self, node: AgentDeclNode) -> None:
        # Check for duplicate param names in agent
        seen_params: set[str] = set()
        for param in node.params:
            if param.name in seen_params:
                self.errors.error(
                    ErrorCode.DUPLICATE_PARAM,
                    f"duplicate parameter '{param.name}' in agent '{node.name}'",
                    param.span,
                )
            seen_params.add(param.name)
            param.accept(self)

        # Validate agent name (PascalCase check)
        if node.name and node.name[0].islower():
            self.errors.warning(
                ErrorCode.INVALID_AGENT_NAME,
                f"Agent name '{node.name}' should be PascalCase",
                node.span,
            )

        # Check for duplicate agent names
        if node.name in self._agent_names:
            self.errors.error(
                ErrorCode.DUPLICATE_AGENT_NAME,
                f"duplicate agent name '{node.name}'",
                node.span,
            )
        else:
            self._agent_names[node.name] = node

        # Validate prompt if present (prompt is optional)
        if node.prompt is not None:
            node.prompt.accept(self)

    def visit_prompt_def(self, node: PromptDefNode) -> None:
        pass  # prompt content is a string, validated at runtime

    def visit_agent_param(self, node: AgentParamNode) -> None:
        if node.default_value is not None:
            node.default_value.accept(self)
        # Type annotation validation
        if node.type_annotation is not None:
            node.type_annotation.accept(self)

    def visit_declaration(self, node: DeclarationNode) -> None:
        pass  # config block, validated structurally

    # ------------------------------------------------------------------
    # Functions
    # ------------------------------------------------------------------

    def visit_function_decl(self, node: FunctionDeclNode) -> None:
        # Check for duplicate param names
        seen_params: set[str] = set()
        for param in node.params:
            if param.name in seen_params:
                self.errors.error(
                    ErrorCode.DUPLICATE_PARAM,
                    f"duplicate parameter '{param.name}' in function '{node.name}'",
                    param.span,
                )
            seen_params.add(param.name)
            param.accept(self)

        # Return type annotation
        if node.return_type is not None:
            node.return_type.accept(self)

        # Register function in current scope
        sym = Symbol(name=node.name, kind="function", type_node=node.return_type)
        existing = self.symbols.define(node.name, sym)
        if existing is not None:
            self.errors.error(
                ErrorCode.DUPLICATE_SYMBOL,
                f"duplicate declaration of '{node.name}'",
                node.span,
            )

        # Store parameter types for compile-time call checking
        self._function_param_types[node.name] = [p.type_annotation for p in node.params]

        # Record error count before body analysis to detect body-specific errors
        errors_before_body = len(self.errors.errors)

        # Save previous return type (for nested functions) and set current
        prev_return_type = self._current_return_type
        self._current_return_type = self._type_from_typenode(node.return_type)

        # Function body gets its own scope
        self._in_function += 1
        self.symbols.enter_scope(f"fn:{node.name}", "function")
        try:
            # Bind parameters in function scope
            for param in node.params:
                sym = Symbol(name=param.name, kind="param", type_node=param.type_annotation)
                self.symbols.define(param.name, sym)
            # Visit function body
            node.body.accept(self)
        finally:
            self.symbols.exit_scope()
            self._in_function -= 1
            self._current_return_type = prev_return_type

        # If body analysis produced new errors, remove the symbol
        # so the function can be redefined after fixing the error
        if len(self.errors.errors) > errors_before_body:
            self.symbols.undefine(node.name)

    def visit_fn_block(self, node: FnBlockNode) -> None:
        self._visit_stmts(node.body)

    # ------------------------------------------------------------------
    # Import
    # ------------------------------------------------------------------

    def visit_import_stmt(self, node: ImportStmtNode) -> None:
        path = node.module_path
        
        # Check if this is a Python module import
        # Python modules: no extension, or .py extension, or dotted names like "os.path"
        # Helen/data files: .helen, .json, .md, .txt, .yaml, .yml
        is_python_module = (
            path.endswith('.py') or  # Explicit .py extension
            not any(path.endswith(ext) for ext in ('.helen', '.json', '.md', '.txt', '.yaml', '.yml'))
        )
        
        if is_python_module:
            # Python module import - register the alias as a variable
            alias = node.alias if node.alias else path.split('.')[-1]
            from helen.semantic.symbols import Symbol
            sym = Symbol(alias, kind="import", is_const=False)
            self.symbols.define(alias, sym)
            return
        
        # Resolve relative to base_dir for Helen/data files
        target = os.path.join(self.base_dir, path)
        if not os.path.exists(target):
            self.errors.error(
                ErrorCode.IMPORT_NOT_FOUND,
                f"import file not found: '{path}'",
                node.span,
            )
            return
        
        # Register the alias as a variable in the current scope
        # For .helen files, agents/functions are registered separately
        # For .json/.md/.txt/.yaml files, the data is registered under the alias
        # If no alias specified, use the filename (without extension) as the alias
        if path.endswith(('.json', '.md', '.txt', '.yaml', '.yml')):
            alias = node.alias if node.alias else os.path.splitext(os.path.basename(path))[0]
            from helen.semantic.symbols import Symbol
            sym = Symbol(alias, kind="import", is_const=False)
            self.symbols.define(alias, sym)
        
        # Track imported paths to avoid duplicate processing for .helen files
        # But still allow multiple aliases for data files
        if path.endswith('.helen'):
            if path in self._imported_paths:
                return
            self._imported_paths.add(path)

    # ------------------------------------------------------------------
    # Async call
    # ------------------------------------------------------------------

    def visit_async_call_stmt(self, node: AsyncCallStmtNode) -> None:
        node.call.accept(self)

    def visit_async_call_expr(self, node) -> None:
        """Validate async expression: async Agent(...) -> Task."""
        node.call.accept(self)

    # ------------------------------------------------------------------
    # Try / catch / finally
    # ------------------------------------------------------------------

    def visit_try_stmt(self, node: TryStmtNode) -> None:
        # Try block
        self.symbols.enter_scope("try", "block")
        try:
            self._visit_stmts(node.body)
        finally:
            self.symbols.exit_scope()

        # Catch clauses — no catch_all_seen needed in v1
        for clause in node.catch_clauses:
            clause.accept(self)

        # Catch-all must be after all typed catches
        if node.catch_all is not None and node.catch_clauses:
            # Verify catch_all is structurally last (already guaranteed by parser order)
            # In v1 we trust the parser; future: detect catch before catch_all
            pass

        # Catch-all
        if node.catch_all is not None:
            node.catch_all.accept(self)

        # Finally block
        if node.finally_block is not None:
            node.finally_block.accept(self)

    def visit_throw_stmt(self, node: ThrowStmtNode) -> None:
        """Validate throw statement: exception type must be predefined."""
        # Validate exception type is a predefined exception
        type_name = node.exception_type.name
        if type_name not in _PREDEFINED_EXCEPTIONS:
            # Try case-insensitive match
            matched = any(t.lower() == type_name.lower() for t in _PREDEFINED_EXCEPTIONS)
            if not matched:
                self.errors.error(
                    ErrorCode.INVALID_CATCH_TYPE,
                    f"'{type_name}' is not a predefined exception type",
                    node.exception_type.span,
                )
        
        # Visit message expression if present
        if node.message is not None:
            node.message.accept(self)

    def visit_catch_clause(self, node: CatchClauseNode) -> None:
        # Validate error type is a predefined exception
        error_type_name = node.error_type.name.lower()
        # Map to check against predefined set (case-insensitive)
        type_name_pascal = node.error_type.name  # e.g., "TimeoutError"
        if type_name_pascal not in _PREDEFINED_EXCEPTIONS:
            # Try case-insensitive match
            matched = any(
                t.lower() == error_type_name for t in _PREDEFINED_EXCEPTIONS
            )
            if not matched:
                self.errors.error(
                    ErrorCode.INVALID_CATCH_TYPE,
                    f"'{node.error_type.name}' is not a predefined exception type",
                    node.error_type.span,
                )

        # Enter scope for catch clause and bind error name
        self.symbols.enter_scope("catch", "block")
        try:
            sym = Symbol(name=node.error_name, kind="variable")
            self.symbols.define(node.error_name, sym)
            self._visit_stmts(node.body)
        finally:
            self.symbols.exit_scope()

    def visit_catch_all(self, node: CatchAllNode) -> None:
        self.symbols.enter_scope("catch-all", "block")
        try:
            self._visit_stmts(node.body)
        finally:
            self.symbols.exit_scope()

    def visit_finally_block(self, node: FinallyBlockNode) -> None:
        self._visit_stmts(node.body)

    # ------------------------------------------------------------------
    # LLM statements
    # ------------------------------------------------------------------

    def visit_llm_if_stmt(self, node: LlmIfStmtNode) -> None:
        # Analyze description expression if it's not a plain string
        if not isinstance(node.description, str):
            node.description.accept(self)
        has_default = False
        for branch in node.branches:
            branch.accept(self)
            if branch.condition is None:
                has_default = True
        self._check_branch_completeness(has_default, node.span, "llm_if")

    def visit_llm_branch(self, node: LlmBranchNode) -> None:
        if node.condition is not None:
            node.condition.accept(self)
        self.symbols.enter_scope("llm-branch", "block")
        try:
            self._visit_stmts(node.body)
        finally:
            self.symbols.exit_scope()

    def visit_llm_act_expr(self, node: LlmActExprNode) -> None:
        """Visit llm act expression: analyze the prompt expression."""
        if node.prompt is not None:
            node.prompt.accept(self)

    def visit_llm_stream_stmt(self, node: LlmStreamStmtNode) -> None:
        """Visit llm stream statement: analyze prompt and optional callback."""
        node.prompt.accept(self)
        if node.on_chunk is not None:
            node.on_chunk.accept(self)

    # ------------------------------------------------------------------
    # Match
    # ------------------------------------------------------------------

    def visit_match_stmt(self, node: MatchStmtNode) -> None:
        node.subject.accept(self)
        for case in node.cases:
            case.accept(self)
        self._check_match_completeness(node)

    def visit_case(self, node: CaseNode) -> None:
        node.pattern.accept(self)
        self.symbols.enter_scope("match-case", "block")
        try:
            self._visit_stmts(node.body)
        finally:
            self.symbols.exit_scope()

    # ------------------------------------------------------------------
    # Type inference helper
    # ------------------------------------------------------------------

    def _infer_type(self, expr: ExpressionNode) -> AnyType:
        """Infer the type of an expression (v1: limited to literals).

        For non-literal expressions, returns AnyType.
        """
        if isinstance(expr, LiteralNode):
            return type_of_literal(expr.value)
        if isinstance(expr, ListLiteralNode):
            from helen.semantic.types import ListType
            if expr.elements:
                elem_type = self._infer_type(expr.elements[0])
                return ListType(elem_type)
            return AnyType()
        if isinstance(expr, MapLiteralNode):
            from helen.semantic.types import MapType
            if expr.entries:
                kt = self._infer_type(expr.entries[0].key)
                vt = self._infer_type(expr.entries[0].value)
                return MapType(kt, vt)
            return AnyType()
        return AnyType()
