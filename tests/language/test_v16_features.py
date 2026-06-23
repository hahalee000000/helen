"""
Tests for Helen v1.6 language features:
1. Module imports support function access (not just data)
2. Reduced reserved words (memory -> context keyword)
3. Function forward references (no declaration order requirement)
"""

import pytest
import subprocess
from pathlib import Path


@pytest.fixture
def helen_dir():
    return Path(__file__).parent.parent.parent


@pytest.fixture
def temp_helen_file(tmp_path):
    """Create a temporary .helen file for testing."""
    def _create(content: str, name: str = "test.helen") -> Path:
        file_path = tmp_path / name
        file_path.write_text(content)
        return file_path
    return _create


class TestModuleFunctionImport:
    """Test that module imports support function access."""
    
    def test_import_module_with_alias(self, temp_helen_file, helen_dir):
        """Should support: import "module.helen" as m"""
        # Create a module file
        module = temp_helen_file("""
fn greet(name: str): str {
    return "Hello, " + name
}

const VERSION = "1.0"
""", "module.helen")
        
        # Create main file that imports and uses it
        main = temp_helen_file(f"""
import "{module}" as m

main {{
    let result = m.greet("World")
    print(result)
    print(m.VERSION)
}}
""", "main.helen")
        
        # Run helen check
        result = subprocess.run(
            ["helen", "check", str(main)],
            capture_output=True,
            text=True,
            cwd=helen_dir
        )
        
        assert result.returncode == 0 or "OK" in result.stdout, \
            f"Should support module function access: {result.stdout}"
    
    @pytest.mark.xfail(reason="Direct function import syntax not yet implemented (v1.6+)")
    def test_import_function_directly(self, temp_helen_file, helen_dir):
        """Should support: import "module.helen" { greet, VERSION }"""
        module = temp_helen_file("""
fn greet(name: str): str {
    return "Hello, " + name
}

const VERSION = "1.0"
""", "module.helen")
        
        main = temp_helen_file(f"""
import "{module}" {{ greet, VERSION }}

main {{
    let result = greet("World")
    print(result)
    print(VERSION)
}}
""", "main.helen")
        
        result = subprocess.run(
            ["helen", "check", str(main)],
            capture_output=True,
            text=True,
            cwd=helen_dir
        )
        
        assert result.returncode == 0 or "OK" in result.stdout, \
            f"Should support direct function import: {result.stdout}"
    
    def test_module_function_execution(self, temp_helen_file, helen_dir):
        """Module functions should be callable and return correct values."""
        module = temp_helen_file("""
fn add(a: int, b: int): int {
    return a + b
}
""", "math_module.helen")
        
        main = temp_helen_file(f"""
import "{module}" as math

main {{
    let result = math.add(2, 3)
    print(result)
}}
""", "main.helen")
        
        result = subprocess.run(
            ["helen", str(main)],
            capture_output=True,
            text=True,
            cwd=helen_dir
        )
        
        assert "5" in result.stdout, f"Should execute module function: {result.stdout}"


class TestReducedReservedWords:
    """Test that 'memory' is no longer a reserved word."""
    
    def test_memory_as_variable_name(self, temp_helen_file, helen_dir):
        """Should allow 'memory' as a variable name."""
        code = """
main {
    let memory = "test data"
    print(memory)
}
"""
        file_path = temp_helen_file(code)
        
        result = subprocess.run(
            ["helen", "check", str(file_path)],
            capture_output=True,
            text=True,
            cwd=helen_dir
        )
        
        assert result.returncode == 0 or "OK" in result.stdout, \
            f"'memory' should be usable as variable name: {result.stdout}"
    
    def test_memory_as_function_parameter(self, temp_helen_file, helen_dir):
        """Should allow 'memory' as function parameter."""
        code = """
fn load_memory(memory: str): str {
    return memory
}

main {
    let result = load_memory("test")
    print(result)
}
"""
        file_path = temp_helen_file(code)
        
        result = subprocess.run(
            ["helen", "check", str(file_path)],
            capture_output=True,
            text=True,
            cwd=helen_dir
        )
        
        assert result.returncode == 0 or "OK" in result.stdout, \
            f"'memory' should be usable as parameter: {result.stdout}"
    
    def test_memory_keyword_still_works_in_agent(self, temp_helen_file, helen_dir):
        """Agent 'memory' setting should still work."""
        code = """
agent TestAgent {
    description "Test agent"
    memory "file://test.json"
    prompt "Test"
}
"""
        file_path = temp_helen_file(code)
        
        result = subprocess.run(
            ["helen", "check", str(file_path)],
            capture_output=True,
            text=True,
            cwd=helen_dir
        )
        
        assert result.returncode == 0 or "OK" in result.stdout, \
            f"Agent 'memory' setting should work: {result.stdout}"


class TestFunctionForwardReferences:
    """Test that functions can be called before declaration."""
    
    def test_forward_reference_simple(self, temp_helen_file, helen_dir):
        """Should allow calling function_b before it's declared."""
        code = """
fn function_a() {
    function_b()
}

fn function_b() {
    print("Hello from B")
}

main {
    function_a()
}
"""
        file_path = temp_helen_file(code)
        
        result = subprocess.run(
            ["helen", "check", str(file_path)],
            capture_output=True,
            text=True,
            cwd=helen_dir
        )
        
        assert result.returncode == 0 or "OK" in result.stdout, \
            f"Should support forward references: {result.stdout}"
    
    def test_mutual_recursion(self, temp_helen_file, helen_dir):
        """Should support mutually recursive functions."""
        code = """
fn is_even(n: int): bool {
    if n == 0 {
        return true
    }
    return is_odd(n - 1)
}

fn is_odd(n: int): bool {
    if n == 0 {
        return false
    }
    return is_even(n - 1)
}

main {
    print(is_even(4))
    print(is_odd(3))
}
"""
        file_path = temp_helen_file(code)
        
        result = subprocess.run(
            ["helen", "check", str(file_path)],
            capture_output=True,
            text=True,
            cwd=helen_dir
        )
        
        assert result.returncode == 0 or "OK" in result.stdout, \
            f"Should support mutual recursion: {result.stdout}"
    
    def test_forward_reference_execution(self, temp_helen_file, helen_dir):
        """Forward referenced functions should execute correctly."""
        code = """
fn function_a(): int {
    return function_b() + 10
}

fn function_b(): int {
    return 5
}

main {
    let result = function_a()
    print(result)
}
"""
        file_path = temp_helen_file(code)
        
        result = subprocess.run(
            ["helen", str(file_path)],
            capture_output=True,
            text=True,
            cwd=helen_dir
        )
        
        assert "15" in result.stdout, f"Should execute forward reference: {result.stdout}"
    
    def test_forward_reference_in_agent_functions(self, temp_helen_file, helen_dir):
        """Should support forward references in agent functions block."""
        code = """
agent TestAgent {
    description "Test"
    prompt "Test"
    
    functions {
        fn helper_a(): str {
            return helper_b()
        }
        
        fn helper_b(): str {
            return "from B"
        }
    }
    
    main {
        print(helper_a())
    }
}
"""
        file_path = temp_helen_file(code)
        
        result = subprocess.run(
            ["helen", "check", str(file_path)],
            capture_output=True,
            text=True,
            cwd=helen_dir
        )
        
        assert result.returncode == 0 or "OK" in result.stdout, \
            f"Should support forward references in agent: {result.stdout}"


class TestIntegration:
    """Integration tests combining multiple v1.6 features."""
    
    def test_combined_features(self, temp_helen_file, helen_dir):
        """Test all v1.6 features together."""
        module = temp_helen_file("""
fn process(data: str): str {
    return transform(data)
}

fn transform(data: str): str {
    return data.upper()
}

const VERSION = "1.6"
""", "utils.helen")
        
        main = temp_helen_file(f"""
import "{module}" as utils

fn main_helper(): str {{
    return utils.process("hello")
}}

main {{
    let memory = "test"
    let result = main_helper()
    print(result)
    print(utils.VERSION)
    print(memory)
}}
""", "main.helen")
        
        result = subprocess.run(
            ["helen", "check", str(main)],
            capture_output=True,
            text=True,
            cwd=helen_dir
        )
        
        assert result.returncode == 0 or "OK" in result.stdout, \
            f"Should support all v1.6 features: {result.stdout}"
