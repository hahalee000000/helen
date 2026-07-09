"""Token types and keyword mapping for the Helen language.

This module defines the complete set of lexical tokens used by the Helen
scanner, along with a keyword lookup that maps reserved source strings to
their corresponding TokenType values.
"""

from __future__ import annotations

import types
from dataclasses import dataclass
from enum import Enum, auto
from typing import TYPE_CHECKING, Union, Mapping

if TYPE_CHECKING:
    from helen.core.source import SourceSpan


class TokenType(Enum):
    """Enumeration of all lexical token types in the Helen language.

    Categories:
    - Delimiters: parens, braces, brackets, punctuation
    - Operators: arithmetic, comparison, logical, assignment
    - Literals: identifiers, strings, numbers, booleans, null
    - Template: {{ and }} delimiters
    - Keywords: reserved language words
    - Special: EOF marker
    """

    # === Delimiters ===
    LEFT_PAREN = auto()
    RIGHT_PAREN = auto()
    LEFT_BRACE = auto()
    RIGHT_BRACE = auto()
    LEFT_BRACKET = auto()
    RIGHT_BRACKET = auto()
    COMMA = auto()
    DOT = auto()
    DOTDOT = auto()  # ..
    COLON = auto()
    SEMICOLON = auto()
    QUESTION = auto()
    PIPE = auto()
    PIPE_RIGHT = auto()  # |> pipe operator

    # === Operators ===
    MINUS = auto()
    PLUS = auto()
    SLASH = auto()
    STAR = auto()
    PERCENT = auto()
    ARROW = auto()  # ->
    BANG = auto()  # !
    BANG_EQUAL = auto()  # !=
    ASSIGN = auto()  # =
    EQUAL_EQUAL = auto()  # ==
    GREATER = auto()  # >
    GREATER_EQUAL = auto()  # >=
    LESS = auto()  # <
    LESS_EQUAL = auto()  # <=
    AND = auto()  # &&
    OR = auto()  # ||
    AT = auto()  # @ (v1.12: decorator for agent isolation level)

    # === Literals ===
    IDENTIFIER = auto()
    STRING = auto()
    TRIPLE_QUOTE_STRING = auto()
    NUMBER = auto()
    TRUE = auto()
    FALSE = auto()
    NULL_KW = auto()

    # === Template ===
    TEMPLATE_OPEN = auto()  # {{
    TEMPLATE_CLOSE = auto()  # }}

    # === Keywords (46 total, including context-only: MEMORY, WILDCARD) ===
    AGENT = auto()
    DESCRIPTION = auto()
    MODEL = auto()
    TOOLS = auto()
    STREAMING = auto()
    TEMPERATURE = auto()
    MAX_TURNS = auto()
    MEMORY = auto()
    PROMPT = auto()
    LLM = auto()
    IMPORT = auto()
    LET = auto()
    CONST = auto()
    IF = auto()
    ELSE = auto()
    FOR = auto()
    WHILE = auto()
    BREAK = auto()
    CONTINUE = auto()
    RETURN = auto()
    AWAIT = auto()
    ASYNC = auto()
    DETACH = auto()  # v1.12: fire-and-forget background execution (Issue #29)
    MATCH = auto()
    CASE = auto()
    BRANCH = auto()
    DEFAULT = auto()
    ACT = auto()
    TRY = auto()
    CATCH = auto()
    FINALLY = auto()
    THROW = auto()
    ASSERT = auto()
    FN = auto()
    AS = auto()
    IN = auto()
    FUNCTIONS = auto()
    MAIN = auto()
    STORE = auto()  # v1.12: shared store declaration
    CHANNEL = auto()  # v1.13: channel declaration
    PROTOCOL = auto()  # v1.7: protocol declaration
    IMPL = auto()      # v1.7: protocol implementation
    IS = auto()        # v1.8: type pattern in match
    WILDCARD = auto()  # v1.8: wildcard pattern `_` in match
    SHARED = auto()    # v1.10: shared let — cross-agent visible variable
    ALIAS = auto()     # v1.10: function alias statement (alias X as Y)

    # === Special ===
    EOF = auto()


# Type alias for literal values a token can carry
LiteralValue = Union[str, int, float, bool, None]

# Keyword → TokenType mapping (94 entries)
# Note: MEMORY and WILDCARD are context keywords — handled by lexer/parser directly,
# not via this map, so they can also be used as variable names.
_KEYWORD_MAP: dict[str, TokenType] = {
    "agent": TokenType.AGENT,
    "description": TokenType.DESCRIPTION,
    "model": TokenType.MODEL,
    "tools": TokenType.TOOLS,
    "streaming": TokenType.STREAMING,
    "temperature": TokenType.TEMPERATURE,
    "max-turns": TokenType.MAX_TURNS,
    "prompt": TokenType.PROMPT,
    "llm": TokenType.LLM,
    "import": TokenType.IMPORT,
    "let": TokenType.LET,
    "const": TokenType.CONST,
    "if": TokenType.IF,
    "else": TokenType.ELSE,
    "for": TokenType.FOR,
    "while": TokenType.WHILE,
    "break": TokenType.BREAK,
    "continue": TokenType.CONTINUE,
    "return": TokenType.RETURN,
    "await": TokenType.AWAIT,
    "async": TokenType.ASYNC,
    "detach": TokenType.DETACH,  # v1.12: fire-and-forget (Issue #29)
    "match": TokenType.MATCH,
    "case": TokenType.CASE,
    "branch": TokenType.BRANCH,
    "default": TokenType.DEFAULT,
    "act": TokenType.ACT,
    "try": TokenType.TRY,
    "catch": TokenType.CATCH,
    "finally": TokenType.FINALLY,
    "throw": TokenType.THROW,
    "assert": TokenType.ASSERT,
    "fn": TokenType.FN,
    "as": TokenType.AS,
    "in": TokenType.IN,
    "functions": TokenType.FUNCTIONS,
    "main": TokenType.MAIN,
    "store": TokenType.STORE,  # v1.12: shared store
    "仓库": TokenType.STORE,   # v1.12: Chinese equivalent
    "channel": TokenType.CHANNEL,  # v1.13: channel declaration
    "通道": TokenType.CHANNEL,     # v1.13: Chinese equivalent
    "alias": TokenType.ALIAS,
    "protocol": TokenType.PROTOCOL,  # v1.7
    "impl": TokenType.IMPL,          # v1.7
    "is": TokenType.IS,              # v1.8
    "true": TokenType.TRUE,
    "false": TokenType.FALSE,
    "null": TokenType.NULL_KW,
    # === Chinese keywords (中文关键字) ===
    # Variable/function
    "定义": TokenType.LET,
    "常量": TokenType.CONST,
    "函数": TokenType.FN,
    "返回": TokenType.RETURN,
    # Control flow
    "如果": TokenType.IF,
    "否则": TokenType.ELSE,
    "对于": TokenType.FOR,
    "属于": TokenType.IN,
    "当": TokenType.WHILE,
    "中断": TokenType.BREAK,
    "继续": TokenType.CONTINUE,
    "匹配": TokenType.MATCH,
    "情况": TokenType.CASE,
    "默认": TokenType.DEFAULT,
    "尝试": TokenType.TRY,
    "捕获": TokenType.CATCH,
    "最终": TokenType.FINALLY,
    "抛出": TokenType.THROW,
    "断言": TokenType.ASSERT,
    # Literals
    "真": TokenType.TRUE,
    "假": TokenType.FALSE,
    "空": TokenType.NULL_KW,
    "是": TokenType.IS,
    # Agent/LLM
    "智能体": TokenType.AGENT,
    "大模型": TokenType.LLM,
    "执行": TokenType.ACT,
    "异步": TokenType.ASYNC,
    "等待": TokenType.AWAIT,
    "分离": TokenType.DETACH,  # v1.12: fire-and-forget (Issue #29)
    "提示词": TokenType.PROMPT,
    "描述": TokenType.DESCRIPTION,
    "模型": TokenType.MODEL,
    "工具": TokenType.TOOLS,
    "流式输出": TokenType.STREAMING,
    "温度": TokenType.TEMPERATURE,
    "最大轮次": TokenType.MAX_TURNS,
    "函数区": TokenType.FUNCTIONS,
    "主函": TokenType.MAIN,
    # Other
    "导入": TokenType.IMPORT,
    "作为": TokenType.AS,
    "协议": TokenType.PROTOCOL,
    "实现": TokenType.IMPL,
    "分支": TokenType.BRANCH,
    # v1.10: shared keyword
    "shared": TokenType.SHARED,
    "共享": TokenType.SHARED,
    # v1.10: alias keyword (function name aliasing)
    "别名": TokenType.ALIAS,
}


def keywords() -> Mapping[str, TokenType]:
    """Return the mapping from keyword strings to their TokenType values.

    Returns:
        A read-only mapping of reserved keywords (e.g. ``"agent"``, ``"let"``)
        to their corresponding ``TokenType`` enum members.  Returns a
        MappingProxyType to prevent mutation while avoiding copy overhead.
    """
    return types.MappingProxyType(_KEYWORD_MAP)


@dataclass(frozen=True)
class Token:
    """An immutable lexical token produced by the Helen scanner.

    Attributes:
        type: The lexical category of this token.
        lexeme: The exact source text that matched this token.
        literal: The semantic value (number, string, bool, etc.) or ``None``.
        line: 1-based starting line number in the source file.
        col: 1-based starting column number in the source file.
        end_line: 1-based ending line number (inclusive).
        end_col: 1-based ending column number (exclusive).
        file: The source filename for error reporting.
    """

    type: TokenType
    lexeme: str
    literal: LiteralValue
    line: int
    col: int
    end_line: int
    end_col: int
    file: str = "<unknown>"

    @property
    def span(self) -> SourceSpan:
        """Return a ``SourceSpan`` covering this token's position in source.

        Returns:
            A ``SourceSpan`` instance derived from this token's file, line,
            and column information.
        """
        from helen.core.source import SourceSpan

        return SourceSpan(self.file, self.line, self.col, self.end_line, self.end_col)

    def __str__(self) -> str:
        """Return a human-readable representation of the token.

        Returns:
            A string in the form ``TokenType('lexeme')`` or
            ``TokenType(literal_value)`` when a literal is present.
        """
        if self.literal is not None:
            return f"Token({self.type.name}, {self.literal!r})"
        return f"Token({self.type.name}, '{self.lexeme}')"

    def __repr__(self) -> str:
        """Return a detailed representation suitable for debugging.

        Returns:
            A string showing all token fields including position info.
        """
        return (
            f"Token(type={self.type.name}, lexeme={self.lexeme!r}, "
            f"literal={self.literal!r}, line={self.line}, col={self.col}, "
            f"end_line={self.end_line}, end_col={self.end_col}, "
            f"file={self.file!r})"
        )
