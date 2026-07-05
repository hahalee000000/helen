"""Helen Language Server Protocol implementation (HLD M12).

Provides IDE support via LSP:
- Diagnostics: real-time error reporting on file change
- Completion: keyword and identifier completion
- Go-to-definition: navigate to agent/function/variable declarations

Uses JSON-RPC 2.0 over stdio (LSP standard transport).
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field
from typing import Any


def _log(msg: str) -> None:
    """Log to stderr — visible in VS Code's 'Helen Language Server' output panel."""
    print(f"[helen-lsp] {msg}", file=sys.stderr, flush=True)


@dataclass
class Position:
    """LSP Position (0-based line and character)."""

    line: int
    character: int

    def to_dict(self) -> dict[str, int]:
        return {"line": self.line, "character": self.character}


@dataclass
class Range:
    """LSP Range."""

    start: Position
    end: Position

    def to_dict(self) -> dict[str, Any]:
        return {"start": self.start.to_dict(), "end": self.end.to_dict()}


@dataclass
class Diagnostic:
    """LSP Diagnostic."""

    range: Range
    severity: int  # 1=Error, 2=Warning, 3=Info, 4=Hint
    message: str
    source: str = "helen"
    code: str | None = None

    def to_dict(self) -> dict[str, Any]:
        result = {
            "range": self.range.to_dict(),
            "severity": self.severity,
            "message": self.message,
            "source": self.source,
        }
        if self.code:
            result["code"] = self.code
        return result


@dataclass
class CompletionItem:
    """LSP CompletionItem."""

    label: str
    kind: int = 1  # 1=Text, 2=Method, 3=Function, 4=Constructor, 5=Field, 6=Variable, 7=Class, 8=Interface, 9=Module, 10=Property, 11=Unit, 12=Value, 13=Enum, 14=Keyword, 15=Snippet, 16=Color, 17=File, 18=Reference, 19=Folder, 20=EnumMember
    detail: str | None = None
    insert_text: str | None = None

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {"label": self.label, "kind": self.kind}
        if self.detail:
            result["detail"] = self.detail
        if self.insert_text:
            result["insertText"] = self.insert_text
        return result


@dataclass
class Location:
    """LSP Location."""

    uri: str
    range: Range

    def to_dict(self) -> dict[str, Any]:
        return {"uri": self.uri, "range": self.range.to_dict()}


# ── Helen keywords for completion ─────────────────────────────

HELLEN_KEYWORDS = [
    # Agent keywords
    "agent", "main", "prompt", "description", "model", "temperature",
    "max-turns", "tools", "streaming",
    # Variable declarations
    "let", "const", "shared",
    # Control flow
    "if", "else", "for", "in", "while",
    "break", "continue", "return",
    # Functions
    "fn", "call", "alias",
    # Error handling
    "try", "catch", "finally", "throw", "assert",
    # Pattern matching
    "match", "case", "branch", "default",
    # Imports
    "import", "as",
    # LLM keywords
    "llm", "act",
    # Async
    "async", "await",
    # Protocol/Interface (v1.7)
    "protocol", "impl", "is",
    # Agent functions block
    "functions",
    # Literals
    "true", "false", "null",
    # Chinese keywords (v1.10 — bilingual support)
    "让", "常量", "函数", "返回",       # let, const, fn, return
    "如果", "否则", "对于", "属于", "当",  # if, else, for, in, while
    "中断", "继续",                     # break, continue
    "匹配", "情况", "默认", "分支",       # match, case, default, branch
    "尝试", "捕获", "最终", "抛出", "断言",  # try, catch, finally, throw, assert
    "真", "假", "空", "是",             # true, false, null, is
    "智能体", "大模型", "执行",               # agent, llm, act
    "异步", "等待",                     # async, await
    "提示", "描述", "模型", "工具",       # prompt, description, model, tools
    "流式输出", "温度", "最大轮次",        # streaming, temperature, max-turns
    "函数区", "主函",                   # functions, main
    "导入", "作为",                     # import, as
    "协议", "实现",                     # protocol, impl
    "共享", "别名",                     # shared, alias
]

HELLEN_TYPES = [
    "str", "int", "float", "bool", "list", "dict", "map",
    "any", "void", "number",
]


# ── LSP Server ─────────────────────────────────────────────────

@dataclass
class DocumentState:
    """State for an open document."""

    uri: str
    content: str = ""
    version: int = 0
    diagnostics: list[Diagnostic] = field(default_factory=list)


class HelenLanguageServer:
    """LSP server for the Helen language.

    Handles JSON-RPC messages on stdin/stdout.
    """

    def __init__(self) -> None:
        self.documents: dict[str, DocumentState] = {}
        self.capabilities = {
            "textDocumentSync": 2,  # Incremental
            "completionProvider": {
                "triggerCharacters": [".", '"', "'", " "],
                "resolveProvider": False,
            },
            "definitionProvider": True,
            "diagnosticProvider": {
                "interFileDependencies": False,
                "workspaceDiagnostics": False,
            },
        }

    # ── Message handling ───────────────────────────────────

    def handle_message(self, message: dict[str, Any]) -> dict[str, Any] | None:
        """Handle a JSON-RPC message and return the response."""
        method = message.get("method")
        msg_id = message.get("id")
        params = message.get("params", {})

        # Request (has id)
        if msg_id is not None:
            result = self._handle_request(method, params)
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": result,
            }

        # Notification (no id)
        self._handle_notification(method, params)
        return None

    def _handle_request(self, method: str, params: dict[str, Any]) -> Any:
        """Handle a JSON-RPC request."""
        if method == "initialize":
            return self._initialize(params)
        elif method == "shutdown":
            return None
        elif method == "textDocument/completion":
            return self._completion(params)
        elif method == "textDocument/definition":
            return self._definition(params)
        elif method == "textDocument/diagnostic":
            return self._diagnostic(params)
        else:
            return None

    def _handle_notification(self, method: str, params: dict[str, Any]) -> None:
        """Handle a JSON-RPC notification."""
        if method == "initialized":
            pass  # Server is ready
        elif method == "exit":
            sys.exit(0)
        elif method == "textDocument/didOpen":
            self._did_open(params)
        elif method == "textDocument/didChange":
            self._did_change(params)
        elif method == "textDocument/didClose":
            self._did_close(params)

    # ── LSP Methods ────────────────────────────────────────

    def _initialize(self, params: dict[str, Any]) -> dict[str, Any]:
        """Handle initialize request."""
        _log(f"initialize — helen-lsp 1.10.0, pid={__import__('os').getpid()}")
        return {
            "capabilities": self.capabilities,
            "serverInfo": {
                "name": "helen-lsp",
                "version": "1.10.0",
            },
        }

    def _did_open(self, params: dict[str, Any]) -> None:
        """Handle textDocument/didOpen."""
        doc = params.get("textDocument", {})
        uri = doc.get("uri", "")
        content = doc.get("text", "")
        version = doc.get("version", 0)

        _log(f"didOpen: {uri} ({len(content)} chars, version={version})")
        self.documents[uri] = DocumentState(
            uri=uri, content=content, version=version
        )
        self._publish_diagnostics(uri)

    def _did_change(self, params: dict[str, Any]) -> None:
        """Handle textDocument/didChange."""
        uri = params.get("textDocument", {}).get("uri", "")
        version = params.get("textDocument", {}).get("version", 0)
        changes = params.get("contentChanges", [])

        doc = self.documents.get(uri)
        if doc is None:
            return

        doc.version = version

        # Apply changes (full sync for simplicity)
        for change in changes:
            if "text" in change:
                if "range" in change:
                    # Incremental update (simplified: replace all)
                    doc.content = change["text"]
                else:
                    # Full content replacement
                    doc.content = change["text"]

        self._publish_diagnostics(uri)

    def _did_close(self, params: dict[str, Any]) -> None:
        """Handle textDocument/didClose."""
        uri = params.get("textDocument", {}).get("uri", "")
        self.documents.pop(uri, None)

    def _completion(self, params: dict[str, Any]) -> dict[str, Any]:
        """Handle textDocument/completion."""
        uri = params.get("textDocument", {}).get("uri", "")
        _ = params.get("position", {})  # position available for future filtering

        doc = self.documents.get(uri)
        if doc is None:
            return {"isIncomplete": False, "items": []}

        items = []

        # Add keywords
        for kw in HELLEN_KEYWORDS:
            items.append(
                CompletionItem(
                    label=kw, kind=14,  # Keyword
                    detail="Helen keyword"
                ).to_dict()
            )

        # Add types
        for t in HELLEN_TYPES:
            items.append(
                CompletionItem(
                    label=t, kind=8,  # Interface (type)
                    detail="Helen type"
                ).to_dict()
            )

        # Add built-in function completions from stdlib
        try:
            from helen.stdlib import stdlib  # noqa: PLC0415
            # Include both canonical names and aliases in completion
            seen_labels: set[str] = set()
            for func in stdlib.list_all():
                items.append(
                    CompletionItem(
                        label=func.name,
                        kind=3,  # Function
                        detail=func.description,
                        insert_text=f"{func.name}(",
                    ).to_dict()
                )
                seen_labels.add(func.name)
            # Add aliases (these resolve to the same canonical function)
            for alias, canonical in stdlib.aliases.items():
                if alias not in seen_labels:
                    items.append(
                        CompletionItem(
                            label=alias,
                            kind=3,  # Function
                            detail=f"alias of {canonical}",
                            insert_text=f"{alias}(",
                        ).to_dict()
                    )
                    seen_labels.add(alias)
        except ImportError:
            pass

        return {"isIncomplete": False, "items": items}

    def _definition(self, params: dict[str, Any]) -> list[dict[str, Any]]:
        """Handle textDocument/definition (go to definition)."""
        uri = params.get("textDocument", {}).get("uri", "")
        position = params.get("position", {})

        doc = self.documents.get(uri)
        if doc is None:
            _log(f"definition: doc not found for {uri}")
            return []

        line_num = position.get("line", 0) + 1  # 1-based
        char_num = position.get("character", 0) + 1

        result = self._find_definition_at(doc.content, uri, line_num, char_num)
        _log(f"definition: line={line_num} col={char_num} → {result}")
        return result

    def _find_definition_at(
        self, content: str, uri: str, line: int, col: int
    ) -> list[dict[str, Any]]:
        """Find the definition at a given position.

        Simplified implementation: scans for agent/fn/let declarations.
        """
        import re  # noqa: PLC0415

        lines = content.split("\n")
        if 0 < line <= len(lines):
            current_line = lines[line - 1]
            # Get word at cursor position
            word_match = re.findall(r'\b\w+\b', current_line)
            if not word_match:
                return []

            # Find the word under cursor
            target = None
            for word in word_match:
                idx = current_line.find(word)
                if idx <= col - 1 <= idx + len(word):
                    target = word
                    break

            if target is None:
                return []

            # Search for declaration in the document
            # \w in Python 3 matches Unicode word chars (incl. CJK) by default
            patterns = [
                rf'agent\s+({target})\s*[\({{{{]',                   # agent decl
                rf'fn\s+({target})\s*\(',                            # function decl
                rf'(?:shared\s+)?(?:let|const|让|常量)\s+({target})\s*=',  # variable decl
            ]

            for i, file_line in enumerate(lines):
                for pattern in patterns:
                    match = re.search(pattern, file_line)
                    if match:
                        start = Position(line=i, character=match.start(1))
                        end = Position(line=i, character=match.end(1))
                        return [
                            Location(
                                uri=uri,
                                range=Range(start=start, end=end),
                            ).to_dict()
                        ]

        return []

    def _diagnostic(self, params: dict[str, Any]) -> dict[str, Any]:
        """Handle textDocument/diagnostic."""
        uri = params.get("textDocument", {}).get("uri", "")
        doc = self.documents.get(uri)
        if doc is None:
            return {"kind": "full", "items": []}

        return {
            "kind": "full",
            "items": [d.to_dict() for d in doc.diagnostics],
        }

    # ── Analysis ───────────────────────────────────────────

    def _publish_diagnostics(self, uri: str) -> None:
        """Analyze document and publish diagnostics."""
        doc = self.documents.get(uri)
        if doc is None:
            return

        try:
            diagnostics = self._analyze(doc.content)
        except Exception as e:
            _log(f"analysis error for {uri}: {e!r}")
            diagnostics = []
        doc.diagnostics = diagnostics

        # Send publishDiagnostics notification
        notification = {
            "jsonrpc": "2.0",
            "method": "textDocument/publishDiagnostics",
            "params": {
                "uri": uri,
                "diagnostics": [d.to_dict() for d in diagnostics],
            },
        }
        self._send(notification)

    def _analyze(self, content: str) -> list[Diagnostic]:
        """Analyze source code and return diagnostics.

        Runs Lex → Parse → Analyze pipeline and converts errors to LSP diagnostics.
        """
        diagnostics = []

        try:
            from helen.core.errors import ErrorReporter  # noqa: PLC0415
            from helen.core.lexer import Scanner  # noqa: PLC0415
            from helen.core.parser import Parser  # noqa: PLC0415
            from helen.semantic.analyzer import SemanticAnalyzer  # noqa: PLC0415

            errors = ErrorReporter()

            # Lex
            try:
                scanner = Scanner(source=content, file="<lsp>")
                tokens = scanner.scan_all()
            except Exception:
                return [
                    Diagnostic(
                        range=Range(
                            start=Position(line=0, character=0),
                            end=Position(line=0, character=1),
                        ),
                        severity=1,
                        message="Lexer error: failed to tokenize source",
                        code="LEX",
                    )
                ]

            # Parse
            parser = Parser(tokens, errors=errors)
            program = parser.parse()

            # Convert parser errors
            for err in errors.errors:
                if err.span:
                    start = Position(
                        line=err.span.start_line - 1,
                        character=err.span.start_col - 1,
                    )
                    end = Position(
                        line=err.span.end_line - 1,
                        character=err.span.end_col - 1,
                    )
                else:
                    start = Position(line=0, character=0)
                    end = Position(line=0, character=1)

                diagnostics.append(
                    Diagnostic(
                        range=Range(start=start, end=end),
                        severity=1,  # Error
                        message=err.message,
                        code=f"E{err.code.value:04d}",
                    )
                )

            if not errors.has_errors:
                # Analyze
                errors.reset()
                analyzer = SemanticAnalyzer(errors)
                analyzer.analyze(program)

                for err in errors.errors:
                    if err.span:
                        start = Position(
                            line=err.span.start_line - 1,
                            character=err.span.start_col - 1,
                        )
                        end = Position(
                            line=err.span.end_line - 1,
                            character=err.span.end_col - 1,
                        )
                    else:
                        start = Position(line=0, character=0)
                        end = Position(line=0, character=1)

                    diagnostics.append(
                        Diagnostic(
                            range=Range(start=start, end=end),
                            severity=1,  # Error
                            message=err.message,
                            code=f"E{err.code.value:04d}",
                        )
                    )

        except ImportError:
            # helen package not available, skip analysis
            pass

        return diagnostics

    # ── I/O ────────────────────────────────────────────────

    def _send(self, message: dict[str, Any]) -> None:
        """Send a JSON-RPC message via stdout."""
        body = json.dumps(message, ensure_ascii=False)
        body_bytes = body.encode("utf-8")
        sys.stdout.buffer.write(
            f"Content-Length: {len(body_bytes)}\r\n"
            f"Content-Type: application/vscode-jsonrpc; charset=utf-8\r\n\r\n"
            .encode("utf-8")
        )
        sys.stdout.buffer.write(body_bytes)
        sys.stdout.buffer.flush()

    def run(self) -> None:
        """Run the LSP server, reading JSON-RPC from stdin."""
        content_length = 0

        while True:
            # Read headers
            while True:
                line = sys.stdin.buffer.readline()
                if not line:
                    return  # EOF

                if line == b"\r\n":
                    break  # End of headers

                if line.startswith(b"Content-Length: "):
                    content_length = int(line.split(b": ")[1])

            # Read body
            body = b""
            while len(body) < content_length:
                chunk = sys.stdin.buffer.read(content_length - len(body))
                if not chunk:
                    return  # EOF
                body += chunk

            # Parse and handle
            message = json.loads(body.decode("utf-8"))
            response = self.handle_message(message)
            if response is not None:
                self._send(response)
