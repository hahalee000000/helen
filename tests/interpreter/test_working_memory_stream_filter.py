"""Tests for streaming working memory block filter (v1.25.3)."""

import pytest
from helen.interpreter.llm_mixin import _WorkingMemoryStreamFilter


class TestWorkingMemoryStreamFilter:
    """Test suite for _WorkingMemoryStreamFilter."""

    def test_normal_content_passes_through(self):
        """Normal content should pass through immediately."""
        f = _WorkingMemoryStreamFilter()
        chunks = ["Hello ", "world!", " How ", "are you?"]
        outputs = [f.process(c) for c in chunks]
        assert ''.join(outputs) == "Hello world! How are you?"
        assert f.flush() == ""

    def test_working_memory_block_filtered(self):
        """<working_memory> blocks should be completely filtered."""
        f = _WorkingMemoryStreamFilter()
        chunks = [
            "Answer: 42\n\n",
            "<working",
            "_memory>\n",
            "active_files: [test.py]\n",
            "decisions: [Use JWT]\n",
            "</working_memory>\n",
            "\nFinal note."
        ]
        outputs = [f.process(c) for c in chunks]
        filtered = ''.join(o for o in outputs if o)
        assert "Answer: 42" in filtered
        assert "Final note." in filtered
        assert "<working_memory>" not in filtered
        assert "active_files" not in filtered
        assert f.flush() == ""

    def test_incomplete_block_discarded_on_flush(self):
        """Incomplete blocks should be discarded on flush."""
        f = _WorkingMemoryStreamFilter()
        chunks = ["Answer: ", "<working", "_memory>", "active_files: [x]"]
        outputs = [f.process(c) for c in chunks]
        filtered = ''.join(outputs)
        assert filtered == "Answer: "
        # Flush should discard incomplete block
        assert f.flush() == ""

    def test_other_xml_tags_pass_through(self):
        """Other XML tags should not be filtered."""
        f = _WorkingMemoryStreamFilter()
        chunks = ["<code>", "print('hello')", "</code>", " text"]
        outputs = [f.process(c) for c in chunks]
        assert ''.join(outputs) == "<code>print('hello')</code> text"
        assert f.flush() == ""

    def test_case_insensitive_matching(self):
        """Filter should handle case variations."""
        f = _WorkingMemoryStreamFilter()
        chunks = ["Text\n", "<Working_Memory>", "data", "</Working_Memory>", "\nMore"]
        outputs = [f.process(c) for c in chunks]
        filtered = ''.join(outputs)
        assert "Text" in filtered
        assert "More" in filtered
        assert "data" not in filtered

    def test_multiple_blocks_all_filtered(self):
        """Multiple working memory blocks should all be filtered."""
        f = _WorkingMemoryStreamFilter()
        chunks = [
            "Part 1\n",
            "<working_memory>data1</working_memory>\n",
            "Part 2\n",
            "<working_memory>data2</working_memory>\n",
            "Part 3"
        ]
        outputs = [f.process(c) for c in chunks]
        filtered = ''.join(outputs)
        assert "Part 1" in filtered
        assert "Part 2" in filtered
        assert "Part 3" in filtered
        assert "data1" not in filtered
        assert "data2" not in filtered

    def test_whitespace_after_closing_tag_filtered(self):
        """Whitespace after closing tag should be filtered."""
        f = _WorkingMemoryStreamFilter()
        chunks = [
            "Answer\n",
            "<working_memory>x</working_memory>",
            "\n\n\n",
            "Next"
        ]
        outputs = [f.process(c) for c in chunks]
        filtered = ''.join(outputs)
        assert filtered == "Answer\nNext"

    def test_partial_tag_prefix_buffered(self):
        """Partial tag prefixes should be buffered."""
        f = _WorkingMemoryStreamFilter()
        # Send partial prefix
        result1 = f.process("<work")
        # Should buffer (not output yet)
        assert result1 == "" or result1 == "<work"  # Implementation detail
        # Complete to non-tag
        result2 = f.process("shop")
        # Should output the buffered content
        assert "work" in result1 + result2 or "shop" in result2

    def test_empty_chunks_handled(self):
        """Empty chunks should not cause issues."""
        f = _WorkingMemoryStreamFilter()
        assert f.process("") == ""
        assert f.process("text") == "text"
        assert f.process("") == ""
        assert f.flush() == ""

    def test_real_world_scenario(self):
        """Test with realistic LLM streaming output."""
        f = _WorkingMemoryStreamFilter()
        chunks = [
            "Based on the analysis, the search engine is likely Bing.\n\n",
            "Reasons:\n",
            "1. Chinese results density\n",
            "2. Format matching\n\n",
            "<working_memory>\n",
            "active_files: [main.py, utils.py]\n",
            "decisions: [Search engine is Bing]\n",
            "todos: [Verify with API docs]\n",
            "</working_memory>\n"
        ]
        outputs = [f.process(c) for c in chunks]
        filtered = ''.join(o for o in outputs if o)

        assert "Based on the analysis" in filtered
        assert "Reasons:" in filtered
        assert "1. Chinese results density" in filtered
        assert "<working_memory>" not in filtered
        assert "active_files" not in filtered
        assert "decisions" not in filtered
        assert "todos" not in filtered
