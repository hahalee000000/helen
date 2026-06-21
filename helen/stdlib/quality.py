"""Quality assessment module for Helen stdlib.

Provides 7-dimension quality analysis for Helen programs:
1. Architecture Design (20%)
2. Code Quality (15%)
3. Security (20%)
4. Test Coverage (15%)
5. Documentation (10%)
6. Maintainability (10%)
7. Engineering Standards (10%)
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


# ── Quality Metrics Types ─────────────────────────────────────


@dataclass
class FunctionMetrics:
    """Metrics for a single function."""
    name: str
    line_start: int
    line_end: int
    line_count: int
    param_count: int
    max_nesting: int
    has_docstring: bool
    complexity: int = 1  # Cyclomatic complexity


@dataclass
class CodeMetrics:
    """Aggregated code metrics."""
    total_lines: int = 0
    code_lines: int = 0
    comment_lines: int = 0
    blank_lines: int = 0
    comment_ratio: float = 0.0
    function_count: int = 0
    agent_count: int = 0
    functions: list[FunctionMetrics] = field(default_factory=list)
    avg_function_length: float = 0.0
    max_function_length: int = 0
    avg_complexity: float = 1.0
    max_complexity: int = 1


@dataclass
class SecurityIssue:
    """A security issue found in code."""
    line: int
    severity: str  # "high", "medium", "low"
    pattern: str
    message: str


@dataclass
class QualityScore:
    """Quality assessment result."""
    architecture: float = 0.0
    code_quality: float = 0.0
    security: float = 0.0
    test_coverage: float = 0.0
    documentation: float = 0.0
    maintainability: float = 0.0
    engineering: float = 0.0
    total: float = 0.0
    grade: str = "D"


@dataclass
class QualityReport:
    """Complete quality assessment report."""
    file: str
    metrics: CodeMetrics
    security_issues: list[SecurityIssue]
    score: QualityScore
    recommendations: list[str] = field(default_factory=list)


# ── Code Analyzer ─────────────────────────────────────────────


class HelenCodeAnalyzer:
    """Analyzes Helen source code for quality metrics."""

    def __init__(self, source: str, filename: str = "<unknown>") -> None:
        self.source = source
        self.filename = filename
        self.lines = source.splitlines()

    def analyze(self) -> CodeMetrics:
        """Perform complete code analysis."""
        metrics = CodeMetrics()
        metrics.total_lines = len(self.lines)

        # Count line types
        for line in self.lines:
            stripped = line.strip()
            if not stripped:
                metrics.blank_lines += 1
            elif stripped.startswith("//") or stripped.startswith("/*"):
                metrics.comment_lines += 1
            else:
                metrics.code_lines += 1

        if metrics.total_lines > 0:
            metrics.comment_ratio = metrics.comment_lines / metrics.total_lines

        # Analyze functions
        metrics.functions = self._analyze_functions()
        metrics.function_count = len(metrics.functions)

        # Analyze agents
        metrics.agent_count = self._count_agents()

        # Calculate aggregates
        if metrics.functions:
            lengths = [f.line_count for f in metrics.functions]
            metrics.avg_function_length = sum(lengths) / len(lengths)
            metrics.max_function_length = max(lengths)

            complexities = [f.complexity for f in metrics.functions]
            metrics.avg_complexity = sum(complexities) / len(complexities)
            metrics.max_complexity = max(complexities)

        return metrics

    def _analyze_functions(self) -> list[FunctionMetrics]:
        """Extract and analyze all functions."""
        functions = []
        fn_pattern = re.compile(r'^\s*fn\s+(\w+)\s*\(([^)]*)\)\s*\{')

        i = 0
        while i < len(self.lines):
            line = self.lines[i]
            match = fn_pattern.match(line)

            if match:
                fn_name = match.group(1)
                params = match.group(2).strip()
                param_count = len([p for p in params.split(',') if p.strip()]) if params else 0

                # Find function end (matching brace)
                start_line = i
                brace_count = line.count('{') - line.count('}')
                j = i + 1

                while j < len(self.lines) and brace_count > 0:
                    brace_count += self.lines[j].count('{') - self.lines[j].count('}')
                    j += 1

                end_line = j - 1
                line_count = end_line - start_line + 1

                # Check for docstring
                has_docstring = self._has_docstring(start_line, end_line)

                # Calculate complexity
                complexity = self._calculate_complexity(start_line, end_line)

                # Calculate max nesting
                max_nesting = self._calculate_nesting(start_line, end_line)

                functions.append(FunctionMetrics(
                    name=fn_name,
                    line_start=start_line + 1,
                    line_end=end_line + 1,
                    line_count=line_count,
                    param_count=param_count,
                    max_nesting=max_nesting,
                    has_docstring=has_docstring,
                    complexity=complexity,
                ))

                i = j
            else:
                i += 1

        return functions

    def _has_docstring(self, start: int, end: int) -> bool:
        """Check if function has a docstring (comment after opening brace)."""
        for i in range(start + 1, min(start + 4, end + 1)):
            if i < len(self.lines):
                stripped = self.lines[i].strip()
                if stripped.startswith("//") or stripped.startswith("/*"):
                    return True
                if stripped and not stripped.startswith('//'):
                    break
        return False

    def _calculate_complexity(self, start: int, end: int) -> int:
        """Calculate cyclomatic complexity."""
        complexity = 1
        branch_keywords = ['if', 'else if', 'elif', 'for', 'while', 'case', 'catch']

        for i in range(start, end + 1):
            line = self.lines[i].strip()
            for keyword in branch_keywords:
                if re.match(rf'^{keyword}\b', line) or f' {keyword} ' in line:
                    complexity += 1

        # Count logical operators
        for i in range(start, end + 1):
            line = self.lines[i]
            complexity += line.count('&&') + line.count('||')
            complexity += line.count(' and ') + line.count(' or ')

        return complexity

    def _calculate_nesting(self, start: int, end: int) -> int:
        """Calculate maximum nesting depth."""
        max_depth = 0
        current_depth = 0

        for i in range(start, end + 1):
            line = self.lines[i]
            current_depth += line.count('{') - line.count('}')
            max_depth = max(max_depth, current_depth)

        return max_depth

    def _count_agents(self) -> int:
        """Count agent declarations."""
        count = 0
        agent_pattern = re.compile(r'^\s*agent\s+\w+')

        for line in self.lines:
            if agent_pattern.match(line):
                count += 1

        return count


# ── Security Analyzer ─────────────────────────────────────────


class SecurityAnalyzer:
    """Analyzes Helen code for security issues."""

    DANGEROUS_PATTERNS = [
        (r'\beval\s*\(', 'high', 'eval()', 'eval() can execute arbitrary code'),
        (r'\bexec\s*\(', 'high', 'exec()', 'exec() can execute arbitrary code'),
        (r'shell\s*=\s*true', 'high', 'shell=True', 'shell=True enables command injection'),
        (r'import\s+os', 'medium', 'os import', 'os module can access system resources'),
        (r'import\s+subprocess', 'medium', 'subprocess import', 'subprocess can execute commands'),
        (r'\bopen\s*\([^)]*["\']w', 'medium', 'file write', 'file write without validation'),
        (r'http_get\s*\([^)]*\+', 'medium', 'URL concatenation', 'URL built from user input may be unsafe'),
        (r'input\s*\(', 'low', 'user input', 'user input should be validated'),
    ]

    def __init__(self, source: str) -> None:
        self.source = source
        self.lines = source.splitlines()

    def analyze(self) -> list[SecurityIssue]:
        """Find security issues."""
        issues = []

        for i, line in enumerate(self.lines, 1):
            # Skip comments
            if line.strip().startswith('//'):
                continue

            for pattern, severity, name, message in self.DANGEROUS_PATTERNS:
                if re.search(pattern, line, re.IGNORECASE):
                    issues.append(SecurityIssue(
                        line=i,
                        severity=severity,
                        pattern=name,
                        message=message,
                    ))

        return issues


# ── Quality Scorer ────────────────────────────────────────────


class QualityScorer:
    """Calculates quality scores based on metrics."""

    def score_architecture(self, metrics: CodeMetrics) -> float:
        """Score architecture design (20% weight)."""
        score = 10.0

        # Penalize long functions
        if metrics.max_function_length > 100:
            score -= 3.0
        elif metrics.max_function_length > 50:
            score -= 1.5

        # Penalize high complexity
        if metrics.max_complexity > 15:
            score -= 3.0
        elif metrics.max_complexity > 10:
            score -= 1.5

        # Penalize deep nesting
        max_nesting = max([f.max_nesting for f in metrics.functions] or [0])
        if max_nesting > 5:
            score -= 2.0
        elif max_nesting > 3:
            score -= 1.0

        # Penalize too many parameters
        max_params = max([f.param_count for f in metrics.functions] or [0])
        if max_params > 6:
            score -= 2.0
        elif max_params > 4:
            score -= 1.0

        return max(0.0, min(10.0, score))

    def score_code_quality(self, metrics: CodeMetrics) -> float:
        """Score code quality (15% weight)."""
        score = 10.0

        # Reward good comment ratio
        if metrics.comment_ratio >= 0.2:
            score += 1.0
        elif metrics.comment_ratio < 0.05:
            score -= 2.0

        # Penalize very long functions
        if metrics.avg_function_length > 30:
            score -= 2.0
        elif metrics.avg_function_length > 20:
            score -= 1.0

        # Penalize high average complexity
        if metrics.avg_complexity > 8:
            score -= 2.0
        elif metrics.avg_complexity > 5:
            score -= 1.0

        return max(0.0, min(10.0, score))

    def score_security(self, issues: list[SecurityIssue]) -> float:
        """Score security (20% weight)."""
        score = 10.0

        for issue in issues:
            if issue.severity == 'high':
                score -= 3.0
            elif issue.severity == 'medium':
                score -= 1.5
            elif issue.severity == 'low':
                score -= 0.5

        return max(0.0, min(10.0, score))

    def score_test_coverage(self, file_path: str) -> float:
        """Score test coverage (15% weight)."""
        # Check if test file exists
        path = Path(file_path)
        test_file = path.with_name(path.stem + '_test.helen')
        test_file2 = path.with_name('test_' + path.name)

        if test_file.exists() or test_file2.exists():
            return 8.0

        # Check for tests directory
        tests_dir = path.parent / 'tests'
        if tests_dir.exists():
            test_files = list(tests_dir.glob('*.helen'))
            if test_files:
                return 6.0

        return 2.0  # No tests found

    def score_documentation(self, metrics: CodeMetrics) -> float:
        """Score documentation (10% weight)."""
        if not metrics.functions:
            return 5.0

        documented = sum(1 for f in metrics.functions if f.has_docstring)
        ratio = documented / metrics.function_count

        # Scale to 0-10
        return ratio * 10.0

    def score_maintainability(self, metrics: CodeMetrics) -> float:
        """Score maintainability (10% weight)."""
        score = 10.0

        # Penalize very long functions
        long_functions = sum(1 for f in metrics.functions if f.line_count > 50)
        if long_functions > 0:
            score -= min(3.0, long_functions * 0.5)

        # Penalize high complexity
        complex_functions = sum(1 for f in metrics.functions if f.complexity > 10)
        if complex_functions > 0:
            score -= min(3.0, complex_functions * 0.5)

        # Reward reasonable function sizes
        if metrics.avg_function_length < 20:
            score += 1.0

        return max(0.0, min(10.0, score))

    def score_engineering(self, metrics: CodeMetrics) -> float:
        """Score engineering standards (10% weight)."""
        score = 10.0

        # Check naming conventions
        for fn in metrics.functions:
            if not re.match(r'^[a-z_][a-z0-9_]*$', fn.name):
                score -= 0.5
                break

        # Check for reasonable file size
        if metrics.total_lines > 1000:
            score -= 2.0
        elif metrics.total_lines > 500:
            score -= 1.0

        return max(0.0, min(10.0, score))

    def calculate_total(self, score: QualityScore) -> float:
        """Calculate weighted total score."""
        total = (
            score.architecture * 0.20 +
            score.code_quality * 0.15 +
            score.security * 0.20 +
            score.test_coverage * 0.15 +
            score.documentation * 0.10 +
            score.maintainability * 0.10 +
            score.engineering * 0.10
        )
        return round(total, 2)

    def assign_grade(self, total: float) -> str:
        """Assign letter grade based on total score."""
        if total >= 9.0:
            return 'S'
        elif total >= 7.5:
            return 'A'
        elif total >= 6.0:
            return 'B'
        elif total >= 4.0:
            return 'C'
        else:
            return 'D'


# ── Stdlib Functions ──────────────────────────────────────────


def _analyze_code(source: str, filename: str = "<unknown>") -> dict[str, Any]:
    """Analyze Helen source code and return metrics.

    Args:
        source: Helen source code
        filename: Optional filename for reporting

    Returns:
        Dict with code metrics
    """
    analyzer = HelenCodeAnalyzer(source, filename)
    metrics = analyzer.analyze()

    return {
        "total_lines": metrics.total_lines,
        "code_lines": metrics.code_lines,
        "comment_lines": metrics.comment_lines,
        "blank_lines": metrics.blank_lines,
        "comment_ratio": round(metrics.comment_ratio, 3),
        "function_count": metrics.function_count,
        "agent_count": metrics.agent_count,
        "avg_function_length": round(metrics.avg_function_length, 1),
        "max_function_length": metrics.max_function_length,
        "avg_complexity": round(metrics.avg_complexity, 1),
        "max_complexity": metrics.max_complexity,
        "functions": [
            {
                "name": f.name,
                "lines": f.line_count,
                "params": f.param_count,
                "complexity": f.complexity,
                "nesting": f.max_nesting,
                "has_docstring": f.has_docstring,
            }
            for f in metrics.functions
        ],
    }


def _check_security(source: str) -> list[dict[str, Any]]:
    """Check source code for security issues.

    Args:
        source: Helen source code

    Returns:
        List of security issues
    """
    analyzer = SecurityAnalyzer(source)
    issues = analyzer.analyze()

    return [
        {
            "line": issue.line,
            "severity": issue.severity,
            "pattern": issue.pattern,
            "message": issue.message,
        }
        for issue in issues
    ]


def _quality_score(source: str, file_path: str = "") -> dict[str, Any]:
    """Calculate 7-dimension quality score.

    Args:
        source: Helen source code
        file_path: Optional file path for test detection

    Returns:
        Dict with quality scores
    """
    code_analyzer = HelenCodeAnalyzer(source)
    metrics = code_analyzer.analyze()

    security_analyzer = SecurityAnalyzer(source)
    security_issues = security_analyzer.analyze()

    scorer = QualityScorer()

    score = QualityScore(
        architecture=scorer.score_architecture(metrics),
        code_quality=scorer.score_code_quality(metrics),
        security=scorer.score_security(security_issues),
        test_coverage=scorer.score_test_coverage(file_path) if file_path else 5.0,
        documentation=scorer.score_documentation(metrics),
        maintainability=scorer.score_maintainability(metrics),
        engineering=scorer.score_engineering(metrics),
    )

    score.total = scorer.calculate_total(score)
    score.grade = scorer.assign_grade(score.total)

    return {
        "architecture": round(score.architecture, 2),
        "code_quality": round(score.code_quality, 2),
        "security": round(score.security, 2),
        "test_coverage": round(score.test_coverage, 2),
        "documentation": round(score.documentation, 2),
        "maintainability": round(score.maintainability, 2),
        "engineering": round(score.engineering, 2),
        "total": score.total,
        "grade": score.grade,
    }


def _quality_report(source: str, filename: str = "<unknown>") -> str:
    """Generate formatted quality report.

    Args:
        source: Helen source code
        filename: Optional filename

    Returns:
        Formatted quality report string
    """
    code_analyzer = HelenCodeAnalyzer(source, filename)
    metrics = code_analyzer.analyze()

    security_analyzer = SecurityAnalyzer(source)
    security_issues = security_analyzer.analyze()

    scorer = QualityScorer()

    score = QualityScore(
        architecture=scorer.score_architecture(metrics),
        code_quality=scorer.score_code_quality(metrics),
        security=scorer.score_security(security_issues),
        test_coverage=5.0,
        documentation=scorer.score_documentation(metrics),
        maintainability=scorer.score_maintainability(metrics),
        engineering=scorer.score_engineering(metrics),
    )

    score.total = scorer.calculate_total(score)
    score.grade = scorer.assign_grade(score.total)

    # Generate recommendations
    recommendations = []

    if metrics.max_function_length > 50:
        recommendations.append("Break down long functions (>50 lines)")

    if metrics.max_complexity > 10:
        recommendations.append("Reduce complexity in complex functions")

    if metrics.comment_ratio < 0.1:
        recommendations.append("Add more comments (current: {:.0%})".format(metrics.comment_ratio))

    if security_issues:
        high_severity = [i for i in security_issues if i.severity == 'high']
        if high_severity:
            recommendations.append(f"Fix {len(high_severity)} high-severity security issues")

    undocumented = [f for f in metrics.functions if not f.has_docstring]
    if len(undocumented) > len(metrics.functions) * 0.5:
        recommendations.append("Add docstrings to functions")

    # Format report
    lines = []
    lines.append("")
    lines.append("=" * 60)
    lines.append("  HELEN QUALITY REPORT")
    lines.append("=" * 60)
    lines.append(f"  File: {filename}")
    lines.append("")

    lines.append("  Code Metrics:")
    lines.append(f"    Total lines: {metrics.total_lines}")
    lines.append(f"    Code lines: {metrics.code_lines}")
    lines.append(f"    Comment lines: {metrics.comment_lines} ({metrics.comment_ratio:.0%})")
    lines.append(f"    Functions: {metrics.function_count}")
    lines.append(f"    Agents: {metrics.agent_count}")
    lines.append(f"    Avg function length: {metrics.avg_function_length:.1f} lines")
    lines.append(f"    Max function length: {metrics.max_function_length} lines")
    lines.append(f"    Avg complexity: {metrics.avg_complexity:.1f}")
    lines.append(f"    Max complexity: {metrics.max_complexity}")
    lines.append("")

    lines.append("  Quality Scores (0-10):")
    lines.append(f"    Architecture:      {score.architecture:.2f} (20%)")
    lines.append(f"    Code Quality:      {score.code_quality:.2f} (15%)")
    lines.append(f"    Security:          {score.security:.2f} (20%)")
    lines.append(f"    Test Coverage:     {score.test_coverage:.2f} (15%)")
    lines.append(f"    Documentation:     {score.documentation:.2f} (10%)")
    lines.append(f"    Maintainability:   {score.maintainability:.2f} (10%)")
    lines.append(f"    Engineering:       {score.engineering:.2f} (10%)")
    lines.append(f"    ─────────────────────────────")
    lines.append(f"    TOTAL:             {score.total:.2f}")
    lines.append(f"    GRADE:             {score.grade}")
    lines.append("")

    if security_issues:
        lines.append(f"  Security Issues ({len(security_issues)}):")
        for issue in security_issues[:5]:  # Show first 5
            lines.append(f"    [{issue.severity.upper()}] Line {issue.line}: {issue.message}")
        if len(security_issues) > 5:
            lines.append(f"    ... and {len(security_issues) - 5} more")
        lines.append("")

    if recommendations:
        lines.append("  Recommendations:")
        for rec in recommendations:
            lines.append(f"    • {rec}")
        lines.append("")

    lines.append("=" * 60)
    lines.append("")

    return "\n".join(lines)
