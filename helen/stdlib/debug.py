"""Debug stdlib functions for Helen.

Provides AI-native debugging functions that give LLMs structured access
to error context, diagnostic suggestions, and data flow information.

All functions in this module follow the "Push model" design:
- Information is proactively provided in structured format
- LLM passively receives and consumes the data
- No LLM calls in the error handling path (100% deterministic)

Usage in Helen:
    # After an error occurs:
    let err = last_error_detail()
    if err != null {
        debug("Error category: " + err.diagnostic_category)
        debug("Suggestion: " + err.suggestion)
    }
"""

from __future__ import annotations

from typing import Any


def last_error_detail() -> dict | None:
    """Get detailed information about the last error that occurred.

    Returns a dictionary with:
    - error_type: str - The type of error (e.g., "RuntimeError", "LLMError")
    - message: str - The error message
    - location: str - Source location (file:line:col)
    - call_stack: list - Call stack at error time
    - scope: dict - Local variables in scope
    - trace: list - Recent execution trace
    - timestamp: float - When the error occurred
    - diagnostic_category: str - Semantic classification (e.g., "LLMTimeout")
    - suggestion: str - Actionable suggestion for fixing the error
    - data_flow: list - Data flow tracing information

    Returns None if no error has occurred yet.
    """
    from helen.stdlib.context_helpers import get_interpreter

    interp = get_interpreter()
    if interp is None or interp.observability is None:
        return None

    snapshot = interp.observability.last_error
    if snapshot is None:
        return None

    return snapshot.to_dict()


def error_category(error: dict) -> str:
    """Extract the diagnostic category from an error dictionary.

    The diagnostic category is a semantic classification of the error,
    such as "LLMTimeout", "AgentCallFailed", "RuntimeGenericError", etc.

    Args:
        error: Error dictionary (from last_error_detail())

    Returns:
        The diagnostic category string, or "Unknown" if not available.
    """
    if not isinstance(error, dict):
        return "Unknown"
    return error.get("diagnostic_category", "Unknown")


def error_suggestion(error: dict) -> str:
    """Extract the actionable suggestion from an error dictionary.

    The suggestion provides specific guidance on how to fix the error,
    generated statically (no LLM calls) based on the error type and context.

    Args:
        error: Error dictionary (from last_error_detail())

    Returns:
        The suggestion string, or empty string if not available.
    """
    if not isinstance(error, dict):
        return ""
    return error.get("suggestion", "")


def error_data_flow(error: dict) -> list:
    """Extract data flow tracing information from an error dictionary.

    Data flow shows where values in the error context came from,
    helping trace the origin of problematic data.

    Args:
        error: Error dictionary (from last_error_detail())

    Returns:
        List of data flow entries (each a dict with variable/source/via fields).
    """
    if not isinstance(error, dict):
        return []
    return error.get("data_flow", [])


def validate_output(output: str, contract: Any) -> dict:
    """Validate LLM output against a contract specification.

    v1.40: Validates output against simple contracts ("json", "text") or
    schema contracts ({type: "object", required: [...], properties: {...}}).

    Args:
        output: The output string to validate
        contract: Contract specification (None, "json", "text", or schema dict)

    Returns:
        Dict with keys:
        - valid: bool - whether output matches contract
        - violation: str - description of violation (empty if valid)
        - parsed: Any - parsed output if applicable (e.g., parsed JSON)

    Example:
        # Validate JSON
        let result = validate_output('{"name": "Alice"}', "json")
        if result.valid {
            debug("Valid JSON: " + result.parsed)
        }

        # Validate schema
        let schema = {type: "object", required: ["name"]}
        let result = validate_output('{"name": "Alice"}', schema)
    """
    from helen.runtime.output_validator import validate_output as _validate

    return _validate(output, contract)


def record_session(cassette_path: str) -> dict:
    """Start recording LLM interactions to a cassette file.

    v1.40: Records all LLM calls (requests and responses) to a JSONL file
    for later replay. This enables deterministic debugging of non-deterministic
    LLM behavior.

    Args:
        cassette_path: Path to save the cassette file (JSONL format)

    Returns:
        Dict with keys:
        - status: "recording" or "error"
        - cassette_path: Path to the cassette file
        - message: Status message

    Example:
        let result = record_session("debug/session.jsonl")
        # ... run agent with LLM calls ...
        stop_recording()

        # Later, replay the session:
        replay_session("debug/session.jsonl")
    """
    from helen.stdlib.context_helpers import get_interpreter

    interp = get_interpreter()
    if interp is None or not hasattr(interp, 'llm_runtime'):
        return {
            "status": "error",
            "cassette_path": cassette_path,
            "message": "No interpreter context available",
        }

    try:
        if hasattr(interp.llm_runtime, 'enable_recording'):
            interp.llm_runtime.enable_recording(cassette_path)
            return {
                "status": "recording",
                "cassette_path": cassette_path,
                "message": f"Recording to {cassette_path}",
            }
        else:
            return {
                "status": "error",
                "cassette_path": cassette_path,
                "message": "LLM runtime does not support recording",
            }
    except Exception as e:
        return {
            "status": "error",
            "cassette_path": cassette_path,
            "message": f"Failed to start recording: {str(e)}",
        }


def stop_recording() -> dict:
    """Stop recording LLM interactions.

    v1.40: Stops the recording started by record_session() and closes the
    cassette file.

    Returns:
        Dict with keys:
        - status: "stopped" or "error"
        - message: Status message

    Example:
        record_session("debug/session.jsonl")
        # ... run agent ...
        let result = stop_recording()
    """
    from helen.stdlib.context_helpers import get_interpreter

    interp = get_interpreter()
    if interp is None or not hasattr(interp, 'llm_runtime'):
        return {
            "status": "error",
            "message": "No interpreter context available",
        }

    try:
        if hasattr(interp.llm_runtime, 'disable_recording'):
            interp.llm_runtime.disable_recording()
            return {
                "status": "stopped",
                "message": "Recording stopped",
            }
        else:
            return {
                "status": "error",
                "message": "LLM runtime does not support recording",
            }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to stop recording: {str(e)}",
        }


def replay_session(cassette_path: str) -> dict:
    """Replay LLM interactions from a cassette file.

    v1.40: Replaces the current LLM runtime with a replay runtime that
    returns recorded responses instead of making actual LLM calls. This
    enables deterministic debugging of non-deterministic LLM behavior.

    Args:
        cassette_path: Path to the cassette file to replay from

    Returns:
        Dict with keys:
        - status: "replaying" or "error"
        - cassette_path: Path to the cassette file
        - entry_count: Number of recorded interactions
        - message: Status message

    Example:
        let result = replay_session("debug/session.jsonl")
        # Now all LLM calls will use recorded responses
    """
    from helen.stdlib.context_helpers import get_interpreter

    interp = get_interpreter()
    if interp is None or not hasattr(interp, 'llm_runtime'):
        return {
            "status": "error",
            "cassette_path": cassette_path,
            "entry_count": 0,
            "message": "No interpreter context available",
        }

    try:
        from helen.runtime.recording import ReplayLLMRuntime, CassetteReader

        # Count entries in cassette
        reader = CassetteReader(cassette_path)
        entry_count = len(reader)

        # Replace LLM runtime with replay runtime
        interp.llm_runtime = ReplayLLMRuntime(cassette_path)

        return {
            "status": "replaying",
            "cassette_path": cassette_path,
            "entry_count": entry_count,
            "message": f"Replaying {entry_count} interactions from {cassette_path}",
        }
    except Exception as e:
        return {
            "status": "error",
            "cassette_path": cassette_path,
            "entry_count": 0,
            "message": f"Failed to start replay: {str(e)}",
        }


def trace_value_origin(message_uuid: str) -> list[dict]:
    """Trace the origin of data consumed by a message.

    v1.40: Queries the data lineage tracker to find where the data in a
    message came from. Useful for debugging data flow issues in multi-agent
    systems.

    Args:
        message_uuid: UUID of the message to trace

    Returns:
        List of dicts, each containing:
        - producer_uuid: UUID of the message that produced the data
        - flow_type: Type of flow ("channel", "agent_call", "prompt")
        - timestamp: When the flow occurred
        - metadata: Additional metadata

    Example:
        let origins = trace_value_origin("msg_xyz")
        for origin in origins {
            debug("Data came from: " + origin.producer_uuid)
        }
    """
    from helen.stdlib.context_helpers import get_interpreter

    interp = get_interpreter()
    if interp is None:
        return []

    # Get data lineage tracker from interpreter context
    tracker = getattr(interp, '_data_lineage_tracker', None)
    if tracker is None:
        return []

    flows = tracker.get_origin(message_uuid)
    return [flow.to_dict() for flow in flows]


def trace_value_consumers(message_uuid: str) -> list[dict]:
    """Trace the consumers of data produced by a message.

    v1.40: Queries the data lineage tracker to find which messages consumed
    data from a given message. Useful for understanding data flow and
    debugging data propagation issues.

    Args:
        message_uuid: UUID of the message to trace

    Returns:
        List of dicts, each containing:
        - consumer_uuid: UUID of the message that consumed the data
        - flow_type: Type of flow ("channel", "agent_call", "prompt")
        - timestamp: When the flow occurred
        - metadata: Additional metadata

    Example:
        let consumers = trace_value_consumers("msg_abc")
        for consumer in consumers {
            debug("Data was consumed by: " + consumer.consumer_uuid)
        }
    """
    from helen.stdlib.context_helpers import get_interpreter

    interp = get_interpreter()
    if interp is None:
        return []

    # Get data lineage tracker from interpreter context
    tracker = getattr(interp, '_data_lineage_tracker', None)
    if tracker is None:
        return []

    flows = tracker.get_consumers(message_uuid)
    return [flow.to_dict() for flow in flows]


def get_data_lineage() -> dict:
    """Get the complete data lineage graph for the current session.

    v1.40: Returns the full data flow graph showing how data moves between
    messages and agents. Useful for visualizing and debugging complex
    multi-agent interactions.

    Returns:
        Dict with keys:
        - nodes: List of message UUIDs
        - edges: List of data flow edges, each containing:
          - source: Producer message UUID
          - target: Consumer message UUID
          - flow_type: Type of flow
          - timestamp: When the flow occurred
          - metadata: Additional metadata

    Example:
        let lineage = get_data_lineage()
        debug("Nodes: " + str(len(lineage.nodes)))
        debug("Edges: " + str(len(lineage.edges)))
    """
    from helen.stdlib.context_helpers import get_interpreter

    interp = get_interpreter()
    if interp is None:
        return {"nodes": [], "edges": []}

    # Get data lineage tracker from interpreter context
    tracker = getattr(interp, '_data_lineage_tracker', None)
    if tracker is None:
        return {"nodes": [], "edges": []}

    return tracker.get_full_lineage()


def record_data_flow(
    producer_uuid: str,
    consumer_uuid: str,
    flow_type: str,
    metadata: dict | None = None,
) -> dict:
    """Manually record a data flow event.

    v1.40: Allows manual recording of data flows for custom tracking scenarios.
    Most data flows are automatically tracked, but this function enables
    recording custom flows that the runtime doesn't automatically detect.

    Args:
        producer_uuid: UUID of the message that produced the data
        consumer_uuid: UUID of the message that consumed the data
        flow_type: Type of flow ("channel", "agent_call", "prompt", or custom)
        metadata: Optional metadata dict (e.g., {"channel": "main", "arg": "input"})

    Returns:
        Dict with keys:
        - status: "recorded" or "error"
        - message: Status message

    Example:
        record_data_flow(
            "msg_abc",
            "msg_xyz",
            "custom_transform",
            {"transform": "uppercase"}
        )
    """
    from helen.stdlib.context_helpers import get_interpreter

    interp = get_interpreter()
    if interp is None:
        return {
            "status": "error",
            "message": "No interpreter context available",
        }

    # Get data lineage tracker from interpreter context
    tracker = getattr(interp, '_data_lineage_tracker', None)
    if tracker is None:
        return {
            "status": "error",
            "message": "Data lineage tracker not initialized",
        }

    try:
        tracker.record_flow(producer_uuid, consumer_uuid, flow_type, metadata or {})
        return {
            "status": "recorded",
            "message": f"Recorded {flow_type} flow from {producer_uuid} to {consumer_uuid}",
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to record data flow: {str(e)}",
        }
