"""Test Helen module import capabilities.

Verifies whether Helen supports:
1. Cross-file function imports
2. Module namespaces
3. Selective imports
"""
import pytest
from pathlib import Path
import subprocess


@pytest.fixture
def temp_dir(tmp_path):
    """Create temporary directory for test files."""
    return tmp_path


class TestModuleImport:
    """Test Helen's module import system."""
    
    def test_basic_import_syntax(self, temp_dir):
        """Test if import statement is recognized."""
        # Create a module file
        module_file = temp_dir / "math_utils.helen"
        module_file.write_text("""
fn add(a: int, b: int) -> int {
    return a + b
}

fn multiply(a: int, b: int) -> int {
    return a * b
}
""")
        
        # Create main file that imports
        main_file = temp_dir / "main.helen"
        main_file.write_text(f"""
import "{module_file}"

main {{
    let result = add(5, 3)
    print(result)
}}
""")
        
        # Try to parse
        result = subprocess.run(
            ["python", "-m", "helen.cli.main", "check", str(main_file)],
            capture_output=True,
            text=True,
            cwd=temp_dir
        )
        
        # Check if import is recognized (even if not fully supported)
        print("STDOUT:", result.stdout)
        print("STDERR:", result.stderr)
        
        # We expect this to fail or have limited support
        # The goal is to document the limitation
    
    def test_import_with_namespace(self, temp_dir):
        """Test if namespaced imports work."""
        module_file = temp_dir / "utils.helen"
        module_file.write_text("""
fn helper() -> str {
    return "help"
}
""")
        
        main_file = temp_dir / "main.helen"
        main_file.write_text(f"""
import "{module_file}" as utils

main {{
    let result = utils.helper()
    print(result)
}}
""")
        
        result = subprocess.run(
            ["python", "-m", "helen.cli.main", "check", str(main_file)],
            capture_output=True,
            text=True,
            cwd=temp_dir
        )
        
        print("Namespace import test:")
        print("STDOUT:", result.stdout)
        print("STDERR:", result.stderr)
    
    def test_selective_import(self, temp_dir):
        """Test if selective imports work."""
        module_file = temp_dir / "math.helen"
        module_file.write_text("""
fn add(a: int, b: int) -> int {
    return a + b
}

fn subtract(a: int, b: int) -> int {
    return a - b
}
""")
        
        main_file = temp_dir / "main.helen"
        main_file.write_text(f"""
import {{ add }} from "{module_file}"

main {{
    let result = add(10, 5)
    print(result)
}}
""")
        
        result = subprocess.run(
            ["python", "-m", "helen.cli.main", "check", str(main_file)],
            capture_output=True,
            text=True,
            cwd=temp_dir
        )
        
        print("Selective import test:")
        print("STDOUT:", result.stdout)
        print("STDERR:", result.stderr)
