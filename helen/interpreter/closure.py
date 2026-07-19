"""Closure class and free-variable analysis for Helen closures.

Extracted from interpreter.py to improve code organization.
"""

from __future__ import annotations

from helen.core.ast import LambdaNode
from helen.interpreter.environment import Environment


class Closure:
    """Represents a closure - a lambda function with its captured environment.

    A closure captures the lexical environment where it was defined,
    allowing it to access variables from that environment even when
    called from a different scope.
    """
    def __init__(self, lambda_node: LambdaNode, captured_env: Environment):
        self.lambda_node = lambda_node
        self.captured_env = captured_env
        # v1.18: For recursive closures — when assigned as
        # ``let f = fn(...) { ... f(...) ... }`` the variable name is stored
        # here so that _call_closure can inject the closure back into the
        # call environment under that name, enabling self-recursion.
        self._self_name: str | None = None

    def __repr__(self):
        return f"<closure with {len(self.lambda_node.params)} params>"


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
        TemplateRefNode, AssertStmtNode, TryStmtNode,
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
    from helen.core.ast import VariablePatternNode
    if isinstance(pattern, VariablePatternNode):
        bound.add(pattern.name)
    # WildcardPatternNode doesn't bind anything
    # Other patterns (literal, range) don't bind variables either
