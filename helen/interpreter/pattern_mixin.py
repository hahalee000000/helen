"""Pattern matching mixin for the Helen interpreter.

Extracted from interpreter.py to improve code organization.
Provides visit methods for match/case statements and pattern matching.
"""

from __future__ import annotations

from typing import Any

from helen.core.ast import (
    CaseNode,
    MatchExprNode,
    MatchStmtNode,
    RangePatternNode,
    TypePatternNode,
    VariablePatternNode,
    WildcardPatternNode,
)

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


class PatternMixin:
    """Mixin providing pattern matching visitor methods.

    Host class must provide:
    - environment: Environment
    - _push_scope() -> context manager
    - _execute_stmts(stmts) -> object
    - _equal(a, b) -> bool
    - _truthy(value) -> bool
    """

    # Declare attributes expected from host class
    environment: Any
    errors: Any

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
                    from helen.core.ast import ExprStmtNode
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
