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

    def test_working_memory_disabled_returns_original(self):
        """Test that when working memory is disabled, response is unchanged."""
        interp = Interpreter(llm_runtime=MockLLMRuntime())
        interp._agent_context = AgentContextManager(working_memory_enabled=False)

        response = """
Response.

<working_memory>
active_files: [test.py]
</working_memory>
"""

        cleaned = interp._apply_working_memory_update(response)

        # When disabled, should return original (block still present)
        assert cleaned == response


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
