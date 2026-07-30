"""Resilience primitives for LLM calls.

Provides:
- ``ErrorCategory`` - classification of LLM API errors into retryable categories
- ``classify_error`` - status-code-based classification (replaces fragile string matching)
- ``compute_backoff`` - exponential backoff with full jitter (prevents thundering herd)
- ``parse_retry_after`` - parse HTTP ``Retry-After`` header (seconds or HTTP-date)
- ``CircuitBreaker`` - three-state breaker (closed/open/half-open) that fails fast
  when the API is down, instead of retrying every call

Design notes
------------
These were extracted from ``http_llm.py``'s ad-hoc retry logic (v1.31) to give
LLM-call resilience a systematic, testable home. The breaker is per-runtime and
thread-safe; backoff uses *full jitter* (``uniform(0, min(base*2^attempt, cap))``)
so concurrent ``spawn``-ed agents that hit 429s simultaneously don't all retry on
the same clock tick.
"""

from __future__ import annotations

import logging
import random
import threading
import time
from email.utils import parsedate_to_datetime
from enum import Enum

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Error classification
# ---------------------------------------------------------------------------


class ErrorCategory(Enum):
    """Categories of LLM API errors, each with a distinct retry strategy."""

    # Retryable - transient server-side problems
    RATE_LIMIT = "rate_limit"        # 429 - slow backoff, respect Retry-After
    SERVER_ERROR = "server_error"    # 500/502/503/504 - medium backoff
    NETWORK = "network"              # connect/read/protocol errors - fast backoff
    TIMEOUT = "timeout"              # request timeout - medium backoff

    # Non-retryable via simple backoff
    CONTEXT_OVERFLOW = "context_overflow"    # handled by recovery cascade, not backoff
    NON_RETRYABLE = "non_retryable"         # 4xx (except 429), auth, bad request


# Per-category backoff parameters (base seconds, cap seconds).
# RATE_LIMIT is slowest (don't hammer a throttling server); NETWORK is fastest
# (transient, often resolves immediately); SERVER_ERROR and TIMEOUT in between.
_BACKOFF_CONFIG: dict[ErrorCategory, tuple[float, float]] = {
    ErrorCategory.RATE_LIMIT: (2.0, 60.0),
    ErrorCategory.SERVER_ERROR: (1.0, 10.0),
    ErrorCategory.NETWORK: (0.5, 5.0),
    ErrorCategory.TIMEOUT: (1.0, 10.0),
}

# Error categories that are worth retrying with backoff.
_RETRYABLE = {
    ErrorCategory.RATE_LIMIT,
    ErrorCategory.SERVER_ERROR,
    ErrorCategory.NETWORK,
    ErrorCategory.TIMEOUT,
}


def classify_error(
    status_code: int | None,
    error_msg: str,
    context_overflow_fn=None,
) -> ErrorCategory:
    """Classify an LLM API error into a retry category.

    Uses the HTTP status code as the primary signal (robust), falling back to
    substring matching on the error message only when no status code is
    available (e.g. raw transport errors).

    Args:
        status_code: HTTP status code, or ``None`` if not an HTTP error.
        error_msg: The error message string.
        context_overflow_fn: Optional callable that returns True for context-length
            errors. Injected to avoid a circular import with ``http_llm``.

    Returns:
        The :class:`ErrorCategory` for this error.
    """
    # Context overflow has its own recovery path - check first.
    if context_overflow_fn is not None and error_msg and context_overflow_fn(error_msg):
        return ErrorCategory.CONTEXT_OVERFLOW

    # Status-code-based classification (primary, robust).
    if status_code == 429:
        return ErrorCategory.RATE_LIMIT
    if status_code in (500, 502, 503, 504):
        return ErrorCategory.SERVER_ERROR
    if status_code is not None and 400 <= status_code < 500:
        # Other 4xx (auth, bad request, etc.) - not retryable via backoff.
        return ErrorCategory.NON_RETRYABLE

    # No status code - fall back to message inspection for transport errors.
    msg_lower = (error_msg or "").lower()
    if "timed out" in msg_lower or "timeout" in msg_lower:
        return ErrorCategory.TIMEOUT
    if "connect" in msg_lower or "read error" in msg_lower or "remote protocol" in msg_lower:
        return ErrorCategory.NETWORK
    if "http request failed" in msg_lower:
        return ErrorCategory.NETWORK

    return ErrorCategory.NON_RETRYABLE


def is_retryable(category: ErrorCategory) -> bool:
    """Whether a category should be retried with backoff."""
    return category in _RETRYABLE


# ---------------------------------------------------------------------------
# Backoff
# ---------------------------------------------------------------------------


def compute_backoff(
    category: ErrorCategory,
    attempt: int,
    retry_after: float | None = None,
) -> float:
    """Compute a backoff wait time with exponential backoff + full jitter.

    Uses the *full jitter* strategy (``uniform(0, min(base * 2^attempt, cap))``)
    rather than a fixed ``2**attempt``. When multiple ``spawn``-ed agents hit a
    429 simultaneously, full jitter spreads their retries across a window instead
    of all retrying on the same tick - avoiding a self-reinforcing throttle loop.

    Args:
        category: The error category (selects base/cap).
        attempt: Zero-based attempt index (0 = first retry).
        retry_after: Parsed ``Retry-After`` value in seconds, if the server
            provided one (typically for 429). When present, it is used as a floor.

    Returns:
        Seconds to wait before the next attempt. Always >= 0.
    """
    base, cap = _BACKOFF_CONFIG.get(category, _BACKOFF_CONFIG[ErrorCategory.SERVER_ERROR])
    exponential = min(base * (2 ** attempt), cap)

    if retry_after is not None and retry_after > 0:
        # Respect the server's hint as a floor, but still jitter above it slightly
        # so concurrent clients don't all wake at the exact Retry-After instant.
        jitter = random.uniform(0, exponential) if exponential > 0 else random.uniform(0, 0.5)
        return retry_after + jitter

    # Full jitter: uniform between 0 and the exponential cap.
    return random.uniform(0, exponential) if exponential > 0 else 0.0


def parse_retry_after(header_value: str | None) -> float | None:
    """Parse an HTTP ``Retry-After`` header value.

    The header may be either:
    - An integer/float number of seconds (``"120"``), or
    - An HTTP-date (``"Wed, 21 Oct 2026 07:28:00 GMT"``).

    Args:
        header_value: Raw header string, or ``None``.

    Returns:
        Seconds to wait (>= 0), or ``None`` if unparseable.
    """
    if not header_value:
        return None
    value = header_value.strip()
    # Integer/float seconds first (most common for API gateways).
    try:
        return max(float(value), 0.0)
    except ValueError:
        pass
    # HTTP-date format.
    try:
        dt = parsedate_to_datetime(value)
        delta = dt.timestamp() - time.time()
        return max(delta, 0.0)
    except (TypeError, ValueError, OverflowError):
        return None


# ---------------------------------------------------------------------------
# Circuit breaker
# ---------------------------------------------------------------------------


class CircuitBreaker:
    """Three-state circuit breaker for LLM API calls.

    States:
    - ``CLOSED``: normal operation; requests pass through and failures are counted.
    - ``OPEN``: tripped after ``failure_threshold`` consecutive failures; requests
      fail fast without hitting the network. After ``recovery_timeout`` seconds,
      transitions to ``HALF_OPEN``.
    - ``HALF_OPEN``: a single probe request is allowed. If it succeeds, the
      breaker closes; if it fails, the breaker reopens for another cooldown.

    This prevents a tool-calling loop from making 4 doomed retry attempts on
    *every* iteration when the API is fully down - instead, after the breaker
    trips, subsequent iterations fail immediately.

    Thread-safe.
    """

    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self._state = self.CLOSED
        self._failure_count = 0
        self._last_failure_time: float | None = None
        self._lock = threading.Lock()

    @property
    def state(self) -> str:
        """Current breaker state (may transition OPEN -> HALF_OPEN on read)."""
        with self._lock:
            self._maybe_recover()
            return self._state

    @property
    def failure_count(self) -> int:
        with self._lock:
            return self._failure_count

    def _maybe_recover(self) -> None:
        """Transition OPEN -> HALF_OPEN if the cooldown has elapsed (caller holds lock)."""
        if (
            self._state == self.OPEN
            and self._last_failure_time is not None
            and time.time() - self._last_failure_time >= self.recovery_timeout
        ):
            self._state = self.HALF_OPEN
            logger.info(
                "Circuit breaker entering HALF_OPEN after %.0fs cooldown",
                self.recovery_timeout,
            )

    def allow_request(self) -> bool:
        """Whether a request should be allowed through right now.

        Returns False only when the breaker is OPEN (fail-fast). In HALF_OPEN it
        returns True to permit a probe; in CLOSED it always returns True.
        """
        with self._lock:
            self._maybe_recover()
            if self._state == self.OPEN:
                return False
            return True

    def record_success(self) -> None:
        """Record a successful call; resets the breaker to CLOSED."""
        with self._lock:
            if self._state != self.CLOSED:
                logger.info("Circuit breaker closing after successful call")
            self._failure_count = 0
            self._state = self.CLOSED
            self._last_failure_time = None

    def record_failure(self) -> None:
        """Record a failed call; may trip the breaker to OPEN."""
        with self._lock:
            self._failure_count += 1
            self._last_failure_time = time.time()
            if self._state == self.HALF_OPEN:
                # Probe failed - reopen for a fresh cooldown.
                logger.warning("Circuit breaker probe failed - reopening")
                self._state = self.OPEN
            elif self._failure_count >= self.failure_threshold:
                if self._state != self.OPEN:
                    logger.warning(
                        "Circuit breaker tripping OPEN after %d consecutive failures",
                        self._failure_count,
                    )
                self._state = self.OPEN

    def reset(self) -> None:
        """Force-reset to CLOSED (e.g. for testing or manual recovery)."""
        with self._lock:
            self._state = self.CLOSED
            self._failure_count = 0
            self._last_failure_time = None
