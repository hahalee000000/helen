"""Tests for helen.runtime.resilience - circuit breaker, error classification, backoff."""

from __future__ import annotations

import time

from helen.runtime.resilience import (
    CircuitBreaker,
    ErrorCategory,
    classify_error,
    compute_backoff,
    is_retryable,
    parse_retry_after,
)


# ── Error classification ──────────────────────────────────────


class TestClassifyError:
    """classify_error should be driven by status code, not string matching."""

    def test_429_is_rate_limit(self):
        assert classify_error(429, "Too Many Requests") == ErrorCategory.RATE_LIMIT

    def test_500_is_server_error(self):
        assert classify_error(500, "Internal Server Error") == ErrorCategory.SERVER_ERROR

    def test_502_503_504_are_server_errors(self):
        for code in (502, 503, 504):
            assert classify_error(code, "bad gateway") == ErrorCategory.SERVER_ERROR

    def test_400_is_non_retryable(self):
        assert classify_error(400, "Bad Request") == ErrorCategory.NON_RETRYABLE

    def test_401_auth_is_non_retryable(self):
        assert classify_error(401, "Unauthorized") == ErrorCategory.NON_RETRYABLE

    def test_404_is_non_retryable(self):
        assert classify_error(404, "Not Found") == ErrorCategory.NON_RETRYABLE

    def test_timeout_from_message(self):
        assert classify_error(None, "Request timed out after 120s") == ErrorCategory.TIMEOUT

    def test_network_from_message(self):
        assert classify_error(None, "HTTP request failed: connect refused") == ErrorCategory.NETWORK

    def test_read_error_is_network(self):
        assert classify_error(None, "read error") == ErrorCategory.NETWORK

    def test_context_overflow_detected(self):
        def overflow_fn(msg):
            return "context length" in msg.lower()
        assert (
            classify_error(400, "This model's maximum context length is 8192",
                           context_overflow_fn=overflow_fn)
            == ErrorCategory.CONTEXT_OVERFLOW
        )

    def test_context_overflow_takes_precedence_over_4xx(self):
        # Context overflow often comes back as 400, but should be classified as
        # overflow (which has its own recovery path), not non-retryable.
        def overflow_fn(msg):
            return "context" in msg.lower()
        assert (
            classify_error(400, "context length exceeded",
                           context_overflow_fn=overflow_fn)
            == ErrorCategory.CONTEXT_OVERFLOW
        )

    def test_unknown_error_is_non_retryable(self):
        assert classify_error(None, "something weird happened") == ErrorCategory.NON_RETRYABLE

    def test_empty_message(self):
        assert classify_error(None, "") == ErrorCategory.NON_RETRYABLE


class TestIsRetryable:
    def test_rate_limit_retryable(self):
        assert is_retryable(ErrorCategory.RATE_LIMIT)

    def test_server_error_retryable(self):
        assert is_retryable(ErrorCategory.SERVER_ERROR)

    def test_network_retryable(self):
        assert is_retryable(ErrorCategory.NETWORK)

    def test_timeout_retryable(self):
        assert is_retryable(ErrorCategory.TIMEOUT)

    def test_context_overflow_not_simple_retryable(self):
        assert not is_retryable(ErrorCategory.CONTEXT_OVERFLOW)

    def test_non_retryable(self):
        assert not is_retryable(ErrorCategory.NON_RETRYABLE)


# ── Backoff ───────────────────────────────────────────────────


class TestComputeBackoff:
    """Backoff should use full jitter and stay within category caps."""

    def test_rate_limit_uses_slow_base(self):
        # attempt 0: base 2.0, so jitter range [0, 2.0]
        for _ in range(50):
            wait = compute_backoff(ErrorCategory.RATE_LIMIT, 0)
            assert 0 <= wait <= 2.0

    def test_network_uses_fast_base(self):
        # attempt 0: base 0.5, so jitter range [0, 0.5]
        for _ in range(50):
            wait = compute_backoff(ErrorCategory.NETWORK, 0)
            assert 0 <= wait <= 0.5

    def test_capped_at_category_cap(self):
        # Even at high attempt counts, never exceeds the cap.
        for _ in range(50):
            assert compute_backoff(ErrorCategory.RATE_LIMIT, 10) <= 60.0
            assert compute_backoff(ErrorCategory.SERVER_ERROR, 10) <= 10.0
            assert compute_backoff(ErrorCategory.NETWORK, 10) <= 5.0

    def test_jitter_varies(self):
        """Full jitter should produce varying values (not fixed 2**attempt)."""
        values = {compute_backoff(ErrorCategory.SERVER_ERROR, 3) for _ in range(30)}
        # With full jitter over [0, 8], we should see many distinct values.
        assert len(values) > 10

    def test_retry_after_is_floor(self):
        """When Retry-After is provided, it should be respected as a floor."""
        for _ in range(20):
            wait = compute_backoff(ErrorCategory.RATE_LIMIT, 0, retry_after=30.0)
            assert wait >= 30.0

    def test_retry_after_zero_ignored(self):
        # retry_after of 0 should not pin the floor.
        wait = compute_backoff(ErrorCategory.SERVER_ERROR, 0, retry_after=0.0)
        assert wait <= 10.0

    def test_non_retryable_category_uses_default_config(self):
        # Falls back to server_error config (base 1.0, cap 10).
        wait = compute_backoff(ErrorCategory.NON_RETRYABLE, 0)
        assert 0 <= wait <= 1.0

    def test_never_negative(self):
        for cat in ErrorCategory:
            for attempt in range(5):
                assert compute_backoff(cat, attempt) >= 0


# ── Retry-After parsing ───────────────────────────────────────


class TestParseRetryAfter:
    def test_integer_seconds(self):
        assert parse_retry_after("120") == 120.0

    def test_float_seconds(self):
        assert parse_retry_after("2.5") == 2.5

    def test_none_returns_none(self):
        assert parse_retry_after(None) is None

    def test_empty_returns_none(self):
        assert parse_retry_after("") is None

    def test_garbage_returns_none(self):
        assert parse_retry_after("not-a-date-or-number") is None

    def test_negative_clamped_to_zero(self):
        assert parse_retry_after("-5") == 0.0

    def test_http_date_future(self):
        # A date ~2 minutes in the future.
        future = time.gmtime(time.time() + 120)
        date_str = time.strftime("%a, %d %b %Y %H:%M:%S GMT", future)
        result = parse_retry_after(date_str)
        assert result is not None
        assert 100 <= result <= 130  # ~120s, allow small drift

    def test_http_date_past_clamped_to_zero(self):
        past = time.gmtime(time.time() - 600)
        date_str = time.strftime("%a, %d %b %Y %H:%M:%S GMT", past)
        assert parse_retry_after(date_str) == 0.0


# ── Circuit breaker ───────────────────────────────────────────


class TestCircuitBreakerStates:
    def test_starts_closed(self):
        cb = CircuitBreaker(failure_threshold=3, recovery_timeout=60)
        assert cb.state == CircuitBreaker.CLOSED
        assert cb.allow_request() is True

    def test_stays_closed_below_threshold(self):
        cb = CircuitBreaker(failure_threshold=3)
        cb.record_failure()
        cb.record_failure()
        assert cb.state == CircuitBreaker.CLOSED
        assert cb.allow_request() is True

    def test_trips_open_at_threshold(self):
        cb = CircuitBreaker(failure_threshold=3)
        cb.record_failure()
        cb.record_failure()
        cb.record_failure()
        assert cb.state == CircuitBreaker.OPEN
        assert cb.allow_request() is False

    def test_success_resets_to_closed(self):
        cb = CircuitBreaker(failure_threshold=3)
        cb.record_failure()
        cb.record_failure()
        cb.record_success()
        assert cb.state == CircuitBreaker.CLOSED
        assert cb.failure_count == 0
        # Threshold should be back to full count after reset.
        cb.record_failure()
        assert cb.state == CircuitBreaker.CLOSED

    def test_reset_force_closes(self):
        cb = CircuitBreaker(failure_threshold=2)
        cb.record_failure()
        cb.record_failure()
        assert cb.state == CircuitBreaker.OPEN
        cb.reset()
        assert cb.state == CircuitBreaker.CLOSED
        assert cb.allow_request() is True


class TestCircuitBreakerRecovery:
    def test_transitions_to_half_open_after_cooldown(self):
        cb = CircuitBreaker(failure_threshold=2, recovery_timeout=0.1)
        cb.record_failure()
        cb.record_failure()
        assert cb.state == CircuitBreaker.OPEN
        time.sleep(0.15)
        # Reading state should trigger the transition.
        assert cb.state == CircuitBreaker.HALF_OPEN
        assert cb.allow_request() is True  # probe allowed

    def test_half_open_success_closes(self):
        cb = CircuitBreaker(failure_threshold=2, recovery_timeout=0.1)
        cb.record_failure()
        cb.record_failure()
        time.sleep(0.15)
        assert cb.state == CircuitBreaker.HALF_OPEN
        cb.record_success()
        assert cb.state == CircuitBreaker.CLOSED

    def test_half_open_failure_reopens(self):
        cb = CircuitBreaker(failure_threshold=2, recovery_timeout=0.1)
        cb.record_failure()
        cb.record_failure()
        time.sleep(0.15)
        assert cb.state == CircuitBreaker.HALF_OPEN
        # Probe fails.
        cb.record_failure()
        assert cb.state == CircuitBreaker.OPEN
        # And we're blocked again.
        assert cb.allow_request() is False

    def test_does_not_recover_before_cooldown(self):
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=10.0)
        cb.record_failure()
        assert cb.state == CircuitBreaker.OPEN
        # Well within cooldown.
        assert cb.allow_request() is False


class TestCircuitBreakerFailFast:
    """The breaker's whole point: when open, skip the network entirely."""

    def test_open_breaker_blocks_repeated_calls(self):
        cb = CircuitBreaker(failure_threshold=3, recovery_timeout=60)
        for _ in range(3):
            cb.record_failure()
        # Simulate a tool-calling loop making many calls while API is down.
        blocked = sum(1 for _ in range(50) if not cb.allow_request())
        assert blocked == 50  # all fail fast, no retries
