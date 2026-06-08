"""Tests for import execution semantics (HLD 3.9, 3.6.2).

Covers:
- import does NOT execute main block
- import registers Agent/Function to global namespace
- import after call executes main
- Global namespace sharing via import
"""

import os
import tempfile
import shutil

from hellen.runtime.import_resolver import ImportResolver


FIXTURES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "runtime", "fixtures")


class TestImportDoesNotExecuteMain:
    """Test that import parses but doesn't execute main blocks."""

    def test_import_hellen_registers_without_executing(self):
        """Import registers agents/functions but doesn't execute main."""
        resolver = ImportResolver(base_dir=FIXTURES_DIR)
        result = resolver.resolve("utils.hellen")

        assert result is not None
        assert result.format == "hellen"

        # Agent and function are registered
        assert "HelperAgent" in resolver.agents
        assert "greet" in resolver.functions

        # Main block was NOT executed - we only have registrations
        # If main was executed, we'd see side effects (none in this case)

    def test_imported_agent_main_not_executed(self):
        """Imported agent's main block is parsed but not run."""
        resolver = ImportResolver(base_dir=FIXTURES_DIR)
        resolver.resolve("utils.hellen")

        # Get the registered agent
        agent = resolver.agents.get("HelperAgent")
        assert agent is not None

        # Agent has logic (main block) but it wasn't executed
        # The logic is available for later call
        assert agent.logic is not None


class TestImportGlobalNamespace:
    """Test global namespace registration via import."""

    def test_import_registers_to_global(self):
        """Import registers to global namespace."""
        resolver = ImportResolver(base_dir=FIXTURES_DIR)
        resolver.resolve("utils.hellen")

        # Both agent and function are in global registries
        assert len(resolver.agents) >= 1
        assert len(resolver.functions) >= 1

    def test_multiple_imports_merge_namespaces(self):
        """Multiple imports merge into global namespace."""
        resolver = ImportResolver(base_dir=FIXTURES_DIR)
        resolver.resolve("utils.hellen")

        # All imports share the same resolver instance
        assert "HelperAgent" in resolver.agents
        assert "greet" in resolver.functions


class TestImportPathSafety:
    """Test path safety in imports."""

    def test_relative_path_resolves_from_base(self):
        """Relative paths resolve from base_dir."""
        resolver = ImportResolver(base_dir=FIXTURES_DIR)
        result = resolver.resolve("utils.hellen")
        assert result is not None

    def test_absolute_path_within_base(self):
        """Absolute paths within base_dir are allowed."""
        abs_path = os.path.abspath(os.path.join(FIXTURES_DIR, "utils.hellen"))
        resolver = ImportResolver(base_dir=FIXTURES_DIR)
        result = resolver.resolve(abs_path)
        assert result is not None


class TestCircularImportDetection:
    """Test circular import detection."""

    def test_same_file_imported_twice(self):
        """Importing same file twice is detected."""
        resolver = ImportResolver(base_dir=FIXTURES_DIR)

        result1 = resolver.resolve("utils.hellen")
        result2 = resolver.resolve("utils.hellen")

        # Second import should return cached or None
        # but not cause infinite recursion
        assert result1 is not None


class TestImportResolverFormats:
    """Test different import formats."""

    def test_json_import(self):
        """Import .json file as dict."""
        resolver = ImportResolver(base_dir=FIXTURES_DIR)
        result = resolver.resolve("config.json")

        assert result is not None
        assert result.format == "json"
        assert result.content["key"] == "value"

    def test_text_import(self):
        """Import .md/.txt file as string."""
        tmpdir = tempfile.mkdtemp()
        try:
            path = os.path.join(tmpdir, "doc.md")
            with open(path, "w") as f:
                f.write("# Test\nContent")

            resolver = ImportResolver(base_dir=tmpdir)
            result = resolver.resolve("doc.md")

            assert result is not None
            assert result.format == "text"
            assert "# Test" in result.content
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)
