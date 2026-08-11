"""Tests for output contract validation (Phase 2).

Tests the output_validator module and integration with agent declarations.
"""

import pytest
from helen.runtime.output_validator import validate_output


class TestOutputValidatorSimpleContracts:
    """Test simple string contracts (json, text)."""

    def test_json_contract_valid(self):
        """Valid JSON should pass json contract."""
        result = validate_output('{"name": "Alice", "age": 30}', "json")
        assert result["valid"] is True
        assert result["violation"] == ""
        assert result["parsed"] == {"name": "Alice", "age": 30}

    def test_json_contract_invalid(self):
        """Invalid JSON should fail json contract."""
        result = validate_output("This is not JSON", "json")
        assert result["valid"] is False
        assert "not valid JSON" in result["violation"]
        assert result["parsed"] is None

    def test_json_contract_array(self):
        """JSON array should pass json contract."""
        result = validate_output('[1, 2, 3]', "json")
        assert result["valid"] is True
        assert result["parsed"] == [1, 2, 3]

    def test_text_contract_always_passes(self):
        """Text contract should always pass."""
        result = validate_output("Any text content", "text")
        assert result["valid"] is True
        assert result["violation"] == ""
        assert result["parsed"] == "Any text content"

    def test_none_contract_always_passes(self):
        """None contract should always pass."""
        result = validate_output("Any content", None)
        assert result["valid"] is True
        assert result["parsed"] == "Any content"


class TestOutputValidatorSchemaContracts:
    """Test schema contracts (dict with type, required, properties)."""

    def test_schema_type_validation_object(self):
        """Schema should validate object type."""
        schema = {"type": "object"}
        result = validate_output('{"name": "Alice"}', schema)
        assert result["valid"] is True

    def test_schema_type_validation_array(self):
        """Schema should validate array type."""
        schema = {"type": "array"}
        result = validate_output('[1, 2, 3]', schema)
        assert result["valid"] is True

    def test_schema_type_mismatch(self):
        """Schema should fail on type mismatch."""
        schema = {"type": "object"}
        result = validate_output('[1, 2, 3]', schema)
        assert result["valid"] is False
        assert "Expected type 'object'" in result["violation"]

    def test_schema_required_fields_present(self):
        """Schema should pass when required fields are present."""
        schema = {
            "type": "object",
            "required": ["name", "age"]
        }
        result = validate_output('{"name": "Alice", "age": 30}', schema)
        assert result["valid"] is True

    def test_schema_required_fields_missing(self):
        """Schema should fail when required fields are missing."""
        schema = {
            "type": "object",
            "required": ["name", "age"]
        }
        result = validate_output('{"name": "Alice"}', schema)
        assert result["valid"] is False
        assert "Missing required fields" in result["violation"]
        assert "age" in result["violation"]

    def test_schema_properties_type_validation(self):
        """Schema should validate property types."""
        schema = {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "age": {"type": "number"}
            }
        }
        result = validate_output('{"name": "Alice", "age": 30}', schema)
        assert result["valid"] is True

    def test_schema_properties_type_mismatch(self):
        """Schema should fail on property type mismatch."""
        schema = {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "age": {"type": "number"}
            }
        }
        result = validate_output('{"name": "Alice", "age": "thirty"}', schema)
        assert result["valid"] is False
        assert "Property 'age'" in result["violation"]
        assert "expected type 'number'" in result["violation"]

    def test_schema_enum_validation(self):
        """Schema should validate enum values."""
        schema = {
            "type": "object",
            "properties": {
                "status": {"type": "string", "enum": ["active", "inactive"]}
            }
        }
        result = validate_output('{"status": "active"}', schema)
        assert result["valid"] is True

    def test_schema_enum_invalid_value(self):
        """Schema should fail on invalid enum value."""
        schema = {
            "type": "object",
            "properties": {
                "status": {"type": "string", "enum": ["active", "inactive"]}
            }
        }
        result = validate_output('{"status": "unknown"}', schema)
        assert result["valid"] is False
        assert "not in allowed values" in result["violation"]

    def test_schema_number_min_max(self):
        """Schema should validate number min/max constraints."""
        schema = {
            "type": "object",
            "properties": {
                "score": {"type": "number", "min": 0, "max": 100}
            }
        }
        result = validate_output('{"score": 50}', schema)
        assert result["valid"] is True

    def test_schema_number_below_min(self):
        """Schema should fail when number is below min."""
        schema = {
            "type": "object",
            "properties": {
                "score": {"type": "number", "min": 0, "max": 100}
            }
        }
        result = validate_output('{"score": -10}', schema)
        assert result["valid"] is False
        assert "less than minimum" in result["violation"]

    def test_schema_number_above_max(self):
        """Schema should fail when number is above max."""
        schema = {
            "type": "object",
            "properties": {
                "score": {"type": "number", "min": 0, "max": 100}
            }
        }
        result = validate_output('{"score": 150}', schema)
        assert result["valid"] is False
        assert "greater than maximum" in result["violation"]


class TestOutputValidatorEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_string_json_contract(self):
        """Empty string should fail json contract."""
        result = validate_output("", "json")
        assert result["valid"] is False

    def test_whitespace_json_contract(self):
        """Whitespace should fail json contract."""
        result = validate_output("   ", "json")
        assert result["valid"] is False

    def test_unknown_contract_type(self):
        """Unknown contract type should fail."""
        result = validate_output("content", "unknown")
        assert result["valid"] is False
        assert "Unknown contract type" in result["violation"]

    def test_invalid_contract_type(self):
        """Invalid contract type (not str or dict) should fail."""
        result = validate_output("content", 123)
        assert result["valid"] is False
        assert "Invalid contract type" in result["violation"]
