"""Tests for the Helen test framework stdlib module."""

import pytest
from helen.stdlib.test import (
    _registry,
    _describe,
    _it,
    _it_skip,
    _assert_true,
    _assert_equal,
    _assert_not_equal,
    _assert_throws,
    _expect,
    _before_each,
    _after_each,
    _run_tests,
    _run_tests_json,
    _test_reset,
    _test_count,
    AssertionError,
    Expectation,
)


class TestAssertTrue:
    """Tests for assert_true function."""

    def test_passes_with_truthy_value(self):
        assert _assert_true(True) is True
        assert _assert_true(1) is True
        assert _assert_true("hello") is True
        assert _assert_true([1, 2]) is True

    def test_fails_with_falsy_value(self):
        with pytest.raises(AssertionError):
            _assert_true(False)
        with pytest.raises(AssertionError):
            _assert_true(0)
        with pytest.raises(AssertionError):
            _assert_true("")
        with pytest.raises(AssertionError):
            _assert_true([])

    def test_custom_message(self):
        with pytest.raises(AssertionError, match="custom error"):
            _assert_true(False, "custom error")


class TestAssertEqual:
    """Tests for assert_equal function."""

    def test_passes_with_equal_values(self):
        assert _assert_equal(1, 1) is True
        assert _assert_equal("hello", "hello") is True
        assert _assert_equal([1, 2], [1, 2]) is True
        assert _assert_equal({"a": 1}, {"a": 1}) is True

    def test_fails_with_unequal_values(self):
        with pytest.raises(AssertionError):
            _assert_equal(1, 2)
        with pytest.raises(AssertionError):
            _assert_equal("hello", "world")

    def test_custom_message(self):
        with pytest.raises(AssertionError, match="values differ"):
            _assert_equal(1, 2, "values differ")


class TestAssertNotEqual:
    """Tests for assert_not_equal function."""

    def test_passes_with_different_values(self):
        assert _assert_not_equal(1, 2) is True
        assert _assert_not_equal("hello", "world") is True

    def test_fails_with_equal_values(self):
        with pytest.raises(AssertionError):
            _assert_not_equal(1, 1)
        with pytest.raises(AssertionError):
            _assert_not_equal("hello", "hello")


class TestAssertThrows:
    """Tests for assert_throws function."""

    def test_passes_when_exception_raised(self):
        def failing():
            raise ValueError("oops")

        result = _assert_throws(failing)
        assert result == "oops"

    def test_fails_when_no_exception(self):
        def passing():
            return 42

        with pytest.raises(AssertionError, match="did not"):
            _assert_throws(passing)

    def test_checks_error_type(self):
        def failing():
            raise ValueError("oops")

        result = _assert_throws(failing, "ValueError")
        assert result == "oops"

    def test_fails_with_wrong_error_type(self):
        def failing():
            raise ValueError("oops")

        with pytest.raises(AssertionError, match="Expected .TypeError."):
            _assert_throws(failing, "TypeError")


class TestExpectation:
    """Tests for expect() chainable assertions."""

    def test_toBe(self):
        _expect(5).toBe(5)
        _expect("hello").toBe("hello")
        with pytest.raises(AssertionError):
            _expect(5).toBe(6)

    def test_toEqual(self):
        _expect([1, 2]).toEqual([1, 2])
        with pytest.raises(AssertionError):
            _expect([1, 2]).toEqual([1, 3])

    def test_toBeNone(self):
        _expect(None).toBeNone()
        with pytest.raises(AssertionError):
            _expect(42).toBeNone()

    def test_toBeTruthy(self):
        _expect(1).toBeTruthy()
        _expect("hello").toBeTruthy()
        with pytest.raises(AssertionError):
            _expect(0).toBeTruthy()

    def test_toBeFalsy(self):
        _expect(0).toBeFalsy()
        _expect("").toBeFalsy()
        _expect(None).toBeFalsy()
        with pytest.raises(AssertionError):
            _expect(1).toBeFalsy()

    def test_toBeType(self):
        _expect(42).toBeType("int")
        _expect("hello").toBeType("str")
        with pytest.raises(AssertionError):
            _expect(42).toBeType("str")

    def test_toBeGreaterThan(self):
        _expect(10).toBeGreaterThan(5)
        with pytest.raises(AssertionError):
            _expect(5).toBeGreaterThan(10)

    def test_toBeLessThan(self):
        _expect(5).toBeLessThan(10)
        with pytest.raises(AssertionError):
            _expect(10).toBeLessThan(5)

    def test_toBeCloseTo(self):
        _expect(3.14159).toBeCloseTo(3.14, 2)
        with pytest.raises(AssertionError):
            _expect(3.14159).toBeCloseTo(3.0, 2)

    def test_toContain(self):
        _expect("hello world").toContain("world")
        _expect([1, 2, 3]).toContain(2)
        with pytest.raises(AssertionError):
            _expect("hello").toContain("xyz")

    def test_toMatch(self):
        _expect("hello123").toMatch(r"\d+")
        with pytest.raises(AssertionError):
            _expect("hello").toMatch(r"\d+")

    def test_toStartWith(self):
        _expect("hello world").toStartWith("hello")
        with pytest.raises(AssertionError):
            _expect("hello").toStartWith("world")

    def test_toEndWith(self):
        _expect("hello world").toEndWith("world")
        with pytest.raises(AssertionError):
            _expect("hello").toEndWith("world")

    def test_toHaveLength(self):
        _expect([1, 2, 3]).toHaveLength(3)
        _expect("hello").toHaveLength(5)
        with pytest.raises(AssertionError):
            _expect([1, 2]).toHaveLength(3)

    def test_toBeEmpty(self):
        _expect([]).toBeEmpty()
        _expect("").toBeEmpty()
        with pytest.raises(AssertionError):
            _expect([1]).toBeEmpty()

    def test_toThrow(self):
        def failing():
            raise ValueError("oops")

        _expect(failing).toThrow()
        _expect(failing).toThrow("ValueError")

    def test_not_negation(self):
        _expect(5).not_.toBe(6)
        _expect("hello").not_.toContain("xyz")
        with pytest.raises(AssertionError):
            _expect(5).not_.toBe(5)

    def test_chaining(self):
        _expect("hello world").toContain("hello").toContain("world").toStartWith("hello")


class TestDescribeIt:
    """Tests for describe/it test structure."""

    def setup_method(self):
        _registry.reset()

    def test_describe_creates_suite(self):
        _describe("my suite", lambda: None)
        assert len(_registry.suites) == 1
        assert _registry.suites[0].name == "my suite"

    def test_it_registers_test(self):
        _describe("suite", lambda: _it("test1", lambda: None))
        assert len(_registry.suites[0].tests) == 1
        assert _registry.suites[0].tests[0]["name"] == "test1"

    def test_it_skip_marks_skipped(self):
        _describe("suite", lambda: _it_skip("skipped", lambda: None))
        assert _registry.suites[0].tests[0]["skip"] is True

    def test_nested_describe(self):
        def outer():
            _it("outer test", lambda: None)
            _describe("inner", lambda: _it("inner test", lambda: None))

        _describe("outer", outer)
        assert len(_registry.suites) == 2

    def test_auto_suite_when_no_describe(self):
        _it("standalone test", lambda: None)
        assert len(_registry.suites) == 1
        assert _registry.suites[0].name == "(default)"


class TestRunTests:
    """Tests for test execution and reporting."""

    def setup_method(self):
        _registry.reset()

    def test_run_passing_tests(self):
        def suite():
            _it("passes", lambda: None)

        _describe("suite", suite)
        report = _registry.run_all()
        assert report.total == 1
        assert report.passed == 1
        assert report.failed == 0

    def test_run_failing_tests(self):
        def failing():
            raise AssertionError("fail")

        def suite():
            _it("fails", failing)

        _describe("suite", suite)
        report = _registry.run_all()
        assert report.total == 1
        assert report.passed == 0
        assert report.failed == 1

    def test_run_skipped_tests(self):
        def suite():
            _it_skip("skipped", lambda: None)

        _describe("suite", suite)
        report = _registry.run_all()
        assert report.total == 1
        assert report.skipped == 1

    def test_before_each_hook(self):
        counter = {"value": 0}

        def increment():
            counter["value"] += 1

        def suite():
            _before_each(increment)
            _it("test1", lambda: None)
            _it("test2", lambda: None)

        _describe("suite", suite)
        _registry.run_all()
        assert counter["value"] == 2

    def test_after_each_hook(self):
        counter = {"value": 0}

        def increment():
            counter["value"] += 1

        def suite():
            _after_each(increment)
            _it("test1", lambda: None)
            _it("test2", lambda: None)

        _describe("suite", suite)
        _registry.run_all()
        assert counter["value"] == 2

    def test_run_tests_returns_formatted_report(self):
        def suite():
            _it("passes", lambda: None)

        _describe("suite", suite)
        report = _run_tests()
        assert "HELEN TEST RESULTS" in report
        assert "1 passed" in report
        assert "ALL TESTS PASSED" in report

    def test_run_tests_json_returns_json(self):
        import json

        def suite():
            _it("passes", lambda: None)

        _describe("suite", suite)
        result = _run_tests_json()
        data = json.loads(result)
        assert data["total"] == 1
        assert data["passed"] == 1
        assert data["failed"] == 0


class TestTestCount:
    """Tests for test_count function."""

    def setup_method(self):
        _registry.reset()

    def test_empty_registry(self):
        count = _test_count()
        assert count["suites"] == 0
        assert count["tests"] == 0
        assert count["results"] == 0

    def test_with_registered_tests(self):
        def suite():
            _it("test1", lambda: None)
            _it("test2", lambda: None)

        _describe("suite", suite)
        count = _test_count()
        assert count["suites"] == 1
        assert count["tests"] == 2


class TestTestReset:
    """Tests for test_reset function."""

    def test_reset_clears_everything(self):
        def suite():
            _it("test", lambda: None)

        _describe("suite", suite)
        _registry.run_all()

        result = _test_reset()
        assert result == "Tests reset"
        count = _test_count()
        assert count["suites"] == 0
        assert count["tests"] == 0
        assert count["results"] == 0
