"""Tests for the Helen quality assessment stdlib module."""

import pytest
from helen.stdlib.quality import (
    HelenCodeAnalyzer,
    SecurityAnalyzer,
    QualityScorer,
    QualityScore,
    _analyze_code,
    _check_security,
    _quality_score,
    _quality_report,
)


class TestHelenCodeAnalyzer:
    """Tests for HelenCodeAnalyzer."""

    def test_basic_metrics(self):
        source = """
// This is a comment
fn add(a, b) {
    return a + b
}

fn subtract(a, b) {
    return a - b
}
"""
        analyzer = HelenCodeAnalyzer(source, "test.helen")
        metrics = analyzer.analyze()

        assert metrics.function_count == 2
        assert metrics.total_lines > 0
        assert metrics.code_lines > 0
        assert metrics.comment_lines >= 1

    def test_function_analysis(self):
        source = """
fn simple() {
    return 42
}

fn complex_fn(x, y, z) {
    if x > 0 {
        if y > 0 {
            return x + y
        }
    }
    return z
}
"""
        analyzer = HelenCodeAnalyzer(source)
        metrics = analyzer.analyze()

        assert metrics.function_count == 2

        simple_fn = next(f for f in metrics.functions if f.name == "simple")
        assert simple_fn.param_count == 0
        assert simple_fn.line_count > 0

        complex_fn = next(f for f in metrics.functions if f.name == "complex_fn")
        assert complex_fn.param_count == 3
        assert complex_fn.complexity > 1
        assert complex_fn.max_nesting >= 2

    def test_comment_ratio(self):
        source = """
// Comment 1
// Comment 2
// Comment 3
fn test() {
    return 1
}
"""
        analyzer = HelenCodeAnalyzer(source)
        metrics = analyzer.analyze()

        assert metrics.comment_lines == 3
        assert metrics.comment_ratio > 0

    def test_agent_count(self):
        source = """
agent MyAgent {
    description: "Test agent"
}

agent AnotherAgent {
    description: "Another"
}

fn helper() {
    return 42
}
"""
        analyzer = HelenCodeAnalyzer(source)
        metrics = analyzer.analyze()

        assert metrics.agent_count == 2
        assert metrics.function_count == 1

    def test_complexity_calculation(self):
        source = """
fn complex(x) {
    if x > 0 {
        for i in range(x) {
            if i % 2 == 0 {
                print(i)
            }
        }
    } else if x < 0 {
        return -1
    }
    return 0
}
"""
        analyzer = HelenCodeAnalyzer(source)
        metrics = analyzer.analyze()

        fn = metrics.functions[0]
        # Should have complexity > 1 due to if/for/else if
        assert fn.complexity >= 4


class TestSecurityAnalyzer:
    """Tests for SecurityAnalyzer."""

    def test_detects_eval(self):
        source = """
fn dangerous() {
    let result = eval(user_input)
    return result
}
"""
        analyzer = SecurityAnalyzer(source)
        issues = analyzer.analyze()

        assert len(issues) > 0
        assert any("eval" in i.pattern for i in issues)

    def test_detects_shell_true(self):
        source = """
fn run_cmd(cmd) {
    exec(cmd, shell = true)
}
"""
        analyzer = SecurityAnalyzer(source)
        issues = analyzer.analyze()

        assert len(issues) > 0
        assert any("shell" in i.pattern.lower() for i in issues)

    def test_ignores_comments(self):
        source = """
// eval() is dangerous
// shell = true is bad
fn safe() {
    return 42
}
"""
        analyzer = SecurityAnalyzer(source)
        issues = analyzer.analyze()

        # Should not detect patterns in comments
        assert len(issues) == 0

    def test_detects_user_input(self):
        source = """
fn get_name() {
    let name = input("Enter name: ")
    return name
}
"""
        analyzer = SecurityAnalyzer(source)
        issues = analyzer.analyze()

        assert len(issues) > 0
        assert any("input" in i.pattern for i in issues)


class TestQualityScorer:
    """Tests for QualityScorer."""

    def test_architecture_score(self):
        from helen.stdlib.quality import CodeMetrics, FunctionMetrics

        scorer = QualityScorer()

        # Good architecture
        good_metrics = CodeMetrics(
            function_count=3,
            functions=[
                FunctionMetrics("fn1", 1, 10, 10, 2, 1, True, 2),
                FunctionMetrics("fn2", 11, 20, 10, 2, 1, True, 2),
                FunctionMetrics("fn3", 21, 30, 10, 2, 1, True, 2),
            ],
            max_function_length=10,
            max_complexity=2,
        )
        score = scorer.score_architecture(good_metrics)
        assert score >= 8.0

        # Bad architecture
        bad_metrics = CodeMetrics(
            function_count=1,
            functions=[
                FunctionMetrics("long_fn", 1, 200, 200, 10, 8, False, 25),
            ],
            max_function_length=200,
            max_complexity=25,
        )
        score = scorer.score_architecture(bad_metrics)
        assert score < 5.0

    def test_security_score(self):
        from helen.stdlib.quality import SecurityIssue

        scorer = QualityScorer()

        # No issues
        score = scorer.score_security([])
        assert score == 10.0

        # High severity issues
        issues = [
            SecurityIssue(1, "high", "eval()", "dangerous"),
            SecurityIssue(5, "high", "exec()", "dangerous"),
        ]
        score = scorer.score_security(issues)
        assert score < 5.0

    def test_documentation_score(self):
        from helen.stdlib.quality import CodeMetrics, FunctionMetrics

        scorer = QualityScorer()

        # All documented
        good_metrics = CodeMetrics(
            function_count=3,
            functions=[
                FunctionMetrics("fn1", 1, 10, 10, 2, 1, True, 2),
                FunctionMetrics("fn2", 11, 20, 10, 2, 1, True, 2),
                FunctionMetrics("fn3", 21, 30, 10, 2, 1, True, 2),
            ],
        )
        score = scorer.score_documentation(good_metrics)
        assert score == 10.0

        # None documented
        bad_metrics = CodeMetrics(
            function_count=3,
            functions=[
                FunctionMetrics("fn1", 1, 10, 10, 2, 1, False, 2),
                FunctionMetrics("fn2", 11, 20, 10, 2, 1, False, 2),
                FunctionMetrics("fn3", 21, 30, 10, 2, 1, False, 2),
            ],
        )
        score = scorer.score_documentation(bad_metrics)
        assert score == 0.0

    def test_grade_assignment(self):
        scorer = QualityScorer()

        assert scorer.assign_grade(9.5) == "S"
        assert scorer.assign_grade(8.0) == "A"
        assert scorer.assign_grade(6.5) == "B"
        assert scorer.assign_grade(5.0) == "C"
        assert scorer.assign_grade(3.0) == "D"


class TestStdlibFunctions:
    """Tests for stdlib functions."""

    def test_analyze_code(self):
        source = """
fn add(a, b) {
    return a + b
}
"""
        result = _analyze_code(source, "test.helen")

        assert "total_lines" in result
        assert "function_count" in result
        assert result["function_count"] == 1
        assert "functions" in result
        assert len(result["functions"]) == 1

    def test_check_security(self):
        source = """
fn dangerous() {
    let x = eval("1+1")
    return x
}
"""
        issues = _check_security(source)

        assert len(issues) > 0
        assert issues[0]["severity"] in ["high", "medium", "low"]

    def test_quality_score(self):
        source = """
// A well-documented function
fn add(a, b) {
    // Add two numbers
    return a + b
}
"""
        score = _quality_score(source, "test.helen")

        assert "architecture" in score
        assert "code_quality" in score
        assert "security" in score
        assert "total" in score
        assert "grade" in score
        assert 0 <= score["total"] <= 10

    def test_quality_report(self):
        source = """
fn test() {
    return 42
}
"""
        report = _quality_report(source, "test.helen")

        assert "HELEN QUALITY REPORT" in report
        assert "test.helen" in report
        assert "Quality Scores" in report
        assert "GRADE" in report
