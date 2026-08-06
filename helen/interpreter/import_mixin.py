"""Import handling mixin for the Helen interpreter.

Extracted from interpreter.py to improve code organization.
Provides visit methods and helpers for import statements.
"""

from __future__ import annotations

import os
from typing import Any

from helen.core.ast import ImportStmtNode
from helen.interpreter.environment import Environment
from helen.runtime.import_resolver import ImportResult


class ImportMixin:
    """Mixin providing import handling visitor methods.

    Host class must provide:
    - environment: Environment
    - errors: ErrorReporter
    - import_resolver: ImportResolver
    - _agents: dict
    - _functions: dict
    - _shared_vars: set
    - _push_scope() -> context manager
    - _runtime_error(span, message) -> None
    """

    # Declare attributes expected from host class
    environment: Any
    errors: Any
    import_resolver: Any
    _agents: Any
    _functions: Any
    _shared_vars: Any

    def visit_import_stmt(self, node: ImportStmtNode) -> object:
        """Execute an import statement (HLD 3.9, 3.6.2).

        Per HLD: import only parses and registers Agent/Function definitions
        from the imported file. It does NOT execute the imported file's main block.

        Supported formats:
        - .helen: Parse and register agents/functions to global namespace
        - .md/.txt: Load as text, register to import_resolver.data
        - .json/.yaml: Parse as data, register to import_resolver.data
        - Python modules (no extension or .py): Import via Python FFI
        - v1.34: Stdlib modules (std.str, std.list, etc.)

        v1.6: Module imports support function/agent access via alias
        """
        # v1.34: Handle stdlib module imports
        if node.is_stdlib_module:
            return self._import_stdlib_module(node)

        # Check if this is a Python module import
        # Python modules: no extension, or .py extension, or dotted names like "os.path"
        # Helen/data files: .helen, .json, .md, .txt, .yaml, .yml
        from helen.core import is_helen_data_file  # noqa: PLC0415

        if not is_helen_data_file(node.module_path):
            # Python module import via FFI
            return self._import_python_module(node)

        # Track the current file for relative path resolution
        current_file = node.source_file if hasattr(node, 'source_file') else None

        result = self.import_resolver.resolve(node.module_path, current_file)
        if result is None:
            # v1.18.2: Fail fast with a clear error instead of silently
            # registering nothing and later surfacing a misleading
            # "'<name>' is not callable" / "'NoneType' has no property".
            self._runtime_error(
                node.span,
                f"Failed to import '{node.module_path}': file not found or could not be loaded",
            )
            return None  # unreachable: _runtime_error raises

        # Register imported content into the interpreter's namespaces
        if result.format == "helen":
            # v1.6: If alias is provided, create a module object for function/agent access
            if node.alias:
                module_obj = self._create_module_object(result)
                self.environment.define(node.alias, module_obj)
                # v1.10/v1.39.2: Register shared let for aliased imports.
                # Per-file so a transitive file's shared let (whose initializer
                # may reference that file's own consts) is evaluated against
                # its own module_env, not the aliased module's env.
                self._register_shared_vars_per_file()
            else:
                # No alias: register agents/functions/constants directly to global namespace.
                # v1.39.2: Process EVERY loaded .helen file (direct + transitive) so
                # each function maps to its OWN file's module_env. Previously the flat
                # resolver registries were iterated once per direct import, mapping
                # transitive functions to the direct file's env and breaking their
                # access to their own file's stdlib imports.
                self._process_loaded_helen_files(register_globals=True)
        else:
            # Register data by user-specified alias (or filename if no alias)
            alias = node.alias if node.alias else os.path.splitext(os.path.basename(result.path))[0]
            self.environment.define(alias, result.content)

        return None

    def _register_imported_shared_vars(self, module_env: Environment | None = None) -> None:
        """Evaluate shared let variables from imported modules and define them.

        v1.10: Imported shared let must be available in the importing
        interpreter's environment so the imported module's functions
        can access them through the scope chain.

        v1.39.2: Deprecated for the aliased path - prefer
        _register_shared_vars_per_file which evaluates each file's shared let
        against its own module_env. Kept for compatibility.
        """
        from helen.core.ast import VarDeclNode  # noqa: PLC0415
        for name, var_node in self.import_resolver.data.items():
            if not isinstance(var_node, VarDeclNode):
                continue
            if not var_node.shared:
                continue
            # Only define if not already in environment
            try:
                self.environment.lookup(name)
            except NameError:
                value = None
                resolved = False
                if module_env is not None:
                    try:
                        value = module_env.lookup(name)
                        resolved = True
                    except NameError:
                        pass
                if not resolved and var_node.initializer is not None:
                    if module_env is not None:
                        with self._push_scope(module_env):
                            value = var_node.initializer.accept(self)
                    else:
                        value = var_node.initializer.accept(self)
                    resolved = True
                if not resolved:
                    value = None
                self.environment.define(name, value)
                self._shared_vars.add(name)

    def _register_shared_vars_per_file(self) -> None:
        """Register shared let from every loaded file into the global env.

        v1.39.2: Each file's shared let was already evaluated into that file's
        module_env by _get_file_module_env (where the file's consts are
        visible). Here we expose the already-computed value on the global env
        for cross-module access, instead of re-evaluating initializers against
        a single (possibly wrong) module_env.
        """
        from helen.core.ast import VarDeclNode  # noqa: PLC0415
        for fpath in self.import_resolver.loaded_helen_paths():
            abs_fpath = os.path.abspath(fpath)
            module_env = self._get_file_module_env(abs_fpath)
            if module_env is None:
                continue
            for name, var_node in self.import_resolver.file_data(abs_fpath).items():
                if not isinstance(var_node, VarDeclNode) or not var_node.shared:
                    continue
                try:
                    self.environment.lookup(name)
                except NameError:
                    try:
                        value = module_env.lookup(name)
                    except NameError:
                        value = None
                    self.environment.define(name, value)
                    self._shared_vars.add(name)

    def _register_imported_consts_and_shared(self, module_env: Environment | None = None) -> None:
        """Evaluate const and shared let from imported modules into the environment."""
        from helen.core.ast import VarDeclNode  # noqa: PLC0415
        for name, const_node in self.import_resolver.data.items():
            try:
                self.environment.lookup(name)
            except NameError:
                if isinstance(const_node, VarDeclNode) and const_node.initializer is not None:
                    if module_env is not None:
                        try:
                            value = module_env.lookup(name)
                        except NameError:
                            with self._push_scope(module_env):
                                value = const_node.initializer.accept(self)
                    else:
                        value = const_node.initializer.accept(self)
                    self.environment.define(name, value, is_const=not const_node.mutable)
                    if const_node.shared:
                        self._shared_vars.add(name)

    # ------------------------------------------------------------------
    # v1.39.2: Per-file module environment construction
    # ------------------------------------------------------------------

    def _get_file_module_env(self, path: str) -> Environment | None:
        """Build (and cache) the module environment for a single .helen file.

        The module_env contains ONLY this file's own consts, shared stores,
        Python imports, and stdlib imports - so a function defined in this
        file runs with access to exactly the symbols its file declares. This
        replaces the v1.39.1 approach of building one module_env per
        directly-imported file and sharing it across all (flat-accumulated)
        functions, which broke transitive functions that needed their own
        file's stdlib imports.

        Idempotent: the built env is cached in self._module_envs keyed by
        absolute path. Returns None if the file's ImportResult is unavailable.
        """
        abs_path = os.path.abspath(path)
        if abs_path in self._module_envs:
            return self._module_envs[abs_path]

        result = self.import_resolver.file_result(abs_path)
        if result is None or result.content is None:
            return None

        from helen.core.ast import VarDeclNode as _VDN  # noqa: PLC0415
        from helen.core.ast import SharedStoreDeclNode as _SSDN  # noqa: PLC0415
        from helen.core.ast import ImportStmtNode as _ImpNode  # noqa: PLC0415

        module_env = Environment(parent=self.environment)

        # 1. Const declarations and shared stores declared in THIS file.
        for name, data in self.import_resolver.file_data(abs_path).items():
            if isinstance(data, _VDN) and (not data.mutable or data.shared):
                if data.initializer is not None:
                    with self._push_scope(module_env):
                        value = data.initializer.accept(self)
                else:
                    value = None
                module_env.define(name, value, is_const=not data.mutable)
            elif isinstance(data, _SSDN):
                with self._push_scope(module_env):
                    container = data.accept(self)
                if container is not None:
                    # Shared stores are cross-module; define on the global env
                    # too (idempotent via NameError guard) for visibility.
                    module_env.define(name, container, is_const=True)
                    try:
                        self.environment.lookup(name)
                    except NameError:
                        self.environment.define(name, container, is_const=True)

        # 2. Python module imports declared in THIS file.
        if not hasattr(self, '_python_runtime'):
            from helen.ffi.python_runtime import DefaultPythonRuntime  # noqa: PLC0415
            self._python_runtime = DefaultPythonRuntime()
        for py_module_name, py_alias in self.import_resolver.file_python_imports(abs_path):
            try:
                module = self._python_runtime.import_module(py_module_name)
                name = py_alias or py_module_name.split('.')[-1]
                module_env.define(name, module)
                # Also expose on the global env (matches v1.17 behavior).
                try:
                    self.environment.lookup(name)
                except NameError:
                    self.environment.define(name, module)
            except ImportError:
                pass  # Best-effort; already validated by resolver

        # 3. Stdlib imports declared in THIS file (the fix: each file's
        # functions see their own file's stdlib imports, not a shared set).
        with self._push_scope(module_env):
            for stmt in result.content.statements:
                if isinstance(stmt, _ImpNode) and stmt.is_stdlib_module:
                    self._import_stdlib_module(stmt)

        self._module_envs[abs_path] = module_env
        return module_env

    def _process_loaded_helen_files(self, register_globals: bool) -> None:
        """Process every loaded .helen file (direct + transitive) per-file.

        Builds a module_env for each file (via _get_file_module_env, idempotent)
        and, when ``register_globals`` is set, registers each file's
        agents/functions/consts into the global namespace. Per-file processing
        is the v1.39.2 fix: previously the flat resolver registries were
        iterated once per direct import, so transitive functions got mapped to
        the directly-imported file's module_env and lost access to their own
        file's stdlib imports.
        """
        for path in self.import_resolver.loaded_helen_paths():
            abs_path = os.path.abspath(path)
            module_env = self._get_file_module_env(abs_path)
            if module_env is None:
                continue
            if register_globals:
                self._register_file_globals(abs_path, module_env)

    def _register_file_globals(self, abs_path: str, module_env: Environment) -> None:
        """Register one file's agents/functions/consts into the global namespace.

        Agents and functions use first-wins semantics (``if name not in ...``);
        the function's module_env mapping is set at the same time so the node
        and its env stay consistent. Consts/shared-let are defined on the global
        env (idempotent via NameError guard), evaluated against ``module_env``
        so the file's stdlib/Python imports are available to initializers.
        """
        from helen.core.ast import VarDeclNode as _VDN  # noqa: PLC0415

        for name, agent in self.import_resolver.file_agents(abs_path).items():
            if name not in self._agents:
                self._agents[name] = agent
        for name, func in self.import_resolver.file_functions(abs_path).items():
            if name not in self._functions:
                self._functions[name] = func
                # Set the env mapping only when we register the node, so a
                # first-wins function node stays paired with its own file's env.
                self._function_module_envs[name] = module_env

        for name, const_node in self.import_resolver.file_data(abs_path).items():
            if not isinstance(const_node, _VDN):
                continue  # shared stores already defined into module_env/global env
            try:
                self.environment.lookup(name)
            except NameError:
                if const_node.initializer is not None:
                    with self._push_scope(module_env):
                        value = const_node.initializer.accept(self)
                else:
                    value = None
                self.environment.define(name, value, is_const=not const_node.mutable)
                if const_node.shared:
                    self._shared_vars.add(name)

    def _create_module_object(self, result: ImportResult) -> dict:
        """Create a module object containing agents and functions from imported .helen file (v1.6).

        v1.10: Also creates a module-level Environment that captures the module's
        consts and shared let.

        v1.16: Also registers module functions as callable wrappers in module_env.

        v1.39.2: Uses per-file module_envs (built by _get_file_module_env) so each
        function - including those from transitively-imported files - runs in its
        own file's environment. Sibling/cross-file wrappers defined in the direct
        module's env use each function's OWN file's env as parent_env, fixing the
        bug where transitive functions ran in the directly-imported file's env.
        """
        # Build module_envs for every loaded file (direct + transitive). Each
        # env carries only its file's consts/Python/stdlib imports.
        self._process_loaded_helen_files(register_globals=False)

        direct_path = os.path.abspath(result.path)
        module_env = self._get_file_module_env(direct_path)
        if module_env is None:
            # No ImportResult available (shouldn't happen for a helen import);
            # fall back to an empty env so downstream code still gets a dict.
            module_env = Environment(parent=self.environment)

        module = {
            "__type__": "module",
            "__path__": result.path,
            "__agents__": {},
            "__functions__": {},
            "__data__": {},
            "__env__": module_env,
        }

        # Define callable wrappers in the direct module's env for EVERY loaded
        # file's functions, so the direct module's functions can call siblings
        # and transitive functions via scope. Each wrapper uses the function's
        # OWN file's module_env (not the direct module's env) as parent_env.
        for fpath in self.import_resolver.loaded_helen_paths():
            abs_fpath = os.path.abspath(fpath)
            file_env = self._get_file_module_env(abs_fpath) or module_env
            for name, func in self.import_resolver.file_functions(abs_fpath).items():
                module_env.define(name, self._create_module_function_wrapper(func, file_env))

        # The module object exposes only the DIRECT file's symbols via `m.x`.
        for name, agent in self.import_resolver.file_agents(direct_path).items():
            module["__agents__"][name] = agent
        for name, func in self.import_resolver.file_functions(direct_path).items():
            module["__functions__"][name] = func
        for name, data in self.import_resolver.file_data(direct_path).items():
            module["__data__"][name] = data

        return module


    def _import_python_module(self, node: ImportStmtNode) -> object:
        """Import a Python module via FFI."""
        from helen.ffi.python_runtime import DefaultPythonRuntime

        if not hasattr(self, '_python_runtime'):
            self._python_runtime = DefaultPythonRuntime()

        module_name = node.module_path
        if module_name.endswith('.py'):
            module_name = module_name[:-3]

        try:
            module = self._python_runtime.import_module(module_name)
            alias = node.alias if node.alias else module_name.split('.')[-1]
            self.environment.define(alias, module)
        except ImportError as e:
            self._runtime_error(node.span, f"Cannot import Python module '{module_name}': {e}")
            return None

        return None

    def _import_stdlib_module(self, node: ImportStmtNode) -> object:
        """Import a stdlib module (v1.34).

        Supports three forms:
        - import std.str.{len, upper}  # selective import
        - import std.str.*             # import all
        - import std.str as S          # namespace import
        """
        from helen.stdlib.modules import (
            StrModule, ListModule, DictModule, MathModule,
            TimeModule, FileModule, SystemModule, IOModule,
            CoreModule, DataModule, NetworkModule, PathModule,
            ToolsModule, DebugModule, ContextModule, TranscriptModule,
            MediaModule, TestModule, QualityModule, LLMModule,
            CryptoModule, ConcurrencyModule,
        )

        # Map module names to module classes
        module_map = {
            # v1.34
            "std.str": StrModule,
            "std.list": ListModule,
            "std.dict": DictModule,
            "std.math": MathModule,
            "std.time": TimeModule,
            "std.file": FileModule,
            "std.system": SystemModule,
            "std.io": IOModule,
            # v1.38
            "std.core": CoreModule,
            "std.data": DataModule,
            "std.network": NetworkModule,
            "std.path": PathModule,
            "std.tools": ToolsModule,
            "std.debug": DebugModule,
            "std.context": ContextModule,
            "std.transcript": TranscriptModule,
            "std.media": MediaModule,
            "std.test": TestModule,
            "std.quality": QualityModule,
            "std.llm": LLMModule,
            "std.crypto": CryptoModule,
            "std.concurrency": ConcurrencyModule,
        }

        module_name = node.module_name
        if module_name not in module_map:
            self._runtime_error(
                node.span,
                f"Unknown stdlib module '{module_name}'. Available: {', '.join(module_map.keys())}",
            )
            return None

        module_class = module_map[module_name]
        exports = module_class.__exports__

        # Handle different import styles
        if node.namespace:
            # Namespace import: import std.str as S
            # Create a module object with all functions
            module_obj = {}
            for name, func in exports.items():
                module_obj[name] = func
            self.environment.define(node.namespace, module_obj, is_const=True)
        elif node.imported_names and "*" in node.imported_names:
            # Wildcard import: import std.str.*
            # Import all functions directly into current scope
            for name, func in exports.items():
                self.environment.define(name, func, is_const=True)
            # v1.39: Also import aliases (e.g. Chinese 长度 for len)
            from helen.stdlib import stdlib as _stdlib  # noqa: PLC0415
            for alias, canonical in _stdlib.aliases.items():
                if canonical in exports:
                    self.environment.define(alias, exports[canonical], is_const=True)
        elif node.imported_names:
            # Selective import: import std.str.{len, upper}
            # Import only specified functions
            for name in node.imported_names:
                if name not in exports:
                    self._runtime_error(
                        node.span,
                        f"Function '{name}' not found in module '{module_name}'. "
                        f"Available: {', '.join(exports.keys())}",
                    )
                    return None
                self.environment.define(name, exports[name], is_const=True)
        else:
            # Default: import all (same as wildcard)
            for name, func in exports.items():
                self.environment.define(name, func, is_const=True)
            # v1.39: Also import aliases
            from helen.stdlib import stdlib as _stdlib  # noqa: PLC0415
            for alias, canonical in _stdlib.aliases.items():
                if canonical in exports:
                    self.environment.define(alias, exports[canonical], is_const=True)

        return None
