"""Helen Language Server Protocol implementation (HLD M12, v1.30.5).

Provides IDE support via LSP:
- Diagnostics: real-time error reporting on file change
- Completion: keyword (91 bilingual) + stdlib + snippet templates
- Go-to-definition: navigate to agent/function/variable declarations
- Find references: cross-document symbol references
- Hover: type info and docstrings for stdlib functions
- Document symbols: outline view of agents/functions/classes/variables

Uses JSON-RPC 2.0 over stdio (LSP standard transport).
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field
from typing import Any


def _log(msg: str) -> None:
    """Log to stderr — visible in VS Code's 'Helen Language Server' output panel."""
    print(f"[helen-lsp] {msg}", file=sys.stderr, flush=True)


@dataclass
class Position:
    """LSP Position (0-based line and character)."""

    line: int
    character: int

    def to_dict(self) -> dict[str, int]:
        return {"line": self.line, "character": self.character}


@dataclass
class Range:
    """LSP Range."""

    start: Position
    end: Position

    def to_dict(self) -> dict[str, Any]:
        return {"start": self.start.to_dict(), "end": self.end.to_dict()}


@dataclass
class Diagnostic:
    """LSP Diagnostic."""

    range: Range
    severity: int  # 1=Error, 2=Warning, 3=Info, 4=Hint
    message: str
    source: str = "helen"
    code: str | None = None

    def to_dict(self) -> dict[str, Any]:
        result = {
            "range": self.range.to_dict(),
            "severity": self.severity,
            "message": self.message,
            "source": self.source,
        }
        if self.code:
            result["code"] = self.code
        return result


@dataclass
class CompletionItem:
    """LSP CompletionItem."""

    label: str
    kind: int = 1  # 1=Text, 2=Method, 3=Function, 4=Constructor, 5=Field, 6=Variable, 7=Class, 8=Interface, 9=Module, 10=Property, 11=Unit, 12=Value, 13=Enum, 14=Keyword, 15=Snippet, 16=Color, 17=File, 18=Reference, 19=Folder, 20=EnumMember
    detail: str | None = None
    insert_text: str | None = None
    insert_text_format: int | None = None  # 1=PlainText, 2=Snippet
    documentation: str | None = None

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {"label": self.label, "kind": self.kind}
        if self.detail:
            result["detail"] = self.detail
        if self.insert_text:
            result["insertText"] = self.insert_text
        if self.insert_text_format:
            result["insertTextFormat"] = self.insert_text_format
        if self.documentation:
            result["documentation"] = {"kind": "markdown", "value": self.documentation}
        return result


@dataclass
class Location:
    """LSP Location."""

    uri: str
    range: Range

    def to_dict(self) -> dict[str, Any]:
        return {"uri": self.uri, "range": self.range.to_dict()}


# ── Helen keywords for completion ─────────────────────────────
# Authoritative source: helen/core/tokens.py _KEYWORD_MAP (91 entries)
# plus context keywords recognized by the parser as identifiers.

HELLEN_KEYWORDS = [
    # === Formal keywords (from tokens.py _KEYWORD_MAP) ===
    # Agent keywords
    "agent", "main", "prompt", "description", "model", "temperature",
    "max-turns", "max-tokens", "tools", "streaming",
    # Variable declarations
    "let", "const", "shared",
    # Control flow
    "if", "else", "for", "in", "while",
    "break", "continue", "return",
    # Functions
    "fn", "call", "alias",
    # Error handling
    "try", "catch", "finally", "throw", "assert",
    # Pattern matching
    "match", "case", "branch", "default",
    # Imports
    "import", "as",
    # LLM keywords
    "llm", "act",
    # Concurrency (v1.18)
    "spawn",
    # Shared store (v1.12)
    "store",
    # Protocol/Interface (v1.7)
    "protocol", "impl", "is",
    # Agent functions block
    "functions",
    # Transcript (v1.29)
    "transcript",
    # Thinking mode (v1.36)
    "thinking-mode", "reasoning-effort",
    # Literals
    "true", "false", "null",
    # Chinese keywords (v1.10 — bilingual support)
    "设", "定义", "常量", "函数", "返回",
    "如果", "否则", "对于", "属于", "当",
    "中断", "继续",
    "匹配", "情况", "默认", "分支",
    "尝试", "捕获", "最终", "抛出", "断言",
    "且", "或",  # v1.30.12: Chinese logical运算符
    "真", "假", "空", "是",
    "智能体", "大模型", "执行", "分生",
    "提示词", "描述", "模型", "工具",
    "流式输出", "温度", "最大轮次", "最大tokens",
    "函数区", "主函",
    "导入", "作为",
    "协议", "实现",
    "共享", "别名",
    "仓库", "记录",
    "思考模式", "推理强度",  # v1.36: thinking mode (formal keywords)
]

# Context keywords: not in _KEYWORD_MAP (parsed as IDENTIFIER + context check)
HELLEN_CONTEXT_KEYWORDS = [
    # Async/concurrency
    "async", "await",
    # Channel (v1.18)
    "Channel", "send", "receive", "try_receive", "cancel", "close",
    "mailbox_select",
    # LLM callbacks (v1.21)
    "on_chunk", "on_complete", "on_tool_end", "on_media", "on_generate",
    # Multimodal (v1.17)
    "media", "provider",
    # Context management (v1.12, v1.19)
    "context", "memory", "persistent", "none",
    # Session resume (v1.27)
    "resume",
    # Test framework
    "expect",
    # Chinese context keywords
    "上下文", "记忆", "恢复会话",
    "逐块处理", "完成", "工具结束", "处理媒体", "生成",
    "媒体",
    "提供商",  # v1.36: provider override (context keyword)
]

# Agent property keywords (inside agent {} blocks)
HELLEN_AGENT_PROPERTIES = [
    "description", "model", "temperature", "max-turns", "max-tokens", "tools",
    "streaming", "prompt", "transcript",
    "描述", "模型", "温度", "最大轮次", "最大tokens", "工具", "流式输出", "提示词", "记录",
]

# Built-in types
HELLEN_TYPES = [
    "str", "int", "float", "bool", "list", "dict", "map",
    "any", "void", "number",
    # Union/Optional syntax hints
    "Optional", "Union",
    # Protocol/Agent types
    "Protocol", "Agent",
    # Literal type
    "Literal",
]

# ── Snippet templates (insertTextFormat=2, LSP snippet syntax) ──
# $0 = final cursor position, $1/$2 = tab stops

HELLEN_SNIPPETS = [
    {
        "label": "agent",
        "detail": "Agent declaration block",
        "insertText": (
            "agent ${1:AgentName} {\n"
            "    description \"${2:description}\"\n"
            "    model \"${3:model}\"\n"
            "    temperature ${4:0.7}\n"
            "    tools [${5}]\n"
            "    prompt {\n"
            "        {{${6:input}}}\n"
            "    }\n"
            "    functions {\n"
            "        ${7}\n"
            "    }\n"
            "    main {\n"
            "        $0\n"
            "    }\n"
            "}"
        ),
    },
    {
        "label": "fn",
        "detail": "Function declaration",
        "insertText": "fn ${1:name}(${2:args}): ${3:void} {\n    $0\n}",
    },
    {
        "label": "llm act",
        "detail": "LLM act with tool loop",
        "insertText": (
            "llm act ${1:agent}(${2:prompt}) {\n"
            "    on_chunk {\n"
            "        ${3}\n"
            "    }\n"
            "    on_complete {\n"
            "        ${4}\n"
            "    }\n"
            "}$0"
        ),
    },
    {
        "label": "llm if",
        "detail": "LLM-routed conditional branch",
        "insertText": (
            "llm if (${1:condition}) {\n"
            "    ${2:branch1}\n"
            "} else {\n"
            "    ${3:branch2}\n"
            "}$0"
        ),
    },
    {
        "label": "shared store",
        "detail": "Thread-safe shared store declaration",
        "insertText": (
            "shared store ${1:StoreName} {\n"
            "    fields {\n"
            "        ${2}\n"
            "    }\n"
            "    methods {\n"
            "        ${3}\n"
            "    }\n"
            "}$0"
        ),
    },
    {
        "label": "spawn",
        "detail": "Spawn agent and return Channel",
        "insertText": "spawn ${1:Agent}(${2:args})$0",
    },
    {
        "label": "match",
        "detail": "Pattern matching block",
        "insertText": (
            "match ${1:expression} {\n"
            "    case ${2:pattern} => {\n"
            "        ${3}\n"
            "    }\n"
            "    default => {\n"
            "        $0\n"
            "    }\n"
            "}"
        ),
    },
    {
        "label": "try",
        "detail": "Try/catch error handling",
        "insertText": (
            "try {\n"
            "    ${1}\n"
            "} catch ${2:e} {\n"
            "    ${3}\n"
            "}$0"
        ),
    },
    {
        "label": "if",
        "detail": "If/else conditional",
        "insertText": "if ${1:condition} {\n    ${2}\n} else {\n    $0\n}",
    },
    {
        "label": "for",
        "detail": "For-in loop",
        "insertText": "for ${1:item} in ${2:collection} {\n    $0\n}",
    },
    {
        "label": "while",
        "detail": "While loop",
        "insertText": "while ${1:condition} {\n    $0\n}",
    },
    {
        "label": "import",
        "detail": "Import statement",
        "insertText": "import \"${1:path}\"${2: as ${3:alias}}$0",
    },
    {
        "label": "protocol",
        "detail": "Protocol declaration",
        "insertText": "protocol ${1:Name} {\n    ${2}\n}$0",
    },
    {
        "label": "@sandbox",
        "detail": "Sandbox agent decorator (tools=[])",
        "insertText": "@sandbox agent ${1:AgentName} {\n    $0\n}",
    },
    {
        "label": "@open",
        "detail": "Open agent decorator (can access module let)",
        "insertText": "@open agent ${1:AgentName} {\n    $0\n}",
    },
    {
        "label": "@strict",
        "detail": "Strict agent decorator (deep-copies shared let)",
        "insertText": "@strict agent ${1:AgentName} {\n    $0\n}",
    },
]

# ── Keyword descriptions for hover ────────────────────────────
_KEYWORD_DESCRIPTIONS: dict[str, str] = {
    "agent": "Declare an agent (AI-native autonomous entity)",
    "fn": "Declare a function",
    "let": "Declare a mutable variable",
    "const": "Declare an immutable constant",
    "if": "Conditional branch",
    "else": "Alternative branch",
    "for": "Loop over a collection",
    "in": "Membership / iteration operator",
    "while": "Loop while condition is true",
    "match": "Pattern matching (range, type, wildcard, variable binding)",
    "case": "A pattern match arm",
    "branch": "Branch arm (legacy)",
    "default": "Default match arm",
    "return": "Return a value from a function",
    "break": "Exit a loop",
    "continue": "Skip to next iteration",
    "try": "Try block for error handling",
    "catch": "Catch block for handling errors",
    "finally": "Block executed regardless of errors",
    "throw": "Raise an error",
    "assert": "Assert a condition (raises AssertionError)",
    "import": "Import a module",
    "as": "Alias an import",
    "llm": "LLM primitive (act / if)",
    "act": "LLM tool-calling loop",
    "spawn": "Spawn an agent and return a Channel (mailbox)",
    "Channel": "Inter-agent communication channel (spawn return type)",
    "send": "Send a message through a Channel",
    "receive": "Blocking receive from a Channel",
    "try_receive": "Non-blocking receive from a Channel",
    "cancel": "Cancel a spawned agent",
    "close": "Close a Channel",
    "mailbox_select": "Multi-channel select (like Go select)",
    "shared": "Shared variable or shared store declaration",
    "store": "Thread-safe shared store (fields + methods)",
    "protocol": "Protocol declaration (structural typing)",
    "impl": "Protocol implementation",
    "is": "Type pattern in match",
    "alias": "Create a function alias",
    "functions": "Agent functions block (LLM-callable tools)",
    "main": "Agent main block (entry point)",
    "transcript": "Agent transcript control (none/memory/persistent)",
    "prompt": "Agent prompt template",
    "description": "Agent description",
    "model": "Agent/model identifier",
    "temperature": "LLM sampling temperature",
    "max-turns": "Maximum LLM interaction turns",
    "max-tokens": "Maximum output tokens for LLM response",
    "thinking-mode": "Enable thinking/reasoning mode (v1.36)",
    "reasoning-effort": "Reasoning effort level: low/medium/high/max (v1.36)",
    "provider": "Explicit provider override (v1.36)",
    "思考模式": "启用思考/推理模式 (v1.36)",
    "推理强度": "推理强度: low/medium/high/max (v1.36)",
    "提供商": "显式指定厂商 (v1.36)",
    "tools": "List of tools available to the agent",
    "streaming": "Enable streaming output",
    "async": "Async function marker",
    "await": "Await an async result",
    "call": "Explicit function call",
    "true": "Boolean true",
    "false": "Boolean false",
    "null": "Null / empty value",
    "context": "Context management (clear_context, compress_context)",
    "memory": "In-memory transcript mode",
    "persistent": "Persistent (disk) transcript mode",
    "none": "No transcript recording (default)",
    "resume": "Resume a saved session",
    "expect": "Test expectation",
    "on_chunk": "Streaming callback: called for each text chunk",
    "on_complete": "Streaming callback: called when generation completes",
    "on_tool_end": "Tool callback: called after a tool executes",
    "on_media": "Multimodal callback: called for media parts",
    "on_generate": "Generation callback: called before LLM request",
    "media": "Multimodal media() function",
    "provider": "Media provider identifier",
    # Chinese keyword descriptions
    "智能体": "声明一个智能体（AI 原生自主实体）",
    "函数": "声明一个函数",
    "设": "声明一个可变变量",
    "定义": "声明一个不可变常量（legacy alias for 设）",
    "常量": "声明一个不可变常量",
    "如果": "条件分支",
    "否则": "否则分支",
    "对于": "遍历集合",
    "属于": "成员/迭代运算符",
    "当": "当条件为真时循环",
    "返回": "从函数返回值",
    "中断": "退出循环",
    "继续": "跳到下一次迭代",
    "匹配": "模式匹配",
    "情况": "匹配分支",
    "默认": "默认匹配分支",
    "分支": "分支（legacy）",
    "尝试": "尝试块（错误处理）",
    "捕获": "捕获块",
    "最终": "最终块（无论是否出错都执行）",
    "抛出": "抛出错误",
    "断言": "断言条件",
    "大模型": "大模型原语（执行/如果）",
    "执行": "大模型工具调用循环",
    "分生": "分生（spawn）智能体并返回 Channel",
    "提示词": "智能体提示词模板",
    "描述": "智能体描述",
    "模型": "模型标识符",
    "温度": "LLM 采样温度",
    "最大轮次": "最大交互轮次",
    "最大tokens": "LLM 响应最大输出 token 数",
    "工具": "智能体可用工具列表",
    "流式输出": "启用流式输出",
    "函数区": "智能体函数区（LLM 可调用的工具）",
    "主函": "智能体主函数（入口）",
    "导入": "导入模块",
    "作为": "导入别名",
    "协议": "协议声明（结构化类型）",
    "实现": "协议实现",
    "共享": "共享变量或共享仓库",
    "别名": "函数别名",
    "仓库": "线程安全的共享仓库",
    "记录": "智能体 transcript 控制",
    "真": "布尔真",
    "假": "布尔假",
    "空": "空值",
    "是": "类型模式匹配",
    "且": "逻辑与（AND）",
    "或": "逻辑或（OR）",
    "上下文": "上下文管理",
    "记忆": "内存 transcript 模式",
    "恢复会话": "恢复已保存的会话",
    "逐块处理": "流式回调：处理每个文本块",
    "完成": "流式回调：生成完成时调用",
    "工具结束": "工具回调：工具执行后调用",
    "处理媒体": "多模态回调：处理媒体部分",
    "生成": "生成回调：LLM 请求前调用",
    "媒体": "多模态 media() 函数",
}


# ── LSP Server ─────────────────────────────────────────────────

@dataclass
class DocumentState:
    """State for an open document."""

    uri: str
    content: str = ""
    version: int = 0
    diagnostics: list[Diagnostic] = field(default_factory=list)


class HelenLanguageServer:
    """LSP server for the Helen language.

    Handles JSON-RPC messages on stdin/stdout.
    """

    def __init__(self) -> None:
        self.documents: dict[str, DocumentState] = {}
        self.capabilities = {
            "textDocumentSync": 1,  # Full sync (we replace content on every change)
            "completionProvider": {
                "triggerCharacters": [".", '"', "'", " ", "@"],
                "resolveProvider": False,
            },
            "definitionProvider": True,
            "referencesProvider": True,
            "hoverProvider": True,
            "documentSymbolProvider": True,
            "diagnosticProvider": {
                "interFileDependencies": False,
                "workspaceDiagnostics": False,
            },
        }

    # ── Message handling ───────────────────────────────────

    def handle_message(self, message: dict[str, Any]) -> dict[str, Any] | None:
        """Handle a JSON-RPC message and return the response."""
        method = message.get("method")
        msg_id = message.get("id")
        params = message.get("params", {})

        # Request (has id)
        if msg_id is not None:
            result = self._handle_request(method, params)
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": result,
            }

        # Notification (no id)
        self._handle_notification(method, params)
        return None

    def _handle_request(self, method: str, params: dict[str, Any]) -> Any:
        """Handle a JSON-RPC request."""
        if method == "initialize":
            return self._initialize(params)
        elif method == "shutdown":
            return None
        elif method == "textDocument/completion":
            return self._completion(params)
        elif method == "textDocument/definition":
            return self._definition(params)
        elif method == "textDocument/references":
            return self._references(params)
        elif method == "textDocument/diagnostic":
            return self._diagnostic(params)
        elif method == "textDocument/hover":
            return self._hover(params)
        elif method == "textDocument/documentSymbol":
            return self._document_symbol(params)
        else:
            return None

    def _handle_notification(self, method: str, params: dict[str, Any]) -> None:
        """Handle a JSON-RPC notification."""
        if method == "initialized":
            pass  # Server is ready
        elif method == "exit":
            sys.exit(0)
        elif method == "textDocument/didOpen":
            self._did_open(params)
        elif method == "textDocument/didChange":
            self._did_change(params)
        elif method == "textDocument/didClose":
            self._did_close(params)

    # ── LSP Methods ────────────────────────────────────────

    def _initialize(self, params: dict[str, Any]) -> dict[str, Any]:
        """Handle initialize request."""
        import helen as _helen_pkg  # noqa: PLC0415
        _lsp_version = getattr(_helen_pkg, "__version__", "unknown")
        _log(f"initialize — helen-lsp {_lsp_version}, pid={__import__('os').getpid()}")
        return {
            "capabilities": self.capabilities,
            "serverInfo": {
                "name": "helen-lsp",
                "version": _lsp_version,
            },
        }

    def _did_open(self, params: dict[str, Any]) -> None:
        """Handle textDocument/didOpen."""
        doc = params.get("textDocument", {})
        uri = doc.get("uri", "")
        content = doc.get("text", "")
        version = doc.get("version", 0)

        _log(f"didOpen: {uri} ({len(content)} chars, version={version})")
        self.documents[uri] = DocumentState(
            uri=uri, content=content, version=version
        )
        self._publish_diagnostics(uri)

    def _did_change(self, params: dict[str, Any]) -> None:
        """Handle textDocument/didChange."""
        uri = params.get("textDocument", {}).get("uri", "")
        version = params.get("textDocument", {}).get("version", 0)
        changes = params.get("contentChanges", [])

        doc = self.documents.get(uri)
        if doc is None:
            return

        doc.version = version

        # Apply changes (Full sync — matches textDocumentSync: 1)
        for change in changes:
            if "text" in change:
                doc.content = change["text"]

        self._publish_diagnostics(uri)

    def _did_close(self, params: dict[str, Any]) -> None:
        """Handle textDocument/didClose."""
        uri = params.get("textDocument", {}).get("uri", "")
        self.documents.pop(uri, None)

    def _completion(self, params: dict[str, Any]) -> dict[str, Any]:
        """Handle textDocument/completion."""
        uri = params.get("textDocument", {}).get("uri", "")
        position = params.get("position", {})

        doc = self.documents.get(uri)
        if doc is None:
            return {"isIncomplete": False, "items": []}

        # Detect context for smart snippet filtering
        line_text = ""
        if position:
            lines = doc.content.split("\n")
            line_idx = position.get("line", 0)
            if 0 <= line_idx < len(lines):
                line_text = lines[line_idx].lstrip()

        items = []

        # Add formal keywords (from tokens.py _KEYWORD_MAP)
        for kw in HELLEN_KEYWORDS:
            items.append(
                CompletionItem(
                    label=kw, kind=14,  # Keyword
                    detail="Helen keyword"
                ).to_dict()
            )

        # Add context keywords (parsed as identifiers but used as keywords)
        for kw in HELLEN_CONTEXT_KEYWORDS:
            items.append(
                CompletionItem(
                    label=kw, kind=14,  # Keyword
                    detail="context keyword"
                ).to_dict()
            )

        # Add types
        for t in HELLEN_TYPES:
            items.append(
                CompletionItem(
                    label=t, kind=8,  # Interface (type)
                    detail="Helen type"
                ).to_dict()
            )

        # Add snippet templates (kind=15 Snippet)
        for snippet in HELLEN_SNIPPETS:
            items.append(
                CompletionItem(
                    label=snippet["label"],
                    kind=15,  # Snippet
                    detail=snippet["detail"],
                    insert_text=snippet["insertText"],
                    insert_text_format=2,  # Snippet format
                ).to_dict()
            )

        # Add built-in function completions from stdlib
        try:
            from helen.stdlib import stdlib  # noqa: PLC0415
            # Include both canonical names and aliases in completion
            seen_labels: set[str] = set()
            for func in stdlib.list_all():
                items.append(
                    CompletionItem(
                        label=func.name,
                        kind=3,  # Function
                        detail=func.description,
                        insert_text=f"{func.name}(",
                        documentation=func.description,
                    ).to_dict()
                )
                seen_labels.add(func.name)
            # Add aliases (these resolve to the same canonical function)
            for alias, canonical in stdlib.aliases.items():
                if alias not in seen_labels:
                    items.append(
                        CompletionItem(
                            label=alias,
                            kind=3,  # Function
                            detail=f"alias of {canonical}",
                            insert_text=f"{alias}(",
                            documentation=f"Alias of `{canonical}`",
                        ).to_dict()
                    )
                    seen_labels.add(alias)
        except ImportError:
            pass

        return {"isIncomplete": False, "items": items}

    def _definition(self, params: dict[str, Any]) -> list[dict[str, Any]]:
        """Handle textDocument/definition (go to definition)."""
        uri = params.get("textDocument", {}).get("uri", "")
        position = params.get("position", {})

        doc = self.documents.get(uri)
        if doc is None:
            _log(f"definition: doc not found for {uri}")
            return []

        line_num = position.get("line", 0) + 1  # 1-based
        char_num = position.get("character", 0) + 1

        result = self._find_definition_at(doc.content, uri, line_num, char_num)
        _log(f"definition: line={line_num} col={char_num} → {result}")
        return result

    def _references(self, params: dict[str, Any]) -> list[dict[str, Any]]:
        """Handle textDocument/references (find all references/call sites).

        Scans all open documents for references to the symbol at the cursor
        position. Returns a list of Location objects for each reference found.
        """
        uri = params.get("textDocument", {}).get("uri", "")
        position = params.get("position", {})
        context = params.get("context", {})
        include_declaration = context.get("includeDeclaration", True)

        doc = self.documents.get(uri)
        if doc is None:
            _log(f"references: doc not found for {uri}")
            return []

        line_num = position.get("line", 0) + 1
        char_num = position.get("character", 0) + 1

        # Get the symbol at cursor
        target = self._get_symbol_at(doc.content, line_num, char_num)
        if not target:
            _log(f"references: no symbol at line={line_num} col={char_num}")
            return []

        _log(f"references: searching for '{target}' across all documents")

        results = []
        for doc_uri, document in self.documents.items():
            refs = self._find_references_in(
                document.content, doc_uri, target, include_declaration
            )
            results.extend(refs)

        _log(f"references: found {len(results)} references")
        return results

    def _get_symbol_at(self, content: str, line: int, col: int) -> str | None:
        """Extract the symbol name at the given position."""
        import re  # noqa: PLC0415

        lines = content.split("\n")
        if not (0 < line <= len(lines)):
            return None

        current_line = lines[line - 1]
        # Match word boundaries (includes Unicode/CJK identifiers)
        for match in re.finditer(r'[\w一-鿿]+', current_line):
            if match.start() <= col - 1 < match.end():
                return match.group(0)
        return None

    def _find_references_in(
        self, content: str, uri: str, target: str, include_declaration: bool
    ) -> list[dict[str, Any]]:
        """Find all references to `target` in the given content."""
        import re  # noqa: PLC0415

        results = []
        lines = content.split("\n")

        # Patterns that indicate a declaration (to optionally skip)
        decl_patterns = [
            rf'^\s*(?:agent|fn|函数)\s+{re.escape(target)}\s*[\({{]',
            rf'^\s*(?:shared\s+)?(?:let|const|定义|常量)\s+{re.escape(target)}\s*=',
        ]

        # Pattern for any reference (word boundary match)
        # \b in Python regex matches Unicode word boundaries
        ref_pattern = rf'\b{re.escape(target)}\b'

        for i, line in enumerate(lines):
            # Skip comments
            if line.lstrip().startswith(('#', '//', '＃')):
                continue
            # Skip string literals (simple heuristic)
            if f'"{target}"' in line or f"'{target}'" in line:
                continue

            for match in re.finditer(ref_pattern, line):
                # Check if this is a declaration
                is_declaration = any(
                    re.search(p, line) for p in decl_patterns
                )

                if is_declaration and not include_declaration:
                    continue

                start = Position(line=i, character=match.start())
                end = Position(line=i, character=match.end())
                results.append(
                    Location(
                        uri=uri,
                        range=Range(start=start, end=end),
                    ).to_dict()
                )

        return results

    def _find_definition_at(
        self, content: str, uri: str, line: int, col: int
    ) -> list[dict[str, Any]]:
        """Find the definition at a given position.

        Simplified implementation: scans for agent/fn/let declarations.
        """
        import re  # noqa: PLC0415

        lines = content.split("\n")
        if 0 < line <= len(lines):
            current_line = lines[line - 1]
            # Get word at cursor position
            word_match = re.findall(r'\b\w+\b', current_line)
            if not word_match:
                return []

            # Find the word under cursor
            target = None
            for word in word_match:
                idx = current_line.find(word)
                if idx <= col - 1 <= idx + len(word):
                    target = word
                    break

            if target is None:
                return []

            # Search for declaration in the document
            # \w in Python 3 matches Unicode word chars (incl. CJK) by default
            patterns = [
                rf'agent\s+({target})\s*[\({{{{]',                   # agent decl
                rf'fn\s+({target})\s*\(',                            # function decl
                rf'(?:shared\s+)?(?:let|const|定义|常量)\s+({target})\s*=',  # variable decl
            ]

            for i, file_line in enumerate(lines):
                for pattern in patterns:
                    match = re.search(pattern, file_line)
                    if match:
                        start = Position(line=i, character=match.start(1))
                        end = Position(line=i, character=match.end(1))
                        return [
                            Location(
                                uri=uri,
                                range=Range(start=start, end=end),
                            ).to_dict()
                        ]

        return []

    def _hover(self, params: dict[str, Any]) -> dict[str, Any] | None:
        """Handle textDocument/hover.

        Returns type info and documentation for the symbol at cursor position.
        Supports:
        - stdlib functions: show description and signature
        - Keywords: show brief description
        - Types: show type description
        - User-defined agents/functions: show declaration line
        """
        uri = params.get("textDocument", {}).get("uri", "")
        position = params.get("position", {})

        doc = self.documents.get(uri)
        if doc is None:
            return None

        line_num = position.get("line", 0) + 1
        char_num = position.get("character", 0) + 1

        # Get the word at cursor
        target = self._get_symbol_at(doc.content, line_num, char_num)
        if not target:
            return None

        # Check stdlib functions first
        try:
            from helen.stdlib import stdlib  # noqa: PLC0415
            for func in stdlib.list_all():
                if func.name == target:
                    sig = f"`{func.name}()` — {func.description}"
                    return {
                        "contents": {"kind": "markdown", "value": sig},
                    }
            # Check aliases
            if target in stdlib.aliases:
                canonical = stdlib.aliases[target]
                return {
                    "contents": {
                        "kind": "markdown",
                        "value": f"`{target}` — alias of `{canonical}`",
                    },
                }
        except ImportError:
            pass

        # Check keywords
        all_keywords = set(HELLEN_KEYWORDS + HELLEN_CONTEXT_KEYWORDS)
        if target in all_keywords:
            desc = _KEYWORD_DESCRIPTIONS.get(target, f"Helen keyword: `{target}`")
            return {
                "contents": {"kind": "markdown", "value": f"**{target}** — {desc}"},
            }

        # Check types
        if target in HELLEN_TYPES:
            return {
                "contents": {"kind": "markdown", "value": f"**{target}** — Helen type"},
            }

        # Check decorators
        if target in ("open", "strict", "sandbox", "开放", "严格", "沙箱"):
            return {
                "contents": {
                    "kind": "markdown",
                    "value": f"**@{target}** — Agent isolation decorator",
                },
            }

        # Check user-defined symbols (scan document for declarations)
        import re  # noqa: PLC0415
        lines = doc.content.split("\n")
        for i, line in enumerate(lines):
            stripped = line.lstrip()
            # agent declaration
            m = re.match(rf'(@\w+\s+)?agent\s+{re.escape(target)}\s*[\({{]', stripped)
            if m:
                return {
                    "contents": {
                        "kind": "markdown",
                        "value": f"```helen\n{stripped.rstrip()}\n```\nAgent declaration (line {i + 1})",
                    },
                }
            # function declaration
            m = re.match(rf'fn\s+{re.escape(target)}\s*\(([^)]*)\)', stripped)
            if m:
                return {
                    "contents": {
                        "kind": "markdown",
                        "value": f"```helen\n{stripped.rstrip()}\n```\nFunction declaration (line {i + 1})",
                    },
                }
            # shared store
            m = re.match(rf'shared\s+store\s+{re.escape(target)}\s*[\({{]', stripped)
            if m:
                return {
                    "contents": {
                        "kind": "markdown",
                        "value": f"```helen\n{stripped.rstrip()}\n```\nShared store declaration (line {i + 1})",
                    },
                }
            # variable declaration
            m = re.match(rf'(?:shared\s+)?(?:let|const|设|定义|常量)\s+{re.escape(target)}\s*(?::\s*(\S+))?\s*=', stripped)
            if m:
                type_info = m.group(1) or "inferred"
                return {
                    "contents": {
                        "kind": "markdown",
                        "value": f"```helen\n{stripped.rstrip()}\n```\nVariable (type: `{type_info}`, line {i + 1})",
                    },
                }
            # protocol declaration
            m = re.match(rf'protocol\s+{re.escape(target)}\s*[\({{]', stripped)
            if m:
                return {
                    "contents": {
                        "kind": "markdown",
                        "value": f"```helen\n{stripped.rstrip()}\n```\nProtocol declaration (line {i + 1})",
                    },
                }

        return None

    def _document_symbol(self, params: dict[str, Any]) -> list[dict[str, Any]]:
        """Handle textDocument/documentSymbol.

        Returns a hierarchical list of symbols in the document for the outline view.
        Symbol kinds:
        - 2=Struct (agent, shared store, protocol)
        - 5=Class (class declarations)
        - 6=Method (functions inside agent)
        - 12=Function (standalone functions)
        - 13=Variable (let/const)
        """
        import re  # noqa: PLC0415

        uri = params.get("textDocument", {}).get("uri", "")
        doc = self.documents.get(uri)
        if doc is None:
            return []

        symbols = []
        lines = doc.content.split("\n")

        # Track agent blocks for nesting methods inside agents
        agent_stack: list[dict[str, Any]] = []  # stack of agent symbol dicts

        for i, line in enumerate(lines):
            stripped = line.lstrip()
            indent = len(line) - len(stripped)

            # Pop agents that we've exited (by indent)
            while agent_stack and agent_stack[-1].get("_indent", -1) >= indent and indent > 0:
                agent_stack.pop()

            # @decorator + agent declaration
            m = re.match(r'(@\w+\s+)?agent\s+(\w+)\s*[\({]', stripped)
            if m:
                decorator = m.group(1) or ""
                name = m.group(2)
                sym: dict[str, Any] = {
                    "name": f"{decorator.strip()}agent {name}".strip(),
                    "kind": 2,  # Struct
                    "range": {
                        "start": {"line": i, "character": 0},
                        "end": {"line": i, "character": len(line)},
                    },
                    "selectionRange": {
                        "start": {"line": i, "character": indent + len(decorator) + len("agent ")},
                        "end": {"line": i, "character": indent + len(decorator) + len("agent ") + len(name)},
                    },
                    "children": [],
                    "_indent": indent,
                }
                symbols.append(sym)
                agent_stack.append(sym)
                continue

            # shared store
            m = re.match(r'shared\s+store\s+(\w+)\s*[\({]', stripped)
            if m:
                name = m.group(1)
                sym = {
                    "name": f"shared store {name}",
                    "kind": 2,  # Struct
                    "range": {
                        "start": {"line": i, "character": 0},
                        "end": {"line": i, "character": len(line)},
                    },
                    "selectionRange": {
                        "start": {"line": i, "character": indent + len("shared store ")},
                        "end": {"line": i, "character": indent + len("shared store ") + len(name)},
                    },
                    "children": [],
                    "_indent": indent,
                }
                symbols.append(sym)
                agent_stack.append(sym)
                continue

            # protocol
            m = re.match(r'protocol\s+(\w+)\s*[\({]', stripped)
            if m:
                name = m.group(1)
                sym = {
                    "name": f"protocol {name}",
                    "kind": 11,  # Struct/Interface
                    "range": {
                        "start": {"line": i, "character": 0},
                        "end": {"line": i, "character": len(line)},
                    },
                    "selectionRange": {
                        "start": {"line": i, "character": indent + len("protocol ")},
                        "end": {"line": i, "character": indent + len("protocol ") + len(name)},
                    },
                    "children": [],
                }
                symbols.append(sym)
                continue

            # fn declaration (top-level or inside agent)
            m = re.match(r'fn\s+(\w+)\s*\(([^)]*)\)\s*(?::\s*(\S+))?\s*\{', stripped)
            if m:
                name = m.group(1)
                ret_type = m.group(3) or ""
                fn_sym: dict[str, Any] = {
                    "name": f"fn {name}({m.group(2)})" + (f": {ret_type}" if ret_type else ""),
                    "kind": 6 if agent_stack else 12,  # Method if inside agent, else Function
                    "range": {
                        "start": {"line": i, "character": 0},
                        "end": {"line": i, "character": len(line)},
                    },
                    "selectionRange": {
                        "start": {"line": i, "character": indent + len("fn ")},
                        "end": {"line": i, "character": indent + len("fn ") + len(name)},
                    },
                }
                if agent_stack:
                    agent_stack[-1].setdefault("children", []).append(fn_sym)
                else:
                    symbols.append(fn_sym)
                continue

            # Variable declarations (let/const/shared let)
            m = re.match(r'(?:shared\s+)?(?:let|const|设|定义|常量)\s+(\w+)', stripped)
            if m:
                name = m.group(1)
                var_sym = {
                    "name": name,
                    "kind": 13,  # Variable
                    "range": {
                        "start": {"line": i, "character": 0},
                        "end": {"line": i, "character": len(line)},
                    },
                    "selectionRange": {
                        "start": {"line": i, "character": indent + len(m.group(0)) - len(name)},
                        "end": {"line": i, "character": indent + len(m.group(0))},
                    },
                }
                if agent_stack:
                    agent_stack[-1].setdefault("children", []).append(var_sym)
                else:
                    symbols.append(var_sym)
                continue

        # Clean up internal _indent keys before returning
        def _clean(sym_dict: dict[str, Any]) -> dict[str, Any]:
            sym_dict.pop("_indent", None)
            for child in sym_dict.get("children", []):
                _clean(child)
            return sym_dict

        return [_clean(s) for s in symbols]

    def _diagnostic(self, params: dict[str, Any]) -> dict[str, Any]:
        """Handle textDocument/diagnostic."""
        uri = params.get("textDocument", {}).get("uri", "")
        doc = self.documents.get(uri)
        if doc is None:
            return {"kind": "full", "items": []}

        return {
            "kind": "full",
            "items": [d.to_dict() for d in doc.diagnostics],
        }

    # ── Analysis ───────────────────────────────────────────

    def _publish_diagnostics(self, uri: str) -> None:
        """Analyze document and publish diagnostics."""
        doc = self.documents.get(uri)
        if doc is None:
            return

        try:
            diagnostics = self._analyze(doc.content, uri)
        except Exception as e:
            _log(f"analysis error for {uri}: {e!r}")
            diagnostics = []
        doc.diagnostics = diagnostics

        # Send publishDiagnostics notification
        notification = {
            "jsonrpc": "2.0",
            "method": "textDocument/publishDiagnostics",
            "params": {
                "uri": uri,
                "diagnostics": [d.to_dict() for d in diagnostics],
            },
        }
        self._send(notification)

    @staticmethod
    def _uri_to_path(uri: str) -> str:
        """Convert a file:// URI to a filesystem path.

        LSP clients send document URIs (e.g. 'file:///tmp/x.helen'). The
        scanner and import resolver need a real filesystem path so that
        relative imports resolve against the document's directory, not the
        LSP process CWD.

        v1.23.5 fix: Previously _analyze hard-coded '<lsp>' as the file name,
        which caused SemanticAnalyzer.visit_import_stmt to fall back to
        base_dir (process CWD) when resolving relative imports, producing
        spurious 'import file not found' diagnostics.
        """
        if uri.startswith("file://"):
            from urllib.parse import urlparse, unquote
            parsed = urlparse(uri)
            return unquote(parsed.path)
        return uri

    def _analyze(self, content: str, uri: str = "") -> list[Diagnostic]:
        """Analyze source code and return diagnostics.

        Runs Lex -> Parse -> Analyze pipeline and converts errors to LSP diagnostics.

        Args:
            content: Source code text.
            uri: Document URI (e.g. 'file:///path/to/file.helen'). Used to
                resolve relative imports. v1.23.5 fix: previously hard-coded
                to '<lsp>', causing 'import file not found' for any relative
                import because the analyzer fell back to the LSP process CWD.
        """
        diagnostics = []

        # Resolve the document's filesystem path so relative imports work.
        # Falls back to '<lsp>' only when no URI is available (e.g. REPL).
        file_path = self._uri_to_path(uri) if uri else "<lsp>"

        try:
            from helen.core.errors import ErrorReporter  # noqa: PLC0415
            from helen.core.lexer import Scanner  # noqa: PLC0415
            from helen.core.parser import Parser  # noqa: PLC0415
            from helen.semantic.analyzer import SemanticAnalyzer  # noqa: PLC0415

            errors = ErrorReporter()

            # Lex
            try:
                scanner = Scanner(source=content, file=file_path)
                tokens = scanner.scan_all()
            except Exception:
                return [
                    Diagnostic(
                        range=Range(
                            start=Position(line=0, character=0),
                            end=Position(line=0, character=1),
                        ),
                        severity=1,
                        message="Lexer error: failed to tokenize source",
                        code="LEX",
                    )
                ]

            # Parse
            parser = Parser(tokens, errors=errors)
            program = parser.parse()

            # Convert parser errors
            for err in errors.errors:
                if err.span:
                    start = Position(
                        line=err.span.start_line - 1,
                        character=err.span.start_col - 1,
                    )
                    end = Position(
                        line=err.span.end_line - 1,
                        character=err.span.end_col - 1,
                    )
                else:
                    start = Position(line=0, character=0)
                    end = Position(line=0, character=1)

                diagnostics.append(
                    Diagnostic(
                        range=Range(start=start, end=end),
                        severity=1,  # Error
                        message=err.message,
                        code=f"E{err.code.value:04d}",
                    )
                )

            if not errors.has_errors:
                # Analyze
                errors.reset()
                # v1.23.5: Set base_dir to the document's directory so that
                # fallback import resolution (when span.file is unavailable)
                # still finds files relative to the document, not the LSP
                # process CWD.
                import os as _os
                base_dir = _os.path.dirname(_os.path.abspath(file_path)) if file_path != "<lsp>" else "."
                analyzer = SemanticAnalyzer(errors, base_dir=base_dir)
                analyzer.analyze(program)

                for err in errors.errors:
                    if err.span:
                        start = Position(
                            line=err.span.start_line - 1,
                            character=err.span.start_col - 1,
                        )
                        end = Position(
                            line=err.span.end_line - 1,
                            character=err.span.end_col - 1,
                        )
                    else:
                        start = Position(line=0, character=0)
                        end = Position(line=0, character=1)

                    diagnostics.append(
                        Diagnostic(
                            range=Range(start=start, end=end),
                            severity=1,  # Error
                            message=err.message,
                            code=f"E{err.code.value:04d}",
                        )
                    )

        except ImportError:
            # helen package not available, skip analysis
            pass

        return diagnostics

    # ── I/O ────────────────────────────────────────────────

    def _send(self, message: dict[str, Any]) -> None:
        """Send a JSON-RPC message via stdout."""
        body = json.dumps(message, ensure_ascii=False)
        body_bytes = body.encode("utf-8")
        sys.stdout.buffer.write(
            f"Content-Length: {len(body_bytes)}\r\n"
            f"Content-Type: application/vscode-jsonrpc; charset=utf-8\r\n\r\n"
            .encode("utf-8")
        )
        sys.stdout.buffer.write(body_bytes)
        sys.stdout.buffer.flush()

    def run(self) -> None:
        """Run the LSP server, reading JSON-RPC from stdin."""
        content_length = 0

        while True:
            # Read headers
            while True:
                line = sys.stdin.buffer.readline()
                if not line:
                    return  # EOF

                if line == b"\r\n":
                    break  # End of headers

                if line.startswith(b"Content-Length: "):
                    content_length = int(line.split(b": ")[1])

            # Read body
            body = b""
            while len(body) < content_length:
                chunk = sys.stdin.buffer.read(content_length - len(body))
                if not chunk:
                    return  # EOF
                body += chunk

            # Parse and handle
            message = json.loads(body.decode("utf-8"))
            response = self.handle_message(message)
            if response is not None:
                self._send(response)
