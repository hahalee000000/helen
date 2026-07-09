#!/usr/bin/env python3
"""
Tutorial Test Generator

Extracts ```helen code blocks from wiki/tutorial/*.md and generates
.helen test files for validation with `helen check`.

Usage:
    python generate_tests.py
"""

import re
import sys
from pathlib import Path
from dataclasses import dataclass, field

TUTORIAL_DIR = Path(__file__).resolve().parent
TESTS_DIR = TUTORIAL_DIR / "tests"


@dataclass
class CodeBlock:
    source_file: str
    line_num: int
    code: str
    cleaned_code: str = ""
    block_type: str = "fragment"  # complete, fragment, error, skip
    skip_reason: str = ""


def extract_blocks(content: str, filename: str) -> list:
    """Extract ```helen code blocks from markdown content."""
    blocks = []
    pattern = re.compile(r"```helen\n(.*?)```", re.DOTALL)

    for match in pattern.finditer(content):
        code = match.group(1).strip()
        line_num = content[:match.start()].count('\n') + 2

        blocks.append(CodeBlock(
            source_file=filename,
            line_num=line_num,
            code=code
        ))

    return blocks


def clean_code(code: str) -> str:
    """Remove output annotations and clean code."""
    lines = []
    for line in code.split('\n'):
        # Skip output-only lines
        if re.match(r'^\s*//\s*→', line):
            continue
        if re.match(r'^\s*//\s*输出:', line):
            continue
        # Remove trailing annotations
        line = re.sub(r'\s*//\s*→.*$', '', line)
        line = re.sub(r'\s*//\s*输出:.*$', '', line)
        lines.append(line)

    return '\n'.join(lines).strip()


def classify_block(code: str, cleaned: str) -> tuple:
    """
    Classify a code block.

    Returns:
        (type, skip_reason)
        type: 'complete', 'fragment', 'error', 'skip'
    """
    # Check for error markers
    if '❌' in code or re.search(r'//\s*Error:', code) or re.search(r'//\s*❌', code):
        return ('error', '')

    # Check for file imports
    if re.search(r'import\s+["\']\./', code):
        return ('skip', 'needs external file import')

    # Check for Python FFI imports
    if re.search(r'import\s+["\'](?:math|json|os|sys|random|datetime|collections|itertools|functools|pathlib|re)', code):
        return ('skip', 'needs Python module import')

    # Check if empty or comment-only
    lines = [l.strip() for l in cleaned.split('\n') if l.strip() and not l.strip().startswith('//')]
    if not lines:
        return ('skip', 'empty or comment-only')

    # Check if it's a complete program (has main or only declarations)
    if re.search(r'\bmain\s*\{', cleaned):
        return ('complete', '')

    # Check if all non-empty lines are declarations
    decl_patterns = [
        r'^(agent|fn|const|let|shared\s+let|enum|protocol|struct)\s+',
        r'^import\s+',
        r'^alias\s+',
    ]
    is_all_declarations = all(
        any(re.match(p, line) for p in decl_patterns)
        for line in lines
    )

    if is_all_declarations:
        return ('complete', '')

    return ('fragment', '')


def extract_declaration_names(code: str) -> set:
    """Extract names of declared functions, agents, and variables."""
    names = set()

    # Extract function names: fn name(
    for match in re.finditer(r'\bfn\s+(\w+)\s*\(', code):
        names.add(match.group(1))

    # Extract agent names: agent Name
    for match in re.finditer(r'\bagent\s+(\w+)', code):
        names.add(match.group(1))

    # Extract variable names: let name = or const name =
    for match in re.finditer(r'\b(?:let|const|shared\s+let)\s+(\w+)\s*=', code):
        names.add(match.group(1))

    return names


def filter_context_to_avoid_duplicates(context: str, new_code: str) -> str:
    """Filter context to remove declarations that are redefined in new_code."""
    if not context:
        return context

    # Get names declared in the new code
    new_names = extract_declaration_names(new_code)

    if not new_names:
        return context

    # Filter context lines to remove declarations that conflict
    filtered_lines = []
    skip_until_brace_close = False
    brace_depth = 0

    for line in context.split('\n'):
        # Check if this line declares something that's redefined
        should_skip = False
        for name in new_names:
            # Check for function/agent declaration
            if re.match(rf'\s*(?:fn\s+{name}\s*\(|agent\s+{name}\b)', line):
                should_skip = True
                # Check if this is a multi-line declaration
                if '{' in line and '}' not in line:
                    skip_until_brace_close = True
                    brace_depth = line.count('{') - line.count('}')
                break
            # Check for variable declaration
            if re.match(rf'\s*(?:let|const|shared\s+let)\s+{name}\s*=', line):
                should_skip = True
                break

        if skip_until_brace_close:
            brace_depth += line.count('{') - line.count('}')
            if brace_depth <= 0:
                skip_until_brace_close = False
            continue

        if not should_skip:
            filtered_lines.append(line)

    return '\n'.join(filtered_lines).strip()


def remove_main_block(code: str) -> str:
    """Remove main block from code, keeping everything else."""
    result = []
    in_main = False
    brace_depth = 0

    for line in code.split('\n'):
        if not in_main and re.search(r'\bmain\s*\{', line):
            in_main = True
            brace_depth = line.count('{') - line.count('}')
            if brace_depth <= 0:
                in_main = False
            continue

        if in_main:
            brace_depth += line.count('{') - line.count('}')
            if brace_depth <= 0:
                in_main = False
            continue

        result.append(line)

    return '\n'.join(result).strip()


def generate_test_file(block: CodeBlock, context: str, output_dir: Path, block_num: int) -> Path:
    """Generate a .helen test file."""

    # Determine filename
    safe_name = re.sub(r'[^\w]', '_', block.source_file.replace('.md', ''))[:30]
    filename = f'block_{block_num:03d}_{safe_name}.helen'
    filepath = output_dir / filename

    # Build file content
    lines = []

    # Header
    lines.append(f'// Test: {block.source_file}:{block.line_num}')

    if block.block_type == 'error':
        lines.append('// @should_fail')
    elif block.block_type == 'skip':
        lines.append(f'// @skip: {block.skip_reason}')

    lines.append('')

    # Context for fragments
    if context and block.block_type == 'fragment':
        lines.append('// === Context from preceding blocks ===')
        lines.append(context)
        lines.append('')
        lines.append('// === Test code ===')

    # Add the code
    lines.append(block.cleaned_code)

    # Write file
    filepath.write_text('\n'.join(lines), encoding='utf-8')

    return filepath


def process_tutorial_file(md_file: Path) -> dict:
    """Process a single tutorial markdown file."""

    content = md_file.read_text(encoding='utf-8')
    blocks = extract_blocks(content, md_file.name)

    if not blocks:
        return {'file': md_file.name, 'total': 0, 'generated': 0, 'skipped': 0, 'errors': 0}

    # Create output directory
    dir_name = md_file.stem
    output_dir = TESTS_DIR / dir_name
    output_dir.mkdir(parents=True, exist_ok=True)

    # Process blocks
    context = ''
    stats = {'total': 0, 'generated': 0, 'skipped': 0, 'errors': 0}
    block_num = 0

    for block in blocks:
        stats['total'] += 1

        # Clean code
        block.cleaned_code = clean_code(block.code)

        # Classify
        block_type, skip_reason = classify_block(block.code, block.cleaned_code)
        block.block_type = block_type
        block.skip_reason = skip_reason

        # Skip if needed
        if block_type == 'skip':
            stats['skipped'] += 1
            block_num += 1
            generate_test_file(block, '', output_dir, block_num)
            stats['generated'] += 1
            continue

        # Extract context from complete blocks (everything except main)
        if block_type == 'complete':
            ctx = remove_main_block(block.cleaned_code)
            if ctx:
                context += ('\n\n' if context else '') + ctx

        # Generate test file with filtered context to avoid duplicates
        block_num += 1
        filtered_context = filter_context_to_avoid_duplicates(context, block.cleaned_code)
        generate_test_file(block, filtered_context, output_dir, block_num)
        stats['generated'] += 1

        if block_type == 'error':
            stats['errors'] += 1

    return {'file': md_file.name, **stats}


def main():
    """Main entry point."""

    # Create tests directory
    TESTS_DIR.mkdir(parents=True, exist_ok=True)

    # Find all tutorial files
    tutorial_files = sorted(TUTORIAL_DIR.glob('*.md'))

    if not tutorial_files:
        print(f"No tutorial files found in {TUTORIAL_DIR}")
        sys.exit(1)

    print(f"Processing {len(tutorial_files)} tutorial files...")
    print(f"Output directory: {TESTS_DIR}")
    print()

    # Process each file
    total_stats = {'total': 0, 'generated': 0, 'skipped': 0, 'errors': 0}

    for md_file in tutorial_files:
        stats = process_tutorial_file(md_file)

        if stats['total'] > 0:
            print(f"{stats['file']}:")
            print(f"  Total blocks: {stats['total']}")
            print(f"  Generated: {stats['generated']}")
            print(f"  Skipped: {stats['skipped']}")
            print(f"  Error examples: {stats['errors']}")
            print()

        for key in total_stats:
            total_stats[key] += stats.get(key, 0)

    print("=" * 60)
    print("Summary:")
    print(f"  Total blocks: {total_stats['total']}")
    print(f"  Generated: {total_stats['generated']}")
    print(f"  Skipped: {total_stats['skipped']}")
    print(f"  Error examples: {total_stats['errors']}")
    print("=" * 60)


if __name__ == '__main__':
    main()
