"""Token types and keyword mapping for the Hellen language.

This module defines the complete set of lexical tokens used by the Hellen
scanner, along with a keyword lookup that maps reserved source strings to
their corresponding TokenType values.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto
from typing import TYPE_CHECKING, Union

if TYPE_CHECKING:
    from hellen.core.source import SourceSpan


class TokenType(Enum):
    """Enumeration of all lexical token types in the Hellen language.

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
    COLON = auto()
    SEMICOLON = auto()
    QUESTION = auto()
    PIPE = auto()

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

    # === Keywords (40 total) ===
    AGENT = auto()
    DESCRIPTION = auto()
    MODEL = auto()
    TOOLS = auto()
    SKILLS = auto()
    SUB_AGENTS = auto()
    MEMORY = auto()
    TEMPERATURE = auto()
    MAX_TURNS = auto()
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
    CALL = auto()
    AWAIT = auto()
    ASYNC = auto()
    MATCH = auto()
    CASE = auto()
    BRANCH = auto()
    OPTION = auto()
    DEFAULT = auto()
    CHOOSE = auto()
    ACT = auto()
    TRY = auto()
    CATCH = auto()
    FINALLY = auto()
    FN = auto()
    AS = auto()
    IN = auto()
    FUNCTIONS = auto()
    MAIN = auto()

    # === Special ===
    EOF = auto()


# Type alias for literal values a token can carry
LiteralValue = Union[str, int, float, bool, None]

# Keyword → TokenType mapping (40 entries)
_KEYWORD_MAP: dict[str, TokenType] = {
    "agent": TokenType.AGENT,
    "description": TokenType.DESCRIPTION,
    "model": TokenType.MODEL,
    "tools": TokenType.TOOLS,
    "skills": TokenType.SKILLS,
    "sub-agents": TokenType.SUB_AGENTS,
    "memory": TokenType.MEMORY,
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
    "call": TokenType.CALL,
    "await": TokenType.AWAIT,
    "async": TokenType.ASYNC,
    "match": TokenType.MATCH,
    "case": TokenType.CASE,
    "branch": TokenType.BRANCH,
    "option": TokenType.OPTION,
    "default": TokenType.DEFAULT,
    "choose": TokenType.CHOOSE,
    "act": TokenType.ACT,
    "try": TokenType.TRY,
    "catch": TokenType.CATCH,
    "finally": TokenType.FINALLY,
    "fn": TokenType.FN,
    "as": TokenType.AS,
    "in": TokenType.IN,
    "functions": TokenType.FUNCTIONS,
    "main": TokenType.MAIN,
    "true": TokenType.TRUE,
    "false": TokenType.FALSE,
    "null": TokenType.NULL_KW,
}


def keywords() -> dict[str, TokenType]:
    """Return the mapping from keyword strings to their TokenType values.

    Returns:
        A dict mapping each reserved keyword (e.g. ``"agent"``, ``"let"``)
        to the corresponding ``TokenType`` enum member.  The returned dict
        is a shallow copy so callers cannot mutate the internal cache.
    """
    return dict(_KEYWORD_MAP)


@dataclass(frozen=True)
class Token:
    """An immutable lexical token produced by the Hellen scanner.

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
        from hellen.core.source import SourceSpan

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
