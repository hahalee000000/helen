"""Tests for Data formats stdlib module.

Tests YAML, TOML, and XML operations.
"""

import pytest
import tempfile
import os
from helen.stdlib.data_formats import (
    # YAML
    _yaml_parse, _yaml_stringify, _yaml_load, _yaml_save,
    # TOML
    _toml_parse, _toml_stringify, _toml_load, _toml_save,
    # XML
    _xml_parse, _xml_stringify, _xml_load, _xml_save,
)


# ── YAML Tests ─────────────────────────────────────────────────


class TestYamlParse:
    """Tests for yaml_parse."""

    def test_basic(self):
        result = _yaml_parse("name: Alice\nage: 30")
        assert result == {"name": "Alice", "age": 30}

    def test_list(self):
        result = _yaml_parse("items:\n  - 1\n  - 2\n  - 3")
        assert result == {"items": [1, 2, 3]}

    def test_nested(self):
        result = _yaml_parse("user:\n  name: Alice\n  age: 30")
        assert result == {"user": {"name": "Alice", "age": 30}}

    def test_invalid(self):
        with pytest.raises(ValueError):
            _yaml_parse("invalid: yaml: :")


class TestYamlStringify:
    """Tests for yaml_stringify."""

    def test_basic(self):
        result = _yaml_stringify({"name": "Alice", "age": 30})
        assert "name: Alice" in result
        assert "age: 30" in result

    def test_list(self):
        result = _yaml_stringify({"items": [1, 2, 3]})
        assert "items:" in result


class TestYamlLoadSave:
    """Tests for yaml_load and yaml_save."""

    def test_save_and_load(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "test.yaml")
            data = {"name": "Alice", "age": 30}

            _yaml_save(path, data)
            loaded = _yaml_load(path)

            assert loaded == data

    def test_load_nonexistent(self):
        with pytest.raises(FileNotFoundError):
            _yaml_load("/nonexistent/path.yaml")


# ── TOML Tests ─────────────────────────────────────────────────


class TestTomlParse:
    """Tests for toml_parse."""

    def test_basic(self):
        result = _toml_parse('name = "Alice"\nage = 30')
        assert result == {"name": "Alice", "age": 30}

    def test_table(self):
        result = _toml_parse("[user]\nname = \"Alice\"\nage = 30")
        assert result == {"user": {"name": "Alice", "age": 30}}

    def test_invalid(self):
        with pytest.raises(ValueError):
            _toml_parse("invalid = = toml")


class TestTomlStringify:
    """Tests for toml_stringify."""

    def test_basic(self):
        result = _toml_stringify({"name": "Alice", "age": 30})
        assert 'name = "Alice"' in result
        assert "age = 30" in result


class TestTomlLoadSave:
    """Tests for toml_load and toml_save."""

    def test_save_and_load(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "test.toml")
            data = {"name": "Alice", "age": 30}

            _toml_save(path, data)
            loaded = _toml_load(path)

            assert loaded == data

    def test_load_nonexistent(self):
        with pytest.raises(FileNotFoundError):
            _toml_load("/nonexistent/path.toml")


# ── XML Tests ──────────────────────────────────────────────────


class TestXmlParse:
    """Tests for xml_parse."""

    def test_basic(self):
        result = _xml_parse("<root><name>Alice</name><age>30</age></root>")
        assert result["root"]["name"] == "Alice"
        assert result["root"]["age"] == "30"

    def test_with_attributes(self):
        result = _xml_parse('<root id="1"><name>Alice</name></root>')
        assert result["root"]["@id"] == "1"
        assert result["root"]["name"] == "Alice"

    def test_invalid(self):
        with pytest.raises(ValueError):
            _xml_parse("<invalid>xml")


class TestXmlStringify:
    """Tests for xml_stringify."""

    def test_basic(self):
        result = _xml_stringify({"name": "Alice", "age": "30"}, root="user")
        assert "<user>" in result
        assert "<name>Alice</name>" in result
        assert "<age>30</age>" in result

    def test_with_attributes(self):
        result = _xml_stringify({"@id": "1", "name": "Alice"}, root="user")
        assert 'id="1"' in result


class TestXmlLoadSave:
    """Tests for xml_load and xml_save."""

    def test_save_and_load(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "test.xml")
            data = {"name": "Alice", "age": "30"}

            _xml_save(path, data, root="user")
            loaded = _xml_load(path)

            assert loaded["user"]["name"] == "Alice"

    def test_load_nonexistent(self):
        with pytest.raises(FileNotFoundError):
            _xml_load("/nonexistent/path.xml")
