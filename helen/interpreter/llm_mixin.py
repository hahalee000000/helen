"""LLM mixin for the Helen interpreter.

Extracts all LLM-related visitor methods and helpers from the main
Interpreter class to reduce its size and improve maintainability.

The mixin expects the host class (Interpreter) to provide:
- self.llm_runtime: LLMRuntime
- self.environment: Environment
- self.errors: ErrorReporter
- self._current_agent: AgentDeclNode | None
- self._history: list[HistoryMessage]
- self._history_manager: HistoryManager
- self._stringify(value) -> str  (static method)
- self._execute_stmts(stmts) -> object
"""

from __future__ import annotations

import os
from typing import Any

from helen.core.ast import (
    AgentDeclNode,
    LlmActExprNode,
    LlmBranchNode,
    LlmIfStmtNode,
    LlmStreamStmtNode,
    LiteralNode,
)
from helen.core.errors import ErrorCode
from helen.interpreter.exceptions import HelenRuntimeError
from helen.runtime.history import Message as HistoryMessage
from helen.runtime.observability import LLMAuditEntry

# Precompiled regex for prompt template rendering (avoids re.compile on every call)
_PROMPT_VAR_RE = __import__('re').compile(r'\{\{(.+?)\}\}')


class LlmMixin:
    """Mixin providing LLM-related visitor methods and helpers.

    This mixin is designed to be used with the Interpreter class via
    multiple inheritance. It expects the host class to provide certain
    attributes (see module docstring).
    """

    # These attributes are provided by the host class (Interpreter)
    llm_runtime: Any
    environment: Any
    errors: Any
    _current_agent: AgentDeclNode | None
    _history: list[HistoryMessage]
    _history_manager: Any

    # Skill index cache (avoid rebuilding on every LLM call)
    _skill_index_cache: str | None = None
    _skill_index_mtime: float = 0.0

    # Note: _execute_stmts and _stringify are provided by the host class.
    # They are called via self but not declared here to avoid type conflicts.

    # ------------------------------------------------------------------
    # LLM Visitor Methods
    # ------------------------------------------------------------------

    def visit_llm_if_stmt(self: Any, node: LlmIfStmtNode) -> object:
        """Execute llm if statement (HLD 3.6.5, 3.6.6).

        Flow:
        1. Build route prompt from description + branches
        2. Call runtime.route() with function calling schema
        3. Match returned branch name to execute corresponding body
        4. If no match or parsing fails -> execute default branch
        """
        branches = []
        for b in node.branches:
            if b.condition is not None:
                # Get branch name from condition expression
                if isinstance(b.condition, LiteralNode):
                    branches.append(str(b.condition.value))
                else:
                    branches.append(str(b.condition))
            else:
                branches.append("default")

        # Evaluate description expression to string
        if isinstance(node.description, str):
            desc_str = node.description
        else:
            desc_val = node.description.accept(self)
            desc_str = str(desc_val) if desc_val is not None else ""

        # Get context from environment (conversation summary)
        context = self._get_context()

        # Record user message to history
        self._add_to_history("user", f"[route] {desc_str}")

        # Call LLM routing
        try:
            selected = self.llm_runtime.route(desc_str, branches, context)
        except HelenRuntimeError:
            # LLM call failed -> execute default
            selected = None

        # Record assistant response to history
        if selected is not None:
            self._add_to_history("assistant", f"[routed to: {selected}]")

        # Validate against pre-defined enum (HLD 3.6.6: branch must match schema)
        if selected is not None and selected not in branches:
            selected = None

        # Find matching branch
        for b in node.branches:
            if b.condition is not None:
                branch_name = None
                if isinstance(b.condition, LiteralNode):
                    branch_name = str(b.condition.value)
                else:
                    branch_name = str(b.condition)
                if branch_name == selected:
                    old_env = self.environment
                    self.environment = self.environment.enter_scope()
                    try:
                        return self._execute_stmts(b.body)
                    finally:
                        self.environment = old_env

        # No match -> execute default
        for b in node.branches:
            if b.condition is None:
                old_env = self.environment
                self.environment = self.environment.enter_scope()
                try:
                    return self._execute_stmts(b.body)
                finally:
                    self.environment = old_env
        return None

    def visit_llm_branch(self: Any, node: LlmBranchNode) -> object:
        """Execute an llm if branch body."""
        return self._execute_stmts(node.body)

    def visit_llm_act_expr(self: Any, node: LlmActExprNode) -> object:
        """Execute llm act as an expression: llm act <prompt_expr>?

        Evaluates the prompt expression and calls the LLM runtime.
        Returns the LLM response text.
        If inside an agent with a prompt field, uses it as system_prompt.

        Bare form (``llm act`` with no expression, or ``llm act ""``):
        When inside an agent context, the agent's rendered prompt template
        is used as the user message automatically. This avoids redundant
        repetition when the agent's prompt already contains all necessary
        information (HLD 3.6.5).
        """
        # P1 optimization: Cache rendered prompt for this LLM call
        # Avoids multiple _render_prompt_template calls during single llm act
        rendered_prompt_cache = self._get_rendered_agent_prompt()
        
        # Evaluate the prompt expression
        if node.prompt is not None:
            prompt = node.prompt.accept(self)
            if not isinstance(prompt, str):
                prompt = self._stringify(prompt)
        else:
            prompt = ""

        # Bare form: if prompt is empty and we're inside an agent,
        # use the rendered agent prompt as the user message
        if not prompt and self._current_agent is not None:
            if rendered_prompt_cache:
                prompt = rendered_prompt_cache

        # Extract agent settings if inside an agent context
        model = self._get_agent_setting("model")
        temperature = float(self._get_agent_setting("temperature", 1.0))
        max_turns = int(self._get_agent_setting("max-turns", 1))

        # Build tools list: always include load_skill + agent-declared tools
        tools = self._build_tools_list()

        # When tools are available, ensure at least 3 turns (tool call + tool result + response)
        if tools and max_turns < 3:
            max_turns = 3

        # Use cached rendered agent prompt as system_prompt (P1 optimization)
        system_prompt = rendered_prompt_cache

        # Inject skill index into system prompt
        skill_index = self._build_skill_index()
        if skill_index:
            system_prompt = (system_prompt or "") + "\n\n" + skill_index

        # Record user message to history
        self._add_to_history("user", prompt)

        # Audit log entry (P2: LLM call audit)
        import time
        audit_start = time.time()
        agent_name = self._current_agent.name if self._current_agent else None

        try:
            # Create custom dispatch function that can execute Helen functions
            dispatch_fn = self._create_dispatch_fn()

            response = self.llm_runtime.act(
                prompt, tools=tools, model=model,
                temperature=temperature, max_turns=max_turns,
                system_prompt=system_prompt,
                dispatch_fn=dispatch_fn,
            )
            audit_duration = (time.time() - audit_start) * 1000

            # Log to audit trail
            actual_model = model or getattr(self.llm_runtime, 'default_model', None) or 'default'
            audit_entry = LLMAuditEntry(
                timestamp=audit_start,
                call_type="act",
                agent_name=agent_name,
                model=actual_model,
                prompt=prompt,
                response=response.text if response else None,
                tokens_in=getattr(response, 'usage', {}).get('prompt_tokens', 0) if response else 0,
                tokens_out=getattr(response, 'usage', {}).get('completion_tokens', 0) if response else 0,
                duration_ms=audit_duration,
            )
            self.observability.llm_audit.log(audit_entry)

            # Record assistant response to history
            if response and response.text:
                self._add_to_history("assistant", response.text)
            return response.text if response else None
        except HelenRuntimeError as e:
            audit_duration = (time.time() - audit_start) * 1000
            actual_model = model or getattr(self.llm_runtime, 'default_model', None) or 'default'
            audit_entry = LLMAuditEntry(
                timestamp=audit_start,
                call_type="act",
                agent_name=agent_name,
                model=actual_model,
                prompt=prompt,
                duration_ms=audit_duration,
                error=str(e),
            )
            self.observability.llm_audit.log(audit_entry)
            return None
        except RuntimeError as e:
            # Python RuntimeError from LLM runtime (e.g. API errors) —
            # wrap in HelenRuntimeError so it propagates to the user
            audit_duration = (time.time() - audit_start) * 1000
            actual_model = model or getattr(self.llm_runtime, 'default_model', None) or 'default'
            audit_entry = LLMAuditEntry(
                timestamp=audit_start,
                call_type="act",
                agent_name=agent_name,
                model=actual_model,
                prompt=prompt,
                duration_ms=audit_duration,
                error=str(e),
            )
            self.observability.llm_audit.log(audit_entry)
            raise HelenRuntimeError(str(e), node.span) from e

    def visit_llm_stream_stmt(self: Any, node: LlmStreamStmtNode) -> object:
        """Execute llm stream statement: stream LLM response chunk by chunk.

        If on_chunk callback is provided, call it for each chunk.
        Otherwise, use stream_print to output chunks to stdout.

        Supports bare form (no prompt) inside agent main blocks.
        """
        # Evaluate the prompt expression (or use rendered agent prompt for bare form)
        if node.prompt is not None:
            prompt = node.prompt.accept(self)
            if not isinstance(prompt, str):
                prompt = self._stringify(prompt)
        else:
            # Bare form: use rendered agent prompt as user message
            prompt = self._get_rendered_agent_prompt()
            if not prompt:
                self.errors.error(
                    ErrorCode.RUNTIME_ERROR,
                    "llm stream (bare form) requires an agent context with a prompt",
                    node.span,
                )
                return None

        # Extract agent settings if inside an agent context
        model = self._get_agent_setting("model")
        temperature = float(self._get_agent_setting("temperature", 1.0))

        # Get rendered agent prompt as system_prompt (only if prompt was explicit)
        if node.prompt is not None:
            system_prompt = self._get_rendered_agent_prompt()
        else:
            # Bare form: system_prompt is the agent description
            system_prompt = self._get_agent_setting("description")

        # Inject skill index into system prompt
        skill_index = self._build_skill_index()
        if skill_index:
            system_prompt = (system_prompt or "") + "\n\n" + skill_index

        # Record user message to history
        self._add_to_history("user", prompt)

        # Check if LLM runtime supports streaming
        if not hasattr(self.llm_runtime, 'act_stream'):
            # Fallback to non-streaming if not supported
            self.errors.error(
                ErrorCode.RUNTIME_ERROR,
                "LLM runtime does not support streaming. Using fallback.",
                node.span,
            )
            response = self.llm_runtime.act(
                prompt, model=model, temperature=temperature,
                system_prompt=system_prompt,
            )
            if response and response.text:
                # Use stream_print for output
                from helen.stdlib import stdlib
                stream_print_fn = stdlib.lookup("stream_print")
                if stream_print_fn:
                    stream_print_fn.fn(response.text)
                    print()  # Add newline at end
                self._add_to_history("assistant", response.text)
            return None

        # Build tools list from agent declarations
        tools = self._build_tools_list()
        max_turns = int(self._get_agent_setting("max-turns", 1))
        if tools and max_turns < 3:
            max_turns = 3

        # Evaluate on_chunk callback if provided
        on_chunk_fn = None
        if node.on_chunk is not None:
            on_chunk_fn = node.on_chunk.accept(self)
            if not callable(on_chunk_fn):
                self.errors.error(
                    ErrorCode.SEMANTIC_TYPE_ERROR,
                    f"on_chunk callback must be callable, got {type(on_chunk_fn).__name__}",
                    node.span,
                )
                return None

        # Evaluate on_complete callback if provided
        on_complete_fn = None
        if node.on_complete is not None:
            on_complete_fn = node.on_complete.accept(self)
            if not callable(on_complete_fn):
                self.errors.error(
                    ErrorCode.SEMANTIC_TYPE_ERROR,
                    f"on_complete callback must be callable, got {type(on_complete_fn).__name__}",
                    node.span,
                )
                return None

        # Audit log entry (P2: LLM call audit)
        import time
        audit_start = time.time()
        agent_name = self._current_agent.name if self._current_agent else None

        try:
            # Create custom dispatch function that can execute Helen functions
            dispatch_fn = self._create_dispatch_fn()

            # Stream response with full tool-calling loop
            full_response = []
            tool_calls_log = []
            stream_usage = {}  # accumulated token usage across turns
            for event in self.llm_runtime.act_stream(
                prompt, model=model, temperature=temperature,
                system_prompt=system_prompt, tools=tools,
                max_turns=max_turns,
                dispatch_fn=dispatch_fn,
            ):
                event_type = event.get("type", "content")

                if event_type == "content":
                    content = event.get("content", "")
                    if content:
                        full_response.append(content)
                        if on_chunk_fn is not None:
                            on_chunk_fn(content)
                        else:
                            from helen.stdlib import stdlib
                            stream_print_fn = stdlib.lookup("stream_print")
                            if stream_print_fn:
                                stream_print_fn.fn(content)

                elif event_type == "tool_call":
                    fn_name = event.get("name", "")
                    fn_args = event.get("args", {})
                    tool_calls_log.append({"name": fn_name, "args": fn_args})
                    # Display tool call progress
                    args_str = ", ".join(f"{k}={v!r}" for k, v in fn_args.items())
                    progress = f"\n🔧 Calling {fn_name}({args_str})...\n"
                    if on_chunk_fn is None:
                        print(progress, end="", flush=True)
                    else:
                        on_chunk_fn(progress)

                elif event_type == "tool_result":
                    fn_name = event.get("name", "")
                    result = event.get("result", "")
                    # Truncate long results for display
                    display_result = result if len(result) <= 200 else result[:200] + "..."
                    result_msg = f"✅ {fn_name} returned: {display_result}\n"
                    if on_chunk_fn is None:
                        print(result_msg, end="", flush=True)
                    else:
                        on_chunk_fn(result_msg)

                elif event_type == "usage":
                    # Accumulate usage across multiple turns (tool-calling loop)
                    u = event.get("usage", {})
                    stream_usage["prompt_tokens"] = stream_usage.get("prompt_tokens", 0) + u.get("prompt_tokens", 0)
                    stream_usage["completion_tokens"] = stream_usage.get("completion_tokens", 0) + u.get("completion_tokens", 0)

                elif event_type == "error":
                    error_msg = event.get("message", "Unknown error")
                    self.errors.error(
                        ErrorCode.RUNTIME_ERROR,
                        f"Streaming error: {error_msg}",
                        node.span,
                    )
                    break

            # Add newline at end if using auto-output
            if on_chunk_fn is None:
                print()

            # Call on_complete callback if provided
            if on_complete_fn is not None:
                on_complete_fn()

            # Record assistant response to history
            full_text = "".join(full_response)
            if full_text:
                self._add_to_history("assistant", full_text)

            # Log to audit trail (P2)
            audit_duration = (time.time() - audit_start) * 1000
            # Use actual model name (from runtime if not specified)
            actual_model = model or getattr(self.llm_runtime, 'default_model', None) or 'default'
            audit_entry = LLMAuditEntry(
                timestamp=audit_start,
                call_type="stream",
                agent_name=agent_name,
                model=actual_model,
                prompt=prompt,
                response=full_text,
                tokens_in=stream_usage.get("prompt_tokens", 0),
                tokens_out=stream_usage.get("completion_tokens", 0),
                duration_ms=audit_duration,
                tool_calls=tool_calls_log,
            )
            self.observability.llm_audit.log(audit_entry)

            # Return the full accumulated response text
            return full_text
        except Exception as e:
            # Log error to audit trail (P2)
            audit_duration = (time.time() - audit_start) * 1000
            actual_model = model or getattr(self.llm_runtime, 'default_model', None) or 'default'
            audit_entry = LLMAuditEntry(
                timestamp=audit_start,
                call_type="stream",
                agent_name=agent_name,
                model=actual_model,
                prompt=prompt,
                duration_ms=audit_duration,
                error=str(e),
            )
            self.observability.llm_audit.log(audit_entry)

            self.errors.error(
                ErrorCode.RUNTIME_ERROR,
                f"Streaming LLM call failed: {e}",
                node.span,
            )
            return None

    # ------------------------------------------------------------------
    # LLM Helper Methods
    # ------------------------------------------------------------------

    def _get_agent_setting(self: Any, name: str, default: Any = None) -> Any:
        """Extract a setting from the current agent's declarations (HLD 3.6.5).

        Scans the current AgentDeclNode's declaration list for a matching
        setting and returns its literal value. Returns default if the agent
        context is not available or the setting is not declared.
        """
        if self._current_agent is None:
            return default
        for decl in self._current_agent.declarations:
            # Map HLD setting names to DeclarationNode fields
            field_map = {
                "model": "model",
                "temperature": "temperature",
                "max-turns": "max_turns",
            }
            field = field_map.get(name)
            if field is not None:
                value = getattr(decl, field, None)
                if value is not None and isinstance(value, LiteralNode):
                    return value.value
        return default

    def _build_tools_list(self: Any) -> list[dict[str, Any]]:
        """Build the tools list for llm act from agent declarations.

        Two sources of tools:
        1. functions { } block — Helen functions become LLM-callable tools
        2. tools ["web_search", ...] — Python tools from Helen tool registry

        Always includes load_skill (HLD 3.6.5) for Tier 2 skill disclosure.
        """
        from helen.runtime.tools import get_tool_schemas

        tools: list[dict[str, Any]] = []
        tool_names: set[str] = set()

        # 1. Scan functions block — Helen functions become tools
        if self._current_agent is not None and self._current_agent.functions:
            for fn_decl in self._current_agent.functions:
                schema = self._function_to_tool_schema(fn_decl)
                if schema and schema["function"]["name"] not in tool_names:
                    tools.append(schema)
                    tool_names.add(schema["function"]["name"])

        # 2. Check if agent declared specific Python tools
        declared_tools: list[str] | None = None
        if self._current_agent is not None:
            for decl in self._current_agent.declarations:
                if decl.tools is not None:
                    # decl.tools is a LiteralNode wrapping a list[str]
                    tools_node = decl.tools
                    if isinstance(tools_node, LiteralNode) and isinstance(tools_node.value, list):
                        declared_tools = tools_node.value
                    break

        if declared_tools is not None:
            # Agent explicitly declared tools — add those not already covered
            for schema in get_tool_schemas(declared_tools):
                if schema["function"]["name"] not in tool_names:
                    tools.append(schema)
                    tool_names.add(schema["function"]["name"])
        elif not tools:
            # No functions block and no explicit tools — include default useful tools
            default_tools = ["web_search", "web_fetch", "read_file",
                             "write_file", "patch_file", "calculate"]
            for schema in get_tool_schemas(default_tools):
                if schema["function"]["name"] not in tool_names:
                    tools.append(schema)
                    tool_names.add(schema["function"]["name"])

        # Always include load_skill for Tier 2 skill disclosure (HLD 3.6.5)
        if "load_skill" not in tool_names:
            tools.extend(get_tool_schemas(["load_skill"]))

        return tools

    def _function_to_tool_schema(self: Any, fn_decl: Any) -> dict[str, Any] | None:
        """Convert a Helen FunctionDeclNode to an OpenAI tool schema.

        Generates a JSON Schema for the function's parameters based on
        type annotations. Returns None if the function cannot be converted.
        """
        from helen.core.ast import TypeNode

        fn_name = fn_decl.name
        properties: dict[str, Any] = {}
        required: list[str] = []

        for param in fn_decl.params:
            param_name = param.name
            param_type = "string"  # default

            # Infer type from annotation
            if param.type_annotation is not None and isinstance(param.type_annotation, TypeNode):
                type_name = param.type_annotation.name.lower()
                if type_name in ("int", "integer"):
                    param_type = "integer"
                elif type_name in ("float", "number"):
                    param_type = "number"
                elif type_name in ("bool", "boolean"):
                    param_type = "boolean"
                elif type_name in ("list", "array"):
                    param_type = "array"
                    # TODO: infer items type if available
                elif type_name in ("map", "dict", "object"):
                    param_type = "object"
                else:
                    param_type = "string"

            properties[param_name] = {"type": param_type}

            # Required if no default value
            if param.default_value is None:
                required.append(param_name)

        return {
            "type": "function",
            "function": {
                "name": fn_name,
                "description": f"Helen function: {fn_name}",
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": required,
                },
            },
        }

    def _create_dispatch_fn(self: Any) -> Any:
        """Create a custom dispatch function that can execute Helen functions.

        Returns a function with signature (name: str, args: dict) -> str.
        When called:
        1. First checks if the name matches an agent's Helen function
        2. If yes, executes the Helen function and returns the result as JSON
        3. If no, falls back to the default Python tool dispatch
        """
        from helen.runtime.tools import dispatch_tool as default_dispatch
        import json

        # Capture current agent context
        agent = self._current_agent
        interpreter = self

        def dispatch(name: str, args: dict) -> str:
            # Check if this is an agent's Helen function
            if agent is not None and agent.functions:
                for fn_decl in agent.functions:
                    if fn_decl.name == name:
                        # Execute the Helen function
                        try:
                            result = interpreter._execute_agent_function(fn_decl, args)
                            # Convert result to JSON string for LLM
                            if isinstance(result, str):
                                return result
                            return json.dumps(result, ensure_ascii=False, default=str)
                        except Exception as e:
                            return json.dumps({"error": f"Helen function '{name}' failed: {e}"})

            # Fall back to Python tool dispatch
            return default_dispatch(name, args)

        return dispatch

    def _execute_agent_function(self: Any, fn_decl: Any, args: dict) -> Any:
        """Execute an agent's Helen function with the given arguments.

        Creates a new scope, binds arguments to parameters, and executes the function body.
        """
        from helen.core.ast import AgentParamNode

        # Create a new scope for the function
        old_env = self.environment
        self.environment = self.environment.enter_scope()

        try:
            # Bind arguments to parameters
            for i, param in enumerate(fn_decl.params):
                param_name = param.name
                if param_name in args:
                    value = args[param_name]
                    self.environment.define(param_name, value)
                elif param.default_value is not None:
                    # Use default value
                    default_val = param.default_value.accept(self)
                    self.environment.define(param_name, default_val)
                else:
                    # Missing required argument
                    raise ValueError(f"Missing required argument: {param_name}")

            # Execute function body
            result = fn_decl.body.accept(self)
            return result
        finally:
            # Restore environment
            self.environment = old_env

    def _build_skill_index(self: Any) -> str:
        """Build the Tier 1 Skill Index for system prompt injection.

        Scans skill directories and formats as <available_skills> XML block.
        Returns empty string if no skills found.

        Caching: uses max mtime across all skill base directories to detect
        changes. Only rebuilds when skills are added/removed/modified.
        """
        # Compute max mtime across all skill base directories
        from helen.runtime.config import get_skill_dirs
        try:
            max_mtime = 0.0
            for base in get_skill_dirs():
                base_str = str(base)
                if os.path.exists(base_str):
                    for root, dirs, files in os.walk(base_str):
                        if "SKILL.md" in files:
                            skill_md = os.path.join(root, "SKILL.md")
                            mtime = os.path.getmtime(skill_md)
                            if mtime > max_mtime:
                                max_mtime = mtime
        except Exception:
            max_mtime = 0.0

        # Return cached index if mtime hasn't changed
        if max_mtime == self._skill_index_mtime and self._skill_index_cache is not None:
            return self._skill_index_cache

        # Rebuild the index
        from helen.runtime import HelenHermesRuntime

        try:
            runtime = HelenHermesRuntime()
            skills = runtime.list_skills()
            if not skills:
                self._skill_index_cache = ""
                self._skill_index_mtime = max_mtime
                return ""

            # Group by category
            by_category: dict[str, list] = {}
            for s in skills:
                by_category.setdefault(s.category or "uncategorized", []).append(s)

            lines = ["<available_skills>"]
            lines.append("Before replying, scan skills below. If relevant,")
            lines.append("use load_skill tool to load full content.")
            lines.append("")

            for category, skill_list in sorted(by_category.items()):
                lines.append(f"  {category}:")
                for s in skill_list:
                    # Truncate long descriptions
                    desc = s.description
                    if len(desc) > 100:
                        desc = desc[:97] + "..."
                    lines.append(f"    - {s.name}: {desc}")

            lines.append("</available_skills>")
            result = "\n".join(lines)
            self._skill_index_cache = result
            self._skill_index_mtime = max_mtime
            return result
        except Exception:
            # If skill listing fails, silently continue without skills
            self._skill_index_cache = ""
            self._skill_index_mtime = max_mtime
            return ""

    def _render_prompt_template(self: Any, template: str) -> str:
        """Render a prompt template by replacing {{var}} with environment values.

        Supports nested attribute access like {{settings.model}}.
        Single-pass rendering: rendered results are not re-rendered.
        Uses precompiled regex (module-level _PROMPT_VAR_RE) to avoid
        re-compilation on every call.
        """

        def replace_var(match):
            var_path = match.group(1).strip()
            parts = var_path.split(".")
            try:
                value = self.environment.lookup(parts[0]) if parts else None
            except NameError:
                return match.group(0)  # Keep original if not found
            for part in parts[1:]:
                if isinstance(value, dict):
                    value = value.get(part)
                else:
                    value = None
                    break
            if value is None:
                return match.group(0)  # Keep original if not found
            return str(value)
        return _PROMPT_VAR_RE.sub(replace_var, template)

    def _get_rendered_agent_prompt(self: Any) -> str | None:
        """Get the current agent's prompt field, rendered with environment variables.

        Returns None if no agent context or no prompt field defined.
        """
        if self._current_agent is None:
            return None
        prompt_def = self._current_agent.prompt
        if prompt_def is None:
            return None
        return self._render_prompt_template(prompt_def.content)

    def _get_context(self: Any) -> str | None:
        """Get the current conversation context for LLM calls.

        Integrates with HistoryManager (HLD 3.12) to build a conversation
        summary from accumulated LLM interaction history. The summary is
        capped at 4096 tokens per HLD 3.6.6 conversation_summary rules.

        Returns:
            Formatted summary string: "[{role}] {content}" per message,
            or None if history is empty.
        """
        if not self._history:
            return None
        return self._history_manager.build_conversation_summary(self._history)

    def _add_to_history(self: Any, role: str, content: str) -> None:
        """Add a message to the conversation history.

        Args:
            role: Message role ("user", "assistant", "system", "tool").
            content: Message content string.
        """
        self._history.append(HistoryMessage(role=role, content=content))

    @property
    def history(self: Any) -> list[HistoryMessage]:
        """Access the conversation history (for testing and external integration)."""
        return list(self._history)

    def clear_history(self: Any) -> None:
        """Clear the conversation history."""
        self._history.clear()
