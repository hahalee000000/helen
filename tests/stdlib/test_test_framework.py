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
    _before_all,
    _after_all,
    _run_tests,
    _run_tests_json,
    _test_reset,
    _test_count,
    _test_suite,
    _test_case,
    _test_case_skip,
    _test_end_suite,
    _fail,
    _set_test_timeout,
    AssertionError,
    Expectation,
    TestRegistry,
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

    def test_reraises_framework_assertion_error(self):
        """Bug fix #3: assert_throws should NOT catch framework's AssertionError."""
        def failing():
            _assert_true(False, "inner assertion")

        with pytest.raises(AssertionError, match="inner assertion"):
            _assert_throws(failing)


class TestFail:
    """Tests for fail function (new)."""

    def test_fail_raises_assertion(self):
        with pytest.raises(AssertionError, match="explicit fail"):
            _fail("explicit fail")

    def test_fail_default_message(self):
        with pytest.raises(AssertionError, match="Test failed"):
            _fail()


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

    def test_toHaveProperty(self):
        """New matcher for dict/map key checking."""
        _expect({"name": "Alice", "age": 30}).toHaveProperty("name")
        with pytest.raises(AssertionError):
            _expect({"name": "Alice"}).toHaveProperty("missing")
        with pytest.raises(AssertionError, match="Expected a dict"):
            _expect("not a dict").toHaveProperty("key")

    def test_toThrow(self):
        def failing():
            raise ValueError("oops")

        _expect(failing).toThrow()
        _expect(failing).toThrow("ValueError")

    def test_toThrow_does_not_catch_framework_assertion(self):
        """Bug fix #3: toThrow should NOT catch framework's AssertionError."""
        def failing():
            _assert_true(False, "inner assertion")

        with pytest.raises(AssertionError, match="inner assertion"):
            _expect(failing).toThrow()

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

    def test_it_skip_with_none_fn(self):
        """Bug fix #2: it_skip should accept None as fn."""
        _describe("suite", lambda: _it_skip("skipped", None))
        assert _registry.suites[0].tests[0]["skip"] is True
        assert _registry.suites[0].tests[0]["fn"] is None

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

    def test_duplicate_test_name_warning(self):
        """Bug fix #4: duplicate test names should generate warning."""
        def suite():
            _it("same name", lambda: None)
            _it("same name", lambda: None)

        _describe("suite", suite)
        assert len(_registry.warnings) == 1
        assert "duplicate" in _registry.warnings[0].lower()


class TestHooks:
    """Tests for before_each/after_each/before_all/after_all hooks."""

    def setup_method(self):
        _registry.reset()

    def test_after_each_runs_on_failure(self):
        """Bug fix #1: after_each must run even when test fails."""
        cleanup_ran = {"value": False}

        def cleanup():
            cleanup_ran["value"] = True

        def failing_test():
            raise AssertionError("fail")

        _registry.start_suite("suite")
        _registry.set_after_each(cleanup)
        _registry.register_test("failing", failing_test)
        _registry.end_suite()

        report = _registry.run_all()
        assert report.failed == 1
        assert cleanup_ran["value"] is True  # after_each ran despite failure

    def test_before_all_runs_once(self):
        """New feature: before_all hook."""
        counter = {"value": 0}

        def setup():
            counter["value"] += 1

        def suite():
            _before_all(setup)
            _it("test1", lambda: None)
            _it("test2", lambda: None)
            _it("test3", lambda: None)

        _describe("suite", suite)
        _registry.run_all()
        assert counter["value"] == 1  # Ran once, not 3 times

    def test_after_all_runs_once(self):
        """New feature: after_all hook."""
        counter = {"value": 0}

        def teardown():
            counter["value"] += 1

        def suite():
            _after_all(teardown)
            _it("test1", lambda: None)
            _it("test2", lambda: None)

        _describe("suite", suite)
        _registry.run_all()
        assert counter["value"] == 1


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
            _it_skip("skipped", None)

        _describe("suite", suite)
        report = _registry.run_all()
        assert report.total == 1
        assert report.skipped == 1

    def test_run_tests_returns_formatted_report(self):
        def suite():
            _it("passes", lambda: None)

        _describe("suite", suite)
        result = _run_tests()
        report = result["report"]
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

    def test_run_tests_with_filter(self):
        """Bug fix #5: run_tests should accept filter parameters."""
        def suite():
            _it("test_add", lambda: None)
            _it("test_sub", lambda: None)
            _it("test_mul", lambda: None)

        _describe("suite", suite)
        result = _run_tests(filter_pattern="add")
        report = result["report"]
        assert "1 passed" in report


class TestRunAllFilters:
    """Tests for run_all filtering options."""

    def setup_method(self):
        _registry.reset()

    def test_run_all_with_only_filter(self):
        def suite():
            _it("test1", lambda: None)
            _it("test2", lambda: None)
            _it("test3", lambda: None)

        _describe("suite", suite)
        report = _registry.run_all(only="test2")
        assert report.total == 1
        assert report.results[0].name == "test2"

    def test_run_all_with_suite_filter(self):
        _registry.start_suite("suite1")
        _registry.register_test("test1", lambda: None)
        _registry.end_suite()

        _registry.start_suite("suite2")
        _registry.register_test("test2", lambda: None)
        _registry.end_suite()

        report = _registry.run_all(suite="suite2")
        assert report.total == 1
        assert report.results[0].suite == "suite2"

    def test_run_all_with_pattern_filter(self):
        def suite():
            _it("test_add", lambda: None)
            _it("test_subtract", lambda: None)
            _it("test_multiply", lambda: None)

        _describe("suite", suite)
        report = _registry.run_all(filter_pattern="add|multiply")
        assert report.total == 2
        names = [r.name for r in report.results]
        assert "test_add" in names
        assert "test_multiply" in names

    def test_run_all_with_combined_filters(self):
        _registry.start_suite("math")
        _registry.register_test("test_add", lambda: None)
        _registry.register_test("test_subtract", lambda: None)
        _registry.end_suite()

        _registry.start_suite("string")
        _registry.register_test("test_concat", lambda: None)
        _registry.end_suite()

        # Filter by suite and pattern
        report = _registry.run_all(suite="math", filter_pattern="add")
        assert report.total == 1
        assert report.results[0].name == "test_add"

    def test_run_all_no_matches(self):
        def suite():
            _it("test1", lambda: None)

        _describe("suite", suite)
        report = _registry.run_all(only="nonexistent")
        assert report.total == 0

    def test_run_all_pattern_case_insensitive(self):
        def suite():
            _it("TestAdd", lambda: None)
            _it("TESTSUBTRACT", lambda: None)

        _describe("suite", suite)
        report = _registry.run_all(filter_pattern="test")
        assert report.total == 2


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


class TestSimpleAPI:
    """Tests for test_suite/test_case/test_end_suite API."""

    def setup_method(self):
        _registry.reset()

    def test_simple_registration(self):
        _test_suite("My Suite")
        _test_case("test1", lambda: None)
        _test_case("test2", lambda: None)
        _test_end_suite()

        assert len(_registry.suites) == 1
        assert _registry.suites[0].name == "My Suite"
        assert len(_registry.suites[0].tests) == 2

    def test_case_skip_with_none(self):
        """Bug fix #2: test_case_skip should accept None."""
        _test_suite("Suite")
        _test_case_skip("skipped", None)
        _test_end_suite()

        assert _registry.suites[0].tests[0]["skip"] is True
        assert _registry.suites[0].tests[0]["fn"] is None


class TestTimeout:
    """Tests for test timeout functionality."""

    def setup_method(self):
        _registry.reset()

    def test_set_timeout(self):
        result = _set_test_timeout(5.0)
        assert "5.0" in result
        assert _registry._test_timeout == 5.0

    def test_timeout_minimum(self):
        _set_test_timeout(0.01)
        assert _registry._test_timeout >= 0.1
