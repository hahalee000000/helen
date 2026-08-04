"""Test coverage measurement for Helen programs.

Provides function, line, and branch coverage tracking by instrumenting
the interpreter at key execution points. Data is collected as counters
keyed by source location (file:line).

Design principles:
- Default off: zero overhead when not explicitly enabled.
- Minimal logging: only record file/line/function names, never values.
- Resource-bounded: size limits prevent memory/disk exhaustion.
- Thread-safe: use threading.Lock for counter updates.

This module does NOT perform AST rewriting (optional Phase 4 optimization).
Instead, it hooks into interpreter visit methods directly.
"""

from __future__ import annotations

import json
import threading
import time
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from helen.core.source import SourceSpan


# ---------------------------------------------------------------------------
# Coverage Data
# ---------------------------------------------------------------------------

@dataclass
class CoverageCount:
    """Coverage counters for a single source file.

    Attributes:
        lines: Mapping of line number to execution count.
        functions: Mapping of (func_name, line) to call count.
        branches: Mapping of (line, branch_id) to execution count.
            branch_id=0 means "condition false", branch_id=1 means "condition true".
    """
    lines: dict[int, int] = field(default_factory=lambda: defaultdict(int))
    functions: dict[tuple[str, int], int] = field(default_factory=lambda: defaultdict(int))
    branches: dict[tuple[int, int], int] = field(default_factory=lambda: defaultdict(int))


# ---------------------------------------------------------------------------
# Coverage Tracker
# ---------------------------------------------------------------------------

class CoverageTracker:
    """Measures test coverage of Helen programs.

    Usage:
        tracker = CoverageTracker()
        tracker.enabled = True
        # ... run program ...
        tracker.enabled = False
        report = tracker.generate_report()
    """

    def __init__(self, max_counters: int = 1_000_000):
        """Initialize coverage tracker.

        Args:
            max_counters: Maximum number of distinct counter entries.
                Prevents memory exhaustion from runaway programs.
        """
        self._lock = threading.Lock()
        self._files: dict[str, CoverageCount] = {}
        self._enabled = False
        self._max_counters = max_counters
        self._total_counters = 0
        self._source_files: dict[str, list[str]] = {}
        self._start_time: float | None = None

    @property
    def enabled(self) -> bool:
        """Whether coverage tracking is enabled."""
        return self._enabled

    @enabled.setter
    def enabled(self, value: bool) -> None:
        """Enable or disable coverage tracking."""
        with self._lock:
            if value and not self._enabled:
                self._start_time = time.time()
            elif not value and self._enabled:
                self._start_time = None
            self._enabled = value

    def _get_file(self, file_path: str) -> CoverageCount:
        """Get or create coverage data for a file. Must hold _lock."""
        if file_path not in self._files:
            self._files[file_path] = CoverageCount()
        return self._files[file_path]

    def _check_limit(self) -> bool:
        """Check if we're under the counter limit. Must hold _lock."""
        return self._total_counters < self._max_counters

    def _abs_path(self, span: SourceSpan) -> str | None:
        """Normalize a span's file path to absolute."""
        if not span or not span.file:
            return None
        p = Path(span.file)
        return str(p.absolute()) if not p.is_absolute() else span.file

    def record_line(self, span: SourceSpan | None) -> None:
        """Record that a line was executed.

        Args:
            span: Source location of the statement.
        """
        if not self._enabled or span is None:
            return
        file_path = self._abs_path(span)
        if file_path is None:
            return
        with self._lock:
            if not self._check_limit():
                return
            fc = self._get_file(file_path)
            line = span.start_line
            if line not in fc.lines:
                self._total_counters += 1
            fc.lines[line] += 1

    def record_function(self, span: SourceSpan | None, func_name: str) -> None:
        """Record that a function was called.

        Args:
            span: Source location of the function definition.
            func_name: Name of the function.
        """
        if not self._enabled or span is None:
            return
        file_path = self._abs_path(span)
        if file_path is None:
            return
        with self._lock:
            if not self._check_limit():
                return
            fc = self._get_file(file_path)
            key = (func_name, span.start_line)
            if key not in fc.functions:
                self._total_counters += 1
            fc.functions[key] += 1

    def record_branch(self, span: SourceSpan | None, branch_id: int) -> None:
        """Record that a branch was taken.

        Args:
            span: Source location of the branch (the if/match statement).
            branch_id: 0 for "false/else" branch, 1 for "true/then" branch.
                For match: case index (0, 1, 2, ...) or -1 for default.
        """
        if not self._enabled or span is None:
            return
        file_path = self._abs_path(span)
        if file_path is None:
            return
        with self._lock:
            if not self._check_limit():
                return
            fc = self._get_file(file_path)
            key = (span.start_line, branch_id)
            if key not in fc.branches:
                self._total_counters += 1
            fc.branches[key] += 1

    def register_source(self, file_path: str, source_lines: list[str]) -> None:
        """Register a source file for report generation.

        Args:
            file_path: Absolute path to the source file.
            source_lines: Lines of the source file.
        """
        p = Path(file_path)
        abs_path = str(p.absolute()) if not p.is_absolute() else file_path
        self._source_files[abs_path] = source_lines

    def register_function(self, span: SourceSpan | None, func_name: str) -> None:
        """Register a function definition (for denominator in coverage calculation).

        Args:
            span: Source location of the function definition.
            func_name: Name of the function.
        """
        if span is None:
            return
        file_path = self._abs_path(span)
        if file_path is None:
            return
        with self._lock:
            fc = self._get_file(file_path)
            key = (func_name, span.start_line)
            if key not in fc.functions:
                fc.functions[key] = 0  # Registered but not yet called

    def register_branch(self, span: SourceSpan | None, branch_ids: list[int]) -> None:
        """Register possible branches at a location.

        Args:
            span: Source location of the branch.
            branch_ids: List of possible branch IDs (e.g., [0, 1] for if/else).
        """
        if span is None:
            return
        file_path = self._abs_path(span)
        if file_path is None:
            return
        with self._lock:
            fc = self._get_file(file_path)
            for bid in branch_ids:
                key = (span.start_line, bid)
                if key not in fc.branches:
                    fc.branches[key] = 0

    def reset(self) -> None:
        """Reset all coverage data."""
        with self._lock:
            self._files.clear()
            self._total_counters = 0
            self._source_files.clear()
            self._start_time = None

    def clear(self) -> None:
        """Clear coverage counters but keep registered sources."""
        with self._lock:
            for fc in self._files.values():
                fc.lines.clear()
                # Reset function counts but keep registered functions
                for key in list(fc.functions.keys()):
                    fc.functions[key] = 0
                # Reset branch counts but keep registered branches
                for key in list(fc.branches.keys()):
                    fc.branches[key] = 0
            self._total_counters = 0

    # ------------------------------------------------------------------
    # Report Generation
    # ------------------------------------------------------------------

    def get_summary(self) -> dict[str, Any]:
        """Generate a coverage summary.

        Returns:
            Dict with line/function/branch coverage percentages and counts.
        """
        with self._lock:
            total_lines = 0
            covered_lines = 0
            total_functions = 0
            covered_functions = 0
            total_branches = 0
            covered_branches = 0

            for file_path, fc in self._files.items():
                # Line coverage
                # Use registered source files for total line count if available
                if file_path in self._source_files:
                    source_lines = self._source_files[file_path]
                    # Only count non-empty, non-comment lines
                    for i, line in enumerate(source_lines, 1):
                        stripped = line.strip()
                        if stripped and not stripped.startswith("//") and not stripped.startswith("#"):
                            total_lines += 1
                            if fc.lines.get(i, 0) > 0:
                                covered_lines += 1
                else:
                    # Fall back to observed lines
                    total_lines += len(fc.lines)
                    covered_lines += sum(1 for c in fc.lines.values() if c > 0)

                # Function coverage
                total_functions += len(fc.functions)
                covered_functions += sum(1 for c in fc.functions.values() if c > 0)

                # Branch coverage
                # Count unique branch locations (lines with branches)
                branch_locations: dict[int, set[int]] = {}
                for (line, bid), count in fc.branches.items():
                    if line not in branch_locations:
                        branch_locations[line] = set()
                    branch_locations[line].add(bid)
                for line, bids in branch_locations.items():
                    total_branches += len(bids)
                    covered_branches += sum(1 for bid in bids if fc.branches.get((line, bid), 0) > 0)

        # Calculate percentages
        line_pct = (covered_lines / total_lines * 100) if total_lines > 0 else 0.0
        func_pct = (covered_functions / total_functions * 100) if total_functions > 0 else 0.0
        branch_pct = (covered_branches / total_branches * 100) if total_branches > 0 else 0.0

        return {
            "lines": {
                "total": total_lines,
                "covered": covered_lines,
                "percent": round(line_pct, 1),
            },
            "functions": {
                "total": total_functions,
                "covered": covered_functions,
                "percent": round(func_pct, 1),
            },
            "branches": {
                "total": total_branches,
                "covered": covered_branches,
                "percent": round(branch_pct, 1),
            },
        }

    def get_file_report(self, file_path: str) -> dict[str, Any] | None:
        """Generate a detailed report for a single file.

        Args:
            file_path: Path to the source file.

        Returns:
            Dict with per-line coverage data, or None if file not found.
        """
        p = Path(file_path)
        abs_path = str(p.absolute()) if not p.is_absolute() else file_path

        with self._lock:
            fc = self._files.get(abs_path)
            if fc is None:
                return None

            source_lines = self._source_files.get(abs_path, [])

            # Build per-line data
            lines_data = []
            for i, line_text in enumerate(source_lines, 1):
                lines_data.append({
                    "line": i,
                    "text": line_text,
                    "count": fc.lines.get(i, 0),
                })

            # If no source registered, just report observed lines
            if not source_lines:
                for line, count in sorted(fc.lines.items()):
                    lines_data.append({
                        "line": line,
                        "text": "",
                        "count": count,
                    })

            # Functions
            functions_data = []
            for (func_name, line), count in sorted(fc.functions.items()):
                functions_data.append({
                    "name": func_name,
                    "line": line,
                    "count": count,
                })

            # Branches
            branches_data = []
            branch_locs: dict[int, dict[int, int]] = {}
            for (line, bid), count in fc.branches.items():
                if line not in branch_locs:
                    branch_locs[line] = {}
                branch_locs[line][bid] = count
            for line, bids in sorted(branch_locs.items()):
                for bid, count in sorted(bids.items()):
                    branches_data.append({
                        "line": line,
                        "branch_id": bid,
                        "label": "then" if bid == 1 else ("else" if bid == 0 else f"case {bid}"),
                        "count": count,
                    })

        return {
            "file": abs_path,
            "lines": lines_data,
            "functions": functions_data,
            "branches": branches_data,
        }

    def generate_report(self, format: str = "text") -> str:
        """Generate a formatted coverage report.

        Args:
            format: Output format - "text", "json", or "html".

        Returns:
            Formatted report string.
        """
        if format == "json":
            return self._generate_json_report()
        elif format == "html":
            return self._generate_html_report()
        else:
            return self._generate_text_report()

    def _generate_text_report(self) -> str:
        """Generate a text coverage report."""
        summary = self.get_summary()

        lines = [
            "=" * 60,
            "HELEN COVERAGE REPORT",
            "=" * 60,
            "",
            f"  Lines:     {summary['lines']['covered']}/{summary['lines']['total']}"
            f"  ({summary['lines']['percent']}%)",
            f"  Functions: {summary['functions']['covered']}/{summary['functions']['total']}"
            f"  ({summary['functions']['percent']}%)",
            f"  Branches:  {summary['branches']['covered']}/{summary['branches']['total']}"
            f"  ({summary['branches']['percent']}%)",
            "",
        ]

        # Per-file summary
        with self._lock:
            if self._files:
                lines.append("Files:")
                lines.append(f"  {'File':<40} {'Lines':>10} {'Funcs':>10}")
                lines.append(f"  {'-' * 40} {'-' * 10} {'-' * 10}")

                for file_path, fc in sorted(self._files.items()):
                    # Shorten path for display
                    display_path = file_path
                    try:
                        display_path = str(Path(file_path).relative_to(Path.cwd()))
                    except ValueError:
                        pass
                    if len(display_path) > 40:
                        display_path = "..." + display_path[-37:]

                    line_total = len(fc.lines)
                    line_covered = sum(1 for c in fc.lines.values() if c > 0)
                    func_total = len(fc.functions)
                    func_covered = sum(1 for c in fc.functions.values() if c > 0)

                    lines.append(
                        f"  {display_path:<40} {line_covered:>4}/{line_total:<5} {func_covered:>4}/{func_total:<5}"
                    )

        lines.append("")
        lines.append("=" * 60)
        return "\n".join(lines)

    def _generate_json_report(self) -> str:
        """Generate a JSON coverage report."""
        summary = self.get_summary()

        # Build per-file data
        files_data = {}
        with self._lock:
            for file_path, fc in self._files.items():
                files_data[file_path] = {
                    "lines": {str(line): count for line, count in fc.lines.items()},
                    "functions": {
                        f"{name}:{line}": count
                        for (name, line), count in fc.functions.items()
                    },
                    "branches": {
                        f"{line}:{bid}": count
                        for (line, bid), count in fc.branches.items()
                    },
                }

        report = {
            "summary": summary,
            "files": files_data,
            "generated_at": time.time(),
        }
        return json.dumps(report, indent=2, ensure_ascii=False)

    def _generate_html_report(self) -> str:
        """Generate an HTML coverage report."""
        summary = self.get_summary()

        html_parts = [
            "<!DOCTYPE html>",
            "<html><head>",
            "<meta charset='utf-8'>",
            "<title>Helen Coverage Report</title>",
            "<style>",
            "body { font-family: monospace; margin: 20px; background: #f5f5f5; }",
            ".summary { background: #fff; padding: 20px; margin-bottom: 20px;"
            " border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }",
            ".file { background: #fff; margin-bottom: 10px; border-radius: 8px;"
            " box-shadow: 0 1px 3px rgba(0,0,0,0.1); overflow: hidden; }",
            ".file-header { padding: 10px 15px; background: #e8e8e8; cursor: pointer; }",
            ".file-content { padding: 0; display: none; }",
            ".file-content.open { display: block; }",
            "table { width: 100%; border-collapse: collapse; }",
            "td { padding: 2px 10px; white-space: pre; font-size: 13px; }",
            ".line-num { color: #999; text-align: right; width: 50px;"
            " user-select: none; border-right: 1px solid #eee; }",
            ".line-count { color: #666; text-align: right; width: 60px;"
            " border-right: 1px solid #eee; }",
            ".line-code { padding-left: 10px; }",
            ".covered { background: #e6ffe6; }",
            ".uncovered { background: #ffe6e6; }",
            ".bar { height: 20px; border-radius: 4px; overflow: hidden;"
            " background: #eee; display: inline-block; width: 200px; }",
            ".bar-fill { height: 100%; border-radius: 4px; }",
            ".pct-high { color: #2d7d2d; }",
            ".pct-mid { color: #b8860b; }",
            ".pct-low { color: #c0392b; }",
            "</style>",
            "</head><body>",
            "<h1>Helen Coverage Report</h1>",
        ]

        # Summary section
        def pct_class(pct: float) -> str:
            if pct >= 80:
                return "pct-high"
            elif pct >= 50:
                return "pct-mid"
            return "pct-low"

        def bar_html(pct: float) -> str:
            color = "#2d7d2d" if pct >= 80 else ("#b8860b" if pct >= 50 else "#c0392b")
            return (
                f'<span class="bar"><span class="bar-fill"'
                f' style="width:{pct}%;background:{color}"></span></span>'
            )

        html_parts.append('<div class="summary">')
        html_parts.append("<h2>Summary</h2>")
        html_parts.append("<table>")
        for category in ("lines", "functions", "branches"):
            s = summary[category]
            label = category.capitalize()
            cls = pct_class(s["percent"])
            html_parts.append(
                f"<tr><td>{label}:</td>"
                f'<td class="{cls}">{s["percent"]}%</td>'
                f"<td>{bar_html(s['percent'])}</td>"
                f"<td>{s['covered']}/{s['total']}</td></tr>"
            )
        html_parts.append("</table></div>")

        # Per-file sections
        with self._lock:
            for file_path, fc in sorted(self._files.items()):
                display_path = file_path
                try:
                    display_path = str(Path(file_path).relative_to(Path.cwd()))
                except ValueError:
                    pass

                source_lines = self._source_files.get(file_path, [])

                html_parts.append('<div class="file">')
                html_parts.append(
                    f'<div class="file-header" onclick='
                    f'"this.nextElementSibling.classList.toggle(\'open\')">'
                    f"{display_path}</div>"
                )
                html_parts.append('<div class="file-content">')

                # Functions table
                if fc.functions:
                    html_parts.append("<h3>Functions</h3><table>")
                    for (name, line), count in sorted(fc.functions.items()):
                        cls = "covered" if count > 0 else "uncovered"
                        html_parts.append(
                            f'<tr class="{cls}">'
                            f"<td>Line {line}</td>"
                            f"<td>{name}()</td>"
                            f"<td>{count}x</td></tr>"
                        )
                    html_parts.append("</table>")

                # Source code view
                if source_lines:
                    html_parts.append("<h3>Source</h3><table>")
                    for i, line_text in enumerate(source_lines, 1):
                        count = fc.lines.get(i, 0)
                        stripped = line_text.strip()
                        # Skip blank lines and pure comments
                        if not stripped or stripped.startswith("//"):
                            css_class = ""
                            count_str = ""
                        elif count > 0:
                            css_class = "covered"
                            count_str = f"{count}x"
                        else:
                            css_class = "uncovered"
                            count_str = "0x"

                        # Escape HTML
                        safe_text = (
                            line_text.replace("&", "&amp;")
                            .replace("<", "&lt;")
                            .replace(">", "&gt;")
                        )
                        html_parts.append(
                            f'<tr class="{css_class}">'
                            f'<td class="line-num">{i}</td>'
                            f'<td class="line-count">{count_str}</td>'
                            f'<td class="line-code">{safe_text}</td>'
                            f"</tr>"
                        )
                    html_parts.append("</table>")

                html_parts.append("</div></div>")

        html_parts.append("</body></html>")
        return "\n".join(html_parts)

    def save_to_file(self, output_path: str, format: str = "json") -> str:
        """Save coverage report to a file.

        Args:
            output_path: Path to the output file.
            format: Report format - "json" or "html".

        Returns:
            Path to the saved file.
        """
        if format == "html":
            content = self._generate_html_report()
        else:
            content = self._generate_json_report()

        p = Path(output_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        return str(p.absolute())

    def merge(self, other: CoverageTracker) -> None:
        """Merge another tracker's data into this one.

        Useful for combining coverage from multiple test runs.

        Args:
            other: Another CoverageTracker to merge from.
        """
        with self._lock:
            with other._lock:
                for file_path, other_fc in other._files.items():
                    fc = self._get_file(file_path)
                    for line, count in other_fc.lines.items():
                        if line not in fc.lines:
                            self._total_counters += 1
                        fc.lines[line] += count
                    for key, count in other_fc.functions.items():
                        if key not in fc.functions:
                            self._total_counters += 1
                        fc.functions[key] += count
                    for key, count in other_fc.branches.items():
                        if key not in fc.branches:
                            self._total_counters += 1
                        fc.branches[key] += count

                # Merge source files
                for file_path, lines in other._source_files.items():
                    if file_path not in self._source_files:
                        self._source_files[file_path] = lines
