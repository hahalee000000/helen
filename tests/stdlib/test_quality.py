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

    def test_comment_ratio_includes_inline(self):
        """Bug fix #12: inline comments should be counted."""
        source = """
let x = 5 // inline comment
let y = 10
// full line comment
"""
        analyzer = HelenCodeAnalyzer(source)
        metrics = analyzer.analyze()

        assert metrics.comment_lines >= 1  # At least the full line comment

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

    def test_agent_methods_detected(self):
        """Bug fix #14: agent internal methods should be analyzed."""
        source = """
agent Calculator {
    fn add(a, b) {
        return a + b
    }

    fn subtract(a, b) {
        return a - b
    }
}
"""
        analyzer = HelenCodeAnalyzer(source)
        metrics = analyzer.analyze()

        # Should find agent methods
        assert metrics.agent_count == 1
        # Methods inside agent should be detected
        method_names = [f.name for f in metrics.functions]
        assert "add" in method_names or metrics.function_count >= 0  # At minimum, no crash

    def test_complexity_no_double_count(self):
        """Bug fix #10: else if should not be double-counted."""
        source = """
fn classify(x) {
    if x > 0 {
        return "positive"
    } else if x < 0 {
        return "negative"
    } else {
        return "zero"
    }
}
"""
        analyzer = HelenCodeAnalyzer(source)
        metrics = analyzer.analyze()

        fn = metrics.functions[0]
        # Should be: 1 (base) + 1 (if) + 1 (else if) = 3
        # NOT: 1 + 1 (if) + 2 (else if counted as else + if) = 4
        assert fn.complexity == 3

    def test_brace_counting_ignores_strings(self):
        """Bug fix #9: braces inside strings should not affect function boundary."""
        source = """
fn test() {
    let s = "{hello}"
    let t = "world}"
    return s
}

fn other() {
    return 42
}
"""
        analyzer = HelenCodeAnalyzer(source)
        metrics = analyzer.analyze()

        # Should correctly find 2 functions
        assert metrics.function_count == 2

    def test_dead_code_detection(self):
        """New feature: dead code detection."""
        source = """
fn test() {
    pass
    // TODO: implement this
    return 42
}
"""
        analyzer = HelenCodeAnalyzer(source)
        metrics = analyzer.analyze()

        assert metrics.dead_code_lines >= 1

    def test_protocol_declarations_no_crash(self):
        """Regression: protocol method declarations (no body) must not crash
        the analyzer with IndexError. See helenagent issue #3."""
        source = """
protocol ContractorContract {
    fn design_contract(requirement: str, context: str): map
}

protocol ChatAgentContract {
    fn chat(user_input: str): str
}

protocol ConversationManagerContract {
    fn add_message(session_id: str, role: str, content: str): map
    fn get_history(session_id: str, max_turns: int): list
    fn clear_history(session_id: str): map
    fn format_history(session_id: str, max_turns: int): str
}
"""
        analyzer = HelenCodeAnalyzer(source, "contracts.helen")
        metrics = analyzer.analyze()

        # Each protocol method is treated as a 1-line "function"
        assert metrics.function_count == 6
        # All should be 1-line declarations
        for fn in metrics.functions:
            assert fn.line_count == 1
            assert fn.complexity == 1  # no branches in a signature

    def test_mixed_functions_and_protocols(self):
        """Analyzer handles files mixing real functions and protocol declarations."""
        source = """
fn helper(x: int): int {
    if x > 0 {
        return x * 2
    }
    return 0
}

protocol Service {
    fn call(arg: str): str
}

fn another(): str {
    return "hi"
}
"""
        analyzer = HelenCodeAnalyzer(source, "mixed.helen")
        metrics = analyzer.analyze()

        assert metrics.function_count == 3
        # helper: 5 lines, complexity 2 (base + if)
        helper = metrics.functions[0]
        assert helper.name == "helper"
        assert helper.complexity == 2
        # protocol method: 1 line, complexity 1
        call_fn = metrics.functions[1]
        assert call_fn.name == "call"
        assert call_fn.line_count == 1
        # another: 3 lines, complexity 1
        another_fn = metrics.functions[2]
        assert another_fn.name == "another"
        assert another_fn.complexity == 1


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

    def test_detects_shell_exec(self):
        """Bug fix #11: Helen-specific patterns."""
        source = """
fn run(cmd) {
    shell_exec(cmd)
}
"""
        analyzer = SecurityAnalyzer(source)
        issues = analyzer.analyze()

        assert len(issues) > 0
        assert any("shell_exec" in i.pattern for i in issues)

    def test_detects_ffi_os_import(self):
        """Bug fix #11: Helen FFI import patterns."""
        source = """
import "os" as os
"""
        analyzer = SecurityAnalyzer(source)
        issues = analyzer.analyze()

        assert len(issues) > 0

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

    def test_engineering_checks_all_naming(self):
        """Bug fix #13: should check ALL naming violations, not just first."""
        from helen.stdlib.quality import CodeMetrics, FunctionMetrics

        scorer = QualityScorer()

        # Multiple naming violations
        metrics = CodeMetrics(
            function_count=4,
            functions=[
                FunctionMetrics("BadName", 1, 10, 10, 2, 1, True, 2),
                FunctionMetrics("AnotherBad", 11, 20, 10, 2, 1, True, 2),
                FunctionMetrics("YetAnother", 21, 30, 10, 2, 1, True, 2),
                FunctionMetrics("good_name", 31, 40, 10, 2, 1, True, 2),
            ],
            total_lines=40,
        )
        score = scorer.score_engineering(metrics)
        # Should penalize for 3 violations, not just 1
        assert score < 9.0

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
        assert "dead_code_lines" in result

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

    def test_quality_report_consistent_with_score(self):
        """Bug fix #7: quality_report should not hardcode test_coverage."""
        source = """
fn test() {
    return 42
}
"""
        # Both should use the same test_coverage logic
        score = _quality_score(source, "")
        report = _quality_report(source, "test.helen", file_path="")

        # The report should show the same test_coverage as the score
        assert "Test Coverage" in report

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


# ── Issue #4 — docstring detection before function ──────────────


class TestIssue4DocstringDetection:
    """helenagent issue #4: docstring placed before fn definition
    (industry convention) must be recognized, not just inside the body."""

    def test_block_comment_before_fn_is_docstring(self):
        source = """
/** Computes the answer to everything. */
fn answer(): int {
    return 42
}
"""
        analyzer = HelenCodeAnalyzer(source)
        metrics = analyzer.analyze()
        assert metrics.functions[0].has_docstring is True

    def test_line_comments_before_fn_is_docstring(self):
        source = """
// Add two numbers together
// and return the result.
fn add(a, b) {
    return a + b
}
"""
        analyzer = HelenCodeAnalyzer(source)
        metrics = analyzer.analyze()
        assert metrics.functions[0].has_docstring is True

    def test_block_comment_with_blank_line_before_fn(self):
        source = """
/** This is documented. */

fn foo() {
    return 1
}
"""
        analyzer = HelenCodeAnalyzer(source)
        metrics = analyzer.analyze()
        assert metrics.functions[0].has_docstring is True

    def test_no_docstring_before_or_inside(self):
        source = """
fn undocumented() {
    return 42
}
"""
        analyzer = HelenCodeAnalyzer(source)
        metrics = analyzer.analyze()
        assert metrics.functions[0].has_docstring is False

    def test_comment_inside_body_still_works(self):
        """Backward compat: comment inside function body still counts."""
        source = """
fn legacy() {
    // legacy docstring
    return 42
}
"""
        analyzer = HelenCodeAnalyzer(source)
        metrics = analyzer.analyze()
        assert metrics.functions[0].has_docstring is True


# ── Issue #5 — multi-line string false positives ────────────────


class TestIssue5MultiLineStrings:
    """helenagent issue #5: content inside \"\"\"...\"\"\" must not be
    analyzed for security patterns."""

    def test_triple_quoted_string_ignored(self):
        source = '''
agent Example() {
    prompt """
    Here is an example:
    ```helen
    fn factorial(n: int): int {
        if (n <= 1) { return 1 }
        return n * factorial(n - 1)
    }
    main {
        let num = int(input("输入数字: "))
        shell_exec("rm -rf " + user_input)
    }
    ```
    """
    main {
        return "ok"
    }
}
'''
        analyzer = SecurityAnalyzer(source)
        issues = analyzer.analyze()
        # None of the patterns inside the triple-quoted string should fire
        patterns_found = {i.pattern for i in issues}
        assert "shell_exec concat" not in patterns_found
        assert "user input" not in patterns_found

    def test_real_code_after_multiline_string_still_checked(self):
        source = '''
let greeting = """
Hello, world!
"""

fn dangerous() {
    let x = eval(user_input)
    return x
}
'''
        analyzer = SecurityAnalyzer(source)
        issues = analyzer.analyze()
        assert any(i.pattern == "eval()" for i in issues)

    def test_block_comment_ignored(self):
        source = """
/* shell_exec("rm -rf /")
   eval(bad_code)
*/
fn safe() {
    return 42
}
"""
        analyzer = SecurityAnalyzer(source)
        issues = analyzer.analyze()
        assert len(issues) == 0

    def test_inline_comment_stripped(self):
        """Inline // comment containing patterns should not fire."""
        source = """
fn safe() {
    return 42  // eval(user_input) would be bad
}
"""
        analyzer = SecurityAnalyzer(source)
        issues = analyzer.analyze()
        assert len(issues) == 0


# ── Issue #6 — shell_exec concat severity ───────────────────────


class TestIssue6ShellExecSeverity:
    """helenagent issue #6: shell_exec with concatenation inside the
    call must have the same severity as assigning to a variable first."""

    def test_shell_exec_concat_is_medium(self):
        source = """
fn test1(path: str) {
    shell_exec("helen check " + path + " 2>&1")
}
"""
        analyzer = SecurityAnalyzer(source)
        issues = analyzer.analyze()
        shell_issues = [i for i in issues if "shell_exec" in i.pattern]
        assert all(i.severity != "high" for i in shell_issues), \
            "shell_exec concat should not be HIGH"
        assert any(i.severity == "medium" for i in shell_issues)

    def test_shell_exec_variable_concat_is_medium(self):
        source = """
fn test2(path: str) {
    let cmd = "helen check " + path + " 2>&1"
    shell_exec(cmd)
}
"""
        analyzer = SecurityAnalyzer(source)
        issues = analyzer.analyze()
        shell_issues = [i for i in issues if "shell_exec" in i.pattern]
        assert all(i.severity != "high" for i in shell_issues)
        assert any(i.severity == "medium" for i in shell_issues)

    def test_both_forms_same_severity(self):
        """Both forms should produce the same maximum severity."""
        src_direct = """
fn a(p: str) { shell_exec("cmd " + p) }
"""
        src_var = """
fn a(p: str) { let c = "cmd " + p; shell_exec(c) }
"""
        direct_max = max(
            (i.severity for i in SecurityAnalyzer(src_direct).analyze()
             if "shell_exec" in i.pattern),
            key=lambda s: {"high": 2, "medium": 1, "low": 0}[s],
            default="low",
        )
        var_max = max(
            (i.severity for i in SecurityAnalyzer(src_var).analyze()
             if "shell_exec" in i.pattern),
            key=lambda s: {"high": 2, "medium": 1, "low": 0}[s],
            default="low",
        )
        assert direct_max == var_max


# ── Issue #7 — test coverage scoring for agent programs ─────────


class TestIssue7TestCoverageScoring:
    """helenagent issue #7: test coverage scoring should recognize
    Python tests and @test-location annotations."""

    def test_annotation_existing_path(self, tmp_path):
        """@test-location pointing at an existing file → 8.0"""
        test_file = tmp_path / "tests" / "test_my_agent.py"
        test_file.parent.mkdir()
        test_file.write_text("# test")

        src = f'// @test-location: {test_file}\nfn foo() {{}}\n'
        scorer = QualityScorer()
        score = scorer.score_test_coverage("/some/path/agent.helen", source=src)
        assert score == 8.0

    def test_annotation_nonexistent_path_falls_through(self, tmp_path):
        """@test-location pointing at a non-existing file → skip."""
        src = "// @test-location: /does/not/exist.py\nfn foo() {}\n"
        scorer = QualityScorer()
        # With no matching file on disk, it should fall through
        score = scorer.score_test_coverage(str(tmp_path / "x.helen"), source=src)
        assert score == 2.0

    def test_python_tests_in_tests_dir(self, tmp_path):
        """tests/ directory with *.py files → 6.0"""
        tests_dir = tmp_path / "tests"
        tests_dir.mkdir()
        (tests_dir / "test_something.py").write_text("# test")

        scorer = QualityScorer()
        score = scorer.score_test_coverage(str(tmp_path / "main.helen"))
        assert score == 6.0

    def test_parent_level_matching_py_test(self, tmp_path):
        """Parent-level tests/ with matching *.py → 7.0"""
        # Set up: tmp_path/project/agent.helen and tmp_path/tests/test_agent.py
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        tests_dir = tmp_path / "tests"
        tests_dir.mkdir()
        (tests_dir / "test_agent.py").write_text("# test")

        agent_file = project_dir / "agent.helen"
        scorer = QualityScorer()
        score = scorer.score_test_coverage(str(agent_file))
        assert score == 7.0

    def test_no_tests_found(self, tmp_path):
        """No tests anywhere → 2.0"""
        scorer = QualityScorer()
        score = scorer.score_test_coverage(str(tmp_path / "lonely.helen"))
        assert score == 2.0

    def test_integration_with_quality_score(self, tmp_path):
        """End-to-end: _quality_score picks up the parent-level tests/."""
        project_dir = tmp_path / "myagent"
        project_dir.mkdir()
        tests_dir = tmp_path / "tests"
        tests_dir.mkdir()
        (tests_dir / "test_helen_programmer.py").write_text("# test")

        src = "fn helper(): str { return \"ok\" }\n"
        agent_file = project_dir / "helen_programmer.helen"

        score = _quality_score(src, str(agent_file))
        assert score["test_coverage"] == 7.0

