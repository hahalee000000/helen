"""Test that <working_memory> block is removed from LLM responses (v1.25.1 fix).

This test verifies that when the LLM includes a <working_memory> block in its
response, the block is extracted for working memory updates but removed from
the response text returned to the user.
"""

import pytest
from helen.interpreter.interpreter import Interpreter
from helen.interpreter.agent_context import AgentContextManager
from helen.runtime.llm_runtime import MockLLMRuntime


class TestWorkingMemoryBlockRemoval:
    """Test that <working_memory> blocks are stripped from responses."""

    def test_working_memory_block_removed_from_response(self):
        """Test that _apply_working_memory_update removes the block."""
        interp = Interpreter(llm_runtime=MockLLMRuntime())
        interp._agent_context = AgentContextManager()

        response_with_block = """
Here is my response to your question.

<working_memory>
active_files: [main.py, utils.py]
decisions: [Use async pattern]
todos: [Add tests]
</working_memory>
"""

        cleaned = interp._apply_working_memory_update(response_with_block)

        # Block should be removed
        assert "<working_memory>" not in cleaned
        assert "</working_memory>" not in cleaned

        # But the rest of the response should remain
        assert "Here is my response to your question." in cleaned

        # Working memory should be updated
        wm = interp._agent_context.working_memory
        assert "main.py" in wm.active_files
        assert "utils.py" in wm.active_files
        assert "Use async pattern" in wm.recent_decisions
        assert "Add tests" in wm.pending_todos

    def test_response_without_block_unchanged(self):
        """Test that responses without the block are returned unchanged."""
        interp = Interpreter(llm_runtime=MockLLMRuntime())
        interp._agent_context = AgentContextManager()

        response_without_block = "This is a normal response without any working memory block."

        cleaned = interp._apply_working_memory_update(response_without_block)

        # Should be unchanged
        assert cleaned == response_without_block

    def test_working_memory_block_case_insensitive(self):
        """Test that block removal is case-insensitive."""
        interp = Interpreter(llm_runtime=MockLLMRuntime())
        interp._agent_context = AgentContextManager()

        response = """
Response text.

<WORKING_MEMORY>
active_files: [test.py]
</WORKING_MEMORY>
"""

        cleaned = interp._apply_working_memory_update(response)

        assert "<WORKING_MEMORY>" not in cleaned
        assert "</WORKING_MEMORY>" not in cleaned
        assert "Response text." in cleaned

    def test_multiple_blocks_removed(self):
        """Test that multiple working memory blocks are all removed."""
        interp = Interpreter(llm_runtime=MockLLMRuntime())
        interp._agent_context = AgentContextManager()

        response = """
First part.

<working_memory>
active_files: [file1.py]
</working_memory>

Middle part.

<working_memory>
active_files: [file2.py]
</working_memory>

End part.
"""

        cleaned = interp._apply_working_memory_update(response)

        # All blocks should be removed
        assert "<working_memory>" not in cleaned
        assert "</working_memory>" not in cleaned

        # But other text should remain
        assert "First part." in cleaned
        assert "Middle part." in cleaned
        assert "End part." in cleaned

    def test_working_memory_disabled_still_strips_block(self):
        """v1.30.1 fix: when working memory is disabled, block is still stripped.

        Previously, disabling working memory caused the <working_memory> block
        to leak into the final response (and on_chunk callbacks), exposing
        internal state to the user.
        """
        interp = Interpreter(llm_runtime=MockLLMRuntime())
        interp._agent_context = AgentContextManager(working_memory_enabled=False)

        response = """
Response.

<working_memory>
active_files: [test.py]
</working_memory>
"""

        cleaned = interp._apply_working_memory_update(response)

        # v1.30.1: block should be stripped even when disabled
        assert "<working_memory>" not in cleaned
        assert "Response." in cleaned


class TestWorkingMemoryBlockOnlyFallback:
    """v1.39.9 fix: when the LLM wraps its ENTIRE response in a
    <working_memory> block (no user-facing answer), stripping the block
    must NOT return an empty string. The original response is returned
    as a fallback so the UI shows content instead of going blank.

    Reproduces the glm-5.2 pattern where, after a few tool calls, the
    model emits only the working-memory block and the agent returns ""
    -> blank UI with no error.
    """

    def test_block_only_returns_original_not_empty(self, capsys):
        """Response containing only a <working_memory> block falls back
        to the original response instead of returning empty."""
        interp = Interpreter(llm_runtime=MockLLMRuntime())
        interp._agent_context = AgentContextManager()

        response = """<working_memory>
active_files: [main.py]
decisions: [Use async pattern]
</working_memory>"""

        cleaned = interp._apply_working_memory_update(response)

        # Must NOT be empty - fallback to original
        assert cleaned != ""
        assert cleaned is not None
        # Fallback returns the original response verbatim
        assert cleaned == response

        # A warning should be printed to stderr
        captured = capsys.readouterr()
        assert "emptied the response" in captured.err

    def test_block_only_still_updates_memory(self, capsys):
        """Even when falling back, the working memory store is still
        updated from the block content."""
        interp = Interpreter(llm_runtime=MockLLMRuntime())
        interp._agent_context = AgentContextManager()

        response = """<working_memory>
active_files: [auth.py]
decisions: [Use JWT]
</working_memory>"""

        interp._apply_working_memory_update(response)

        wm = interp._agent_context.working_memory
        assert "auth.py" in wm.active_files
        assert "Use JWT" in wm.recent_decisions

    def test_block_only_whitespace_outside_falls_back(self, capsys):
        """If the only non-block content is whitespace, still fall back."""
        interp = Interpreter(llm_runtime=MockLLMRuntime())
        interp._agent_context = AgentContextManager()

        response = "\n\n<working_memory>\nactive_files: [x.py]\n</working_memory>\n\n"

        cleaned = interp._apply_working_memory_update(response)

        # Whitespace-only after strip -> fall back to original
        assert cleaned == response

    def test_block_only_disabled_memory_still_falls_back(self, capsys):
        """Fallback applies even when working memory is disabled - the
        point is to never return an empty response to the user."""
        interp = Interpreter(llm_runtime=MockLLMRuntime())
        interp._agent_context = AgentContextManager(working_memory_enabled=False)

        response = """<working_memory>
active_files: [test.py]
</working_memory>"""

        cleaned = interp._apply_working_memory_update(response)

        # Must not be empty
        assert cleaned == response


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
