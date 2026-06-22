"""Interpreter for the Helen language.

Walks the AST (as a Visitor[object]) executing deterministic statements:
variable declaration/assignment, control flow (if/for/while), function
definition/call, return/break/continue, const protection, match, and
expression evaluation.
"""

from __future__ import annotations

import os

from helen.core.ast import (
    AccessNode,
    AgentDeclNode,
    AgentParamNode,
    AssertStmtNode,
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
    ForAwaitStmtNode,
    FunctionDeclNode,
    GroupingNode,
    IfStmtNode,
    ImportStmtNode,
    IndexNode,
    LambdaNode,
    ListLiteralNode,
    LiteralNode,
    LiteralTypeNode,
    MainBlockNode,
    MapEntryNode,
    MapLiteralNode,
    MatchStmtNode,
    OptionalTypeNode,
    PipeExprNode,
    ProgramNode,
    PromptDefNode,
    ProtocolDeclNode,
    ImplDeclNode,
    RangePatternNode,
    ReturnStmtNode,
    StatementNode,
    TemplateRefNode,
    ThrowStmtNode,
    TryStmtNode,
    TypeNode,
    TypePatternNode,
    UnaryOpNode,
    UnionTypeNode,
    VarDeclNode,
    VariableNode,
    VariablePatternNode,
    Visitor,
    WhileStmtNode,
    WildcardPatternNode,
)
from helen.core.errors import ErrorCode, ErrorReporter
from helen.core.source import SourceSpan
from helen.core.tokens import TokenType
from helen.interpreter.environment import Environment
from helen.interpreter.exceptions import (
    AggregateError,
    AssertionError as HelenAssertionError,
    BreakSentinel,
    ConstAssignmentError,
    ContinueSentinel,
    HelenRuntimeError,
    ReturnSentinel,
    RuntimeError as HelenRuntimeErrorClass,
    error_matches,
    resolve_exception,
    _PREDEFINED_EXCEPTIONS,
)
from helen.interpreter.task import Task
from helen.interpreter.llm_mixin import LlmMixin
from helen.runtime.llm_runtime import LLMRuntime, MockLLMRuntime
from helen.runtime.import_resolver import ImportResolver, ImportResult
from helen.runtime.history import HistoryManager, Message as HistoryMessage
from helen.runtime.observability import ObservabilityManager
from helen.semantic.types import (
    AnyType,
    Type,
    type_compatible,
    type_of_literal,
)


class Closure:
    """Represents a closure - a lambda function with its captured environment.

    A closure captures the lexical environment where it was defined,
    allowing it to access variables from that environment even when
    called from a different scope.
    """
    def __init__(self, lambda_node: LambdaNode, captured_env: Environment):
        self.lambda_node = lambda_node
        self.captured_env = captured_env

    def __repr__(self):
        return f"<closure with {len(self.lambda_node.params)} params>"


class Interpreter(LlmMixin, Visitor[object]):
    """AST visitor that executes Helen programs.

    Each visit method returns the evaluated value of the node, or a
    control-flow sentinel (BreakSentinel, ContinueSentinel, ReturnSentinel).

    LLM-related methods are inherited from LlmMixin.
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
        # AI-native observability (P0-P3)
        self.observability = ObservabilityManager()
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
        """Inject all stdlib functions into the global environment.
        
        Loads the Helen stdlib module and registers all builtin functions
        (e.g., print, len, type, debug_*) into the global environment.
        Also connects the observability manager to stdlib debug functions.
        
        Called during initialization and after reset_definitions().
        """
        from helen.stdlib import stdlib  # noqa: PLC0415
        from helen.stdlib import _set_interpreter_observability  # noqa: PLC0415
        # Connect observability manager to stdlib debug functions
        _set_interpreter_observability(self.observability)
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
        """Clear all user-defined functions and agents (keep stdlib).
        
        Removes all user-defined functions and agents from the interpreter's
        registries, then re-registers stdlib builtins. Use this to reset
        the interpreter state between REPL evaluations.
        
        Note:
            Does NOT clear the environment (variables persist).
            Use Environment.reset() for full environment reset.
        """
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
        """Look up a variable in the environment.

        Resolution order:
        1. Environment (let/const variables, builtins)
        2. User-defined functions (fn declarations) — returns callable wrapper
        3. User-defined agents (agent declarations) — returns callable wrapper
        """
        try:
            return self.environment.lookup(node.name)
        except NameError:
            # Fallback: check if it's a user-defined function name
            if node.name in self._functions:
                func_node = self._functions[node.name]
                # Return a callable wrapper so functions can be used as first-class values

                def _function_wrapper(*args):
                    return self._call_function(func_node, list(args))
                return _function_wrapper
            # Fallback: check if it's a user-defined agent name
            if node.name in self._agents:
                agent_node = self._agents[node.name]

                def _agent_wrapper(*args):
                    agent_args = {}
                    for i, arg in enumerate(args):
                        if i < len(agent_node.params):
                            agent_args[agent_node.params[i].name] = arg
                    return self._call_agent(agent_node, agent_args)
                return _agent_wrapper
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

        self._runtime_error(node.span, f"Unknown operator '{node.operator.lexeme}'")
        return None

    def visit_pipe_expr(self, node: PipeExprNode) -> object:
        """Evaluate a pipe expression: value |> fn.

        Desugars to: fn(value)
        """
        # Evaluate the left-hand side (the value to pipe)
        value = node.value.accept(self)

        # The right-hand side should be a callable
        func_name = node.function.name if isinstance(node.function, VariableNode) else None

        # Check if it's a registered function
        if func_name is not None and func_name in self._functions:
            func = self._functions[func_name]
            return self._call_function(func, [value])

        # Check if it's a registered agent
        if func_name is not None and func_name in self._agents:
            agent = self._agents[func_name]
            if len(agent.params) > 0:
                agent_args = {agent.params[0].name: value}
            else:
                agent_args = {}
            return self._call_agent(agent, agent_args)

        # Otherwise evaluate as expression and try to call
        func = node.function.accept(self)

        # Closure call
        if isinstance(func, Closure):
            return self._call_closure(func, [value])

        # Python FFI
        from helen.ffi.python_object import WrappedPythonObject
        if isinstance(func, WrappedPythonObject):
            return func.call(value)

        # Stdlib builtin or any other callable
        if callable(func):
            return func(value)

        func_str = func_name if func_name else type(func).__name__
        self._runtime_error(node.span, f"'{func_str}' is not callable")
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

        # Closure call (lambda expression)
        if isinstance(callee, Closure):
            return self._call_closure(callee, args)

        # Check if callee is a Python FFI object
        from helen.ffi.python_object import WrappedPythonObject
        if isinstance(callee, WrappedPythonObject):
            return callee.call(*args)

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
                # v1.6: Check if this is a module object
                if target.get("__type__") == "module":
                    # Look up function or agent in module
                    prop = node.property
                    if prop in target.get("__functions__", {}):
                        func_node = target["__functions__"][prop]
                        # Return a callable wrapper for the function
                        return self._create_module_function_wrapper(func_node, target)
                    elif prop in target.get("__agents__", {}):
                        agent_node = target["__agents__"][prop]
                        # Return a callable wrapper for the agent
                        return self._create_module_agent_wrapper(agent_node, target)
                    elif prop in target.get("__data__", {}):
                        return target["__data__"][prop]
                    else:
                        # Fall back to regular dict access
                        return target[prop]
                else:
                    return target[node.property]
            if hasattr(target, node.property):
                return getattr(target, node.property)
            self._runtime_error(node.span, f"'{type(target).__name__}' has no property '{node.property}'")
            return None
        except KeyError:
            self._runtime_error(node.span, f"Property '{node.property}' not found")
            return None

    def _create_module_function_wrapper(self, func_node, module: dict):
        """Create a callable wrapper for a module function (v1.6)."""
        def wrapper(*args, **kwargs):
            # Call the function with the provided arguments
            return self._call_function(func_node, list(args))
        return wrapper

    def _create_module_agent_wrapper(self, agent_node, module: dict):
        """Create a callable wrapper for a module agent (v1.6)."""
        def wrapper(*args, **kwargs):
            # Convert positional args to dict based on agent params
            args_dict = {}
            for i, param in enumerate(agent_node.params):
                if i < len(args):
                    args_dict[param.name] = args[i]
                elif param.name in kwargs:
                    args_dict[param.name] = kwargs[param.name]
                elif param.default_value is not None:
                    # Evaluate default value
                    args_dict[param.name] = param.default_value.accept(self)
            # Call the agent with the provided arguments
            return self._call_agent(agent_node, args_dict)
        return wrapper

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

    def visit_for_await_stmt(self, node: ForAwaitStmtNode) -> object:
        """Execute a for-await-in loop (async iteration)."""
        import asyncio
        from helen.interpreter.task import Task

        iterable = node.iterable.accept(self)

        # If iterable is a Task, await it first to get the actual async iterable
        if isinstance(iterable, Task):
            if iterable.is_pending:
                iterable.execute()
            iterable = iterable.result()

        # Check if iterable is an async iterable
        if not hasattr(iterable, '__aiter__'):
            self._runtime_error(node.span, f"Cannot async iterate over {type(iterable).__name__}")
            return None

        # Run async iteration using asyncio
        async def _async_iterate():
            result = None
            async for item in iterable:
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

        # Run the async iteration
        try:
            return asyncio.run(_async_iterate())
        except Exception as e:
            self._runtime_error(node.span, f"Error in for-await loop: {e}")
            return None

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

    def visit_lambda(self, node: LambdaNode) -> object:
        """Create a closure from a lambda expression.

        The closure captures the current environment, allowing the lambda
        to access variables from its defining scope.
        """
        return Closure(lambda_node=node, captured_env=self.environment)

    def visit_protocol_decl(self, node: ProtocolDeclNode) -> object:
        """Register a protocol declaration (do not execute).

        v1.7 feature: protocols define interfaces.
        For now, we just register the protocol name.
        """
        # Store protocol for future reference
        if not hasattr(self, '_protocols'):
            self._protocols = {}
        self._protocols[node.name] = node
        return None

    def visit_impl_decl(self, node: ImplDeclNode) -> object:
        """Register protocol method implementations for a struct.

        v1.7 feature: implements protocol methods.
        For now, we register the methods so they can be called on struct instances.
        """
        # Store impl methods - they will be available as methods on struct instances
        if not hasattr(self, '_impls'):
            self._impls = {}

        key = (node.protocol_name, node.struct_name)
        self._impls[key] = node

        # Register each method as a function that can be called
        for method in node.methods:
            # Create a method name that includes the struct name for disambiguation
            # This allows calling struct.method() syntax
            self._functions[method.name] = method

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
        """Execute a match statement with range, wildcard, variable binding, and type pattern support."""
        subject = node.subject.accept(self)
        for case in node.cases:
            pattern_node = case.pattern
            matched = False
            bindings = {}  # Variable bindings for this case

            # Handle different pattern types
            if isinstance(pattern_node, WildcardPatternNode):
                # Wildcard matches anything
                matched = True
            elif isinstance(pattern_node, VariablePatternNode):
                # Variable binding: bind subject to variable name
                matched = True
                bindings[pattern_node.name] = subject
            elif isinstance(pattern_node, TypePatternNode):
                # Type pattern: check if subject is of the specified type
                matched = self._check_type(subject, pattern_node.type_name)
                if matched and pattern_node.binding_name:
                    bindings[pattern_node.binding_name] = subject
            else:
                # Evaluate pattern (for range, literal, etc.)
                pattern = pattern_node.accept(self)
                # Check if pattern is a range pattern
                if isinstance(pattern, tuple) and len(pattern) == 3 and pattern[0] == "__range__":
                    _, start, end = pattern
                    if isinstance(subject, (int, float)) and isinstance(start, (int, float)) and isinstance(end, (int, float)):
                        matched = start <= subject <= end
                else:
                    matched = self._equal(subject, pattern)

            # Check guard condition if present
            if matched and case.guard is not None:
                # Enter scope with bindings before evaluating guard
                old_env = self.environment
                self.environment = self.environment.enter_scope()
                try:
                    # Bind variables for guard evaluation
                    for name, value in bindings.items():
                        self.environment.define(name, value, is_const=False)
                    guard_result = case.guard.accept(self)
                    matched = self._truthy(guard_result)
                finally:
                    self.environment = old_env

            if matched:
                old_env = self.environment
                self.environment = self.environment.enter_scope()
                try:
                    # Bind variables in the case scope
                    for name, value in bindings.items():
                        self.environment.define(name, value, is_const=False)
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

    def _check_type(self, value: object, type_name: str) -> bool:
        """Check if value matches the specified type name."""
        type_map = {
            "Int": int,
            "Float": float,
            "String": str,
            "Bool": bool,
            "List": list,
            "Map": dict,
            "Null": type(None),
        }
        expected_type = type_map.get(type_name)
        if expected_type is None:
            return False
        return isinstance(value, expected_type)

    def visit_case(self, node: CaseNode) -> object:
        # Cases are handled inside visit_match_stmt
        return None

    def visit_range_pattern(self, node: RangePatternNode) -> object:
        """Evaluate a range pattern to a (start, end) tuple."""
        start = node.start.accept(self)
        end = node.end.accept(self)
        return ("__range__", start, end)

    def visit_wildcard_pattern(self, node: WildcardPatternNode) -> object:
        """Visit a WildcardPatternNode. Handled in visit_match_stmt."""
        return None

    def visit_variable_pattern(self, node: VariablePatternNode) -> object:
        """Visit a VariablePatternNode. Handled in visit_match_stmt."""
        return None

    def visit_type_pattern(self, node: TypePatternNode) -> object:
        """Visit a TypePatternNode. Handled in visit_match_stmt."""
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

    def visit_assert_stmt(self, node: AssertStmtNode) -> object:
        """Execute an assert statement: assert condition or assert condition, message.

        AI-native observability (P3): If the condition is false, raises AssertionError
        with structured error context for AI debugging.
        """
        # Evaluate the condition
        condition_value = node.condition.accept(self)

        # Check if condition is truthy
        if not self._truthy(condition_value):
            # Evaluate optional message
            if node.message is not None:
                message = node.message.accept(self)
                if not isinstance(message, str):
                    message = str(message)
            else:
                message = "Assertion failed"

            # Capture structured error context
            self.observability.capture_error(
                "AssertionError", message, node.span,
                scope={}  # Could capture local vars here if needed
            )

            # Raise AssertionError
            raise HelenAssertionError(message, node.span)

        return None

    # ------------------------------------------------------------------
    # Import & LLM
    # ------------------------------------------------------------------

    def visit_import_stmt(self, node: ImportStmtNode) -> object:
        """Execute an import statement (HLD 3.9, 3.6.2).

        Per HLD: import only parses and registers Agent/Function definitions
        from the imported file. It does NOT execute the imported file's main block.

        Supported formats:
        - .helen: Parse and register agents/functions to global namespace
        - .md/.txt: Load as text, register to import_resolver.data
        - .json/.yaml: Parse as data, register to import_resolver.data
        - Python modules (no extension or .py): Import via Python FFI

        v1.6: Module imports support function/agent access via alias
        """
        # Check if this is a Python module import
        # Python modules: no extension, or .py extension, or dotted names like "os.path"
        # Helen/data files: .helen, .json, .md, .txt, .yaml, .yml
        path = node.module_path
        is_python_module = (
            path.endswith('.py') or  # Explicit .py extension
            not any(path.endswith(ext) for ext in ('.helen', '.json', '.md', '.txt', '.yaml', '.yml'))
        )

        if is_python_module:
            # Python module import via FFI
            return self._import_python_module(node)

        # Track the current file for relative path resolution
        current_file = node.source_file if hasattr(node, 'source_file') else None

        result = self.import_resolver.resolve(node.module_path, current_file)
        if result is None:
            # Error already reported by ImportResolver
            return None

        # Register imported content into the interpreter's namespaces
        if result.format == "helen":
            # v1.6: If alias is provided, create a module object for function/agent access
            if node.alias:
                module_obj = self._create_module_object(result)
                self.environment.define(node.alias, module_obj)
            else:
                # No alias: register agents/functions/constants directly to global namespace
                for name, agent in self.import_resolver.agents.items():
                    if name not in self._agents:
                        self._agents[name] = agent
                for name, func in self.import_resolver.functions.items():
                    if name not in self._functions:
                        self._functions[name] = func
                # Register constants by evaluating their initializers
                for name, const_node in self.import_resolver.data.items():
                    # Check if already defined in environment
                    try:
                        self.environment.lookup(name)
                        # Already defined, skip
                    except NameError:
                        # Not defined, evaluate and define it
                        from helen.core.ast import VarDeclNode
                        if isinstance(const_node, VarDeclNode) and const_node.initializer is not None:
                            value = const_node.initializer.accept(self)
                            self.environment.define(name, value)
        else:
            # Register data by user-specified alias (or filename if no alias)
            alias = node.alias if node.alias else os.path.splitext(os.path.basename(result.path))[0]
            # Define the variable in the environment
            self.environment.define(alias, result.content)

        return None

    def _create_module_object(self, result: ImportResult) -> dict:
        """Create a module object containing agents and functions from imported .helen file (v1.6)."""
        module = {
            "__type__": "module",
            "__path__": result.path,
            "__agents__": {},
            "__functions__": {},
            "__data__": {}
        }

        # Collect agents
        for name, agent in self.import_resolver.agents.items():
            module["__agents__"][name] = agent

        # Collect functions
        for name, func in self.import_resolver.functions.items():
            module["__functions__"][name] = func

        # Collect data (constants, etc.)
        for name, data in self.import_resolver.data.items():
            module["__data__"][name] = data

        return module

    def _import_python_module(self, node: ImportStmtNode) -> object:
        """Import a Python module via FFI.

        Args:
            node: The import statement node

        Returns:
            None
        """
        from helen.ffi.python_runtime import DefaultPythonRuntime

        # Get or create Python runtime
        if not hasattr(self, '_python_runtime'):
            self._python_runtime = DefaultPythonRuntime()

        # Import the module
        module_name = node.module_path
        if module_name.endswith('.py'):
            module_name = module_name[:-3]  # Remove .py extension

        try:
            module = self._python_runtime.import_module(module_name)

            # Register the module under the alias (or module name if no alias)
            alias = node.alias if node.alias else module_name.split('.')[-1]
            self.environment.define(alias, module)

        except ImportError as e:
            self._runtime_error(node.span, f"Cannot import Python module '{module_name}': {e}")
            return None

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
        """Convert an AST TypeNode to a semantic Type.

        Delegates to the shared utility in type_utils module.
        """
        from helen.semantic.type_utils import type_from_typenode
        return type_from_typenode(type_node)

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

        # Push call stack frame (AI observability)
        call_args = {}
        for i, param in enumerate(func.params):
            if i < len(args):
                call_args[param.name] = args[i]
        self.observability.call_stack.push(func.name, func.span, call_args)
        self.observability.tracer.trace("call", func.span, {"function": func.name, "args": call_args})

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
                self.observability.tracer.trace("return", func.span, {"function": func.name, "value": result.value})
                return result.value
            self.observability.tracer.trace("return", func.span, {"function": func.name})
            return result
        except Exception as e:
            # Capture error snapshot with call stack
            scope_vars = {}
            for k in call_args.keys():
                try:
                    scope_vars[k] = call_env.lookup(k)
                except NameError:
                    pass
            self.observability.capture_error(
                type(e).__name__, str(e), func.span,
                scope=scope_vars
            )
            raise
        finally:
            self.environment = old_env
            self.observability.call_stack.pop()

    def _call_closure(self, closure: Closure, args: list[object]) -> object:
        """Call a closure (lambda expression) with the given arguments.

        The key difference from _call_function is that we use the captured
        environment (from where the lambda was defined) as the parent scope,
        not the current caller's environment. This enables closures.
        """
        lambda_node = closure.lambda_node

        # Runtime parameter type checking (same as _call_function)
        for i, param in enumerate(lambda_node.params):
            if i < len(args) and param.type_annotation is not None:
                expected_type = self._type_from_typenode(param.type_annotation)
                actual_value = args[i]
                if actual_value is not None:
                    actual_type = type_of_literal(actual_value)
                    if not isinstance(actual_type, AnyType):
                        if not type_compatible(actual_type, expected_type):
                            raise HelenRuntimeError(
                                f"argument {i+1} type '{actual_type.name}' is not compatible with parameter type '{expected_type.name}'"
                            )

        # Create a new scope with the CAPTURED environment as parent
        # This is the key to closures - we use closure.captured_env, not self.environment
        call_env = closure.captured_env.enter_scope()

        # Bind parameters
        for i, param in enumerate(lambda_node.params):
            if i < len(args):
                call_env.define(param.name, args[i])
            elif param.default_value is not None:
                # Evaluate default in caller's environment
                default_val = param.default_value.accept(self)
                call_env.define(param.name, default_val)
            else:
                # Too few arguments — use None
                call_env.define(param.name, None)

        # Execute lambda body in the new environment
        old_env = self.environment
        self.environment = call_env
        try:
            result = self._execute_stmts(lambda_node.body.body)
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
        # Check if agent is streaming mode
        is_streaming = self._is_agent_streaming(agent)

        # Push call stack frame (AI observability)
        self.observability.call_stack.push(agent.name, agent.span, args)
        self.observability.tracer.trace("call", agent.span, {"agent": agent.name, "args": args})

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
            self._functions.get(func_node.name)
            self._functions[func_node.name] = func_node
            registered_names.append(func_node.name)

        # Define variables from functions { } block (let/const declarations)
        for var_node in agent.function_vars:
            value = None
            if var_node.initializer is not None:
                value = var_node.initializer.accept(self)
            is_const = not var_node.mutable
            call_env.define(var_node.name, value, is_const=is_const)

        # Execute the agent's logic (main block)
        old_env = self.environment
        self.environment = call_env
        try:
            if agent.logic is not None:
                result = agent.logic.accept(self)
                if isinstance(result, ReturnSentinel):
                    self.observability.tracer.trace("return", agent.span, {"agent": agent.name, "value": result.value})
                    # If streaming mode, wrap result in StreamingResponse
                    if is_streaming and isinstance(result.value, str):
                        return self._create_streaming_response(result.value)
                    return result.value
                self.observability.tracer.trace("return", agent.span, {"agent": agent.name})
                # If streaming mode, wrap result in StreamingResponse
                if is_streaming and isinstance(result, str):
                    return self._create_streaming_response(result)
                return result
            elif agent.prompt is not None:
                # Agent has no logic but has a prompt - auto-execute LLM call
                rendered_prompt = self._get_rendered_agent_prompt()
                if rendered_prompt:
                    if is_streaming:
                        # Return streaming response
                        return self._call_llm_streaming(rendered_prompt, agent)
                    else:
                        # Return complete response
                        return self.llm_runtime.act(rendered_prompt)
                return None
            return None
        except Exception as e:
            # Capture error snapshot with call stack
            scope_vars = {}
            for k in args.keys():
                try:
                    scope_vars[k] = call_env.lookup(k)
                except NameError:
                    pass
            self.observability.capture_error(
                type(e).__name__, str(e), agent.span,
                scope=scope_vars
            )
            raise
        finally:
            self.environment = old_env
            self._current_agent = old_agent
            self.observability.call_stack.pop()
            # Unregister agent functions to avoid leaking
            for fname in registered_names:
                self._functions.pop(fname, None)

    def _is_agent_streaming(self, agent: AgentDeclNode) -> bool:
        """Check if agent has streaming true declaration."""
        for decl in agent.declarations:
            if decl.streaming:
                return True
        return False

    def _create_streaming_response(self, text: str):
        """Create a StreamingResponse from text for for-await iteration."""
        from helen.runtime.streaming_response import StreamingResponse

        # Create a simple async iterator that yields the text in chunks
        async def _text_iterator():
            # Split text into chunks for streaming effect
            chunk_size = 50
            for i in range(0, len(text), chunk_size):
                yield text[i:i + chunk_size]

        return StreamingResponse(_text_iterator())

    def _call_llm_streaming(self, prompt: str, agent: AgentDeclNode):
        """Call LLM with streaming and return StreamingResponse."""
        from helen.runtime.streaming_response import StreamingResponse

        # Get agent settings
        model = self._get_agent_setting("model")
        temperature = float(self._get_agent_setting("temperature", 1.0))
        system_prompt = self._get_agent_setting("description")

        # Get the stream iterator from LLM runtime
        if hasattr(self.llm_runtime, 'act_stream'):
            stream_iterator = self.llm_runtime.act_stream(
                prompt,
                model=model,
                temperature=temperature,
                system_prompt=system_prompt,
            )
            return StreamingResponse(stream_iterator)
        else:
            # Fallback to non-streaming
            response = self.llm_runtime.act(
                prompt,
                model=model,
                temperature=temperature,
                system_prompt=system_prompt,
            )
            if response and response.text:
                return self._create_streaming_response(response.text)
            return None

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

    def _error_matches(self, exc: Exception, type_name: str) -> bool:
        """Check if a runtime error matches a catch type name.

        Deprecated: use error_matches() from exceptions module instead.
        Kept for backward compatibility.
        """
        return error_matches(exc, type_name)

    def _runtime_error(self, span: SourceSpan | None, message: str) -> None:
        """Report a runtime error and raise an exception."""
        self.errors.error(ErrorCode.RUNTIME_ERROR, message, span)
        raise HelenRuntimeErrorClass(message, span)
