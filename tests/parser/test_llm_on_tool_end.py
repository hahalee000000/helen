"""Tests for on_tool_end callback parsing in llm act.

v1.21: on_tool_end callback allows injecting hints into the agentic loop
after each tool execution. Returns str (user hint), dict (full message),
or None (no injection).
"""
from helen.core.lexer import Scanner
from helen.core.parser import Parser
from helen.core.errors import ErrorReporter
from helen.core.ast import LlmActExprNode, ExprStmtNode


def _format_errors(errors: ErrorReporter) -> str:
    return "\n".join(str(e) for e in errors.errors)


def _parse(source: str):
    """Parse source and return (program, errors)."""
    errors = ErrorReporter()
    scanner = Scanner(source=source, file="<test>")
    tokens = scanner.scan_all()
    parser = Parser(tokens, errors=errors)
    program = parser.parse()
    return program, errors


def _get_llm_act_node(source: str) -> LlmActExprNode:
    """Parse source and return the LlmActExprNode."""
    program, errors = _parse(source)
    assert not errors.has_errors, f"Parse errors: {_format_errors(errors)}"
    stmt = program.statements[0]
    if isinstance(stmt, ExprStmtNode):
        node = stmt.expression
    else:
        node = stmt
    assert isinstance(node, LlmActExprNode), f"Expected LlmActExprNode, got {type(node)}"
    return node


class TestOnToolEndParsing:
    """Test on_tool_end callback parsing."""

    def test_llm_act_with_on_tool_end(self):
        """Basic: llm act 'prompt' on_tool_end handler."""
        node = _get_llm_act_node('llm act "prompt" on_tool_end my_handler')
        assert node.on_tool_end is not None
        assert node.on_chunk is None
        assert node.on_complete is None

    def test_llm_act_with_all_callbacks(self):
        """All callbacks together: on_chunk + on_complete + on_tool_end."""
        source = (
            'llm act "prompt" '
            'on_chunk handle_chunk '
            'on_complete handle_done '
            'on_tool_end handle_tool'
        )
        node = _get_llm_act_node(source)
        assert node.on_chunk is not None
        assert node.on_complete is not None
        assert node.on_tool_end is not None

    def test_llm_act_on_tool_end_with_lambda(self):
        """Lambda form: on_tool_end fn(name, result) { ... }."""
        source = 'llm act "prompt" on_tool_end fn(name, result) { return null }'
        node = _get_llm_act_node(source)
        assert node.on_tool_end is not None

    def test_llm_act_on_tool_end_order_independent(self):
        """on_tool_end can appear before on_chunk."""
        source = (
            'llm act "prompt" '
            'on_tool_end handle_tool '
            'on_chunk handle_chunk'
        )
        node = _get_llm_act_node(source)
        assert node.on_tool_end is not None
        assert node.on_chunk is not None

    def test_llm_act_bare_form_with_on_tool_end(self):
        """Bare form: llm act on_tool_end handler."""
        node = _get_llm_act_node('llm act on_tool_end my_handler')
        assert node.prompt is None  # bare form
        assert node.on_tool_end is not None

    def test_llm_act_on_tool_end_without_other_callbacks(self):
        """on_tool_end alone, no other callbacks."""
        node = _get_llm_act_node('llm act "do something" on_tool_end handler')
        assert node.on_tool_end is not None
        assert node.on_chunk is None
        assert node.on_complete is None
        assert node.on_media is None
        assert node.on_generate == []


class TestOnToolEndChineseAlias:
    """Test Chinese alias 工具结束 for on_tool_end."""

    def test_chinese_alias_工具结束(self):
        """工具结束 as Chinese alias for on_tool_end."""
        node = _get_llm_act_node('llm act "prompt" 工具结束 my_handler')
        assert node.on_tool_end is not None

    def test_chinese_alias_with_other_callbacks(self):
        """Chinese aliases can be mixed with English."""
        source = (
            'llm act "prompt" '
            '逐块处理 handle_chunk '
            '完成 handle_done '
            '工具结束 handle_tool'
        )
        node = _get_llm_act_node(source)
        assert node.on_chunk is not None
        assert node.on_complete is not None
        assert node.on_tool_end is not None


class TestChineseAliasesForExistingCallbacks:
    """Test that Chinese aliases for on_chunk and on_complete work."""

    def test_逐块处理_for_on_chunk(self):
        """逐块处理 is Chinese alias for on_chunk."""
        node = _get_llm_act_node('llm act "prompt" 逐块处理 handle_chunk')
        assert node.on_chunk is not None
        assert node.on_complete is None

    def test_完成_for_on_complete(self):
        """完成 is Chinese alias for on_complete."""
        node = _get_llm_act_node('llm act "prompt" 完成 handle_done')
        assert node.on_complete is not None
        assert node.on_chunk is None

    def test_bare_form_with_chinese_aliases(self):
        """Bare form with Chinese alias."""
        node = _get_llm_act_node('llm act 逐块处理 handle_chunk')
        assert node.prompt is None
        assert node.on_chunk is not None

    def test_all_chinese_aliases_bare_form(self):
        """Bare form with all Chinese aliases."""
        node = _get_llm_act_node(
            'llm act 逐块处理 cb1 完成 cb2 工具结束 cb3'
        )
        assert node.prompt is None
        assert node.on_chunk is not None
        assert node.on_complete is not None
        assert node.on_tool_end is not None
