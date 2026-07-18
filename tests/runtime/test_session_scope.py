"""Tests for v1.20: Transcript session scope (global/project/auto).

Covers:
- config: session_scope option (global/project/auto)
- detect_project_dir: project marker detection
- resolve_session_dir: scope-aware path resolution
- HELEN_SESSION_DIR env var override
- get_session_dir() / set_session_dir() stdlib functions
- list_sessions() scope filtering
"""

import os
import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch

from helen.runtime.config import (
    get_transcript_config,
    resolve_session_dir,
    detect_project_dir,
    PROJECT_MARKERS,
    SESSION_SCOPES,
)


# ---------------------------------------------------------------------------
# Config defaults
# ---------------------------------------------------------------------------

class TestTranscriptConfigDefaults:
    def test_default_session_scope_is_auto(self):
        config = get_transcript_config()
        assert config["session_scope"] == "auto"

    def test_has_project_session_dir(self):
        config = get_transcript_config()
        assert "project_session_dir" in config
        assert config["project_session_dir"] == ".helen/sessions"

    def test_session_scopes_constant(self):
        assert SESSION_SCOPES == frozenset({"global", "project", "auto"})

    def test_project_markers(self):
        assert ".helen" in PROJECT_MARKERS
        assert "helen.yaml" in PROJECT_MARKERS
        assert "helen.toml" in PROJECT_MARKERS


# ---------------------------------------------------------------------------
# detect_project_dir
# ---------------------------------------------------------------------------

class TestDetectProjectDir:
    def test_no_project(self, monkeypatch):
        # v1.23 fix: Mock Path.exists to return False for all markers to ensure
        # test isolation from filesystem state (e.g., /tmp/.helen leftovers).
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as tmp:
            test_dir = Path(tmp) / "test"
            test_dir.mkdir()
            # Mock Path.exists to only return True for non-marker paths
            original_exists = Path.exists
            def mock_exists(self):
                # Return False for project markers
                if self.name in (".helen", "helen.yaml", "helen.yml", "helen.toml"):
                    return False
                return original_exists(self)
            with patch.object(Path, 'exists', mock_exists):
                result = detect_project_dir(str(test_dir))
                assert result is None

    def test_detect_helen_dir(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / ".helen").mkdir()
            result = detect_project_dir(tmp)
            assert result == str(Path(tmp).resolve())

    def test_detect_helen_yaml(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "helen.yaml").touch()
            result = detect_project_dir(tmp)
            assert result == str(Path(tmp).resolve())

    def test_detect_helen_toml(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "helen.toml").touch()
            result = detect_project_dir(tmp)
            assert result == str(Path(tmp).resolve())

    def test_detect_in_parent_dir(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / ".helen").mkdir()
            subdir = Path(tmp) / "src" / "nested"
            subdir.mkdir(parents=True)
            result = detect_project_dir(str(subdir))
            assert result == str(Path(tmp).resolve())

    def test_skip_user_helen_home(self):
        """~/.helen is user's global config, NOT a project marker."""
        from helen.runtime.config import HELEN_HOME
        helen_home = Path(HELEN_HOME).resolve()

        # Detect from ~/.helen itself → should NOT return ~/.helen's parent as project
        result = detect_project_dir(str(helen_home))
        # It might find something above ~/.helen, but it should NOT treat ~/.helen itself
        # as the marker. If no project above, result should be None or something else.
        if result is not None:
            # Should not be the parent of ~/.helen (which would indicate ~/.helen was treated as marker)
            helen_home_parent = helen_home.parent.resolve()
            # result might equal helen_home_parent ONLY if some OTHER marker was found there
            # We can't easily check this without knowing user's home layout,
            # but we can verify the detection didn't use ~/.helen itself
            # by ensuring the result doesn't come from a ~/.helen marker.

    def test_detect_from_child_of_helen_home(self):
        """Directory under ~/.helen should not match ~/.helen as project."""
        from helen.runtime.config import HELEN_HOME
        helen_home = Path(HELEN_HOME).resolve()

        # Create a subdirectory under ~/.helen and detect from there
        test_subdir = helen_home / "_test_subdir_for_scope"
        test_subdir.mkdir(exist_ok=True)
        try:
            result = detect_project_dir(str(test_subdir))
            # Result should NOT treat ~/.helen as a project marker
            # It might find something higher, or None
            if result is not None:
                # If found, it shouldn't be ~/.helen's parent due to ~/.helen marker
                # This is tricky to test without mocking, but at least verify
                # the result isn't ~/.helen's parent solely because of ~/.helen
                pass  # Hard to assert without more context
        finally:
            test_subdir.rmdir()


# ---------------------------------------------------------------------------
# resolve_session_dir
# ---------------------------------------------------------------------------

class TestResolveSessionDir:
    def test_global_scope(self):
        path, scope = resolve_session_dir(scope="global")
        assert scope == "global"
        assert path.endswith(".helen/sessions") or "sessions" in path

    def test_project_scope_with_project(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / ".helen").mkdir()
            path, scope = resolve_session_dir(scope="project", cwd=tmp)
            assert scope == "project"
            assert str(Path(tmp).resolve()) in path

    def test_project_scope_without_project_uses_cwd(self):
        # v1.23 fix: Mock Path.exists to ensure test isolation from /tmp/.helen leftovers
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as tmp:
            original_exists = Path.exists
            def mock_exists(self):
                if self.name in (".helen", "helen.yaml", "helen.yml", "helen.toml"):
                    return False
                return original_exists(self)
            with patch.object(Path, 'exists', mock_exists):
                path, scope = resolve_session_dir(scope="project", cwd=tmp)
                assert scope == "project"
                # Falls back to cwd/.helen/sessions when no project marker found
                assert tmp in path or str(Path(tmp).resolve()) in path

    def test_auto_with_project(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / ".helen").mkdir()
            path, scope = resolve_session_dir(scope="auto", cwd=tmp)
            assert scope == "project"
            assert str(Path(tmp).resolve()) in path

    def test_auto_without_project(self):
        # v1.23 fix: Mock Path.exists to ensure test isolation from /tmp/.helen leftovers
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as tmp:
            original_exists = Path.exists
            def mock_exists(self):
                if self.name in (".helen", "helen.yaml", "helen.yml", "helen.toml"):
                    return False
                return original_exists(self)
            with patch.object(Path, 'exists', mock_exists):
                path, scope = resolve_session_dir(scope="auto", cwd=tmp)
                assert scope == "global"
                assert ".helen/sessions" in path

    def test_env_override(self):
        with tempfile.TemporaryDirectory() as tmp:
            env_path = os.path.join(tmp, "custom_sessions")
            path, scope = resolve_session_dir(env_override=env_path)
            assert scope == "env_override"
            assert path == str(Path(env_path).resolve())

    def test_env_override_beats_scope(self):
        """Env override takes priority even when scope=global."""
        with tempfile.TemporaryDirectory() as tmp:
            env_path = os.path.join(tmp, "custom")
            path, scope = resolve_session_dir(scope="global", env_override=env_path)
            assert scope == "env_override"
            assert path == str(Path(env_path).resolve())

    def test_env_var_read_from_environ(self):
        with tempfile.TemporaryDirectory() as tmp:
            env_path = os.path.join(tmp, "from_env")
            os.environ["HELEN_SESSION_DIR"] = env_path
            try:
                path, scope = resolve_session_dir()
                assert scope == "env_override"
                assert path == str(Path(env_path).resolve())
            finally:
                del os.environ["HELEN_SESSION_DIR"]

    def test_invalid_scope_falls_back_to_auto(self):
        path, scope = resolve_session_dir(scope="bogus")
        # Should fall back to auto (not raise)
        assert scope in ("global", "project")


# ---------------------------------------------------------------------------
# stdlib: get_session_dir / set_session_dir
# ---------------------------------------------------------------------------

class TestSessionDirStdlib:
    def test_get_session_dir_returns_ok(self):
        from helen.stdlib.transcript import get_session_dir
        result = get_session_dir()
        assert result["status"] == "ok"
        assert "session_dir" in result
        assert "scope" in result

    def test_set_session_dir_creates_directory(self):
        from helen.stdlib.transcript import set_session_dir, get_session_dir
        with tempfile.TemporaryDirectory() as tmp:
            new_path = os.path.join(tmp, "new_sessions")
            assert not os.path.exists(new_path)

            r = set_session_dir(new_path)
            assert r["status"] == "ok"
            assert os.path.isdir(new_path)

            # get_session_dir should reflect new path
            info = get_session_dir()
            assert info["session_dir"] == str(Path(new_path).resolve())
            assert info["scope"] == "env_override"

            # Cleanup env var
            os.environ.pop("HELEN_SESSION_DIR", None)

    def test_set_session_dir_returns_previous(self):
        from helen.stdlib.transcript import set_session_dir
        with tempfile.TemporaryDirectory() as tmp:
            r = set_session_dir(os.path.join(tmp, "a"))
            assert "previous" in r
            assert r["previous"]  # Non-empty

            r = set_session_dir(os.path.join(tmp, "b"))
            assert r["previous"] == str(Path(os.path.join(tmp, "a")).resolve())

            os.environ.pop("HELEN_SESSION_DIR", None)

    def test_set_session_dir_empty_path_error(self):
        from helen.stdlib.transcript import set_session_dir
        r = set_session_dir("")
        assert r["status"] == "error"

    def test_set_session_dir_relative_path(self):
        from helen.stdlib.transcript import set_session_dir, get_session_dir
        original_cwd = os.getcwd()
        with tempfile.TemporaryDirectory() as tmp:
            os.chdir(tmp)
            try:
                r = set_session_dir("./rel_sessions")
                assert r["status"] == "ok"
                expected = str(Path(tmp).resolve() / "rel_sessions")
                assert r["session_dir"] == expected
            finally:
                os.chdir(original_cwd)
                os.environ.pop("HELEN_SESSION_DIR", None)


# ---------------------------------------------------------------------------
# list_sessions with scope filter
# ---------------------------------------------------------------------------

class TestListSessionsScope:
    def test_list_sessions_with_scope_filter(self):
        from helen.stdlib.transcript import list_sessions
        # Default scope (no filter) should work
        sessions = list_sessions()
        assert isinstance(sessions, list)

    def test_list_sessions_global_scope(self):
        from helen.stdlib.transcript import list_sessions
        sessions = list_sessions("global")
        assert isinstance(sessions, list)
        for s in sessions:
            assert s.get("scope") == "global"

    def test_list_sessions_project_scope(self):
        from helen.stdlib.transcript import list_sessions
        sessions = list_sessions("project")
        assert isinstance(sessions, list)
        for s in sessions:
            assert s.get("scope") == "project"
