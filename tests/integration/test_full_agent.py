"""Integration tests for complete Helen Agent programs."""

import os
import tempfile

from helen.cli.__main__ import run_command, check_command


class TestFullAgentProgram:
    """Test complete Agent program end-to-end."""

    def test_agent_decl_and_check(self):
        """Full agent: declaration passes check."""
        code = """
agent Greeter {
    prompt "You are a friendly greeter"

    main {
        let message = "Hello, World!"
    }
}
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".helen", delete=False) as f:
            f.write(code)
            f.flush()
            try:
                result = check_command(f.name)
                assert result == 0
            finally:
                os.unlink(f.name)

    def test_simple_run(self):
        """Simple program runs successfully."""
        code = "let x = 1 + 2"
        with tempfile.NamedTemporaryFile(mode="w", suffix=".helen", delete=False) as f:
            f.write(code)
            f.flush()
            try:
                result = run_command(f.name)
                assert result == 0
            finally:
                os.unlink(f.name)

    def test_agent_with_params_check(self):
        """Agent with parameters passes check."""
        code = """
agent Greeter(name: string) {
    prompt "You greet a person by name"

    main {
        let greeting = "Hello"
    }
}
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".helen", delete=False) as f:
            f.write(code)
            f.flush()
            try:
                result = check_command(f.name)
                assert result == 0
            finally:
                os.unlink(f.name)

    def test_agent_with_settings_check(self):
        """Agent with model/temperature/max-turns declarations passes check."""
        code = """
agent Analyzer {
    description "Analyzes text"
    model "gpt-4"
    temperature 0.7
    max-turns 5

    prompt "You analyze text"

    main {
        let result = "analyzed"
    }
}
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".helen", delete=False) as f:
            f.write(code)
            f.flush()
            try:
                result = check_command(f.name)
                assert result == 0
            finally:
                os.unlink(f.name)


class TestControlFlowInAgent:
    """Test control flow within agent main blocks."""

    def test_if_else_in_agent_check(self):
        """Agent main block with if/else passes check."""
        code = """
agent ConditionChecker {
    prompt "Checks conditions"

    main {
        let x = 1
        if (x == 1) {
            let result = "one"
        } else {
            let result = "other"
        }
    }
}
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".helen", delete=False) as f:
            f.write(code)
            f.flush()
            try:
                result = check_command(f.name)
                assert result == 0
            finally:
                os.unlink(f.name)

    def test_for_loop_in_agent_check(self):
        """Agent main block with for loop passes check."""
        code = """
agent LoopAgent {
    prompt "Runs a loop"

    main {
        let sum = 0
        for i in [1, 2, 3] {
            sum = sum + i
        }
    }
}
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".helen", delete=False) as f:
            f.write(code)
            f.flush()
            try:
                result = check_command(f.name)
                assert result == 0
            finally:
                os.unlink(f.name)


class TestImportAndCall:
    """Test import + agent call workflow."""

    def test_import_and_check(self):
        """Import a .helen file and check."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a library file
            lib_path = os.path.join(tmpdir, "lib.helen")
            with open(lib_path, "w") as f:
                f.write("""
agent LibAgent {
    prompt "A library agent"

    main {
        let result = "from library"
    }
}
""")

            # Create main file that imports
            main_path = os.path.join(tmpdir, "main.helen")
            with open(main_path, "w") as f:
                f.write(f'import "{lib_path}"')

            result = check_command(main_path)
            assert result == 0


class TestLlmActCheck:
    """Test llm act with MockLLMRuntime (check mode)."""

    def test_llm_act_simple_check(self):
        """Simple llm act passes check."""
        code = """
agent Assistant {
    prompt "You are a helpful assistant"

    main {
        llm act "hello"
    }
}
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".helen", delete=False) as f:
            f.write(code)
            f.flush()
            try:
                result = check_command(f.name)
                assert result == 0
            finally:
                os.unlink(f.name)
