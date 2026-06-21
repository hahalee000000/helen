"""Test framework module for Helen stdlib.

Provides describe/it/assert/expect for TDD-style testing of Helen programs.
"""

from __future__ import annotations

import signal
import time
import traceback
from dataclasses import dataclass, field
from typing import Any, Callable


# ── Test Result Types ──────────────────────────────────────────


@dataclass
class TestResult:
    """Result of a single test case."""
    name: str
    suite: str
    passed: bool
    error: str | None = None
    duration_ms: float = 0.0


@dataclass
class TestSuite:
    """A named group of test cases."""
    name: str
    tests: list[dict[str, Any]] = field(default_factory=list)
    before_each: Callable | None = None
    after_each: Callable | None = None
    before_all: Callable | None = None
    after_all: Callable | None = None


@dataclass
class TestReport:
    """Aggregated test results."""
    suites: list[TestSuite] = field(default_factory=list)
    results: list[TestResult] = field(default_factory=list)
    total: int = 0
    passed: int = 0
    failed: int = 0
    skipped: int = 0
    duration_ms: float = 0.0
    warnings: list[str] = field(default_factory=list)


# ── Global Test Registry ──────────────────────────────────────


class TestRegistry:
    """Global registry for test suites and cases."""

    def __init__(self) -> None:
        self._suites: list[TestSuite] = []
        self._current_suite: TestSuite | None = None
        self._results: list[TestResult] = []
        self._running = False
        self._warnings: list[str] = []
        self._test_timeout: float = 30.0  # seconds per test

    def reset(self) -> None:
        """Clear all registered tests and results."""
        self._suites.clear()
        self._current_suite = None
        self._results.clear()
        self._warnings.clear()
        self._running = False

    def start_suite(self, name: str) -> None:
        """Begin a new test suite (describe block)."""
        suite = TestSuite(name=name)
        self._suites.append(suite)
        self._current_suite = suite

    def end_suite(self) -> None:
        """End the current test suite."""
        self._current_suite = None

    def register_test(self, name: str, fn: Callable | None, skip: bool = False) -> None:
        """Register a test case (it block) in the current suite."""
        if self._current_suite is None:
            # Auto-create a default suite
            self.start_suite("(default)")
        assert self._current_suite is not None  # for type checker

        # Check for duplicate test names
        for existing in self._current_suite.tests:
            if existing["name"] == name:
                warning = f"Warning: duplicate test name '{name}' in suite '{self._current_suite.name}'"
                self._warnings.append(warning)
                break

        self._current_suite.tests.append({
            "name": name,
            "fn": fn,
            "skip": skip,
        })

    def set_before_each(self, fn: Callable) -> None:
        """Set before-each hook for current suite."""
        if self._current_suite is not None:
            self._current_suite.before_each = fn

    def set_after_each(self, fn: Callable) -> None:
        """Set after-each hook for current suite."""
        if self._current_suite is not None:
            self._current_suite.after_each = fn

    def set_before_all(self, fn: Callable) -> None:
        """Set before-all hook for current suite."""
        if self._current_suite is not None:
            self._current_suite.before_all = fn

    def set_after_all(self, fn: Callable) -> None:
        """Set after-all hook for current suite."""
        if self._current_suite is not None:
            self._current_suite.after_all = fn

    def set_timeout(self, seconds: float) -> None:
        """Set per-test timeout in seconds."""
        self._test_timeout = max(0.1, seconds)

    def run_all(
        self,
        only: str | None = None,
        suite: str | None = None,
        filter_pattern: str | None = None,
    ) -> TestReport:
        """Execute registered tests and return a report.

        Args:
            only: Run only the test with this exact name
            suite: Run only tests in the suite with this name
            filter_pattern: Run only tests whose name contains this pattern

        Returns:
            TestReport with results
        """
        import re

        self._running = True
        self._results.clear()
        start = time.monotonic()

        # Build filter regex if pattern provided
        filter_re = None
        if filter_pattern:
            try:
                filter_re = re.compile(filter_pattern, re.IGNORECASE)
            except re.error:
                # Fall back to substring match
                filter_re = None

        filtered_suites = []

        for s in self._suites:
            # Filter by suite name
            if suite and s.name != suite:
                continue

            filtered_tests = []
            for test in s.tests:
                test_name = test["name"]

                # Filter by exact test name
                if only and test_name != only:
                    continue

                # Filter by pattern
                if filter_pattern:
                    if filter_re:
                        if not filter_re.search(test_name):
                            continue
                    else:
                        if filter_pattern.lower() not in test_name.lower():
                            continue

                filtered_tests.append(test)

            if filtered_tests:
                # Create a filtered suite copy
                filtered_suite = TestSuite(
                    name=s.name,
                    tests=filtered_tests,
                    before_each=s.before_each,
                    after_each=s.after_each,
                    before_all=s.before_all,
                    after_all=s.after_all,
                )
                filtered_suites.append(filtered_suite)

                # Run before_all hook once
                if s.before_all is not None:
                    try:
                        s.before_all()
                    except Exception:
                        pass  # before_all failure doesn't stop tests

                for test in filtered_tests:
                    result = self._run_test(filtered_suite, test)
                    self._results.append(result)

                # Run after_all hook once
                if s.after_all is not None:
                    try:
                        s.after_all()
                    except Exception:
                        pass

        elapsed = (time.monotonic() - start) * 1000

        report = TestReport(
            suites=filtered_suites,
            results=self._results,
            total=len(self._results),
            passed=sum(1 for r in self._results if r.passed),
            failed=sum(1 for r in self._results if not r.passed and r.error != "SKIPPED"),
            skipped=sum(1 for r in self._results if r.error == "SKIPPED"),
            duration_ms=round(elapsed, 2),
            warnings=list(self._warnings),
        )
        self._running = False
        return report

    def _run_test(self, suite: TestSuite, test: dict) -> TestResult:
        """Run a single test case."""
        name = test["name"]
        fn = test["fn"]
        skip = test.get("skip", False)

        if skip or fn is None:
            return TestResult(
                name=name, suite=suite.name,
                passed=False, error="SKIPPED", duration_ms=0.0,
            )

        start = time.monotonic()
        try:
            # Run before_each hook
            if suite.before_each is not None:
                suite.before_each()

            # Run the test with timeout
            try:
                self._run_with_timeout(fn, self._test_timeout)
            except TimeoutError:
                elapsed = (time.monotonic() - start) * 1000
                return TestResult(
                    name=name, suite=suite.name,
                    passed=False,
                    error=f"Test timed out after {self._test_timeout}s",
                    duration_ms=round(elapsed, 2),
                )

            elapsed = (time.monotonic() - start) * 1000
            return TestResult(
                name=name, suite=suite.name,
                passed=True, duration_ms=round(elapsed, 2),
            )
        except AssertionError as e:
            elapsed = (time.monotonic() - start) * 1000
            return TestResult(
                name=name, suite=suite.name,
                passed=False, error=str(e) or "Assertion failed",
                duration_ms=round(elapsed, 2),
            )
        except Exception as e:
            elapsed = (time.monotonic() - start) * 1000
            tb = traceback.format_exc()
            return TestResult(
                name=name, suite=suite.name,
                passed=False, error=f"{type(e).__name__}: {e}\n{tb}",
                duration_ms=round(elapsed, 2),
            )
        finally:
            # Always run after_each hook, even on failure
            if suite.after_each is not None:
                try:
                    suite.after_each()
                except Exception:
                    pass  # after_each failure doesn't override test result

    def _run_with_timeout(self, fn: Callable, timeout: float) -> None:
        """Run a function with a timeout."""
        # Use signal-based timeout on Unix
        if hasattr(signal, 'SIGALRM'):
            def handler(signum: int, frame: Any) -> None:
                raise TimeoutError(f"Test timed out after {timeout}s")

            old_handler = signal.signal(signal.SIGALRM, handler)
            signal.setitimer(signal.ITIMER_REAL, timeout)
            try:
                fn()
            finally:
                signal.setitimer(signal.ITIMER_REAL, 0)
                signal.signal(signal.SIGALRM, old_handler)
        else:
            # Fallback: just run without timeout
            fn()

    @property
    def suites(self) -> list[TestSuite]:
        return list(self._suites)

    @property
    def results(self) -> list[TestResult]:
        return list(self._results)

    @property
    def warnings(self) -> list[str]:
        return list(self._warnings)


# Global registry instance
_registry = TestRegistry()


# ── Assertion Error ────────────────────────────────────────────


class AssertionError(Exception):
    """Raised when an assertion fails."""
    pass


# ── Expect API (chainable matchers) ───────────────────────────


class Expectation:
    """Chainable assertion builder returned by expect()."""

    def __init__(self, value: Any, negated: bool = False) -> None:
        self._value = value
        self._negated = negated

    def _check(self, condition: bool, message: str) -> None:
        """Assert condition, respecting negation."""
        actual = not condition if self._negated else condition
        if not actual:
            prefix = "NOT " if self._negated else ""
            raise AssertionError(f"{prefix}{message}")

    # ── Equality ──

    def toBe(self, expected: Any) -> "Expectation":
        """Assert strict equality."""
        eq = self._value == expected
        msg = f"Expected {self._value!r} to be {expected!r}"
        self._check(eq, msg)
        return self

    def toEqual(self, expected: Any) -> "Expectation":
        """Assert deep equality (same as toBe for Python)."""
        return self.toBe(expected)

    def toBeNone(self) -> "Expectation":
        """Assert value is None."""
        msg = f"Expected {self._value!r} to be None"
        self._check(self._value is None, msg)
        return self

    # ── Type checks ──

    def toBeTruthy(self) -> "Expectation":
        """Assert value is truthy."""
        msg = f"Expected {self._value!r} to be truthy"
        self._check(bool(self._value), msg)
        return self

    def toBeFalsy(self) -> "Expectation":
        """Assert value is falsy."""
        msg = f"Expected {self._value!r} to be falsy"
        self._check(not bool(self._value), msg)
        return self

    def toBeType(self, type_name: str) -> "Expectation":
        """Assert value is of given type."""
        actual_type = type(self._value).__name__
        msg = f"Expected {self._value!r} to be type '{type_name}', got '{actual_type}'"
        self._check(actual_type == type_name, msg)
        return self

    # ── Numeric ──

    def toBeGreaterThan(self, other: float) -> "Expectation":
        """Assert value > other."""
        msg = f"Expected {self._value!r} > {other!r}"
        self._check(self._value > other, msg)
        return self

    def toBeLessThan(self, other: float) -> "Expectation":
        """Assert value < other."""
        msg = f"Expected {self._value!r} < {other!r}"
        self._check(self._value < other, msg)
        return self

    def toBeGreaterThanOrEqual(self, other: float) -> "Expectation":
        """Assert value >= other."""
        msg = f"Expected {self._value!r} >= {other!r}"
        self._check(self._value >= other, msg)
        return self

    def toBeLessThanOrEqual(self, other: float) -> "Expectation":
        """Assert value <= other."""
        msg = f"Expected {self._value!r} <= {other!r}"
        self._check(self._value <= other, msg)
        return self

    def toBeCloseTo(self, expected: float, precision: int = 2) -> "Expectation":
        """Assert value is close to expected within precision decimal places."""
        threshold = 10 ** (-precision) / 2
        diff = abs(self._value - expected)
        msg = f"Expected {self._value!r} to be close to {expected!r} (diff={diff:.{precision}f}, threshold={threshold})"
        self._check(diff < threshold, msg)
        return self

    # ── String ──

    def toContain(self, item: Any) -> "Expectation":
        """Assert value contains item (substring or element)."""
        msg = f"Expected {self._value!r} to contain {item!r}"
        self._check(item in self._value, msg)
        return self

    def toMatch(self, pattern: str) -> "Expectation":
        """Assert string matches regex pattern."""
        import re
        msg = f"Expected {self._value!r} to match pattern {pattern!r}"
        self._check(bool(re.search(pattern, str(self._value))), msg)
        return self

    def toStartWith(self, prefix: str) -> "Expectation":
        """Assert string starts with prefix."""
        msg = f"Expected {self._value!r} to start with {prefix!r}"
        self._check(str(self._value).startswith(prefix), msg)
        return self

    def toEndWith(self, suffix: str) -> "Expectation":
        """Assert string ends with suffix."""
        msg = f"Expected {self._value!r} to end with {suffix!r}"
        self._check(str(self._value).endswith(suffix), msg)
        return self

    # ── Collection ──

    def toHaveLength(self, length: int) -> "Expectation":
        """Assert value has given length."""
        actual = len(self._value)
        msg = f"Expected length {length}, got {actual}"
        self._check(actual == length, msg)
        return self

    def toBeEmpty(self) -> "Expectation":
        """Assert value is empty."""
        msg = f"Expected {self._value!r} to be empty"
        self._check(len(self._value) == 0, msg)
        return self

    def toHaveProperty(self, key: str) -> "Expectation":
        """Assert dict/map has given key."""
        if not isinstance(self._value, dict):
            raise AssertionError(f"Expected a dict, got {type(self._value).__name__}")
        msg = f"Expected dict to have key {key!r}"
        self._check(key in self._value, msg)
        return self

    # ── Exception ──

    def toThrow(self, error_type: str | None = None) -> "Expectation":
        """Assert calling value() raises an exception.

        Note: Does NOT catch test framework's own AssertionError —
        only catches application-level exceptions.
        """
        if not callable(self._value):
            raise AssertionError(f"Expected a callable, got {type(self._value).__name__}")
        try:
            self._value()
            raised = False
            actual_error = None
        except AssertionError:
            # Re-raise framework's own assertion errors
            raise
        except Exception as e:
            raised = True
            actual_error = e

        if error_type:
            msg = f"Expected function to throw {error_type!r}"
            if raised:
                self._check(type(actual_error).__name__ == error_type,
                            f"{msg}, got {type(actual_error).__name__}: {actual_error}")
            else:
                raise AssertionError(f"{msg}, but no exception was thrown")
        else:
            msg = "Expected function to throw an exception"
            self._check(raised, msg)
        return self

    # ── Negation ──

    @property
    def not_(self) -> "Expectation":
        """Negate the next assertion."""
        return Expectation(self._value, negated=not self._negated)


# ── Stdlib Functions (registered in Helen) ─────────────────────


def _test_suite(name: str) -> str:
    """Start a new test suite.

    Args:
        name: Suite name

    Returns:
        Suite name
    """
    _registry.start_suite(name)
    return name


def _test_case(name: str, fn: Callable) -> str:
    """Register a test case in the current suite.

    Args:
        name: Test name
        fn: Test function (must be a named function)

    Returns:
        Test name
    """
    _registry.register_test(name, fn)
    return name


def _test_case_skip(name: str, fn: Callable | None = None) -> str:
    """Register a skipped test case.

    Args:
        name: Test name
        fn: Optional test function (will not be called). Can be null.

    Returns:
        Test name with [SKIP] prefix
    """
    _registry.register_test(name, fn, skip=True)
    return f"[SKIP] {name}"


def _test_end_suite() -> str:
    """End the current test suite.

    Returns:
        "suite ended"
    """
    _registry.end_suite()
    return "suite ended"


def _describe(name: str, fn: Callable) -> str:
    """Define a test suite.

    Args:
        name: Suite name
        fn: Function containing it() calls

    Returns:
        Suite name
    """
    _registry.start_suite(name)
    try:
        fn()
    finally:
        _registry.end_suite()
    return name


def _it(name: str, fn: Callable) -> str:
    """Define a test case within a describe block.

    Args:
        name: Test name
        fn: Test function

    Returns:
        Test name
    """
    _registry.register_test(name, fn)
    return name


def _it_skip(name: str, fn: Callable | None = None) -> str:
    """Define a skipped test case.

    Args:
        name: Test name
        fn: Optional test function (will not be called). Can be null.

    Returns:
        Test name with [SKIP] prefix
    """
    _registry.register_test(name, fn, skip=True)
    return f"[SKIP] {name}"


def _assert_true(condition: Any, message: str = "") -> bool:
    """Assert that condition is truthy.

    Args:
        condition: Value to check
        message: Optional error message

    Returns:
        True if assertion passes

    Raises:
        AssertionError: If condition is falsy
    """
    if not condition:
        msg = message or f"Assertion failed: {condition!r} is not truthy"
        raise AssertionError(msg)
    return True


def _assert_equal(actual: Any, expected: Any, message: str = "") -> bool:
    """Assert that actual == expected.

    Args:
        actual: Actual value
        expected: Expected value
        message: Optional error message

    Returns:
        True if assertion passes

    Raises:
        AssertionError: If values are not equal
    """
    if actual != expected:
        msg = message or f"Expected {expected!r}, got {actual!r}"
        raise AssertionError(msg)
    return True


def _assert_not_equal(actual: Any, expected: Any, message: str = "") -> bool:
    """Assert that actual != expected.

    Args:
        actual: Actual value
        expected: Expected value
        message: Optional error message

    Returns:
        True if assertion passes

    Raises:
        AssertionError: If values are equal
    """
    if actual == expected:
        msg = message or f"Expected values to differ, both are {actual!r}"
        raise AssertionError(msg)
    return True


def _assert_throws(fn: Callable, error_type: str = "") -> str:
    """Assert that calling fn raises an exception.

    Args:
        fn: Callable to test
        error_type: Optional expected exception type name

    Returns:
        The error message string

    Raises:
        AssertionError: If no exception is raised
    """
    try:
        fn()
    except AssertionError:
        # Re-raise framework's own assertion errors
        raise
    except Exception as e:
        if error_type and type(e).__name__ != error_type:
            raise AssertionError(
                f"Expected {error_type!r}, got {type(e).__name__}: {e}"
            ) from e
        return str(e)
    raise AssertionError("Expected function to throw, but it did not")


def _fail(message: str = "Test failed") -> None:
    """Explicitly fail a test with a message.

    Args:
        message: Failure message

    Raises:
        AssertionError: Always
    """
    raise AssertionError(message)


def _expect(value: Any) -> Expectation:
    """Create an expectation for chainable assertions.

    Args:
        value: Value to test

    Returns:
        Expectation object with chainable matchers

    Example:
        expect(add(2, 3)).toBe(5)
        expect("hello").toContain("ell")
        expect(len(items)).toBeGreaterThan(0)
    """
    return Expectation(value)


def _before_each(fn: Callable) -> str:
    """Register a before-each hook for the current suite.

    Args:
        fn: Function to run before each test

    Returns:
        "before_each registered"
    """
    _registry.set_before_each(fn)
    return "before_each registered"


def _after_each(fn: Callable) -> str:
    """Register an after-each hook for the current suite.

    Args:
        fn: Function to run after each test (always runs, even on failure)

    Returns:
        "after_each registered"
    """
    _registry.set_after_each(fn)
    return "after_each registered"


def _before_all(fn: Callable) -> str:
    """Register a before-all hook for the current suite.

    Args:
        fn: Function to run once before all tests in suite

    Returns:
        "before_all registered"
    """
    _registry.set_before_all(fn)
    return "before_all registered"


def _after_all(fn: Callable) -> str:
    """Register an after-all hook for the current suite.

    Args:
        fn: Function to run once after all tests in suite

    Returns:
        "after_all registered"
    """
    _registry.set_after_all(fn)
    return "after_all registered"


def _set_test_timeout(seconds: float) -> str:
    """Set per-test timeout in seconds.

    Args:
        seconds: Timeout in seconds (minimum 0.1)

    Returns:
        Confirmation message
    """
    _registry.set_timeout(seconds)
    return f"Test timeout set to {seconds}s"


def _run_tests(
    only: str = "",
    suite: str = "",
    filter_pattern: str = "",
) -> str:
    """Execute all registered tests and return a formatted report.

    Args:
        only: Run only the test with this exact name (empty = all)
        suite: Run only tests in this suite (empty = all)
        filter_pattern: Run only tests matching this pattern (empty = all)

    Returns:
        Formatted test report string
    """
    report = _registry.run_all(
        only=only or None,
        suite=suite or None,
        filter_pattern=filter_pattern or None,
    )
    return _format_report(report)


def _run_tests_json(
    only: str = "",
    suite: str = "",
    filter_pattern: str = "",
) -> str:
    """Execute all registered tests and return JSON results.

    Args:
        only: Run only the test with this exact name (empty = all)
        suite: Run only tests in this suite (empty = all)
        filter_pattern: Run only tests matching this pattern (empty = all)

    Returns:
        JSON string with test results
    """
    import json
    report = _registry.run_all(
        only=only or None,
        suite=suite or None,
        filter_pattern=filter_pattern or None,
    )
    data = {
        "total": report.total,
        "passed": report.passed,
        "failed": report.failed,
        "skipped": report.skipped,
        "duration_ms": report.duration_ms,
        "warnings": report.warnings,
        "suites": [
            {
                "name": s.name,
                "tests": len(s.tests),
            }
            for s in report.suites
        ],
        "results": [
            {
                "name": r.name,
                "suite": r.suite,
                "passed": r.passed,
                "error": r.error,
                "duration_ms": r.duration_ms,
            }
            for r in report.results
        ],
    }
    return json.dumps(data, ensure_ascii=False, indent=2)


def _test_reset() -> str:
    """Clear all registered tests and results.

    Returns:
        "Tests reset"
    """
    _registry.reset()
    return "Tests reset"


def _test_count() -> dict:
    """Return count of registered tests.

    Returns:
        Dict with suites, tests, results counts
    """
    return {
        "suites": len(_registry.suites),
        "tests": sum(len(s.tests) for s in _registry.suites),
        "results": len(_registry.results),
    }


# ── Report Formatting ─────────────────────────────────────────


def _format_report(report: TestReport) -> str:
    """Format a test report as a human-readable string."""
    lines = []
    lines.append("")
    lines.append("=" * 60)
    lines.append("  HELEN TEST RESULTS")
    lines.append("=" * 60)
    lines.append("")

    # Show warnings
    if report.warnings:
        for warning in report.warnings:
            lines.append(f"  ⚠ {warning}")
        lines.append("")

    for suite in report.suites:
        suite_results = [r for r in report.results if r.suite == suite.name]
        if not suite_results:
            continue

        lines.append(f"  {suite.name}")
        for r in suite_results:
            if r.error == "SKIPPED":
                lines.append(f"    ○ {r.name} (skipped)")
            elif r.passed:
                lines.append(f"    ✓ {r.name} ({r.duration_ms:.1f}ms)")
            else:
                lines.append(f"    ✗ {r.name}")
                # Show first line of error
                error_line = (r.error or "").split("\n")[0]
                lines.append(f"      → {error_line}")
        lines.append("")

    lines.append("-" * 60)
    lines.append(
        f"  {report.passed} passed, {report.failed} failed, "
        f"{report.skipped} skipped ({report.total} total)"
    )
    lines.append(f"  Duration: {report.duration_ms:.1f}ms")
    lines.append("=" * 60)

    if report.failed > 0:
        lines.append("  ✗ TESTS FAILED")
    else:
        lines.append("  ✓ ALL TESTS PASSED")
    lines.append("=" * 60)
    lines.append("")

    return "\n".join(lines)
