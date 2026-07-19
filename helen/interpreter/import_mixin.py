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

        v1.6: Module imports support function/agent access via alias
        """
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
                # v1.10: Also register shared let for aliased imports.
                self._register_imported_shared_vars(module_obj.get("__env__"))
            else:
                # No alias: register agents/functions/constants directly to global namespace
                from helen.core.ast import VarDeclNode as _VDN
                from helen.core.ast import SharedStoreDeclNode as _SSDN
                module_env = Environment(parent=self.environment)
                for name, data in self.import_resolver.data.items():
                    if isinstance(data, _VDN) and (not data.mutable or data.shared):
                        if data.initializer is not None:
                            with self._push_scope(module_env):
                                value = data.initializer.accept(self)
                        else:
                            value = None
                        module_env.define(name, value, is_const=not data.mutable)
                    elif isinstance(data, _SSDN):
                        # v1.17 (Issue #35): Execute shared store/channel declaration
                        with self._push_scope(module_env):
                            container = data.accept(self)
                        if container is not None:
                            self.environment.define(name, container, is_const=True)

                # v1.17 (Issue #35 follow-up): Execute nested Python imports
                if hasattr(self.import_resolver, 'python_imports'):
                    if not hasattr(self, '_python_runtime'):
                        from helen.ffi.python_runtime import DefaultPythonRuntime
                        self._python_runtime = DefaultPythonRuntime()
                    for py_module_name, py_alias in self.import_resolver.python_imports:
                        try:
                            module = self._python_runtime.import_module(py_module_name)
                            name = py_alias or py_module_name.split('.')[-1]
                            module_env.define(name, module)
                            self.environment.define(name, module)
                        except ImportError:
                            pass  # Best-effort; already validated by resolver

                for name, agent in self.import_resolver.agents.items():
                    if name not in self._agents:
                        self._agents[name] = agent
                for name, func in self.import_resolver.functions.items():
                    if name not in self._functions:
                        self._functions[name] = func
                        if not hasattr(self, '_function_module_envs'):
                            self._function_module_envs: dict[str, Environment] = {}
                        self._function_module_envs[name] = module_env
                # Register constants and shared let
                self._register_imported_consts_and_shared(module_env)
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

    def _create_module_object(self, result: ImportResult) -> dict:
        """Create a module object containing agents and functions from imported .helen file (v1.6).

        v1.10: Also creates a module-level Environment that captures the module's
        consts and shared let.

        v1.16: Also registers module functions as callable wrappers in module_env.
        """
        from helen.core.ast import VarDeclNode  # noqa: PLC0415
        from helen.core.ast import SharedStoreDeclNode as _SSDN  # noqa: PLC0415
        module = {
            "__type__": "module",
            "__path__": result.path,
            "__agents__": {},
            "__functions__": {},
            "__data__": {}
        }

        module_env = Environment(parent=self.environment)
        for name, data in self.import_resolver.data.items():
            if isinstance(data, VarDeclNode) and (not data.mutable or data.shared):
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
                    self.environment.define(name, container, is_const=True)

        # Execute nested Python imports
        if hasattr(self.import_resolver, 'python_imports'):
            if not hasattr(self, '_python_runtime'):
                from helen.ffi.python_runtime import DefaultPythonRuntime
                self._python_runtime = DefaultPythonRuntime()
            for py_module_name, py_alias in self.import_resolver.python_imports:
                try:
                    py_mod = self._python_runtime.import_module(py_module_name)
                    name = py_alias or py_module_name.split('.')[-1]
                    module_env.define(name, py_mod)
                    self.environment.define(name, py_mod)
                except ImportError:
                    pass

        module["__env__"] = module_env

        # v1.16: Register module functions in module_env as callable wrappers
        for name, func in self.import_resolver.functions.items():
            wrapper = self._create_module_function_wrapper(func, module)
            module_env.define(name, wrapper)

        for name, agent in self.import_resolver.agents.items():
            module["__agents__"][name] = agent

        for name, func in self.import_resolver.functions.items():
            module["__functions__"][name] = func

        for name, data in self.import_resolver.data.items():
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
