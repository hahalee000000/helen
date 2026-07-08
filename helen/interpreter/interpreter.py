"""Interpreter for the Helen language.

Walks the AST (as a Visitor[object]) executing deterministic statements:
variable declaration/assignment, control flow (if/for/while), function
definition/call, return/break/continue, const protection, match, and
expression evaluation.
"""

from __future__ import annotations

import os
import asyncio
import concurrent.futures
import copy
import types
from contextlib import contextmanager
from typing import Callable, Mapping
from helen.core.ast import (
    AccessNode,
    AgentDeclNode,
    AgentParamNode,
    AliasStmtNode,
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
    DetachStmtNode,
    ExprStmtNode,
    ExpressionNode,
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
    MatchExprNode,
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
    AgentError,
    AssertionError as HelenAssertionError,
    BreakSentinel,
    ConstAssignmentError,
    ContinueSentinel,
    HelenRuntimeError,
    ReturnSentinel,
    RuntimeError as HelenRuntimeErrorClass,
    ScopeViolationError,
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

# Module-level constants for performance optimization (P1)
# Type name mapping for _check_type - avoids creating dict on every match
_TYPE_NAME_MAP: dict[str, type] = {
    "Int": int,
    "Float": float,
    "String": str,
    "Bool": bool,
    "List": list,
    "Map": dict,
    "Null": type(None),
}

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


class ReadOnlyView:
    """Read-only wrapper for mutable types (list, dict) passed to agents.

    v1.12: Agent isolation improvement. When a reference type (list, dict)
    is passed as a parameter to an agent, it is wrapped in a ReadOnlyView
    to prevent the agent from modifying the caller's data.

    The wrapper supports read operations (iteration, indexing, len) but
    raises ScopeViolationError on mutation attempts.

    Security notes:
    - __iter__ wraps each yielded item in ReadOnlyView to prevent escape
      through iteration (e.g. `for item in param { item.append(1) }`)
    - unwrap is renamed to _unwrap and is inaccessible from Helen code
      (__getattr__ blocks _-prefixed names)
    """
    def __init__(self, data):
        object.__setattr__(self, '_data', data)

    def __getitem__(self, key):
        value = self._data[key]
        # Wrap nested mutable types (list, dict) as well
        # Also wrap tuples that may contain mutable items
        if isinstance(value, (list, dict)):
            return ReadOnlyView(value)
        if isinstance(value, tuple) and any(isinstance(v, (list, dict)) for v in value):
            return ReadOnlyView(value)
        return value

    def __len__(self):
        return len(self._data)

    def __iter__(self):
        """Iterate with each item wrapped in ReadOnlyView if mutable."""
        for item in self._data:
            if isinstance(item, (list, dict)):
                yield ReadOnlyView(item)
            elif isinstance(item, tuple) and any(isinstance(v, (list, dict)) for v in item):
                yield ReadOnlyView(item)
            else:
                yield item

    def __contains__(self, item):
        return item in self._data

    def __bool__(self):
        return bool(self._data)

    def __str__(self):
        return str(self._data)

    def __repr__(self):
        return f"ReadOnly({self._data!r})"

    def __eq__(self, other):
        if isinstance(other, ReadOnlyView):
            return self._data == other._data
        return self._data == other

    def __ne__(self, other):
        return not self.__eq__(other)

    def __lt__(self, other):
        other_data = other._data if isinstance(other, ReadOnlyView) else other
        return self._data < other_data

    def __le__(self, other):
        other_data = other._data if isinstance(other, ReadOnlyView) else other
        return self._data <= other_data

    def __gt__(self, other):
        other_data = other._data if isinstance(other, ReadOnlyView) else other
        return self._data > other_data

    def __ge__(self, other):
        other_data = other._data if isinstance(other, ReadOnlyView) else other
        return self._data >= other_data

    def __add__(self, other):
        other_data = other._data if isinstance(other, ReadOnlyView) else other
        result = self._data + other_data
        if isinstance(result, (list, dict)):
            return ReadOnlyView(result)
        return result

    def __radd__(self, other):
        """Support [1, 2] + ReadOnlyView([3, 4])."""
        other_data = other._data if isinstance(other, ReadOnlyView) else other
        result = other_data + self._data
        if isinstance(result, (list, dict)):
            return ReadOnlyView(result)
        return result

    def __hash__(self):
        return hash(self._data) if not isinstance(self._data, (list, dict)) else id(self)

    def keys(self):
        """Dict-like keys() method."""
        if hasattr(self._data, 'keys'):
            return self._data.keys()
        raise AttributeError("ReadOnly list has no keys() method")

    def values(self):
        """Dict-like values() method — returns ReadOnlyView for mutable values."""
        if hasattr(self._data, 'values'):
            return [ReadOnlyView(v) if isinstance(v, (list, dict)) else v
                    for v in self._data.values()]
        raise AttributeError("ReadOnly list has no values() method")

    def items(self):
        """Dict-like items() method — values wrapped in ReadOnlyView if mutable."""
        if hasattr(self._data, 'items'):
            result = []
            for k, v in self._data.items():
                if isinstance(v, (list, dict)):
                    result.append((k, ReadOnlyView(v)))
                else:
                    result.append((k, v))
            return result
        raise AttributeError("ReadOnly list has no items() method")

    def get(self, key, default=None):
        """Dict-like get() method."""
        if hasattr(self._data, 'get'):
            value = self._data.get(key, default)
            if isinstance(value, (list, dict)):
                return ReadOnlyView(value)
            return value
        raise AttributeError("ReadOnly list has no get() method")

    def _mutate_error(self, *args, **kwargs):
        """Raise error for any mutation attempt."""
        from helen.interpreter.exceptions import ScopeViolationError
        raise ScopeViolationError(
            "cannot modify read-only parameter in agent scope. "
            "Parameters are passed as read-only views to prevent "
            "accidental modification of caller's data. "
            "Create a local copy with `let copy = list(param)` if you need to modify."
        )

    # Block all mutation methods
    __setitem__ = _mutate_error
    __delitem__ = _mutate_error
    append = _mutate_error
    extend = _mutate_error
    insert = _mutate_error
    remove = _mutate_error
    pop = _mutate_error
    clear = _mutate_error
    sort = _mutate_error
    reverse = _mutate_error
    update = _mutate_error
    setdefault = _mutate_error
    popitem = _mutate_error


class SharedStore:
    """Shared store instance for controlled shared mutable state.

    v1.12: Provides a structured way to share mutable state across agents.
    Fields are private, methods provide the public interface.

    Thread safety: All field access is protected by a reentrant lock (RLock).
    This allows concurrent agents to safely read/write shared state.

    Security: Internal attributes (_name, _fields, _methods, _lock) cannot be
    accessed or modified from Helen code — __getattr__/__setattr__ block
    underscore-prefixed names.

    Example:
        shared store Counter {
            count: int = 0
            fn increment() { count += 1 }
            fn get(): int { return count }
        }
    """
    # Internal attribute names — set in __init__ via object.__setattr__
    _INTERNAL_ATTRS = frozenset({'_name', '_fields', '_methods', '_lock'})

    def __init__(self, name: str, fields: dict[str, object], methods: dict[str, object]):
        """Initialize a shared store.

        Args:
            name: The store's name.
            fields: Initial field values (private state).
            methods: Method implementations (callable closures).
        """
        import threading
        object.__setattr__(self, '_name', name)
        object.__setattr__(self, '_fields', dict(fields))  # defensive copy
        object.__setattr__(self, '_methods', dict(methods))  # defensive copy
        object.__setattr__(self, '_lock', threading.RLock())

    def __getattr__(self, name: str) -> object:
        """Access a field or method by name. Private attrs (_prefix) are blocked."""
        if name.startswith('_'):
            raise AttributeError(f"Cannot access private attribute '{name}'")
        fields = object.__getattribute__(self, '_fields')
        methods = object.__getattribute__(self, '_methods')
        store_name = object.__getattribute__(self, '_name')
        if name in methods:
            return methods[name]
        if name in fields:
            return fields[name]
        raise AttributeError(f"Shared store '{store_name}' has no field or method '{name}'")

    def __setattr__(self, name: str, value: object) -> None:
        """Set a field value. Only public fields can be modified, not methods or internals."""
        # Block ALL underscore-prefixed names — including after __init__
        if name.startswith('_'):
            store_name = object.__getattribute__(self, '_name')
            raise AttributeError(
                f"Cannot set private attribute '{name}' on shared store '{store_name}'. "
                f"Internal attributes are not accessible from Helen code."
            )
        methods = object.__getattribute__(self, '_methods')
        fields = object.__getattribute__(self, '_fields')
        store_name = object.__getattribute__(self, '_name')
        if name in methods:
            raise AttributeError(f"Cannot overwrite method '{name}' in shared store '{store_name}'")
        if name in fields:
            lock = object.__getattribute__(self, '_lock')
            with lock:
                fields[name] = value
            return
        raise AttributeError(f"Shared store '{store_name}' has no field '{name}'")

    def __repr__(self) -> str:
        name = object.__getattribute__(self, '_name')
        fields = object.__getattribute__(self, '_fields')
        methods = object.__getattribute__(self, '_methods')
        return f"<SharedStore {name} with {len(fields)} fields, {len(methods)} methods>"

    def get_field(self, name: str) -> object:
        """Get a field value (thread-safe)."""
        fields = object.__getattribute__(self, '_fields')
        store_name = object.__getattribute__(self, '_name')
        if name not in fields:
            raise AttributeError(f"Shared store '{store_name}' has no field '{name}'")
        lock = object.__getattribute__(self, '_lock')
        with lock:
            return fields[name]

    def set_field(self, name: str, value: object) -> None:
        """Set a field value (thread-safe)."""
        fields = object.__getattribute__(self, '_fields')
        store_name = object.__getattribute__(self, '_name')
        if name not in fields:
            raise AttributeError(f"Shared store '{store_name}' has no field '{name}'")
        lock = object.__getattribute__(self, '_lock')
        with lock:
            fields[name] = value


class SharedStoreMethod:
    """A callable wrapper for a shared store method.

    When accessed via store.method, returns this callable.
    When called, executes the method with access to the store's fields.

    v1.12 fix: Method execution is serialized via the store's lock to prevent
    concurrent field corruption.
    """
    def __init__(self, method_node, store: SharedStore, interpreter):
        object.__setattr__(self, '_method_node', method_node)
        object.__setattr__(self, '_store', store)
        object.__setattr__(self, '_interpreter', interpreter)

    def __call__(self, *args):
        """Call the method with the given arguments (serialized via store lock)."""
        interp = self._interpreter
        m_node = object.__getattribute__(self, '_method_node')
        store_inst = object.__getattribute__(self, '_store')
        lock = object.__getattribute__(store_inst, '_lock')
        fields = object.__getattribute__(store_inst, '_fields')

        # Serialize method execution to prevent concurrent field corruption
        with lock:
            # Create execution environment with store fields as variables
            old_env = interp.environment
            method_env = old_env.enter_scope()
            # Bind store fields as local variables
            for fname, fvalue in fields.items():
                method_env.define(fname, fvalue)
            # Bind method parameters
            for i, param in enumerate(m_node.params):
                if i < len(args):
                    method_env.define(param.name, args[i])
            interp.environment = method_env
            try:
                result = interp._execute_stmts(m_node.body.body)
                # Write back any field modifications
                for fname in fields:
                    try:
                        fields[fname] = method_env.lookup(fname)
                    except NameError:
                        pass
                if isinstance(result, ReturnSentinel):
                    return result.value
                return result
            finally:
                interp.environment = old_env


def _is_mutable_type(value: object) -> bool:
    """Check if a value is a mutable reference type."""
    return isinstance(value, (list, dict))


def _compute_free_variables(lambda_node: LambdaNode) -> set[str]:
    """Compute the free variables used in a lambda body.

    Free variables are variables that are:
    - Used in the lambda body
    - NOT bound by the lambda's own parameters
    - NOT defined locally within the lambda body

    This is used for closure value capture (v1.12) — we only capture
    the values of variables that are actually needed by the closure.

    Args:
        lambda_node: The lambda AST node to analyze.

    Returns:
        Set of variable names that are free (need to be captured).
    """
    # Variables bound by lambda parameters
    bound_vars = {p.name for p in lambda_node.params}

    # Collect all variable references in the body
    used_vars: set[str] = set()
    _collect_variable_refs(lambda_node.body, bound_vars, used_vars)

    # Free variables = used - bound
    return used_vars - bound_vars


def _collect_variable_refs(node: object, bound: set[str], used: set[str]) -> None:
    """Recursively collect variable references from an AST node.

    Args:
        node: The AST node to traverse.
        bound: Variables that are bound (params, local lets) — these don't count as free.
        used: Accumulator for variable names that are referenced.
    """
    if node is None:
        return

    # Import here to avoid circular imports at module load
    from helen.core.ast import (
        VariableNode, BinaryOpNode, UnaryOpNode, CallNode, CallArgNode,
        IfStmtNode, ForStmtNode, WhileStmtNode, ReturnStmtNode, ExprStmtNode,
        VarDeclNode, FnBlockNode, MatchStmtNode, LambdaNode, IndexNode,
        AccessNode, GroupingNode, PipeExprNode, ListLiteralNode, MapLiteralNode,
        TemplateRefNode, AssertStmtNode, AsyncCallExprNode,
        AsyncCallStmtNode, ForAwaitStmtNode, TryStmtNode,
        CatchClauseNode, FinallyBlockNode, CaseNode,
        LlmActExprNode,
        MatchExprNode,
    )

    # Skip if already a primitive or None
    if not hasattr(node, '__dict__') and not isinstance(node, (list, tuple)):
        return

    if isinstance(node, VariableNode):
        if node.name not in bound:
            used.add(node.name)
        return

    if isinstance(node, (list, tuple)):
        for item in node:
            _collect_variable_refs(item, bound, used)
        return

    # Handle specific node types
    if isinstance(node, VarDeclNode):
        # Variable declaration: the variable being declared is now bound
        if node.initializer is not None:
            _collect_variable_refs(node.initializer, bound, used)
        # After this declaration, the variable is bound for subsequent code
        # (handled by caller adding to bound set)
        return

    if isinstance(node, FnBlockNode):
        # Function body: traverse statements
        for stmt in node.body:
            _collect_variable_refs(stmt, bound, used)
        return

    if isinstance(node, BinaryOpNode):
        _collect_variable_refs(node.left, bound, used)
        _collect_variable_refs(node.right, bound, used)
        return

    if isinstance(node, UnaryOpNode):
        _collect_variable_refs(node.operand, bound, used)
        return

    if isinstance(node, CallNode):
        _collect_variable_refs(node.callee, bound, used)
        for arg in node.arguments:
            _collect_variable_refs(arg, bound, used)
        return

    if isinstance(node, CallArgNode):
        _collect_variable_refs(node.value, bound, used)
        return

    if isinstance(node, IfStmtNode):
        _collect_variable_refs(node.condition, bound, used)
        _collect_variable_refs(node.then_branch, bound, used)
        if node.else_branch is not None:
            _collect_variable_refs(node.else_branch, bound, used)
        return

    if isinstance(node, ForStmtNode):
        # For loop: iterator variable is bound in body
        _collect_variable_refs(node.iterable, bound, used)
        body_bound = bound | {node.variable}
        _collect_variable_refs(node.body, body_bound, used)
        return

    if isinstance(node, ForAwaitStmtNode):
        _collect_variable_refs(node.iterable, bound, used)
        body_bound = bound | {node.variable}
        _collect_variable_refs(node.body, body_bound, used)
        return

    if isinstance(node, WhileStmtNode):
        _collect_variable_refs(node.condition, bound, used)
        _collect_variable_refs(node.body, bound, used)
        return

    if isinstance(node, ReturnStmtNode):
        if node.value is not None:
            _collect_variable_refs(node.value, bound, used)
        return

    if isinstance(node, ExprStmtNode):
        _collect_variable_refs(node.expression, bound, used)
        return

    if isinstance(node, MatchStmtNode):
        _collect_variable_refs(node.subject, bound, used)
        for case in node.cases:
            _collect_variable_refs(case, bound, used)
        if node.default is not None:
            _collect_variable_refs(node.default, bound, used)
        return

    if isinstance(node, CaseNode):
        # Case pattern may bind variables
        case_bound = bound.copy()
        _collect_pattern_bindings(node.pattern, case_bound)
        _collect_variable_refs(node.body, case_bound, used)
        if node.guard is not None:
            _collect_variable_refs(node.guard, case_bound, used)
        return

    if isinstance(node, LambdaNode):
        # Nested lambda: its parameters are bound in its body
        inner_bound = bound | {p.name for p in node.params}
        _collect_variable_refs(node.body, inner_bound, used)
        return

    if isinstance(node, IndexNode):
        _collect_variable_refs(node.target, bound, used)
        _collect_variable_refs(node.index, bound, used)
        return

    if isinstance(node, AccessNode):
        _collect_variable_refs(node.target, bound, used)
        return

    if isinstance(node, GroupingNode):
        _collect_variable_refs(node.expression, bound, used)
        return

    if isinstance(node, PipeExprNode):
        _collect_variable_refs(node.value, bound, used)
        _collect_variable_refs(node.function, bound, used)
        return

    if isinstance(node, ListLiteralNode):
        for elem in node.elements:
            _collect_variable_refs(elem, bound, used)
        return

    if isinstance(node, MapLiteralNode):
        for entry in node.entries:
            _collect_variable_refs(entry, bound, used)
        return

    if hasattr(node, 'key') and hasattr(node, 'value'):
        # MapEntryNode or similar
        _collect_variable_refs(node.key, bound, used)
        _collect_variable_refs(node.value, bound, used)
        return

    if isinstance(node, TemplateRefNode):
        for part in node.parts:
            _collect_variable_refs(part, bound, used)
        return

    if isinstance(node, AssertStmtNode):
        _collect_variable_refs(node.condition, bound, used)
        if node.message is not None:
            _collect_variable_refs(node.message, bound, used)
        return

    if isinstance(node, (AsyncCallExprNode, AsyncCallStmtNode)):
        _collect_variable_refs(node.call, bound, used)
        return

    if isinstance(node, TryStmtNode):
        _collect_variable_refs(node.body, bound, used)
        for catch in node.catches:
            _collect_variable_refs(catch, bound, used)
        if node.finally_block is not None:
            _collect_variable_refs(node.finally_block, bound, used)
        return

    if isinstance(node, CatchClauseNode):
        catch_bound = bound.copy()
        if node.variable:
            catch_bound.add(node.variable)
        _collect_variable_refs(node.body, catch_bound, used)
        return

    if isinstance(node, FinallyBlockNode):
        _collect_variable_refs(node.body, bound, used)
        return

    if isinstance(node, LlmActExprNode):
        # LLM act node: traverse prompt and callback expressions
        if hasattr(node, 'prompt'):
            _collect_variable_refs(node.prompt, bound, used)
        if hasattr(node, 'on_chunk'):
            _collect_variable_refs(node.on_chunk, bound, used)
        if hasattr(node, 'on_complete'):
            _collect_variable_refs(node.on_complete, bound, used)
        if hasattr(node, 'options'):
            _collect_variable_refs(node.options, bound, used)
        if hasattr(node, 'tools'):
            _collect_variable_refs(node.tools, bound, used)
        return

    if isinstance(node, MatchExprNode):
        _collect_variable_refs(node.subject, bound, used)
        for case in node.cases:
            _collect_variable_refs(case, bound, used)
        return

    # For any other node type, try to traverse its attributes
    if hasattr(node, '__dict__'):
        for attr_name, attr_value in vars(node).items():
            if attr_name.startswith('_'):
                continue
            if attr_name in ('span',):
                continue
            _collect_variable_refs(attr_value, bound, used)


def _collect_pattern_bindings(pattern: object, bound: set[str]) -> None:
    """Collect variable names bound by a match pattern.

    Args:
        pattern: The pattern AST node.
        bound: Set to add bound variable names to.
    """
    from helen.core.ast import VariablePatternNode, WildcardPatternNode
    if isinstance(pattern, VariablePatternNode):
        bound.add(pattern.name)
    # WildcardPatternNode doesn't bind anything
    # Other patterns (literal, range) don't bind variables either


class Interpreter(LlmMixin, Visitor[object]):
    """AST visitor that executes Helen programs.

    Each visit method returns the evaluated value of the node, or a
    control-flow sentinel (BreakSentinel, ContinueSentinel, ReturnSentinel).

    LLM-related methods are inherited from LlmMixin.
    """

    def __init__(self, errors: ErrorReporter | None = None,
                 llm_runtime: LLMRuntime | None = None,
                 import_resolver: ImportResolver | None = None,
                 program_args: list[str] | None = None,
                 transcript_store_enabled: bool = True) -> None:
        self.errors = errors or ErrorReporter()
        self.environment = Environment()
        self._functions: dict[str, FunctionDeclNode] = {}
        self._agents: dict[str, AgentDeclNode] = {}
        self.llm_runtime = llm_runtime or MockLLMRuntime()
        self._current_agent: AgentDeclNode | None = None
        self.import_resolver = import_resolver or ImportResolver()
        self._program_args: list[str] = list(program_args) if program_args else []
        self._transcript_store_enabled = transcript_store_enabled
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
        )
        # P2: Initialize PromptBuilder for unified prompt construction
        from helen.runtime.prompt_builder import PromptBuilder
        self._prompt_builder = PromptBuilder()
        # Configure skill directories for mtime-based caching
        try:
            from helen.runtime.config import get_skill_dirs
            self._prompt_builder.set_skill_dirs([str(d) for d in get_skill_dirs()])
            # Set runtime for skill listing
            from helen.runtime import HelenHermesRuntime
            self._prompt_builder._runtime = HelenHermesRuntime()
        except Exception:
            pass
        self._shared_vars: set[str] = set()
        # Register stdlib builtins in global environment (HLD M15)
        self._register_stdlib()
        # Set CLI args in the stdlib module (for get_cli_args/parse_cli_args)
        from helen.stdlib.system import _set_cli_args
        _set_cli_args(self._program_args)
        # Define `argv` as a pre-defined const (CLI arguments after the filename)
        self.environment.define("argv", self._program_args, is_const=True)

    @property
    def _history(self) -> list[HistoryMessage]:
        """Phase 2 SSOT: _history is now a read-only derived view.

        When TranscriptStore is enabled, returns transcript_store.read_view()
        which applies all BoundaryMarkers to reconstruct the effective message list.

        When TranscriptStore is disabled, returns _interpreter_history (fallback).

        This property is read-only — all writes go directly to TranscriptStore.
        """
        if self._agent_context is not None and self._agent_context.transcript_store is not None:
            return self._agent_context.transcript_store.read_view()
        else:
            return self._interpreter_history

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
        # Connect observability manager to stdlib debug functions
        _set_interpreter_observability(self.observability)
        # Connect history to stdlib context management functions
        # Phase 2 SSOT: Use _interpreter_history as the underlying storage
        _set_interpreter_context(self._interpreter_history, self._history_manager, self._agent_context)
        # Connect agent context to stdlib transcript functions
        _set_transcript_context(self._agent_context)
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
        if node.initializer is not None:
            value = node.initializer.accept(self)
        is_const = not node.mutable
        self.environment.define(node.name, value, is_const=is_const)
        # v1.10: Track shared variables for cross-agent visibility
        if node.shared:
            self._shared_vars.add(node.name)
        return value

    def _visit_shared_container(self, node: object, node_cls: type) -> object:
        """Execute a shared store or channel declaration.

        v1.12/v1.13: Both create a SharedStore instance at runtime.
        """
        if not isinstance(node, node_cls):
            return None

        fields: dict[str, object] = {}
        for field_node in node.fields:
            value = None
            if field_node.initializer is not None:
                value = field_node.initializer.accept(self)
            fields[field_node.name] = value

        container = SharedStore(node.name, fields, {})
        for method_node in node.methods:
            container._methods[method_node.name] = SharedStoreMethod(method_node, container, self)

        self.environment.define(node.name, container, is_const=True)
        self._shared_vars.add(node.name)
        return container

    def visit_shared_store_decl(self, node: object) -> object:
        """Execute a shared store declaration."""
        from helen.core.ast import SharedStoreDeclNode  # noqa: PLC0415
        return self._visit_shared_container(node, SharedStoreDeclNode)

    def visit_channel_decl(self, node: object) -> object:
        """Execute a channel declaration."""
        from helen.core.ast import ChannelDeclNode  # noqa: PLC0415
        return self._visit_shared_container(node, ChannelDeclNode)

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
                result = self._execute(node.body)
                if isinstance(result, BreakSentinel):
                    break
                if isinstance(result, ContinueSentinel):
                    continue
                if isinstance(result, ReturnSentinel):
                    return result

        return result

    def visit_for_await_stmt(self, node: ForAwaitStmtNode) -> object:
        """Execute a for-await-in loop (async iteration)."""
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
                with self._push_scope():
                    if node.iterator is not None:
                        self.environment.define(node.iterator.name, item)
                    result = self._execute(node.body)
                    if isinstance(result, BreakSentinel):
                        break
                    if isinstance(result, ContinueSentinel):
                        continue
                    if isinstance(result, ReturnSentinel):
                        return result
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
        """Execute a main block."""
        with self._push_scope():
            return self._execute_stmts(node.body)

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
            match pattern_node:
                case WildcardPatternNode():
                    # Wildcard matches anything
                    matched = True
                case VariablePatternNode():
                    # Variable binding: bind subject to variable name
                    matched = True
                    bindings[pattern_node.name] = subject
                case TypePatternNode():
                    # Type pattern: check if subject is of the specified type
                    matched = self._check_type(subject, pattern_node.type_name)
                    if matched and pattern_node.binding_name:
                        bindings[pattern_node.binding_name] = subject
                case _:
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
                with self._push_scope():
                    # Bind variables for guard evaluation
                    for name, value in bindings.items():
                        self.environment.define(name, value, is_const=False)
                    guard_result = case.guard.accept(self)
                    matched = self._truthy(guard_result)

            if matched:
                with self._push_scope():
                    # Bind variables in the case scope
                    for name, value in bindings.items():
                        self.environment.define(name, value, is_const=False)
                    return self._execute_stmts(case.body)
        # Default branch
        if node.default:
            with self._push_scope():
                return self._execute_stmts(node.default)
        return None

    def visit_match_expr(self, node: MatchExprNode) -> object:
        """Evaluate a match expression — returns the value of the matched branch.

        Each case body is a single expression (wrapped in ExprStmtNode).
        The result of that expression becomes the match result.
        """
        subject = node.subject.accept(self)
        for case in node.cases:
            pattern_node = case.pattern
            matched = False
            bindings = {}

            match pattern_node:
                case WildcardPatternNode():
                    matched = True
                case VariablePatternNode():
                    matched = True
                    bindings[pattern_node.name] = subject
                case TypePatternNode():
                    matched = self._check_type(subject, pattern_node.type_name)
                    if matched and pattern_node.binding_name:
                        bindings[pattern_node.binding_name] = subject
                case _:
                    pattern = pattern_node.accept(self)
                    if isinstance(pattern, tuple) and len(pattern) == 3 and pattern[0] == "__range__":
                        _, start, end = pattern
                        if isinstance(subject, (int, float)) and isinstance(start, (int, float)) and isinstance(end, (int, float)):
                            matched = start <= subject <= end
                    else:
                        matched = self._equal(subject, pattern)

            if matched and case.guard is not None:
                with self._push_scope():
                    for name, value in bindings.items():
                        self.environment.define(name, value, is_const=False)
                    guard_result = case.guard.accept(self)
                    matched = self._truthy(guard_result)

            if matched:
                with self._push_scope():
                    for name, value in bindings.items():
                        self.environment.define(name, value, is_const=False)
                    # Body is a single ExprStmtNode — evaluate its expression
                    body_stmt = case.body[0]
                    if isinstance(body_stmt, ExprStmtNode):
                        return body_stmt.expression.accept(self)
                    return self._execute_stmts(case.body)

        # Default branch
        if node.default_body is not None:
            return node.default_body.accept(self)
        return None

    def _check_type(self, value: object, type_name: str) -> bool:
        """Check if value matches the specified type name."""
        expected_type = _TYPE_NAME_MAP.get(type_name)
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
            with self._push_scope():
                result = self._execute_stmts(node.body)
        except HelenRuntimeError as exc:
            caught = True
            exc_to_rethrow = exc

            # Match typed catches in order (HLD 3.6.4 inheritance support)
            for clause in node.catch_clauses:
                error_type_name = clause.error_type.name
                if error_matches(exc, error_type_name):
                    with self._push_scope():
                        self.environment.define(clause.error_name, exc)
                        catch_result = self._execute_stmts(clause.body)
                        if isinstance(catch_result, ReturnSentinel):
                            result = catch_result.value
                            caught = False
                            return result
                        result = catch_result
                    caught = False
                    break

            # Try catch-all if no typed catch matched
            if caught and node.catch_all is not None:
                with self._push_scope():
                    catch_result = self._execute_stmts(node.catch_all.body)
                    if isinstance(catch_result, ReturnSentinel):
                        result = catch_result.value
                        caught = False
                        return result
                    result = catch_result
                caught = False

        finally:
            # Finally block always executes (HLD 3.6.4)
            if node.finally_block is not None:
                with self._push_scope():
                    self._execute_stmts(node.finally_block.body)

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
        from helen.core import is_helen_data_file  # noqa: PLC0415

        if not is_helen_data_file(node.module_path):
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
                # v1.10: Also register shared let for aliased imports.
                # Pass the module env so initializers can reference consts
                # from the imported module (fixes Issue #10b regression).
                self._register_imported_shared_vars(module_obj.get("__env__"))
            else:
                # No alias: register agents/functions/constants directly to global namespace
                # v1.10: Create a module env for imported functions so they can
                # access their own module's consts and shared let.
                from helen.core.ast import VarDeclNode as _VDN
                module_env = Environment(parent=self.environment)
                for name, data in self.import_resolver.data.items():
                    if isinstance(data, _VDN) and (not data.mutable or data.shared):
                        if data.initializer is not None:
                            with self._push_scope(module_env):
                                value = data.initializer.accept(self)
                        else:
                            value = None
                        module_env.define(name, value, is_const=not data.mutable)

                for name, agent in self.import_resolver.agents.items():
                    if name not in self._agents:
                        self._agents[name] = agent
                for name, func in self.import_resolver.functions.items():
                    if name not in self._functions:
                        self._functions[name] = func
                        # v1.10: Track module env for this function
                        if not hasattr(self, '_function_module_envs'):
                            self._function_module_envs: dict[str, Environment] = {}
                        self._function_module_envs[name] = module_env
                # Register constants and shared let by evaluating their initializers
                # Pass module_env so initializers can reference other consts in the same module
                self._register_imported_consts_and_shared(module_env)
        else:
            # Register data by user-specified alias (or filename if no alias)
            alias = node.alias if node.alias else os.path.splitext(os.path.basename(result.path))[0]
            # Define the variable in the environment
            self.environment.define(alias, result.content)

        return None

    def _register_imported_shared_vars(self, module_env: Environment | None = None) -> None:
        """Evaluate shared let variables from imported modules and define them.

        v1.10: Imported shared let must be available in the importing
        interpreter's environment so the imported module's functions
        can access them through the scope chain.

        Called for BOTH aliased and non-aliased .helen imports.

        Args:
            module_env: The module-level environment where consts and shared
                       let have already been evaluated (by _create_module_object
                       or the non-aliased import path). If provided, use it to
                       look up already-evaluated values so shared let
                       initializers can reference consts from the same module.
        """
        from helen.core.ast import VarDeclNode  # noqa: PLC0415
        for name, var_node in self.import_resolver.data.items():
            if not isinstance(var_node, VarDeclNode):
                continue
            if not var_node.shared:
                continue
            # Only define if not already in environment
            try:
                self.environment.lookup(name)
            except NameError:
                value = None
                resolved = False
                # Prefer the already-evaluated value in module_env
                # (_create_module_object evaluated all consts/shared let there)
                if module_env is not None:
                    try:
                        value = module_env.lookup(name)
                        resolved = True
                    except NameError:
                        pass
                if not resolved and var_node.initializer is not None:
                    # Fall back to evaluating the initializer. Use module_env
                    # as context so const references from the same module resolve.
                    if module_env is not None:
                        with self._push_scope(module_env):
                            value = var_node.initializer.accept(self)
                    else:
                        value = var_node.initializer.accept(self)
                    resolved = True
                if not resolved:
                    value = None
                self.environment.define(name, value)
                self._shared_vars.add(name)

    def _register_imported_consts_and_shared(self, module_env: Environment | None = None) -> None:
        """Evaluate const and shared let from imported modules into the environment.

        Used by the non-aliased import path to register all constants and
        shared variables into the global namespace.

        Args:
            module_env: The module-level environment where consts are already defined.
                       If provided, use it for evaluating initializers so that
                       shared let can reference consts from the same module.
        """
        from helen.core.ast import VarDeclNode  # noqa: PLC0415
        for name, const_node in self.import_resolver.data.items():
            try:
                self.environment.lookup(name)
                # Already defined, skip
            except NameError:
                if isinstance(const_node, VarDeclNode) and const_node.initializer is not None:
                    # If module_env is provided and contains the value, use it
                    if module_env is not None:
                        try:
                            value = module_env.lookup(name)
                        except NameError:
                            # Not in module_env yet, evaluate initializer in module_env
                            with self._push_scope(module_env):
                                value = const_node.initializer.accept(self)
                    else:
                        value = const_node.initializer.accept(self)
                    self.environment.define(name, value, is_const=not const_node.mutable)
                    if const_node.shared:
                        self._shared_vars.add(name)

    def _create_module_object(self, result: ImportResult) -> dict:
        """Create a module object containing agents and functions from imported .helen file (v1.6).

        v1.10: Also creates a module-level Environment that captures the module's
        consts and shared let. This env is used as the parent scope when calling
        module functions, so they can access their own module's variables.

        v1.16: Also registers module functions as callable wrappers in module_env,
        so cross-function calls within the same aliased module resolve correctly.
        """
        from helen.core.ast import VarDeclNode  # noqa: PLC0415
        module = {
            "__type__": "module",
            "__path__": result.path,
            "__agents__": {},
            "__functions__": {},
            "__data__": {}
        }

        # v1.10: Create module-level environment for function scope resolution.
        # Parent is the current (caller's) environment so stdlib is accessible.
        module_env = Environment(parent=self.environment)
        for name, data in self.import_resolver.data.items():
            if isinstance(data, VarDeclNode) and (not data.mutable or data.shared):
                # Evaluate const and shared let initializers in the module env
                if data.initializer is not None:
                    # Temporarily use module_env for evaluation so const refs resolve
                    with self._push_scope(module_env):
                        value = data.initializer.accept(self)
                else:
                    value = None
                module_env.define(name, value, is_const=not data.mutable)
        module["__env__"] = module_env

        # v1.16: Register module functions in module_env as callable wrappers,
        # so cross-function calls within the same aliased module resolve correctly.
        # Without this, `fn quadruple()` calling `fn double()` inside an aliased
        # import fails because `double` is not in module_env.
        for name, func in self.import_resolver.functions.items():
            wrapper = self._create_module_function_wrapper(func, module)
            module_env.define(name, wrapper)

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

    def visit_detach_stmt(self, node: DetachStmtNode) -> object:
        """Execute detach statement: fire-and-forget background execution (Issue #29).

        Starts the agent call in a background thread without waiting for completion.
        No Task object is returned - completely detached from the main flow.

        Example: detach Worker("input")

        Returns:
            None (fire-and-forget)
        """
        import threading

        # Create a thread that will execute the call
        def run_detached():
            try:
                node.call.accept(self)
            except Exception as e:
                # Log error but don't propagate - fire-and-forget
                import sys
                print(f"[detach] Background task error: {e}", file=sys.stderr)

        # Start the thread
        thread = threading.Thread(target=run_detached, daemon=True)
        thread.start()

        # Return immediately - fire-and-forget
        return None

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

        # Push call stack frame (AI observability)
        self.observability.call_stack.push(agent.name, agent.span, args)
        self.observability.tracer.trace("call", agent.span, {"agent": agent.name, "args": args, "isolation": isolation_level})

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
        # Check if we're already in a running event loop (e.g., in REPL)
        # Use asyncio.get_running_loop() which raises RuntimeError if no loop is running
        in_event_loop = False
        try:
            _loop = asyncio.get_running_loop()
            in_event_loop = True
        except RuntimeError:
            # No running event loop
            in_event_loop = False

        if isinstance(tasks, Task):
            # Single task: execute if pending, then return result or raise exception
            if tasks.is_pending:
                if in_event_loop:
                    # Already in event loop - use thread pool directly
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
        """Report a runtime error and raise an exception.

        v1.11: Don't report to error collector. Runtime errors propagate
        via exception and are caught by try-catch. If uncaught, CLI handles it.
        """
        raise HelenRuntimeErrorClass(message, span)
