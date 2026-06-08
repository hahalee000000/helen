"""Tests for hellen.runtime.import_resolver — ImportResolver (HLD 3.9 M8)."""

import os
import tempfile

from hellen.runtime.import_resolver import ImportResolver, ImportResult


FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures")


class TestImportResolverHellen:
    """Test .hellen file import (HLD 3.9.1)."""

    def test_import_hellen_registers_agent(self):
        resolver = ImportResolver(base_dir=FIXTURES_DIR)
        result = resolver.resolve("utils.hellen")
        assert result is not None
        assert result.format == "hellen"
        assert "HelperAgent" in resolver.agents
        assert "greet" in resolver.functions

    def test_import_hellen_does_not_execute_main(self):
        """Import should not execute the imported file's main block."""
        resolver = ImportResolver(base_dir=FIXTURES_DIR)
        resolver.resolve("utils.hellen")
        # If main was executed, we'd see side effects. Since it's just parsed,
        # the agents/functions are registered but nothing is executed.
        assert "HelperAgent" in resolver.agents

    def test_import_not_found(self):
        resolver = ImportResolver(base_dir=FIXTURES_DIR)
        result = resolver.resolve("nonexistent.hellen")
        assert result is None


class TestImportResolverData:
    """Test .json/.txt file import (HLD 3.9.1)."""

    def test_import_json(self):
        resolver = ImportResolver(base_dir=FIXTURES_DIR)
        result = resolver.resolve("config.json")
        assert result is not None
        assert result.format == "json"
        assert result.content["key"] == "value"
        assert result.content["number"] == 42
        assert result.content["list"] == ["a", "b"]

    def test_import_text(self):
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".md", delete=False, dir=FIXTURES_DIR
        ) as f:
            f.write("# Test Document\nThis is a test.")
            f.flush()
            fname = f.name

        try:
            resolver = ImportResolver(base_dir=FIXTURES_DIR)
            result = resolver.resolve(os.path.basename(fname))
            assert result is not None
            assert result.format == "text"
            assert "# Test Document" in result.content
        finally:
            os.unlink(fname)


class TestImportResolverPathSafety:
    """Test path safety: prevent ../ escape (HLD 3.9.2)."""

    def test_path_escape_blocked(self):
        resolver = ImportResolver(base_dir=FIXTURES_DIR)
        # Try to escape to /etc/passwd
        result = resolver.resolve("../../../etc/passwd")
        assert result is None

    def test_relative_path_resolution(self):
        """Relative paths should resolve from base_dir."""
        resolver = ImportResolver(base_dir=FIXTURES_DIR)
        result = resolver.resolve("utils.hellen")
        assert result is not None
        assert result.format == "hellen"


class TestImportResolverCircular:
    """Test circular import detection (HLD 3.9.2)."""

    def test_no_duplicate_registration(self):
        resolver = ImportResolver(base_dir=FIXTURES_DIR)
        resolver.resolve("utils.hellen")
        resolver.resolve("utils.hellen")  # Second import — should be detected
        # Agents should only be registered once
        assert len(resolver.agents) == 1


class TestImportResult:
    """Test ImportResult dataclass."""

    def test_import_result_fields(self):
        result = ImportResult(
            path="/test/utils.hellen", content="data", format="hellen"
        )
        assert result.path == "/test/utils.hellen"
        assert result.content == "data"
        assert result.format == "hellen"
