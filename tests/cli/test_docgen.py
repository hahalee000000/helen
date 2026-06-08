"""Tests for Helen CLI — doc command."""

import os
import tempfile
import json

from helen.cli.docgen import (
    generate_docs, format_markdown, extract_agent_doc,
    extract_function_doc, parse_source,
)


class TestDocgenBasics:
    """Test documentation generation."""

    def test_generate_docs_empty(self):
        """No files → empty docs."""
        docs = generate_docs([], include_builtins=True)
        assert "agents" in docs
        assert "functions" in docs
        assert "builtins" in docs

    def test_generate_docs_nonexistent_file(self):
        """Nonexistent file → silently skipped."""
        docs = generate_docs(["/nonexistent/file.helen"])
        assert docs["agents"] == []
        assert docs["functions"] == []

    def test_generate_docs_with_agent(self):
        """Single agent file → documented."""
        code = """
agent Greeter {
    description "A friendly greeter"
    model "gpt-4"

    prompt "You greet people"

    main {
        let msg = "Hello"
    }
}
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".helen", delete=False) as f:
            f.write(code)
            f.flush()
            try:
                docs = generate_docs([f.name])
                assert len(docs["agents"]) == 1
                assert docs["agents"][0]["name"] == "Greeter"
                assert docs["agents"][0]["description"] == "A friendly greeter"
                assert docs["agents"][0]["model"] == "gpt-4"
            finally:
                os.unlink(f.name)

    def test_generate_docs_with_function(self):
        """Function declaration → documented."""
        code = """
fn greet(name: string) {
    let msg = "Hello, " + name
}
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".helen", delete=False) as f:
            f.write(code)
            f.flush()
            try:
                docs = generate_docs([f.name])
                assert len(docs["functions"]) == 1
                assert docs["functions"][0]["name"] == "greet"
                assert "name" in docs["functions"][0]["params"]
            finally:
                os.unlink(f.name)

    def test_generate_docs_no_builtins(self):
        """include_builtins=False → no builtins."""
        docs = generate_docs([], include_builtins=False)
        assert "builtins" not in docs

    def test_generate_docs_with_builtins(self):
        """include_builtins=True → stdlib included."""
        docs = generate_docs([], include_builtins=True)
        assert len(docs["builtins"]) > 0
        # Check some well-known builtins exist
        builtin_names = {b["name"] for b in docs["builtins"]}
        assert "print" in builtin_names
        assert "len" in builtin_names
        assert "upper" in builtin_names
        assert "sqrt" in builtin_names


class TestMarkdownFormat:
    """Test Markdown documentation output."""

    def test_markdown_header(self):
        """Output starts with H1 header."""
        docs = generate_docs([])
        md = format_markdown(docs)
        assert "# Helen API Documentation" in md

    def test_markdown_agents_section(self):
        """Agents section rendered."""
        code = """
agent TestAgent {
    description "Test agent"

    main {
        let x = 1
    }
}
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".helen", delete=False) as f:
            f.write(code)
            f.flush()
            try:
                docs = generate_docs([f.name])
                md = format_markdown(docs)
                assert "## Agents" in md
                assert "### `TestAgent`" in md
                assert "Test agent" in md
            finally:
                os.unlink(f.name)

    def test_markdown_builtins_section(self):
        """Builtins section rendered with table."""
        docs = generate_docs([], include_builtins=True)
        md = format_markdown(docs)
        assert "Built-in Functions" in md
        assert "| Function |" in md


class TestJsonFormat:
    """Test JSON documentation output."""

    def test_json_serializable(self):
        """Docs are JSON serializable."""
        code = """
agent TestAgent {
    description "Test"
    main { let x = 1 }
}
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".helen", delete=False) as f:
            f.write(code)
            f.flush()
            try:
                docs = generate_docs([f.name])
                json_str = json.dumps(docs, indent=2)
                parsed = json.loads(json_str)
                assert parsed["agents"][0]["name"] == "TestAgent"
            finally:
                os.unlink(f.name)


class TestExtractDoc:
    """Test individual doc extraction."""

    def test_extract_agent_with_params(self):
        """Extract agent doc with parameters."""
        from helen.core.ast import AgentDeclNode, AgentParamNode, MainBlockNode, LiteralNode
        from helen.core.source import SourceSpan

        param = AgentParamNode(
            name="name", type_annotation=None, default_value=None,
            span=SourceSpan("<test>", 1, 1, 1, 5),
        )
        agent = AgentDeclNode(
            name="Greeter", params=[param], declarations=[],
            prompt=None, logic=MainBlockNode(body=[], span=SourceSpan("<test>", 1, 1, 1, 5)),
            span=SourceSpan("<test>", 1, 1, 1, 5),
        )

        doc = extract_agent_doc(agent, "test.helen")
        assert doc.name == "Greeter"
        assert len(doc.params) == 1
        assert doc.params[0]["name"] == "name"
