"""Interpreter for the Helen language.

Walks the AST (as a Visitor[object]) executing deterministic statements:
variable declaration/assignment, control flow (if/for/while), function
definition/call, return/break/continue, const protection, match, and
expression evaluation.
"""

from __future__ import annotations

import copy
import threading
from contextlib import contextmanager
from typing import Any, Callable
from helen.core.ast import (
    AccessNode,
    AgentDeclNode,
    AgentParamNode,
    AliasStmtNode,
    BinaryOpNode,
    BreakStmtNode,
    CallArgNode,
    CallNode,
    ContinueStmtNode,
    DeclarationNode,
    ExprStmtNode,
    FnBlockNode,
    ForStmtNode,
    FunctionDeclNode,
    GroupingNode,
    IfStmtNode,
    IndexNode,
    LambdaNode,
    ListLiteralNode,
    LiteralNode,
    LiteralTypeNode,
    MainBlockNode,
    MapEntryNode,
    MapLiteralNode,
    OptionalTypeNode,
    PipeExprNode,
    ProgramNode,
    PromptDefNode,
    ProtocolDeclNode,
    ImplDeclNode,
    ReturnStmtNode,
    StatementNode,
    TemplateRefNode,
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
    AgentError,
    BreakSentinel,
    ConstAssignmentError,
    ContinueSentinel,
    HelenRuntimeError,
    ReturnSentinel,
    RuntimeError as HelenRuntimeErrorClass,
    ScopeViolationError,
)
from helen.interpreter.exception_mixin import ExceptionMixin
from helen.interpreter.import_mixin import ImportMixin
from helen.interpreter.llm_mixin import LlmMixin
from helen.interpreter.pattern_mixin import PatternMixin
from helen.interpreter.streaming_mixin import StreamingMixin, _StreamingHandle
from helen.runtime.llm_runtime import LLMRuntime
from helen.runtime.import_resolver import ImportResolver
from helen.runtime.history import HistoryManager, Message as HistoryMessage
from helen.runtime.observability import ObservabilityManager
from helen.semantic.types import (
    AnyType,
    Type,
    type_compatible,
    type_of_literal,
)


# Stdlib function cache for agent calls - avoids 219+ lookups per call (P1)
_STDLIB_CACHE: dict[str, Callable] | None = None


def _get_stdlib_cache() -> dict[str, Callable]:
    """Lazy-initialize and return the stdlib function cache."""
    global _STDLIB_CACHE
    if _STDLIB_CACHE is None:
        from helen.stdlib import stdlib
        _STDLIB_CACHE = {}
        for name in stdlib.names:
            builtin = stdlib.lookup(name)
            if builtin is not None:
                _STDLIB_CACHE[name] = builtin.fn
    return _STDLIB_CACHE


# ── Extracted classes (re-imported for backward compatibility) ──────
from helen.interpreter.closure import Closure, _compute_free_variables  # noqa: E402
from helen.interpreter.readonly_view import ReadOnlyView  # noqa: E402
from helen.interpreter.shared_store import (  # noqa: E402
    SharedStore,
    SharedStoreMethod,
    _is_mutable_type,
)


class Interpreter(LlmMixin, StreamingMixin, PatternMixin, ExceptionMixin, ImportMixin, Visitor[object]):
    """AST visitor that executes Helen programs.

    Each visit method returns the evaluated value of the node, or a
    control-flow sentinel (BreakSentinel, ContinueSentinel, ReturnSentinel).

    LLM-related methods are inherited from LlmMixin.
    """

    def __init__(self, errors: ErrorReporter | None = None,
                 llm_runtime: LLMRuntime | None = None,
                 import_resolver: ImportResolver | None = None,
                 program_args: list[str] | None = None,
                 transcript_store_enabled: bool = True,
                 session_id: str | None = None,  # v1.24: Resume specific session
                 parent_session_id: str = "") -> None:  # v1.23.7: Track spawn relationships
        self.errors = errors or ErrorReporter()
        self.environment = Environment()
        self._functions: dict[str, FunctionDeclNode] = {}
        self._agents: dict[str, AgentDeclNode] = {}
        # v1.17: Lazy-load HttpLLMRuntime as default instead of MockLLMRuntime.
        # MockLLMRuntime is for deterministic testing only — production code
        # (CLI, REPL, Python Bridge) needs real LLM calls. The runtime is
        # initialized on first access to avoid import overhead for programs
        # that don't use llm act/if/choose.
        self._llm_runtime: LLMRuntime | None = llm_runtime
        self._current_agent: AgentDeclNode | None = None
        self.import_resolver = import_resolver or ImportResolver()
        self._program_args: list[str] = list(program_args) if program_args else []
        self._transcript_store_enabled = transcript_store_enabled
        self._session_id = session_id  # v1.24: Resume specific session
        self._parent_session_id = parent_session_id  # v1.23.7
        # AI-native observability (P0-P3)
        self.observability = ObservabilityManager()
        # Merge imported agents/functions into local registries
        for name, agent in self.import_resolver.agents.items():
            self._agents[name] = agent
        for name, func in self.import_resolver.functions.items():
            self._functions[name] = func
        # Conversation history for LLM context (HLD 3.6.6, 3.12)
        # Initialize HistoryManager with model-aware context window
        # Phase 2 SSOT: Use _interpreter_history as fallback when TranscriptStore disabled
        self._interpreter_history: list[HistoryMessage] = []
        try:
            from helen.runtime.config import load_config
            config = load_config()
            model = config.get("model")
        except Exception:
            model = None
        self._history_manager = HistoryManager(model=model)
        # Phase 7: Initialize AgentContextManager for working memory and compression
        from helen.interpreter.agent_context import AgentContextManager
        self._agent_context = AgentContextManager(
            working_memory_tokens=5000,
            compression_strategy="graduated",
            working_memory_enabled=True,
            cache_aware_enabled=True,
            transcript_store_enabled=self._transcript_store_enabled,
            session_id=self._session_id,  # v1.24: Resume specific session
            parent_session_id=self._parent_session_id,  # v1.23.7
        )
        # v1.22: Invocation tree tracking (see reports/v1.22-invocation-tree-proposal.md)
        # _current_invocation_id: the invocation currently executing (or "" at top-level)
        # _invocation_stack: stack of parent invocation IDs for nested agent calls
        # _invocation_index: in-memory cache of invocation metadata (rebuilt from transcript)
        self._current_invocation_id: str = ""
        self._invocation_stack: list[str] = []
        self._invocation_index: dict[str, dict[str, Any]] = {}
        # P2: Initialize PromptBuilder for unified prompt construction
        from helen.runtime.prompt_builder import PromptBuilder
        self._prompt_builder = PromptBuilder()
        # Configure skill directories for mtime-based caching
        try:
            from helen.runtime.config import get_skill_dirs
            self._prompt_builder.set_skill_dirs([str(d) for d in get_skill_dirs()])
            # Set runtime for skill listing
            from helen.runtime import HelenRuntime
            self._prompt_builder._runtime = HelenRuntime()
        except Exception:
            pass
        self._shared_vars: set[str] = set()
        # Shared store instance cache: ensures that importing the same module
        # multiple times reuses the same SharedStore instance instead of
        # re-creating and re-initializing it on each import pass.
        self._shared_store_instances: dict[str, "SharedStore"] = {}
        # Phase 3: Streaming call registry for cancel/KeyboardInterrupt support
        self._streaming_calls: dict[str, _StreamingHandle] = {}
        self._streaming_lock = threading.Lock()
        # Register stdlib builtins in global environment (HLD M15)
        self._register_stdlib()
        # Set CLI args in the stdlib module (for get_cli_args/parse_cli_args)
        from helen.stdlib.system import _set_cli_args
        _set_cli_args(self._program_args)
        # Define `argv` as a pre-defined const (CLI arguments after the filename)
        self.environment.define("argv", self._program_args, is_const=True)

    @property
    def llm_runtime(self) -> LLMRuntime:
        """Lazy-load HttpLLMRuntime on first access.

        Production code (CLI, REPL, Python Bridge) needs real LLM calls.
        MockLLMRuntime should only be used for deterministic testing.
        Tests pass llm_runtime explicitly; everyone else gets HttpLLMRuntime
        initialized from ~/.helen/config.yaml on first use.
        """
        if self._llm_runtime is None:
            from helen.runtime.http_llm import HttpLLMRuntime
            self._llm_runtime = HttpLLMRuntime()
        return self._llm_runtime

    @llm_runtime.setter
    def llm_runtime(self, value: LLMRuntime | None) -> None:
        """Allow explicit assignment (used by tests with MockLLMRuntime)."""
        self._llm_runtime = value

    @property
    def _history(self) -> list[HistoryMessage]:
        """Phase 2 SSOT: _history is now a read-only derived view.

        When TranscriptStore is enabled, returns transcript_store.read_view()
        which applies all BoundaryMarkers to reconstruct the effective message list.

        When TranscriptStore is disabled, returns _interpreter_history (fallback).

        v1.22: Filtered by current invocation_id. Each agent main {} is an
        invocation; the LLM only sees messages from the current invocation.
        This gives per-agent context isolation. When _current_invocation_id
        is "" (top-level code outside main {}), no filter is applied.

        This property is read-only — all writes go directly to TranscriptStore.
        """
        if self._agent_context is not None and self._agent_context.transcript_store is not None:
            all_messages = self._agent_context.transcript_store.read_view()
        else:
            all_messages = self._interpreter_history

        # v1.22: Filter by current invocation_id for per-agent isolation.
        # Empty _current_invocation_id means no invocation active (top-level
        # code outside main {}) — no filter.
        if not self._current_invocation_id:
            return all_messages

        return [
            m for m in all_messages
            if getattr(m, 'invocation_id', '') == self._current_invocation_id
        ]

    @contextmanager
    def _push_scope(self, set_to: Environment | None = None):
        """Context manager for temporary scope/environment switch.

        Usage:
            with self._push_scope():                # create child scope
            with self._push_scope(module_env):      # switch to specific env
        """
        old_env = self.environment
        self.environment = set_to if set_to is not None else old_env.enter_scope()
        try:
            yield
        finally:
            self.environment = old_env

    def _register_stdlib(self) -> None:
        """Inject all stdlib functions into the global environment.
        
        Loads the Helen stdlib module and registers all builtin functions
        (e.g., print, len, type, debug_*) into the global environment.
        Also connects the observability manager to stdlib debug functions.

        Called during initialization and after reset_definitions().
        """
        from helen.stdlib import stdlib  # noqa: PLC0415
        from helen.stdlib import _set_interpreter_observability  # noqa: PLC0415
        from helen.stdlib import _set_interpreter_context  # noqa: PLC0415
        from helen.stdlib.transcript import _set_transcript_context  # noqa: PLC0415
        from helen.stdlib.llm_control import _set_interpreter_ref  # noqa: PLC0415
        # Connect observability manager to stdlib debug functions
        _set_interpreter_observability(self.observability)
        # Connect history to stdlib context management functions
        # Phase 2 SSOT: Use _interpreter_history as the underlying storage
        _set_interpreter_context(self._interpreter_history, self._history_manager, self._agent_context)
        # Connect agent context to stdlib transcript functions
        _set_transcript_context(self._agent_context)
        # Phase 5: Connect interpreter ref to LLM control stdlib functions
        _set_interpreter_ref(self)
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
                # v1.10: Pass module env for imported functions
                _parent_env = None
                if hasattr(self, '_function_module_envs'):
                    _parent_env = self._function_module_envs.get(node.name)

                def _function_wrapper(*args):
                    return self._call_function(func_node, list(args), parent_env=_parent_env)
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

        # Assignment: handle VariableNode, IndexNode, and AccessNode targets
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
            if isinstance(node.left, IndexNode):
                # arr[i] = value
                target = node.left.target.accept(self)
                index = node.left.index.accept(self)
                try:
                    target[index] = right
                except ScopeViolationError:
                    raise  # v1.12: Don't swallow isolation errors
                except (TypeError, IndexError, KeyError) as e:
                    self._runtime_error(node.span, str(e))
                    return None
                return right
            if isinstance(node.left, AccessNode):
                # obj.field = value
                target = node.left.target.accept(self)
                prop = node.left.property
                # v1.12 fix: ReadOnlyView blocks mutation via attribute access
                if isinstance(target, ReadOnlyView):
                    raise ScopeViolationError(
                        "cannot modify read-only parameter in agent scope. "
                        "Parameters are passed as read-only views to prevent "
                        "accidental modification of caller's data. "
                        "Create a local copy with `let copy = dict(param)` if you need to modify."
                    )
                try:
                    if isinstance(target, dict):
                        target[prop] = right
                    else:
                        setattr(target, prop, right)
                except (TypeError, AttributeError) as e:
                    self._runtime_error(node.span, str(e))
                    return None
                return right
            self._runtime_error(node.span, "Invalid assignment target")
            return None

        # Short-circuit evaluation for AND/OR (evaluate left first, skip right if result is determined)
        if op == TokenType.AND:
            left = node.left.accept(self)
            if not self._truthy(left):
                return False
            right = node.right.accept(self)
            return self._truthy(right)

        if op == TokenType.OR:
            left = node.left.accept(self)
            if self._truthy(left):
                return True
            right = node.right.accept(self)
            return self._truthy(right)

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
            _penv = None
            if hasattr(self, '_function_module_envs'):
                _penv = self._function_module_envs.get(func_name)
            return self._call_function(func, [value], parent_env=_penv)

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

        # Closure / FFI / callable dispatch
        from helen.ffi.python_object import WrappedPythonObject
        match func:
            case Closure():
                return self._call_closure(func, [value])
            case WrappedPythonObject():
                return func.call(value)
            case _ if callable(func):
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
            # v1.10: Pass module env for imported functions so they can
            # access their module's consts and shared let
            parent_env = None
            if hasattr(self, '_function_module_envs'):
                parent_env = self._function_module_envs.get(callee_name)
            return self._call_function(func, args, parent_env=parent_env)

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

        # Function/Closure/FFI/builtin dispatch
        from helen.ffi.python_object import WrappedPythonObject
        match callee:
            case FunctionDeclNode():
                return self._call_function(callee, args)

            case Closure():
                return self._call_closure(callee, args)

            case WrappedPythonObject():
                return callee.call(*args)

            case _ if callable(callee):
                # stdlib builtin function (HLD M15)
                # Wrap Closure arguments as Python callables for stdlib functions
                wrapped_args = []
                for arg in args:
                    match arg:
                        case Closure() as closure_obj:
                            # Create a Python wrapper that calls the closure
                            def wrapper(*py_args, _c=closure_obj):
                                return self._call_closure(_c, list(py_args))
                            wrapped_args.append(wrapper)
                        case _:
                            wrapped_args.append(arg)
                try:
                    return callee(*wrapped_args)
                except HelenRuntimeError:
                    raise  # Already a Helen exception, propagate as-is
                except Exception as e:
                    # Wrap Python exceptions in RuntimeError so try-catch can catch them.
                    # Preserve the original Python exception type in the message
                    # so users can distinguish (e.g., "Python TypeError: ..." vs "Python ValueError: ...").
                    py_type = type(e).__name__
                    raise HelenRuntimeErrorClass(f"Python {py_type}: {e}", node.span) from e

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
            # v1.12: ReadOnlyView supports __getitem__ directly
            if isinstance(target, ReadOnlyView):
                return target[index]
            if isinstance(target, (list, tuple)):
                if isinstance(index, int):
                    return target[index]
                self._runtime_error(node.span, f"List index must be integer, got {type(index).__name__}")
                return None
            if isinstance(target, dict):
                try:
                    return target[index]
                except KeyError:
                    # v1.11: Provide more detailed error message for map key access
                    # Include available keys to help debugging
                    available_keys = list(target.keys())
                    if len(available_keys) > 10:
                        keys_str = str(available_keys[:10])[:-1] + ", ...]"
                    else:
                        keys_str = str(available_keys)
                    self._runtime_error(
                        node.span,
                        f"Map key {index!r} not found. Available keys: {keys_str}"
                    )
                    return None
            self._runtime_error(node.span, f"Type {type(target).__name__} does not support indexing")
            return None
        except (IndexError, TypeError) as e:
            self._runtime_error(node.span, str(e))
            return None

    def visit_access(self, node: AccessNode) -> object:
        """Evaluate member access: target.property."""
        target = node.target.accept(self)
        try:
            # v1.12 fix: ReadOnlyView wrapping a dict — delegate to __getitem__
            if isinstance(target, ReadOnlyView):
                prop = node.property
                data = target._data
                if isinstance(data, dict):
                    if prop in data:
                        value = data[prop]
                        if isinstance(value, (list, dict)):
                            return ReadOnlyView(value)
                        return value
                    # Fall through to method access (keys, values, items, get)
                # Check for ReadOnlyView's own methods
                if hasattr(target, prop):
                    return getattr(target, prop)
                self._runtime_error(node.span, f"'{type(data).__name__}' has no property '{prop}'")
                return None
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
                        data_val = target["__data__"][prop]
                        # v1.10: Evaluate VarDeclNode (const/shared let) on access
                        from helen.core.ast import VarDeclNode as _VDN
                        if isinstance(data_val, _VDN) and data_val.initializer is not None:
                            evaluated = data_val.initializer.accept(self)
                            target["__data__"][prop] = evaluated  # cache for future access
                            return evaluated
                        # SharedStoreDeclNode: return the runtime SharedStore
                        # instance from the module's environment (where it was
                        # created by _create_module_object), not the raw AST node.
                        from helen.core.ast import SharedStoreDeclNode as _SSDN
                        if isinstance(data_val, _SSDN):
                            module_env = target.get("__env__")
                            if module_env is not None:
                                try:
                                    store = module_env.lookup(prop)
                                    target["__data__"][prop] = store  # cache
                                    return store
                                except NameError:
                                    pass
                            # Fallback: check interpreter's shared store cache
                            cached = self._shared_store_instances.get(prop)
                            if cached is not None:
                                target["__data__"][prop] = cached
                                return cached
                        return data_val
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
        """Create a callable wrapper for a module function (v1.6).

        v1.10: The wrapper passes the module's environment as parent scope,
        so module functions can access their own module's consts and shared let.
        """
        module_env = module.get("__env__")

        def wrapper(*args, **kwargs):
            return self._call_function(func_node, list(args), parent_env=module_env)
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
        is_const = not node.mutable

        # v1.18: Recursive closure support.
        # When a let/const is initialized with a lambda, pre-define the
        # variable so the lambda body can reference its own name
        # (e.g. ``let factorial = fn(n) { ... factorial(n-1) ... }``).
        # After evaluation, the closure's _self_name is set so that
        # _call_closure injects the real closure into the call environment.
        is_lambda_init = isinstance(node.initializer, LambdaNode)
        if is_lambda_init:
            self.environment.define(node.name, None)

        if node.initializer is not None:
            value = node.initializer.accept(self)

        if is_lambda_init and isinstance(value, Closure):
            value._self_name = node.name

        self.environment.define(node.name, value, is_const=is_const)
        # v1.10: Track shared variables for cross-agent visibility
        if node.shared:
            self._shared_vars.add(node.name)
        return value

    def _visit_shared_container(self, node: object, node_cls: type) -> object:
        """Execute a shared store or channel declaration.

        v1.12/v1.13: Both create a SharedStore instance at runtime.

        Uses _shared_store_instances cache to ensure that re-importing a module
        reuses the existing SharedStore instance instead of creating a new one
        with freshly-initialized fields.
        """
        if not isinstance(node, node_cls):
            return None

        # Return cached instance if already created (e.g. from a prior import).
        # This prevents re-initialization when multiple modules import the same
        # shared store module — the first import creates it, subsequent imports
        # reuse the same instance with its current field values.
        cached = self._shared_store_instances.get(node.name)
        if cached is not None:
            self.environment.define(node.name, cached, is_const=True)
            self._shared_vars.add(node.name)
            return cached

        fields: dict[str, object] = {}
        for field_node in node.fields:
            value = None
            if field_node.initializer is not None:
                value = field_node.initializer.accept(self)
            fields[field_node.name] = value

        container = SharedStore(node.name, fields, {})
        for method_node in node.methods:
            container._methods[method_node.name] = SharedStoreMethod(method_node, container, self)

        self._shared_store_instances[node.name] = container
        self.environment.define(node.name, container, is_const=True)
        self._shared_vars.add(node.name)
        return container

    def visit_shared_store_decl(self, node: object) -> object:
        """Execute a shared store declaration."""
        from helen.core.ast import SharedStoreDeclNode  # noqa: PLC0415
        return self._visit_shared_container(node, SharedStoreDeclNode)

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
        # v1.12: ReadOnlyView is iterable (yields wrapped items)
        if not isinstance(iterable, (list, tuple, ReadOnlyView)):
            self._runtime_error(node.span, f"Cannot iterate over {type(iterable).__name__}")
            return None

        result = None
        for item in iterable:
            # Create a new scope for each iteration? No -- Helen uses
            # block scope: one scope for the entire loop body.
            # We'll use a fresh scope per loop to match semantic analysis.
            with self._push_scope():
                if node.iterator is not None:
                    self.environment.define(node.iterator.name, item)
                step = self._execute(node.body)
                if isinstance(step, BreakSentinel):
                    return result  # absorb sentinel, return last normal value
                if isinstance(step, ContinueSentinel):
                    continue
                if isinstance(step, ReturnSentinel):
                    return step
                result = step

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

    def visit_lambda(self, node: LambdaNode) -> object:
        """Create a closure from a lambda expression.

        v1.12: Closure value capture. Instead of capturing the entire environment
        by reference (which can cause agent environment leaks), we capture only
        the values of free variables used by the lambda. This provides:
        - Isolation: closures don't hold references to agent environments
        - Memory efficiency: only captured values are retained, not entire scopes
        - Predictability: captured values are snapshots, immune to later mutations
          (reference types like list/dict are deep-copied for true value semantics)
        """
        # Compute free variables used in the lambda body
        free_vars = _compute_free_variables(node)

        # Create a snapshot environment with only the captured values
        captured_env = Environment()
        for var_name in free_vars:
            try:
                value = self.environment.lookup(var_name)
                # v1.12 fix: Deep copy reference types for true value semantics.
                # Without this, the closure captures a reference to the mutable,
                # and later mutations are visible inside the closure — contradicting
                # the "snapshot" promise.
                if _is_mutable_type(value):
                    value = copy.deepcopy(value)
                # Note: SharedStore instances are NOT deep-copied — they are
                # designed for controlled cross-agent sharing. Closures that
                # capture a SharedStore retain access to its public interface
                # (methods), which is thread-safe by design. This is intentional:
                # @sandbox restricts LLM tools, not shared-state access.
                captured_env.define(var_name, value)
            except NameError:
                # Variable not found in current scope — skip
                # (will be caught at call time if actually used)
                pass

        return Closure(lambda_node=node, captured_env=captured_env)

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

    def visit_context_config(self, node) -> object:
        """Phase 7: Context configuration is processed during agent execution."""
        return None

    # ------------------------------------------------------------------
    # Program & blocks
    # ------------------------------------------------------------------

    def visit_program(self, node: ProgramNode) -> object:
        return self._execute_stmts(node.statements)

    def visit_main_block(self, node: MainBlockNode) -> object:
        """Execute a main block.

        v1.22: Top-level main (when _current_agent is None) is an invocation.
        Agent main blocks are invocations created by _call_agent; we skip
        creating a nested invocation here.
        """
        if self._current_agent is None:
            # Top-level main: create an invocation
            self._enter_invocation(None)
            try:
                with self._push_scope():
                    return self._execute_stmts(node.body)
            finally:
                self._exit_invocation()
        else:
            # Agent main: _call_agent handles invocation entry/exit
            with self._push_scope():
                return self._execute_stmts(node.body)

    def visit_alias_stmt(self, node: AliasStmtNode) -> object:
        """Execute alias statement: alias <canonical> as <alias_name>.

        Looks up the canonical name in the environment, functions registry,
        agents registry, or stdlib. Then defines the alias name pointing
        to the same callable/value. Supports stdlib functions, user-defined
        functions, agents, and variables.
        """
        canonical = node.canonical
        alias_name = node.alias_name

        # Priority order for lookup:
        # 1. Environment (variables, closures, stdlib-in-env)
        # 2. User-defined functions
        # 3. User-defined agents
        # 4. Stdlib builtin (fallback for names not in env)
        value = None
        found = False

        # Try environment first
        try:
            value = self.environment.lookup(canonical)
            found = True
        except NameError:
            pass

        # Try user-defined functions
        if not found and canonical in self._functions:
            # Create a closure-like callable wrapper for the function
            func_node = self._functions[canonical]

            def _make_alias_callable(fn_node):
                def alias_callable(*args, **kwargs):
                    return self._call_function(fn_node, list(args))
                return alias_callable

            value = _make_alias_callable(func_node)
            found = True

        # Try user-defined agents
        if not found and canonical in self._agents:
            agent_node = self._agents[canonical]

            def _make_alias_agent_callable(ag_node):
                def alias_callable(*args, **kwargs):
                    # Convert args to dict format for agent call
                    arg_names = [p.name for p in ag_node.params]
                    arg_dict = dict(zip(arg_names, args))
                    return self._call_agent(ag_node, arg_dict)
                return alias_callable

            value = _make_alias_agent_callable(agent_node)
            found = True

        # Fall back to stdlib
        if not found:
            from helen.stdlib import stdlib
            builtin = stdlib.lookup(canonical)
            if builtin is not None:
                value = builtin.fn
                found = True

        if not found:
            self._runtime_error(
                node.span,
                f"Cannot alias '{canonical}': name not found"
            )
            return None

        # Define the alias in the current environment
        self.environment.define(alias_name, value)

        # Also register in the functions/agents registry if applicable
        # so the alias can be called like a normal function/agent
        if canonical in self._functions:
            self._functions[alias_name] = self._functions[canonical]
        if canonical in self._agents:
            self._agents[alias_name] = self._agents[canonical]

        # Also register in stdlib alias map for introspection
        from helen.stdlib import stdlib
        stdlib.register_alias(alias_name, canonical)

        return None

    def visit_spawn_expr(self, node: object) -> object:
        """Execute spawn expression: spawn an agent and return a Channel endpoint.

        Creates a bidirectional Channel, spawns the agent in a daemon thread
        with an isolated environment snapshot, and returns the main-thread
        ChannelEndpoint for communication.

        The agent's last parameter must be typed as Channel — spawn
        auto-injects the spawned-side endpoint.

        Example: mailbox = spawn Worker("task")
        """
        import threading
        from helen.core.ast import SpawnExprNode
        from helen.runtime.channel import Channel, ChannelEndpoint

        if not isinstance(node, SpawnExprNode):
            return None

        call_node = node.call

        # Resolve the agent being called
        if not hasattr(call_node.callee, 'name'):
            self.errors.error(
                ErrorCode.RUNTIME_ERROR,
                "spawn requires an agent call",
                node.span,
            )
            return None

        agent_name = call_node.callee.name
        agent_decl = self._agents.get(agent_name)
        if agent_decl is None:
            self.errors.error(
                ErrorCode.RUNTIME_ERROR,
                f"Undefined agent '{agent_name}' in spawn",
                node.span,
            )
            return None

        # Evaluate the user-provided arguments (exclude the Channel parameter)
        # The agent expects N params; the last one is Channel (auto-injected)
        arg_values = []
        for arg in call_node.arguments:
            val = arg.accept(self)
            arg_values.append(val)

        # Create the bidirectional Channel
        channel = Channel(name=f"spawn_{agent_name}")
        main_endpoint = ChannelEndpoint(channel, is_main_thread=True)
        spawned_endpoint = ChannelEndpoint(channel, is_main_thread=False)

        # Append spawned endpoint as the last argument (auto-inject)
        arg_values.append(spawned_endpoint)

        # Snapshot environment for isolation (all deep-copied)
        env_snapshot = self.environment.snapshot()

        # Capture references for the thread
        errors = self.errors
        llm_runtime = self.llm_runtime
        import_resolver = self.import_resolver
        program_args = self._program_args
        transcript_enabled = self._transcript_store_enabled
        # v1.23.7: Pass parent session_id for spawn tracking
        parent_session_id = self._agent_context.session_id or ""

        def run_spawned():
            try:
                spawned_interp = Interpreter(
                    errors=errors,
                    llm_runtime=llm_runtime,
                    import_resolver=import_resolver,
                    program_args=program_args,
                    transcript_store_enabled=transcript_enabled,
                    parent_session_id=parent_session_id,  # v1.23.7
                )
                spawned_interp.environment = env_snapshot
                # Copy agent/function registries from parent
                spawned_interp._agents = dict(self._agents)
                spawned_interp._functions = dict(self._functions)

                # Phase 6: Inject Channel cancel_event so spawned interpreter's
                # streaming path can check it and abort on endpoint.cancel()
                spawned_interp._agent_cancel_event = spawned_endpoint.cancel_event

                # Construct a new CallNode with evaluated args
                from helen.core.ast import CallNode as CN, CallArgNode, VariableNode, LiteralNode
                new_args = []
                for val in arg_values:
                    lit = LiteralNode(value=val, span=node.span)
                    new_args.append(CallArgNode(name=None, value=lit))
                new_call = CN(
                    callee=VariableNode(name=agent_name, span=node.span),
                    arguments=new_args,
                    span=node.span,
                )
                new_call.accept(spawned_interp)
            except Exception as e:
                try:
                    spawned_endpoint.send({"__error__": True, "message": str(e)})
                except Exception:
                    pass
            finally:
                spawned_endpoint.close()

        thread = threading.Thread(target=run_spawned, daemon=True,
                                  name=f"spawn-{agent_name}")
        thread.start()

        return main_endpoint

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
        # v1.12: ReadOnlyView delegates truthiness to underlying data
        if isinstance(value, ReadOnlyView):
            return len(value._data) > 0
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
        """Addition with string concatenation and list concatenation support."""
        if isinstance(left, str) or isinstance(right, str):
            return str(left) + str(right)
        if isinstance(left, (int, float)) and isinstance(right, (int, float)):
            return left + right
        # v1.12: Unwrap ReadOnlyView for list concatenation
        l_data = left._data if isinstance(left, ReadOnlyView) else left
        r_data = right._data if isinstance(right, ReadOnlyView) else right
        if isinstance(l_data, list) and isinstance(r_data, list):
            result = l_data + r_data
            # If either operand was read-only, result should be too
            if isinstance(left, ReadOnlyView) or isinstance(right, ReadOnlyView):
                return ReadOnlyView(result)
            return result
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
        # v1.12: Unwrap ReadOnlyView for stringification
        if isinstance(value, ReadOnlyView):
            return Interpreter._stringify(value._data)
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

    def _call_function(self, func: FunctionDeclNode, args: list[object], parent_env: Environment | None = None) -> object:
        """Call a function with the given arguments.

        Creates a new environment scope, binds parameters, and executes
        the function body.

        Args:
            func: The function declaration node.
            args: The positional arguments.
            parent_env: Optional parent environment for the call scope.
                If None, uses the current environment. Module functions
                pass their module's environment here so they can access
                module-local consts and shared let.
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

        # v1.10: Use provided parent_env (for module functions) or current env
        if parent_env is not None:
            call_env = Environment(parent=parent_env)
        else:
            call_env = self.environment.enter_scope()

        # Bind parameters
        # v1.10: For module functions, evaluate defaults in the module env
        default_eval_env = parent_env if parent_env is not None else self.environment
        for i, param in enumerate(func.params):
            if i < len(args):
                call_env.define(param.name, args[i])
            elif param.default_value is not None:
                # Evaluate default in the appropriate environment
                old_env_for_default = self.environment
                self.environment = default_eval_env
                try:
                    default_val = param.default_value.accept(self)
                finally:
                    self.environment = old_env_for_default
                call_env.define(param.name, default_val)
            else:
                # Too few arguments — use None
                call_env.define(param.name, None)

        # Execute function body in the new environment
        with self._push_scope(call_env):
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

        # v1.18: Recursive closure support.
        # When a closure was assigned as ``let f = fn(...){...f(...)}``,
        # inject the closure itself into the call environment so the body
        # can call itself by name (overrides the _PLACEHOLDER captured value).
        if closure._self_name is not None:
            call_env.define(closure._self_name, closure)

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
        with self._push_scope(call_env):
            result = self._execute_stmts(lambda_node.body.body)
            if isinstance(result, ReturnSentinel):
                return result.value
            return result

    # ------------------------------------------------------------------
    # v1.22: Invocation tree management
    # ------------------------------------------------------------------
    # See reports/v1.22-invocation-tree-proposal.md for the full design.
    #
    # An "invocation" is one execution of an agent's main {} block (or the
    # top-level main block). Each invocation has:
    #   - invocation_id: a UUID unique to this execution
    #   - agent_name: the agent that produced it (None for top-level)
    #   - parent_invocation_id: the invocation that called it ("" at top-level)
    #
    # Active context (what LLM sees) is isolated per-invocation:
    #   - On entry:  save caller's history; start with empty history
    #   - On exit:   restore caller's history (agent's history is discarded
    #                from active context, but preserved in transcript SSOT)
    # ------------------------------------------------------------------

    def _enter_invocation(self, agent_name: str | None) -> str:
        """Enter a new invocation. Returns the new invocation_id.

        Args:
            agent_name: Name of the agent (None for top-level main).

        Saves caller's invocation_id on the stack, allocates a fresh
        invocation_id, and records metadata in _invocation_index.
        """
        import time
        import uuid as _uuid

        parent_id = self._current_invocation_id
        new_id = f"inv_{int(time.time())}_{_uuid.uuid4().hex[:8]}"

        # Push current onto stack
        self._invocation_stack.append(self._current_invocation_id)
        self._current_invocation_id = new_id

        # Record metadata (used by list_invocations / get_invocation_tree)
        self._invocation_index[new_id] = {
            "invocation_id": new_id,
            "agent_name": agent_name,
            "parent_invocation_id": parent_id,
            "start_time": time.time(),
            "end_time": None,
            "children": [],
            "message_count": 0,
        }
        if parent_id and parent_id in self._invocation_index:
            self._invocation_index[parent_id]["children"].append(new_id)

        return new_id

    def _exit_invocation(self) -> None:
        """Exit the current invocation, restoring the caller's invocation_id.

        Records end_time and final message_count. Does NOT touch active
        context — that's _call_agent's responsibility.
        """
        import time

        inv_id = self._current_invocation_id
        if inv_id and inv_id in self._invocation_index:
            entry = self._invocation_index[inv_id]
            entry["end_time"] = time.time()
            # Count messages belonging to this invocation in transcript
            store = getattr(self._agent_context, "transcript_store", None)
            if store is not None:
                from helen.runtime.transcript_store import Message as _TranscriptMessage
                entry["message_count"] = sum(
                    1 for item in store.transcript
                    if isinstance(item, _TranscriptMessage)
                    and item.invocation_id == inv_id
                )

        # Pop stack
        if self._invocation_stack:
            self._current_invocation_id = self._invocation_stack.pop()
        else:
            self._current_invocation_id = ""

    def _call_agent(self, agent: AgentDeclNode, args: dict[str, object]) -> object:
        """Call an agent with the given arguments (HLD 3.5.2, 3.6.2).

        Per HLD 3.5.2: Sub-agents get a completely isolated Environment.
        They do NOT inherit parent agent's variables. The only parameter
        passing channel is explicit call Agent(param=value) arguments.

        v1.12: Isolation levels affect the agent's behavior:
        - "open" (L0): Module-level let is visible (for debugging)
        - "standard" (L1): Default isolation (const + shared let visible)
        - "strict" (L2): Standard + deep copy parameters and return values
        - "sandbox" (L3): Strict + no I/O tools, limited capabilities

        Args:
            agent: The AgentDeclNode to execute.
            args: Keyword arguments from the call statement.
        """
        # v1.12: Determine isolation level
        isolation_level = getattr(agent, 'isolation_level', 'standard')

        # Check if agent is streaming mode
        is_streaming = self._is_agent_streaming(agent)

        # v1.22: Enter a new invocation for this agent call.
        # The invocation_id will be attached to all messages this agent produces
        # (via _add_to_history in llm_mixin.py). The _history property filters
        # by invocation_id, so the agent's LLM calls see ONLY this invocation's
        # messages — achieving per-agent context isolation.
        inv_id = self._enter_invocation(agent.name)

        # Push call stack frame (AI observability)
        self.observability.call_stack.push(agent.name, agent.span, args)
        self.observability.tracer.trace("call", agent.span, {"agent": agent.name, "args": args, "isolation": isolation_level, "invocation_id": inv_id})

        # Create a completely isolated environment (HLD 3.5.2)
        # Start from a fresh root, not inheriting parent agent's variables.
        # But stdlib must still be available — inject it into the fresh env.
        call_env = Environment()
        # Use pre-cached stdlib functions for performance (P1 optimization)
        stdlib_cache = _get_stdlib_cache()
        for _name, _fn in stdlib_cache.items():
            call_env.define(_name, _fn)

        # v1.12: L0 (open) isolation — inject module-level let for debugging
        if isolation_level == "open":
            current_env = self.environment
            while current_env is not None:
                for _name, _value in current_env._store.items():
                    if not current_env.is_const(_name):
                        # This is a module-level let, inject it
                        try:
                            call_env.lookup(_name)
                        except NameError:
                            call_env.define(_name, _value, is_const=False)
                current_env = current_env.parent

        # v1.10: Inject module-level consts as read-only shared state.
        # const values are immutable by definition, so sharing them across
        # agent boundaries is safe — no state corruption risk.
        # Also inject shared let variables (explicitly declared cross-agent).
        # v1.11: Walk the entire scope chain to find all consts, not just
        # the current scope. This fixes the issue where imported consts
        # (defined in parent scopes) were not visible in agent functions{}.
        current_env = self.environment
        while current_env is not None:
            for _name, _value in current_env._store.items():
                if current_env.is_const(_name):
                    # Only define if not already defined (inner scope takes precedence)
                    try:
                        call_env.lookup(_name)
                    except NameError:
                        call_env.define(_name, _value, is_const=True)
            current_env = current_env.parent
        # Shared let variables are tracked in a module-level registry
        # v1.12: Deep copy shared let values to prevent accidental sharing
        # of mutable objects. Note: shared let is now restricted to value types
        # (int, float, str, bool), so deep copy is mostly a no-op for these
        # immutable types. This is for safety and future-proofing.
        for _name in getattr(self, '_shared_vars', set()):
            try:
                _value = self.environment.lookup(_name)
                # Deep copy for mutable types (shouldn't happen with value type restriction)
                if _is_mutable_type(_value):
                    _value = copy.deepcopy(_value)
                call_env.define(_name, _value, is_const=False)
            except NameError:
                pass

        # v1.12: Switch to agent environment BEFORE evaluating defaults
        # and function_vars initializers. This ensures isolation — defaults
        # and initializers are evaluated in the agent's isolated env, not
        # the caller's env. Module-level `let` variables are not visible.
        old_env = self.environment
        self.environment = call_env

        # Bind parameters from agent's param declarations
        # v1.12: Wrap mutable reference types (list, dict) in ReadOnlyView
        # to prevent agent from modifying caller's data.
        # L2 (strict): Deep copy parameters instead of read-only wrapper
        for param in agent.params:
            if param.name in args:
                value = args[param.name]
                if isolation_level == "strict" or isolation_level == "sandbox":
                    # L2/L3: Deep copy mutable types
                    if _is_mutable_type(value):
                        value = copy.deepcopy(value)
                else:
                    # L1: Read-only wrapper
                    if _is_mutable_type(value):
                        value = ReadOnlyView(value)
                call_env.define(param.name, value)
            elif param.default_value is not None:
                # v1.12: Evaluate default in agent's isolated environment.
                # If the default references a module-level let, it will
                # raise NameError at runtime — this is correct behavior.
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
        # v1.12: Initializers are evaluated in agent's isolated environment.
        # Variables can reference earlier function_vars (sequential evaluation).
        for var_node in agent.function_vars:
            value = None
            if var_node.initializer is not None:
                value = var_node.initializer.accept(self)
            is_const = not var_node.mutable
            call_env.define(var_node.name, value, is_const=is_const)

        # Execute the agent's logic (main block)
        # Note: self.environment is already set to call_env above
        try:
            if agent.logic is not None:
                result = agent.logic.accept(self)
                if isinstance(result, ReturnSentinel):
                    # v1.12: Deep copy return value for L2/L3 to prevent reference escape
                    return_value = result.value
                    if (isolation_level == "strict" or isolation_level == "sandbox") and _is_mutable_type(return_value):
                        return_value = copy.deepcopy(return_value)
                    self.observability.tracer.trace("return", agent.span, {"agent": agent.name, "value": return_value})
                    # If streaming mode, wrap result in StreamingResponse
                    if is_streaming and isinstance(return_value, str):
                        return self._create_streaming_response(return_value)
                    return return_value
                self.observability.tracer.trace("return", agent.span, {"agent": agent.name})
                # v1.12: Deep copy return value for L2/L3 to prevent reference escape
                if (isolation_level == "strict" or isolation_level == "sandbox") and _is_mutable_type(result):
                    result = copy.deepcopy(result)
                # If streaming mode, wrap result in StreamingResponse
                if is_streaming and isinstance(result, str):
                    return self._create_streaming_response(result)
                return result
            elif agent.prompt is not None:
                # Agent has no logic but has a prompt - auto-execute LLM call
                rendered_prompt = self._get_rendered_agent_prompt()
                if rendered_prompt:
                    # v1.12 fix: @sandbox agents get NO tools, even in auto-execution
                    sandbox_tools = [] if isolation_level == "sandbox" else None
                    if is_streaming:
                        # Return streaming response
                        return self._call_llm_streaming(rendered_prompt, agent)
                    else:
                        # Return complete response
                        return self.llm_runtime.act(rendered_prompt, tools=sandbox_tools)
                return None
            return None
        except AgentError:
            # Already wrapped (e.g. from a nested agent call) — re-raise as-is.
            # Still capture observability for the outer call frame.
            scope_vars = {}
            for k in args.keys():
                try:
                    scope_vars[k] = call_env.lookup(k)
                except NameError:
                    pass
            self.observability.capture_error(
                "AgentError", f"Agent '{agent.name}' propagated failure", agent.span,
                scope=scope_vars,
            )
            raise
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
            # Wrap as AgentError with agent context for try-catch handling
            raise AgentError(
                agent_name=agent.name,
                agent_args=dict(args),
                cause=e,
            ) from e
        finally:
            # v1.22: Exit the invocation. This records end_time and message_count,
            # and pops the invocation stack to restore the caller's invocation_id.
            # The _history property then filters by caller's invocation_id, so
            # the caller's subsequent LLM calls see only its own messages (not the
            # agent's). The agent's messages remain in transcript SSOT for audit.
            self._exit_invocation()

            # Write back shared let modifications from agent to caller (v1.11 fix).
            # Agent's call_env has its own copies of shared let values; any
            # mutations must be propagated back to the caller's scope chain
            # so that subsequent reads see the updated values.
            # v1.12: Deep copy values on writeback for safety (same rationale as injection).
            for _name in getattr(self, '_shared_vars', set()):
                if _name in call_env._store:
                    # Skip const variables (e.g., shared stores are const references)
                    if old_env.is_const(_name):
                        continue
                    _value = call_env._store[_name]
                    if _is_mutable_type(_value):
                        _value = copy.deepcopy(_value)
                    try:
                        old_env.assign(_name, _value)
                    except NameError:
                        pass
            # v1.12: For @open agents, also write back module-level let modifications.
            # @open agents have read/write access to module-level let for debugging;
            # without writeback, modifications are lost when the agent returns.
            if isolation_level == "open":
                for _name, _value in call_env._store.items():
                    if _name in getattr(self, '_shared_vars', set()):
                        continue  # already handled above
                    # Skip consts, stdlib, agent params, function_vars
                    if call_env.is_const(_name):
                        continue
                    # Only write back if the variable exists in the caller's scope chain
                    try:
                        old_env.lookup(_name)
                        # Variable exists in caller — write back
                        if _is_mutable_type(_value):
                            _value = copy.deepcopy(_value)
                        old_env.assign(_name, _value)
                    except NameError:
                        pass  # Not a caller variable (stdlib, agent-local, etc.)
            self.environment = old_env
            self._current_agent = old_agent
            self.observability.call_stack.pop()
            # Unregister agent functions to avoid leaking
            for fname in registered_names:
                self._functions.pop(fname, None)

    def _is_agent_streaming(self, agent: AgentDeclNode) -> bool:
        """Check if agent has streaming true declaration."""
        # Use pre-computed attribute for O(1) lookup (P2 optimization)
        return agent.has_streaming

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

    def _runtime_error(self, span: SourceSpan | None, message: str) -> None:
        """Report a runtime error and raise an exception.

        v1.11: Don't report to error collector. Runtime errors propagate
        via exception and are caught by try-catch. If uncaught, CLI handles it.
        """
        raise HelenRuntimeErrorClass(message, span)
