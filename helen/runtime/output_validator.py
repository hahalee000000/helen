"""Output validation for LLM responses.

v1.40: Validates LLM output against agent's output_contract declaration.

Supports two contract types:
1. Simple string contracts: "json" or "text"
2. Schema contracts: {type: "object", required: [...], properties: {...}}

Usage:
    from helen.runtime.output_validator import validate_output

    result = validate_output("some output", "json")
    if not result["valid"]:
        raise LLMOutputContractError(...)

    result = validate_output("some output", {"type": "object", "required": ["name"]})
"""

from __future__ import annotations

import json
from typing import Any


def validate_output(output: str, contract: str | dict | None) -> dict[str, Any]:
    """Validate LLM output against a contract.

    Args:
        output: The LLM output string to validate
        contract: The contract specification (None, "json", "text", or schema dict)

    Returns:
        Dict with keys:
        - valid: bool - whether output matches contract
        - violation: str - description of violation (empty if valid)
        - parsed: Any - parsed output if applicable (e.g., parsed JSON)
    """
    if contract is None:
        return {"valid": True, "violation": "", "parsed": output}

    if isinstance(contract, str):
        return _validate_simple_contract(output, contract)
    elif isinstance(contract, dict):
        return _validate_schema_contract(output, contract)
    else:
        return {"valid": False, "violation": f"Invalid contract type: {type(contract)}", "parsed": None}


def _validate_simple_contract(output: str, contract: str) -> dict[str, Any]:
    """Validate against simple string contract."""
    if contract == "json":
        return _validate_json(output)
    elif contract == "text":
        # Text contract always passes
        return {"valid": True, "violation": "", "parsed": output}
    else:
        return {"valid": False, "violation": f"Unknown contract type: {contract}", "parsed": None}


def _validate_json(output: str) -> dict[str, Any]:
    """Validate that output is valid JSON."""
    output = output.strip()
    try:
        parsed = json.loads(output)
        return {"valid": True, "violation": "", "parsed": parsed}
    except json.JSONDecodeError as e:
        return {
            "valid": False,
            "violation": f"Output is not valid JSON: {str(e)}",
            "parsed": None,
        }


def _validate_schema_contract(output: str, schema: dict) -> dict[str, Any]:
    """Validate output against a schema contract."""
    # First, try to parse as JSON
    json_result = _validate_json(output)
    if not json_result["valid"]:
        return json_result

    parsed = json_result["parsed"]

    # Validate against schema
    schema_type = schema.get("type")
    if schema_type:
        if not _validate_type(parsed, schema_type):
            return {
                "valid": False,
                "violation": f"Expected type '{schema_type}', got {type(parsed).__name__}",
                "parsed": parsed,
            }

    # Validate required fields
    required = schema.get("required", [])
    if required and isinstance(parsed, dict):
        missing = [field for field in required if field not in parsed]
        if missing:
            return {
                "valid": False,
                "violation": f"Missing required fields: {', '.join(missing)}",
                "parsed": parsed,
            }

    # Validate properties
    properties = schema.get("properties", {})
    if properties and isinstance(parsed, dict):
        for prop_name, prop_schema in properties.items():
            if prop_name in parsed:
                prop_value = parsed[prop_name]
                prop_result = _validate_property(prop_value, prop_schema, prop_name)
                if not prop_result["valid"]:
                    return prop_result

    return {"valid": True, "violation": "", "parsed": parsed}


def _validate_type(value: Any, expected_type: str) -> bool:
    """Validate that value matches expected type."""
    type_map = {
        "string": str,
        "number": (int, float),
        "integer": int,
        "boolean": bool,
        "array": list,
        "object": dict,
    }
    expected = type_map.get(expected_type)
    if expected is None:
        return True  # Unknown type, allow
    return isinstance(value, expected)


def _validate_property(value: Any, schema: dict, prop_name: str) -> dict[str, Any]:
    """Validate a property value against its schema."""
    prop_type = schema.get("type")
    if prop_type and not _validate_type(value, prop_type):
        return {
            "valid": False,
            "violation": f"Property '{prop_name}': expected type '{prop_type}', got {type(value).__name__}",
            "parsed": value,
        }

    # Validate enum
    enum_values = schema.get("enum")
    if enum_values and value not in enum_values:
        return {
            "valid": False,
            "violation": f"Property '{prop_name}': value {value} not in allowed values {enum_values}",
            "parsed": value,
        }

    # Validate number constraints
    if isinstance(value, (int, float)):
        min_val = schema.get("min")
        max_val = schema.get("max")
        if min_val is not None and value < min_val:
            return {
                "valid": False,
                "violation": f"Property '{prop_name}': value {value} is less than minimum {min_val}",
                "parsed": value,
            }
        if max_val is not None and value > max_val:
            return {
                "valid": False,
                "violation": f"Property '{prop_name}': value {value} is greater than maximum {max_val}",
                "parsed": value,
            }

    # Validate string constraints
    if isinstance(value, str):
        min_length = schema.get("minLength")
        max_length = schema.get("maxLength")
        if min_length is not None and len(value) < min_length:
            return {
                "valid": False,
                "violation": f"Property '{prop_name}': string length {len(value)} is less than minimum {min_length}",
                "parsed": value,
            }
        if max_length is not None and len(value) > max_length:
            return {
                "valid": False,
                "violation": f"Property '{prop_name}': string length {len(value)} is greater than maximum {max_length}",
                "parsed": value,
            }

    return {"valid": True, "violation": "", "parsed": value}
