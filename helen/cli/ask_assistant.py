"""REPL assistant (:ask command) - L1/L2/L3 implementation.

Design:
- L1: Direct LLM call with a system prompt assembled from prompt_builder
  + REPL context (definitions / last error / recent output / cwd).
  No dependency on helen_assistant.helen.
- L2: Four REPL-state tools (repl_definitions / repl_last_error /
  repl_history / repl_read_file) injected into the assistant's tool list
  via a custom dispatch_fn. The LLM can proactively query REPL state.
- L3: AssistantSession with its own TranscriptStore for multi-turn chat.
  `:ask` without a question enters a sub-REPL chat mode; `:exit` or
  Ctrl+C returns to the main REPL. Sessions persist via session_id and
  can be resumed with `:ask --resume <sid>`.
"""

from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from helen.runtime.prompt_builder import PromptBuilder


# ---------------------------------------------------------------------------
# REPL state capture (L1 / L2)
# ---------------------------------------------------------------------------

@dataclass
class ReplState:
    """Captured REPL state passed into the assistant prompt.

    The REPL module updates this after every input turn so the assistant
    sees fresh data on each :ask invocation.
    """

    # Bounded buffer of recent REPL output lines (most-recent-last).
    output_buffer: list[str] = field(default_factory=list)
    # Maximum number of output lines to retain.
    output_buffer_max: int = 50
    # Persistent "last error" - survives errors.reset() between REPL turns.
    last_error_text: str | None = None

    def record_output(self, text: str) -> None:
        """Append a REPL output line, evicting oldest if over capacity."""
        for line in text.splitlines():
            self.output_buffer.append(line)
        if len(self.output_buffer) > self.output_buffer_max:
            del self.output_buffer[:len(self.output_buffer) - self.output_buffer_max]

    def record_error(self, text: str) -> None:
        """Record a persistent last-error snapshot."""
        self.last_error_text = text

    def clear(self) -> None:
        self.output_buffer.clear()
        self.last_error_text = None


# ---------------------------------------------------------------------------
# L2: REPL state tools (exposed to the LLM via dispatch_fn)
# ---------------------------------------------------------------------------

def _build_repl_tools(repl_state: ReplState, interp: Any, cwd: str) -> tuple[
    list[dict[str, Any]],
    Callable[[str, dict[str, Any]], str],
]:
    """Build tool definitions + a dispatch_fn that handles the REPL tools.

    Returns (tool_schemas, dispatch_fn). The dispatch_fn falls through to
    the default ``dispatch_tool`` for non-REPL tools (stdlib / load_skill).
    """
    from helen.runtime.tools import dispatch_tool as _default_dispatch

    repl_tools: list[dict[str, Any]] = [
        {
            "name": "repl_definitions",
            "description": (
                "List all functions and agents currently defined in the "
                "user's REPL session. Call this when the user refers to "
                "'my function X' or 'the agent I defined' so you know what "
                "actually exists."
            ),
            "parameters": {
                "type": "object",
                "properties": {},
            },
        },
        {
            "name": "repl_last_error",
            "description": (
                "Return the last error the user hit in the REPL (type, "
                "message, location). Use this when the user asks 'why did "
                "this fail' or 'fix my error'."
            ),
            "parameters": {
                "type": "object",
                "properties": {},
            },
        },
        {
            "name": "repl_history",
            "description": (
                "Return the last N lines of REPL output (default 10). "
                "Use this to see what the user's code actually produced."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "n": {
                        "type": "integer",
                        "description": "Number of recent lines (default 10, max 50).",
                    },
                },
            },
        },
        {
            "name": "repl_read_file",
            "description": (
                "Read a file from the user's current working directory. "
                "Path is relative to the REPL's cwd. Use this to inspect "
                "source code the user is working on. Restricted to cwd for "
                "safety."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Relative path within the REPL cwd.",
                    },
                },
                "required": ["path"],
            },
        },
    ]

    def dispatch(name: str, args: dict[str, Any]) -> str:
        if name == "repl_definitions":
            try:
                defs = interp.list_definitions()
            except Exception as e:
                return json.dumps({"error": str(e)})
            return json.dumps({
                "functions": defs.get("functions") or [],
                "agents": defs.get("agents") or [],
            }, ensure_ascii=False)

        if name == "repl_last_error":
            if repl_state.last_error_text:
                return repl_state.last_error_text
            # Fall back to observability.last_error snapshot
            snap = getattr(getattr(interp, "observability", None),
                           "last_error", None)
            if snap is not None:
                try:
                    return snap.format_text(verbose=False)
                except Exception:
                    return json.dumps(snap.to_dict(), ensure_ascii=False)
            return "(no error recorded)"

        if name == "repl_history":
            n = int(args.get("n", 10)) if args else 10
            n = max(1, min(n, 50))
            lines = repl_state.output_buffer[-n:]
            return "\n".join(lines) if lines else "(no recent output)"

        if name == "repl_read_file":
            rel_path = (args or {}).get("path", "")
            if not rel_path:
                return "(error: 'path' argument required)"
            # Safety: confine to cwd
            cwd_path = Path(cwd).resolve()
            target = (cwd_path / rel_path).resolve()
            try:
                target.relative_to(cwd_path)
            except ValueError:
                return f"(error: path escapes cwd: {rel_path})"
            if not target.is_file():
                return f"(error: not a file: {rel_path})"
            try:
                text = target.read_text(encoding="utf-8", errors="replace")
            except Exception as e:
                return f"(error reading file: {e})"
            # Cap at 8000 chars to avoid blowing context
            if len(text) > 8000:
                text = text[:8000] + f"\n\n... [{len(text) - 8000} chars truncated]"
            return text

        # Fall through to stdlib / skill tools
        try:
            return _default_dispatch(name, args)
        except Exception as e:
            return f"(tool '{name}' not found: {e})"

    return repl_tools, dispatch


# ---------------------------------------------------------------------------
# Prompt assembly (L1)
# ---------------------------------------------------------------------------

def build_assistant_prompt(
    interp: Any,
    repl_state: ReplState,
    cwd: str,
    skill_dirs: list[str] | None = None,
) -> str:
    """Assemble the assistant's system prompt (L1).

    Combines framework_instructions + helen_conventions + skill_index +
    REPL context block. Called fresh on every :ask invocation so the
    assistant always sees current REPL state.
    """
    builder = PromptBuilder()
    if skill_dirs:
        builder.set_skill_dirs(skill_dirs)

    try:
        definitions = interp.list_definitions()
    except Exception:
        definitions = {"functions": [], "agents": []}

    repl_block = PromptBuilder.format_repl_context_block(
        definitions=definitions,
        last_error_text=repl_state.last_error_text,
        recent_output=repl_state.output_buffer,
        cwd=cwd,
    )
    return builder.build_assistant_system_prompt(repl_context=repl_block)


# ---------------------------------------------------------------------------
# Single-turn :ask (L1 + L2)
# ---------------------------------------------------------------------------

def ask_single(
    question: str,
    interp: Any,
    repl_state: ReplState,
    cwd: str,
    skill_dirs: list[str] | None = None,
    stream: bool = True,
) -> str:
    """Run a single :ask question and return the assistant's response.

    Streams the response to stdout if ``stream=True`` (default). Also
    returns the full response text so callers can record it.
    """
    from helen.runtime.http_llm import HttpLLMRuntime

    system_prompt = build_assistant_prompt(interp, repl_state, cwd, skill_dirs)
    repl_tools, dispatch_fn = _build_repl_tools(repl_state, interp, cwd)

    # Use the interp's llm_runtime if it's an HttpLLMRuntime; otherwise build one
    runtime = getattr(interp, "llm_runtime", None)
    if runtime is None or not isinstance(runtime, HttpLLMRuntime):
        runtime = HttpLLMRuntime()

    if stream and hasattr(runtime, "act_stream"):
        return _run_streaming(runtime, question, system_prompt, repl_tools,
                              dispatch_fn)
    # Fallback: non-streaming
    response = runtime.act(
        prompt=question,
        system_prompt=system_prompt,
        tools=repl_tools,
        max_turns=5,
        dispatch_fn=dispatch_fn,
    )
    text = response.text if hasattr(response, "text") else str(response)
    print(text)
    return text


def _run_streaming(runtime: Any, prompt: str, system_prompt: str,
                   tools: list[dict[str, Any]], dispatch_fn: Callable) -> str:
    """Stream the assistant response to stdout; return the full text."""
    chunks: list[str] = []
    try:
        stream_iter = runtime.act_stream(
            prompt=prompt,
            system_prompt=system_prompt,
            tools=tools,
            max_turns=5,
            dispatch_fn=dispatch_fn,
        )
        for chunk in stream_iter:
            if chunk:
                sys.stdout.write(chunk)
                sys.stdout.flush()
                chunks.append(chunk)
    except KeyboardInterrupt:
        # Graceful interrupt
        if hasattr(runtime, "cancel_streaming"):
            runtime.cancel_streaming()
        sys.stdout.write("\n⚡ assistant interrupted")
        sys.stdout.flush()
    except Exception as e:
        sys.stdout.write(f"\n(assistant error: {e})")
        sys.stdout.flush()
    print()  # final newline
    return "".join(chunks)


# ---------------------------------------------------------------------------
# Multi-turn chat mode (L3)
# ---------------------------------------------------------------------------

@dataclass
class AssistantSession:
    """Multi-turn :ask conversation state.

    Each session has its own session_id (separate from the main REPL's
    transcript) so the assistant's conversation history doesn't pollute
    the REPL's program transcript. Persists via TranscriptStore so it
    can be resumed with ``:ask --resume <sid>``.
    """

    session_id: str
    # The dedicated interpreter used for this assistant session. Kept
    # between chat turns so llm act sees prior turns via transcript.
    interp: Any = None
    # Per-session REPL state snapshot (independent of main REPL's buffer).
    repl_state: ReplState = field(default_factory=ReplState)

    def record_user_message(self, text: str) -> None:
        """Record a user turn into the assistant's transcript."""
        store = getattr(getattr(self.interp, "_agent_context", None),
                        "transcript_store", None)
        if store is not None:
            try:
                from helen.runtime.transcript_store import Message
                store.add(Message(role="user", content=text))
            except Exception:
                pass

    def record_assistant_message(self, text: str) -> None:
        store = getattr(getattr(self.interp, "_agent_context", None),
                        "transcript_store", None)
        if store is not None:
            try:
                from helen.runtime.transcript_store import Message
                store.add(Message(role="assistant", content=text))
            except Exception:
                pass


def new_assistant_session(
    cwd: str,
    skill_dirs: list[str] | None = None,
    session_id: str | None = None,
) -> AssistantSession:
    """Create a new assistant session (or resume an existing one).

    The session uses its own Interpreter with its own TranscriptStore,
    isolated from the main REPL's transcript.
    """
    from helen.core.errors import ErrorReporter
    from helen.interpreter.interpreter import Interpreter
    from helen.runtime.http_llm import HttpLLMRuntime
    from helen.runtime.import_resolver import ImportResolver

    errors = ErrorReporter()
    runtime = HttpLLMRuntime()
    import_resolver = ImportResolver(base_dir=cwd, error_reporter=errors)
    interp = Interpreter(
        errors=errors,
        llm_runtime=runtime,
        import_resolver=import_resolver,
        session_id=session_id,  # None -> new session; else resume
    )
    actual_sid = interp.get_session_id() if hasattr(interp, "get_session_id") else session_id or ""
    return AssistantSession(session_id=actual_sid, interp=interp)


def chat_turn(
    user_input: str,
    session: AssistantSession,
    cwd: str,
    skill_dirs: list[str] | None = None,
    stream: bool = True,
) -> str:
    """Run one turn of the chat conversation. Returns the assistant text."""
    session.record_user_message(user_input)
    # Build prompt using the session's own interpreter + its repl_state
    system_prompt = build_assistant_prompt(
        session.interp, session.repl_state, cwd, skill_dirs,
    )
    repl_tools, dispatch_fn = _build_repl_tools(
        session.repl_state, session.interp, cwd,
    )

    runtime = getattr(session.interp, "llm_runtime", None)
    if runtime is None:
        from helen.runtime.http_llm import HttpLLMRuntime
        runtime = HttpLLMRuntime()

    if stream and hasattr(runtime, "act_stream"):
        text = _run_streaming(runtime, user_input, system_prompt,
                              repl_tools, dispatch_fn)
    else:
        response = runtime.act(
            prompt=user_input,
            system_prompt=system_prompt,
            tools=repl_tools,
            max_turns=5,
            dispatch_fn=dispatch_fn,
        )
        text = response.text if hasattr(response, "text") else str(response)
        print(text)

    session.record_assistant_message(text)
    return text


def run_chat_mode(
    session: AssistantSession,
    cwd: str,
    skill_dirs: list[str] | None = None,
) -> None:
    """Enter the multi-turn :ask sub-REPL.

    Loops until the user types ``:exit``, ``exit``, or presses Ctrl+C at
    an empty prompt. Each turn is a chat_turn() call; the session's
    transcript accumulates the conversation.
    """
    print(f"\n💬 Entered :ask chat mode (session: {session.session_id})")
    print("   Type :exit or Ctrl+C to return to the main REPL.\n")

    while True:
        try:
            user_input = input("[:ask] >>> ")
        except EOFError:
            print()
            break
        except KeyboardInterrupt:
            print("\n(chat mode exited)")
            break

        line = user_input.strip()
        if not line:
            continue
        if line in (":exit", "exit", ":quit", "quit"):
            break

        try:
            chat_turn(line, session, cwd, skill_dirs)
        except KeyboardInterrupt:
            print("\n⚡ turn interrupted; chat mode preserved")
        except Exception as e:
            print(f"(assistant error: {e})", file=sys.stderr)


# ---------------------------------------------------------------------------
# Listing / resuming sessions
# ---------------------------------------------------------------------------

def list_assistant_sessions() -> list[dict[str, Any]]:
    """List past :ask chat sessions from TranscriptStore.

    Returns list of session dicts (session_id, created_at, message_count).
    Sorted newest-first.
    """
    from helen.runtime.session_manager import SessionManager
    try:
        manager = SessionManager()
        all_sessions = manager.list_sessions()
    except Exception:
        return []
    # Filter to sessions that look like assistant sessions
    # (We can't perfectly distinguish them, so we return all and let the
    # user pick. In the future we could prefix assistant session IDs.)
    return all_sessions[:20]  # Cap to most recent 20
