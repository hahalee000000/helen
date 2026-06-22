"""helen/core/parser.py — Helen Pratt precedence parser + recursive descent."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional

from .source import SourceSpan
from .ast import (
    ASTNode,
    AgentDeclNode,
    AgentParamNode,
    AssertStmtNode,
    AsyncCallStmtNode,
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
    ForAwaitStmtNode,
    FunctionDeclNode,
    GroupingNode,
    IfStmtNode,
    ImportStmtNode,
    LambdaNode,
    ListLiteralNode,
    LlmActExprNode,
    LlmBranchNode,
    LlmIfStmtNode,
    LlmStreamStmtNode,
    LiteralNode,
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
    WildcardPatternNode,
    WhileStmtNode,
    IndexNode,
    AccessNode,
    BinaryOpNode,
    AsyncCallExprNode,
)
from .errors import ErrorCode, ErrorReporter
from .tokens import Token, TokenType

# Tokens that indicate the end of an expression (for bare form detection)
# Used in llm act/llm if/llm stream to detect when no prompt expression follows
BARE_FORM_TOKENS = (
    TokenType.RIGHT_BRACE, TokenType.SEMICOLON, TokenType.EOF,
    # Statement keywords that indicate the current statement has ended
    TokenType.RETURN, TokenType.LET, TokenType.CONST,
    TokenType.IF, TokenType.FOR, TokenType.WHILE,
    TokenType.BREAK, TokenType.CONTINUE, TokenType.MATCH,
    TokenType.TRY, TokenType.THROW,
    TokenType.LLM, TokenType.ASYNC,
)

PrefixParseFn = Callable[["Parser"], ExpressionNode]
InfixParseFn = Callable[["Parser", ExpressionNode], ExpressionNode]


class Precedence:
    """Pratt parsing precedence levels (higher value = tighter binding)."""
    NONE = 0
    ASSIGNMENT = 1
    PIPE = 2          # |> pipe operator
    OR = 3
    AND = 4
    EQUALITY = 5
    COMPARISON = 6
    TERM = 7
    FACTOR = 8
    UNARY = 9
    AWAIT = 10
    CALL = 11


@dataclass
class ParseFn:
    """Pratt parsing rule for a single TokenType."""
    prefix: Optional[PrefixParseFn] = None
    infix: Optional[InfixParseFn] = None
    precedence: int = Precedence.NONE


class Parser:
    """Helen Pratt precedence parser + recursive descent."""

    # Class-level cache for Pratt rules to avoid re-registration
    _PRATT_RULES_CACHE: dict[TokenType, ParseFn] | None = None

    def __init__(self, tokens: list[Token], errors: ErrorReporter | None = None):
        """Initialize the Parser.
        Args:
            tokens: Token list produced by the lexer
            errors: Error reporter (optional)
        """
        self.tokens = tokens
        self.errors = errors or ErrorReporter()
        self._pos = 0
        self._rules: dict[TokenType, ParseFn] = {}
        self._register_pratt_rules()

    def parse(self) -> ProgramNode:
        """Parse the token stream and return a ProgramNode."""
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
        """Register Pratt parsing rules.
        
        Note: Cannot cache rules at class level because they contain bound methods
        (self._literal_number, etc.) that are specific to each Parser instance.
        """
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

        # llm act as expression: llm act <prompt_expr>
        self._rules[TokenType.LLM].prefix = self._llm_act_expr

        # async as expression: async Agent(...)
        self._rules[TokenType.ASYNC].prefix = self._async_call_expr

        # lambda as expression: fn(params) { body }
        self._rules[TokenType.FN].prefix = self._lambda_expr

        # match as expression: match expr { case ... { value } ... }
        self._rules[TokenType.MATCH].prefix = self._match_expr

        # Precedence for prefix operators
        self._rules[TokenType.BANG].precedence = Precedence.UNARY
        self._rules[TokenType.MINUS].precedence = Precedence.UNARY
        self._rules[TokenType.AWAIT].precedence = Precedence.AWAIT
        self._rules[TokenType.ASYNC].precedence = Precedence.UNARY

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

        # Pipe operator: |> (left-associative, low precedence)
        self._rules[TokenType.PIPE_RIGHT].infix = self._pipe
        self._rules[TokenType.PIPE_RIGHT].precedence = Precedence.PIPE

    def _expression(self, precedence: int = Precedence.NONE) -> ExpressionNode:
        """Pratt core: parse an expression."""
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
        """Parse a number literal."""
        prev = self._previous()
        return LiteralNode(value=prev.literal, span=prev.span)

    def _literal_string(self) -> ExpressionNode:
        """Parse a string literal."""
        prev = self._previous()
        return LiteralNode(value=prev.literal, span=prev.span)

    def _literal_bool(self) -> ExpressionNode:
        """Parse a boolean literal."""
        prev = self._previous()
        return LiteralNode(value=prev.literal, span=prev.span)

    def _literal_null(self) -> ExpressionNode:
        """Parse a null literal."""
        prev = self._previous()
        return LiteralNode(value=None, span=prev.span)

    def _identifier(self) -> ExpressionNode:
        """Parse an identifier as a variable node."""
        prev = self._previous()
        return VariableNode(name=prev.lexeme, span=prev.span)

    def _llm_act_expr(self) -> ExpressionNode:
        """Parse an llm act expression: llm act <expression>?

        Supports bare ``llm act`` (no expression) inside an agent context,
        where the agent's rendered prompt template is used automatically.

        Bare form detection:
        - Statement terminators: }, ;, EOF
        - Statement keywords: return, let, if, for, etc.
        - Newline: if the next token is on a different line than 'act'
        """
        start = self._previous()  # LLM token
        self._consume(TokenType.ACT, "Expected 'act' after 'llm'.")
        act_token = self._previous()

        # Check if there's an expression following 'llm act'.
        # If we hit a statement terminator or a new statement keyword, treat as bare form.
        if self._check(*BARE_FORM_TOKENS):
            prompt_expr = None
        # Newline check: if next token is on a different line, treat as bare form
        # This handles: let result = llm act\nprint(...)
        elif self._current().line > act_token.line:
            prompt_expr = None
        else:
            prompt_expr = self._expression()
        return LlmActExprNode(
            prompt=prompt_expr,
            span=self._make_span(start, self._previous())
        )

    def _grouping(self) -> ExpressionNode:
        """Parse a grouping expression (expr)."""
        expr = self._expression()
        end = self._consume(TokenType.RIGHT_PAREN, "Expected ')' after expression.")
        return GroupingNode(expression=expr, span=self._make_span(expr.span if hasattr(expr, 'span') else self._previous(), end))

    def _unary(self) -> ExpressionNode:
        """Parse a unary expression."""
        operator = self._previous()
        right = self._expression(Precedence.UNARY)
        return UnaryOpNode(operator=operator, operand=right,
                           span=self._make_span(operator, self._previous()))

    def _binary(self, left: ExpressionNode) -> ExpressionNode:
        """Parse a binary expression."""
        operator = self._previous()
        rule = self._rules.get(operator.type, ParseFn())
        right = self._expression(rule.precedence + 1)
        return BinaryOpNode(left=left, operator=operator, right=right,
                            span=self._make_span(operator, self._previous()))

    def _pipe(self, left: ExpressionNode) -> ExpressionNode:
        """Parse a pipe expression: value |> fn."""
        operator = self._previous()  # PIPE_RIGHT token
        rule = self._rules.get(TokenType.PIPE_RIGHT, ParseFn())
        right = self._expression(rule.precedence + 1)  # left-associative
        return PipeExprNode(value=left, function=right,
                            span=self._make_span(operator, self._previous()))

    def _call(self, callee: ExpressionNode) -> ExpressionNode:
        """Parse a function call callee(args)."""
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
        """Parse an index access target[index]."""
        index = self._expression()
        bracket = self._consume(TokenType.RIGHT_BRACKET, "Expected ']' after index.")
        return IndexNode(target=target, index=index,
                         span=self._make_span(target.span if hasattr(target, 'span') else self._previous(), bracket))

    def _access(self, target: ExpressionNode) -> ExpressionNode:
        """Parse a member access target.property."""
        prop = self._consume(TokenType.IDENTIFIER, "Expected property name after '.'.")
        return AccessNode(target=target, property=prop.lexeme,
                          span=self._make_span(target.span if hasattr(target, 'span') else self._previous(), prop))

    def _list_literal(self) -> ExpressionNode:
        """Parse a list literal: [expr, ...]."""
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
        """Parse a map literal: {key: value, ...}."""
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
        """Parse a single map entry: key: value."""
        key = self._expression()
        self._consume(TokenType.COLON, "Expected ':' after map key.")
        value = self._expression()
        return MapEntryNode(key=key, value=value,
                            span=self._make_span(key.span if hasattr(key, 'span') else self._previous(), self._previous()))

    def _template_ref(self) -> ExpressionNode:
        """Parse a template reference: {{expr}}."""
        start = self._previous()
        expr = self._expression()
        end = self._consume(TokenType.TEMPLATE_CLOSE, "Expected '}}' to close template.")
        return TemplateRefNode(expression=expr,
                               span=self._make_span(start, end))

    def _declaration(self) -> StatementNode | None:
        """Parse a top-level declaration."""
        if self._at_end():
            return None

        # Skip stray closing braces at top level (e.g. from unmatched blocks)
        if self._check(TokenType.RIGHT_BRACE):
            self._advance()
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
        if self._match(TokenType.THROW):
            return self._throw_stmt()
        if self._match(TokenType.ASSERT):
            return self._assert_stmt()
        if self._match(TokenType.MATCH):
            return self._match_stmt()
        if self._match(TokenType.PROTOCOL):
            return self._protocol_decl()
        if self._match(TokenType.IMPL):
            return self._impl_decl()

        # LLM keyword disambiguation (HLD 3.3.5)
        if self._check(TokenType.LLM):
            return self._llm_stmt()

        if self._at_end():
            return None
        return self._expr_stmt()

    def _llm_stmt(self) -> StatementNode:
        """Parse an llm statement: dispatch based on the next token (llm if / llm act / llm stream)."""
        self._advance()  # consume LLM
        if self._check(TokenType.IF):
            return self._llm_if_stmt()
        elif self._check(TokenType.ACT):
            return self._llm_act_stmt()
        elif self._check(TokenType.STREAM):
            return self._llm_stream_stmt()
        else:
            self._error("Expected 'if', 'act', or 'stream' after 'llm'.")
            self._synchronize()
            return None

    def _async_call_stmt(self) -> AsyncCallStmtNode:
        """Parse an async statement modifier: async AgentName(...) (HLD 3.3.3)."""
        start = self._advance()  # consume ASYNC
        # Parse as a call expression (no 'call' keyword needed)
        call_expr = self._expression(Precedence.NONE)
        if not isinstance(call_expr, CallNode):
            self._error("'async' must be followed by a function call.")
            return AsyncCallStmtNode(call=CallNode(callee=VariableNode(name="", span=start.span), arguments=[], span=start.span), span=start.span)
        return AsyncCallStmtNode(call=call_expr,
                                 span=self._make_span(start, self._previous()))

    def _async_call_expr(self) -> "AsyncCallExprNode":
        """Parse async as expression prefix: async Agent(...) -> Task."""
        start = self._previous()  # ASYNC already consumed by Pratt framework
        call_expr = self._expression(Precedence.NONE)
        if not isinstance(call_expr, CallNode):
            self._error("'async' must be followed by a function call.")
            return AsyncCallExprNode(call=CallNode(callee=VariableNode(name="", span=start.span), arguments=[], span=start.span), span=start.span)
        return AsyncCallExprNode(call=call_expr,
                                 span=self._make_span(start, self._previous()))

    def _statement(self) -> StatementNode | None:
        """Parse a single statement."""
        return self._declaration()

    def _var_decl(self) -> VarDeclNode:
        """Parse a variable declaration: let/const name = expr."""
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
        """Parse an if statement: if (cond) { ... } or if cond { ... }."""
        start = self._previous()
        # Parentheses are optional for if condition
        if self._match(TokenType.LEFT_PAREN):
            condition = self._expression()
            self._consume(TokenType.RIGHT_PAREN, "Expected ')' after if condition.")
        else:
            condition = self._expression()
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

    def _for_stmt(self) -> ForStmtNode | ForAwaitStmtNode:
        """Parse a for statement: for x in expr { ... } or for await x in expr { ... }."""
        start = self._previous()
        # Check for 'for await' syntax
        is_await = self._match(TokenType.AWAIT)
        iter_tok = self._consume(TokenType.IDENTIFIER, "Expected iterator after 'for'.")
        self._consume(TokenType.IN, "Expected 'in' after iterator.")
        iterable = self._expression()
        self._consume(TokenType.LEFT_BRACE, "Expected '{' before for body.")
        body = self._block_body()
        end = self._previous()
        iter_node = VariableNode(name=iter_tok.lexeme, span=iter_tok.span)
        if is_await:
            return ForAwaitStmtNode(iterator=iter_node, iterable=iterable, body=body,
                                    span=self._make_span(start, end))
        return ForStmtNode(iterator=iter_node, iterable=iterable, body=body,
                           span=self._make_span(start, end))

    def _while_stmt(self) -> WhileStmtNode:
        """Parse a while statement: while (cond) { ... } or while cond { ... }."""
        start = self._previous()
        # Parentheses are optional for while condition
        if self._match(TokenType.LEFT_PAREN):
            condition = self._expression()
            self._consume(TokenType.RIGHT_PAREN, "Expected ')' after while condition.")
        else:
            condition = self._expression()
        self._consume(TokenType.LEFT_BRACE, "Expected '{' before while body.")
        body = self._block_body()
        end = self._previous()
        return WhileStmtNode(condition=condition, body=body,
                             span=self._make_span(start, end))

    def _break_stmt(self) -> BreakStmtNode:
        """Parse a break statement."""
        prev = self._previous()
        return BreakStmtNode(span=prev.span)

    def _continue_stmt(self) -> ContinueStmtNode:
        """Parse a continue statement."""
        prev = self._previous()
        return ContinueStmtNode(span=prev.span)

    def _return_stmt(self) -> ReturnStmtNode:
        """Parse a return statement."""
        start = self._previous()
        value: ExpressionNode | None = None
        if not self._check(TokenType.SEMICOLON, TokenType.RIGHT_BRACE, TokenType.EOF):
            value = self._expression()
        self._match(TokenType.SEMICOLON)
        return ReturnStmtNode(value=value, span=start.span)

    def _expr_stmt(self) -> StatementNode:
        """Parse an expression statement."""
        expr = self._expression()
        self._match(TokenType.SEMICOLON)
        # Wrap expression in a statement-compatible node for Phase 0
        from .ast import ExprStmtNode
        return ExprStmtNode(expression=expr, span=expr.span)  # type: ignore[return-value]

    def _agent_decl(self) -> AgentDeclNode:
        """Parse an agent declaration: agent Name(params?) { decl* prompt? main? }."""
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
        agent_functions: list = []
        agent_function_vars: list = []
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
            elif self._match(TokenType.FUNCTIONS):
                # Parse functions { fn ... / let ... / const ... } block
                self._consume(TokenType.LEFT_BRACE, "Expected '{' after 'functions'.")
                while not self._check(TokenType.RIGHT_BRACE, TokenType.EOF):
                    if self._match(TokenType.FN):
                        agent_functions.append(self._function_decl())
                    elif self._check(TokenType.LET, TokenType.CONST):
                        self._advance()  # consume let/const
                        agent_function_vars.append(self._var_decl())
                    else:
                        self._error(f"Expected 'fn', 'let', or 'const' inside functions block, got {self._current().type.name}")
                        self._synchronize()
                self._consume(TokenType.RIGHT_BRACE, "Expected '}' after functions block.")
            elif self._check(
                TokenType.DESCRIPTION, TokenType.MODEL, TokenType.TOOLS,
                TokenType.MEMORY, TokenType.TEMPERATURE,
                TokenType.MAX_TURNS, TokenType.SUB_AGENTS, TokenType.STREAMING,
            ) or self._is_context_keyword("memory"):
                declarations.append(self._declaration_block())
            else:
                self._error(f"Unexpected token in agent body: {self._current().type.name}")
                self._synchronize()
        end = self._consume(TokenType.RIGHT_BRACE, "Expected '}' after agent body.")
        return AgentDeclNode(name=name_tok.lexeme, params=params,
                             declarations=declarations, prompt=prompt, logic=logic,
                             span=self._make_span(name_tok, end),
                             functions=agent_functions,
                             function_vars=agent_function_vars)

    def _agent_param(self) -> AgentParamNode:
        """Parse an agent parameter: name: Type? = expr?."""
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
        """Parse a config declaration: description "..." / model "..." / tools [...] / streaming true etc."""
        start = self._advance()  # consume the config keyword
        token_type = start.type

        # Handle context keyword "memory" (v1.6)
        if token_type == TokenType.IDENTIFIER and start.lexeme == "memory":
            token_type = TokenType.MEMORY

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
        elif self._check(TokenType.TRUE, TokenType.FALSE):
            # Boolean value for streaming
            self._advance()
            value_tok = self._previous()
            value = LiteralNode(
                value=value_tok.type == TokenType.TRUE, span=value_tok.span
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
            TokenType.SUB_AGENTS: "sub_agents",
            TokenType.MEMORY: "memory",
            TokenType.TEMPERATURE: "temperature",
            TokenType.MAX_TURNS: "max_turns",
            TokenType.STREAMING: "streaming",
        }
        field_name = field_map.get(token_type)

        streaming_value = False
        if field_name == "streaming" and isinstance(value, LiteralNode):
            streaming_value = bool(value.value)

        return DeclarationNode(
            description=value if field_name == "description" else None,
            model=value if field_name == "model" else None,
            tools=value if field_name == "tools" else None,
            sub_agents=value if field_name == "sub_agents" else None,
            memory=value if field_name == "memory" else None,
            temperature=value if field_name == "temperature" else None,
            max_turns=value if field_name == "max_turns" else None,
            streaming=streaming_value,
            span=span,
        )

    def _prompt_def(self) -> PromptDefNode:
        """Parse a prompt definition."""
        self._advance()  # consume PROMPT
        if self._match(TokenType.STRING, TokenType.TRIPLE_QUOTE_STRING):
            content = self._previous().literal or ""
        else:
            content = ""
            self._error("Expected string after 'prompt'.")
        return PromptDefNode(content=content, span=self._previous().span)

    def _main_block(self) -> MainBlockNode:
        """Parse a main block: main { stmt* }."""
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
        """Parse a block body: { stmt* }, returns a MainBlockNode."""
        start = self._previous()
        body: list[StatementNode] = []
        while not self._check(TokenType.RIGHT_BRACE, TokenType.EOF,
                              TokenType.CATCH, TokenType.FINALLY,
                              TokenType.CASE, TokenType.DEFAULT,
                              TokenType.BRANCH):
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
        """Parse a function declaration: fn name(params) -> type { stmt* }."""
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
        if self._match(TokenType.ARROW) or self._match(TokenType.COLON):
            ret_type = self._parse_type()
        self._consume(TokenType.LEFT_BRACE, "Expected '{' before function body.")
        body_stmts: list[StatementNode] = []
        while not self._check(TokenType.RIGHT_BRACE, TokenType.EOF,
                              TokenType.PROMPT, TokenType.MAIN, TokenType.FN,
                              TokenType.DESCRIPTION, TokenType.MODEL, TokenType.TOOLS,
                              TokenType.MEMORY, TokenType.TEMPERATURE,
                              TokenType.MAX_TURNS, TokenType.SUB_AGENTS):
            # Also check for context keyword "memory" (v1.6)
            if self._is_context_keyword("memory"):
                break
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

    def _lambda_expr(self) -> LambdaNode:
        """Parse a lambda expression: fn(params) { body }.

        Anonymous function that can be assigned to variables or passed as arguments.
        """
        start = self._previous()  # FN token
        # Parse parameters (same as function declaration)
        self._consume(TokenType.LEFT_PAREN, "Expected '(' after 'fn'.")
        params: list[AgentParamNode] = []
        if not self._check(TokenType.RIGHT_PAREN):
            params.append(self._agent_param())
            while self._match(TokenType.COMMA):
                if self._check(TokenType.RIGHT_PAREN):
                    break
                params.append(self._agent_param())
        self._consume(TokenType.RIGHT_PAREN, "Expected ')' after parameters.")

        # Optional return type
        ret_type: TypeNode | None = None
        if self._match(TokenType.ARROW) or self._match(TokenType.COLON):
            ret_type = self._parse_type()

        # Parse body
        self._consume(TokenType.LEFT_BRACE, "Expected '{' before lambda body.")
        body_stmts: list[StatementNode] = []
        while not self._check(TokenType.RIGHT_BRACE, TokenType.EOF):
            prev_pos = self._pos
            s = self._statement()
            if s is not None:
                body_stmts.append(s)
            if self._pos == prev_pos:
                break
        end = self._consume(TokenType.RIGHT_BRACE, "Expected '}' after lambda body.")
        fn_body = FnBlockNode(body=body_stmts, span=self._make_span(self._previous(), end))

        return LambdaNode(params=params, return_type=ret_type, body=fn_body,
                         span=self._make_span(start, end))

    def _protocol_decl(self) -> ProtocolDeclNode:
        """Parse a protocol declaration: protocol Name { fn signatures }.

        v1.7 feature for interface/protocol support.
        """
        start = self._previous()  # PROTOCOL token
        name_tok = self._consume(TokenType.IDENTIFIER, "Expected protocol name.")
        self._consume(TokenType.LEFT_BRACE, "Expected '{' after protocol name.")

        methods: list[FunctionDeclNode] = []
        while not self._check(TokenType.RIGHT_BRACE, TokenType.EOF):
            # Parse method signature (no body)
            self._consume(TokenType.FN, "Expected 'fn' in protocol.")
            method_name = self._consume(TokenType.IDENTIFIER, "Expected method name.")
            self._consume(TokenType.LEFT_PAREN, "Expected '(' after method name.")

            # Parse parameters
            params: list[AgentParamNode] = []
            if not self._check(TokenType.RIGHT_PAREN):
                params.append(self._agent_param())
                while self._match(TokenType.COMMA):
                    if self._check(TokenType.RIGHT_PAREN):
                        break
                    params.append(self._agent_param())
            self._consume(TokenType.RIGHT_PAREN, "Expected ')' after parameters.")

            # Parse return type
            ret_type: TypeNode | None = None
            if self._match(TokenType.ARROW) or self._match(TokenType.COLON):
                ret_type = self._parse_type()

            # Protocol methods have no body - just a signature
            # Create a minimal FnBlockNode with empty body
            empty_body = FnBlockNode(body=[], span=self._make_span(self._previous(), self._previous()))

            method = FunctionDeclNode(
                name=method_name.lexeme,
                params=params,
                return_type=ret_type,
                body=empty_body,
                span=self._make_span(start, self._previous())
            )
            methods.append(method)

        end = self._consume(TokenType.RIGHT_BRACE, "Expected '}' after protocol body.")
        return ProtocolDeclNode(
            name=name_tok.lexeme,
            methods=methods,
            span=self._make_span(start, end)
        )

    def _impl_decl(self) -> ImplDeclNode:
        """Parse a protocol implementation: impl Protocol for Struct { fn implementations }.

        v1.7 feature for interface/protocol support.
        """
        start = self._previous()  # IMPL token
        protocol_name = self._consume(TokenType.IDENTIFIER, "Expected protocol name.")
        self._consume(TokenType.FOR, "Expected 'for' after protocol name.")
        struct_name = self._consume(TokenType.IDENTIFIER, "Expected struct name.")
        self._consume(TokenType.LEFT_BRACE, "Expected '{' after struct name.")

        methods: list[FunctionDeclNode] = []
        while not self._check(TokenType.RIGHT_BRACE, TokenType.EOF):
            # Parse full function implementation
            if self._match(TokenType.FN):
                method = self._function_decl()
                methods.append(method)
            else:
                self._error("Expected 'fn' in impl block.")
                self._advance()

        end = self._consume(TokenType.RIGHT_BRACE, "Expected '}' after impl body.")
        return ImplDeclNode(
            protocol_name=protocol_name.lexeme,
            struct_name=struct_name.lexeme,
            methods=methods,
            span=self._make_span(start, end)
        )

    def _import_stmt(self) -> ImportStmtNode:
        """Parse an import statement: import "path" as alias."""
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
        """Parse a type: T?, A|B, Literal[...]."""
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
        """Parse a simple type or optional type: IDENTIFIER or IDENTIFIER?."""
        name_tok = self._consume(TokenType.IDENTIFIER, "Expected type name.")
        base = TypeNode(name=name_tok.lexeme, span=name_tok.span)
        # Check for optional: T?
        if self._check(TokenType.QUESTION):
            q = self._advance()
            return OptionalTypeNode(inner=base, span=self._make_span(name_tok, q))
        return base

    def _llm_if_stmt(self) -> LlmIfStmtNode:
        """Parse an llm if statement: llm if "desc" { branch "cond" { ... } default { ... } }."""
        start = self._previous()  # LLM token
        self._consume(TokenType.IF, "Expected 'if' after 'llm'.")
        desc_expr = self._expression()  # Parse expression instead of just STRING
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
        return LlmIfStmtNode(description=desc_expr, branches=branches,
                             span=self._make_span(start, end))

    def _llm_branch(self) -> LlmBranchNode:
        """Parse a branch clause: branch "condition" { ... }."""
        start = self._advance()  # consume BRANCH
        cond = self._expression()
        self._consume(TokenType.LEFT_BRACE, "Expected '{' after branch condition.")
        body = self._block_body_list()
        self._consume(TokenType.RIGHT_BRACE, "Expected '}' after branch body.")
        return LlmBranchNode(condition=cond, body=body,
                             span=self._make_span(start, self._previous()))

    def _llm_act_stmt(self) -> StatementNode:
        """Parse an llm act statement: only supports expression form.

        Syntax: llm act <expr>?
        - llm act "prompt" — direct LLM invocation
        - llm act — bare form, automatically uses the rendered prompt inside an agent

        Note: The statement form `llm act Agent(args) "desc"` is deprecated; use `call Agent(args)` instead.
        """
        start = self._previous()  # LLM token
        self._consume(TokenType.ACT, "Expected 'act' after 'llm'.")

        # 检查是否误用语句形式：llm act Agent(args) "desc"
        # 如果下一个 token 是 IDENTIFIER 且后面跟着 ( 或 STRING，报错
        if self._check(TokenType.IDENTIFIER):
            saved_pos = self._pos
            ident_tok = self._advance()
            if self._check(TokenType.LEFT_PAREN) or self._check(TokenType.STRING):
                self._error(
                    f"'llm act {ident_tok.lexeme}(...)' is deprecated. "
                    f"Use 'call {ident_tok.lexeme}(...)' instead."
                )
            self._pos = saved_pos

        # 解析表达式形式：llm act <expr>?
        # 检查是否有表达式
        if self._check(*BARE_FORM_TOKENS):
            prompt_expr = None
        elif self._current().line > start.line:
            # 换行边界
            prompt_expr = None
        else:
            prompt_expr = self._expression()

        return ExprStmtNode(
            expression=LlmActExprNode(prompt=prompt_expr,
                                      span=self._make_span(start, self._previous())),
            span=self._make_span(start, self._previous())
        )

    def _llm_stream_stmt(self) -> LlmStreamStmtNode:
        """Parse an llm stream statement: streaming LLM call.

        Syntax:
        - llm stream                             # bare form, automatically uses the rendered prompt inside an agent
        - llm stream "prompt"                    # automatically outputs to stdout
        - llm stream "prompt" on_chunk callback  # invokes callback(chunk)
        """
        start = self._previous()  # LLM token
        self._consume(TokenType.STREAM, "Expected 'stream' after 'llm'.")

        # 检查是否有表达式（支持 bare form）
        if self._check(*BARE_FORM_TOKENS):
            prompt_expr = None
        elif self._current().line > start.line:
            # 换行边界
            prompt_expr = None
        else:
            prompt_expr = self._expression()

        # 检查是否有 on_chunk 回调
        on_chunk_expr = None
        if prompt_expr is not None and self._check(TokenType.IDENTIFIER) and self._current().lexeme == "on_chunk":
            self._advance()  # consume 'on_chunk'
            on_chunk_expr = self._expression()

        return LlmStreamStmtNode(
            prompt=prompt_expr,
            on_chunk=on_chunk_expr,
            span=self._make_span(start, self._previous())
        )

    def _match_stmt(self) -> MatchStmtNode:
        """Parse a match statement: match expr { case pattern { ... } default { ... } }."""
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

    def _match_expr(self) -> MatchExprNode:
        """Parse a match expression: match expr { case pattern { expr } ... default { expr } }.

        Unlike match statement, each case body is a single expression whose
        value becomes the result of the match expression.

        Syntax:
            let result = match value {
                case 1 { "one" }
                case 2..5 { "few" }
                case x if x > 10 { "many" }
                default { "unknown" }
            }
        """
        start = self._previous()  # MATCH token
        subject = self._expression()
        self._consume(TokenType.LEFT_BRACE, "Expected '{' after match subject.")
        cases: list[CaseNode] = []
        default_body: ExpressionNode | None = None
        while not self._check(TokenType.RIGHT_BRACE, TokenType.EOF):
            if self._check(TokenType.CASE):
                case_start = self._advance()  # consume CASE

                # Parse pattern (reuse same logic as _case)
                if self._check(TokenType.WILDCARD):
                    wildcard_tok = self._advance()
                    pattern = WildcardPatternNode(span=self._make_span(wildcard_tok, wildcard_tok))
                elif self._check(TokenType.IS):
                    is_tok = self._advance()
                    type_tok = self._consume(TokenType.IDENTIFIER, "Expected type name after 'is'.")
                    binding_name = None
                    if self._check(TokenType.IDENTIFIER):
                        binding_tok = self._advance()
                        binding_name = binding_tok.lexeme
                    pattern = TypePatternNode(
                        type_name=type_tok.lexeme,
                        binding_name=binding_name,
                        span=self._make_span(is_tok, self._previous())
                    )
                else:
                    pattern = self._expression()
                    if isinstance(pattern, VariableNode):
                        if self._check(TokenType.IF) or self._check(TokenType.LEFT_BRACE):
                            pattern = VariablePatternNode(name=pattern.name, span=pattern.span)
                    if self._match(TokenType.DOTDOT):
                        pattern_start = pattern.span
                        end_expr = self._expression()
                        pattern = RangePatternNode(
                            start=pattern, end=end_expr,
                            span=SourceSpan(
                                pattern_start.file,
                                pattern_start.start_line, pattern_start.start_col,
                                end_expr.span.end_line, end_expr.span.end_col))

                guard = None
                if self._match(TokenType.IF):
                    guard = self._expression()

                self._consume(TokenType.LEFT_BRACE, "Expected '{' after case pattern.")
                # Expression body: parse a single expression
                body_expr = self._expression()
                self._consume(TokenType.RIGHT_BRACE, "Expected '}' after case expression.")

                # Wrap expression in ExprStmtNode for CaseNode compatibility
                from .ast import ExprStmtNode
                body_stmt = ExprStmtNode(expression=body_expr, span=body_expr.span)
                cases.append(CaseNode(
                    pattern=pattern, body=[body_stmt], guard=guard,
                    span=self._make_span(case_start, self._previous())))

            elif self._check(TokenType.DEFAULT):
                self._advance()
                self._consume(TokenType.LEFT_BRACE, "Expected '{' after default.")
                default_body = self._expression()
                self._consume(TokenType.RIGHT_BRACE, "Expected '}' after default expression.")
            else:
                self._error(f"Expected 'case' or 'default', got {self._current().type.name}")
                self._synchronize()
        self._consume(TokenType.RIGHT_BRACE, "Expected '}' after match body.")
        end = self._previous()
        return MatchExprNode(subject=subject, cases=cases, default_body=default_body,
                             span=self._make_span(start, end))

    def _case(self) -> CaseNode:
        """Parse a case clause: case pattern { ... } or case start..end { ... } or case pattern if guard { ... }.

        v1.8 patterns:
        - case _ { ... }                    wildcard
        - case x { ... }                    variable binding
        - case x if x > 0 { ... }           variable binding with guard
        - case is Type { ... }              type pattern
        - case is Type name { ... }         type pattern with binding
        """
        start = self._advance()  # consume CASE

        # v1.8: Check for wildcard pattern
        if self._check(TokenType.WILDCARD):
            wildcard_tok = self._advance()
            pattern = WildcardPatternNode(span=self._make_span(wildcard_tok, wildcard_tok))
        # v1.8: Check for type pattern: is Type [name]
        elif self._check(TokenType.IS):
            is_tok = self._advance()
            type_tok = self._consume(TokenType.IDENTIFIER, "Expected type name after 'is'.")
            type_name = type_tok.lexeme
            binding_name = None
            # Optional binding name
            if self._check(TokenType.IDENTIFIER):
                binding_tok = self._advance()
                binding_name = binding_tok.lexeme
            pattern = TypePatternNode(
                type_name=type_name,
                binding_name=binding_name,
                span=self._make_span(is_tok, self._previous())
            )
        else:
            pattern = self._expression()

            # v1.8: Check if pattern is a simple variable (variable binding)
            if isinstance(pattern, VariableNode):
                # Check if it's followed by guard or brace (not a value comparison)
                if self._check(TokenType.IF) or self._check(TokenType.LEFT_BRACE):
                    pattern = VariablePatternNode(
                        name=pattern.name,
                        span=pattern.span
                    )

            # Check for range pattern: expr..expr
            if self._match(TokenType.DOTDOT):
                pattern_start = pattern.span  # Save start span before parsing end
                end_expr = self._expression()
                pattern = RangePatternNode(start=pattern, end=end_expr,
                                           span=SourceSpan(
                                               pattern_start.file,
                                               pattern_start.start_line,
                                               pattern_start.start_col,
                                               end_expr.span.end_line,
                                               end_expr.span.end_col))

        # Check for guard condition: if expr
        guard = None
        if self._match(TokenType.IF):
            guard = self._expression()
        self._consume(TokenType.LEFT_BRACE, "Expected '{' after case pattern.")
        body = self._block_body_list()
        self._consume(TokenType.RIGHT_BRACE, "Expected '}' after case body.")
        return CaseNode(pattern=pattern, body=body, guard=guard,
                        span=self._make_span(start, self._previous()))

    def _try_stmt(self) -> TryStmtNode:
        """Parse a try statement: try { ... } catch Type name { ... } catch { ... } finally { ... }."""
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

    def _throw_stmt(self) -> ThrowStmtNode:
        """Parse a throw statement: throw ExceptionType or throw ExceptionType(message)."""
        start = self._previous()  # THROW token
        exception_type = self._parse_type()
        message: ExpressionNode | None = None
        # Optional message in parentheses: throw RuntimeError("message")
        if self._match(TokenType.LEFT_PAREN):
            if not self._check(TokenType.RIGHT_PAREN):
                message = self._expression()
            self._consume(TokenType.RIGHT_PAREN, "Expected ')' after exception message.")
        self._match(TokenType.SEMICOLON)  # Optional semicolon
        end = self._previous()
        return ThrowStmtNode(exception_type=exception_type, message=message,
                             span=self._make_span(start, end))

    def _assert_stmt(self) -> AssertStmtNode:
        """Parse an assert statement: assert condition or assert condition, message.

        AI-native observability (P3): Asserts that a condition is true.
        If false, raises AssertionError with structured context for AI debugging.
        """
        start = self._previous()  # ASSERT token
        condition = self._expression()
        message: ExpressionNode | None = None
        # Optional message after comma: assert x > 0, "x must be positive"
        if self._match(TokenType.COMMA):
            message = self._expression()
        self._match(TokenType.SEMICOLON)  # Optional semicolon
        end = self._previous()
        return AssertStmtNode(condition=condition, message=message,
                              span=self._make_span(start, end))

    def _catch_clause(self) -> CatchClauseNode:
        """Parse a typed catch: catch Type name { ... }."""
        start = self._previous()  # CATCH token
        error_type = self._parse_type()
        error_name = self._consume(TokenType.IDENTIFIER, "Expected error variable name.")
        self._consume(TokenType.LEFT_BRACE, "Expected '{' after catch clause.")
        body = self._block_body_list()
        self._consume(TokenType.RIGHT_BRACE, "Expected '}' after catch body.")
        return CatchClauseNode(error_type=error_type, error_name=error_name.lexeme,
                               body=body, span=self._make_span(start, self._previous()))

    def _catch_all(self) -> CatchAllNode:
        """Parse a catch-all: catch { ... }."""
        start = self._previous()  # CATCH token
        self._consume(TokenType.LEFT_BRACE, "Expected '{' after catch.")
        body = self._block_body_list()
        self._consume(TokenType.RIGHT_BRACE, "Expected '}' after catch body.")
        return CatchAllNode(body=body, span=self._make_span(start, self._previous()))

    def _finally_block(self) -> FinallyBlockNode:
        """Parse a finally block: finally { ... }. (FINALLY already consumed by _match)"""
        start = self._previous()  # FINALLY token (already consumed)
        self._consume(TokenType.LEFT_BRACE, "Expected '{' after finally.")
        body = self._block_body_list()
        self._consume(TokenType.RIGHT_BRACE, "Expected '}' after finally body.")
        return FinallyBlockNode(body=body, span=self._make_span(start, self._previous()))

    def _block_body_list(self) -> list[StatementNode]:
        """Parse a list of statements inside a block body (without the outer { })."""
        body: list[StatementNode] = []
        while not self._check(TokenType.RIGHT_BRACE, TokenType.EOF,
                              TokenType.CATCH, TokenType.FINALLY,
                              TokenType.CASE, TokenType.DEFAULT,
                              TokenType.BRANCH):
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
        """Consume a token of the specified type, or report an error."""
        if self._check(tt):
            return self._advance()
        self._error(message)
        peek = self._peek()
        return Token(type=tt, lexeme="<missing>", literal=None,
                     line=peek.line, col=peek.col,
                     end_line=peek.line, end_col=peek.col, file=peek.file)

    def _check(self, *types: TokenType) -> bool:
        """Check whether the current token type matches any of the given types."""
        if self._at_end():
            return TokenType.EOF in types
        return self._current().type in types

    def _is_context_keyword(self, keyword: str) -> bool:
        """Check if current token is an identifier matching a context keyword (v1.6)."""
        if self._at_end():
            return False
        tok = self._current()
        return tok.type == TokenType.IDENTIFIER and tok.lexeme == keyword

    def _peek(self) -> Token:
        """Peek at the current token (without consuming it)."""
        return self._current()

    def _previous(self) -> Token:
        """Return the previously consumed token."""
        return self.tokens[self._pos - 1]

    def _advance(self) -> Token:
        """Advance to the next token and return the previously consumed one."""
        if not self._at_end():
            self._pos += 1
        return self._previous()

    def _match(self, *types: TokenType) -> bool:
        """If the current token matches, consume it and return True."""
        for t in types:
            if self._check(t):
                self._advance()
                return True
        return False

    def _error(self, message: str) -> None:
        """Report a parse error."""
        tok = self._peek()
        span = SourceSpan(tok.file, tok.line, tok.col, tok.end_line, tok.end_col)
        self.errors.error(ErrorCode.PARSER_ERROR, message, span)

    def _synchronize(self) -> None:
        """Panic-mode error recovery: skip tokens until a synchronization point."""
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
        """Check whether the end of the token stream has been reached."""
        return self._current().type == TokenType.EOF

    def _current(self) -> Token:
        """Return the current token."""
        return self.tokens[self._pos]

    def _make_span(self, start: Token | SourceSpan, end: Token) -> SourceSpan:
        """Build a SourceSpan from a start token/span and an end token."""
        if isinstance(start, SourceSpan):
            return SourceSpan(start.file, start.start_line, start.start_col, end.end_line, end.end_col)
        return SourceSpan(start.file, start.line, start.col, end.end_line, end.end_col)
