#!/usr/bin/env python3
"""Wrap bare top-level executable code in main {}.

Scans .helen files and wraps any executable statements (let, if, for, print, etc.)
that appear at module level into a main {} block. Declarations (fn, agent, const,
import, alias, shared, protocol, impl) remain at top level.

Usage:
    python tools/wrap_main.py                    # dry run (show changes)
    python tools/wrap_main.py --apply            # apply changes
    python tools/wrap_main.py path/to/file.helen # process single file
"""

import re
import sys
from pathlib import Path

# Pattern matching the start of a top-level declaration
DECL_START = re.compile(
    r'^\s*(?:'
    # English
    r'fn\s|agent\s|const\s|import\s|alias\s|protocol\s|impl\s|'
    r'shared\s+(?:let|const|store)\s|'
    r'@(?:open|strict|sandbox)\s|'
    r'main\s*\{|'
    # Chinese
    r'函数\s|智能体\s|常量\s|导入\s|别名\s|协议\s|实现\s|'
    r'共享\s+(?:定义|常量|仓库|let|const|store)\s|'
    r'主函\s*\{'
    r')'
)


def _find_decl_end(lines: list[str], start: int) -> int:
    """Find the line index AFTER a declaration (including multi-line blocks).

    For single-line declarations, returns start + 1.
    For multi-line (fn/agent with braces), tracks brace depth to find closing }.
    """
    line = lines[start]
    brace_depth = line.count('{') - line.count('}')

    if brace_depth <= 0:
        return start + 1  # single-line declaration

    # Multi-line: track brace depth
    idx = start + 1
    while idx < len(lines) and brace_depth > 0:
        brace_depth += lines[idx].count('{') - lines[idx].count('}')
        idx += 1
    return idx


def wrap_file(content: str) -> str:
    """Wrap bare top-level executable code in main {}.

    Strategy:
    1. Scan top-level lines, identifying contiguous declaration blocks
    2. If executable code follows declarations, wrap it in main {}
    3. If already has main {} or no executable code, return unchanged
    """
    lines = content.split('\n')

    # First check: does the file already have a TOP-LEVEL main {}?
    brace_depth = 0
    for line in lines:
        if brace_depth == 0 and re.match(r'^\s*(?:main|主函)\s*\{', line.strip()):
            return content  # already has top-level main, don't touch
        brace_depth += line.count('{') - line.count('}')
        if brace_depth < 0:
            brace_depth = 0

    # Phase 1: Identify the declaration zone and executable zone
    # Walk through lines, tracking declaration blocks
    # Leading comments/empty lines are kept with declarations
    decl_end = 0  # exclusive end of the declaration zone
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        # Empty lines and comments: stay in decl zone (leading or inter-decl)
        if not stripped or stripped.startswith('//') or stripped.startswith('#'):
            i += 1
            decl_end = i  # include in decl zone
            continue

        # Check if this is a declaration
        if DECL_START.match(line):
            end = _find_decl_end(lines, i)
            decl_end = end  # update the end of declarations
            i = end
            continue

        # Not a declaration, not empty/comment → executable code starts here
        break

    # Phase 2: Check if there's any executable code after declarations
    exec_start = i
    if exec_start >= len(lines):
        return content  # no executable code

    # Check if the remaining content is all empty/comments
    remaining = lines[exec_start:]
    has_exec = any(
        l.strip() and not l.strip().startswith('//') and not l.strip().startswith('#')
        for l in remaining
    )
    if not has_exec:
        return content  # nothing executable to wrap

    # Phase 3: Build the output
    # Declarations section: lines[:decl_end] (trimmed)
    decl_lines = lines[:decl_end]
    while decl_lines and not decl_lines[-1].strip():
        decl_lines.pop()

    # Executable section: lines[exec_start:]
    exec_lines = lines[exec_start:]
    # Trim trailing empty lines
    while exec_lines and not exec_lines[-1].strip():
        exec_lines.pop()

    # Build result
    result = []
    if decl_lines:
        result.extend(decl_lines)
        result.append('')

    result.append('main {')
    for line in exec_lines:
        if line.strip():
            result.append('    ' + line)
        else:
            result.append('')
    result.append('}')

    return '\n'.join(result)


def process_file(filepath: Path, apply: bool = False) -> bool:
    """Process a single .helen file. Returns True if changes were made."""
    content = filepath.read_text(encoding='utf-8')
    new_content = wrap_file(content)

    if new_content == content:
        return False

    if apply:
        filepath.write_text(new_content, encoding='utf-8')
        print(f"  ✓ {filepath}")
    else:
        print(f"  ~ {filepath} (would change)")
    return True


def main():
    apply = '--apply' in sys.argv
    single_file = None
    for arg in sys.argv[1:]:
        if arg != '--apply':
            single_file = Path(arg)

    if single_file:
        changed = process_file(single_file, apply)
        if changed:
            print(f"\n{'Applied' if apply else 'Would apply'} changes to {single_file}")
        else:
            print(f"No changes needed for {single_file}")
        return

    # Find all .helen files under ~/helen
    helen_root = Path(__file__).resolve().parent.parent
    targets = [
        helen_root / "examples",
        helen_root / "tests",
        helen_root / "helen" / "agent" / "tests",
        helen_root / "wiki" / "skill_tests",
    ]

    total = 0
    changed = 0
    for target in targets:
        if not target.exists():
            continue
        files = sorted(target.rglob("*.helen"))
        if not files:
            continue
        print(f"\n{target.relative_to(helen_root)}/:")
        for f in files:
            total += 1
            if process_file(f, apply):
                changed += 1

    print(f"\n{'=' * 60}")
    print(f"Total: {total} files, {'Changed' if apply else 'Would change'}: {changed}")
    if not apply:
        print("Run with --apply to write changes")


if __name__ == '__main__':
    main()
