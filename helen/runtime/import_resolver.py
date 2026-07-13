"""Import Resolver for the Helen language (HLD 3.9 M8).

Resolves and loads imported modules in multiple formats:
- .helen: Parse recursively, register agents/functions (don't execute main)
- .md/.txt: Load as plain text string
- .json: Parse as JSON dict/list
- .yaml/.yml: Parse as YAML dict

Features:
- Circular import detection via tracking loaded paths
- Path safety: prevents ../ escape outside base directory
- Relative path resolution from the importing file's directory
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from helen.core.ast import ProgramNode
from helen.core.errors import ErrorReporter
from helen.core.lexer import Scanner
from helen.core.parser import Parser


@dataclass
class ImportResult:
    """Result of resolving an import.

    Attributes:
        path: The resolved absolute path.
        content: Parsed/loaded content (ProgramNode for .helen, str for text,
                 dict/list for json/yaml).
        format: The detected file format ('helen', 'text', 'json', 'yaml').
    """

    path: str
    content: Any
    format: str


class ImportResolver:
    """Resolve and load imports for Helen programs (HLD 3.9).

    Handles multi-format loading, circular import detection, and path safety.

    Args:
        base_dir: The base directory for resolving relative paths.
                  All imports must be within this directory tree.
        error_reporter: Optional error reporter for import errors.
    """

    def __init__(
        self,
        base_dir: str | None = None,
        error_reporter: ErrorReporter | None = None,
    ) -> None:
        self.base_dir = os.path.abspath(base_dir or os.getcwd())
        self.errors = error_reporter or ErrorReporter()
        # Track resolved paths to detect circular imports
        self._loaded: set[str] = set()
        # Cache of ImportResult per loaded helen file path, so that
        # repeated imports of a helen file (e.g. transitively loaded
        # via another module, then imported directly) return a valid
        # result instead of None. Fixes Issue #10b.
        self._cached_results: dict[str, ImportResult] = {}
        # Registry for imported agents/functions
        self._agents: dict[str, Any] = {}  # name -> AgentDeclNode
        self._functions: dict[str, Any] = {}  # name -> FunctionDeclNode
        self._data: dict[str, Any] = {}  # alias -> loaded content
        # v1.17 (Issue #35 follow-up): Python module imports from
        # transitively-imported .helen files. Each entry is a
        # (module_name, alias_or_none) tuple so aliased imports like
        # `import "ui.renderer" as PyUIRenderer` preserve their alias.
        # The interpreter executes these during import so nested Python
        # dependencies are available when the imported module's functions
        # are called.
        self._python_imports: list[tuple[str, str | None]] = []

    def resolve(
        self, import_path: str, from_file: str | None = None
    ) -> ImportResult | None:
        """Resolve and load an import (HLD 3.9.1, 3.9.2).

        Args:
            import_path: The import path string (from import statement).
            from_file: The path of the file doing the import (for relative paths).

        Returns:
            ImportResult with resolved path, content, and format.
            None if the import could not be resolved.
        """
        # Resolve the path
        resolved = self._resolve_path(import_path, from_file)
        if resolved is None:
            return None

        # Path safety check
        if not self._is_safe_path(resolved):
            self.errors.error(
                None, f"Import path escapes base directory: {import_path}"
            )
            return None

        # Circular import detection
        abs_resolved = os.path.abspath(resolved)
        if abs_resolved in self._loaded:
            # Already loaded (possibly transitively). Return the cached
            # ImportResult if we have one — this is critical for helen files
            # that were loaded via _register_helen recursion, so a subsequent
            # direct import can still go through the non-aliased path in the
            # interpreter and register functions/consts properly.
            if abs_resolved in self._cached_results:
                return self._cached_results[abs_resolved]
            # Fall back to filename-alias lookup (works for data files
            # stored in _data under their alias).
            filename_alias = os.path.splitext(os.path.basename(resolved))[0]
            if filename_alias in self._data:
                return ImportResult(
                    path=abs_resolved, content=self._data[filename_alias], format=self._detect_format(resolved)
                )
            return None

        self._loaded.add(abs_resolved)

        # Load based on file extension
        fmt = self._detect_format(resolved)
        try:
            content = self._load_file(resolved, fmt)
        except (OSError, json.JSONDecodeError) as e:
            self.errors.error(None, f"Failed to import '{import_path}': {e}")
            self._loaded.discard(abs_resolved)
            return None

        # Register content based on format
        alias = os.path.splitext(os.path.basename(resolved))[0]
        if fmt == "helen":
            self._register_helen(content, alias, resolved)
        else:
            self._data[alias] = content

        result = ImportResult(path=abs_resolved, content=content, format=fmt)
        if fmt == "helen":
            self._cached_results[abs_resolved] = result
        return result

    def _resolve_path(self, import_path: str, from_file: str | None) -> str | None:
        """Resolve an import path to an absolute filesystem path.

        Relative paths are resolved from the directory of from_file,
        falling back to base_dir.
        """
        path = Path(import_path)

        # If it's an absolute path, use it directly
        if path.is_absolute():
            return str(path)

        # Try relative to from_file's directory
        if from_file:
            from_dir = os.path.dirname(os.path.abspath(from_file))
            candidate = os.path.join(from_dir, import_path)
            if os.path.exists(candidate):
                return os.path.normpath(candidate)

        # Try relative to base_dir
        candidate = os.path.join(self.base_dir, import_path)
        if os.path.exists(candidate):
            return os.path.normpath(candidate)

        self.errors.error(None, f"Import file not found: {import_path}")
        return None

    def _is_safe_path(self, resolved: str) -> bool:
        """Check that resolved path is safe to import (HLD 3.9.2 path safety).

        Allows:
        - Absolute paths (for REPL and explicit imports)
        - Paths within base_dir (for relative imports)
        
        Prevents:
        - Relative paths that escape base_dir via ../
        """
        abs_resolved = os.path.realpath(os.path.abspath(resolved))
        
        # Allow absolute paths (explicit imports from REPL or scripts)
        if os.path.isabs(resolved):
            return True
        
        # For relative paths, ensure they stay within base_dir
        abs_base = os.path.realpath(os.path.abspath(self.base_dir))
        return abs_resolved.startswith(abs_base + os.sep) or abs_resolved == abs_base

    @staticmethod
    def _detect_format(path: str) -> str:
        """Detect the file format from its extension (HLD 3.9.1)."""
        ext = Path(path).suffix.lower()
        if ext == ".helen":
            return "helen"
        if ext in (".md", ".txt"):
            return "text"
        if ext == ".json":
            return "json"
        if ext in (".yaml", ".yml"):
            return "yaml"
        return "text"  # default to text for unknown extensions

    def _load_file(self, path: str, fmt: str) -> Any:
        """Load and parse a file based on its detected format."""
        with open(path, "r", encoding="utf-8") as f:
            raw = f.read()

        if fmt == "helen":
            return self._parse_helen(raw, path)
        if fmt == "json":
            return json.loads(raw)
        # yaml requires pyyaml; if not available, return raw text
        if fmt == "yaml":
            try:
                import yaml  # noqa: PLC0415
                return yaml.safe_load(raw)
            except ImportError:
                return raw
        return raw  # text

    def _parse_helen(self, source: str, filename: str) -> ProgramNode:
        """Parse a .helen source file into a ProgramNode."""
        scanner = Scanner(source=source, file=filename)
        tokens = scanner.scan_all()
        parser = Parser(tokens)
        return parser.parse()

    def _register_helen(self, program: ProgramNode, alias: str, file_path: str | None = None) -> None:
        """Register agents/functions/constants from a parsed .helen file (HLD 3.9.1).

        Per HLD: import only registers Agent/Function/Const definitions to the
        global namespace. It does NOT execute the imported file's main block.
        
        P0 FIX: Also recursively process imports in the imported file.
        
        Args:
            program: The parsed ProgramNode from the .helen file
            alias: The alias for the module (filename without extension)
            file_path: The absolute path of the .helen file (for resolving nested imports)
        """
        from helen.core.ast import (  # noqa: PLC0415
            AgentDeclNode,
            FunctionDeclNode,
            VarDeclNode,
            ImportStmtNode,
            SharedStoreDeclNode,
        )

        for stmt in program.statements:
            if isinstance(stmt, AgentDeclNode):
                self._agents[stmt.name] = stmt
            elif isinstance(stmt, FunctionDeclNode):
                self._functions[stmt.name] = stmt
            elif isinstance(stmt, VarDeclNode) and (not stmt.mutable or stmt.shared):
                # Register const declarations and shared let (v1.10)
                # Store the VarDeclNode so we can evaluate it later
                self._data[stmt.name] = stmt
            elif isinstance(stmt, SharedStoreDeclNode):
                # v1.17 (Issue #35): Register shared store declarations
                # so they can be executed and made visible cross-module.
                # Previously these fell through and were silently dropped,
                # making the container name resolve to None when the module's
                # functions were called from another module.
                self._data[stmt.name] = stmt
            elif isinstance(stmt, ImportStmtNode):
                # Recursively process imports in the imported file
                # Resolve the import path relative to the current file's directory
                import_path = stmt.module_path
                # v1.17 (Issue #35 follow-up): collect Python module imports
                # so the interpreter can execute them when the importing
                # .helen module is loaded. Without this, nested Python
                # imports (e.g. helper.helen importing 'json') were only
                # validated but never executed, causing the Python module
                # name to resolve to None at runtime.
                from helen.core import is_helen_data_file  # noqa: PLC0415
                if not is_helen_data_file(import_path):
                    module_name = import_path
                    if module_name.endswith('.py'):
                        module_name = module_name[:-3]
                    # Preserve the alias (if any) so the interpreter
                    # defines the Python module under the correct name.
                    # E.g. `import "ui.renderer" as PyUIRenderer` must
                    # be defined as PyUIRenderer, not renderer.
                    import_alias = stmt.alias
                    entry = (module_name, import_alias)
                    if entry not in self._python_imports:
                        self._python_imports.append(entry)
                # Pass the current file's path so nested imports can be resolved correctly
                self.resolve(import_path, file_path)

    @property
    def agents(self) -> dict[str, Any]:
        """Registered agent definitions from imports."""
        return self._agents

    @property
    def functions(self) -> dict[str, Any]:
        """Registered function definitions from imports."""
        return self._functions

    @property
    def python_imports(self) -> list[tuple[str, str | None]]:
        """Python module imports from transitively-loaded .helen files.

        Each entry is (module_name, alias_or_none). The alias preserves
        user-specified names like ``import "ui.renderer" as PyUIRenderer``.
        """
        return self._python_imports

    @property
    def data(self) -> dict[str, Any]:
        """Registered imported data (text/json/yaml content by alias)."""
        return self._data

    def reset(self) -> None:
        """Clear all loaded paths and registered content."""
        self._loaded.clear()
        self._cached_results.clear()
        self._agents.clear()
        self._functions.clear()
        self._data.clear()
