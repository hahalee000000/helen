"""Integration tests for HttpLLMRuntime retry with circuit breaker + layered backoff.

These verify that ``_chat_with_messages_retry`` correctly orchestrates the
resilience primitives in ``helen.runtime.resilience``: circuit-breaker fail-fast,
layered backoff with jitter, and Retry-After header honoring.
"""

from __future__ import annotations

from unittest.mock import patch

from helen.runtime.http_llm import HttpLLMRuntime
from helen.runtime.resilience import CircuitBreaker


def _make_runtime(max_retries: int = 3, threshold: int = 5) -> HttpLLMRuntime:
    """Build a runtime without hitting ``__post_init__``'s config/network setup."""
    runtime = HttpLLMRuntime(base_url="http://localhost", api_key="k")
    runtime.max_retries = max_retries
    runtime._circuit_breaker = CircuitBreaker(
        failure_threshold=threshold, recovery_timeout=60.0,
    )
    return runtime


class TestRetryFailFast:
    """When the breaker is open, the retry method should not call the API at all."""

    def test_open_breaker_skips_api_call(self):
        runtime = _make_runtime(max_retries=3)
        # Trip the breaker manually.
        for _ in range(5):
            runtime._circuit_breaker.record_failure()
        assert runtime._circuit_breaker.state == CircuitBreaker.OPEN

        call_count = 0

        def fake_chat(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            return {"content": "should not reach here"}

        with patch.object(runtime, "_chat_with_messages", side_effect=fake_chat):
            result = runtime._chat_with_messages_retry([{"role": "user", "content": "hi"}])

        assert result is None
        assert call_count == 0  # breaker prevented the call entirely
        assert "Circuit breaker open" in (runtime._last_error or "")


class TestRetryLayeredBackoff:
    """Retryable errors should be classified and backed off with jitter."""

    def test_429_retries_then_succeeds(self):
        runtime = _make_runtime(max_retries=3)
        attempts = 0

        def flaky_chat(*args, **kwargs):
            nonlocal attempts
            attempts += 1
            if attempts < 3:
                runtime._last_status_code = 429
                runtime._last_retry_after = 0.0  # don't actually wait
                runtime._last_error = "API error (429 rate_limited): slow down"
                return None
            runtime._last_status_code = None
            runtime._last_error = None
            return {"content": "ok"}

        with patch.object(runtime, "_chat_with_messages", side_effect=flaky_chat):
            with patch("helen.runtime.http_llm.time.sleep") as mock_sleep:
                result = runtime._chat_with_messages_retry([{"role": "user", "content": "hi"}])

        assert result == {"content": "ok"}
        assert attempts == 3
        # Should have slept between the failed attempts.
        assert mock_sleep.call_count == 2
        # Breaker should be closed again after success.
        assert runtime._circuit_breaker.state == CircuitBreaker.CLOSED

    def test_500_retries_with_backoff(self):
        runtime = _make_runtime(max_retries=2)

        def always_500(*args, **kwargs):
            runtime._last_status_code = 500
            runtime._last_retry_after = None
            runtime._last_error = "API error (500): internal"
            return None

        with patch.object(runtime, "_chat_with_messages", side_effect=always_500):
            with patch("helen.runtime.http_llm.time.sleep") as mock_sleep:
                result = runtime._chat_with_messages_retry([{"role": "user", "content": "hi"}])

        assert result is None
        # max_retries=2 -> 3 total attempts -> 2 sleeps.
        assert mock_sleep.call_count == 2
        # Each sleep should be within the server-error cap (10s) since no Retry-After.
        for call in mock_sleep.call_args_list:
            wait = call.args[0]
            assert 0 <= wait <= 10.0

    def test_400_non_retryable_no_retry(self):
        runtime = _make_runtime(max_retries=3)
        attempts = 0

        def bad_request(*args, **kwargs):
            nonlocal attempts
            attempts += 1
            runtime._last_status_code = 400
            runtime._last_retry_after = None
            runtime._last_error = "API error (400): bad request"
            return None

        with patch.object(runtime, "_chat_with_messages", side_effect=bad_request):
            with patch("helen.runtime.http_llm.time.sleep") as mock_sleep:
                result = runtime._chat_with_messages_retry([{"role": "user", "content": "hi"}])

        assert result is None
        assert attempts == 1  # 4xx not retried
        assert mock_sleep.call_count == 0

    def test_retry_after_respected_as_floor(self):
        runtime = _make_runtime(max_retries=1)

        def rate_limited(*args, **kwargs):
            runtime._last_status_code = 429
            runtime._last_retry_after = 5.0  # server says wait 5s
            runtime._last_error = "API error (429): slow down"
            return None

        with patch.object(runtime, "_chat_with_messages", side_effect=rate_limited):
            with patch("helen.runtime.http_llm.time.sleep") as mock_sleep:
                runtime._chat_with_messages_retry([{"role": "user", "content": "hi"}])

        assert mock_sleep.call_count == 1
        wait = mock_sleep.call_args.args[0]
        # Retry-After (5s) is the floor; with jitter it should be >= 5.
        assert wait >= 5.0
        # But capped at 120s.
        assert wait <= 120.0


class TestRetryBreakerTripping:
    """Sustained failures should trip the breaker so subsequent calls fail fast."""

    def test_breaker_trips_after_threshold(self):
        # threshold=2, max_retries=0 so each retry call = 1 attempt = 1 failure.
        runtime = _make_runtime(max_retries=0, threshold=2)

        def always_fail(*args, **kwargs):
            runtime._last_status_code = 500
            runtime._last_retry_after = None
            runtime._last_error = "API error (500): down"
            return None

        with patch.object(runtime, "_chat_with_messages", side_effect=always_fail):
            with patch("helen.runtime.http_llm.time.sleep"):
                # First call: 1 failure, breaker still closed (threshold=2).
                runtime._chat_with_messages_retry([{"role": "user", "content": "1"}])
                assert runtime._circuit_breaker.state == CircuitBreaker.CLOSED
                # Second call: 2nd failure, breaker trips.
                runtime._chat_with_messages_retry([{"role": "user", "content": "2"}])
                assert runtime._circuit_breaker.state == CircuitBreaker.OPEN
                # Third call: breaker open -> fail fast, no API call.
                call_count = 0

                def counting(*a, **kw):
                    nonlocal call_count
                    call_count += 1
                    return None

                with patch.object(runtime, "_chat_with_messages", side_effect=counting):
                    result = runtime._chat_with_messages_retry(
                        [{"role": "user", "content": "3"}],
                    )
                assert result is None
                assert call_count == 0  # fail fast

    def test_success_resets_failure_count(self):
        runtime = _make_runtime(max_retries=0, threshold=3)

        def fail_then_succeed(state):
            def chat(*args, **kwargs):
                if state["fail"]:
                    runtime._last_status_code = 500
                    runtime._last_retry_after = None
                    runtime._last_error = "500"
                    return None
                runtime._last_status_code = None
                runtime._last_error = None
                return {"content": "ok"}
            return chat

        state = {"fail": True}
        with patch.object(runtime, "_chat_with_messages", side_effect=fail_then_succeed(state)):
            with patch("helen.runtime.http_llm.time.sleep"):
                # Two failures (below threshold of 3).
                runtime._chat_with_messages_retry([{"role": "user", "content": "1"}])
                runtime._chat_with_messages_retry([{"role": "user", "content": "2"}])
                assert runtime._circuit_breaker.failure_count == 2
                # Now succeed - should reset.
                state["fail"] = False
                runtime._chat_with_messages_retry([{"role": "user", "content": "3"}])
                assert runtime._circuit_breaker.failure_count == 0
                assert runtime._circuit_breaker.state == CircuitBreaker.CLOSED
