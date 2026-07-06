#!/usr/bin/env python3
"""Build docs/tutorial.md from wiki/tutorial/*.md (canonical source → generated output).

Usage:
    python3 scripts/build_tutorial.py

This script reads all numbered tutorial files (NN-*.md) from wiki/tutorial/,
strips YAML frontmatter, and concatenates them into docs/tutorial.md with:
- A header indicating auto-generation
- A table of contents
- Chapter separators

The wiki/tutorial/ directory is the canonical source — edit files there,
then re-run this script to regenerate docs/tutorial.md.
"""

import glob
import os
import re
from datetime import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TUTORIAL_DIR = os.path.join(ROOT, "wiki", "tutorial")
OUTPUT = os.path.join(ROOT, "docs", "tutorial.md")

HEADER = """\
# Helen 语言完整教程

> **Helen** — A Prompt-first Agent Programming Language
> 版本: v1.15 | 状态: Phase 0-10 + Phase 1-7 上下文管理 + 中文语法 + Agent 隔离

<!-- ⚠️ AUTO-GENERATED — DO NOT EDIT MANUALLY -->
<!-- Generated from wiki/tutorial/*.md by scripts/build_tutorial.py -->
<!-- Generated at: {timestamp} -->

---

<!-- TABLE OF CONTENTS -->

{toc}

---

"""

FOOTER = """
---

<!-- Auto-generated from wiki/tutorial/*.md | {timestamp} | Helen v1.15 -->
"""


def get_tutorial_files():
    """Get sorted list of tutorial files (NN-*.md pattern)."""
    pattern = os.path.join(TUTORIAL_DIR, "[0-9][0-9]-*.md")
    files = sorted(glob.glob(pattern))
    return files


def extract_title(content):
    """Extract first H1 title from markdown content."""
    for line in content.split("\n"):
        if line.startswith("# "):
            return line[2:].strip()
    return "Untitled"


def extract_subtitle(content):
    """Extract subtitle from blockquote line."""
    for line in content.split("\n"):
        if line.startswith("> ") and not line.startswith("> **"):
            return line[2:].strip()
    return ""


def build_toc(files):
    """Build table of contents from tutorial files."""
    lines = ["| 章节 | 主题 |", "|------|------|"]
    for f in files:
        with open(f, encoding="utf-8") as fh:
            content = fh.read()
        title = extract_title(content)
        subtitle = extract_subtitle(content)
        num = os.path.basename(f)[:2]
        # Build anchor from title
        anchor = title.lower().replace(" ", "-")
        # Remove CJK punctuation for cleaner anchors
        anchor = re.sub(r"[：（）]", "", anchor)
        anchor = anchor.strip("-")
        if subtitle:
            lines.append(f"| [{num}](#{anchor}) | {title} — {subtitle} |")
        else:
            lines.append(f"| [{num}](#{anchor}) | {title} |")
    return "\n".join(lines)


def strip_frontmatter(content):
    """Strip YAML frontmatter from markdown content."""
    if content.startswith("---"):
        end = content.find("---", 3)
        if end != -1:
            content = content[end + 3:].lstrip("\n")
    return content


def process_file(filepath):
    """Read file, strip frontmatter, return content with separator."""
    with open(filepath, encoding="utf-8") as fh:
        content = fh.read()
    content = strip_frontmatter(content)
    return content.rstrip() + "\n\n---\n\n"


def main():
    files = get_tutorial_files()
    if not files:
        print("ERROR: No tutorial files found in", TUTORIAL_DIR)
        return

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")

    toc = build_toc(files)
    header = HEADER.format(timestamp=timestamp, toc=toc)
    footer = FOOTER.format(timestamp=timestamp)

    parts = [header]
    for f in files:
        parts.append(process_file(f))
    parts.append(footer)

    output = "".join(parts)

    os.makedirs(os.path.dirname(OUTPUT), exist_ok=True)
    with open(OUTPUT, "w", encoding="utf-8") as out:
        out.write(output)

    print(f"Generated {OUTPUT}")
    print(f"  Files: {len(files)}")
    print(f"  Lines: {len(output.splitlines())}")
    for f in files:
        print(f"    - {os.path.basename(f)}")


if __name__ == "__main__":
    main()
