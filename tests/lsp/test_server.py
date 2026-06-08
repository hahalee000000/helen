"""Tests for Helen LSP Server (HLD M12)."""

from helen.lsp.server import (
    HelenLanguageServer, Position, Range, Diagnostic,
    CompletionItem, Location, HELLEN_KEYWORDS, HELLEN_TYPES,
)


class TestLspDataStructures:
    """Test LSP data structures."""

    def test_position_to_dict(self):
        """Position serializes correctly."""
        pos = Position(line=5, character=10)
        assert pos.to_dict() == {"line": 5, "character": 10}

    def test_range_to_dict(self):
        """Range serializes correctly."""
        r = Range(
            start=Position(line=0, character=0),
            end=Position(line=0, character=5),
        )
        expected = {
            "start": {"line": 0, "character": 0},
            "end": {"line": 0, "character": 5},
        }
        assert r.to_dict() == expected

    def test_diagnostic_to_dict(self):
        """Diagnostic serializes correctly."""
        d = Diagnostic(
            range=Range(
                start=Position(line=1, character=0),
                end=Position(line=1, character=5),
            ),
            severity=1,
            message="test error",
            code="E0301",
        )
        result = d.to_dict()
        assert result["severity"] == 1
        assert result["message"] == "test error"
        assert result["code"] == "E0301"
        assert result["source"] == "helen"

    def test_diagnostic_without_code(self):
        """Diagnostic without code omits it."""
        d = Diagnostic(
            range=Range(
                start=Position(line=0, character=0),
                end=Position(line=0, character=1),
            ),
            severity=1,
            message="error",
        )
        assert "code" not in d.to_dict()

    def test_completion_item_to_dict(self):
        """CompletionItem serializes correctly."""
        item = CompletionItem(
            label="agent", kind=14, detail="Helen keyword"
        )
        result = item.to_dict()
        assert result["label"] == "agent"
        assert result["kind"] == 14
        assert result["detail"] == "Helen keyword"

    def test_location_to_dict(self):
        """Location serializes correctly."""
        loc = Location(
            uri="file:///test.helen",
            range=Range(
                start=Position(line=0, character=0),
                end=Position(line=0, character=5),
            ),
        )
        result = loc.to_dict()
        assert result["uri"] == "file:///test.helen"
        assert "range" in result


class TestLspInitialize:
    """Test LSP server initialization."""

    def test_initialize_returns_capabilities(self):
        """Initialize response includes capabilities."""
        server = HelenLanguageServer()
        result = server._initialize({})
        assert "capabilities" in result
        assert "serverInfo" in result
        assert result["serverInfo"]["name"] == "helen-lsp"

    def test_capabilities_include_sync(self):
        """Capabilities include textDocumentSync."""
        server = HelenLanguageServer()
        caps = server.capabilities
        assert "textDocumentSync" in caps
        assert caps["textDocumentSync"] == 2  # Incremental

    def test_capabilities_include_completion(self):
        """Capabilities include completionProvider."""
        server = HelenLanguageServer()
        caps = server.capabilities
        assert "completionProvider" in caps
        assert "triggerCharacters" in caps["completionProvider"]

    def test_capabilities_include_definition(self):
        """Capabilities include definitionProvider."""
        server = HelenLanguageServer()
        caps = server.capabilities
        assert caps["definitionProvider"] is True


class TestLspDocumentLifecycle:
    """Test document open/change/close lifecycle."""

    def test_did_open_registers_document(self):
        """didOpen registers the document."""
        server = HelenLanguageServer()
        server._did_open({
            "textDocument": {
                "uri": "file:///test.helen",
                "text": "let x = 1",
                "version": 1,
            }
        })
        assert "file:///test.helen" in server.documents
        doc = server.documents["file:///test.helen"]
        assert doc.content == "let x = 1"
        assert doc.version == 1

    def test_did_change_updates_content(self):
        """didChange updates document content."""
        server = HelenLanguageServer()
        server._did_open({
            "textDocument": {
                "uri": "file:///test.helen",
                "text": "let x = 1",
                "version": 1,
            }
        })
        server._did_change({
            "textDocument": {"uri": "file:///test.helen", "version": 2},
            "contentChanges": [{"text": "let x = 2"}],
        })
        doc = server.documents["file:///test.helen"]
        assert doc.content == "let x = 2"
        assert doc.version == 2

    def test_did_close_removes_document(self):
        """didClose removes the document."""
        server = HelenLanguageServer()
        server._did_open({
            "textDocument": {
                "uri": "file:///test.helen",
                "text": "let x = 1",
                "version": 1,
            }
        })
        server._did_close({
            "textDocument": {"uri": "file:///test.helen"}
        })
        assert "file:///test.helen" not in server.documents


class TestLspCompletion:
    """Test completion provider."""

    def test_completion_includes_keywords(self):
        """Completion includes Helen keywords."""
        server = HelenLanguageServer()
        server._did_open({
            "textDocument": {
                "uri": "file:///test.helen",
                "text": "",
                "version": 1,
            }
        })
        result = server._completion({
            "textDocument": {"uri": "file:///test.helen"},
            "position": {"line": 0, "character": 0},
        })
        labels = {item["label"] for item in result["items"]}
        for kw in HELLEN_KEYWORDS:
            assert kw in labels

    def test_completion_includes_types(self):
        """Completion includes Helen types."""
        server = HelenLanguageServer()
        server._did_open({
            "textDocument": {
                "uri": "file:///test.helen",
                "text": "",
                "version": 1,
            }
        })
        result = server._completion({
            "textDocument": {"uri": "file:///test.helen"},
            "position": {"line": 0, "character": 0},
        })
        labels = {item["label"] for item in result["items"]}
        for t in HELLEN_TYPES:
            assert t in labels

    def test_completion_includes_builtins(self):
        """Completion includes stdlib builtins."""
        server = HelenLanguageServer()
        server._did_open({
            "textDocument": {
                "uri": "file:///test.helen",
                "text": "",
                "version": 1,
            }
        })
        result = server._completion({
            "textDocument": {"uri": "file:///test.helen"},
            "position": {"line": 0, "character": 0},
        })
        labels = {item["label"] for item in result["items"]}
        assert "print" in labels
        assert "len" in labels

    def test_completion_for_unknown_doc(self):
        """Completion for unknown document returns empty."""
        server = HelenLanguageServer()
        result = server._completion({
            "textDocument": {"uri": "file:///unknown.helen"},
            "position": {"line": 0, "character": 0},
        })
        assert result["items"] == []


class TestLspDefinition:
    """Test go-to-definition."""

    def test_definition_finds_agent(self):
        """Go-to-definition finds agent declaration."""
        server = HelenLanguageServer()
        content = "agent Greeter {\n    main { let x = 1 }\n}"
        server._did_open({
            "textDocument": {
                "uri": "file:///test.helen",
                "text": content,
                "version": 1,
            }
        })
        # Click on "Greeter" on line 0, col 7 (inside the word)
        result = server._find_definition_at(
            content, "file:///test.helen", line=1, col=7
        )
        # Should find "Greeter" at line 0
        assert len(result) == 1
        assert result[0]["uri"] == "file:///test.helen"

    def test_definition_finds_function(self):
        """Go-to-definition finds function declaration."""
        server = HelenLanguageServer()
        content = "fn greet(name) {\n    let msg = name\n}"
        server._did_open({
            "textDocument": {
                "uri": "file:///test.helen",
                "text": content,
                "version": 1,
            }
        })
        result = server._find_definition_at(
            content, "file:///test.helen", line=2, col=12
        )
        assert len(result) == 1

    def test_definition_finds_variable(self):
        """Go-to-definition finds variable declaration."""
        server = HelenLanguageServer()
        content = "let x = 1\nlet y = x + 1"
        server._did_open({
            "textDocument": {
                "uri": "file:///test.helen",
                "text": content,
                "version": 1,
            }
        })
        # Click on "y" on line 2 (1-indexed for LSP), col 5
        # "let y" - the "y" starts at col 4
        result = server._find_definition_at(
            content, "file:///test.helen", line=2, col=5
        )
        assert len(result) == 1

    def test_definition_not_found(self):
        """Go-to-definition returns empty for undefined symbol."""
        server = HelenLanguageServer()
        content = "let x = 1"
        server._did_open({
            "textDocument": {
                "uri": "file:///test.helen",
                "text": content,
                "version": 1,
            }
        })
        result = server._find_definition_at(
            content, "file:///test.helen", line=1, col=1
        )
        assert result == []

    def test_definition_empty_document(self):
        """Go-to-definition returns empty for unknown document."""
        server = HelenLanguageServer()
        result = server._definition({
            "textDocument": {"uri": "file:///unknown.helen"},
            "position": {"line": 0, "character": 0},
        })
        assert result == []


class TestLspDiagnostics:
    """Test diagnostic provider."""

    def test_analyze_valid_code_no_errors(self):
        """Valid code produces no diagnostics."""
        server = HelenLanguageServer()
        diagnostics = server._analyze("let x = 1")
        assert len(diagnostics) == 0

    def test_analyze_invalid_code_has_errors(self):
        """Invalid code produces diagnostics."""
        server = HelenLanguageServer()
        diagnostics = server._analyze("agent {")
        assert len(diagnostics) > 0
        assert all(d.severity == 1 for d in diagnostics)  # All errors

    def test_analyze_empty_code_no_errors(self):
        """Empty code produces no diagnostics."""
        server = HelenLanguageServer()
        diagnostics = server._analyze("")
        assert len(diagnostics) == 0

    def test_diagnostic_has_error_code(self):
        """Diagnostics include error codes."""
        server = HelenLanguageServer()
        diagnostics = server._analyze("agent {")
        if diagnostics:
            assert diagnostics[0].code is not None


class TestLspMessageHandling:
    """Test JSON-RPC message handling."""

    def test_handle_initialize_request(self):
        """Initialize request returns capabilities."""
        server = HelenLanguageServer()
        response = server.handle_message({
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {},
        })
        assert response is not None
        assert response["id"] == 1
        assert "capabilities" in response["result"]

    def test_handle_shutdown_request(self):
        """Shutdown request returns null."""
        server = HelenLanguageServer()
        response = server.handle_message({
            "jsonrpc": "2.0",
            "id": 2,
            "method": "shutdown",
            "params": {},
        })
        assert response is not None
        assert response["result"] is None

    def test_handle_unknown_method(self):
        """Unknown method returns null result."""
        server = HelenLanguageServer()
        response = server.handle_message({
            "jsonrpc": "2.0",
            "id": 3,
            "method": "unknown/method",
            "params": {},
        })
        assert response is not None
        assert response["result"] is None

    def test_handle_notification_no_response(self):
        """Notification returns None (no response)."""
        server = HelenLanguageServer()
        response = server.handle_message({
            "jsonrpc": "2.0",
            "method": "initialized",
            "params": {},
        })
        assert response is None
