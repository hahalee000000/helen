"""Tests for Helen LSP Server (HLD M12)."""

from helen.lsp.server import (
    HelenLanguageServer, Position, Range, Diagnostic,
    CompletionItem, Location, HELLEN_KEYWORDS, HELLEN_CONTEXT_KEYWORDS,
    HELLEN_SNIPPETS, HELLEN_TYPES, _KEYWORD_DESCRIPTIONS,
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
        assert caps["textDocumentSync"] == 1  # Full (not incremental — server does full replacement)

    def test_capabilities_include_hover(self):
        """Capabilities include hoverProvider (v1.30.5)."""
        server = HelenLanguageServer()
        caps = server.capabilities
        assert caps.get("hoverProvider") is True

    def test_capabilities_include_document_symbol(self):
        """Capabilities include documentSymbolProvider (v1.30.5)."""
        server = HelenLanguageServer()
        caps = server.capabilities
        assert caps.get("documentSymbolProvider") is True

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
                "text": "const X = 1",
                "version": 1,
            }
        })
        assert "file:///test.helen" in server.documents
        doc = server.documents["file:///test.helen"]
        assert doc.content == "const X = 1"
        assert doc.version == 1

    def test_did_change_updates_content(self):
        """didChange updates document content."""
        server = HelenLanguageServer()
        server._did_open({
            "textDocument": {
                "uri": "file:///test.helen",
                "text": "const X = 1",
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
                "text": "const X = 1",
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
        content = "const X = 1"
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
        diagnostics = server._analyze("const X = 1")
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


# ═══════════════════════════════════════════════════════════════════════
# v1.23.5 regression tests: LSP import resolution with file URI
# ═══════════════════════════════════════════════════════════════════════


class TestUriToPath:
    """v1.23.5 fix: _uri_to_path converts file:// URIs to filesystem paths.

    Before v1.23.5, _analyze hard-coded '<lsp>' as the file name. This
    caused SemanticAnalyzer.visit_import_stmt to fall back to base_dir
    (process CWD) when resolving relative imports, producing spurious
    'import file not found' diagnostics.
    """

    def test_file_uri_to_path(self):
        server = type('S', (), {})()
        from helen.lsp.server import HelenLanguageServer
        result = HelenLanguageServer._uri_to_path("file:///tmp/helen_test/main.helen")
        assert result == "/tmp/helen_test/main.helen"

    def test_file_uri_with_encoded_chars(self):
        from helen.lsp.server import HelenLanguageServer
        result = HelenLanguageServer._uri_to_path(
            "file:///home/user/my%20project/test.helen"
        )
        assert result == "/home/user/my project/test.helen"

    def test_plain_path_passthrough(self):
        from helen.lsp.server import HelenLanguageServer
        result = HelenLanguageServer._uri_to_path("/tmp/plain/path.helen")
        assert result == "/tmp/plain/path.helen"

    def test_analyze_with_uri_resolves_imports(self, tmp_path):
        """End-to-end: _analyze with file URI finds sibling import."""
        from helen.lsp.server import HelenLanguageServer

        # Create two files: main.helen imports ./helper.helen
        helper = tmp_path / "helper.helen"
        helper.write_text("agent Helper { main { } }\n")

        main = tmp_path / "main.helen"
        main.write_text(
            'import "./helper.helen"\n\n'
            "agent Runner { main { Helper() } }\n"
        )

        server = HelenLanguageServer.__new__(HelenLanguageServer)
        diagnostics = server._analyze(main.read_text(), main.as_uri())

        # Should NOT contain "import file not found" error
        error_messages = [d.message for d in diagnostics if d.severity == 1]
        assert not any("import file not found" in m for m in error_messages), (
            f"Import error still reported: {error_messages}"
        )

    def test_analyze_without_uri_reports_missing_import(self, tmp_path):
        """Without URI, relative imports cannot be resolved (baseline)."""
        from helen.lsp.server import HelenLanguageServer

        main = tmp_path / "main.helen"
        main.write_text(
            'import "./nonexistent.helen"\n\n'
            "agent Runner { main { } }\n"
        )

        server = HelenLanguageServer.__new__(HelenLanguageServer)
        diagnostics = server._analyze(main.read_text(), "")  # no URI

        error_messages = [d.message for d in diagnostics if d.severity == 1]
        assert any("import file not found" in m for m in error_messages), (
            "Expected 'import file not found' when URI is missing"
        )


class TestLspKeywords:
    """Test comprehensive keyword coverage (v1.30.5 update)."""

    def test_formal_keywords_from_tokens(self):
        """HELLEN_KEYWORDS contains all 91 formal keywords from tokens.py."""
        from helen.core.tokens import keywords
        formal = set(keywords().keys())
        # All formal keywords should be in the completion list
        missing = formal - set(HELLEN_KEYWORDS)
        assert not missing, f"Formal keywords missing from LSP completion: {missing}"

    def test_context_keywords_present(self):
        """HELLEN_CONTEXT_KEYWORDS includes spawn/channel/callback keywords."""
        # Note: 'spawn' is a formal keyword (in tokens.py), so it's in HELLEN_KEYWORDS,
        # not HELLEN_CONTEXT_KEYWORDS. This test covers context keywords that are
        # recognized by the parser as identifiers with contextual meaning.
        expected = {
            "Channel", "send", "receive", "try_receive", "cancel",
            "close", "mailbox_select", "on_chunk", "on_complete",
            "on_tool_end", "on_media", "on_generate", "media", "provider",
            "context", "memory", "resume", "expect",
        }
        actual = set(HELLEN_CONTEXT_KEYWORDS)
        missing = expected - actual
        assert not missing, f"Context keywords missing: {missing}"

    def test_chinese_formal_keywords_present(self):
        """Chinese formal keywords are in the completion list."""
        expected_cn = {
            "智能体", "大模型", "执行", "分生", "设", "定义", "常量",
            "函数", "返回", "如果", "否则", "对于", "属于", "当",
            "中断", "继续", "匹配", "情况", "默认", "分支",
            "尝试", "捕获", "最终", "抛出", "断言", "真", "假",
            "空", "是", "提示词", "描述", "模型", "工具",
            "流式输出", "温度", "最大轮次", "函数区", "主函",
            "导入", "作为", "协议", "实现", "共享", "别名", "仓库", "记录",
        }
        actual = set(HELLEN_KEYWORDS)
        missing = expected_cn - actual
        assert not missing, f"Chinese keywords missing from LSP: {missing}"

    def test_keyword_descriptions_cover_keywords(self):
        """Every formal + context keyword has a hover description."""
        all_keywords = set(HELLEN_KEYWORDS + HELLEN_CONTEXT_KEYWORDS)
        missing = all_keywords - set(_KEYWORD_DESCRIPTIONS.keys())
        assert not missing, f"Keywords without hover descriptions: {missing}"


class TestLspSnippets:
    """Test snippet templates (v1.30.5)."""

    def test_snippets_are_valid(self):
        """Each snippet has required fields."""
        for s in HELLEN_SNIPPETS:
            assert "label" in s, f"Snippet missing label: {s}"
            assert "detail" in s, f"Snippet missing detail: {s}"
            assert "insertText" in s, f"Snippet missing insertText: {s}"

    def test_key_snippets_exist(self):
        """Key snippet templates exist."""
        labels = {s["label"] for s in HELLEN_SNIPPETS}
        expected = {"agent", "fn", "llm act", "llm if", "shared store",
                    "spawn", "match", "try", "for", "while", "import",
                    "protocol", "@sandbox", "@open", "@strict"}
        missing = expected - labels
        assert not missing, f"Key snippets missing: {missing}"

    def test_completion_returns_snippets(self):
        """Completion response includes snippet items."""
        server = HelenLanguageServer()
        uri = "file:///test.helen"
        server.documents[uri] = __import__('helen.lsp.server', fromlist=['DocumentState']).DocumentState(
            uri=uri, content="agent Test {\n  main { }\n}\n", version=1
        )
        result = server._completion({
            "textDocument": {"uri": uri},
            "position": {"line": 2, "character": 10},
        })
        labels = [item["label"] for item in result["items"]]
        assert "agent" in labels, "agent snippet not in completion"
        # Snippet items should have insertTextFormat=2
        agent_items = [item for item in result["items"] if item["label"] == "agent"]
        assert any(item.get("insertTextFormat") == 2 for item in agent_items)


class TestLspHover:
    """Test hover support (v1.30.5)."""

    def _make_server_with_doc(self, content: str) -> tuple:
        server = HelenLanguageServer()
        uri = "file:///test.helen"
        server.documents[uri] = __import__('helen.lsp.server', fromlist=['DocumentState']).DocumentState(
            uri=uri, content=content, version=1
        )
        return server, uri

    def test_hover_on_keyword(self):
        """Hover on a keyword returns its description."""
        server, uri = self._make_server_with_doc("agent Test {\n  main { }\n}\n")
        result = server._hover({
            "textDocument": {"uri": uri},
            "position": {"line": 0, "character": 2},  # on 'agent'
        })
        assert result is not None
        assert "agent" in result["contents"]["value"].lower()

    def test_hover_on_user_function(self):
        """Hover on a user-defined function shows declaration."""
        server, uri = self._make_server_with_doc("fn greet(name: str): str {\n  return name\n}\n")
        result = server._hover({
            "textDocument": {"uri": uri},
            "position": {"line": 0, "character": 4},  # on 'greet'
        })
        assert result is not None
        assert "greet" in result["contents"]["value"]

    def test_hover_on_agent_declaration(self):
        """Hover on an agent shows agent declaration."""
        server, uri = self._make_server_with_doc("agent MyBot {\n  description \"test\"\n  main { }\n}\n")
        result = server._hover({
            "textDocument": {"uri": uri},
            "position": {"line": 0, "character": 8},  # on 'MyBot'
        })
        assert result is not None
        assert "MyBot" in result["contents"]["value"]
        assert "Agent" in result["contents"]["value"]

    def test_hover_unknown_symbol_returns_none(self):
        """Hover on unknown symbol returns None."""
        server, uri = self._make_server_with_doc("let x = 42\n")
        result = server._hover({
            "textDocument": {"uri": uri},
            "position": {"line": 0, "character": 20},  # beyond line content
        })
        assert result is None


class TestLspDocumentSymbols:
    """Test document symbol support (v1.30.5)."""

    def _make_server_with_doc(self, content: str) -> tuple:
        server = HelenLanguageServer()
        uri = "file:///test.helen"
        server.documents[uri] = __import__('helen.lsp.server', fromlist=['DocumentState']).DocumentState(
            uri=uri, content=content, version=1
        )
        return server, uri

    def test_symbols_includes_agent(self):
        """Agent declarations appear in document symbols."""
        server, uri = self._make_server_with_doc("agent MyAgent {\n  description \"test\"\n  main { }\n}\n")
        result = server._document_symbol({"textDocument": {"uri": uri}})
        names = [s["name"] for s in result]
        assert any("MyAgent" in n for n in names), f"Agent not in symbols: {names}"

    def test_symbols_includes_function(self):
        """Top-level function declarations appear in document symbols."""
        server, uri = self._make_server_with_doc("fn helper(): void {\n  return\n}\n")
        result = server._document_symbol({"textDocument": {"uri": uri}})
        names = [s["name"] for s in result]
        assert any("helper" in n for n in names), f"Function not in symbols: {names}"

    def test_symbols_includes_variable(self):
        """Variable declarations appear in document symbols."""
        server, uri = self._make_server_with_doc("let counter = 0\n")
        result = server._document_symbol({"textDocument": {"uri": uri}})
        names = [s["name"] for s in result]
        assert "counter" in names, f"Variable not in symbols: {names}"

    def test_symbols_nested_in_agent(self):
        """Functions inside agent {} are nested as children."""
        content = (
            "agent Bot {\n"
            "  description \"bot\"\n"
            "  functions {\n"
            "    fn tool_call(): void { return }\n"
            "  }\n"
            "  main { }\n"
            "}\n"
        )
        server, uri = self._make_server_with_doc(content)
        result = server._document_symbol({"textDocument": {"uri": uri}})
        # Find the agent symbol
        agent_syms = [s for s in result if "Bot" in s["name"]]
        assert len(agent_syms) == 1, f"Expected one agent symbol: {result}"
        agent = agent_syms[0]
        # Agent should have children (functions)
        children = agent.get("children", [])
        child_names = [c["name"] for c in children]
        assert any("tool_call" in n for n in child_names), (
            f"Function not nested in agent: {child_names}"
        )

    def test_symbols_empty_document(self):
        """Empty document returns empty symbols list."""
        server, uri = self._make_server_with_doc("")
        result = server._document_symbol({"textDocument": {"uri": uri}})
        assert result == []

    def test_symbols_decorated_agent(self):
        """Decorated agents appear with decorator in name."""
        server, uri = self._make_server_with_doc("@sandbox agent SafeBot {\n  main { }\n}\n")
        result = server._document_symbol({"textDocument": {"uri": uri}})
        names = [s["name"] for s in result]
        assert any("@sandbox" in n and "SafeBot" in n for n in names), (
            f"Decorated agent not in symbols: {names}"
        )
