"""Built-in tool registry for Helen programs.

Provides a set of tools that LLM can call during `llm act` execution.
Each tool has an OpenAI-format schema and a Python handler function.

Tools are registered at module level and discovered by name.
"""

from __future__ import annotations

import json
import os
import urllib.request
import urllib.error
import urllib.parse
from dataclasses import dataclass
from typing import Any, Callable


@dataclass
class HelenTool:
    """A tool available to the LLM during llm act."""

    name: str
    description: str
    parameters: dict[str, Any]
    handler: Callable[..., str]


# Global tool registry
_tools: dict[str, HelenTool] = {}


def register_tool(name: str, description: str, parameters: dict[str, Any],
                  handler: Callable[..., str]) -> None:
    """Register a tool in the global registry."""
    _tools[name] = HelenTool(
        name=name,
        description=description,
        parameters=parameters,
        handler=handler,
    )


def get_tool(name: str) -> HelenTool | None:
    """Look up a tool by name."""
    return _tools.get(name)


def list_tools() -> list[HelenTool]:
    """Return all registered tools."""
    return list(_tools.values())


def get_tool_schemas(tool_names: list[str] | None = None) -> list[dict[str, Any]]:
    """Return OpenAI-format tool schemas for the given tool names.

    If tool_names is None, returns all registered tools.
    """
    names = tool_names if tool_names is not None else list(_tools.keys())
    schemas = []
    for name in names:
        tool = _tools.get(name)
        if tool is None:
            continue
        schemas.append({
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.parameters,
            },
        })
    return schemas


def dispatch_tool(name: str, args: dict[str, Any]) -> str:
    """Execute a tool by name with the given arguments.

    Returns the tool result as a string, or an error message.
    """
    tool = _tools.get(name)
    if tool is None:
        return json.dumps({"error": f"Unknown tool: {name}"}, ensure_ascii=False)
    try:
        return tool.handler(**args)
    except Exception as e:
        return json.dumps({"error": f"Tool '{name}' failed: {type(e).__name__}: {e}"}, ensure_ascii=False)


# ── Built-in Tool Implementations ──────────────────────────────


def _web_search(query: str, num_results: int = 3) -> str:
    """Search the web using Bing and return results.

    Uses Bing.com search (accessible in China, no API key needed).
    Parses HTML search results page.
    """
    import re

    results = []

    try:
        # Build Bing search URL
        search_url = f"https://www.bing.com/search?q={urllib.parse.quote(query)}&count={num_results}"
        req = urllib.request.Request(search_url, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate"
        })

        with urllib.request.urlopen(req, timeout=15) as resp:
            # Handle content encoding
            content_encoding = resp.headers.get('Content-Encoding', '').lower()
            raw_data = resp.read()

            if content_encoding == 'gzip':
                import gzip
                raw_data = gzip.decompress(raw_data)
            elif content_encoding == 'deflate':
                import zlib
                raw_data = zlib.decompress(raw_data)

            html = raw_data.decode("utf-8", errors="replace")

        # Extract search results container
        results_match = re.search(r'<ol id="b_results"(.*?)</ol>', html, re.DOTALL)
        if not results_match:
            return json.dumps({"results": [], "message": f"No results found for '{query}'."}, ensure_ascii=False)

        results_html = results_match.group(1)

        # Find all search result blocks (b_algo class)
        algo_items = re.findall(r'<li class="b_algo"(.*?)</li>', results_html, re.DOTALL)

        for item in algo_items[:num_results]:
            # Extract title and URL from <h2><a href="URL">Title</a></h2>
            title_match = re.search(r'<h2[^>]*><a[^>]+href="([^"]+)"[^>]*>(.*?)</a>', item, re.DOTALL)
            if not title_match:
                continue

            url = title_match.group(1)
            title_html = title_match.group(2)
            # Remove HTML tags and clean up
            title = re.sub(r'<[^>]+>', '', title_html).strip()

            # Extract description from <p class="b_lineclamp..."> or <div class="b_caption">
            snippet = ""
            desc_match = re.search(r'<p[^>]*class="b_lineclamp[^"]*"[^>]*>(.*?)</p>', item, re.DOTALL)
            if not desc_match:
                desc_match = re.search(r'<div class="b_caption"[^>]*>(.*?)</div>', item, re.DOTALL)

            if desc_match:
                snippet_html = desc_match.group(1)
                snippet = re.sub(r'<[^>]+>', '', snippet_html).strip()
                # Clean up whitespace and HTML entities
                snippet = re.sub(r'\s+', ' ', snippet)
                snippet = snippet.replace('&ensp;', ' ').replace('&amp;', '&')

            # Format result
            entry = f"- {title}\n  {snippet}\n  {url}"
            results.append(entry)

    except Exception as e:
        import logging
        logging.debug("Bing search failed for query %r: %s", query, e)
        return json.dumps({"results": [], "message": f"Search failed: {e}"}, ensure_ascii=False)

    if not results:
        return json.dumps({"results": [], "message": f"No results found for '{query}'."}, ensure_ascii=False)
    return json.dumps({"results": results}, ensure_ascii=False)


def _web_fetch(url: str) -> str:
    """Fetch the text content of a URL."""
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (compatible; Helen/1.0)",
        "Accept-Encoding": "gzip, deflate"
    })
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            # Handle content encoding (gzip/deflate)
            content_encoding = resp.headers.get('Content-Encoding', '').lower()
            raw_data = resp.read()

            # Decompress if needed
            if content_encoding == 'gzip':
                import gzip
                raw_data = gzip.decompress(raw_data)
            elif content_encoding == 'deflate':
                import zlib
                raw_data = zlib.decompress(raw_data)

            # Decode to text
            content = raw_data.decode("utf-8", errors="replace")

        # Strip HTML tags for a rough text extraction
        import re
        text = re.sub(r'<script[^>]*>.*?</script>', '', content, flags=re.DOTALL)
        text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL)
        text = re.sub(r'<[^>]+>', ' ', text)
        text = re.sub(r'\s+', ' ', text).strip()
        # Truncate to reasonable length
        if len(text) > 8000:
            text = text[:8000] + "... [truncated]"
        return json.dumps({"url": url, "content": text}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": f"Fetch failed: {e}"}, ensure_ascii=False)


def _read_file(path: str) -> str:
    """Read the content of a local file."""
    try:
        from pathlib import Path
        content = Path(path).read_text(encoding="utf-8")
        if len(content) > 16000:
            content = content[:16000] + "\n... [truncated]"
        return json.dumps({"path": path, "content": content}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": f"Read failed: {e}"}, ensure_ascii=False)


def _write_file(path: str, content: str) -> str:
    """Write content to a local file."""
    try:
        from pathlib import Path
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).write_text(content, encoding="utf-8")
        return json.dumps({"path": path, "bytes_written": len(content), "status": "ok"}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": f"Write failed: {e}"}, ensure_ascii=False)


def _shell_exec(command: str, timeout: int = 30, shell: bool = True) -> str:
    """Execute a shell command and return output.

    Args:
        command: Command to execute. When shell=True (default), passed as string
                 to the shell. When shell=False, split into args for safety.
        timeout: Timeout in seconds (default 30).
        shell: Whether to use shell execution (default True).

    Note: When shell=True, be careful with user input to avoid shell injection.
    Use shell=False for commands with untrusted input.
    """
    import shlex
    import subprocess

    try:
        cmd = command if shell else shlex.split(command)
        result = subprocess.run(
            cmd, shell=shell, capture_output=True, text=True,
            timeout=timeout,
        )
        output = result.stdout
        if result.stderr:
            output += f"\n[stderr] {result.stderr}"
        if len(output) > 8000:
            output = output[:8000] + "\n... [truncated]"
        return json.dumps({
            "command": command,
            "exit_code": result.returncode,
            "output": output,
        }, ensure_ascii=False)
    except subprocess.TimeoutExpired:
        return json.dumps({"error": f"Command timed out after {timeout}s"}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": f"Exec failed: {e}"}, ensure_ascii=False)


def _calculate(expression: str) -> str:
    """Evaluate a mathematical expression safely."""
    import ast
    import math
    try:
        # Only allow safe operations
        tree = ast.parse(expression, mode='eval')
        # Walk the AST to ensure no dangerous nodes
        allowed_types = (
            ast.Expression, ast.BinOp, ast.UnaryOp, ast.Constant,
            ast.Add, ast.Sub, ast.Mult, ast.Div, ast.FloorDiv,
            ast.Mod, ast.Pow, ast.USub, ast.UAdd,
            ast.Call, ast.Name, ast.Attribute, ast.Load,
        )
        for node in ast.walk(tree):
            if not isinstance(node, allowed_types):
                return json.dumps({"error": f"Unsafe expression node: {type(node).__name__}"}, ensure_ascii=False)
            # Block imports and other dangerous names
            if isinstance(node, ast.Name) and node.id not in (
                'math', 'sqrt', 'abs', 'round', 'sin', 'cos', 'tan',
                'log', 'log10', 'pi', 'e', 'pow', 'ceil', 'floor',
                'exp', 'asin', 'acos', 'atan', 'degrees', 'radians',
            ):
                return json.dumps({"error": f"Unsafe name: {node.id}"}, ensure_ascii=False)
        # Provide safe math namespace
        safe_ns = {"__builtins__": {}, "math": math,
                   "sqrt": math.sqrt, "abs": abs, "round": round,
                   "sin": math.sin, "cos": math.cos, "tan": math.tan,
                   "log": math.log, "log10": math.log10, "pi": math.pi, "e": math.e,
                   "pow": pow, "ceil": math.ceil, "floor": math.floor,
                   "exp": math.exp, "asin": math.asin, "acos": math.acos,
                   "atan": math.atan, "degrees": math.degrees, "radians": math.radians}
        result = eval(compile(tree, '<expr>', 'eval'), safe_ns)
        return json.dumps({"expression": expression, "result": result}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": f"Calculation failed: {e}"}, ensure_ascii=False)


def _patch_file(path: str, old_string: str, new_string: str, replace_all: bool = False) -> str:
    """Patch a file using fuzzy matching (Hermes fuzzy_match engine).

    Uses 9 matching strategies to handle whitespace/indentation differences:
    1. Exact match
    2. Line-trimmed match
    3. Whitespace-normalized match
    4. Indentation-flexible match
    5. Escape-normalized match
    6. Trimmed-boundary match
    7. Unicode-normalized match
    8. Block-anchor match (SequenceMatcher)
    9. Context-aware match (line-by-line similarity)
    """
    from pathlib import Path
    try:
        file_path = Path(path)
        if not file_path.exists():
            return json.dumps({"error": f"File not found: {path}"}, ensure_ascii=False)

        content = file_path.read_text(encoding="utf-8")
        # Strip UTF-8 BOM if present
        if content.startswith('\ufeff'):
            content = content[1:]

        # Use Helen's built-in fuzzy matching (copied from Hermes)
        from helen.runtime.fuzzy_match import fuzzy_find_and_replace, format_no_match_hint

        # Use Hermes fuzzy matching
        new_content, match_count, strategy, error = fuzzy_find_and_replace(
            content, old_string, new_string, replace_all=replace_all
        )

        if error:
            # Generate helpful hint
            hint = format_no_match_hint(error, match_count, old_string, content)
            return json.dumps({"error": error, "hint": hint}, ensure_ascii=False)

        if match_count == 0:
            return json.dumps({"error": "No matches found"}, ensure_ascii=False)

        # Write the patched content
        file_path.write_text(new_content, encoding="utf-8")

        # Generate unified diff for feedback
        import difflib
        diff_lines = difflib.unified_diff(
            content.splitlines(keepends=True),
            new_content.splitlines(keepends=True),
            fromfile=f"a/{path}",
            tofile=f"b/{path}",
            lineterm=""
        )
        diff = "".join(diff_lines)
        if len(diff) > 4000:
            diff = diff[:4000] + "\n... [diff truncated]"

        return json.dumps({
            "path": path,
            "status": "patched",
            "matches": match_count,
            "strategy": strategy,
            "diff": diff,
        }, ensure_ascii=False)

    except Exception as e:
        return json.dumps({"error": f"Patch failed: {e}"}, ensure_ascii=False)


def _load_skill(name: str) -> str:
    """Load a skill's full SKILL.md content by name.

    Searches skill directories in priority order:
    1. ~/.helen/skills/ (Helen native)
    2. ~/.hermes/skills/ (Hermes fallback)
    3. ~/.hermes/hermes-agent/skills/ (Hermes agent skills)

    This is the Tier 2 of the two-phase skill disclosure:
    - Tier 1: Skill Index (lightweight) injected in System Prompt
    - Tier 2: Full SKILL.md loaded on-demand via this tool
    """
    from pathlib import Path
    from helen.runtime.config import get_skill_dirs

    try:
        # Search all skill directories
        for base in get_skill_dirs():
            base_str = str(base)
            if not Path(base_str).exists():
                continue

            # Walk the skill directory tree
            for root, dirs, files in os.walk(base_str):
                # Match by directory name
                if os.path.basename(root) == name and "SKILL.md" in files:
                    skill_path = os.path.join(root, "SKILL.md")
                    with open(skill_path, encoding="utf-8") as f:
                        content = f.read()
                    return json.dumps({
                        "name": name,
                        "path": skill_path,
                        "content": content,
                    }, ensure_ascii=False)

        return json.dumps({"error": f"Skill '{name}' not found in any skill directory"}, ensure_ascii=False)

    except Exception as e:
        return json.dumps({"error": f"Load skill failed: {e}"}, ensure_ascii=False)


# ── Register all built-in tools ────────────────────────────────


def _register_builtin_tools() -> None:
    """Register all built-in tools."""
    register_tool(
        name="web_search",
        description="Search the web for information. Returns search results with titles, snippets, and links.",
        parameters={
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"},
                "num_results": {"type": "integer", "description": "Number of results (default 3)", "default": 3},
            },
            "required": ["query"],
        },
        handler=_web_search,
    )

    register_tool(
        name="web_fetch",
        description="Fetch the text content of a web page by URL.",
        parameters={
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "URL to fetch"},
            },
            "required": ["url"],
        },
        handler=_web_fetch,
    )

    register_tool(
        name="read_file",
        description="Read the content of a local file by path.",
        parameters={
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "File path to read"},
            },
            "required": ["path"],
        },
        handler=_read_file,
    )

    register_tool(
        name="write_file",
        description="Write content to a local file. Creates parent directories if needed.",
        parameters={
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "File path to write"},
                "content": {"type": "string", "description": "Content to write"},
            },
            "required": ["path", "content"],
        },
        handler=_write_file,
    )

    register_tool(
        name="shell_exec",
        description="Execute a command and return stdout/stderr output. Uses safe mode (shell=False) by default.",
        parameters={
            "type": "object",
            "properties": {
                "command": {"type": "string", "description": "Command to execute"},
                "timeout": {"type": "integer", "description": "Timeout in seconds (default 30)", "default": 30},
                "shell": {"type": "boolean", "description": "Use shell execution (default: false for safety)", "default": False},
            },
            "required": ["command"],
        },
        handler=_shell_exec,
    )

    register_tool(
        name="calculate",
        description="Evaluate a mathematical expression. Supports basic arithmetic and math functions (sqrt, sin, cos, log, etc.).",
        parameters={
            "type": "object",
            "properties": {
                "expression": {"type": "string", "description": "Math expression to evaluate, e.g. 'sqrt(16) + 2**3'"},
            },
            "required": ["expression"],
        },
        handler=_calculate,
    )

    register_tool(
        name="patch_file",
        description="Patch a file by replacing old_string with new_string. Uses fuzzy matching (9 strategies) to handle whitespace/indentation differences. More reliable than write_file for targeted edits.",
        parameters={
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "File path to patch"},
                "old_string": {"type": "string", "description": "Text to find and replace (should be unique in file)"},
                "new_string": {"type": "string", "description": "Replacement text"},
                "replace_all": {"type": "boolean", "description": "Replace all occurrences (default: false, requires unique match)", "default": False},
            },
            "required": ["path", "old_string", "new_string"],
        },
        handler=_patch_file,
    )

    register_tool(
        name="load_skill",
        description="Load a skill's full SKILL.md content by name. Use this to get detailed instructions for a skill listed in <available_skills>.",
        parameters={
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Skill name to load (from <available_skills> list)"},
            },
            "required": ["name"],
        },
        handler=_load_skill,
    )


# Auto-register on import
_register_builtin_tools()
