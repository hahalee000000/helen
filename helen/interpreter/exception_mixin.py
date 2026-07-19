"""Exception handling mixin for the Helen interpreter.

Extracted from interpreter.py to improve code organization.
Provides visit methods for try/catch/finally/throw/assert statements.
"""

from __future__ import annotations

from typing import Any

from helen.core.ast import (
    AssertStmtNode,
    CatchAllNode,
    CatchClauseNode,
    FinallyBlockNode,
    ThrowStmtNode,
    TryStmtNode,
)
from helen.interpreter.exceptions import (
    AssertionError as HelenAssertionError,
    HelenRuntimeError,
    ReturnSentinel,
    error_matches,
    resolve_exception,
    _PREDEFINED_EXCEPTIONS,
)


class ExceptionMixin:
    """Mixin providing exception handling visitor methods.

    Host class must provide:
    - environment: Environment
    - errors: ErrorReporter
    - observability: ObservabilityManager
    - _push_scope() -> context manager
    - _execute_stmts(stmts) -> object
    - _truthy(value) -> bool
    - _runtime_error(span, message) -> None
    """

    # Declare attributes expected from host class
    environment: Any
    errors: Any
    observability: Any

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
