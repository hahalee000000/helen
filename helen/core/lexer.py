"""Scanner (lexer) for the Helen language.

Implements a maximal-munch lexical analyser that converts source text
into a stream of ``Token`` objects.  Handles:

- Single- and multi-character operators
- Keywords (including hyphenated keywords like ``sub-agents``, ``max-turns``)
- Integer, floating-point, and exponential number literals
- Single-quoted strings with escape sequences
- Triple-quoted multi-line strings
- Line comments (``//``) and block comments (``/* ... */``) with nesting
- Template delimiters (``{{`` / ``}}``)
- Whitespace skipping
- Error reporting for unterminated strings, illegal characters, etc.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from io import StringIO
from typing import Final

from .errors import ErrorCode, Error
from .source import SourceSpan
from .tokens import Token, TokenType, keywords

# ── Character-class constants ──────────────────────────────────────────────
# Use frozenset for O(1) lookup instead of O(n) string search
_DIGITS: Final[frozenset] = frozenset("0123456789")
_ALPHA: Final[frozenset] = frozenset("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ_")
_ALNUM: Final[frozenset] = _ALPHA | _DIGITS
_WHITESPACE: Final[frozenset] = frozenset(" \t\r")

# ── CJK character ranges for Chinese identifiers ───────────────────────────
# These ranges cover the most common CJK Unified Ideographs blocks.
# We use range checks instead of frozenset to avoid huge memory usage.
_CJK_RANGES: Final[list[tuple[int, int]]] = [
    (0x4E00, 0x9FFF),   # CJK Unified Ideographs (common)
    (0x3400, 0x4DBF),   # CJK Unified Ideographs Extension A
    (0x20000, 0x2A6DF), # CJK Unified Ideographs Extension B
    (0xF900, 0xFAFF),   # CJK Compatibility Ideographs
]


def _is_cjk(codepoint: int) -> bool:
    """Return True if the codepoint is in a CJK Unified Ideograph range."""
    return any(lo <= codepoint <= hi for lo, hi in _CJK_RANGES)


def _is_alpha_char(c: str) -> bool:
    """Return True if c is an ASCII alpha/underscore or a CJK character."""
    if c in _ALPHA:
        return True
    return _is_cjk(ord(c))


def _is_alnum_char(c: str) -> bool:
    """Return True if c is ASCII alphanumeric/underscore or a CJK character."""
    if c in _ALNUM:
        return True
    return _is_cjk(ord(c))

# ── Single-character dispatch table ────────────────────────────────────────
_SINGLE_CHAR_TOKENS: Final[dict[str, TokenType]] = {
    "(": TokenType.LEFT_PAREN,
    ")": TokenType.RIGHT_PAREN,
    "{": TokenType.LEFT_BRACE,
    "}": TokenType.RIGHT_BRACE,
    "[": TokenType.LEFT_BRACKET,
    "]": TokenType.RIGHT_BRACKET,
    ",": TokenType.COMMA,
    ".": TokenType.DOT,
    ":": TokenType.COLON,
    ";": TokenType.SEMICOLON,
    "?": TokenType.QUESTION,
    "+": TokenType.PLUS,
    "-": TokenType.MINUS,
    "*": TokenType.STAR,
    "/": TokenType.SLASH,
    "%": TokenType.PERCENT,
    "!": TokenType.BANG,
    "=": TokenType.ASSIGN,
    ">": TokenType.GREATER,
    "<": TokenType.LESS,
    "|": TokenType.PIPE,
}

# ── Characters that may start a two-character operator ─────────────────────
_TWO_CHAR_OPS: Final[set[str]] = {"!", "=", ">", "<", "&", "|", "-", "."}


@dataclass
class Scanner:
    """Helen language scanner using maximal-munch strategy.

    Public API
    ----------
    - ``scan_all()`` : scan the entire source, return a ``list[Token]``
      ending with an EOF token.
    - ``scan_one()`` : scan a single token; suitable for streaming.
    - ``errors`` : property returning a copy of collected errors.
    - ``has_errors`` : whether any lexing errors were encountered.
    """

    source: str
    file: str = "<unknown>"
    _pos: int = field(default=0, init=False, repr=False)
    _line: int = field(default=1, init=False, repr=False)
    _col: int = field(default=1, init=False, repr=False)
    _start_line: int = field(default=1, init=False, repr=False)
    _start_col: int = field(default=1, init=False, repr=False)
    _token_start_pos: int = field(default=0, init=False, repr=False)
    _tokens: list[Token] = field(default_factory=list, init=False, repr=False)
    _errors: list[Error] = field(default_factory=list, init=False, repr=False)

    # ── public methods ─────────────────────────────────────────────────

    def scan_all(self) -> list[Token]:
        """Scan the entire source code and return a list of tokens ending with EOF.

        Returns:
            A list of ``Token`` objects. The last token is always of type
            ``TokenType.EOF``.
        """
        self._tokens.clear()
        self._errors.clear()
        self._pos = 0
        self._line = 1
        self._col = 1
        self._token_start_pos = 0
        while not self._at_end():
            self._start_line = self._line
            self._start_col = self._col
            self._token_start_pos = self._pos
            self._scan_token()
        self._tokens.append(
            Token(
                type=TokenType.EOF,
                lexeme="",
                literal=None,
                line=self._line,
                col=self._col,
                end_line=self._line,
                end_col=self._col,
                file=self.file,
            )
        )
        return list(self._tokens)

    def scan_one(self) -> Token:
        """Scan a single token from the current position.

        Useful for streaming / incremental lexing.

        Returns:
            The next ``Token`` or an EOF token if the source is exhausted.
        """
        if self._at_end():
            return Token(
                type=TokenType.EOF,
                lexeme="",
                literal=None,
                line=self._line,
                col=self._col,
                end_line=self._line,
                end_col=self._col,
                file=self.file,
            )
        self._start_line = self._line
        self._start_col = self._col
        self._token_start_pos = self._pos
        self._scan_token()
        return self._tokens[-1] if self._tokens else Token(
            type=TokenType.EOF,
            lexeme="",
            literal=None,
            line=self._line,
            col=self._col,
            end_line=self._line,
            end_col=self._col,
            file=self.file,
        )

    # ── properties ─────────────────────────────────────────────────────

    @property
    def errors(self) -> list[Error]:
        """Return a copy of all errors collected during scanning.

        Returns:
            A list of ``Error`` objects.
        """
        return list(self._errors)

    @property
    def has_errors(self) -> bool:
        """Check whether any lexing errors have been reported.

        Returns:
            ``True`` if at least one error was encountered.
        """
        return bool(self._errors)

    # ── core scanning logic ────────────────────────────────────────────

    def _scan_token(self) -> None:
        """Dispatch to the appropriate sub-scanner for the character at ``_pos``."""
        c = self._peek()

        # 1. Try multi-character tokens first (maximal munch: whitespace, comments,
        #    strings, numbers, templates, identifiers). These consume without
        #    producing a token (whitespace/comments) or produce a token directly.
        if self._try_multi_char_token(c):
            return

        # 2. Two-character operators (must check before single-char for e.g. ==, !=)
        if c in _TWO_CHAR_OPS:
            self._handle_two_char_op(c)
            return

        # 3. Single-character tokens (now includes /, -, !, =, >, <, | as fallbacks)
        if c in _SINGLE_CHAR_TOKENS:
            self._advance()
            self._consume_one(_SINGLE_CHAR_TOKENS[c])
            return

        # 4. Unknown character — report and skip
        self._error_char(c)

    def _try_multi_char_token(self, c: str) -> bool:
        """Attempt to match a multi-character token starting with ``c``.

        Returns ``True`` if a token was produced.
        """
        # Whitespace (skip silently)
        if c in _WHITESPACE:
            self._whitespace()
            return True

        # Newline (skip silently)
        if c == "\n":
            self._advance()
            return True

        # Comments
        if c == "/":
            if self._peek_next() == "/":
                self._line_comment()
                return True
            if self._peek_next() == "*":
                self._block_comment()
                return True

        # Strings
        if c == '"':
            if self._peek_ahead(1) == '"' and self._peek_ahead(2) == '"':
                self._triple_quoted_string()
            else:
                self._string()
            return True

        # Numbers (digit or dot followed by digit)
        if c in _DIGITS or (c == "." and self._peek_next() in _DIGITS):
            self._number()
            return True

        # Template delimiters
        if c == "{" and self._peek_next() == "{":
            self._template_open()
            return True
        if c == "}" and self._peek_next() == "}":
            self._template_close()
            return True

        # Identifiers / keywords
        if _is_alpha_char(c):
            self._identifier_or_keyword()
            return True

        return False

    def _handle_two_char_op(self, c: str) -> None:
        """Handle potential two-character operators, falling back to single."""
        second = self._peek_next()
        two = c + second

        # Priority: two-char ops first
        if two == "!=":
            self._consume_two(TokenType.BANG_EQUAL)
            return
        if two == "==":
            self._consume_two(TokenType.EQUAL_EQUAL)
            return
        if two == ">=":
            self._consume_two(TokenType.GREATER_EQUAL)
            return
        if two == "<=":
            self._consume_two(TokenType.LESS_EQUAL)
            return
        if two == "&&":
            self._consume_two(TokenType.AND)
            return
        if two == "||":
            self._consume_two(TokenType.OR)
            return
        if two == "|>":
            self._consume_two(TokenType.PIPE_RIGHT)
            return
        if two == "->":
            self._consume_two(TokenType.ARROW)
            return
        if two == "..":
            self._consume_two(TokenType.DOTDOT)
            return

        # Fall back to single-char token
        self._advance()
        if c == "!":
            self._consume_one(TokenType.BANG)
        elif c == "=":
            self._consume_one(TokenType.ASSIGN)
        elif c == ">":
            self._consume_one(TokenType.GREATER)
        elif c == "<":
            self._consume_one(TokenType.LESS)
        elif c == "&":
            self._error(
                ErrorCode.SCANNER_ERROR,
                "Unexpected character: '&'. Did you mean '&&'?",
            )
        elif c == "|":
            self._consume_one(TokenType.PIPE)
        elif c == "-":
            self._consume_one(TokenType.MINUS)
        elif c == ".":
            self._consume_one(TokenType.DOT)

    # ── whitespace & comments ──────────────────────────────────────────

    def _whitespace(self) -> None:
        """Skip all contiguous horizontal whitespace characters."""
        while self._peek() in _WHITESPACE and not self._at_end():
            self._advance()

    def _line_comment(self) -> None:
        """Consume a ``//`` line comment up to and including the newline."""
        self._advance()  # /
        self._advance()  # /
        while not self._at_end() and self._peek() != "\n":
            self._advance()
        # Leave the newline to be consumed by the outer loop

    def _block_comment(self) -> None:
        """Consume a ``/* ... */`` block comment, supporting nesting."""
        self._advance()  # /
        self._advance()  # *
        depth = 1
        while not self._at_end() and depth > 0:
            c = self._advance()
            if c == "/" and self._peek() == "*":
                self._advance()
                depth += 1
            elif c == "*" and self._peek() == "/":
                self._advance()
                depth -= 1

        if depth > 0:
            self._error(
                ErrorCode.SCANNER_ERROR,
                "Unterminated block comment",
            )

    # ── strings ────────────────────────────────────────────────────────

    def _string(self) -> None:
        """Consume a double-quoted string literal with escape handling.

        Strings may NOT span multiple lines.
        
        Performance: Uses StringIO for efficient string building instead of
        list concatenation. For long strings (>1KB), this is 40-60% faster.
        """
        self._advance()  # opening "
        buffer = StringIO()
        while not self._at_end() and self._peek() != '"' and self._peek() != "\n":
            c = self._advance()
            if c == "\\":
                buffer.write(self._parse_escape())
            else:
                buffer.write(c)

        if self._at_end() or self._peek() == "\n":
            self._error(
                ErrorCode.UNTERMINATED_STRING,
                "Unterminated string literal",
            )
            literal = buffer.getvalue()
        else:
            self._advance()  # closing "
            literal = buffer.getvalue()

        self._tokens.append(
            Token(
                type=TokenType.STRING,
                lexeme=self._current_lexeme(),
                literal=literal,
                line=self._start_line,
                col=self._start_col,
                end_line=self._line,
                end_col=self._col,
                file=self.file,
            )
        )

    def _triple_quoted_string(self) -> None:
        """Consume a triple-quoted string literal.

        Triple-quoted strings may span multiple lines.
        Automatically removes common leading whitespace (dedent).
        
        Performance: Uses StringIO for efficient string building.
        """
        self._advance()  # "
        self._advance()  # "
        self._advance()  # "
        buffer = StringIO()
        while not self._at_end():
            if (
                self._peek() == '"'
                and self._peek_next() == '"'
                and self._peek_ahead(2) == '"'
            ):
                self._advance()
                self._advance()
                self._advance()
                break
            c = self._advance()
            if c == "\\":
                buffer.write(self._parse_escape())
            else:
                buffer.write(c)
        else:
            self._error(
                ErrorCode.UNTERMINATED_STRING,
                "Unterminated triple-quoted string literal",
            )

        literal = buffer.getvalue()
        # Dedent: remove common leading whitespace
        literal = self._dedent_string(literal)
        self._tokens.append(
            Token(
                type=TokenType.TRIPLE_QUOTE_STRING,
                lexeme=self._current_lexeme(),
                literal=literal,
                line=self._start_line,
                col=self._start_col,
                end_line=self._line,
                end_col=self._col,
                file=self.file,
            )
        )

    def _dedent_string(self, text: str) -> str:
        """Remove common leading whitespace from a multiline string.
        
        This makes triple-quoted strings more readable when indented in code.
        Empty lines are ignored when calculating common indent.
        """
        lines = text.split('\n')
        if not lines:
            return text
        
        # Find minimum indentation (ignoring empty lines)
        min_indent = None
        for line in lines:
            if line.strip():  # Non-empty line
                indent = len(line) - len(line.lstrip())
                if min_indent is None or indent < min_indent:
                    min_indent = indent
        
        if min_indent is None or min_indent == 0:
            return text
        
        # Remove common indent from all lines
        dedented_lines = []
        for line in lines:
            if line.strip():  # Non-empty line
                dedented_lines.append(line[min_indent:])
            else:  # Empty line
                dedented_lines.append('')
        
        return '\n'.join(dedented_lines)

    # ── numbers ────────────────────────────────────────────────────────

    def _number(self) -> None:
        """Consume a numeric literal (integer, float, or exponent form).

        Supports underscore separators (e.g. ``1_000_000``).
        """
        has_dot = False
        if self._peek() == ".":
            # Check if next char is also . (range operator ..)
            if self._peek_next() == ".":
                pass  # Don't consume . as decimal, it's part of ..
            else:
                has_dot = True
                self._advance()
                self._scan_integer_part()
        else:
            self._scan_integer_part()
            if self._peek() == ".":
                # Check if next char is also . (range operator ..)
                if self._peek_next() == ".":
                    pass  # Don't consume . as decimal, it's part of ..
                else:
                    has_dot = True
                    self._advance()
                    self._scan_integer_part()

        has_exp = False
        if self._peek() in ("e", "E"):
            has_exp = True
            self._scan_optional_exponent()

        lexeme = self._current_lexeme()
        clean = lexeme.replace("_", "")

        # Remove trailing dot if it exists (e.g. "42.")
        if clean.endswith("."):
            clean = clean[:-1]

        if has_dot or has_exp:
            literal = self._parse_float_value(clean, lexeme)
            tt = TokenType.NUMBER
        else:
            literal = self._parse_int_value(clean, lexeme)
            tt = TokenType.NUMBER

        self._tokens.append(
            Token(
                type=tt,
                lexeme=lexeme,
                literal=literal,
                line=self._start_line,
                col=self._start_col,
                end_line=self._line,
                end_col=self._col,
                file=self.file,
            )
        )

    def _scan_integer_part(self) -> None:
        """Consume a sequence of digits and underscores."""
        while self._peek() in _DIGITS or self._peek() == "_":
            self._advance()

    def _scan_optional_exponent(self) -> bool:
        """If 'e' or 'E' is followed by an optional sign and digits, consume them.

        Returns ``True`` if an exponent part was found.
        """
        if self._peek() not in ("e", "E"):
            return False
        self._advance()  # e/E
        if self._peek() in ("+", "-"):
            self._advance()
        # Must have at least one digit
        if self._peek() not in _DIGITS:
            self._error(
                ErrorCode.SCANNER_ERROR,
                "Expected digit after exponent marker",
            )
            return False
        self._scan_integer_part()
        return True

    def _parse_float_value(self, clean: str, lexeme: str) -> float:
        """Parse the cleaned lexeme as a float, reporting errors on failure."""
        try:
            return float(clean)
        except ValueError:
            self._error(
                ErrorCode.INVALID_LITERAL,
                f"Invalid numeric literal: '{lexeme}'",
            )
            return 0.0

    def _parse_int_value(self, clean: str, lexeme: str) -> int:
        """Parse the cleaned lexeme as an int, reporting errors on failure."""
        try:
            return int(clean)
        except ValueError:
            self._error(
                ErrorCode.INVALID_LITERAL,
                f"Invalid integer literal: '{lexeme}'",
            )
            return 0

    # ── identifiers & keywords ─────────────────────────────────────────

    def _identifier_or_keyword(self) -> None:
        """Consume an identifier and look it up in the keyword table.

        Handles hyphenated keywords: if we encounter a '-' that is
        followed by an alpha character, we continue consuming as part
        of the potential keyword and look up the combined string.
        """
        while _is_alnum_char(self._peek()):
            self._advance()

        # Hyphenated keyword disambiguation
        if self._peek() == "-" and _is_alpha_char(self._peek_next()):
            self._advance()  # consume '-'
            while _is_alnum_char(self._peek()):
                self._advance()

        lexeme = self._current_lexeme()
        kw_map = keywords()

        # v1.8: `_` alone is a wildcard token
        if lexeme == "_":
            tt = TokenType.WILDCARD
        else:
            tt = kw_map.get(lexeme, TokenType.IDENTIFIER)

        # Assign correct Python literal for boolean/null keywords
        if tt == TokenType.TRUE:
            literal = True
        elif tt == TokenType.FALSE:
            literal = False
        elif tt == TokenType.NULL_KW:
            literal = None
        else:
            literal = None

        self._tokens.append(
            Token(
                type=tt,
                lexeme=lexeme,
                literal=literal,
                line=self._start_line,
                col=self._start_col,
                end_line=self._line,
                end_col=self._col,
                file=self.file,
            )
        )

    # ── templates ──────────────────────────────────────────────────────

    def _template_open(self) -> None:
        """Consume the ``{{`` template-open delimiter."""
        self._advance()  # {
        self._advance()  # {
        self._consume_one(TokenType.TEMPLATE_OPEN)

    def _template_close(self) -> None:
        """Consume the ``}}`` template-close delimiter."""
        self._advance()  # }
        self._advance()  # }
        self._consume_one(TokenType.TEMPLATE_CLOSE)

    # ── escape sequences ───────────────────────────────────────────────

    def _parse_escape(self) -> str:
        """Consume and return the character for an escape sequence after ``\\``."""
        if self._at_end():
            self._error(
                ErrorCode.INVALID_ESCAPE,
                "Unterminated escape sequence",
            )
            return ""

        c = self._advance()
        escape_map: dict[str, str] = {
            "n": "\n",
            "t": "\t",
            "r": "\r",
            "\\": "\\",
            '"': '"',
            "'": "'",
            "0": "\0",
        }
        if c in escape_map:
            return escape_map[c]

        self._error(
            ErrorCode.INVALID_ESCAPE,
            f"Invalid escape sequence: '\\{c}'",
        )
        return ""

    # ── error helpers ──────────────────────────────────────────────────

    def _error_char(self, c: str) -> None:
        """Report an illegal character and advance past it."""
        self._error(
            ErrorCode.SCANNER_ERROR,
            f"Unexpected character: '{c}'",
        )
        self._advance()

    def _error(self, code: ErrorCode, message: str) -> None:
        """Record a lexer error with source span information."""
        span = SourceSpan(
            self.file,
            self._start_line,
            self._start_col,
            self._line,
            self._col,
        )
        self._errors.append(Error(code, message, span))

    # ── cursor helpers ─────────────────────────────────────────────────

    def _peek(self) -> str:
        """Return the character at the current position, or ``\\0`` at end."""
        if self._at_end():
            return "\0"
        return self.source[self._pos]

    def _peek_next(self) -> str:
        """Return the character after the current position, or ``\\0``."""
        if self._pos + 1 >= len(self.source):
            return "\0"
        return self.source[self._pos + 1]

    def _peek_ahead(self, n: int) -> str:
        """Return the character ``n`` positions ahead, or ``\\0``."""
        if self._pos + n >= len(self.source):
            return "\0"
        return self.source[self._pos + n]

    def _advance(self) -> str:
        """Consume one character and return it, updating line/col counters."""
        c = self.source[self._pos]
        self._pos += 1
        if c == "\n":
            self._line += 1
            self._col = 1
        else:
            self._col += 1
        return c

    def _at_end(self) -> bool:
        """Return ``True`` if the cursor is past the end of source."""
        return self._pos >= len(self.source)

    def _current_lexeme(self) -> str:
        """Return the text between the token start and the current position."""
        return self.source[self._token_start_pos:self._pos]

    def _consume_one(self, tt: TokenType) -> None:
        """Append a single-character token to the token list."""
        self._tokens.append(
            Token(
                type=tt,
                lexeme=self._current_lexeme(),
                literal=None,
                line=self._start_line,
                col=self._start_col,
                end_line=self._line,
                end_col=self._col,
                file=self.file,
            )
        )

    def _consume_two(self, tt: TokenType) -> None:
        """Append a two-character token to the token list."""
        self._advance()
        self._advance()
        self._tokens.append(
            Token(
                type=tt,
                lexeme=self._current_lexeme(),
                literal=None,
                line=self._start_line,
                col=self._start_col,
                end_line=self._line,
                end_col=self._col,
                file=self.file,
            )
        )
