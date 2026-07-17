"""Test module import functionality (P0 fix).

Tests verify that Helen supports cross-file function imports:
1. Import .helen file and call functions directly (no alias)
2. Import .helen file with alias and call via module.function()
3. Import multiple files
4. Handle import errors gracefully
"""
import pytest
import subprocess
import tempfile
from pathlib import Path


@pytest.fixture
def temp_dir():
    """Create temporary directory for test files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


def run_helen(file_path: Path) -> dict:
    """Run a Helen file and return result."""
    result = subprocess.run(
        ["helen", str(file_path)],
        capture_output=True,
        text=True,
        timeout=10
    )
    return {
        "returncode": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr
    }


class TestModuleImport:
    """Test Helen's module import system."""
    
    def test_import_helen_file_direct_call(self, temp_dir):
        """Should import .helen file and call functions directly."""
        # Create math module
        math_file = temp_dir / "math_utils.helen"
        math_file.write_text("""
fn add(a: int, b: int): int {
    return a + b
}

fn multiply(a: int, b: int): int {
    return a * b
}
""")
        
        # Create main file that imports
        main_file = temp_dir / "main.helen"
        main_file.write_text(f"""
import "math_utils.helen"

main {{
    let result = add(5, 3)
    print(result)
}}
""")
        
        result = run_helen(main_file)
        
        # Should successfully call add() function
        assert result["returncode"] == 0, f"Expected success, got error: {result['stderr']}"
        assert "8" in result["stdout"]
    
    def test_import_helen_file_with_alias(self, temp_dir):
        """Should import .helen file with alias and call via module.function()."""
        # Create math module
        math_file = temp_dir / "math_utils.helen"
        math_file.write_text("""
fn add(a: int, b: int): int {
    return a + b
}
""")
        
        # Create main file with alias
        main_file = temp_dir / "main.helen"
        main_file.write_text(f"""
import "math_utils.helen" as math

main {{
    let result = math.add(5, 3)
    print(result)
}}
""")
        
        result = run_helen(main_file)
        
        # Should successfully call math.add() function
        assert result["returncode"] == 0, f"Expected success, got error: {result['stderr']}"
        assert "8" in result["stdout"]
    
    def test_import_multiple_files(self, temp_dir):
        """Should import multiple .helen files."""
        # Create math module
        math_file = temp_dir / "math.helen"
        math_file.write_text("""
fn add_nums(a: int, b: int): int {
    return a + b
}
""")

        # Create string module
        string_file = temp_dir / "string_utils.helen"
        string_file.write_text("""
fn greet(name: str): str {
    return "Hello, " + name
}
""")

        # Create main file
        main_file = temp_dir / "main.helen"
        main_file.write_text(f"""
import "math.helen"
import "string_utils.helen"

main {{
    let total = add_nums(10, 20)
    let greeting = greet("Helen")
    print(total)
    print(greeting)
}}
""")
        
        result = run_helen(main_file)
        
        assert result["returncode"] == 0, f"Expected success, got error: {result['stderr']}"
        assert "30" in result["stdout"]
        assert "Hello, Helen" in result["stdout"]
    
    def test_import_with_constants(self, temp_dir):
        """Should import .helen file with constants."""
        # Create config module
        config_file = temp_dir / "config.helen"
        config_file.write_text("""
const MAX_SIZE = 100
const DEFAULT_NAME = "World"
""")
        
        # Create main file
        main_file = temp_dir / "main.helen"
        main_file.write_text(f"""
import "config.helen"

main {{
    print(MAX_SIZE)
    print(DEFAULT_NAME)
}}
""")
        
        result = run_helen(main_file)
        
        assert result["returncode"] == 0, f"Expected success, got error: {result['stderr']}"
        assert "100" in result["stdout"]
        assert "World" in result["stdout"]
    
    def test_import_nonexistent_file(self, temp_dir):
        """Should report error for nonexistent import file."""
        main_file = temp_dir / "main.helen"
        main_file.write_text("""
import "nonexistent.helen"

main {
    print("test")
}
""")
        
        result = run_helen(main_file)
        
        # Should fail with import error (error can be in stdout or stderr)
        assert result["returncode"] != 0
        error_output = (result["stdout"] + result["stderr"]).lower()
        assert "not found" in error_output or "error" in error_output
    
    def test_import_function_with_multiple_params(self, temp_dir):
        """Should import and call functions with multiple parameters."""
        # Create module
        module_file = temp_dir / "utils.helen"
        module_file.write_text("""
fn compute(a: int, b: int, c: int): int {
    return a + b * c
}
""")

        # Create main file
        main_file = temp_dir / "main.helen"
        main_file.write_text(f"""
import "utils.helen"

main {{
    let out = compute(2, 3, 4)
    print(out)
}}
""")

        result = run_helen(main_file)

        assert result["returncode"] == 0, f"Expected success, got error: {result['stderr']}"
        assert "14" in result["stdout"]  # 2 + 3 * 4 = 14
    
    def test_import_agent(self, temp_dir):
        """Should import and use agents from .helen files."""
        # Create agent module
        agent_file = temp_dir / "agents.helen"
        agent_file.write_text("""
agent Greeter(name: str) {
    description "A simple greeter agent"
    model "test"
    
    functions {
        fn greet(): str {
            return "Hello, " + name
        }
    }
    
    main {
        return greet()
    }
}
""")
        
        # Create main file
        main_file = temp_dir / "main.helen"
        main_file.write_text(f"""
import "agents.helen"

main {{
    let result = Greeter(name="World")
    print(result)
}}
""")
        
        result = run_helen(main_file)
        
        # Should successfully create and call agent
        assert result["returncode"] == 0, f"Expected success, got error: {result['stderr']}"


class TestImportEdgeCases:
    """Test edge cases for module imports."""
    
    def test_import_same_file_twice(self, temp_dir):
        """Should handle importing the same file twice gracefully."""
        # Create module
        module_file = temp_dir / "utils.helen"
        module_file.write_text("""
fn add(a: int, b: int): int {
    return a + b
}
""")
        
        # Create main file that imports twice
        main_file = temp_dir / "main.helen"
        main_file.write_text(f"""
import "utils.helen"
import "utils.helen"

main {{
    let result = add(5, 3)
    print(result)
}}
""")
        
        result = run_helen(main_file)
        
        # Should still work (idempotent import)
        assert result["returncode"] == 0, f"Expected success, got error: {result['stderr']}"
        assert "8" in result["stdout"]
    
    def test_import_with_function_calling_imported_function(self, temp_dir):
        """Should handle functions that call imported functions."""
        # Create base module
        base_file = temp_dir / "base.helen"
        base_file.write_text("""
fn double(x: int): int {
    return x * 2
}
""")
        
        # Create wrapper module
        wrapper_file = temp_dir / "wrapper.helen"
        wrapper_file.write_text(f"""
import "base.helen"

fn quadruple(x: int): int {{
    return double(double(x))
}}
""")
        
        # Create main file
        main_file = temp_dir / "main.helen"
        main_file.write_text(f"""
import "wrapper.helen"

main {{
    let result = quadruple(5)
    print(result)
}}
""")
        
        result = run_helen(main_file)
        
        assert result["returncode"] == 0, f"Expected success, got error: {result['stderr']}"
        assert "20" in result["stdout"]  # 5 * 2 * 2 = 20
