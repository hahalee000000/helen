"""Data formats contracts for Helen stdlib.

Defines interfaces for YAML, TOML, and XML operations.
"""

from typing import Any


class YamlContract:
    """Contract for YAML operations."""

    @staticmethod
    def yaml_parse(text: str) -> Any:
        """Parse YAML string.

        Args:
            text: YAML string

        Returns:
            Parsed Python object

        Raises:
            ValueError: If YAML is invalid
        """
        ...

    @staticmethod
    def yaml_stringify(value: Any) -> str:
        """Convert Python object to YAML string.

        Args:
            value: Python object to serialize

        Returns:
            YAML string
        """
        ...

    @staticmethod
    def yaml_load(path: str) -> Any:
        """Load YAML from file.

        Args:
            path: File path

        Returns:
            Parsed Python object

        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If YAML is invalid
        """
        ...

    @staticmethod
    def yaml_save(path: str, value: Any) -> str:
        """Save Python object to YAML file.

        Args:
            path: File path
            value: Python object to serialize

        Returns:
            Success message
        """
        ...


class TomlContract:
    """Contract for TOML operations."""

    @staticmethod
    def toml_parse(text: str) -> dict[str, Any]:
        """Parse TOML string.

        Args:
            text: TOML string

        Returns:
            Parsed Python dict

        Raises:
            ValueError: If TOML is invalid
        """
        ...

    @staticmethod
    def toml_stringify(value: dict[str, Any]) -> str:
        """Convert Python dict to TOML string.

        Args:
            value: Python dict to serialize

        Returns:
            TOML string
        """
        ...

    @staticmethod
    def toml_load(path: str) -> dict[str, Any]:
        """Load TOML from file.

        Args:
            path: File path

        Returns:
            Parsed Python dict

        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If TOML is invalid
        """
        ...

    @staticmethod
    def toml_save(path: str, value: dict[str, Any]) -> str:
        """Save Python dict to TOML file.

        Args:
            path: File path
            value: Python dict to serialize

        Returns:
            Success message
        """
        ...


class XmlContract:
    """Contract for XML operations."""

    @staticmethod
    def xml_parse(text: str) -> dict[str, Any]:
        """Parse XML string to dict.

        Args:
            text: XML string

        Returns:
            Parsed Python dict

        Raises:
            ValueError: If XML is invalid
        """
        ...

    @staticmethod
    def xml_stringify(value: dict[str, Any], root: str = "root") -> str:
        """Convert Python dict to XML string.

        Args:
            value: Python dict to serialize
            root: Root element name

        Returns:
            XML string
        """
        ...

    @staticmethod
    def xml_load(path: str) -> dict[str, Any]:
        """Load XML from file.

        Args:
            path: File path

        Returns:
            Parsed Python dict

        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If XML is invalid
        """
        ...

    @staticmethod
    def xml_save(path: str, value: dict[str, Any], root: str = "root") -> str:
        """Save Python dict to XML file.

        Args:
            path: File path
            value: Python dict to serialize
            root: Root element name

        Returns:
            Success message
        """
        ...
