"""Abstract Syntax Tree node definitions for the Helen language."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Generic, TypeVar

from helen.core.source import SourceSpan
from helen.core.tokens import Token

if TYPE_CHECKING:
    pass

R = TypeVar("R")


# ---------------------------------------------------------------------------
# Visitor abstract base class
# ---------------------------------------------------------------------------

class Visitor(ABC, Generic[R]):
    """AST visitor abstract base class."""

    @abstractmethod
    def visit_literal(self, node: LiteralNode) -> R:
        """Visit a LiteralNode."""

    @abstractmethod
    def visit_variable(self, node: VariableNode) -> R:
        """Visit a VariableNode."""

    @abstractmethod
    def visit_binary_op(self, node: BinaryOpNode) -> R:
        """Visit a BinaryOpNode."""

    @abstractmethod
    def visit_unary_op(self, node: UnaryOpNode) -> R:
        """Visit a UnaryOpNode."""

    @abstractmethod
    def visit_grouping(self, node: GroupingNode) -> R:
        """Visit a GroupingNode."""

    @abstractmethod
    def visit_call(self, node: CallNode) -> R:
        """Visit a CallNode."""

    @abstractmethod
    def visit_call_arg(self, node: CallArgNode) -> R:
        """Visit a CallArgNode."""

    @abstractmethod
    def visit_var_decl(self, node: VarDeclNode) -> R:
        """Visit a VarDeclNode."""

    @abstractmethod
    def visit_if_stmt(self, node: IfStmtNode) -> R:
        """Visit an IfStmtNode."""

    @abstractmethod
    def visit_for_stmt(self, node: ForStmtNode) -> R:
        """Visit a ForStmtNode."""

    @abstractmethod
    def visit_while_stmt(self, node: WhileStmtNode) -> R:
        """Visit a WhileStmtNode."""

    @abstractmethod
    def visit_break_stmt(self, node: BreakStmtNode) -> R:
        """Visit a BreakStmtNode."""

    @abstractmethod
    def visit_continue_stmt(self, node: ContinueStmtNode) -> R:
        """Visit a ContinueStmtNode."""

    @abstractmethod
    def visit_return_stmt(self, node: ReturnStmtNode) -> R:
        """Visit a ReturnStmtNode."""

    @abstractmethod
    def visit_expr_stmt(self, node: ExprStmtNode) -> R:
        """Visit an ExprStmtNode."""

    @abstractmethod
    def visit_agent_decl(self, node: AgentDeclNode) -> R:
        """Visit an AgentDeclNode."""

    @abstractmethod
    def visit_prompt_def(self, node: PromptDefNode) -> R:
        """Visit a PromptDefNode."""

    @abstractmethod
    def visit_main_block(self, node: MainBlockNode) -> R:
        """Visit a MainBlockNode."""

    @abstractmethod
    def visit_program(self, node: ProgramNode) -> R:
        """Visit a ProgramNode."""

    @abstractmethod
    def visit_function_decl(self, node: FunctionDeclNode) -> R:
        """Visit a FunctionDeclNode."""

    @abstractmethod
    def visit_import_stmt(self, node: ImportStmtNode) -> R:
        """Visit an ImportStmtNode."""

    @abstractmethod
    def visit_type(self, node: TypeNode) -> R:
        """Visit a TypeNode."""

    @abstractmethod
    def visit_index(self, node: IndexNode) -> R:
        """Visit an IndexNode."""

    @abstractmethod
    def visit_access(self, node: AccessNode) -> R:
        """Visit an AccessNode."""

    @abstractmethod
    def visit_declaration(self, node: DeclarationNode) -> R:
        """Visit a DeclarationNode."""

    @abstractmethod
    def visit_agent_param(self, node: AgentParamNode) -> R:
        """Visit an AgentParamNode."""

    @abstractmethod
    def visit_async_call_stmt(self, node: AsyncCallStmtNode) -> R:
        """Visit an AsyncCallStmtNode."""

    @abstractmethod
    def visit_case(self, node: CaseNode) -> R:
        """Visit a CaseNode."""

    @abstractmethod
    def visit_catch_clause(self, node: CatchClauseNode) -> R:
        """Visit a CatchClauseNode."""

    @abstractmethod
    def visit_catch_all(self, node: CatchAllNode) -> R:
        """Visit a CatchAllNode."""

    @abstractmethod
    def visit_finally_block(self, node: FinallyBlockNode) -> R:
        """Visit a FinallyBlockNode."""

    @abstractmethod
    def visit_try_stmt(self, node: TryStmtNode) -> R:
        """Visit a TryStmtNode."""

    @abstractmethod
    def visit_throw_stmt(self, node: ThrowStmtNode) -> R:
        """Visit a ThrowStmtNode."""

    @abstractmethod
    def visit_llm_branch(self, node: LlmBranchNode) -> R:
        """Visit a LlmBranchNode."""

    @abstractmethod
    def visit_llm_if_stmt(self, node: LlmIfStmtNode) -> R:
        """Visit a LlmIfStmtNode."""

    @abstractmethod
    def visit_llm_option(self, node: LlmOptionNode) -> R:
        """Visit a LlmOptionNode."""

    @abstractmethod
    def visit_llm_choose_stmt(self, node: LlmChooseStmtNode) -> R:
        """Visit a LlmChooseStmtNode."""

    @abstractmethod
    def visit_llm_act_stmt(self, node: LlmActStmtNode) -> R:
        """Visit a LlmActStmtNode."""

    @abstractmethod
    def visit_llm_act_expr(self, node: LlmActExprNode) -> R:
        """Visit a LlmActExprNode."""

    @abstractmethod
    def visit_match_stmt(self, node: MatchStmtNode) -> R:
        """Visit a MatchStmtNode."""

    @abstractmethod
    def visit_optional_type(self, node: OptionalTypeNode) -> R:
        """Visit an OptionalTypeNode."""

    @abstractmethod
    def visit_union_type(self, node: UnionTypeNode) -> R:
        """Visit a UnionTypeNode."""

    @abstractmethod
    def visit_literal_type(self, node: LiteralTypeNode) -> R:
        """Visit a LiteralTypeNode."""

    @abstractmethod
    def visit_list_literal(self, node: ListLiteralNode) -> R:
        """Visit a ListLiteralNode."""

    @abstractmethod
    def visit_map_entry(self, node: MapEntryNode) -> R:
        """Visit a MapEntryNode."""

    @abstractmethod
    def visit_map_literal(self, node: MapLiteralNode) -> R:
        """Visit a MapLiteralNode."""

    @abstractmethod
    def visit_template_ref(self, node: TemplateRefNode) -> R:
        """Visit a TemplateRefNode."""

    @abstractmethod
    def visit_fn_block(self, node: FnBlockNode) -> R:
        """Visit a FnBlockNode."""


# ---------------------------------------------------------------------------
# AST node base classes
# ---------------------------------------------------------------------------

class ASTNode(ABC):
    """All AST nodes inherit from this."""
    span: SourceSpan

    @abstractmethod
    def accept(self, visitor: Visitor[R]) -> R:
        """Dispatch to the visitor."""


class ExpressionNode(ASTNode):
    """Expression node base class."""


class StatementNode(ASTNode):
    """Statement node base class."""


# ---------------------------------------------------------------------------
# Expression nodes
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class LiteralNode(ExpressionNode):
    """Literal value: 42, 3.14, \"hello\", true, false, null."""
    value: str | int | float | bool | None
    span: SourceSpan

    def accept(self, visitor: Visitor[R]) -> R:
        """Dispatch to the visitor."""
        return visitor.visit_literal(self)


@dataclass(frozen=True)
class VariableNode(ExpressionNode):
    """Identifier: x, my_var."""
    name: str
    span: SourceSpan

    def accept(self, visitor: Visitor[R]) -> R:
        """Dispatch to the visitor."""
        return visitor.visit_variable(self)


@dataclass(frozen=True)
class BinaryOpNode(ExpressionNode):
    """Binary operation: a + b, x == y."""
    left: ExpressionNode
    operator: Token
    right: ExpressionNode
    span: SourceSpan

    def accept(self, visitor: Visitor[R]) -> R:
        """Dispatch to the visitor."""
        return visitor.visit_binary_op(self)


@dataclass(frozen=True)
class UnaryOpNode(ExpressionNode):
    """Unary operation: !x, -n."""
    operator: Token
    operand: ExpressionNode
    span: SourceSpan

    def accept(self, visitor: Visitor[R]) -> R:
        """Dispatch to the visitor."""
        return visitor.visit_unary_op(self)


@dataclass(frozen=True)
class GroupingNode(ExpressionNode):
    """Grouped expression: (a + b)."""
    expression: ExpressionNode
    span: SourceSpan

    def accept(self, visitor: Visitor[R]) -> R:
        """Dispatch to the visitor."""
        return visitor.visit_grouping(self)


@dataclass(frozen=True)
class CallArgNode:
    """Call argument: name = value."""
    name: str | None
    value: ExpressionNode

    def accept(self, visitor: Visitor[R]) -> R:
        """Dispatch to the visitor."""
        return visitor.visit_call_arg(self)


@dataclass(frozen=True)
class CallNode(ExpressionNode):
    """Function call: print(x)."""
    callee: ExpressionNode
    arguments: list[CallArgNode]
    span: SourceSpan

    def accept(self, visitor: Visitor[R]) -> R:
        """Dispatch to the visitor."""
        return visitor.visit_call(self)


@dataclass(frozen=True)
class IndexNode(ExpressionNode):
    """Index access: arr[0]."""
    target: ExpressionNode
    index: ExpressionNode
    span: SourceSpan

    def accept(self, visitor: Visitor[R]) -> R:
        """Dispatch to the visitor."""
        return visitor.visit_index(self)


@dataclass(frozen=True)
class AccessNode(ExpressionNode):
    """Member access: obj.field."""
    target: ExpressionNode
    property: str
    span: SourceSpan

    def accept(self, visitor: Visitor[R]) -> R:
        """Dispatch to the visitor."""
        return visitor.visit_access(self)


@dataclass(frozen=True)
class ListLiteralNode(ExpressionNode):
    """List literal: [1, 2, 3]."""
    elements: list[ExpressionNode]
    span: SourceSpan

    def accept(self, visitor: Visitor[R]) -> R:
        """Dispatch to the visitor."""
        return visitor.visit_list_literal(self)


@dataclass(frozen=True)
class MapEntryNode:
    """Map entry: key: value."""
    key: ExpressionNode
    value: ExpressionNode
    span: SourceSpan

    def accept(self, visitor: Visitor[R]) -> R:
        """Dispatch to the visitor."""
        return visitor.visit_map_entry(self)


@dataclass(frozen=True)
class MapLiteralNode(ExpressionNode):
    """Map literal: {"key": value}."""
    entries: list[MapEntryNode]
    span: SourceSpan

    def accept(self, visitor: Visitor[R]) -> R:
        """Dispatch to the visitor."""
        return visitor.visit_map_literal(self)


@dataclass(frozen=True)
class TemplateRefNode(ExpressionNode):
    """Template variable reference: {{expr}}."""
    expression: ExpressionNode
    span: SourceSpan

    def accept(self, visitor: Visitor[R]) -> R:
        """Dispatch to the visitor."""
        return visitor.visit_template_ref(self)


# ---------------------------------------------------------------------------
# Type nodes
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class TypeNode(ExpressionNode):
    """Type reference: int, str, MyType."""
    name: str
    span: SourceSpan

    def accept(self, visitor: Visitor[R]) -> R:
        """Dispatch to the visitor."""
        return visitor.visit_type(self)


@dataclass(frozen=True)
class OptionalTypeNode(ExpressionNode):
    """Optional type: T?."""
    inner: TypeNode
    span: SourceSpan

    def accept(self, visitor: Visitor[R]) -> R:
        """Dispatch to the visitor."""
        return visitor.visit_optional_type(self)


@dataclass(frozen=True)
class UnionTypeNode(ExpressionNode):
    """Union type: A|B|C."""
    members: list[TypeNode]
    span: SourceSpan

    def accept(self, visitor: Visitor[R]) -> R:
        """Dispatch to the visitor."""
        return visitor.visit_union_type(self)


@dataclass(frozen=True)
class LiteralTypeNode(ExpressionNode):
    """Literal type: Literal["hello", 42]."""
    values: list[ExpressionNode]
    span: SourceSpan

    def accept(self, visitor: Visitor[R]) -> R:
        """Dispatch to the visitor."""
        return visitor.visit_literal_type(self)


# ---------------------------------------------------------------------------
# Statement nodes
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class VarDeclNode(StatementNode):
    """Variable declaration: let x = 42, const MAX = 100."""
    name: str
    type_annotation: TypeNode | None
    initializer: ExpressionNode | None
    mutable: bool
    span: SourceSpan

    def accept(self, visitor: Visitor[R]) -> R:
        """Dispatch to the visitor."""
        return visitor.visit_var_decl(self)


@dataclass(frozen=True)
class IfStmtNode(StatementNode):
    """Conditional: if cond { ... } else { ... }."""
    condition: ExpressionNode
    then_branch: StatementNode
    else_branch: StatementNode | None
    span: SourceSpan

    def accept(self, visitor: Visitor[R]) -> R:
        """Dispatch to the visitor."""
        return visitor.visit_if_stmt(self)


@dataclass(frozen=True)
class ForStmtNode(StatementNode):
    """For loop: for x in items { ... }."""
    iterator: VariableNode | None
    iterable: ExpressionNode
    body: StatementNode
    span: SourceSpan

    def accept(self, visitor: Visitor[R]) -> R:
        """Dispatch to the visitor."""
        return visitor.visit_for_stmt(self)


@dataclass(frozen=True)
class WhileStmtNode(StatementNode):
    """While loop: while cond { ... }."""
    condition: ExpressionNode
    body: StatementNode
    span: SourceSpan

    def accept(self, visitor: Visitor[R]) -> R:
        """Dispatch to the visitor."""
        return visitor.visit_while_stmt(self)


@dataclass(frozen=True)
class BreakStmtNode(StatementNode):
    """Break statement."""
    span: SourceSpan

    def accept(self, visitor: Visitor[R]) -> R:
        """Dispatch to the visitor."""
        return visitor.visit_break_stmt(self)


@dataclass(frozen=True)
class ContinueStmtNode(StatementNode):
    """Continue statement."""
    span: SourceSpan

    def accept(self, visitor: Visitor[R]) -> R:
        """Dispatch to the visitor."""
        return visitor.visit_continue_stmt(self)


@dataclass(frozen=True)
class ReturnStmtNode(StatementNode):
    """Return statement."""
    value: ExpressionNode | None
    span: SourceSpan

    def accept(self, visitor: Visitor[R]) -> R:
        """Dispatch to the visitor."""
        return visitor.visit_return_stmt(self)


@dataclass(frozen=True)
class ExprStmtNode(StatementNode):
    """Expression as a statement."""
    expression: ExpressionNode
    span: SourceSpan

    def accept(self, visitor: Visitor[R]) -> R:
        """Dispatch to the visitor."""
        return visitor.visit_expr_stmt(self)


@dataclass(frozen=True)
class PromptDefNode(StatementNode):
    """Prompt definition."""
    content: str
    span: SourceSpan

    def accept(self, visitor: Visitor[R]) -> R:
        """Dispatch to the visitor."""
        return visitor.visit_prompt_def(self)


@dataclass(frozen=True)
class DeclarationNode(StatementNode):
    """Agent declaration config block."""
    description: str | None
    model: str | None
    tools: list[str] | None
    skills: list[str] | None
    sub_agents: list[str] | None
    memory: str | None
    temperature: float | None
    max_turns: int | None
    span: SourceSpan

    def accept(self, visitor: Visitor[R]) -> R:
        """Dispatch to the visitor."""
        return visitor.visit_declaration(self)


@dataclass(frozen=True)
class AgentParamNode(StatementNode):
    """Agent parameter declaration: name: Type? = default?."""
    name: str
    type_annotation: TypeNode | None
    default_value: ExpressionNode | None
    span: SourceSpan

    def accept(self, visitor: Visitor[R]) -> R:
        """Dispatch to the visitor."""
        return visitor.visit_agent_param(self)


@dataclass(frozen=True)
class AgentDeclNode(StatementNode):
    """Agent declaration: agent Name(params?) { declarations, prompt, logic }.

    Attributes:
        functions: Functions declared inside ``functions { }`` block (HLD 3.5.3).
            Registered in the agent's call scope when invoked, so ``main`` can call them.
    """
    name: str
    params: list[AgentParamNode]
    declarations: list["DeclarationNode"]
    prompt: PromptDefNode | None
    logic: StatementNode | None  # MainBlockNode or other statement
    span: SourceSpan
    functions: list["FunctionDeclNode"] = field(default_factory=list)

    def accept(self, visitor: Visitor[R]) -> R:
        """Dispatch to the visitor."""
        return visitor.visit_agent_decl(self)


@dataclass(frozen=True)
class MainBlockNode(StatementNode):
    """Main block: main { body }."""
    body: list[StatementNode]
    span: SourceSpan

    def accept(self, visitor: Visitor[R]) -> R:
        """Dispatch to the visitor."""
        return visitor.visit_main_block(self)


@dataclass(frozen=True)
class FunctionDeclNode(StatementNode):
    """Function declaration: fn name(params) -> type { body }."""
    name: str
    params: list[AgentParamNode]
    return_type: TypeNode | None
    body: "FnBlockNode"
    span: SourceSpan

    def accept(self, visitor: Visitor[R]) -> R:
        """Dispatch to the visitor."""
        return visitor.visit_function_decl(self)


@dataclass(frozen=True)
class FnBlockNode(StatementNode):
    """Function body block: { stmt* }."""
    body: list[StatementNode]
    span: SourceSpan

    def accept(self, visitor: Visitor[R]) -> R:
        """Dispatch to the visitor."""
        return visitor.visit_fn_block(self)


@dataclass(frozen=True)
class ImportStmtNode(StatementNode):
    """Import statement: import \"path\" as alias."""
    module_path: str
    alias: str | None
    span: SourceSpan

    def accept(self, visitor: Visitor[R]) -> R:
        """Dispatch to the visitor."""
        return visitor.visit_import_stmt(self)


@dataclass(frozen=True)
class AsyncCallStmtNode(StatementNode):
    """Async call statement."""
    call: CallNode
    span: SourceSpan

    def accept(self, visitor: Visitor[R]) -> R:
        """Dispatch to the visitor."""
        return visitor.visit_async_call_stmt(self)


@dataclass(frozen=True)
class CaseNode(StatementNode):
    """Match case: case pattern { ... }."""
    pattern: ExpressionNode
    body: list[StatementNode]
    span: SourceSpan

    def accept(self, visitor: Visitor[R]) -> R:
        """Dispatch to the visitor."""
        return visitor.visit_case(self)


@dataclass(frozen=True)
class CatchClauseNode(StatementNode):
    """Typed catch clause."""
    error_type: TypeNode
    error_name: str
    body: list[StatementNode]
    span: SourceSpan

    def accept(self, visitor: Visitor[R]) -> R:
        """Dispatch to the visitor."""
        return visitor.visit_catch_clause(self)


@dataclass(frozen=True)
class CatchAllNode(StatementNode):
    """Catch-all clause."""
    body: list[StatementNode]
    span: SourceSpan

    def accept(self, visitor: Visitor[R]) -> R:
        """Dispatch to the visitor."""
        return visitor.visit_catch_all(self)


@dataclass(frozen=True)
class FinallyBlockNode(StatementNode):
    """Finally block."""
    body: list[StatementNode]
    span: SourceSpan

    def accept(self, visitor: Visitor[R]) -> R:
        """Dispatch to the visitor."""
        return visitor.visit_finally_block(self)


@dataclass(frozen=True)
class TryStmtNode(StatementNode):
    """Try-catch-finally statement."""
    body: list[StatementNode]
    catch_clauses: list[CatchClauseNode]
    catch_all: CatchAllNode | None
    finally_block: FinallyBlockNode | None
    span: SourceSpan

    def accept(self, visitor: Visitor[R]) -> R:
        """Dispatch to the visitor."""
        return visitor.visit_try_stmt(self)


@dataclass(frozen=True)
class ThrowStmtNode(StatementNode):
    """Throw statement: throw ExceptionType or throw ExceptionType(message)."""
    exception_type: TypeNode
    message: ExpressionNode | None
    span: SourceSpan

    def accept(self, visitor: Visitor[R]) -> R:
        """Dispatch to the visitor."""
        return visitor.visit_throw_stmt(self)


@dataclass(frozen=True)
class LlmBranchNode(StatementNode):
    """LLM if branch."""
    condition: ExpressionNode | None
    body: list[StatementNode]
    span: SourceSpan

    def accept(self, visitor: Visitor[R]) -> R:
        """Dispatch to the visitor."""
        return visitor.visit_llm_branch(self)


@dataclass(frozen=True)
class LlmIfStmtNode(StatementNode):
    """LLM if statement."""
    description: str
    branches: list[LlmBranchNode]
    span: SourceSpan

    def accept(self, visitor: Visitor[R]) -> R:
        """Dispatch to the visitor."""
        return visitor.visit_llm_if_stmt(self)


@dataclass(frozen=True)
class LlmOptionNode(StatementNode):
    """LLM choose option."""
    label: str
    body: list[StatementNode]
    span: SourceSpan

    def accept(self, visitor: Visitor[R]) -> R:
        """Dispatch to the visitor."""
        return visitor.visit_llm_option(self)


@dataclass(frozen=True)
class LlmChooseStmtNode(StatementNode):
    """LLM choose statement."""
    description: str
    options: list[LlmOptionNode]
    default: list[StatementNode]
    span: SourceSpan

    def accept(self, visitor: Visitor[R]) -> R:
        """Dispatch to the visitor."""
        return visitor.visit_llm_choose_stmt(self)


@dataclass(frozen=True)
class LlmActStmtNode(StatementNode):
    """LLM act statement."""
    target: str
    arguments: dict[str, ExpressionNode]
    description: str
    span: SourceSpan

    def accept(self, visitor: Visitor[R]) -> R:
        """Dispatch to the visitor."""
        return visitor.visit_llm_act_stmt(self)


@dataclass(frozen=True)
class LlmActExprNode(ExpressionNode):
    """LLM act as an expression: llm act <prompt_expr>? Returns the LLM response text.

    When prompt is None (bare ``llm act``), the agent's rendered prompt template
    is used as the user message automatically (HLD 3.6.5).
    """
    prompt: ExpressionNode | None
    span: SourceSpan

    def accept(self, visitor: Visitor[R]) -> R:
        """Dispatch to the visitor."""
        return visitor.visit_llm_act_expr(self)


@dataclass(frozen=True)
class MatchStmtNode(StatementNode):
    """Match statement."""
    subject: ExpressionNode
    cases: list[CaseNode]
    default: list[StatementNode]
    span: SourceSpan

    def accept(self, visitor: Visitor[R]) -> R:
        """Dispatch to the visitor."""
        return visitor.visit_match_stmt(self)


# ---------------------------------------------------------------------------
# Program root
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ProgramNode(ASTNode):
    """Root program node."""
    statements: list[ASTNode]
    span: SourceSpan

    def accept(self, visitor: Visitor[R]) -> R:
        """Dispatch to the visitor."""
        return visitor.visit_program(self)


# ---------------------------------------------------------------------------
# ASTPrinter — debug serializer
# ---------------------------------------------------------------------------

class ASTPrinter(Visitor[str]):
    """Serialize AST to S-expression format."""

    def print(self, node: ASTNode) -> str:
        """Print an AST node."""
        return node.accept(self)

    def _parenthesize(self, name: str, *parts: Any) -> str:
        """Format parts as an S-expression."""
        result_parts: list[str] = [name]
        for p in parts:
            if isinstance(p, ASTNode):
                result_parts.append(p.accept(self))
            elif isinstance(p, (list, tuple)):
                for item in p:
                    if isinstance(item, ASTNode):
                        result_parts.append(item.accept(self))
                    else:
                        result_parts.append(str(item))
            elif p is None:
                result_parts.append("<none>")
            else:
                result_parts.append(str(p))
        return "(" + " ".join(result_parts) + ")"

    def visit_literal(self, node: LiteralNode) -> str:
        """Visit a LiteralNode."""
        if node.value is None:
            return "null"
        if isinstance(node.value, bool):
            return "true" if node.value else "false"
        if isinstance(node.value, str):
            return '"' + node.value + '"'
        return str(node.value)

    def visit_variable(self, node: VariableNode) -> str:
        """Visit a VariableNode."""
        return node.name

    def visit_binary_op(self, node: BinaryOpNode) -> str:
        """Visit a BinaryOpNode."""
        return self._parenthesize(node.operator.lexeme, node.left, node.right)

    def visit_unary_op(self, node: UnaryOpNode) -> str:
        """Visit a UnaryOpNode."""
        return self._parenthesize(node.operator.lexeme, node.operand)

    def visit_grouping(self, node: GroupingNode) -> str:
        """Visit a GroupingNode."""
        return self._parenthesize("group", node.expression)

    def visit_call(self, node: CallNode) -> str:
        """Visit a CallNode."""
        args = " ".join(a.value.accept(self) for a in node.arguments)
        return self._parenthesize("call", node.callee.accept(self), args)

    def visit_call_arg(self, node: CallArgNode) -> str:
        """Visit a CallArgNode."""
        if node.name:
            return node.name + "=" + node.value.accept(self)
        return node.value.accept(self)

    def visit_index(self, node: IndexNode) -> str:
        """Visit an IndexNode."""
        return self._parenthesize("index", node.target, node.index)

    def visit_access(self, node: AccessNode) -> str:
        """Visit an AccessNode."""
        return "(" + node.target.accept(self) + " . " + node.property + ")"

    def visit_var_decl(self, node: VarDeclNode) -> str:
        """Visit a VarDeclNode."""
        kw = "let" if node.mutable else "const"
        parts: list[Any] = [node.name]
        if node.initializer:
            parts.append("=")
            parts.append(node.initializer)
        return self._parenthesize(kw, *parts)

    def visit_if_stmt(self, node: IfStmtNode) -> str:
        """Visit an IfStmtNode."""
        parts: list[Any] = [node.condition, node.then_branch]
        if node.else_branch:
            parts.append(node.else_branch)
        return self._parenthesize("if", *parts)

    def visit_for_stmt(self, node: ForStmtNode) -> str:
        """Visit a ForStmtNode."""
        return self._parenthesize("for", node.iterator, node.iterable, node.body)

    def visit_while_stmt(self, node: WhileStmtNode) -> str:
        """Visit a WhileStmtNode."""
        return self._parenthesize("while", node.condition, node.body)

    def visit_break_stmt(self, node: BreakStmtNode) -> str:
        """Visit a BreakStmtNode."""
        return "(break)"

    def visit_continue_stmt(self, node: ContinueStmtNode) -> str:
        """Visit a ContinueStmtNode."""
        return "(continue)"

    def visit_return_stmt(self, node: ReturnStmtNode) -> str:
        """Visit a ReturnStmtNode."""
        if node.value:
            return self._parenthesize("return", node.value)
        return "(return)"

    def visit_expr_stmt(self, node: ExprStmtNode) -> str:
        """Visit an ExprStmtNode."""
        return node.expression.accept(self)

    def visit_agent_decl(self, node: AgentDeclNode) -> str:
        """Visit an AgentDeclNode."""
        parts: list[Any] = [node.name]
        if node.params:
            parts.append(node.params)
        if node.prompt:
            parts.append(node.prompt)
        return self._parenthesize("agent", *parts)

    def visit_prompt_def(self, node: PromptDefNode) -> str:
        """Visit a PromptDefNode."""
        return '"' + node.content + '"'

    def visit_main_block(self, node: MainBlockNode) -> str:
        """Visit a MainBlockNode."""
        return self._parenthesize("main-block", *node.body)

    def visit_program(self, node: ProgramNode) -> str:
        """Visit a ProgramNode."""
        return self._parenthesize("program", *node.statements)

    def visit_function_decl(self, node: FunctionDeclNode) -> str:
        """Visit a FunctionDeclNode."""
        return self._parenthesize("fn", node.name)

    def visit_import_stmt(self, node: ImportStmtNode) -> str:
        """Visit an ImportStmtNode."""
        return self._parenthesize("import", node.module_path)

    def visit_type(self, node: TypeNode) -> str:
        """Visit a TypeNode."""
        return node.name

    def visit_declaration(self, node: DeclarationNode) -> str:
        """Visit a DeclarationNode."""
        return "(declaration)"

    def visit_agent_param(self, node: AgentParamNode) -> str:
        """Visit an AgentParamNode."""
        return "(param " + node.name + ")"

    def visit_async_call_stmt(self, node: AsyncCallStmtNode) -> str:
        """Visit an AsyncCallStmtNode."""
        return self._parenthesize("async-call", node.call)

    def visit_case(self, node: CaseNode) -> str:
        """Visit a CaseNode."""
        return self._parenthesize("case", node.pattern)

    def visit_catch_clause(self, node: CatchClauseNode) -> str:
        """Visit a CatchClauseNode."""
        return self._parenthesize("catch", node.error_type)

    def visit_catch_all(self, node: CatchAllNode) -> str:
        """Visit a CatchAllNode."""
        return "(catch-all)"

    def visit_finally_block(self, node: FinallyBlockNode) -> str:
        """Visit a FinallyBlockNode."""
        return self._parenthesize("finally", *node.body)

    def visit_try_stmt(self, node: TryStmtNode) -> str:
        """Visit a TryStmtNode."""
        return self._parenthesize("try", *node.body)

    def visit_throw_stmt(self, node: ThrowStmtNode) -> str:
        """Visit a ThrowStmtNode."""
        parts: list[Any] = [node.exception_type]
        if node.message:
            parts.append(node.message)
        return self._parenthesize("throw", *parts)

    def visit_llm_branch(self, node: LlmBranchNode) -> str:
        """Visit a LlmBranchNode."""
        return self._parenthesize("branch", *node.body)

    def visit_llm_if_stmt(self, node: LlmIfStmtNode) -> str:
        """Visit a LlmIfStmtNode."""
        return self._parenthesize("llm-if", node.description, *node.branches)

    def visit_llm_option(self, node: LlmOptionNode) -> str:
        """Visit a LlmOptionNode."""
        return self._parenthesize("option", node.label)

    def visit_llm_choose_stmt(self, node: LlmChooseStmtNode) -> str:
        """Visit a LlmChooseStmtNode."""
        return self._parenthesize("llm-choose", node.description)

    def visit_llm_act_stmt(self, node: LlmActStmtNode) -> str:
        """Visit a LlmActStmtNode."""
        return self._parenthesize("llm-act", node.target, node.description)

    def visit_llm_act_expr(self, node: LlmActExprNode) -> str:
        """Visit a LlmActExprNode."""
        return self._parenthesize("llm-act-expr", node.prompt)

    def visit_match_stmt(self, node: MatchStmtNode) -> str:
        """Visit a MatchStmtNode."""
        return self._parenthesize("match", node.subject)

    def visit_optional_type(self, node: OptionalTypeNode) -> str:
        """Visit an OptionalTypeNode."""
        return self._parenthesize("optional", node.inner)

    def visit_union_type(self, node: UnionTypeNode) -> str:
        """Visit a UnionTypeNode."""
        return self._parenthesize("union", *node.members)

    def visit_literal_type(self, node: LiteralTypeNode) -> str:
        """Visit a LiteralTypeNode."""
        return self._parenthesize("literal-type", *node.values)

    def visit_list_literal(self, node: ListLiteralNode) -> str:
        """Visit a ListLiteralNode."""
        return self._parenthesize("list", *node.elements)

    def visit_map_entry(self, node: MapEntryNode) -> str:
        """Visit a MapEntryNode."""
        return self._parenthesize("entry", node.key, node.value)

    def visit_map_literal(self, node: MapLiteralNode) -> str:
        """Visit a MapLiteralNode."""
        return self._parenthesize("map", *node.entries)

    def visit_template_ref(self, node: TemplateRefNode) -> str:
        """Visit a TemplateRefNode."""
        return self._parenthesize("template-ref", node.expression)

    def visit_fn_block(self, node: FnBlockNode) -> str:
        """Visit a FnBlockNode."""
        return self._parenthesize("fn-block", *node.body)
