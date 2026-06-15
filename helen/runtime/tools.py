"""Built-in tool registry for Helen programs.

Provides a set of tools that LLM can call during `llm act` execution.
Each tool has an OpenAI-format schema and a Python handler function.

Tools are registered at module level and discovered by name.
"""

from __future__ import annotations

import json
import urllib.request
import urllib.error
import urllib.parse
from dataclasses import dataclass, field
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
        return json.dumps({"error": f"Unknown tool: {name}"})
    try:
        return tool.handler(**args)
    except Exception as e:
        return json.dumps({"error": f"Tool '{name}' failed: {type(e).__name__}: {e}"})


# ── Built-in Tool Implementations ──────────────────────────────


def _web_search(query: str, num_results: int = 3) -> str:
    """Search the web and return results.

    Uses Wikipedia API as primary source (reliable, no API key needed).
    Falls back to DuckDuckGo lite if Wikipedia has no results.
    """
    import re

    results = []

    # Try Wikipedia API first (reliable, structured)
    try:
        wiki_url = (
            f"https://en.wikipedia.org/api/rest_v1/page/summary/"
            f"{urllib.parse.quote(query.replace(' ', '_'))}"
        )
        req = urllib.request.Request(wiki_url, headers={
            "User-Agent": "HelenAgent/1.0 (https://github.com/hahalee000000/helen)",
        })
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        if data.get("type") != "not_found":
            title = data.get("title", query)
            extract = data.get("extract", "")
            url = data.get("content_urls", {}).get("desktop", {}).get("page", "")
            results.append(f"- {title}\n  {extract[:300]}\n  {url}")
    except Exception:
        pass

    # Also try Wikipedia search for multiple results
    try:
        search_url = (
            f"https://en.wikipedia.org/w/api.php?"
            f"action=opensearch&search={urllib.parse.quote(query)}"
            f"&limit={num_results}&format=json"
        )
        req = urllib.request.Request(search_url, headers={
            "User-Agent": "HelenAgent/1.0 (https://github.com/hahalee000000/helen)",
        })
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        # opensearch returns [query, [titles], [descriptions], [urls]]
        if len(data) >= 4:
            titles = data[1]
            descriptions = data[2]
            urls = data[3]
            for t, d, u in zip(titles, descriptions, urls):
                entry = f"- {t}"
                if d:
                    entry += f"\n  {d}"
                entry += f"\n  {u}"
                if entry not in results:
                    results.append(entry)
    except Exception:
        pass

    if not results:
        return json.dumps({"results": [], "message": f"No results found for '{query}'."})
    return json.dumps({"results": results[:num_results]})


def _web_fetch(url: str) -> str:
    """Fetch the text content of a URL."""
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (compatible; Helen/1.0)"
    })
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            content = resp.read().decode("utf-8", errors="replace")
        # Strip HTML tags for a rough text extraction
        import re
        text = re.sub(r'<script[^>]*>.*?</script>', '', content, flags=re.DOTALL)
        text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL)
        text = re.sub(r'<[^>]+>', ' ', text)
        text = re.sub(r'\s+', ' ', text).strip()
        # Truncate to reasonable length
        if len(text) > 8000:
            text = text[:8000] + "... [truncated]"
        return json.dumps({"url": url, "content": text})
    except Exception as e:
        return json.dumps({"error": f"Fetch failed: {e}"})


def _read_file(path: str) -> str:
    """Read the content of a local file."""
    try:
        from pathlib import Path
        content = Path(path).read_text(encoding="utf-8")
        if len(content) > 16000:
            content = content[:16000] + "\n... [truncated]"
        return json.dumps({"path": path, "content": content})
    except Exception as e:
        return json.dumps({"error": f"Read failed: {e}"})


def _write_file(path: str, content: str) -> str:
    """Write content to a local file."""
    try:
        from pathlib import Path
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).write_text(content, encoding="utf-8")
        return json.dumps({"path": path, "bytes_written": len(content), "status": "ok"})
    except Exception as e:
        return json.dumps({"error": f"Write failed: {e}"})


def _shell_exec(command: str, timeout: int = 30) -> str:
    """Execute a shell command and return output."""
    import subprocess
    try:
        result = subprocess.run(
            command, shell=True, capture_output=True, text=True,
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
        })
    except subprocess.TimeoutExpired:
        return json.dumps({"error": f"Command timed out after {timeout}s"})
    except Exception as e:
        return json.dumps({"error": f"Exec failed: {e}"})


def _calculate(expression: str) -> str:
    """Evaluate a mathematical expression safely."""
    import ast
    import math
    try:
        # Only allow safe operations
        tree = ast.parse(expression, mode='eval')
        # Walk the AST to ensure no dangerous nodes
        allowed_types = (
            ast.Expression, ast.BinOp, ast.UnaryOp, ast.Constant, ast.Num,
            ast.Add, ast.Sub, ast.Mult, ast.Div, ast.FloorDiv,
            ast.Mod, ast.Pow, ast.USub, ast.UAdd,
            ast.Call, ast.Name, ast.Attribute, ast.Load,
        )
        for node in ast.walk(tree):
            if not isinstance(node, allowed_types):
                return json.dumps({"error": f"Unsafe expression node: {type(node).__name__}"})
            # Block imports and other dangerous names
            if isinstance(node, ast.Name) and node.id not in (
                'math', 'sqrt', 'abs', 'round', 'sin', 'cos', 'tan',
                'log', 'log10', 'pi', 'e', 'pow', 'ceil', 'floor',
                'exp', 'asin', 'acos', 'atan', 'degrees', 'radians',
            ):
                return json.dumps({"error": f"Unsafe name: {node.id}"})
        # Provide safe math namespace
        safe_ns = {"__builtins__": {}, "math": math,
                    "sqrt": math.sqrt, "abs": abs, "round": round,
                    "sin": math.sin, "cos": math.cos, "tan": math.tan,
                    "log": math.log, "log10": math.log10, "pi": math.pi, "e": math.e,
                    "pow": pow, "ceil": math.ceil, "floor": math.floor,
                    "exp": math.exp, "asin": math.asin, "acos": math.acos,
                    "atan": math.atan, "degrees": math.degrees, "radians": math.radians}
        result = eval(compile(tree, '<expr>', 'eval'), safe_ns)
        return json.dumps({"expression": expression, "result": result})
    except Exception as e:
        return json.dumps({"error": f"Calculation failed: {e}"})


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
            return json.dumps({"error": f"File not found: {path}"})

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
            return json.dumps({"error": error, "hint": hint})

        if match_count == 0:
            return json.dumps({"error": "No matches found"})

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
        })

    except Exception as e:
        return json.dumps({"error": f"Patch failed: {e}"})


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
        description="Execute a shell command and return stdout/stderr output.",
        parameters={
            "type": "object",
            "properties": {
                "command": {"type": "string", "description": "Shell command to execute"},
                "timeout": {"type": "integer", "description": "Timeout in seconds (default 30)", "default": 30},
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


# Auto-register on import
_register_builtin_tools()
