"""Interpreter for the Helen language.

Walks the AST (as a Visitor[object]) executing deterministic statements:
variable declaration/assignment, control flow (if/for/while), function
definition/call, return/break/continue, const protection, match, and
expression evaluation.
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, Any

from helen.core.ast import (
    AccessNode,
    AgentDeclNode,
    AgentParamNode,
    AsyncCallExprNode,
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
from helen.core.source import SourceSpan
from helen.core.tokens import TokenType
from helen.interpreter.environment import Environment
from helen.interpreter.exceptions import (
    BreakSentinel,
    ConstAssignmentError,
    ContinueSentinel,
    HelenRuntimeError,
    ReturnSentinel,
    RuntimeError,
    error_matches,
    resolve_exception,
    _PREDEFINED_EXCEPTIONS,
)
from helen.runtime.llm_runtime import LLMRuntime, MockLLMRuntime
from helen.runtime.import_resolver import ImportResolver
from helen.runtime.history import HistoryManager, Message as HistoryMessage
from helen.interpreter.task import Task, AggregateError
from helen.semantic.types import (
    AnyType, IntType, FloatType, StringType, BoolType, NullType,
    NumberType, Type, type_compatible, type_of_literal,
)

if TYPE_CHECKING:
    pass


class Interpreter(Visitor[object]):
    """AST visitor that executes Helen programs.

    Each visit method returns the evaluated value of the node, or a
    control-flow sentinel (BreakSentinel, ContinueSentinel, ReturnSentinel).
    """

    def __init__(self, errors: ErrorReporter | None = None,
                 llm_runtime: LLMRuntime | None = None,
                 import_resolver: ImportResolver | None = None) -> None:
        self.errors = errors or ErrorReporter()
        self.environment = Environment()
        self._functions: dict[str, FunctionDeclNode] = {}
        self._agents: dict[str, AgentDeclNode] = {}
        self.llm_runtime = llm_runtime or MockLLMRuntime()
        self._current_agent: AgentDeclNode | None = None
        self.import_resolver = import_resolver or ImportResolver()
        # Merge imported agents/functions into local registries
        for name, agent in self.import_resolver.agents.items():
            self._agents[name] = agent
        for name, func in self.import_resolver.functions.items():
            self._functions[name] = func
        # Conversation history for LLM context (HLD 3.6.6, 3.12)
        self._history: list[HistoryMessage] = []
        self._history_manager = HistoryManager()
        # Register stdlib builtins in global environment (HLD M15)
        self._register_stdlib()

    def _register_stdlib(self) -> None:
        """Inject all stdlib functions into the global environment."""
        from helen.stdlib import stdlib  # noqa: PLC0415
        for name in stdlib.names:
            builtin = stdlib.lookup(name)
            if builtin is not None:
                self.environment.define(name, builtin.fn)

    # ------------------------------------------------------------------
    # REPL management helpers
    # ------------------------------------------------------------------

    def undefine_function(self, name: str) -> bool:
        """Remove a function from the registry. Returns True if it existed."""
        return self._functions.pop(name, None) is not None

    def undefine_agent(self, name: str) -> bool:
        """Remove an agent from the registry. Returns True if it existed."""
        return self._agents.pop(name, None) is not None

    def list_definitions(self) -> dict[str, list[str]]:
        """Return names of all user-defined functions and agents."""
        return {
            "functions": sorted(self._functions.keys()),
            "agents": sorted(self._agents.keys()),
        }

    def reset_definitions(self) -> None:
        """Clear all user-defined functions and agents (keep stdlib)."""
        self._functions.clear()
        self._agents.clear()
        self._current_agent = None
        # Re-register stdlib builtins
        self._register_stdlib()

    def interpret(self, program: ProgramNode) -> object:
        """Execute a Helen program.

        Args:
            program: The root ProgramNode.

        Returns:
            The result of the last statement executed, or None.
        """
        result = self.visit_program(program)
        # Unwrap sentinels at the top level
        if isinstance(result, ReturnSentinel):
            return result.value
        if isinstance(result, (BreakSentinel, ContinueSentinel)):
            return None
        return result

    # ------------------------------------------------------------------
    # Execution helper
    # ------------------------------------------------------------------

    def _execute(self, node: StatementNode) -> object:
        """Execute a statement node, returning its result."""
        return node.accept(self)

    def _execute_stmts(self, stmts: list[StatementNode]) -> object:
        """Execute a list of statements, returning the last result."""
        result = None
        for stmt in stmts:
            step = self._execute(stmt)
            if isinstance(step, ReturnSentinel):
                return step
            if isinstance(step, (BreakSentinel, ContinueSentinel)):
                # Return sentinel so loop handlers can consume it
                return step
            result = step
        return result

    # ------------------------------------------------------------------
    # Expression evaluation
    # ------------------------------------------------------------------

    def visit_literal(self, node: LiteralNode) -> object:
        """Return the literal value."""
        return node.value

    def visit_variable(self, node: VariableNode) -> object:
        """Look up a variable in the environment."""
        try:
            return self.environment.lookup(node.name)
        except NameError:
            self.errors.error(
                ErrorCode.UNDECLARED_VARIABLE,
                f"Undefined variable '{node.name}'",
                node.span,
            )
            return None

    def visit_binary_op(self, node: BinaryOpNode) -> object:
        """Evaluate a binary operation."""
        op = node.operator.type

        # Assignment is special: do NOT evaluate the left-hand side
        if op == TokenType.ASSIGN:
            right = node.right.accept(self)
            if isinstance(node.left, VariableNode):
                if self.environment.is_const(node.left.name):
                    raise ConstAssignmentError(node.left.name, node.span)
                try:
                    self.environment.assign(node.left.name, right)
                except NameError:
                    self._runtime_error(node.span, f"Undefined variable '{node.left.name}'")
                    return None
                return right
            self._runtime_error(node.span, "Invalid assignment target")
            return None

        left = node.left.accept(self)
        right = node.right.accept(self)

        if op == TokenType.PLUS:
            return self._add(left, right)
        if op == TokenType.MINUS:
            self._check_number(node.operator, left, right)
            return left - right
        if op == TokenType.STAR:
            self._check_number(node.operator, left, right)
            return left * right
        if op == TokenType.SLASH:
            self._check_number(node.operator, left, right)
            if right == 0:
                self._runtime_error(node.span, "Division by zero")
                return None
            return left / right
        if op == TokenType.PERCENT:
            self._check_number(node.operator, left, right)
            if right == 0:
                self._runtime_error(node.span, "Modulo by zero")
                return None
            return left % right
        if op == TokenType.EQUAL_EQUAL:
            return self._equal(left, right)
        if op == TokenType.BANG_EQUAL:
            return not self._equal(left, right)
        if op == TokenType.GREATER:
            self._check_number(node.operator, left, right)
            return left > right
        if op == TokenType.GREATER_EQUAL:
            self._check_number(node.operator, left, right)
            return left >= right
        if op == TokenType.LESS:
            self._check_number(node.operator, left, right)
            return left < right
        if op == TokenType.LESS_EQUAL:
            self._check_number(node.operator, left, right)
            return left <= right
        if op == TokenType.AND:
            return self._truthy(left) and self._truthy(right)
        if op == TokenType.OR:
            return self._truthy(left) or self._truthy(right)
        if op == TokenType.ASSIGN:
            # Runtime const protection
            if isinstance(node.left, VariableNode):
                if self.environment.is_const(node.left.name):
                    raise ConstAssignmentError(node.left.name, node.span)
                try:
                    self.environment.assign(node.left.name, right)
                except NameError:
                    self._runtime_error(node.span, f"Undefined variable '{node.left.name}'")
                    return None
                return right
            self._runtime_error(node.span, "Invalid assignment target")
            return None

        self._runtime_error(node.span, f"Unknown operator '{node.operator.lexeme}'")
        return None

    def visit_unary_op(self, node: UnaryOpNode) -> object:
        """Evaluate a unary operation."""
        operand = node.operand.accept(self)
        op = node.operator.type

        if op == TokenType.BANG:
            return not self._truthy(operand)
        if op == TokenType.MINUS:
            self._check_number(node.operator, operand)
            return -operand
        if op == TokenType.AWAIT:
            # await task or await [task1, task2, ...] (HLD 3.6.7)
            # operand is either a Task or a list of Tasks
            return self._await_tasks(operand)

        self._runtime_error(node.span, f"Unknown unary operator '{node.operator.lexeme}'")
        return None

    def visit_grouping(self, node: GroupingNode) -> object:
        """Evaluate a grouped expression."""
        return node.expression.accept(self)

    def visit_call(self, node: CallNode) -> object:
        """Evaluate a function or agent call (HLD 3.6.2, 3.5.2).

        Call resolution order:
        1. Check if callee matches a registered function -> call function
        2. Check if callee matches a registered agent -> call agent (isolated env)
        3. Otherwise evaluate callee as expression and try to call
        """
        callee_name = node.callee.name if isinstance(node.callee, VariableNode) else None

        # First check if callee name matches a registered function
        if callee_name is not None and callee_name in self._functions:
            func = self._functions[callee_name]
            args = [arg.value.accept(self) for arg in node.arguments]
            return self._call_function(func, args)

        # Check if callee matches a registered agent (HLD 3.5.2: isolated env)
        if callee_name is not None and callee_name in self._agents:
            agent = self._agents[callee_name]
            # Build args dict: support both named and positional arguments
            agent_args: dict[str, object] = {}
            for i, arg in enumerate(node.arguments):
                if arg.name is not None:
                    # Named argument: text="hello"
                    agent_args[arg.name] = arg.value.accept(self)
                elif i < len(agent.params):
                    # Positional argument: bind to i-th parameter
                    agent_args[agent.params[i].name] = arg.value.accept(self)
                else:
                    self._runtime_error(
                        node.span,
                        f"too many positional arguments for agent '{callee_name}' "
                        f"(expected at most {len(agent.params)})"
                    )
            return self._call_agent(agent, agent_args)

        # Otherwise evaluate the callee as an expression
        callee = node.callee.accept(self)

        # Evaluate arguments
        args = []
        for arg in node.arguments:
            args.append(arg.value.accept(self))

        # Function call (if callee was a function node directly)
        if isinstance(callee, FunctionDeclNode):
            return self._call_function(callee, args)

        # Check if callee is a stdlib builtin function (HLD M15)
        if callable(callee):
            return callee(*args)

        callee_str = callee_name if callee_name else type(callee).__name__
        self._runtime_error(node.span, f"'{callee_str}' is not callable")
        return None

    def visit_call_arg(self, node: CallArgNode) -> object:
        """Evaluate a call argument value."""
        return node.value.accept(self)

    def visit_index(self, node: IndexNode) -> object:
        """Evaluate index access: target[index]."""
        target = node.target.accept(self)
        index = node.index.accept(self)
        try:
            if isinstance(target, (list, tuple)):
                if isinstance(index, int):
                    return target[index]
                self._runtime_error(node.span, f"List index must be integer, got {type(index).__name__}")
                return None
            if isinstance(target, dict):
                return target[index]
            self._runtime_error(node.span, f"Type {type(target).__name__} does not support indexing")
            return None
        except (KeyError, IndexError, TypeError) as e:
            self._runtime_error(node.span, str(e))
            return None

    def visit_access(self, node: AccessNode) -> object:
        """Evaluate member access: target.property."""
        target = node.target.accept(self)
        try:
            if isinstance(target, dict):
                return target[node.property]
            if hasattr(target, node.property):
                return getattr(target, node.property)
            self._runtime_error(node.span, f"'{type(target).__name__}' has no property '{node.property}'")
            return None
        except KeyError:
            self._runtime_error(node.span, f"Property '{node.property}' not found")
            return None

    def visit_expr_stmt(self, node: ExprStmtNode) -> object:
        """Evaluate an expression as a statement."""
        return node.expression.accept(self)

    # ------------------------------------------------------------------
    # Collections
    # ------------------------------------------------------------------

    def visit_list_literal(self, node: ListLiteralNode) -> object:
        """Evaluate a list literal: [expr, ...]."""
        return [elem.accept(self) for elem in node.elements]

    def visit_map_entry(self, node: MapEntryNode) -> tuple:
        """Evaluate a map entry: (key, value)."""
        return (node.key.accept(self), node.value.accept(self))

    def visit_map_literal(self, node: MapLiteralNode) -> object:
        """Evaluate a map literal: {key: value, ...}."""
        result = {}
        for entry in node.entries:
            key, value = entry.accept(self)
            result[key] = value
        return result

    def visit_template_ref(self, node: TemplateRefNode) -> object:
        """Evaluate a template reference: {{expr}}."""
        return node.expression.accept(self)

    # ------------------------------------------------------------------
    # Types (no-op at runtime in v1)
    # ------------------------------------------------------------------

    def visit_type(self, node: TypeNode) -> object:
        """Type node: no runtime action in v1."""
        return None

    def visit_optional_type(self, node: OptionalTypeNode) -> object:
        return None

    def visit_union_type(self, node: UnionTypeNode) -> object:
        return None

    def visit_literal_type(self, node: LiteralTypeNode) -> object:
        return None

    # ------------------------------------------------------------------
    # Variable declaration
    # ------------------------------------------------------------------

    def visit_var_decl(self, node: VarDeclNode) -> object:
        """Execute a variable declaration: let/const name = expr."""
        value = None
        if node.initializer is not None:
            value = node.initializer.accept(self)
        is_const = not node.mutable
        self.environment.define(node.name, value, is_const=is_const)
        return value

    # ------------------------------------------------------------------
    # Control flow
    # ------------------------------------------------------------------

    def visit_if_stmt(self, node: IfStmtNode) -> object:
        """Execute an if/else statement."""
        condition = node.condition.accept(self)
        if self._truthy(condition):
            return node.then_branch.accept(self)
        if node.else_branch is not None:
            return node.else_branch.accept(self)
        return None

    def visit_for_stmt(self, node: ForStmtNode) -> object:
        """Execute a for-in loop."""
        iterable = node.iterable.accept(self)
        if not isinstance(iterable, (list, tuple)):
            self._runtime_error(node.span, f"Cannot iterate over {type(iterable).__name__}")
            return None

        result = None
        for item in iterable:
            # Create a new scope for each iteration? No -- Helen uses
            # block scope: one scope for the entire loop body.
            # We'll use a fresh scope per loop to match semantic analysis.
            old_env = self.environment
            self.environment = self.environment.enter_scope()
            try:
                if node.iterator is not None:
                    self.environment.define(node.iterator.name, item)
                result = self._execute(node.body)
                if isinstance(result, BreakSentinel):
                    break
                if isinstance(result, ContinueSentinel):
                    continue
                if isinstance(result, ReturnSentinel):
                    return result
            finally:
                self.environment = old_env

        return result

    def visit_while_stmt(self, node: WhileStmtNode) -> object:
        """Execute a while loop."""
        result = None
        while True:
            condition = node.condition.accept(self)
            if not self._truthy(condition):
                break
            step_result = self._execute(node.body)
            if isinstance(step_result, BreakSentinel):
                break
            if isinstance(step_result, ContinueSentinel):
                continue
            if isinstance(step_result, ReturnSentinel):
                return step_result
            result = step_result
        return result

    def visit_break_stmt(self, node: BreakStmtNode) -> object:
        """Return a break sentinel."""
        return BreakSentinel(span=node.span)

    def visit_continue_stmt(self, node: ContinueStmtNode) -> object:
        """Return a continue sentinel."""
        return ContinueSentinel(span=node.span)

    def visit_return_stmt(self, node: ReturnStmtNode) -> object:
        """Return a return sentinel with the value."""
        value = None
        if node.value is not None:
            value = node.value.accept(self)
        return ReturnSentinel(value=value)

    # ------------------------------------------------------------------
    # Functions
    # ------------------------------------------------------------------

    def visit_function_decl(self, node: FunctionDeclNode) -> object:
        """Register a function definition (do not execute)."""
        self._functions[node.name] = node
        return None

    def visit_fn_block(self, node: FnBlockNode) -> object:
        """Execute a function body (list of statements)."""
        return self._execute_stmts(node.body)

    def visit_agent_decl(self, node: AgentDeclNode) -> object:
        """Register an agent definition (do not execute)."""
        self._agents[node.name] = node
        # Track as current agent for llm act setting extraction (HLD 3.6.5)
        self._current_agent = node
        return None

    def visit_agent_param(self, node: AgentParamNode) -> object:
        return None

    def visit_declaration(self, node: DeclarationNode) -> object:
        return None

    def visit_prompt_def(self, node: PromptDefNode) -> object:
        return None

    # ------------------------------------------------------------------
    # Program & blocks
    # ------------------------------------------------------------------

    def visit_program(self, node: ProgramNode) -> object:
        return self._execute_stmts(node.statements)

    def visit_main_block(self, node: MainBlockNode) -> object:
        """Execute a main block."""
        old_env = self.environment
        self.environment = self.environment.enter_scope()
        try:
            return self._execute_stmts(node.body)
        finally:
            self.environment = old_env

    # ------------------------------------------------------------------
    # Match
    # ------------------------------------------------------------------

    def visit_match_stmt(self, node: MatchStmtNode) -> object:
        """Execute a match statement."""
        subject = node.subject.accept(self)
        for case in node.cases:
            pattern = case.pattern.accept(self)
            if self._equal(subject, pattern):
                old_env = self.environment
                self.environment = self.environment.enter_scope()
                try:
                    return self._execute_stmts(case.body)
                finally:
                    self.environment = old_env
        # Default branch
        if node.default:
            old_env = self.environment
            self.environment = self.environment.enter_scope()
            try:
                return self._execute_stmts(node.default)
            finally:
                self.environment = old_env
        return None

    def visit_case(self, node: CaseNode) -> object:
        # Cases are handled inside visit_match_stmt
        return None

    # ------------------------------------------------------------------
    # Try/catch/finally (basic)
    # ------------------------------------------------------------------

    def visit_try_stmt(self, node: TryStmtNode) -> object:
        """Execute a try-catch-finally statement (HLD 3.6.4).

        Execution flow:
        1. Execute try body
        2. If HelenRuntimeError raised, match typed catches in order
        3. If no typed catch matches, try catch-all
        4. Finally block always executes
        5. If uncaught, re-raise
        """
        result = None
        caught = False
        exc_to_rethrow: HelenRuntimeError | None = None

        # Execute try body
        try:
            old_env = self.environment
            self.environment = self.environment.enter_scope()
            try:
                result = self._execute_stmts(node.body)
            finally:
                self.environment = old_env
        except HelenRuntimeError as exc:
            caught = True
            exc_to_rethrow = exc

            # Match typed catches in order (HLD 3.6.4 inheritance support)
            for clause in node.catch_clauses:
                error_type_name = clause.error_type.name
                if error_matches(exc, error_type_name):
                    old_env = self.environment
                    self.environment = self.environment.enter_scope()
                    try:
                        self.environment.define(clause.error_name, exc)
                        catch_result = self._execute_stmts(clause.body)
                        if isinstance(catch_result, ReturnSentinel):
                            result = catch_result.value
                            caught = False
                            return result
                        result = catch_result
                    finally:
                        self.environment = old_env
                    caught = False
                    break

            # Try catch-all if no typed catch matched
            if caught and node.catch_all is not None:
                old_env = self.environment
                self.environment = self.environment.enter_scope()
                try:
                    catch_result = self._execute_stmts(node.catch_all.body)
                    if isinstance(catch_result, ReturnSentinel):
                        result = catch_result.value
                        caught = False
                        return result
                    result = catch_result
                finally:
                    self.environment = old_env
                caught = False

        finally:
            # Finally block always executes (HLD 3.6.4)
            if node.finally_block is not None:
                old_env = self.environment
                self.environment = self.environment.enter_scope()
                try:
                    self._execute_stmts(node.finally_block.body)
                finally:
                    self.environment = old_env

            # Re-raise if not caught
            if caught and exc_to_rethrow is not None:
                raise exc_to_rethrow

        return result

    def visit_catch_clause(self, node: CatchClauseNode) -> object:
        return None

    def visit_catch_all(self, node: CatchAllNode) -> object:
        return None

    def visit_finally_block(self, node: FinallyBlockNode) -> object:
        return None

    def visit_throw_stmt(self, node: ThrowStmtNode) -> object:
        """Execute a throw statement: raise the specified exception."""
        # Resolve exception type
        type_name = node.exception_type.name
        exc_class = resolve_exception(type_name)
        if exc_class is None:
            # Try case-insensitive match
            for name, cls in _PREDEFINED_EXCEPTIONS.items():
                if name.lower() == type_name.lower():
                    exc_class = cls
                    break
        
        if exc_class is None:
            # Should not happen if semantic analysis passed, but handle gracefully
            self._runtime_error(
                node.span,
                f"'{type_name}' is not a valid exception type"
            )
            return None
        
        # Evaluate message if present
        message = None
        if node.message is not None:
            message = node.message.accept(self)
            if not isinstance(message, str):
                message = str(message)
        else:
            # Use default message from exception class
            message = exc_class.__init__.__defaults__[0] if exc_class.__init__.__defaults__ else f"{type_name} thrown"
        
        # Raise the exception
        raise exc_class(message, node.span)

    # ------------------------------------------------------------------
    # Import & LLM (stubs for Phase 3)
    # ------------------------------------------------------------------

    def visit_import_stmt(self, node: ImportStmtNode) -> object:
        """Execute an import statement (HLD 3.9, 3.6.2).

        Per HLD: import only parses and registers Agent/Function definitions
        from the imported file. It does NOT execute the imported file's main block.

        Supported formats:
        - .helen: Parse and register agents/functions to global namespace
        - .md/.txt: Load as text, register to import_resolver.data
        - .json/.yaml: Parse as data, register to import_resolver.data
        """
        # Track the current file for relative path resolution
        current_file = node.source_file if hasattr(node, 'source_file') else None

        result = self.import_resolver.resolve(node.module_path, current_file)
        if result is None:
            # Error already reported by ImportResolver
            return None

        # Register imported content into the interpreter's namespaces
        if result.format == "helen":
            for name, agent in self.import_resolver.agents.items():
                if name not in self._agents:
                    self._agents[name] = agent
            for name, func in self.import_resolver.functions.items():
                if name not in self._functions:
                    self._functions[name] = func
        else:
            # Register data by user-specified alias (or filename if no alias)
            alias = node.alias if node.alias else os.path.splitext(os.path.basename(result.path))[0]
            # Define the variable in the environment
            self.environment.define(alias, result.content)

        return None

    def visit_async_call_stmt(self, node: AsyncCallStmtNode) -> object:
        """Execute async call statement (HLD 3.6.7).

        In v1 synchronous mode, executes the call immediately but wraps
        the result in a Task object for await semantics.

        Returns:
            A Task object wrapping the call result or exception.
        """
        try:
            result = node.call.accept(self)
            return Task.completed(result)
        except Exception as exc:
            return Task.failed(exc)

    def visit_async_call_expr(self, node: AsyncCallExprNode) -> object:
        """Execute async call expression (HLD 3.6.7).

        Phase 1b: Creates a pending Task that will execute on await.
        This enables true concurrency when multiple async calls are awaited together.

        Example: let task = async Worker("input")

        Returns:
            A pending Task object that executes on await.
        """
        # Create environment snapshot for isolation
        env_snapshot = self.environment.snapshot()
        
        # Create pending task (will execute on await)
        return Task.pending(node.call, self, env_snapshot)

    def visit_llm_if_stmt(self, node: LlmIfStmtNode) -> object:
        """Execute llm if statement (HLD 3.6.5, 3.6.6).

        Flow:
        1. Build route prompt from description + branches
        2. Call runtime.route() with function calling schema
        3. Match returned branch name to execute corresponding body
        4. If no match or parsing fails -> execute default branch
        """
        branches = []
        for b in node.branches:
            if b.condition is not None:
                # Get branch name from condition expression
                if isinstance(b.condition, LiteralNode):
                    branches.append(str(b.condition.value))
                else:
                    branches.append(str(b.condition))
            else:
                branches.append("default")

        # Evaluate description expression to string
        if isinstance(node.description, str):
            desc_str = node.description
        else:
            desc_val = node.description.accept(self)
            desc_str = str(desc_val) if desc_val is not None else ""

        # Get context from environment (conversation summary)
        context = self._get_context()

        # Record user message to history
        self._add_to_history("user", f"[route] {desc_str}")

        # Call LLM routing
        try:
            selected = self.llm_runtime.route(desc_str, branches, context)
        except HelenRuntimeError:
            # LLM call failed -> execute default
            selected = None

        # Record assistant response to history
        if selected is not None:
            self._add_to_history("assistant", f"[routed to: {selected}]")

        # Validate against pre-defined enum (HLD 3.6.6: branch must match schema)
        if selected is not None and selected not in branches:
            selected = None

        # Find matching branch
        for b in node.branches:
            if b.condition is not None:
                branch_name = None
                if isinstance(b.condition, LiteralNode):
                    branch_name = str(b.condition.value)
                else:
                    branch_name = str(b.condition)
                if branch_name == selected:
                    old_env = self.environment
                    self.environment = self.environment.enter_scope()
                    try:
                        return self._execute_stmts(b.body)
                    finally:
                        self.environment = old_env

        # No match -> execute default
        for b in node.branches:
            if b.condition is None:
                old_env = self.environment
                self.environment = self.environment.enter_scope()
                try:
                    return self._execute_stmts(b.body)
                finally:
                    self.environment = old_env
        return None

    def visit_llm_branch(self, node: LlmBranchNode) -> object:
        """Execute an llm if branch body."""
        return self._execute_stmts(node.body)

    def visit_llm_act_expr(self, node: LlmActExprNode) -> object:
        """Execute llm act as an expression: llm act <prompt_expr>?

        Evaluates the prompt expression and calls the LLM runtime.
        Returns the LLM response text.
        If inside an agent with a prompt field, uses it as system_prompt.

        Bare form (``llm act`` with no expression, or ``llm act ""``):
        When inside an agent context, the agent's rendered prompt template
        is used as the user message automatically. This avoids redundant
        repetition when the agent's prompt already contains all necessary
        information (HLD 3.6.5).
        """
        # Evaluate the prompt expression
        if node.prompt is not None:
            prompt = node.prompt.accept(self)
            if not isinstance(prompt, str):
                prompt = self._stringify(prompt)
        else:
            prompt = ""

        # Bare form: if prompt is empty and we're inside an agent,
        # use the rendered agent prompt as the user message
        if not prompt and self._current_agent is not None:
            rendered = self._get_rendered_agent_prompt()
            if rendered:
                prompt = rendered

        # Extract agent settings if inside an agent context
        model = self._get_agent_setting("model")
        temperature = float(self._get_agent_setting("temperature", 1.0))
        max_turns = int(self._get_agent_setting("max-turns", 1))

        # Build tools list: always include load_skill + agent-declared tools
        tools = self._build_tools_list()

        # When tools are available, ensure at least 3 turns (tool call + tool result + response)
        if tools and max_turns < 3:
            max_turns = 3

        # Get rendered agent prompt as system_prompt
        system_prompt = self._get_rendered_agent_prompt()

        # Record user message to history
        self._add_to_history("user", prompt)

        try:
            response = self.llm_runtime.act(
                prompt, tools=tools, model=model,
                temperature=temperature, max_turns=max_turns,
                system_prompt=system_prompt,
            )
            # Record assistant response to history
            if response and response.text:
                self._add_to_history("assistant", response.text)
            return response.text if response else None
        except HelenRuntimeError:
            return None

    def visit_llm_stream_stmt(self, node: LlmStreamStmtNode) -> object:
        """Execute llm stream statement: stream LLM response chunk by chunk.
        
        If on_chunk callback is provided, call it for each chunk.
        Otherwise, use stream_print to output chunks to stdout.
        """
        # Evaluate the prompt expression
        prompt = node.prompt.accept(self)
        if not isinstance(prompt, str):
            prompt = self._stringify(prompt)
        
        # Extract agent settings if inside an agent context
        model = self._get_agent_setting("model")
        temperature = float(self._get_agent_setting("temperature", 1.0))
        
        # Get rendered agent prompt as system_prompt
        system_prompt = self._get_rendered_agent_prompt()
        
        # Record user message to history
        self._add_to_history("user", prompt)
        
        # Check if LLM runtime supports streaming
        from helen.runtime.llm_runtime import LLMRuntime
        if not hasattr(self.llm_runtime, 'act_stream'):
            # Fallback to non-streaming if not supported
            self.errors.error(
                ErrorCode.RUNTIME_ERROR,
                "LLM runtime does not support streaming. Using fallback.",
                node.span,
            )
            response = self.llm_runtime.act(
                prompt, model=model, temperature=temperature,
                system_prompt=system_prompt,
            )
            if response and response.text:
                # Use stream_print for output
                from helen.stdlib import stdlib
                stream_print_fn = stdlib.lookup("stream_print")
                if stream_print_fn:
                    stream_print_fn.fn(response.text)
                    print()  # Add newline at end
                self._add_to_history("assistant", response.text)
            return None
        
        # Evaluate on_chunk callback if provided
        on_chunk_fn = None
        if node.on_chunk is not None:
            on_chunk_fn = node.on_chunk.accept(self)
            if not callable(on_chunk_fn):
                self.errors.error(
                    ErrorCode.SEMANTIC_TYPE_ERROR,
                    f"on_chunk callback must be callable, got {type(on_chunk_fn).__name__}",
                    node.span,
                )
                return None
        
        try:
            # Stream response chunk by chunk
            full_response = []
            for chunk in self.llm_runtime.act_stream(
                prompt, model=model, temperature=temperature,
                system_prompt=system_prompt,
            ):
                # Handle both dict and object chunk formats
                if isinstance(chunk, dict):
                    content = chunk.get("content", "")
                elif hasattr(chunk, "content"):
                    content = chunk.content
                else:
                    content = str(chunk)
                if content:
                    full_response.append(content)
                    if on_chunk_fn is not None:
                        # Call user-provided callback
                        on_chunk_fn(content)
                    else:
                        # Use stream_print for auto-output
                        from helen.stdlib import stdlib
                        stream_print_fn = stdlib.lookup("stream_print")
                        if stream_print_fn:
                            stream_print_fn.fn(content)
            
            # Add newline at end if using auto-output
            if on_chunk_fn is None:
                print()
            
            # Record assistant response to history
            full_text = "".join(full_response)
            if full_text:
                self._add_to_history("assistant", full_text)
            
            return None
        except Exception as e:
            self.errors.error(
                ErrorCode.RUNTIME_ERROR,
                f"Streaming LLM call failed: {e}",
                node.span,
            )
            return None

    # ------------------------------------------------------------------
    # Helper methods
    # ------------------------------------------------------------------

    @staticmethod
    def _truthy(value: object) -> bool:
        """Convert a Helen value to boolean.

        Rules:
        - None/null -> False
        - False -> False
        - 0, 0.0 -> False
        - Empty string -> False
        - Empty list/dict -> False
        - Everything else -> True
        """
        if value is None:
            return False
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)):
            return value != 0
        if isinstance(value, str):
            return len(value) > 0
        if isinstance(value, (list, dict)):
            return len(value) > 0
        return True

    @staticmethod
    def _equal(a: object, b: object) -> bool:
        """Check equality between two Helen values."""
        if a is None and b is None:
            return True
        if a is None or b is None:
            return False
        return a == b

    @staticmethod
    def _check_number(op_token, *values: object) -> None:
        """Raise a runtime error if any value is not a number."""
        for v in values:
            if not isinstance(v, (int, float)):
                span = op_token.span if hasattr(op_token, 'span') else None
                raise HelenRuntimeError(
                    f"Operator '{op_token.lexeme}' requires numbers, got {type(v).__name__}",
                    span,
                )

    @staticmethod
    def _add(left: object, right: object) -> object:
        """Addition with string concatenation support."""
        if isinstance(left, str) or isinstance(right, str):
            return str(left) + str(right)
        if isinstance(left, (int, float)) and isinstance(right, (int, float)):
            return left + right
        raise HelenRuntimeError(
            f"Cannot add {type(left).__name__} and {type(right).__name__}"
        )

    @staticmethod
    def _stringify(value: object) -> str:
        """Convert a Helen value to its string representation."""
        if value is None:
            return "null"
        if isinstance(value, bool):
            return "true" if value else "false"
        if isinstance(value, float):
            # Format integers without decimal point
            if value == int(value):
                return str(int(value))
            return str(value)
        if isinstance(value, list):
            items = ", ".join(Interpreter._stringify(item) for item in value)
            return f"[{items}]"
        if isinstance(value, dict):
            items = ", ".join(
                f"{Interpreter._stringify(k)}: {Interpreter._stringify(v)}"
                for k, v in value.items()
            )
            return f"{{{items}}}"
        return str(value)

    def _type_from_typenode(self, type_node: TypeNode | None) -> "Type":
        """Convert an AST TypeNode to a semantic Type."""
        if type_node is None:
            return AnyType()

        # Handle composite type nodes (OptionalTypeNode, UnionTypeNode, LiteralTypeNode)
        from helen.core.ast import OptionalTypeNode, UnionTypeNode, LiteralTypeNode
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
            return IntType()
        if name == "float" or name == "double":
            return FloatType()
        if name == "str" or name == "string":
            return StringType()
        if name == "bool" or name == "boolean":
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

    def _call_function(self, func: FunctionDeclNode, args: list[object]) -> object:
        """Call a function with the given arguments.

        Creates a new environment scope, binds parameters, and executes
        the function body.
        """
        # Runtime parameter type checking
        for i, param in enumerate(func.params):
            if i < len(args) and param.type_annotation is not None:
                expected_type = self._type_from_typenode(param.type_annotation)
                actual_value = args[i]
                # Only check if we can infer the type (not None or unknown)
                if actual_value is not None:
                    actual_type = type_of_literal(actual_value)
                    if not isinstance(actual_type, AnyType):
                        if not type_compatible(actual_type, expected_type):
                            raise HelenRuntimeError(
                                f"argument {i+1} type '{actual_type.name}' is not compatible with parameter type '{expected_type.name}'"
                            )

        call_env = self.environment.enter_scope()

        # Bind parameters
        for i, param in enumerate(func.params):
            if i < len(args):
                call_env.define(param.name, args[i])
            elif param.default_value is not None:
                # Evaluate default in caller's environment
                default_val = param.default_value.accept(self)
                call_env.define(param.name, default_val)
            else:
                # Too few arguments — use None
                call_env.define(param.name, None)

        # Execute function body in the new environment
        old_env = self.environment
        self.environment = call_env
        try:
            result = self._execute_stmts(func.body.body)
            if isinstance(result, ReturnSentinel):
                return result.value
            return result
        finally:
            self.environment = old_env

    def _call_agent(self, agent: AgentDeclNode, args: dict[str, object]) -> object:
        """Call an agent with the given arguments (HLD 3.5.2, 3.6.2).

        Per HLD 3.5.2: Sub-agents get a completely isolated Environment.
        They do NOT inherit parent agent's variables. The only parameter
        passing channel is explicit call Agent(param=value) arguments.

        Args:
            agent: The AgentDeclNode to execute.
            args: Keyword arguments from the call statement.
        """
        # Create a completely isolated environment (HLD 3.5.2)
        # Start from a fresh root, not inheriting parent agent's variables.
        # But stdlib must still be available — inject it into the fresh env.
        call_env = Environment()
        from helen.stdlib import stdlib as _stdlib  # noqa: PLC0415
        for _name in _stdlib.names:
            _builtin = _stdlib.lookup(_name)
            if _builtin is not None:
                call_env.define(_name, _builtin.fn)

        # Bind parameters from agent's param declarations
        for param in agent.params:
            if param.name in args:
                call_env.define(param.name, args[param.name])
            elif param.default_value is not None:
                # Evaluate default in caller's environment (parent interpreter)
                default_val = param.default_value.accept(self)
                call_env.define(param.name, default_val)
            else:
                # No argument and no default -> None
                call_env.define(param.name, None)

        # Track as current agent for llm act setting extraction
        old_agent = self._current_agent
        self._current_agent = agent

        # Register agent's functions { } block functions into scope (HLD 3.5.3)
        # Save and restore to avoid leaking into caller's scope
        registered_names: list[str] = []
        for func_node in agent.functions:
            old_val = self._functions.get(func_node.name)
            self._functions[func_node.name] = func_node
            registered_names.append(func_node.name)

        # Execute the agent's logic (main block)
        old_env = self.environment
        self.environment = call_env
        try:
            if agent.logic is not None:
                result = agent.logic.accept(self)
                if isinstance(result, ReturnSentinel):
                    return result.value
                return result
            return None
        finally:
            self.environment = old_env
            self._current_agent = old_agent
            # Unregister agent functions to avoid leaking
            for fname in registered_names:
                self._functions.pop(fname, None)

    def _await_tasks(self, tasks: list[Task] | Task) -> object:
        """Await one or more tasks with Promise.all semantics (HLD 3.6.7).

        Phase 1b: Executes pending tasks concurrently using asyncio.
        Uses asyncio.to_thread() for sync interpreter code, which uses
        a global thread pool (fixed memory, not per-task threads).

        For a single task: returns its result or raises its exception.
        For a list of tasks: returns list of results if all succeed,
        or raises AggregateError containing all failed task exceptions.

        Args:
            tasks: A single Task or list of Task objects.

        Returns:
            Single result for one task, list of results for multiple tasks.

        Raises:
            The task's exception for single failed task.
            AggregateError if any task in a list fails.
        """
        import asyncio
        
        # Check if we're already in a running event loop (e.g., in REPL)
        # Use a safer approach that works in all contexts
        in_event_loop = False
        try:
            _loop = asyncio.get_event_loop()
            if _loop.is_running():
                in_event_loop = True
        except Exception:
            # No event loop or can't determine
            in_event_loop = False
        
        if isinstance(tasks, Task):
            # Single task: execute if pending, then return result or raise exception
            if tasks.is_pending:
                if in_event_loop:
                    # Already in event loop - use thread pool directly
                    import concurrent.futures
                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        future = executor.submit(tasks.execute)
                        future.result()  # Wait for completion
                else:
                    # No event loop - use asyncio.run()
                    asyncio.run(tasks.execute_async())
            return tasks.result()

        # List of tasks: execute pending tasks concurrently using asyncio
        pending_tasks = [t for t in tasks if t.is_pending]
        
        if pending_tasks:
            if in_event_loop:
                # Already in event loop - use thread pool for concurrency
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    futures = [executor.submit(task.execute) for task in pending_tasks]
                    # Wait for all to complete
                    for future in concurrent.futures.as_completed(futures):
                        future.result()  # Raise any exceptions
            else:
                # No event loop - use asyncio.run()
                async def execute_all():
                    # Create coroutines for all pending tasks
                    coros = [task.execute_async() for task in pending_tasks]
                    # Execute concurrently
                    await asyncio.gather(*coros)
                
                asyncio.run(execute_all())

        # Collect results from all tasks (both pending and already completed)
        results = []
        errors = []

        for task in tasks:
            if task.has_error:
                errors.append(task.exception)
            else:
                results.append(task.result())

        if errors:
            # Per HLD 3.6.7: AggregateError contains all failures
            raise AggregateError(
                f"{len(errors)} task(s) failed",
                errors=errors,
            )

        return results

    def _get_agent_setting(self, name: str, default: Any = None) -> Any:
        """Extract a setting from the current agent's declarations (HLD 3.6.5).

        Scans the current AgentDeclNode's declaration list for a matching
        setting and returns its literal value. Returns default if the agent
        context is not available or the setting is not declared.
        """
        if self._current_agent is None:
            return default
        for decl in self._current_agent.declarations:
            # Map HLD setting names to DeclarationNode fields
            field_map = {
                "model": "model",
                "temperature": "temperature",
                "max-turns": "max_turns",
            }
            field = field_map.get(name)
            if field is not None:
                value = getattr(decl, field, None)
                if value is not None and isinstance(value, LiteralNode):
                    return value.value
        return default

    def _build_tools_list(self) -> list[dict[str, Any]]:
        """Build the tools list for llm act from agent declarations.

        Always includes load_skill (HLD 3.6.5) for Tier 2 skill disclosure.
        If the agent declares `tools ["web_search", ...]`, includes those
        built-in tool schemas from the Helen tool registry.
        If no tools are declared, includes a default set of useful tools.
        """
        from helen.runtime.tools import get_tool_schemas

        tools: list[dict[str, Any]] = []

        # Check if agent declared specific tools
        declared_tools: list[str] | None = None
        if self._current_agent is not None:
            for decl in self._current_agent.declarations:
                if decl.tools is not None:
                    # decl.tools is a LiteralNode wrapping a list[str]
                    tools_node = decl.tools
                    if isinstance(tools_node, LiteralNode) and isinstance(tools_node.value, list):
                        declared_tools = tools_node.value
                    break

        if declared_tools is not None:
            # Agent explicitly declared tools — use those
            tools.extend(get_tool_schemas(declared_tools))
        else:
            # No explicit tools declaration — include default useful tools
            default_tools = ["web_search", "web_fetch", "read_file",
                             "write_file", "patch_file", "calculate"]
            tools.extend(get_tool_schemas(default_tools))

        # Always include load_skill for Tier 2 skill disclosure (HLD 3.6.5)
        # Check if it's already included
        tool_names = [t["function"]["name"] for t in tools]
        if "load_skill" not in tool_names:
            tools.extend(get_tool_schemas(["load_skill"]))

        return tools

    def _render_prompt_template(self, template: str) -> str:
        """Render a prompt template by replacing {{var}} with environment values.

        Supports nested attribute access like {{settings.model}}.
        Single-pass rendering: rendered results are not re-rendered.
        """
        import re
        def replace_var(match):
            var_path = match.group(1).strip()
            parts = var_path.split(".")
            try:
                value = self.environment.lookup(parts[0]) if parts else None
            except NameError:
                return match.group(0)  # Keep original if not found
            for part in parts[1:]:
                if isinstance(value, dict):
                    value = value.get(part)
                else:
                    value = None
                    break
            if value is None:
                return match.group(0)  # Keep original if not found
            return str(value)
        return re.sub(r"\{\{(.+?)\}\}", replace_var, template)

    def _get_rendered_agent_prompt(self) -> str | None:
        """Get the current agent's prompt field, rendered with environment variables.

        Returns None if no agent context or no prompt field defined.
        """
        if self._current_agent is None:
            return None
        prompt_def = self._current_agent.prompt
        if prompt_def is None:
            return None
        return self._render_prompt_template(prompt_def.content)

    @staticmethod
    def _load_skill_tool_schema() -> dict[str, Any]:
        """Generate the load_skill tool schema (always included per HLD 3.6.5).

        This tool enables the LLM to autonomously load skill content
        based on the Skill Index injected in System Prompt (Tier 2).
        """
        return {
            "type": "function",
            "function": {
                "name": "load_skill",
                "description": "Load a skill's full content by name",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "description": "Skill name to load"}
                    },
                    "required": ["name"]
                }
            }
        }

    def _get_context(self) -> str | None:
        """Get the current conversation context for LLM calls.

        Integrates with HistoryManager (HLD 3.12) to build a conversation
        summary from accumulated LLM interaction history. The summary is
        capped at 4096 tokens per HLD 3.6.6 conversation_summary rules.

        Returns:
            Formatted summary string: "[{role}] {content}" per message,
            or None if history is empty.
        """
        if not self._history:
            return None
        return self._history_manager.build_conversation_summary(self._history)

    def _add_to_history(self, role: str, content: str) -> None:
        """Add a message to the conversation history.

        Args:
            role: Message role ("user", "assistant", "system", "tool").
            content: Message content string.
        """
        self._history.append(HistoryMessage(role=role, content=content))

    @property
    def history(self) -> list[HistoryMessage]:
        """Access the conversation history (for testing and external integration)."""
        return list(self._history)

    def clear_history(self) -> None:
        """Clear the conversation history."""
        self._history.clear()

    def _error_matches(self, exc: Exception, type_name: str) -> bool:
        """Check if a runtime error matches a catch type name.

        Deprecated: use error_matches() from exceptions module instead.
        Kept for backward compatibility.
        """
        return error_matches(exc, type_name)

    def _runtime_error(self, span: SourceSpan | None, message: str) -> None:
        """Report a runtime error and raise an exception."""
        self.errors.error(ErrorCode.RUNTIME_ERROR, message, span)
        raise RuntimeError(message, span)
