"""Context helpers for stdlib modules that need access to the current interpreter.

Several stdlib modules (debug.py, transcript_query.py) need access to the
active interpreter instance for observability data, agent context, etc.

This module provides a single function `get_interpreter()` that returns
the interpreter reference set via `_set_interpreter_ref()` in llm_control.py.

Note: This was originally intended as a separate module but is implemented
here as a thin wrapper around llm_control._interpreter_ref to avoid
circular imports.
"""
from __future__ import annotations
from typing import Any


def get_interpreter() -> Any:
    """Get the currently active interpreter instance.

    Returns the interpreter reference set by llm_control._set_interpreter_ref().
    Returns None if no interpreter is active (e.g., in unit tests or standalone
    Python code without a running Helen interpreter).

    The interpreter provides access to:
    - observability: LLM call traces, error snapshots
    - llm_runtime: LLM configuration and recording
    - agent_context: Agent-specific context (transcript store, etc.)
    """
    from helen.stdlib.llm_control import _interpreter_ref
    return _interpreter_ref
