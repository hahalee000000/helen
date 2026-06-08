"""hellen/core/parser.py — Hellen Pratt 优先级解析器 + 递归下降。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional

from .source import SourceSpan
from .ast import (
    ASTNode,
    AgentDeclNode,
    AgentParamNode,
    AsyncCallStmtNode,
    BreakStmtNode,
    CallArgNode,
    CallNode,
    CaseNode,
    CatchAllNode,
    CatchClauseNode,
    ContinueStmtNode,
    DeclarationNode,
    ExpressionNode,
    FinallyBlockNode,
    FnBlockNode,
    ForStmtNode,
    FunctionDeclNode,
    GroupingNode,
    IfStmtNode,
    ImportStmtNode,
    ListLiteralNode,
    LlmActStmtNode,
    LlmBranchNode,
    LlmChooseStmtNode,
    LlmIfStmtNode,
    LlmOptionNode,
    LiteralNode,
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
    TryStmtNode,
    TypeNode,
    UnaryOpNode,
    UnionTypeNode,
    VarDeclNode,
    VariableNode,
    WhileStmtNode,
    IndexNode,
    AccessNode,
    BinaryOpNode,
)
from .errors import ErrorCode, ErrorReporter
from .tokens import Token, TokenType

PrefixParseFn = Callable[["Parser"], ExpressionNode]
InfixParseFn = Callable[["Parser", ExpressionNode], ExpressionNode]


class Precedence:
    """Pratt 解析优先级（数值越大绑定越紧）。"""
    NONE = 0
    ASSIGNMENT = 1
    OR = 2
    AND = 3
    EQUALITY = 4
    COMPARISON = 5
    TERM = 6
    FACTOR = 7
    UNARY = 8
    AWAIT = 9
    CALL = 10


@dataclass
class ParseFn:
    """单个 TokenType 的 Pratt 解析规则。"""
    prefix: Optional[PrefixParseFn] = None
    infix: Optional[InfixParseFn] = None
    precedence: int = Precedence.NONE


class Parser:
    """Hellen Pratt 优先级解析器 + 递归下降。"""

    def __init__(self, tokens: list[Token], errors: ErrorReporter | None = None):
        """初始化 Parser。
        Args:
            tokens: 词法分析产出的 Token 列表
            errors: 错误报告器（可选）
        """
        self.tokens = tokens
        self.errors = errors or ErrorReporter()
        self._pos = 0
        self._rules: dict[TokenType, ParseFn] = {}
        self._register_pratt_rules()

    def parse(self) -> ProgramNode:
        """解析 Token 流，返回 ProgramNode。"""
        statements: list[ASTNode] = []
        while not self._at_end():
            stmt = self._declaration()
            if stmt is not None:
                statements.append(stmt)
        if self.tokens:
            span = SourceSpan(
                file=self.tokens[0].file,
                start_line=self.tokens[0].line,
                start_col=self.tokens[0].col,
                end_line=self.tokens[-1].end_line,
                end_col=self.tokens[-1].end_col,
            )
        else:
            span = SourceSpan("<unknown>", 1, 1, 1, 1)
        return ProgramNode(statements=statements, span=span)

    def _register_pratt_rules(self) -> None:
        """注册 Pratt 解析规则。"""
        # Initialize all token types with empty rules
        for tt in TokenType:
            self._rules[tt] = ParseFn()

        # Prefix rules
        self._rules[TokenType.NUMBER].prefix = self._literal_number
        self._rules[TokenType.STRING].prefix = self._literal_string
        self._rules[TokenType.TRIPLE_QUOTE_STRING].prefix = self._literal_string
        self._rules[TokenType.TRUE].prefix = self._literal_bool
        self._rules[TokenType.FALSE].prefix = self._literal_bool
        self._rules[TokenType.NULL_KW].prefix = self._literal_null
        self._rules[TokenType.IDENTIFIER].prefix = self._identifier
        self._rules[TokenType.LEFT_PAREN].prefix = self._grouping
        self._rules[TokenType.BANG].prefix = self._unary
        self._rules[TokenType.MINUS].prefix = self._unary
        self._rules[TokenType.AWAIT].prefix = self._unary
        self._rules[TokenType.LEFT_BRACKET].prefix = self._list_literal
        self._rules[TokenType.LEFT_BRACE].prefix = self._map_literal
        self._rules[TokenType.TEMPLATE_OPEN].prefix = self._template_ref
        # CALL keyword as expression prefix (like identifier)
        self._rules[TokenType.CALL].prefix = self._call_kw

        # Precedence for prefix operators
        self._rules[TokenType.BANG].precedence = Precedence.UNARY
        self._rules[TokenType.MINUS].precedence = Precedence.UNARY
        self._rules[TokenType.AWAIT].precedence = Precedence.AWAIT

        # Infix rules with precedence
        infix_map = {
            TokenType.PLUS: Precedence.TERM,
            TokenType.MINUS: Precedence.TERM,
            TokenType.STAR: Precedence.FACTOR,
            TokenType.SLASH: Precedence.FACTOR,
            TokenType.PERCENT: Precedence.FACTOR,
            TokenType.BANG_EQUAL: Precedence.EQUALITY,
            TokenType.EQUAL_EQUAL: Precedence.EQUALITY,
            TokenType.GREATER: Precedence.COMPARISON,
            TokenType.GREATER_EQUAL: Precedence.COMPARISON,
            TokenType.LESS: Precedence.COMPARISON,
            TokenType.LESS_EQUAL: Precedence.COMPARISON,
            TokenType.AND: Precedence.AND,
            TokenType.OR: Precedence.OR,
            TokenType.ASSIGN: Precedence.ASSIGNMENT,
            TokenType.LEFT_PAREN: Precedence.CALL,
            TokenType.LEFT_BRACKET: Precedence.CALL,
            TokenType.DOT: Precedence.CALL,
        }
        for tt, prec in infix_map.items():
            self._rules[tt].infix = self._binary if tt not in (TokenType.LEFT_PAREN, TokenType.LEFT_BRACKET, TokenType.DOT) else (self._call if tt == TokenType.LEFT_PAREN else (self._index if tt == TokenType.LEFT_BRACKET else self._access))
            self._rules[tt].precedence = prec

    def _expression(self, precedence: int = Precedence.NONE) -> ExpressionNode:
        """Pratt 核心：解析表达式。"""
        if self._at_end():
            self._error("Expected expression.")
            return LiteralNode(value=None, span=self._make_span(self._peek(), self._peek()))

        token = self._current()
        rule = self._rules.get(token.type, ParseFn())
        if rule.prefix is None:
            self._error(f"Expected expression, got {token.type.name}")
            self._advance()  # Consume the unexpected token to avoid infinite loops
            return LiteralNode(value=None, span=self._make_span(token, token))

        self._advance()
        left = rule.prefix()

        while True:
            if self._at_end():
                break
            rule = self._rules.get(self._current().type, ParseFn())
            if rule.infix is None or rule.precedence < precedence:
                break
            self._advance()
            left = rule.infix(left)

        return left

    def _literal_number(self) -> ExpressionNode:
        """解析数字字面量。"""
        prev = self._previous()
        return LiteralNode(value=prev.literal, span=prev.span)

    def _literal_string(self) -> ExpressionNode:
        """解析字符串字面量。"""
        prev = self._previous()
        return LiteralNode(value=prev.literal, span=prev.span)

    def _literal_bool(self) -> ExpressionNode:
        """解析布尔字面量。"""
        prev = self._previous()
        return LiteralNode(value=prev.literal, span=prev.span)

    def _literal_null(self) -> ExpressionNode:
        """解析 null 字面量。"""
        prev = self._previous()
        return LiteralNode(value=None, span=prev.span)

    def _identifier(self) -> ExpressionNode:
        """解析标识符为变量节点。"""
        prev = self._previous()
        return VariableNode(name=prev.lexeme, span=prev.span)

    def _call_kw(self) -> ExpressionNode:
        """解析 call 关键字为变量节点（与普通标识符相同）。"""
        prev = self._previous()
        return VariableNode(name=prev.lexeme, span=prev.span)

    def _grouping(self) -> ExpressionNode:
        """解析分组表达式 (expr)。"""
        expr = self._expression()
        end = self._consume(TokenType.RIGHT_PAREN, "Expected ')' after expression.")
        return GroupingNode(expression=expr, span=self._make_span(expr.span if hasattr(expr, 'span') else self._previous(), end))

    def _unary(self) -> ExpressionNode:
        """解析一元表达式。"""
        operator = self._previous()
        right = self._expression(Precedence.UNARY)
        return UnaryOpNode(operator=operator, operand=right,
                           span=self._make_span(operator, self._previous()))

    def _binary(self, left: ExpressionNode) -> ExpressionNode:
        """解析二元表达式。"""
        operator = self._previous()
        rule = self._rules.get(operator.type, ParseFn())
        right = self._expression(rule.precedence + 1)
        return BinaryOpNode(left=left, operator=operator, right=right,
                            span=self._make_span(operator, self._previous()))

    def _call(self, callee: ExpressionNode) -> ExpressionNode:
        """解析函数调用 callee(args)。"""
        args: list[CallArgNode] = []
        if not self._check(TokenType.RIGHT_PAREN):
            # Check for named arg: name = expr or just expr
            if self._check(TokenType.IDENTIFIER):
                # Peek ahead: if next is ASSIGN, it's a named arg
                saved_pos = self._pos
                self._advance()
                if self._check(TokenType.ASSIGN):
                    # Named argument
                    name = self._previous().lexeme
                    self._advance()  # consume =
                    value = self._expression()
                    args.append(CallArgNode(name=name, value=value))
                else:
                    # Just an identifier expression - backtrack
                    self._pos = saved_pos
                    args.append(CallArgNode(name=None, value=self._expression()))
            else:
                args.append(CallArgNode(name=None, value=self._expression()))
            while self._match(TokenType.COMMA):
                if self._check(TokenType.RIGHT_PAREN):
                    break
                if self._check(TokenType.IDENTIFIER):
                    saved_pos = self._pos
                    self._advance()
                    if self._check(TokenType.ASSIGN):
                        name = self._previous().lexeme
                        self._advance()
                        value = self._expression()
                        args.append(CallArgNode(name=name, value=value))
                    else:
                        self._pos = saved_pos
                        args.append(CallArgNode(name=None, value=self._expression()))
                else:
                    args.append(CallArgNode(name=None, value=self._expression()))
        paren = self._consume(TokenType.RIGHT_PAREN, "Expected ')' after arguments.")
        return CallNode(callee=callee, arguments=args,
                        span=self._make_span(callee.span if hasattr(callee, 'span') else self._previous(), paren))

    def _index(self, target: ExpressionNode) -> ExpressionNode:
        """解析索引访问 target[index]。"""
        index = self._expression()
        bracket = self._consume(TokenType.RIGHT_BRACKET, "Expected ']' after index.")
        return IndexNode(target=target, index=index,
                         span=self._make_span(target.span if hasattr(target, 'span') else self._previous(), bracket))

    def _access(self, target: ExpressionNode) -> ExpressionNode:
        """解析成员访问 target.property。"""
        prop = self._consume(TokenType.IDENTIFIER, "Expected property name after '.'.")
        return AccessNode(target=target, property=prop.lexeme,
                          span=self._make_span(target.span if hasattr(target, 'span') else self._previous(), prop))

    def _list_literal(self) -> ExpressionNode:
        """解析列表字面量: [expr, ...]。"""
        start = self._previous()
        elements: list[ExpressionNode] = []
        if not self._check(TokenType.RIGHT_BRACKET):
            elements.append(self._expression())
            while self._match(TokenType.COMMA):
                if self._check(TokenType.RIGHT_BRACKET):
                    break
                elements.append(self._expression())
        end = self._consume(TokenType.RIGHT_BRACKET, "Expected ']' after list elements.")
        return ListLiteralNode(elements=elements,
                               span=self._make_span(start, end))

    def _map_literal(self) -> ExpressionNode:
        """解析 Map 字面量: {key: value, ...}。"""
        start = self._previous()
        entries: list[MapEntryNode] = []
        if not self._check(TokenType.RIGHT_BRACE):
            # Try to parse as map entry; if it fails, report error
            entry = self._map_entry()
            if entry is not None:
                entries.append(entry)
            while self._match(TokenType.COMMA):
                if self._check(TokenType.RIGHT_BRACE):
                    break
                entry = self._map_entry()
                if entry is not None:
                    entries.append(entry)
        end = self._consume(TokenType.RIGHT_BRACE, "Expected '}' after map entries.")
        return MapLiteralNode(entries=entries,
                              span=self._make_span(start, end))

    def _map_entry(self) -> MapEntryNode | None:
        """解析单个 Map 条目: key: value。"""
        key = self._expression()
        self._consume(TokenType.COLON, "Expected ':' after map key.")
        value = self._expression()
        return MapEntryNode(key=key, value=value,
                            span=self._make_span(key.span if hasattr(key, 'span') else self._previous(), self._previous()))

    def _template_ref(self) -> ExpressionNode:
        """解析模板引用: {{expr}}。"""
        start = self._previous()
        expr = self._expression()
        end = self._consume(TokenType.TEMPLATE_CLOSE, "Expected '}}' to close template.")
        return TemplateRefNode(expression=expr,
                               span=self._make_span(start, end))

    def _declaration(self) -> StatementNode | None:
        """解析顶层声明。"""
        if self._at_end() or self._check(TokenType.RIGHT_BRACE):
            return None

        # async statement modifier detection (HLD 3.3.3)
        if self._check(TokenType.ASYNC):
            return self._async_call_stmt()

        if self._match(TokenType.LET, TokenType.CONST):
            return self._var_decl()
        if self._match(TokenType.IF):
            return self._if_stmt()
        if self._match(TokenType.FOR):
            return self._for_stmt()
        if self._match(TokenType.WHILE):
            return self._while_stmt()
        if self._match(TokenType.BREAK):
            return self._break_stmt()
        if self._match(TokenType.CONTINUE):
            return self._continue_stmt()
        if self._match(TokenType.RETURN):
            return self._return_stmt()
        if self._match(TokenType.FN):
            return self._function_decl()
        if self._match(TokenType.MAIN):
            return self._main_block()
        if self._match(TokenType.IMPORT):
            return self._import_stmt()
        if self._match(TokenType.AGENT):
            return self._agent_decl()
        if self._match(TokenType.TRY):
            return self._try_stmt()
        if self._match(TokenType.MATCH):
            return self._match_stmt()

        # LLM keyword disambiguation (HLD 3.3.5)
        if self._check(TokenType.LLM):
            return self._llm_stmt()

        if self._at_end():
            return None
        return self._expr_stmt()

    def _llm_stmt(self) -> StatementNode:
        """解析 llm 语句：根据下一个 Token 决定分支 (llm if / llm choose / llm act)。"""
        self._advance()  # consume LLM
        if self._check(TokenType.IF):
            return self._llm_if_stmt()
        elif self._check(TokenType.CHOOSE):
            return self._llm_choose_stmt()
        elif self._check(TokenType.ACT):
            return self._llm_act_stmt()
        else:
            self._error("Expected 'if', 'choose', or 'act' after 'llm'.")
            self._synchronize()
            return None

    def _async_call_stmt(self) -> AsyncCallStmtNode:
        """解析 async 语句修饰符：async call(...) (HLD 3.3.3)。"""
        start = self._advance()  # consume ASYNC
        # Optionally consume 'call' keyword
        self._match(TokenType.CALL)
        # Parse as a call expression
        call_expr = self._expression(Precedence.NONE)
        if not isinstance(call_expr, CallNode):
            self._error("'async' must be followed by a function call.")
            return AsyncCallStmtNode(call=CallNode(callee=VariableNode(name="", span=start.span), arguments=[], span=start.span), span=start.span)
        return AsyncCallStmtNode(call=call_expr,
                                 span=self._make_span(start, self._previous()))

    def _statement(self) -> StatementNode | None:
        """解析单个语句。"""
        return self._declaration()

    def _var_decl(self) -> VarDeclNode:
        """解析变量声明：let/const name = expr。"""
        mutable = self._previous().type == TokenType.LET
        name_tok = self._consume(TokenType.IDENTIFIER, "Expected variable name after 'let'/'const'.")
        type_annotation: TypeNode | None = None
        if self._match(TokenType.COLON):
            type_annotation = self._parse_type()
        init: ExpressionNode | None = None
        if self._match(TokenType.ASSIGN):
            init = self._expression()
        end = self._previous()
        span = self._make_span(name_tok, end)
        return VarDeclNode(name=name_tok.lexeme, type_annotation=type_annotation,
                           initializer=init, mutable=mutable, span=span)

    def _if_stmt(self) -> IfStmtNode:
        """解析 if 语句。"""
        start = self._previous()
        self._consume(TokenType.LEFT_PAREN, "Expected '(' after 'if'.")
        condition = self._expression()
        self._consume(TokenType.RIGHT_PAREN, "Expected ')' after if condition.")
        self._consume(TokenType.LEFT_BRACE, "Expected '{' before if body.")
        then_body = self._block_body()
        else_branch: StatementNode | None = None
        if self._match(TokenType.ELSE):
            if self._check(TokenType.LEFT_BRACE):
                self._advance()  # consume '{'
                else_branch = self._block_body()
            elif self._check(TokenType.IF):
                self._advance()
                else_branch = self._if_stmt()
        end = self._previous()
        return IfStmtNode(condition=condition, then_branch=then_body,
                          else_branch=else_branch,
                          span=self._make_span(start, end))

    def _for_stmt(self) -> ForStmtNode:
        """解析 for 语句：for x in expr { ... }。"""
        start = self._previous()
        iter_tok = self._consume(TokenType.IDENTIFIER, "Expected iterator after 'for'.")
        self._consume(TokenType.IN, "Expected 'in' after iterator.")
        iterable = self._expression()
        self._consume(TokenType.LEFT_BRACE, "Expected '{' before for body.")
        body = self._block_body()
        end = self._previous()
        iter_node = VariableNode(name=iter_tok.lexeme, span=iter_tok.span)
        return ForStmtNode(iterator=iter_node, iterable=iterable, body=body,
                           span=self._make_span(start, end))

    def _while_stmt(self) -> WhileStmtNode:
        """解析 while 语句：while (expr) { ... }。"""
        start = self._previous()
        self._consume(TokenType.LEFT_PAREN, "Expected '(' after 'while'.")
        condition = self._expression()
        self._consume(TokenType.RIGHT_PAREN, "Expected ')' after while condition.")
        self._consume(TokenType.LEFT_BRACE, "Expected '{' before while body.")
        body = self._block_body()
        end = self._previous()
        return WhileStmtNode(condition=condition, body=body,
                             span=self._make_span(start, end))

    def _break_stmt(self) -> BreakStmtNode:
        """解析 break 语句。"""
        prev = self._previous()
        return BreakStmtNode(span=prev.span)

    def _continue_stmt(self) -> ContinueStmtNode:
        """解析 continue 语句。"""
        prev = self._previous()
        return ContinueStmtNode(span=prev.span)

    def _return_stmt(self) -> ReturnStmtNode:
        """解析 return 语句。"""
        start = self._previous()
        value: ExpressionNode | None = None
        if not self._check(TokenType.SEMICOLON, TokenType.RIGHT_BRACE, TokenType.EOF):
            value = self._expression()
        return ReturnStmtNode(value=value, span=start.span)

    def _expr_stmt(self) -> StatementNode:
        """解析表达式语句。"""
        expr = self._expression()
        self._match(TokenType.SEMICOLON)
        # Wrap expression in a statement-compatible node for Phase 0
        from .ast import ExprStmtNode
        return ExprStmtNode(expression=expr, span=expr.span)  # type: ignore[return-value]

    def _agent_decl(self) -> AgentDeclNode:
        """解析 Agent 声明：agent Name(params?) { decl* prompt? main? }。"""
        name_tok = self._consume(TokenType.IDENTIFIER, "Expected agent name after 'agent'.")
        # Optional parameter list (HLD 3.3.6)
        params: list[AgentParamNode] = []
        if self._check(TokenType.LEFT_PAREN):
            self._advance()
            if not self._check(TokenType.RIGHT_PAREN):
                params.append(self._agent_param())
                while self._match(TokenType.COMMA):
                    if self._check(TokenType.RIGHT_PAREN):
                        break
                    params.append(self._agent_param())
            self._consume(TokenType.RIGHT_PAREN, "Expected ')' after agent parameters.")
        self._consume(TokenType.LEFT_BRACE, "Expected '{' after agent name.")
        declarations: list[DeclarationNode] = []
        prompt: PromptDefNode | None = None
        logic: StatementNode | None = None
        while not self._check(TokenType.RIGHT_BRACE, TokenType.EOF):
            if self._match(TokenType.PROMPT):
                if self._match(TokenType.STRING, TokenType.TRIPLE_QUOTE_STRING):
                    content = self._previous().literal or ""
                else:
                    content = ""
                    self._error("Expected string after 'prompt'.")
                prompt = PromptDefNode(content=content, span=self._previous().span)
            elif self._match(TokenType.MAIN):
                logic = self._main_block()
            elif self._match(TokenType.FN):
                self._function_decl()
            elif self._check(
                TokenType.DESCRIPTION, TokenType.MODEL, TokenType.TOOLS,
                TokenType.SKILLS, TokenType.MEMORY, TokenType.TEMPERATURE,
                TokenType.MAX_TURNS, TokenType.SUB_AGENTS,
            ):
                declarations.append(self._declaration_block())
            else:
                self._error(f"Unexpected token in agent body: {self._current().type.name}")
                self._synchronize()
        end = self._consume(TokenType.RIGHT_BRACE, "Expected '}' after agent body.")
        return AgentDeclNode(name=name_tok.lexeme, params=params,
                             declarations=declarations, prompt=prompt, logic=logic,
                             span=self._make_span(name_tok, end))

    def _agent_param(self) -> AgentParamNode:
        """解析 Agent 参数: name: Type? = expr?。"""
        name_tok = self._consume(TokenType.IDENTIFIER, "Expected parameter name.")
        type_annotation: TypeNode | None = None
        default_value: ExpressionNode | None = None
        if self._match(TokenType.COLON):
            type_annotation = self._parse_type()
        if self._match(TokenType.ASSIGN):
            default_value = self._expression()
        end = self._previous()
        return AgentParamNode(name=name_tok.lexeme, type_annotation=type_annotation,
                              default_value=default_value,
                              span=self._make_span(name_tok, end))

    def _declaration_block(self) -> DeclarationNode:
        """Parse a config declaration: description "..." / model "..." / tools [...] etc."""
        start = self._advance()  # consume the config keyword
        token_type = start.type
        # Parse the value
        if self._check(TokenType.STRING, TokenType.TRIPLE_QUOTE_STRING):
            self._advance()
            value_tok = self._previous()
            value: ExpressionNode = LiteralNode(
                value=value_tok.literal, span=value_tok.span
            )
        elif self._check(TokenType.NUMBER):
            self._advance()
            value_tok = self._previous()
            value = LiteralNode(
                value=value_tok.literal, span=value_tok.span
            )
        elif self._check(TokenType.LEFT_BRACKET):
            # tools/skills/sub_agents list: [ "a", "b" ]
            self._advance()
            items: list[str] = []
            while not self._check(TokenType.RIGHT_BRACKET, TokenType.EOF):
                if self._check(TokenType.STRING, TokenType.TRIPLE_QUOTE_STRING):
                    self._advance()
                    items.append(self._previous().literal or "")
                if self._check(TokenType.COMMA):
                    self._advance()
                else:
                    break
            if self._check(TokenType.RIGHT_BRACKET):
                self._advance()
            value = LiteralNode(value=items, span=self._make_span(start, self._previous()))
        else:
            self._error(f"Expected value after '{start.lexeme}'.")
            value = LiteralNode(value=None, span=start.span)

        end = self._previous()
        span = self._make_span(start, end)

        # Map token type to DeclarationNode field
        field_map = {
            TokenType.DESCRIPTION: "description",
            TokenType.MODEL: "model",
            TokenType.TOOLS: "tools",
            TokenType.SKILLS: "skills",
            TokenType.SUB_AGENTS: "sub_agents",
            TokenType.MEMORY: "memory",
            TokenType.TEMPERATURE: "temperature",
            TokenType.MAX_TURNS: "max_turns",
        }
        field_name = field_map.get(token_type)

        return DeclarationNode(
            description=value if field_name == "description" else None,
            model=value if field_name == "model" else None,
            tools=value if field_name == "tools" else None,
            skills=value if field_name == "skills" else None,
            sub_agents=value if field_name == "sub_agents" else None,
            memory=value if field_name == "memory" else None,
            temperature=value if field_name == "temperature" else None,
            max_turns=value if field_name == "max_turns" else None,
            span=span,
        )

    def _prompt_def(self) -> PromptDefNode:
        """解析 prompt 定义。"""
        self._advance()  # consume PROMPT
        if self._match(TokenType.STRING, TokenType.TRIPLE_QUOTE_STRING):
            content = self._previous().literal or ""
        else:
            content = ""
            self._error("Expected string after 'prompt'.")
        return PromptDefNode(content=content, span=self._previous().span)

    def _main_block(self) -> MainBlockNode:
        """解析 main 块：main { stmt* }。"""
        start = self._previous()  # _match already consumed MAIN
        self._consume(TokenType.LEFT_BRACE, "Expected '{' after 'main'.")
        body: list[StatementNode] = []
        while not self._check(TokenType.RIGHT_BRACE, TokenType.EOF):
            prev_pos = self._pos
            stmt = self._statement()
            if stmt is not None:
                body.append(stmt)
            if self._pos == prev_pos:
                break
        end = self._consume(TokenType.RIGHT_BRACE, "Expected '}' after main block.")
        return MainBlockNode(body=body, span=self._make_span(start, end))

    def _block_body(self) -> StatementNode:
        """解析块体：{ stmt* }，返回 MainBlockNode。"""
        start = self._previous()
        body: list[StatementNode] = []
        while not self._check(TokenType.RIGHT_BRACE, TokenType.EOF,
                              TokenType.CATCH, TokenType.FINALLY,
                              TokenType.CASE, TokenType.DEFAULT,
                              TokenType.BRANCH, TokenType.OPTION):
            prev_pos = self._pos
            stmt = self._statement()
            if stmt is not None:
                body.append(stmt)
            if self._pos == prev_pos:
                # No progress made, break to avoid infinite loop
                break
        end = self._consume(TokenType.RIGHT_BRACE, "Expected '}'")
        return MainBlockNode(body=body, span=self._make_span(start, end))  # type: ignore[return-value]

    def _function_decl(self) -> FunctionDeclNode:
        """解析函数声明：fn name(params) -> type { stmt* }。"""
        start = self._previous()
        name_tok = self._consume(TokenType.IDENTIFIER, "Expected function name.")
        self._consume(TokenType.LEFT_PAREN, "Expected '(' after function name.")
        params: list[AgentParamNode] = []
        if not self._check(TokenType.RIGHT_PAREN):
            params.append(self._agent_param())
            while self._match(TokenType.COMMA):
                if self._check(TokenType.RIGHT_PAREN):
                    break
                params.append(self._agent_param())
        self._consume(TokenType.RIGHT_PAREN, "Expected ')' after parameters.")
        ret_type: TypeNode | None = None
        if self._match(TokenType.ARROW):
            ret_type = self._parse_type()
        self._consume(TokenType.LEFT_BRACE, "Expected '{' before function body.")
        body_stmts: list[StatementNode] = []
        while not self._check(TokenType.RIGHT_BRACE, TokenType.EOF,
                              TokenType.PROMPT, TokenType.MAIN, TokenType.FN,
                              TokenType.DESCRIPTION, TokenType.MODEL, TokenType.TOOLS,
                              TokenType.SKILLS, TokenType.MEMORY, TokenType.TEMPERATURE,
                              TokenType.MAX_TURNS, TokenType.SUB_AGENTS):
            prev_pos = self._pos
            s = self._statement()
            if s is not None:
                body_stmts.append(s)
            if self._pos == prev_pos:
                break
        end = self._consume(TokenType.RIGHT_BRACE, "Expected '}' after function body.")
        fn_body = FnBlockNode(body=body_stmts, span=self._make_span(self._previous(), end))
        return FunctionDeclNode(name=name_tok.lexeme, params=params,
                                return_type=ret_type, body=fn_body,
                                span=self._make_span(start, end))

    def _import_stmt(self) -> ImportStmtNode:
        """解析 import 语句：import "path" as alias。"""
        start = self._previous()
        path_tok = self._consume(TokenType.STRING, "Expected string path after 'import'.")
        alias: str | None = None
        if self._match(TokenType.AS):
            alias_tok = self._consume(TokenType.IDENTIFIER, "Expected alias after 'as'.")
            alias = alias_tok.lexeme
        end = self._previous()
        return ImportStmtNode(module_path=path_tok.literal or path_tok.lexeme, alias=alias,
                              span=self._make_span(start, end))

    def _parse_type(self) -> TypeNode:
        """解析类型：T?, A|B, Literal[...]。"""
        start = self._current()
        # Check for union type first: parse first type, then look for |
        first = self._simple_type()
        if self._match(TokenType.PIPE):
            # Union type
            members: list[TypeNode] = [first]
            while True:
                member = self._simple_type()
                members.append(member)
                if not self._match(TokenType.PIPE):
                    break
            end = self._previous()
            return UnionTypeNode(members=members,
                                 span=self._make_span(start, end))
        return first

    def _simple_type(self) -> TypeNode:
        """解析简单类型或可选类型: IDENTIFIER 或 IDENTIFIER?。"""
        name_tok = self._consume(TokenType.IDENTIFIER, "Expected type name.")
        base = TypeNode(name=name_tok.lexeme, span=name_tok.span)
        # Check for optional: T?
        if self._check(TokenType.QUESTION):
            q = self._advance()
            return OptionalTypeNode(inner=base, span=self._make_span(name_tok, q))
        return base

    def _llm_if_stmt(self) -> LlmIfStmtNode:
        """解析 llm if 语句：llm if "desc" { branch "cond" { ... } default { ... } }。"""
        start = self._previous()  # LLM token
        self._consume(TokenType.IF, "Expected 'if' after 'llm'.")
        desc_tok = self._consume(TokenType.STRING, "Expected description after 'llm if'.")
        self._consume(TokenType.LEFT_BRACE, "Expected '{' after llm if description.")
        branches: list[LlmBranchNode] = []
        while not self._check(TokenType.RIGHT_BRACE, TokenType.EOF):
            if self._check(TokenType.BRANCH):
                branches.append(self._llm_branch())
            elif self._check(TokenType.DEFAULT):
                # default branch (no condition)
                self._advance()
                self._consume(TokenType.LEFT_BRACE, "Expected '{' after default.")
                body = self._block_body_list()
                self._consume(TokenType.RIGHT_BRACE, "Expected '}' after default body.")
                branches.append(LlmBranchNode(condition=None, body=body,
                                              span=self._make_span(self._previous(), self._previous())))
            else:
                self._error(f"Expected 'branch' or 'default', got {self._current().type.name}")
                self._synchronize()
        self._consume(TokenType.RIGHT_BRACE, "Expected '}' after llm if body.")
        end = self._previous()
        return LlmIfStmtNode(description=desc_tok.literal or desc_tok.lexeme, branches=branches,
                             span=self._make_span(start, end))

    def _llm_branch(self) -> LlmBranchNode:
        """解析 branch 子句：branch "condition" { ... }。"""
        start = self._advance()  # consume BRANCH
        cond = self._expression()
        self._consume(TokenType.LEFT_BRACE, "Expected '{' after branch condition.")
        body = self._block_body_list()
        self._consume(TokenType.RIGHT_BRACE, "Expected '}' after branch body.")
        return LlmBranchNode(condition=cond, body=body,
                             span=self._make_span(start, self._previous()))

    def _llm_choose_stmt(self) -> LlmChooseStmtNode:
        """解析 llm choose 语句：llm choose "desc" { option "label" { ... } default { ... } }。"""
        start = self._previous()  # LLM token
        self._consume(TokenType.CHOOSE, "Expected 'choose' after 'llm'.")
        desc_tok = self._consume(TokenType.STRING, "Expected description after 'llm choose'.")
        self._consume(TokenType.LEFT_BRACE, "Expected '{' after llm choose description.")
        options: list[LlmOptionNode] = []
        default: list[StatementNode] = []
        while not self._check(TokenType.RIGHT_BRACE, TokenType.EOF):
            if self._check(TokenType.OPTION):
                options.append(self._llm_option())
            elif self._check(TokenType.DEFAULT):
                self._advance()
                self._consume(TokenType.LEFT_BRACE, "Expected '{' after default.")
                default = self._block_body_list()
                self._consume(TokenType.RIGHT_BRACE, "Expected '}' after default body.")
            else:
                self._error(f"Expected 'option' or 'default', got {self._current().type.name}")
                self._synchronize()
        self._consume(TokenType.RIGHT_BRACE, "Expected '}' after llm choose body.")
        end = self._previous()
        return LlmChooseStmtNode(description=desc_tok.literal or desc_tok.lexeme,
                                 options=options, default=default,
                                 span=self._make_span(start, end))

    def _llm_option(self) -> LlmOptionNode:
        """解析 option 子句：option "label" { ... }。"""
        start = self._advance()  # consume OPTION
        label_tok = self._consume(TokenType.STRING, "Expected label after 'option'.")
        self._consume(TokenType.LEFT_BRACE, "Expected '{' after option label.")
        body = self._block_body_list()
        self._consume(TokenType.RIGHT_BRACE, "Expected '}' after option body.")
        return LlmOptionNode(label=label_tok.literal or label_tok.lexeme, body=body,
                             span=self._make_span(start, self._previous()))

    def _llm_act_stmt(self) -> LlmActStmtNode:
        """解析 llm act 语句：llm act target(arg1=val1, ...) "desc"。"""
        start = self._previous()  # LLM token
        self._consume(TokenType.ACT, "Expected 'act' after 'llm'.")
        target_tok = self._consume(TokenType.IDENTIFIER, "Expected target after 'llm act'.")
        args: dict[str, ExpressionNode] = {}
        if self._check(TokenType.LEFT_PAREN):
            self._advance()
            if not self._check(TokenType.RIGHT_PAREN):
                arg_name = self._consume(TokenType.IDENTIFIER, "Expected argument name.")
                self._consume(TokenType.ASSIGN, "Expected '=' after argument name.")
                args[arg_name.lexeme] = self._expression()
                while self._match(TokenType.COMMA):
                    if self._check(TokenType.RIGHT_PAREN):
                        break
                    arg_name = self._consume(TokenType.IDENTIFIER, "Expected argument name.")
                    self._consume(TokenType.ASSIGN, "Expected '=' after argument name.")
                    args[arg_name.lexeme] = self._expression()
            self._consume(TokenType.RIGHT_PAREN, "Expected ')' after arguments.")
        desc_tok = self._consume(TokenType.STRING, "Expected description after 'llm act' args.")
        return LlmActStmtNode(target=target_tok.lexeme, arguments=args,
                              description=desc_tok.literal or desc_tok.lexeme,
                              span=self._make_span(start, self._previous()))

    def _match_stmt(self) -> MatchStmtNode:
        """解析 match 语句：match expr { case pattern { ... } default { ... } }。"""
        start = self._previous()
        subject = self._expression()
        self._consume(TokenType.LEFT_BRACE, "Expected '{' after match subject.")
        cases: list[CaseNode] = []
        default: list[StatementNode] = []
        while not self._check(TokenType.RIGHT_BRACE, TokenType.EOF):
            if self._check(TokenType.CASE):
                cases.append(self._case())
            elif self._check(TokenType.DEFAULT):
                self._advance()
                self._consume(TokenType.LEFT_BRACE, "Expected '{' after default.")
                default = self._block_body_list()
                self._consume(TokenType.RIGHT_BRACE, "Expected '}' after default body.")
            else:
                self._error(f"Expected 'case' or 'default', got {self._current().type.name}")
                self._synchronize()
        self._consume(TokenType.RIGHT_BRACE, "Expected '}' after match body.")
        end = self._previous()
        return MatchStmtNode(subject=subject, cases=cases, default=default,
                             span=self._make_span(start, end))

    def _case(self) -> CaseNode:
        """解析 case 子句：case pattern { ... }。"""
        start = self._advance()  # consume CASE
        pattern = self._expression()
        self._consume(TokenType.LEFT_BRACE, "Expected '{' after case pattern.")
        body = self._block_body_list()
        self._consume(TokenType.RIGHT_BRACE, "Expected '}' after case body.")
        return CaseNode(pattern=pattern, body=body,
                        span=self._make_span(start, self._previous()))

    def _try_stmt(self) -> TryStmtNode:
        """解析 try 语句：try { ... } catch Type name { ... } catch { ... } finally { ... }。"""
        start = self._previous()
        self._consume(TokenType.LEFT_BRACE, "Expected '{' after 'try'.")
        body = self._block_body_list()
        self._consume(TokenType.RIGHT_BRACE, "Expected '}' after try body.")
        catch_clauses: list[CatchClauseNode] = []
        catch_all: CatchAllNode | None = None
        finally_block: FinallyBlockNode | None = None
        while self._check(TokenType.CATCH) or self._check(TokenType.FINALLY):
            if self._match(TokenType.CATCH):
                if self._check(TokenType.IDENTIFIER):
                    # Typed catch: catch Type name { ... }
                    catch_clauses.append(self._catch_clause())
                else:
                    # Catch-all: catch { ... }
                    catch_all = self._catch_all()
            elif self._match(TokenType.FINALLY):
                finally_block = self._finally_block()
        if not catch_clauses and catch_all is None and finally_block is None:
            self._error("Expected at least one 'catch' or 'finally' after 'try'.")
        end = self._previous()
        return TryStmtNode(body=body, catch_clauses=catch_clauses,
                           catch_all=catch_all, finally_block=finally_block,
                           span=self._make_span(start, end))

    def _catch_clause(self) -> CatchClauseNode:
        """解析类型 catch：catch Type name { ... }。"""
        start = self._previous()  # CATCH token
        error_type = self._parse_type()
        error_name = self._consume(TokenType.IDENTIFIER, "Expected error variable name.")
        self._consume(TokenType.LEFT_BRACE, "Expected '{' after catch clause.")
        body = self._block_body_list()
        self._consume(TokenType.RIGHT_BRACE, "Expected '}' after catch body.")
        return CatchClauseNode(error_type=error_type, error_name=error_name.lexeme,
                               body=body, span=self._make_span(start, self._previous()))

    def _catch_all(self) -> CatchAllNode:
        """解析 catch-all：catch { ... }。"""
        start = self._previous()  # CATCH token
        self._consume(TokenType.LEFT_BRACE, "Expected '{' after catch.")
        body = self._block_body_list()
        self._consume(TokenType.RIGHT_BRACE, "Expected '}' after catch body.")
        return CatchAllNode(body=body, span=self._make_span(start, self._previous()))

    def _finally_block(self) -> FinallyBlockNode:
        """解析 finally：finally { ... }。（FINALLY 已由 _match 消费）"""
        start = self._previous()  # FINALLY token (already consumed)
        self._consume(TokenType.LEFT_BRACE, "Expected '{' after finally.")
        body = self._block_body_list()
        self._consume(TokenType.RIGHT_BRACE, "Expected '}' after finally body.")
        return FinallyBlockNode(body=body, span=self._make_span(start, self._previous()))

    def _block_body_list(self) -> list[StatementNode]:
        """解析块体内的语句列表（不带外层的 { }）。"""
        body: list[StatementNode] = []
        while not self._check(TokenType.RIGHT_BRACE, TokenType.EOF,
                              TokenType.CATCH, TokenType.FINALLY,
                              TokenType.CASE, TokenType.DEFAULT,
                              TokenType.BRANCH, TokenType.OPTION):
            prev_pos = self._pos
            stmt = self._statement()
            if stmt is not None:
                body.append(stmt)
            if self._pos == prev_pos:
                # No progress made, break to avoid infinite loop
                break
        return body

    # Token 消费辅助
    def _consume(self, tt: TokenType, message: str) -> Token:
        """消费指定类型的 Token，否则报错。"""
        if self._check(tt):
            return self._advance()
        self._error(message)
        peek = self._peek()
        return Token(type=tt, lexeme="<missing>", literal=None,
                     line=peek.line, col=peek.col,
                     end_line=peek.line, end_col=peek.col, file=peek.file)

    def _check(self, *types: TokenType) -> bool:
        """检查当前 Token 类型是否匹配任一。"""
        if self._at_end():
            return TokenType.EOF in types
        return self._current().type in types

    def _peek(self) -> Token:
        """查看当前 Token（不消费）。"""
        return self._current()

    def _previous(self) -> Token:
        """返回上一个消费的 Token。"""
        return self.tokens[self._pos - 1]

    def _advance(self) -> Token:
        """前进到下一个 Token，返回之前消费的。"""
        if not self._at_end():
            self._pos += 1
        return self._previous()

    def _match(self, *types: TokenType) -> bool:
        """如果当前 Token 匹配，则消费并返回 True。"""
        for t in types:
            if self._check(t):
                self._advance()
                return True
        return False

    def _error(self, message: str) -> None:
        """报告解析错误。"""
        tok = self._peek()
        span = SourceSpan(tok.file, tok.line, tok.col, tok.end_line, tok.end_col)
        self.errors.error(ErrorCode.PARSER_ERROR, message, span)

    def _synchronize(self) -> None:
        """Panic mode 错误恢复：跳过到同步点。"""
        self._advance()
        while not self._at_end():
            if self._previous().type == TokenType.SEMICOLON:
                return
            if self._check(TokenType.AGENT, TokenType.FN, TokenType.MAIN,
                           TokenType.IF, TokenType.FOR, TokenType.WHILE,
                           TokenType.RETURN, TokenType.BREAK, TokenType.CONTINUE,
                           TokenType.LET, TokenType.CONST, TokenType.RIGHT_BRACE):
                return
            self._advance()

    def _at_end(self) -> bool:
        """是否到达 Token 流末尾。"""
        return self._current().type == TokenType.EOF

    def _current(self) -> Token:
        """返回当前 Token。"""
        return self.tokens[self._pos]

    def _make_span(self, start: Token | SourceSpan, end: Token) -> SourceSpan:
        """从起始和结束 Token 构建 SourceSpan。"""
        if isinstance(start, SourceSpan):
            return SourceSpan(start.file, start.start_line, start.start_col, end.end_line, end.end_col)
        return SourceSpan(start.file, start.line, start.col, end.end_line, end.end_col)
