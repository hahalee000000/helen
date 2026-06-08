"""Documentation generator for Hellen (HLD Phase 7).

Generates API documentation from source code by analyzing:
- Agent declarations (name, params, prompt, description)
- Function declarations (name, params, body)
- Built-in functions (from stdlib)

Output formats: Markdown, JSON.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from hellen.core.ast import (
    AgentDeclNode,
    AgentParamNode,
    DeclarationNode,
    FunctionDeclNode,
    LiteralNode,
    ProgramNode,
)
from hellen.core.errors import ErrorReporter
from hellen.core.lexer import Scanner
from hellen.core.parser import Parser


@dataclass
class AgentDoc:
    """Documentation for an agent declaration."""

    name: str
    description: str | None = None
    model: str | None = None
    temperature: float | None = None
    max_turns: int | None = None
    params: list[dict[str, str]] = None  # [{name, type}]
    prompt: str | None = None
    source_file: str = ""
    line: int = 0

    def __post_init__(self) -> None:
        if self.params is None:
            self.params = []

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {"name": self.name}
        if self.description:
            result["description"] = self.description
        if self.model:
            result["model"] = self.model
        if self.temperature is not None:
            result["temperature"] = self.temperature
        if self.max_turns:
            result["max_turns"] = self.max_turns
        if self.params:
            result["params"] = self.params
        if self.prompt:
            result["prompt"] = self.prompt
        if self.source_file:
            result["source_file"] = self.source_file
            result["line"] = self.line
        return result


@dataclass
class FunctionDoc:
    """Documentation for a function declaration."""

    name: str
    params: list[str] = None
    source_file: str = ""
    line: int = 0

    def __post_init__(self) -> None:
        if self.params is None:
            self.params = []

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "params": self.params,
            "source_file": self.source_file,
            "line": self.line,
        }


@dataclass
class BuiltinDoc:
    """Documentation for a built-in function."""

    name: str
    description: str
    signature: str
    category: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "signature": self.signature,
            "category": self.category,
        }


def extract_agent_doc(node: AgentDeclNode, source_file: str = "") -> AgentDoc:
    """Extract documentation from an AgentDeclNode."""
    doc = AgentDoc(
        name=node.name,
        source_file=source_file,
        line=node.span.start_line if node.span else 0,
    )

    # Extract params
    for param in node.params:
        if isinstance(param, AgentParamNode):
            doc.params.append({
                "name": param.name,
                "type": param.type_annotation.accept(_type_visitor())
                if param.type_annotation else "any",
            })

    # Extract declarations (description, model, temperature, max-turns)
    for decl in node.declarations:
        if isinstance(decl, DeclarationNode):
            if decl.description and isinstance(decl.description, LiteralNode):
                doc.description = str(decl.description.value)
            if decl.model and isinstance(decl.model, LiteralNode):
                doc.model = str(decl.model.value)
            if decl.temperature and isinstance(decl.temperature, LiteralNode):
                doc.temperature = float(decl.temperature.value)
            if decl.max_turns and isinstance(decl.max_turns, LiteralNode):
                doc.max_turns = int(decl.max_turns.value)

    return doc


def extract_function_doc(
    node: FunctionDeclNode, source_file: str = ""
) -> FunctionDoc:
    """Extract documentation from a FunctionDeclNode."""
    params = [p.name for p in node.params] if node.params else []
    return FunctionDoc(
        name=node.name,
        params=params,
        source_file=source_file,
        line=node.span.start_line if node.span else 0,
    )


class _type_visitor:
    """Minimal visitor to extract type name strings."""

    def visit(self, node: Any) -> str:
        if hasattr(node, 'accept'):
            return node.accept(self)
        return str(node)

    def visit_type(self, node: Any) -> str:
        return getattr(node, 'name', 'any')

    def visit_optional_type(self, node: Any) -> str:
        inner = self.visit(node.inner) if hasattr(node, 'inner') else 'any'
        return f"{inner}?"


def parse_source(source: str, source_file: str = "") -> ProgramNode | None:
    """Parse Hellen source into a ProgramNode."""
    errors = ErrorReporter()
    scanner = Scanner(source=source, file=source_file)
    tokens = scanner.scan_all()
    parser = Parser(tokens, errors=errors)
    return parser.parse()


def generate_docs(
    source_files: list[str],
    include_builtins: bool = False,
) -> dict[str, Any]:
    """Generate documentation for multiple source files.

    Args:
        source_files: List of .hellen file paths.
        include_builtins: Whether to include stdlib builtins (default: False).

    Returns:
        Documentation dict with agents, functions, builtins.
    """
    agents: list[AgentDoc] = []
    functions: list[FunctionDoc] = []

    for path in source_files:
        file_path = Path(path)
        if not file_path.exists():
            continue

        source = file_path.read_text(encoding="utf-8")
        program = parse_source(source, str(file_path))
        if program is None:
            continue

        for stmt in program.statements:
            if isinstance(stmt, AgentDeclNode):
                agents.append(extract_agent_doc(stmt, str(file_path)))
            elif isinstance(stmt, FunctionDeclNode):
                functions.append(extract_function_doc(stmt, str(file_path)))

    result: dict[str, Any] = {
        "agents": [a.to_dict() for a in agents],
        "functions": [f.to_dict() for f in functions],
    }

    if include_builtins:
        try:
            from hellen.stdlib import stdlib  # noqa: PLC0415
            result["builtins"] = [
                BuiltinDoc(
                    name=f.name,
                    description=f.description,
                    signature=f.signature,
                    category=f.category,
                ).to_dict()
                for f in stdlib.list_all()
            ]
        except ImportError:
            result["builtins"] = []

    return result


def format_markdown(docs: dict[str, Any]) -> str:
    """Format documentation as Markdown."""
    lines: list[str] = [
        "# Hellen API Documentation",
        "",
        "Auto-generated from source code analysis.",
        "",
    ]

    # Agents
    if docs.get("agents"):
        lines.append("## Agents")
        lines.append("")
        for agent in docs["agents"]:
            lines.append(f"### `{agent['name']}`")
            lines.append("")
            if agent.get("description"):
                lines.append(f"> {agent['description']}")
                lines.append("")
            if agent.get("params"):
                lines.append("**Parameters:**")
                lines.append("")
                for p in agent["params"]:
                    lines.append(f"- `{p['name']}`: {p.get('type', 'any')}")
                lines.append("")
            if agent.get("model"):
                lines.append(f"**Model:** {agent['model']}")
            if agent.get("source_file"):
                lines.append(f"**Source:** `{agent['source_file']}`:{agent.get('line', '?')}")
            lines.append("")

    # Functions
    if docs.get("functions"):
        lines.append("## Functions")
        lines.append("")
        for func in docs["functions"]:
            params = ", ".join(func["params"])
            lines.append(f"### `{func['name']}({params})`")
            lines.append("")
            if func.get("source_file"):
                lines.append(f"**Source:** `{func['source_file']}`:{func.get('line', '?')}")
            lines.append("")

    # Builtins
    if docs.get("builtins"):
        # Group by category
        categories: dict[str, list[dict]] = {}
        for b in docs["builtins"]:
            cat = b.get("category", "core")
            categories.setdefault(cat, []).append(b)

        for cat_name in sorted(categories):
            lines.append(f"## Built-in Functions ({cat_name})")
            lines.append("")
            lines.append("| Function | Signature | Description |")
            lines.append("|----------|-----------|-------------|")
            for b in sorted(categories[cat_name], key=lambda x: x["name"]):
                lines.append(
                    f"| `{b['name']}` | `{b['signature']}` | {b['description']} |"
                )
            lines.append("")

    return "\n".join(lines)


def generate_cli() -> int:
    """CLI entry point for docgen: `hellen doc <files...> [--format markdown|json]`."""
    import argparse  # noqa: PLC0415

    parser = argparse.ArgumentParser(description="Generate Hellen documentation")
    parser.add_argument("files", nargs="*", help=".hellen source files")
    parser.add_argument(
        "--format", choices=["markdown", "json"], default="markdown",
        help="Output format (default: markdown)",
    )
    parser.add_argument(
        "--with-builtins", action="store_true",
        help="Include built-in functions in documentation",
    )
    parser.add_argument(
        "-o", "--output", help="Output file path (default: stdout)",
    )

    args = parser.parse_args()

    docs = generate_docs(args.files, include_builtins=args.with_builtins)

    if args.format == "json":
        output = json.dumps(docs, indent=2, ensure_ascii=False)
    else:
        output = format_markdown(docs)

    if args.output:
        Path(args.output).write_text(output, encoding="utf-8")
    else:
        print(output)

    return 0
