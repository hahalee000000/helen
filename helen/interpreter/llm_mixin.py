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
import time
from typing import Any

from helen.core.ast import (
    AgentDeclNode,
    LlmActExprNode,
    LlmBranchNode,
    LlmIfStmtNode,
    LiteralNode,
)
from helen.core.errors import ErrorCode
from helen.interpreter.exceptions import HelenRuntimeError, ReturnSentinel
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
    _prompt_builder: Any  # P2: PromptBuilder instance (from interpreter init)

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
        """Execute llm act expression with multimodal support.

        Syntax: llm act <prompt_expr>? [media(...)]* [on_chunk <cb>] [on_complete <cb>]
                [on_media <cb>] [on_generate <cb>]* [provider(<expr>)]

        Without callbacks: synchronous LLM call, returns response text.
        With callbacks: streaming LLM call, calls on_chunk for each chunk,
        on_complete when done, returns full accumulated response text.

        Bare form (``llm act`` with no expression, or ``llm act ""``):
        When inside an agent context, the agent's rendered prompt template
        is used as the user message automatically (HLD 3.6.5).

        Multimodal support (v1.17):
        - media: Evaluate media expressions to MediaPart objects
        - on_media: Custom adapter for provider-specific format
        - on_generate: Register as tools for media generation
        - provider: Hint for default adaptation
        """
        from helen.runtime.media import MediaPart

        # Evaluate the prompt expression
        if node.prompt is not None:
            prompt = node.prompt.accept(self)
            if not isinstance(prompt, str):
                prompt = self._stringify(prompt)
        else:
            prompt = ""

        # Track bare form: prompt is empty (either no expression or empty string)
        # and we're inside an agent context. In this case we'll use the rendered
        # agent prompt as the user message, and must NOT re-render it below.
        is_bare_form = (not prompt) and (self._current_agent is not None)

        # Bare form: if prompt is empty and we're inside an agent,
        # use the rendered agent prompt as the user message
        if is_bare_form:
            rendered = self._get_rendered_agent_prompt()
            if rendered:
                prompt = rendered

        # Evaluate media expressions (v1.17)
        media_parts = []
        for media_expr in node.media:
            media_val = media_expr.accept(self)
            if isinstance(media_val, MediaPart):
                media_parts.append(media_val)
            elif media_val is not None:
                self.errors.error(
                    ErrorCode.SEMANTIC_TYPE_ERROR,
                    f"media() must return MediaPart, got {type(media_val).__name__}",
                    media_expr.span if hasattr(media_expr, 'span') else None,
                )

        # Extract agent settings if inside an agent context
        model = self._get_agent_setting("model")
        temperature = float(self._get_agent_setting("temperature", 1.0))
        max_turns = int(self._get_agent_setting("max-turns", 1))

        # Phase 7: Apply context config if agent has one
        if self._current_agent is not None and hasattr(self._current_agent, 'context_config'):
            ctx_config = self._current_agent.context_config
            if ctx_config is not None and hasattr(self, '_agent_context') and self._agent_context is not None:
                # Update AgentContextManager with agent-specific settings
                self._agent_context.compression_strategy = ctx_config.compression
                self._agent_context.working_memory_enabled = ctx_config.working_memory
                self._agent_context.cache_aware_enabled = ctx_config.cache_aware
                if ctx_config.working_memory_tokens > 0:
                    self._agent_context.working_memory.max_tokens = ctx_config.working_memory_tokens

        # P2: Update history manager's model for model-aware context window
        if model:
            self._history_manager.set_model(model)

        # Evaluate provider expression (v1.17) - do this first, needed for generate tools
        provider_hint = None
        if node.provider is not None:
            provider_val = node.provider.accept(self)
            if isinstance(provider_val, str):
                provider_hint = provider_val

        # Build tools list: always include load_skill + agent-declared tools
        tools = self._build_tools_list()

        # Register on_generate callbacks as tools (v1.17)
        generate_tools = []
        for gen_expr in node.on_generate:
            gen_fn = gen_expr.accept(self)
            if callable(gen_fn):
                generate_tools.append(gen_fn)
            else:
                self.errors.error(
                    ErrorCode.SEMANTIC_TYPE_ERROR,
                    f"on_generate callback must be callable, got {type(gen_fn).__name__}",
                    gen_expr.span if hasattr(gen_expr, 'span') else None,
                )

        # Register generate tools if any
        generate_tool_defs = []
        if generate_tools:
            generate_tool_defs = self._build_generate_tools(generate_tools, provider_hint)
            tools.extend(generate_tool_defs)

        # Store generate tools for dispatch (v1.17)
        # Save previous value to handle recursive llm act calls
        prev_generate_tools = getattr(self, '_current_generate_tools', None)
        self._current_generate_tools = generate_tool_defs

        # When tools are available, ensure at least 3 turns (tool call + tool result + response)
        if tools and max_turns < 3:
            max_turns = 3

        # Evaluate on_media callback (v1.17)
        on_media_fn = None
        if node.on_media is not None:
            on_media_fn = node.on_media.accept(self)
            if not callable(on_media_fn):
                self.errors.error(
                    ErrorCode.SEMANTIC_TYPE_ERROR,
                    f"on_media callback must be callable, got {type(on_media_fn).__name__}",
                    node.on_media.span if hasattr(node.on_media, 'span') else None,
                )
                on_media_fn = None

        # P2: System/User prompt role separation
        # System prompt: framework + helen_conventions + description + skill_index
        # User prompt: rendered agent prompt (task description) + llm act expression (query)
        system_prompt_parts = []

        # 1. Framework instructions (P0+P1: tool use, skills, parallel, completion)
        framework = self._build_framework_instructions()
        if framework:
            system_prompt_parts.append(framework)

        # 2. Helen language conventions (always included)
        helen_conventions = self._build_helen_conventions()
        if helen_conventions:
            system_prompt_parts.append(helen_conventions)

        # 3. Agent description (role definition)
        description = self._get_agent_setting("description")
        if description:
            system_prompt_parts.append(description)

        # 4. Skill Index (Tier 1)
        skill_index = self._build_skill_index()
        if skill_index:
            system_prompt_parts.append(skill_index)

        system_prompt = "\n\n".join(system_prompt_parts) if system_prompt_parts else None

        # User prompt construction:
        # - Bare form (no prompt expression OR empty prompt): `prompt` already contains
        #   the rendered agent prompt from above, so use it directly.
        # - Non-bare form (user provided a prompt expression): `prompt` contains that string,
        #   and we prepend the agent's rendered prompt template (if any) as task description.
        user_prompt_parts = []

        # Only render agent prompt template when NOT in bare form
        # (bare form already has the rendered template in `prompt`)
        if not is_bare_form and node.prompt is not None:
            rendered_agent_prompt = self._get_rendered_agent_prompt()
            if rendered_agent_prompt:
                user_prompt_parts.append(rendered_agent_prompt)

        # The llm act expression is the actual query
        if prompt:
            user_prompt_parts.append(prompt)

        user_prompt = "\n\n".join(user_prompt_parts) if user_prompt_parts else prompt

        # Build user message with multimodal content if media is present (v1.17)
        user_message = self._build_user_message(user_prompt, media_parts, on_media_fn, provider_hint)

        # Record user message to history (v1.17: store multimodal content in TranscriptStore SSOT)
        # When media is present, store the full multimodal content (list[dict])
        # Otherwise store plain text. This ensures session restore preserves media.
        if media_parts:
            self._add_to_history("user", user_message["content"])
        else:
            self._add_to_history("user", user_prompt)

        # P0: Prepare history for LLM call (trim to fit context window)
        history_for_llm = self._prepare_history_for_llm(system_prompt, user_prompt)

        # If we have multimodal content, modify the last user message in history
        if media_parts and history_for_llm:
            # Replace the last user message with multimodal content
            for i in range(len(history_for_llm) - 1, -1, -1):
                if history_for_llm[i].get("role") == "user":
                    history_for_llm[i] = user_message
                    break

        # Determine streaming vs synchronous path
        has_streaming = node.on_chunk is not None or node.on_complete is not None

        try:
            if has_streaming:
                return self._visit_llm_act_streaming(node, user_prompt, model, temperature, max_turns,
                                                       tools, system_prompt, history_for_llm)
            else:
                return self._visit_llm_act_sync(node, user_prompt, model, temperature, max_turns,
                                                tools, system_prompt, history_for_llm)
        finally:
            # Restore previous generate tools to handle recursive llm act calls (v1.17)
            if prev_generate_tools is not None:
                self._current_generate_tools = prev_generate_tools
            elif hasattr(self, '_current_generate_tools'):
                delattr(self, '_current_generate_tools')

    def _log_llm_audit(self: Any, call_type: str, prompt: str, audit_start: float,
                       agent_name: str | None, model: str,
                       response: str | None = None, error: str | None = None,
                       tokens_in: int = 0, tokens_out: int = 0,
                       tool_calls: list | None = None) -> None:
        """Build and log an LLMAuditEntry (deduplicates 5 identical audit sites)."""
        actual_model = model or getattr(self.llm_runtime, 'default_model', None) or 'default'
        duration_ms = (time.time() - audit_start) * 1000
        entry = LLMAuditEntry(
            timestamp=audit_start,
            call_type=call_type,
            agent_name=agent_name,
            model=actual_model,
            prompt=prompt,
            response=response,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            duration_ms=duration_ms,
            error=error,
            tool_calls=tool_calls,
        )
        self.observability.llm_audit.log(entry)

    def _visit_llm_act_sync(self: Any, node: LlmActExprNode, prompt: str,
                            model: str, temperature: float, max_turns: int,
                            tools: list, system_prompt: str, history_for_llm: list) -> object:
        """Synchronous llm act: call act() and return response text."""
        audit_start = time.time()
        agent_name = self._current_agent.name if self._current_agent else None

        try:
            # Create custom dispatch function that can execute Helen functions
            dispatch_fn = self._create_dispatch_fn()

            # Extract on_tool_end callback if provided (v1.21)
            on_tool_end_fn = None
            if node.on_tool_end is not None:
                on_tool_end_fn = node.on_tool_end.accept(self)
                if not callable(on_tool_end_fn):
                    self.errors.error(
                        ErrorCode.SEMANTIC_TYPE_ERROR,
                        f"on_tool_end callback must be callable, got {type(on_tool_end_fn).__name__}",
                        node.span,
                    )
                    return None

            # Create hint collector to persist hints to TranscriptStore (v1.21.1)
            def hint_collector(hint_msg):
                self._add_to_history(hint_msg["role"], hint_msg["content"])

            response = self.llm_runtime.act(
                prompt, tools=tools, model=model,
                temperature=temperature, max_turns=max_turns,
                system_prompt=system_prompt,
                history=history_for_llm,
                dispatch_fn=dispatch_fn,
                on_tool_end_fn=on_tool_end_fn,
                hint_collector_fn=hint_collector,
            )

            # Log to audit trail
            self._log_llm_audit(
                "act", prompt, audit_start, agent_name, model,
                response=response.text if response else None,
                tokens_in=getattr(response, 'usage', {}).get('prompt_tokens', 0) if response else 0,
                tokens_out=getattr(response, 'usage', {}).get('completion_tokens', 0) if response else 0,
            )

            # P1: Record tool calls + final response to history
            if response:
                self._record_llm_response_to_history(response)
            return response.text if response else None
        except HelenRuntimeError as e:
            self._log_llm_audit("act", prompt, audit_start, agent_name, model, error=str(e))
            return None
        except RuntimeError as e:
            # Python RuntimeError from LLM runtime (e.g. API errors) —
            # wrap in HelenRuntimeError so it propagates to the user
            self._log_llm_audit("act", prompt, audit_start, agent_name, model, error=str(e))
            raise HelenRuntimeError(str(e), node.span) from e

    def _visit_llm_act_streaming(self: Any, node: LlmActExprNode, prompt: str,
                                 model: str, temperature: float, max_turns: int,
                                 tools: list, system_prompt: str, history_for_llm: list) -> object:
        """Streaming llm act: call act_stream() and dispatch chunks via callbacks."""
        # Check if LLM runtime supports streaming
        if not hasattr(self.llm_runtime, 'act_stream'):
            self.errors.error(
                ErrorCode.RUNTIME_ERROR,
                "LLM runtime does not support streaming. Using fallback.",
                node.span,
            )
            # Fallback to non-streaming (v1.17: pass tools for on_generate support)
            # Extract on_tool_end_fn for fallback (v1.21)
            fallback_on_tool_end_fn = None
            if node.on_tool_end is not None:
                fallback_on_tool_end_fn = node.on_tool_end.accept(self)
                if not callable(fallback_on_tool_end_fn):
                    fallback_on_tool_end_fn = None

            # Create hint collector for fallback path (v1.21.1)
            def fallback_hint_collector(hint_msg):
                self._add_to_history(hint_msg["role"], hint_msg["content"])

            response = self.llm_runtime.act(
                prompt, tools=tools, model=model, temperature=temperature,
                system_prompt=system_prompt,
                history=history_for_llm,
                dispatch_fn=self._create_dispatch_fn(),
                on_tool_end_fn=fallback_on_tool_end_fn,
                hint_collector_fn=fallback_hint_collector,
            )
            if response and response.text:
                if node.on_chunk is not None:
                    on_chunk_fn = node.on_chunk.accept(self)
                    if callable(on_chunk_fn):
                        on_chunk_fn(response.text)
                self._add_to_history("assistant", response.text)
            return response.text if response else None

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

        # Evaluate on_tool_end callback if provided (v1.21)
        on_tool_end_fn = None
        if node.on_tool_end is not None:
            on_tool_end_fn = node.on_tool_end.accept(self)
            if not callable(on_tool_end_fn):
                self.errors.error(
                    ErrorCode.SEMANTIC_TYPE_ERROR,
                    f"on_tool_end callback must be callable, got {type(on_tool_end_fn).__name__}",
                    node.span,
                )
                return None

        # Create hint collector to persist hints to TranscriptStore (v1.21.1)
        def hint_collector(hint_msg):
            self._add_to_history(hint_msg["role"], hint_msg["content"])

        # Audit log entry
        audit_start = time.time()
        agent_name = self._current_agent.name if self._current_agent else None

        try:
            # Create custom dispatch function that can execute Helen functions
            dispatch_fn = self._create_dispatch_fn()

            # Stream response with full tool-calling loop
            full_response = []
            tool_calls_log = []
            stream_usage = {}  # accumulated token usage across turns
            interrupted = False

            # Phase 3: Register streaming call for cancel/KeyboardInterrupt support
            stream_handle = self._register_streaming_call()

            # Merge cancel signals: stream_handle + external (spawn scenario)
            external_cancel = getattr(self, '_agent_cancel_event', None)

            # Phase 2: Pass cancel_event to act_stream
            try:
                try:
                    stream_iter = self.llm_runtime.act_stream(
                        prompt, model=model, temperature=temperature,
                        system_prompt=system_prompt, tools=tools,
                        max_turns=max_turns,
                        history=history_for_llm,
                        dispatch_fn=dispatch_fn,
                        cancel_event=stream_handle.cancelled,
                        on_tool_end_fn=on_tool_end_fn,
                        hint_collector_fn=hint_collector,
                    )
                except TypeError:
                    # Fallback: custom LLMRuntime doesn't support cancel_event
                    stream_iter = self.llm_runtime.act_stream(
                        prompt, model=model, temperature=temperature,
                        system_prompt=system_prompt, tools=tools,
                        max_turns=max_turns,
                        history=history_for_llm,
                        dispatch_fn=dispatch_fn,
                        on_tool_end_fn=on_tool_end_fn,
                        hint_collector_fn=hint_collector,
                    )

                for event in stream_iter:
                    # Check cancel signals
                    if stream_handle.cancelled.is_set():
                        interrupted = True
                        break
                    if external_cancel is not None and external_cancel.is_set():
                        stream_handle.cancelled.set()
                        interrupted = True
                        break

                    event_type = event.get("type", "content")

                    if event_type == "content":
                        content = event.get("content", "")
                        if content:
                            full_response.append(content)
                            if on_chunk_fn is not None:
                                # Phase 1: Check on_chunk return value
                                chunk_result = on_chunk_fn(content)
                                if chunk_result is False:
                                    interrupted = True
                                    break

                    elif event_type == "tool_call":
                        fn_name = event.get("name", "")
                        fn_args = event.get("args", {})
                        tool_calls_log.append({"name": fn_name, "args": fn_args})
                        if on_chunk_fn is not None:
                            args_str = ", ".join(f"{k}={v!r}" for k, v in fn_args.items())
                            progress = f"\n🔧 Calling {fn_name}({args_str})...\n"
                            # Phase 1: Check on_chunk return value
                            chunk_result = on_chunk_fn(progress)
                            if chunk_result is False:
                                interrupted = True
                                break

                    elif event_type == "tool_result":
                        fn_name = event.get("name", "")
                        result = event.get("result", "")
                        if on_chunk_fn is not None:
                            display_result = result if len(result) <= 200 else result[:200] + "..."
                            result_msg = f"✅ {fn_name} returned: {display_result}\n"
                            # Phase 1: Check on_chunk return value
                            chunk_result = on_chunk_fn(result_msg)
                            if chunk_result is False:
                                interrupted = True
                                break

                    elif event_type == "usage":
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

            except KeyboardInterrupt:
                # Ctrl+C during streaming — captured here, REPL won't see it
                interrupted = True
                stream_handle.cancelled.set()

            finally:
                stream_handle.done.set()
                self._unregister_streaming_call(stream_handle.call_id)

            # on_complete only called when NOT interrupted
            if not interrupted and on_complete_fn is not None:
                on_complete_fn()

            # Record tool calls + final response to history (including partial)
            full_text = "".join(full_response)
            if full_text or tool_calls_log:
                class _StreamResponse:
                    pass
                stream_resp = _StreamResponse()
                stream_resp.text = full_text
                stream_resp.tool_calls = tool_calls_log
                self._record_llm_response_to_history(stream_resp)

            # Log to audit trail
            audit_response = full_text + (" [interrupted]" if interrupted else "")
            self._log_llm_audit(
                "act_stream", prompt, audit_start, agent_name, model,
                response=audit_response,
                tokens_in=stream_usage.get("prompt_tokens", 0),
                tokens_out=stream_usage.get("completion_tokens", 0),
                tool_calls=tool_calls_log,
            )

            return full_text
        except Exception as e:
            self._log_llm_audit("act_stream", prompt, audit_start, agent_name, model, error=str(e))

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

        Two-layer authorization model (HLD):
        - functions { } block declares the agent's full capability set
          (callable from main {} by Helen code, but NOT auto-exposed to LLM)
        - tools = [...] is the LLM allowlist — only names listed here are
          visible to the LLM for autonomous invocation. Each name can refer
          to either a Helen function (from functions {}) or a Python tool
          (from the runtime registry).
        - tools = CONST_NAME references a module-level const that holds a list.
        - load_skill is always included for Tier 2 skill disclosure (HLD 3.6.5)
        - If tools is not declared, the LLM has NO tools (except load_skill)

        v1.12: @sandbox (L3) agents have NO tools at all — not even load_skill.
        """
        from helen.core.ast import VariableNode
        from helen.runtime.tools import get_tool_schemas

        tools: list[dict[str, Any]] = []
        tool_names: set[str] = set()

        # v1.12: @sandbox (L3) — force empty tools, except load_skill + list_skill_references
        if self._current_agent is not None:
            isolation = getattr(self._current_agent, 'isolation_level', 'standard')
            if isolation == "sandbox":
                # Sandbox agents get skill tools for skill access
                tools.extend(get_tool_schemas(["load_skill", "list_skill_references"]))
                return tools

        # 1. Read declared tools allowlist
        declared_tools: list[str] | None = None
        if self._current_agent is not None:
            for decl in self._current_agent.declarations:
                if decl.tools is not None:
                    tools_node = decl.tools
                    if isinstance(tools_node, LiteralNode) and isinstance(tools_node.value, list):
                        # tools = ["web_search", "read_file", ...]
                        declared_tools = tools_node.value
                    elif isinstance(tools_node, VariableNode):
                        # tools = CONST_NAME — look up the const value
                        try:
                            const_value = self.environment.lookup(tools_node.name)
                            if isinstance(const_value, list):
                                declared_tools = [str(x) for x in const_value]
                            else:
                                declared_tools = []
                        except NameError:
                            declared_tools = []
                    break

        # 2. If no tools declared → LLM gets nothing (skill tools added below)
        if declared_tools is None:
            tools.extend(get_tool_schemas(["load_skill", "list_skill_references"]))
            return tools

        # 3. For each name in the allowlist, resolve to Helen fn or Python tool
        for name in declared_tools:
            # 3a. Try Helen function in functions {} block
            fn_schema = None
            if self._current_agent is not None and self._current_agent.functions:
                for fn_decl in self._current_agent.functions:
                    if fn_decl.name == name:
                        fn_schema = self._function_to_tool_schema(fn_decl)
                        break

            if fn_schema is not None:
                if name not in tool_names:
                    tools.append(fn_schema)
                    tool_names.add(name)
                continue

            # 3b. Try Python tool in runtime registry
            py_schemas = get_tool_schemas([name])
            for schema in py_schemas:
                if schema["function"]["name"] not in tool_names:
                    tools.append(schema)
                    tool_names.add(schema["function"]["name"])

        # 4. Always include skill tools for Tier 2/3 skill disclosure (HLD 3.6.5)
        default_skill_tools = ["load_skill", "list_skill_references"]
        missing = [t for t in default_skill_tools if t not in tool_names]
        if missing:
            tools.extend(get_tool_schemas(missing))

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
                    # Note: Helen doesn't support generic types yet (e.g., list[int]),
                    # so we can't infer item types. Leaving `items` unspecified means
                    # the array can contain any type, which is valid JSON Schema.
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
        1. First checks if the name matches a generate_media tool (v1.17)
        2. Then checks if the name matches an agent's Helen function
        3. If yes, executes the Helen function and returns the result as JSON
        4. If no, falls back to the default Python tool dispatch
        """
        from helen.runtime.tools import dispatch_tool as default_dispatch
        from helen.runtime.media import MediaPart
        import json

        # Capture current agent context
        agent = self._current_agent
        interpreter = self

        # Capture generate tools from current llm act node (v1.17)
        generate_tools_map = {}
        if hasattr(self, '_current_generate_tools') and self._current_generate_tools:
            for tool in self._current_generate_tools:
                if "_helen_generate_fn" in tool:
                    tool_name = tool["function"]["name"]
                    generate_tools_map[tool_name] = {
                        "fn": tool["_helen_generate_fn"],
                        "provider_hint": tool.get("_helen_provider_hint"),
                    }

        def dispatch(name: str, args: dict) -> str:
            # Check if this is a generate_media tool (v1.17)
            if name in generate_tools_map:
                gen_info = generate_tools_map[name]
                gen_fn = gen_info["fn"]
                try:
                    # Call the generate callback with params
                    result = gen_fn(args)

                    # Handle MediaPart result
                    if isinstance(result, MediaPart):
                        # Save media to file and return path info
                        path = interpreter._save_generate_media(result, args.get("prompt", ""))
                        return json.dumps({
                            "status": "success",
                            "message": f"媒体已保存到: {path}",
                            "path": path,
                            "media_type": result.media_type,
                            "mime": result.mime,
                        }, ensure_ascii=False)
                    elif isinstance(result, str):
                        return result
                    else:
                        return json.dumps(result, ensure_ascii=False, default=str)
                except Exception as e:
                    return json.dumps({
                        "error": f"Generate tool '{name}' failed: {e}"
                    }, ensure_ascii=False)

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
                            return json.dumps({"error": f"Helen function '{name}' failed: {e}"}, ensure_ascii=False)

            # Fall back to Python tool dispatch
            return default_dispatch(name, args)

        return dispatch

    def _save_generate_media(self: Any, media: Any, prompt: str) -> str:
        """Save generated media to a file.

        Args:
            media: MediaPart object to save
            prompt: The generation prompt (for naming)

        Returns:
            Path where the media was saved
        """
        import os
        import base64
        import hashlib
        from pathlib import Path

        from helen.runtime.media import MediaPart

        if not isinstance(media, MediaPart):
            return str(media)

        # Determine output directory
        output_dir = Path.home() / ".helen" / "generated_media"
        output_dir.mkdir(parents=True, exist_ok=True)

        # Generate filename from prompt hash + media type
        prompt_hash = hashlib.md5(prompt.encode()).hexdigest()[:8]
        ext_map = {
            "image/png": "png",
            "image/jpeg": "jpg",
            "image/gif": "gif",
            "image/webp": "webp",
            "video/mp4": "mp4",
            "audio/mp3": "mp3",
            "audio/wav": "wav",
        }
        ext = ext_map.get(media.mime, media.media_type)
        filename = f"{media.media_type}_{prompt_hash}.{ext}"
        output_path = output_dir / filename

        # Save based on source type
        if media.source == "url":
            # Download from URL
            try:
                import urllib.request
                urllib.request.urlretrieve(media.content, output_path)
            except Exception:
                # If download fails, just save the URL as text
                output_path.write_text(media.content)
        elif media.source == "base64":
            # Decode and save
            data = base64.b64decode(media.content)
            output_path.write_bytes(data)
        elif media.source == "file":
            # Copy file
            import shutil
            if os.path.exists(media.content):
                shutil.copy2(media.content, output_path)
            else:
                output_path.write_text(media.content)

        return str(output_path)

    def _execute_agent_function(self: Any, fn_decl: Any, args: dict) -> Any:
        """Execute an agent's Helen function with the given arguments.

        Creates a new scope, binds arguments to parameters, and executes the function body.
        """

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
            if isinstance(result, ReturnSentinel):
                return result.value
            return result
        finally:
            # Restore environment
            self.environment = old_env

    def _build_framework_instructions(self: Any) -> str:
        """Build framework-level behavioral instructions (P0+P1).

        P2: Delegates to PromptBuilder for unified implementation.
        Provides foundational behavioral guidance for all agents:
        - P0: Tool use enforcement (MUST use tools, not describe)
        - P0: Skill loading enforcement (MUST load relevant skills)
        - P1: Parallel tool calls (batch independent calls)
        - P1: Completion criteria (working artifact, not description)
        """
        if hasattr(self, '_prompt_builder') and self._prompt_builder is not None:
            return self._prompt_builder._build_framework_instructions()

        # Fallback: return empty string (should not reach here normally)
        return ""

    def _build_helen_conventions(self: Any) -> str:
        """Build Helen language conventions section for system prompt.

        P2: Delegates to PromptBuilder for unified implementation.
        Provides foundational guidance for generating correct Helen code.
        """
        if hasattr(self, '_prompt_builder') and self._prompt_builder is not None:
            return self._prompt_builder._build_helen_conventions()

        # Fallback: return empty string (should not reach here normally)
        return ""

    def _build_skill_index(self: Any) -> str:
        """Build the Tier 1 Skill Index for system prompt injection.

        P2: Delegates to PromptBuilder for unified implementation.
        Uses mtime-based caching to avoid rebuilding on every LLM call.
        """
        if hasattr(self, '_prompt_builder') and self._prompt_builder is not None:
            return self._prompt_builder.build_skill_index()

        # Fallback: legacy inline implementation (should not reach here normally)
        return self._build_skill_index_legacy()

    def _build_skill_index_legacy(self: Any) -> str:
        """Legacy skill index builder (fallback if PromptBuilder is not available).

        This is kept for backward compatibility and should be removed after
        the PromptBuilder migration is fully validated.
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
        from helen.runtime import HelenRuntime

        try:
            runtime = HelenRuntime()
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
            lines.append("Before replying, scan skills below. If a skill matches or is")
            lines.append("even partially relevant to your task, you MUST load it with")
            lines.append("load_skill and follow its instructions. Err on the side of loading.")
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

        P2: Delegates to PromptBuilder for unified implementation.
        Supports nested attribute access like {{settings.model}}.
        Single-pass rendering: rendered results are not re-rendered.
        """
        if hasattr(self, '_prompt_builder') and self._prompt_builder is not None:
            return self._prompt_builder.render(template, self.environment)

        # Fallback: legacy inline implementation
        return self._render_prompt_template_legacy(template)

    def _render_prompt_template_legacy(self: Any, template: str) -> str:
        """Legacy template renderer (fallback if PromptBuilder is not available).

        Kept for backward compatibility.
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

    def _add_to_history(self: Any, role: str, content: str | list[dict]) -> None:
        """Add a message to the conversation history.

        Phase 2 SSOT: When TranscriptStore is enabled, write ONLY to it.
                      _history is a read-only derived view (property).
                      When disabled, write to _interpreter_history (fallback).

        P3: Sets model on message for accurate token counting.
        Phase 7: Update working memory from message content.
        v1.17: content can be str (plain text) or list[dict] (multimodal content parts).
        v1.22: Fills agent_name / invocation_id / parent_invocation_id for
               invocation tree tracking (per-agent context isolation).
        """
        agent_ctx = getattr(self, '_agent_context', None)

        # P3: Set model on message for tiktoken encoding selection
        model = getattr(self._history_manager, '_model', None)

        # v1.22: Invocation tree fields
        current_agent = getattr(self, '_current_agent', None)
        agent_name = current_agent.name if current_agent is not None else None
        invocation_id = getattr(self, '_current_invocation_id', '') or ''
        invocation_stack = getattr(self, '_invocation_stack', [])
        parent_invocation_id = invocation_stack[-1] if invocation_stack else ''

        msg = HistoryMessage(
            role=role,
            content=content,
            _model=model,
            agent_name=agent_name,
            invocation_id=invocation_id,
            parent_invocation_id=parent_invocation_id,
        )

        # Phase 2 SSOT: Write to TranscriptStore when enabled (NO dual-write)
        if agent_ctx is not None and agent_ctx.transcript_store is not None:
            # Write ONLY to TranscriptStore (SSOT)
            agent_ctx.transcript_store.append(msg)
        else:
            # Fallback: write to _interpreter_history when TranscriptStore disabled
            self._interpreter_history.append(msg)

        # Phase 7: Update working memory from message
        # For multimodal content, extract text portion for working memory
        from helen.runtime.history import _message_text
        text_content = _message_text(content)
        if agent_ctx is not None:
            agent_ctx.update_from_message(text_content, role)

        # Phase 2 SSOT: NO destructive in-place replacement.
        # Compression is handled by AgentContextManager.prepare_context() which
        # records BoundaryMarkers in TranscriptStore.
        # When TranscriptStore is disabled, use old enforce_limit logic on fallback storage.
        if agent_ctx is None or agent_ctx.transcript_store is None:
            if agent_ctx is None or not agent_ctx.compression_enabled:
                trimmed = self._history_manager.enforce_limit(self._interpreter_history)
                if len(trimmed) < len(self._interpreter_history):
                    self._interpreter_history[:] = trimmed

    def _record_llm_response_to_history(self: Any, response: Any) -> None:
        """Record LLM response (with tool calls) to conversation history.

        P1: Makes tool calling context visible to subsequent llm act calls.
        Records a structured summary of tool calls followed by the final response,
        so that future LLM calls can reference what tools were called and what
        they returned, preventing redundant tool executions.

        Phase 7: Update working memory from tool calls.

        Args:
            response: LLMResponse-like object with .text and .tool_calls attributes.
        """
        tool_calls = getattr(response, 'tool_calls', None) or []
        text = getattr(response, 'text', None) or ""

        if tool_calls:
            # Build a compact summary of tool calls for history
            parts = []
            for tc in tool_calls:
                name = tc.get("name", "unknown")
                args_raw = tc.get("args", "{}")
                result = tc.get("result", "")

                # Phase 7: Update working memory from tool call
                if hasattr(self, '_agent_context') and self._agent_context is not None:
                    exit_code = tc.get("exit_code")
                    self._agent_context.update_from_tool_call(name, args_raw, result, exit_code)

                # Parse args for compact display
                try:
                    if isinstance(args_raw, str):
                        import json as _json
                        args = _json.loads(args_raw)
                    else:
                        args = args_raw
                except Exception:
                    args = {}
                # Compact args: show key values, truncate long strings
                args_parts = []
                for k, v in (args.items() if isinstance(args, dict) else []):
                    v_str = str(v)
                    if len(v_str) > 100:
                        v_str = v_str[:97] + "..."
                    args_parts.append(f"{k}={v_str!r}")
                args_display = ", ".join(args_parts)

                # Truncate result for display
                result_display = result
                if len(result_display) > 200:
                    result_display = result_display[:197] + "..."

                parts.append(f"[{name}({args_display}) → {result_display}]")

            tool_summary = "Tool calls: " + " | ".join(parts)
            self._add_to_history("assistant", tool_summary)

        # Record the final text response
        if text:
            self._add_to_history("assistant", text)

    def _prepare_history_for_llm(
        self: Any,
        system_prompt: str | None,
        current_prompt: str,
    ) -> list[dict[str, Any]] | None:
        """Prepare conversation history for an LLM API call.

        Phase 7: Uses AgentContextManager to build three-channel context
        with working memory and graduated compression.

        Phase 3 SSOT: When TranscriptStore is enabled, uses read_view() to get
        the current effective message list (with compression applied via BoundaryMarkers).

        Uses HistoryManager to calculate budget, trim to fit context window,
        and convert to OpenAI messages format.

        Args:
            system_prompt: System prompt text (for budget calculation).
            current_prompt: Current instruction text (for budget calculation).

        Returns:
            List of message dicts for API, or None if history is empty.
        """
        # v1.23 fix: Always use self._history which applies invocation_id
        # filtering for per-agent context isolation (v1.22 design).
        #
        # Previously, when TranscriptStore was enabled (the default), this
        # method called transcript_store.read_view() directly, which returned
        # ALL messages across ALL invocations — breaking the per-agent
        # isolation that interpreter.py:_history property provides.
        #
        # self._history:
        #   - When TranscriptStore enabled: read_view() + invocation_id filter
        #   - When TranscriptStore disabled: _interpreter_history + filter
        # Either way, the result is correctly scoped to the current invocation.
        history_for_compression = self._history

        if not history_for_compression:
            return None

        # Phase 7: Use AgentContextManager if available
        agent_ctx = getattr(self, '_agent_context', None)
        if agent_ctx is not None:
            max_tokens = self._history_manager.MAX_TOKENS
            return agent_ctx.prepare_context(
                system_prompt=system_prompt,
                history=history_for_compression,
                max_tokens=max_tokens,
                current_prompt=current_prompt,
            )

        # Fallback: Use HistoryManager (Phase 1-6 behavior)
        return self._history_manager.prepare_for_llm(
            history_for_compression, system_prompt, current_prompt
        )

    # ------------------------------------------------------------------
    # Multimodal Support (v1.17)
    # ------------------------------------------------------------------

    def _build_user_message(self: Any, text: str, media_parts: list,
                            on_media_fn: callable | None, provider_hint: str | None) -> dict:
        """Build a user message with optional multimodal content.

        Args:
            text: Text content of the message
            media_parts: List of MediaPart objects
            on_media_fn: Optional custom adapter function
            provider_hint: Optional provider hint for default adaptation

        Returns:
            Message dict with 'role' and 'content' fields.
            content is either str (text only) or list[dict] (with media).
        """
        if not media_parts:
            return {"role": "user", "content": text}

        # With media: build content parts array
        if on_media_fn is not None:
            # User-provided adapter
            try:
                content_parts = on_media_fn(media_parts, provider_hint or "default")
            except Exception as e:
                # Fall back to default adapter on error
                self.errors.error(
                    ErrorCode.RUNTIME_ERROR,
                    f"on_media callback error: {e}. Using default adapter.",
                    None,
                )
                content_parts = self._default_media_adapter(media_parts, provider_hint)
        else:
            # Default OpenAI-compatible adapter
            content_parts = self._default_media_adapter(media_parts, provider_hint)

        # Prepend text content
        full_content = [{"type": "text", "text": text}] + content_parts
        return {"role": "user", "content": full_content}

    def _default_media_adapter(self: Any, media_parts: list, provider_hint: str | None) -> list[dict]:
        """Default media adapter: OpenAI-compatible format.

        Delegates to :func:`helen.stdlib.media._to_openai_parts` so the
        conversion logic is shared with the user-facing ``to_openai_parts``
        stdlib function.

        Args:
            media_parts: List of MediaPart objects
            provider_hint: Optional provider hint (currently unused)

        Returns:
            List of content part dicts
        """
        from helen.stdlib.media import _to_openai_parts
        return _to_openai_parts(media_parts)

    def _build_generate_tools(self: Any, generate_fns: list, provider_hint: str | None) -> list[dict]:
        """Build tool definitions for on_generate callbacks.

        Each on_generate callback becomes a 'generate_media' tool.
        Multiple callbacks create multiple tools with different internal handlers.

        Args:
            generate_fns: List of callable generate functions
            provider_hint: Optional provider hint

        Returns:
            List of tool definition dicts
        """
        tools = []
        for i, gen_fn in enumerate(generate_fns):
            # Create unique tool name for each generate callback
            tool_name = "generate_media" if len(generate_fns) == 1 else f"generate_media_{i+1}"

            tool_def = {
                "type": "function",
                "function": {
                    "name": tool_name,
                    "description": "根据描述生成图片或视频。用户会在 prompt 中指定保存路径和格式要求。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "prompt": {
                                "type": "string",
                                "description": "生成内容的详细描述"
                            },
                            "size": {
                                "type": "string",
                                "description": "尺寸，如 1024x1024"
                            },
                            "duration": {
                                "type": "integer",
                                "description": "视频时长（秒）"
                            },
                            "format": {
                                "type": "string",
                                "description": "输出格式，如 png, jpg, mp4"
                            }
                        },
                        "required": ["prompt"]
                    }
                },
                # Internal: store the callback for execution
                "_helen_generate_fn": gen_fn,
                "_helen_provider_hint": provider_hint,
            }
            tools.append(tool_def)
        return tools

    @property
    def history(self: Any) -> list[HistoryMessage]:
        """Access the conversation history (for testing and external integration)."""
        return list(self._history)

    def clear_history(self: Any) -> None:
        """Clear the conversation history.

        Phase 2 SSOT: Clears the underlying storage (_interpreter_history or TranscriptStore).
        """
        agent_ctx = getattr(self, '_agent_context', None)
        if agent_ctx is not None and agent_ctx.transcript_store is not None:
            # Clear TranscriptStore
            agent_ctx.transcript_store.transcript.clear()
            agent_ctx.transcript_store._uuid_index.clear()
            agent_ctx.transcript_store._dirty = True
        else:
            # Clear fallback storage
            self._interpreter_history.clear()

    # ------------------------------------------------------------------
    # Context Statistics (for REPL display)
    # ------------------------------------------------------------------

    def format_context_stats(self: Any, system_prompt: str | None = None) -> str:
        """Get formatted context usage string for display.

        P4: Returns human-readable context stats for REPL/debug output.
        """
        stats = self._history_manager.get_usage_stats(self._history, system_prompt)
        return self._history_manager.format_usage_stats(stats)
