"""Tests for the coverage measurement module."""

import json
import tempfile
from pathlib import Path

import pytest

from helen.runtime.coverage import CoverageTracker, CoverageCount
from helen.core.source import SourceSpan


class TestCoverageCount:
    """Tests for CoverageCount dataclass."""

    def test_default_values(self):
        """CoverageCount starts with empty dicts."""
        cc = CoverageCount()
        assert cc.lines == {}
        assert cc.functions == {}
        assert cc.branches == {}

    def test_lines_tracking(self):
        """Lines can be tracked as counters."""
        cc = CoverageCount()
        cc.lines[1] += 1
        cc.lines[2] += 1
        cc.lines[1] += 1
        assert cc.lines[1] == 2
        assert cc.lines[2] == 1


class TestCoverageTracker:
    """Tests for CoverageTracker class."""

    def test_default_disabled(self):
        """Coverage tracker is disabled by default."""
        tracker = CoverageTracker()
        assert tracker.enabled is False

    def test_enable_disable(self):
        """Coverage tracker can be enabled and disabled."""
        tracker = CoverageTracker()
        tracker.enabled = True
        assert tracker.enabled is True
        tracker.enabled = False
        assert tracker.enabled is False

    def test_record_line_when_disabled(self):
        """Recording when disabled is a no-op."""
        tracker = CoverageTracker()
        span = SourceSpan("test.helen", 1, 1, 1, 10)
        tracker.record_line(span)
        summary = tracker.get_summary()
        assert summary["lines"]["total"] == 0

    def test_record_line_when_enabled(self):
        """Recording when enabled tracks line execution."""
        tracker = CoverageTracker()
        tracker.enabled = True
        span = SourceSpan("test.helen", 1, 1, 1, 10)
        tracker.record_line(span)
        tracker.record_line(span)  # Execute twice
        summary = tracker.get_summary()
        assert summary["lines"]["covered"] == 1

    def test_record_function(self):
        """Recording function calls tracks function coverage."""
        tracker = CoverageTracker()
        tracker.enabled = True
        span = SourceSpan("test.helen", 1, 1, 5, 1)
        tracker.record_function(span, "my_func")
        tracker.record_function(span, "my_func")  # Call twice
        summary = tracker.get_summary()
        assert summary["functions"]["covered"] == 1

    def test_record_branch(self):
        """Recording branches tracks branch coverage."""
        tracker = CoverageTracker()
        tracker.enabled = True
        span = SourceSpan("test.helen", 5, 1, 5, 20)
        tracker.record_branch(span, 1)  # Then branch
        tracker.record_branch(span, 0)  # Else branch
        summary = tracker.get_summary()
        assert summary["branches"]["covered"] == 2

    def test_register_source(self):
        """Source files can be registered for reporting."""
        tracker = CoverageTracker()
        source_lines = ["fn foo() {", "  return 1", "}"]
        tracker.register_source("test.helen", source_lines)
        # register_source converts to absolute path
        assert len(tracker._source_files) == 1
        assert "test.helen" in list(tracker._source_files.keys())[0]

    def test_register_function(self):
        """Functions can be registered for coverage denominator."""
        tracker = CoverageTracker()
        span = SourceSpan("test.helen", 1, 1, 3, 1)
        tracker.register_function(span, "foo")
        tracker.register_function(span, "bar")
        summary = tracker.get_summary()
        # Without calls, both are in denominator but not covered
        assert summary["functions"]["total"] == 2
        assert summary["functions"]["covered"] == 0

    def test_coverage_percentage(self):
        """Coverage percentage is calculated correctly."""
        tracker = CoverageTracker()
        tracker.enabled = True

        # Register 4 functions
        for i in range(4):
            span = SourceSpan("test.helen", i + 1, 1, i + 1, 10)
            tracker.register_function(span, f"func_{i}")

        # Call 2 of them
        tracker.record_function(SourceSpan("test.helen", 1, 1, 1, 10), "func_0")
        tracker.record_function(SourceSpan("test.helen", 2, 1, 2, 10), "func_1")

        summary = tracker.get_summary()
        assert summary["functions"]["percent"] == 50.0

    def test_reset(self):
        """Reset clears all coverage data."""
        tracker = CoverageTracker()
        tracker.enabled = True
        span = SourceSpan("test.helen", 1, 1, 1, 10)
        tracker.record_line(span)
        tracker.register_source("test.helen", ["line1"])
        tracker.reset()
        summary = tracker.get_summary()
        assert summary["lines"]["total"] == 0
        assert tracker._source_files == {}

    def test_clear(self):
        """Clear resets counters but keeps registrations."""
        tracker = CoverageTracker()
        tracker.enabled = True
        span = SourceSpan("test.helen", 1, 1, 1, 10)
        tracker.register_function(span, "foo")
        tracker.record_function(span, "foo")
        tracker.clear()
        summary = tracker.get_summary()
        # Function is still registered (denominator) but count is 0
        assert summary["functions"]["total"] == 1
        assert summary["functions"]["covered"] == 0

    def test_max_counters_limit(self):
        """Coverage tracker respects counter limit."""
        tracker = CoverageTracker(max_counters=5)
        tracker.enabled = True
        # Record more than max_counters lines
        for i in range(10):
            span = SourceSpan("test.helen", i + 1, 1, i + 1, 10)
            tracker.record_line(span)
        # Should have recorded up to the limit
        summary = tracker.get_summary()
        assert summary["lines"]["covered"] <= 5

    def test_generate_text_report(self):
        """Text report is generated correctly."""
        tracker = CoverageTracker()
        tracker.enabled = True
        span = SourceSpan("test.helen", 1, 1, 1, 10)
        tracker.record_line(span)
        report = tracker.generate_report("text")
        assert "HELEN COVERAGE REPORT" in report
        assert "Lines:" in report

    def test_generate_json_report(self):
        """JSON report is valid JSON."""
        tracker = CoverageTracker()
        tracker.enabled = True
        span = SourceSpan("test.helen", 1, 1, 1, 10)
        tracker.record_line(span)
        report = tracker.generate_report("json")
        data = json.loads(report)
        assert "summary" in data
        assert "files" in data

    def test_generate_html_report(self):
        """HTML report is valid HTML."""
        tracker = CoverageTracker()
        tracker.enabled = True
        span = SourceSpan("test.helen", 1, 1, 1, 10)
        tracker.record_line(span)
        tracker.register_source("test.helen", ["fn foo() {"])
        report = tracker.generate_report("html")
        assert "<!DOCTYPE html>" in report
        assert "Helen Coverage Report" in report

    def test_save_to_file_json(self):
        """Coverage can be saved to JSON file."""
        tracker = CoverageTracker()
        tracker.enabled = True
        span = SourceSpan("test.helen", 1, 1, 1, 10)
        tracker.record_line(span)
        with tempfile.TemporaryDirectory() as tmpdir:
            output = str(Path(tmpdir) / "coverage.json")
            tracker.save_to_file(output, format="json")
            assert Path(output).exists()
            data = json.loads(Path(output).read_text())
            assert "summary" in data

    def test_save_to_file_html(self):
        """Coverage can be saved to HTML file."""
        tracker = CoverageTracker()
        tracker.enabled = True
        span = SourceSpan("test.helen", 1, 1, 1, 10)
        tracker.record_line(span)
        with tempfile.TemporaryDirectory() as tmpdir:
            output = str(Path(tmpdir) / "index.html")
            tracker.save_to_file(output, format="html")
            assert Path(output).exists()
            content = Path(output).read_text()
            assert "<!DOCTYPE html>" in content

    def test_merge(self):
        """Coverage data from two trackers can be merged."""
        tracker1 = CoverageTracker()
        tracker1.enabled = True
        span1 = SourceSpan("test1.helen", 1, 1, 1, 10)
        tracker1.record_line(span1)

        tracker2 = CoverageTracker()
        tracker2.enabled = True
        span2 = SourceSpan("test2.helen", 1, 1, 1, 10)
        tracker2.record_line(span2)

        tracker1.merge(tracker2)
        summary = tracker1.get_summary()
        # Both files should be present
        assert summary["lines"]["covered"] == 2


class TestCoverageTrackerIntegration:
    """Integration tests for coverage tracking with interpreter."""

    def test_function_coverage_with_interpreter(self):
        """Function coverage is tracked through interpreter."""
        from helen.core.lexer import Scanner
        from helen.core.parser import Parser
        from helen.core.errors import ErrorReporter
        from helen.semantic.analyzer import SemanticAnalyzer
        from helen.interpreter.interpreter import Interpreter

        source = '''
fn add(a, b) {
    return a + b
}

fn test_add() {
    let result = add(1, 2)
    assert_equal(result, 3)
}

test_add()
'''
        errors = ErrorReporter()
        scanner = Scanner(source=source, file="test.helen")
        tokens = scanner.scan_all()
        parser = Parser(tokens, errors=errors)
        program = parser.parse()
        analyzer = SemanticAnalyzer(errors)
        analyzer.analyze(program)

        interp = Interpreter(errors=errors)
        interp.observability.coverage.enabled = True
        interp.observability.coverage.register_source("test.helen", source.splitlines())
        interp.interpret(program)

        summary = interp.observability.coverage.get_summary()
        # Both add and test_add should be covered
        assert summary["functions"]["covered"] == 2
        assert summary["functions"]["total"] == 2

    def test_branch_coverage_with_interpreter(self):
        """Branch coverage is tracked through interpreter."""
        from helen.core.lexer import Scanner
        from helen.core.parser import Parser
        from helen.core.errors import ErrorReporter
        from helen.semantic.analyzer import SemanticAnalyzer
        from helen.interpreter.interpreter import Interpreter

        source = '''
fn classify(x) {
    if x > 0 {
        return 1
    } else {
        return 0
    }
}

fn test_positive() {
    assert_equal(classify(5), 1)
}

fn test_negative() {
    assert_equal(classify(-3), 0)
}

test_positive()
test_negative()
'''
        errors = ErrorReporter()
        scanner = Scanner(source=source, file="test.helen")
        tokens = scanner.scan_all()
        parser = Parser(tokens, errors=errors)
        program = parser.parse()
        analyzer = SemanticAnalyzer(errors)
        analyzer.analyze(program)

        interp = Interpreter(errors=errors)
        interp.observability.coverage.enabled = True
        interp.interpret(program)

        summary = interp.observability.coverage.get_summary()
        # Both branches should be covered
        assert summary["branches"]["covered"] == 2
        assert summary["branches"]["total"] == 2

    def test_coverage_off_by_default(self):
        """Coverage tracking is off by default in interpreter."""
        from helen.core.lexer import Scanner
        from helen.core.parser import Parser
        from helen.core.errors import ErrorReporter
        from helen.interpreter.interpreter import Interpreter

        source = "fn foo() { return 1 }\nfoo()"
        errors = ErrorReporter()
        scanner = Scanner(source=source, file="test.helen")
        tokens = scanner.scan_all()
        parser = Parser(tokens, errors=errors)
        program = parser.parse()

        interp = Interpreter(errors=errors)
        # Coverage is disabled by default
        assert interp.observability.coverage.enabled is False
        interp.interpret(program)
        # No coverage data recorded
        summary = interp.observability.coverage.get_summary()
        assert summary["functions"]["covered"] == 0


class TestCoverageStdlib:
    """Tests for coverage stdlib functions."""

    def test_coverage_on_off(self):
        """coverage_on and coverage_off stdlib functions work."""
        from helen.stdlib import _coverage_on, _coverage_off, _interpreter_observability
        from helen.runtime.observability import ObservabilityManager
        from helen.stdlib import _set_interpreter_observability

        # Set up mock observability
        obs = ObservabilityManager()
        _set_interpreter_observability(obs)

        try:
            result = _coverage_on()
            assert "enabled" in result
            assert obs.coverage.enabled is True

            result = _coverage_off()
            assert "disabled" in result
            assert obs.coverage.enabled is False
        finally:
            _set_interpreter_observability(None)

    def test_coverage_summary(self):
        """coverage_summary stdlib function returns summary."""
        from helen.stdlib import _coverage_summary
        from helen.runtime.observability import ObservabilityManager
        from helen.stdlib import _set_interpreter_observability

        obs = ObservabilityManager()
        _set_interpreter_observability(obs)

        try:
            result = _coverage_summary()
            assert "Coverage:" in result
            assert "Lines" in result
            assert "Functions" in result
        finally:
            _set_interpreter_observability(None)
