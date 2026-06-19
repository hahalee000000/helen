"""AI-native observability for Helen runtime.

Provides structured execution context for AI debugging:
- Call stack tracking
- Execution trace logging
- Structured error snapshots
- LLM call audit logging

This module is designed for AI consumption, not human interactive debugging.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from typing import Any

from helen.core.source import SourceSpan


# ---------------------------------------------------------------------------
# Call Stack Frame
# ---------------------------------------------------------------------------

@dataclass
class CallFrame:
    """A single frame in the call stack.

    Attributes:
        function_name: Name of the function/agent being called.
        location: Source location (file:line:col).
        args: Arguments passed to the function (for debugging).
        locals_snapshot: Snapshot of local variables at entry (optional).
    """

    function_name: str
    location: str  # "file:line:col" or "line:col"
    args: dict[str, Any] = field(default_factory=dict)
    entry_time: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        """Convert to JSON-serializable dict."""
        return {
            "function": self.function_name,
            "location": self.location,
            "args": _safe_serialize(self.args),
        }

    @staticmethod
    def format_location(span: SourceSpan | None) -> str:
        """Format a SourceSpan as a location string."""
        if span is None:
            return "<unknown>"
        if span.file:
            return f"{span.file}:{span.start_line}:{span.start_col}"
        return f"{span.start_line}:{span.start_col}"


# ---------------------------------------------------------------------------
# Call Stack Tracker
# ---------------------------------------------------------------------------

class CallStackTracker:
    """Tracks the call stack during execution.

    Provides structured call stack information for AI debugging.
    """

    def __init__(self, max_depth: int = 100):
        """Initialize the call stack tracker.

        Args:
            max_depth: Maximum call stack depth to track.
        """
        self._stack: list[CallFrame] = []
        self._max_depth = max_depth
        self._enabled = False

    @property
    def enabled(self) -> bool:
        """Whether call stack tracking is enabled."""
        return self._enabled

    @enabled.setter
    def enabled(self, value: bool) -> None:
        """Enable or disable call stack tracking."""
        self._enabled = value
        if not value:
            self._stack.clear()

    def push(self, function_name: str, span: SourceSpan | None,
             args: dict[str, Any] | None = None) -> None:
        """Push a new frame onto the call stack.

        Args:
            function_name: Name of the function being called.
            span: Source location of the call.
            args: Arguments passed to the function.
        """
        if not self._enabled:
            return

        if len(self._stack) >= self._max_depth:
            # Prevent stack overflow in tracker itself
            return

        frame = CallFrame(
            function_name=function_name,
            location=CallFrame.format_location(span),
            args=args or {},
        )
        self._stack.append(frame)

    def pop(self) -> CallFrame | None:
        """Pop the top frame from the call stack.

        Returns:
            The popped frame, or None if stack is empty.
        """
        if not self._enabled or not self._stack:
            return None
        return self._stack.pop()

    @property
    def depth(self) -> int:
        """Current call stack depth."""
        return len(self._stack)

    @property
    def frames(self) -> list[CallFrame]:
        """Get a copy of the current call stack (bottom to top)."""
        return list(self._stack)

    def to_list(self) -> list[dict[str, Any]]:
        """Convert call stack to JSON-serializable list."""
        return [frame.to_dict() for frame in self._stack]

    def format_traceback(self) -> str:
        """Format call stack as a human-readable traceback string."""
        if not self._stack:
            return ""

        lines = ["Traceback (most recent call first):"]
        for i, frame in enumerate(reversed(self._stack)):
            prefix = "  " if i < len(self._stack) - 1 else "-> "
            lines.append(f"{prefix}{frame.location} in {frame.function_name}")
        return "\n".join(lines)

    def clear(self) -> None:
        """Clear the call stack."""
        self._stack.clear()


# ---------------------------------------------------------------------------
# Execution Trace
# ---------------------------------------------------------------------------

@dataclass
class TraceEntry:
    """A single entry in the execution trace.

    Attributes:
        timestamp: Unix timestamp of the trace event.
        event_type: Type of event (e.g., "stmt", "branch", "call", "return").
        location: Source location.
        data: Additional data for the event.
    """

    timestamp: float
    event_type: str
    location: str
    data: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to JSON-serializable dict."""
        return {
            "time": self.timestamp,
            "type": self.event_type,
            "location": self.location,
            "data": _safe_serialize(self.data),
        }


class ExecutionTracer:
    """Records execution trace for AI debugging.

    Captures statement execution, branch decisions, and variable changes.
    """

    def __init__(self, max_entries: int = 10000):
        """Initialize the execution tracer.

        Args:
            max_entries: Maximum number of trace entries to keep.
        """
        self._entries: list[TraceEntry] = []
        self._max_entries = max_entries
        self._enabled = False

    @property
    def enabled(self) -> bool:
        """Whether tracing is enabled."""
        return self._enabled

    @enabled.setter
    def enabled(self, value: bool) -> None:
        """Enable or disable tracing."""
        self._enabled = value
        if not value:
            self._entries.clear()

    def trace(self, event_type: str, span: SourceSpan | None,
              data: dict[str, Any] | None = None) -> None:
        """Record a trace entry.

        Args:
            event_type: Type of event (stmt, branch, call, return, etc.).
            span: Source location of the event.
            data: Additional data for the event.
        """
        if not self._enabled:
            return

        if len(self._entries) >= self._max_entries:
            # Drop oldest entries
            self._entries.pop(0)

        entry = TraceEntry(
            timestamp=time.time(),
            event_type=event_type,
            location=CallFrame.format_location(span),
            data=data or {},
        )
        self._entries.append(entry)

    @property
    def entries(self) -> list[TraceEntry]:
        """Get a copy of all trace entries."""
        return list(self._entries)

    def to_list(self) -> list[dict[str, Any]]:
        """Convert trace to JSON-serializable list."""
        return [entry.to_dict() for entry in self._entries]

    def format_trace(self, last_n: int = 50) -> str:
        """Format recent trace entries as a human-readable string.

        Args:
            last_n: Number of recent entries to show.

        Returns:
            Formatted trace string.
        """
        if not self._entries:
            return "(no trace entries)"

        entries = self._entries[-last_n:]
        lines = []
        for entry in entries:
            data_str = ""
            if entry.data:
                data_str = " " + json.dumps(entry.data, ensure_ascii=False)
            lines.append(f"[{entry.event_type}] {entry.location}{data_str}")
        return "\n".join(lines)

    def clear(self) -> None:
        """Clear all trace entries."""
        self._entries.clear()


# ---------------------------------------------------------------------------
# Error Snapshot
# ---------------------------------------------------------------------------

@dataclass
class ErrorSnapshot:
    """Structured error context for AI debugging.

    Captures the complete context when an error occurs:
    - Error message and type
    - Source location
    - Call stack at error time
    - Local variables in scope
    - Recent execution trace
    """

    error_type: str
    message: str
    location: str
    call_stack: list[dict[str, Any]]
    scope: dict[str, Any] = field(default_factory=dict)
    trace: list[dict[str, Any]] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        """Convert to JSON-serializable dict."""
        return {
            "error": {
                "type": self.error_type,
                "message": self.message,
                "location": self.location,
            },
            "call_stack": self.call_stack,
            "scope": _safe_serialize(self.scope),
            "trace": self.trace[-20:],  # Last 20 trace entries
            "timestamp": self.timestamp,
        }

    def to_json(self, indent: int = 2) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)

    def format_text(self) -> str:
        """Format as human-readable error context."""
        lines = [
            f"Error: {self.error_type}: {self.message}",
            f"Location: {self.location}",
            "",
            "Call Stack:",
        ]

        if self.call_stack:
            for i, frame in enumerate(reversed(self.call_stack)):
                prefix = "  " if i < len(self.call_stack) - 1 else "-> "
                lines.append(f"{prefix}{frame['location']} in {frame['function']}")
        else:
            lines.append("  (empty)")

        if self.scope:
            lines.append("")
            lines.append("Variables in scope:")
            for name, value in self.scope.items():
                lines.append(f"  {name} = {_format_value(value)}")

        return "\n".join(lines)


# ---------------------------------------------------------------------------
# LLM Audit Log
# ---------------------------------------------------------------------------

@dataclass
class LLMAuditEntry:
    """Audit log entry for LLM calls.

    Attributes:
        timestamp: Unix timestamp of the call.
        call_type: Type of call (act, stream, route).
        agent_name: Name of the agent making the call.
        model: Model used for the call.
        prompt: The prompt sent to the LLM.
        response: The response from the LLM (truncated if long).
        tokens_in: Input tokens consumed.
        tokens_out: Output tokens generated.
        duration_ms: Call duration in milliseconds.
        tool_calls: List of tool calls made by the LLM (if any).
        error: Error message if call failed.
    """

    timestamp: float
    call_type: str
    agent_name: str | None
    model: str | None
    prompt: str
    response: str | None = None
    tokens_in: int = 0
    tokens_out: int = 0
    duration_ms: float = 0
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to JSON-serializable dict."""
        result = {
            "time": self.timestamp,
            "type": self.call_type,
            "agent": self.agent_name,
            "model": self.model,
            "prompt": _truncate(self.prompt, 500),
            "tokens_in": self.tokens_in,
            "tokens_out": self.tokens_out,
            "duration_ms": round(self.duration_ms, 2),
        }
        if self.response:
            result["response"] = _truncate(self.response, 500)
        if self.tool_calls:
            result["tool_calls"] = self.tool_calls
        if self.error:
            result["error"] = self.error
        return result


class LLMAuditLog:
    """Audit log for LLM calls.

    Records all LLM interactions for debugging and analysis.
    """

    def __init__(self, max_entries: int = 1000):
        """Initialize the audit log.

        Args:
            max_entries: Maximum number of entries to keep.
        """
        self._entries: list[LLMAuditEntry] = []
        self._max_entries = max_entries
        self._enabled = True  # Enabled by default

    @property
    def enabled(self) -> bool:
        """Whether audit logging is enabled."""
        return self._enabled

    @enabled.setter
    def enabled(self, value: bool) -> None:
        """Enable or disable audit logging."""
        self._enabled = value

    def log(self, entry: LLMAuditEntry) -> None:
        """Add an entry to the audit log.

        Args:
            entry: The audit entry to add.
        """
        if not self._enabled:
            return

        if len(self._entries) >= self._max_entries:
            self._entries.pop(0)

        self._entries.append(entry)

    @property
    def entries(self) -> list[LLMAuditEntry]:
        """Get a copy of all audit entries."""
        return list(self._entries)

    def to_list(self) -> list[dict[str, Any]]:
        """Convert audit log to JSON-serializable list."""
        return [entry.to_dict() for entry in self._entries]

    def format_summary(self) -> str:
        """Format a summary of LLM calls."""
        if not self._entries:
            return "(no LLM calls recorded)"

        total_calls = len(self._entries)
        total_tokens_in = sum(e.tokens_in for e in self._entries)
        total_tokens_out = sum(e.tokens_out for e in self._entries)
        total_duration = sum(e.duration_ms for e in self._entries)
        errors = sum(1 for e in self._entries if e.error)

        lines = [
            "LLM Call Summary:",
            f"  Total calls: {total_calls}",
            f"  Total tokens: {total_tokens_in} in / {total_tokens_out} out",
            f"  Total duration: {total_duration:.0f}ms",
            f"  Errors: {errors}",
        ]

        if self._entries:
            lines.append("")
            lines.append("Recent calls:")
            for entry in self._entries[-5:]:
                status = "❌" if entry.error else "✅"
                lines.append(
                    f"  {status} [{entry.call_type}] {entry.agent_name or 'anonymous'} "
                    f"({entry.tokens_in}+{entry.tokens_out} tokens, {entry.duration_ms:.0f}ms)"
                )

        return "\n".join(lines)

    def clear(self) -> None:
        """Clear all audit entries."""
        self._entries.clear()


# ---------------------------------------------------------------------------
# Observability Manager
# ---------------------------------------------------------------------------

class ObservabilityManager:
    """Central manager for all observability features.

    Provides unified access to:
    - Call stack tracking
    - Execution tracing
    - Error snapshots
    - LLM audit logging
    """

    def __init__(self):
        """Initialize the observability manager."""
        self.call_stack = CallStackTracker()
        self.tracer = ExecutionTracer()
        self.llm_audit = LLMAuditLog()
        self._last_error: ErrorSnapshot | None = None

    def capture_error(self, error_type: str, message: str,
                      span: SourceSpan | None,
                      scope: dict[str, Any] | None = None) -> ErrorSnapshot:
        """Capture a structured error snapshot.

        Args:
            error_type: Type of error (e.g., "RuntimeError", "ValueError").
            message: Error message.
            span: Source location of the error.
            scope: Local variables in scope at error time.

        Returns:
            The captured error snapshot.
        """
        snapshot = ErrorSnapshot(
            error_type=error_type,
            message=message,
            location=CallFrame.format_location(span),
            call_stack=self.call_stack.to_list(),
            scope=scope or {},
            trace=self.tracer.to_list(),
        )
        self._last_error = snapshot
        return snapshot

    @property
    def last_error(self) -> ErrorSnapshot | None:
        """Get the last captured error snapshot."""
        return self._last_error

    def reset(self) -> None:
        """Reset all observability state."""
        self.call_stack.clear()
        self.tracer.clear()
        self.llm_audit.clear()
        self._last_error = None


# ---------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------

def _safe_serialize(obj: Any, max_depth: int = 3) -> Any:
    """Safely serialize an object for JSON output.

    Handles circular references and non-serializable types.
    """
    def _serialize(o: Any, depth: int) -> Any:
        if depth > max_depth:
            return "<max depth>"

        if o is None or isinstance(o, (bool, int, float, str)):
            return o

        if isinstance(o, (list, tuple)):
            if len(o) > 50:
                return [_serialize(item, depth + 1) for item in o[:50]] + [f"... ({len(o)} items)"]
            return [_serialize(item, depth + 1) for item in o]

        if isinstance(o, dict):
            result = {}
            items = list(o.items())[:50]
            for k, v in items:
                key_str = str(k)
                result[key_str] = _serialize(v, depth + 1)
            if len(o) > 50:
                result["..."] = f"({len(o)} keys total)"
            return result

        # For other types, use repr
        try:
            return repr(o)
        except Exception:
            return f"<{type(o).__name__}>"

    return _serialize(obj, 0)


def _truncate(s: str, max_len: int) -> str:
    """Truncate a string to max length."""
    if len(s) <= max_len:
        return s
    return s[:max_len] + "... [truncated]"


def _format_value(value: Any) -> str:
    """Format a value for display."""
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, str):
        if len(value) > 50:
            return f'"{value[:50]}..."'
        return f'"{value}"'
    if isinstance(value, (list, tuple)):
        if len(value) > 5:
            return f"[{', '.join(_format_value(v) for v in value[:5])}, ... ({len(value)} items)]"
        return f"[{', '.join(_format_value(v) for v in value)}]"
    if isinstance(value, dict):
        if len(value) > 5:
            items = list(value.items())[:5]
            return "{" + ", ".join(f"{k}: {_format_value(v)}" for k, v in items) + ", ...}"
        return "{" + ", ".join(f"{k}: {_format_value(v)}" for k, v in value.items()) + "}"
    return str(value)
