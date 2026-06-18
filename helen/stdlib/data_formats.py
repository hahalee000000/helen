"""Data formats module for Helen stdlib.

Provides YAML, TOML, and XML parsing and generation.
"""

from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from typing import Any
from pathlib import Path

# Try to import YAML support
try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False

# Try to import TOML support (Python 3.11+ has tomllib)
try:
    import tomllib
    HAS_TOML_READ = True
except ImportError:
    try:
        import toml
        HAS_TOML_READ = True
    except ImportError:
        HAS_TOML_READ = False

try:
    import toml
    HAS_TOML_WRITE = True
except ImportError:
    HAS_TOML_WRITE = False


# ── YAML operations ────────────────────────────────────────────


def _yaml_parse(text: str) -> Any:
    """Parse YAML string.

    Args:
        text: YAML string

    Returns:
        Parsed Python object

    Raises:
        ValueError: If YAML is invalid
    """
    if not HAS_YAML:
        raise ImportError("PyYAML is required for YAML support. Install with: pip install pyyaml")
    
    try:
        return yaml.safe_load(text)
    except yaml.YAMLError as e:
        raise ValueError(f"Invalid YAML: {e}") from e


def _yaml_stringify(value: Any) -> str:
    """Convert Python object to YAML string.

    Args:
        value: Python object to serialize

    Returns:
        YAML string
    """
    if not HAS_YAML:
        raise ImportError("PyYAML is required for YAML support. Install with: pip install pyyaml")
    
    return yaml.dump(value, default_flow_style=False, allow_unicode=True)


def _yaml_load(path: str) -> Any:
    """Load YAML from file.

    Args:
        path: File path

    Returns:
        Parsed Python object

    Raises:
        FileNotFoundError: If file doesn't exist
        ValueError: If YAML is invalid
    """
    if not HAS_YAML:
        raise ImportError("PyYAML is required for YAML support. Install with: pip install pyyaml")
    
    try:
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        raise FileNotFoundError(f"File not found: {path}")
    except yaml.YAMLError as e:
        raise ValueError(f"Invalid YAML in file: {e}") from e


def _yaml_save(path: str, value: Any) -> str:
    """Save Python object to YAML file.

    Args:
        path: File path
        value: Python object to serialize

    Returns:
        Success message
    """
    if not HAS_YAML:
        raise ImportError("PyYAML is required for YAML support. Install with: pip install pyyaml")
    
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    
    with open(p, "w", encoding="utf-8") as f:
        yaml.dump(value, f, default_flow_style=False, allow_unicode=True)
    
    return f"Saved YAML to {path}"


# ── TOML operations ────────────────────────────────────────────


def _toml_parse(text: str) -> dict[str, Any]:
    """Parse TOML string.

    Args:
        text: TOML string

    Returns:
        Parsed Python dict

    Raises:
        ValueError: If TOML is invalid
    """
    if not HAS_TOML_READ:
        raise ImportError("TOML support requires Python 3.11+ or 'toml' package. Install with: pip install toml")
    
    try:
        # Python 3.11+ tomllib
        if "tomllib" in globals():
            return tomllib.loads(text)
        # Fallback to toml package
        else:
            return toml.loads(text)
    except Exception as e:
        raise ValueError(f"Invalid TOML: {e}") from e


def _toml_stringify(value: dict[str, Any]) -> str:
    """Convert Python dict to TOML string.

    Args:
        value: Python dict to serialize

    Returns:
        TOML string
    """
    if not HAS_TOML_WRITE:
        raise ImportError("TOML write support requires 'toml' package. Install with: pip install toml")
    
    return toml.dumps(value)


def _toml_load(path: str) -> dict[str, Any]:
    """Load TOML from file.

    Args:
        path: File path

    Returns:
        Parsed Python dict

    Raises:
        FileNotFoundError: If file doesn't exist
        ValueError: If TOML is invalid
    """
    if not HAS_TOML_READ:
        raise ImportError("TOML support requires Python 3.11+ or 'toml' package. Install with: pip install toml")
    
    try:
        # Python 3.11+ tomllib
        if "tomllib" in globals():
            with open(path, "rb") as f:
                return tomllib.load(f)
        # Fallback to toml package
        else:
            return toml.load(path)
    except FileNotFoundError:
        raise FileNotFoundError(f"File not found: {path}")
    except Exception as e:
        raise ValueError(f"Invalid TOML in file: {e}") from e


def _toml_save(path: str, value: dict[str, Any]) -> str:
    """Save Python dict to TOML file.

    Args:
        path: File path
        value: Python dict to serialize

    Returns:
        Success message
    """
    if not HAS_TOML_WRITE:
        raise ImportError("TOML write support requires 'toml' package. Install with: pip install toml")
    
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    
    with open(p, "w", encoding="utf-8") as f:
        toml.dump(value, f)
    
    return f"Saved TOML to {path}"


# ── XML operations ─────────────────────────────────────────────


def _xml_to_dict(element: ET.Element) -> dict[str, Any]:
    """Convert XML element to dict.

    Args:
        element: XML element

    Returns:
        Dict representation
    """
    result: dict[str, Any] = {}
    
    # Handle attributes
    if element.attrib:
        for key, value in element.attrib.items():
            result[f"@{key}"] = value
    
    # Handle children
    children = list(element)
    if children:
        child_dict = {}
        for child in children:
            child_result = _xml_to_dict(child)
            if child.tag in child_dict:
                # Convert to list if multiple elements with same tag
                if not isinstance(child_dict[child.tag], list):
                    child_dict[child.tag] = [child_dict[child.tag]]
                child_dict[child.tag].append(child_result[child.tag])
            else:
                child_dict[child.tag] = child_result[child.tag]
        result.update(child_dict)
    elif element.text and element.text.strip():
        # Text content
        if result:
            result["#text"] = element.text.strip()
        else:
            result = element.text.strip()
    
    return {element.tag: result}


def _dict_to_xml(data: Any, parent: ET.Element | None = None, tag: str = "root") -> ET.Element:
    """Convert dict to XML element.

    Args:
        data: Data to convert
        parent: Parent element
        tag: Element tag name

    Returns:
        XML element
    """
    if parent is None:
        element = ET.Element(tag)
    else:
        element = ET.SubElement(parent, tag)
    
    if isinstance(data, dict):
        for key, value in data.items():
            if key.startswith("@"):
                # Attribute
                element.set(key[1:], str(value))
            elif key == "#text":
                # Text content
                element.text = str(value)
            else:
                # Child element
                if isinstance(value, list):
                    for item in value:
                        _dict_to_xml(item, element, key)
                else:
                    _dict_to_xml(value, element, key)
    else:
        element.text = str(data)
    
    return element


def _xml_parse(text: str) -> dict[str, Any]:
    """Parse XML string to dict.

    Args:
        text: XML string

    Returns:
        Parsed Python dict

    Raises:
        ValueError: If XML is invalid
    """
    try:
        root = ET.fromstring(text)
        return _xml_to_dict(root)
    except ET.ParseError as e:
        raise ValueError(f"Invalid XML: {e}") from e


def _xml_stringify(value: dict[str, Any], root: str = "root") -> str:
    """Convert Python dict to XML string.

    Args:
        value: Python dict to serialize
        root: Root element name

    Returns:
        XML string
    """
    element = _dict_to_xml(value, tag=root)
    return ET.tostring(element, encoding="unicode", method="xml")


def _xml_load(path: str) -> dict[str, Any]:
    """Load XML from file.

    Args:
        path: File path

    Returns:
        Parsed Python dict

    Raises:
        FileNotFoundError: If file doesn't exist
        ValueError: If XML is invalid
    """
    try:
        tree = ET.parse(path)
        root = tree.getroot()
        return _xml_to_dict(root)
    except FileNotFoundError:
        raise FileNotFoundError(f"File not found: {path}")
    except ET.ParseError as e:
        raise ValueError(f"Invalid XML in file: {e}") from e


def _xml_save(path: str, value: dict[str, Any], root: str = "root") -> str:
    """Save Python dict to XML file.

    Args:
        path: File path
        value: Python dict to serialize
        root: Root element name

    Returns:
        Success message
    """
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    
    element = _dict_to_xml(value, tag=root)
    tree = ET.ElementTree(element)
    tree.write(path, encoding="utf-8", xml_declaration=True)
    
    return f"Saved XML to {path}"
