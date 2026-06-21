"""Test helpers for Helen Programming Agent tests."""

import json
import subprocess
import sys
from pathlib import Path
from typing import Any


HELEN_ROOT = Path(__file__).parent.parent.parent  # ~/helen/
AGENTS_DIR = HELEN_ROOT / "agents"
SKILLS_DIR = AGENTS_DIR / "skills"
MEMORY_DIR = AGENTS_DIR / "memory"


def run_helen(file_path: str, timeout: int = 30) -> dict[str, Any]:
    """Execute a Helen file and return the result.
    
    Args:
        file_path: Path to .helen file
        timeout: Execution timeout in seconds
    
    Returns:
        Dict with:
            - stdout: str
            - stderr: str
            - exit_code: int
            - success: bool
    """
    result = subprocess.run(
        [sys.executable, "-c", 
         f"from helen.cli.__main__ import main; import sys; sys.exit(main(['{file_path}']))"],
        capture_output=True,
        text=True,
        timeout=timeout,
        cwd=str(HELEN_ROOT),
    )
    
    return {
        "stdout": result.stdout,
        "stderr": result.stderr,
        "exit_code": result.returncode,
        "success": result.returncode == 0,
    }


def check_helen(file_path: str) -> dict[str, Any]:
    """Check a Helen file for syntax errors without executing.
    
    Returns:
        Dict with:
            - valid: bool
            - errors: list[str]
    """
    result = subprocess.run(
        [sys.executable, "-c",
         f"from helen.cli.__main__ import main; import sys; sys.exit(main(['check', '{file_path}']))"],
        capture_output=True,
        text=True,
        timeout=10,
        cwd=str(HELEN_ROOT),
    )
    
    errors = []
    if result.returncode != 0:
        errors = result.stderr.strip().split("\n") if result.stderr else ["Unknown error"]
    
    return {
        "valid": result.returncode == 0,
        "errors": errors,
    }


def create_test_skill(name: str, category: str, content: str | None = None) -> Path:
    """Create a test skill for testing purposes.
    
    Returns:
        Path to created SKILL.md
    """
    skill_dir = SKILLS_DIR / category / name
    skill_dir.mkdir(parents=True, exist_ok=True)
    
    if content is None:
        content = f"""---
name: {name}
description: "Test skill for {name}"
version: 1.0.0
category: {category}
tags: [test]
triggers:
  - error_type: "TestError"
    message_contains: "test"
confidence: 0.9
occurrences: 1
---

# Test Skill: {name}

## Trigger
Test trigger condition.

## Steps
1. Step one
2. Step two

## Pitfalls
- Watch out for X
"""
    
    skill_file = skill_dir / "SKILL.md"
    skill_file.write_text(content)
    return skill_file


def cleanup_test_skills():
    """Remove test skills created during testing."""
    import shutil
    for category_dir in SKILLS_DIR.iterdir():
        if category_dir.is_dir():
            for skill_dir in category_dir.iterdir():
                if skill_dir.is_dir() and skill_dir.name.startswith("test-"):
                    shutil.rmtree(skill_dir)


def rebuild_skill_index() -> bool:
    """Rebuild the skill index by scanning all skills.
    
    Returns:
        True if successful
    """
    index_path = SKILLS_DIR / "SKILL_INDEX.md"
    lines = [
        "# Helen Programming Agent — Skill Index",
        "",
        "> Auto-maintained skill catalog. Do not edit manually.",
        "",
    ]
    
    categories = {}
    for category_dir in sorted(SKILLS_DIR.iterdir()):
        if not category_dir.is_dir():
            continue
        category = category_dir.name
        if category.startswith("."):
            continue
        categories[category] = []
        
        for skill_dir in sorted(category_dir.iterdir()):
            if not skill_dir.is_dir():
                continue
            skill_file = skill_dir / "SKILL.md"
            if skill_file.exists():
                content = skill_file.read_text()
                # Extract description from frontmatter
                desc = "No description"
                for line in content.split("\n"):
                    if line.startswith("description:"):
                        desc = line.split(":", 1)[1].strip().strip('"')
                        break
                categories[category].append({
                    "name": skill_dir.name,
                    "description": desc,
                    "path": str(skill_file.relative_to(HELEN_ROOT)),
                })
    
    for category, skills in categories.items():
        if skills:
            lines.append(f"## {category}/")
            lines.append("")
            for skill in skills:
                lines.append(f"### {skill['name']}")
                lines.append(f"- **Description**: {skill['description']}")
                lines.append(f"- **Path**: {skill['path']}")
                lines.append("")
    
    index_path.write_text("\n".join(lines))
    return True
