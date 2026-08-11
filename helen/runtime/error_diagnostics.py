"""Error diagnostics for AI-native debugging.

This module provides structured error classification and suggestion generation
for Helen runtime errors. All suggestions are generated statically (no LLM calls)
to ensure 100% deterministic error handling.

Design Principles:
- Push model: suggestions are embedded in ErrorSnapshot, AI passively receives
- Zero LLM dependency: runtime error chain must be deterministic
- Coverage: all 10 exception types in helen/interpreter/exceptions.py
- Extensible: template registry + rule-based matching

Usage:
    from helen.runtime.error_diagnostics import generate_diagnostics

    snapshot = generate_diagnostics(error_type, message, scope, call_stack)
    # snapshot now has: diagnostic_category, suggestion, data_flow
"""

from __future__ import annotations

import re
from typing import Any


# ---------------------------------------------------------------------------
# Error Suggestion Registry
# ---------------------------------------------------------------------------
# Maps exception type names to their diagnostic templates.
# Each entry has:
#   - category: semantic classification (e.g., "LLMTimeout")
#   - template: suggestion text with {field} placeholders
#   - fields: list of field names to extract from exception context
#   - rules: optional list of regex-based rules for more specific suggestions

ERROR_SUGGESTION_REGISTRY: dict[str, dict[str, Any]] = {
    "AnyError": {
        "category": "GenericError",
        "template": "通用错误。检查错误消息 '{message}' 里的具体描述。",
        "fields": ["message"],
    },
    "LLMError": {
        "category": "LLMGenericError",
        "template": "LLM 调用失败。检查 LLM 配置（base_url、api_key、model）是否正确。"
                   "如果问题持续，查看 :llm_log 获取详细调用日志。",
        "fields": [],
    },
    "TimeoutError": {
        "category": "LLMTimeout",
        "template": "LLM 调用超时。考虑：(1) 增加 timeout 配置，(2) 减小 prompt 长度，"
                   "(3) 检查网络连接，(4) 确认 LLM 服务是否可用。",
        "fields": [],
    },
    "ModelError": {
        "category": "LLMModelUnavailable",
        "template": "模型不可用或配额耗尽。检查：(1) model 名称是否正确，"
                   "(2) API key 是否有效，(3) 账户余额是否充足。",
        "fields": [],
    },
    "PromptTooLongError": {
        "category": "LLMContextOverflow",
        "template": "Prompt 超出模型上下文窗口（{tokens_used}/{tokens_limit} tokens）。"
                   "使用 compress_context() 压缩历史，或 clear_context() 清空，"
                   "或减小 agent prompt 模板大小。",
        "fields": ["tokens_used", "tokens_limit"],
    },
    "AgentError": {
        "category": "AgentCallFailed",
        "template": "Agent '{agent_name}' 调用失败。根因：{cause}。"
                   "检查：(1) agent 参数类型是否匹配，(2) agent 内部逻辑是否有 bug，"
                   "(3) agent 的 LLM 调用是否失败（用 :llm_log 查看）。",
        "fields": ["agent_name", "cause"],
    },
    "LLMOutputContractError": {
        "category": "LLMOutputContractViolation",
        "template": "Agent '{agent_name}' 的 LLM 输出不符合契约要求。违反：{violation}。"
                   "检查：(1) agent prompt 是否明确要求输出格式，(2) output_contract 定义是否正确，"
                   "(3) 考虑在 prompt 中添加更明确的格式说明或示例。",
        "fields": ["agent_name", "violation"],
    },
    "ToolError": {
        "category": "ToolCallFailed",
        "template": "工具调用失败。检查：(1) 工具参数是否符合 schema，"
                   "(2) 工具是否返回错误，(3) 加重试逻辑或 try/catch 包裹。",
        "fields": [],
    },
    "RuntimeError": {
        "category": "RuntimeGenericError",
        "template": "运行时错误：{message}。检查变量类型和边界条件。",
        "fields": ["message"],
        "rules": [
            # Rule 1: Division by zero
            {
                "match": r"division by zero",
                "suggestion": "除零错误。在除法前检查分母是否为 0。",
            },
            # Rule 2: Type mismatch
            {
                "match": r"expected .*, got .*",
                "suggestion": "类型不匹配。检查函数返回值类型是否符合预期。",
            },
            # Rule 3: Undefined variable
            {
                "match": r"undefined variable .*",
                "suggestion": "未定义变量。检查变量是否已声明，或作用域是否正确。",
            },
            # Rule 4: Index out of range
            {
                "match": r"index .* out of range",
                "suggestion": "索引越界。检查数组/列表长度，确保索引在有效范围内。",
            },
            # Rule 5: Key not found
            {
                "match": r"key .* not found",
                "suggestion": "字典键不存在。检查键名是否正确，或用 get() 方法提供默认值。",
            },
        ],
    },
    "AssertionError": {
        "category": "AssertionFailed",
        "template": "断言失败：{message}。程序状态不符合预期。"
                   "检查断言条件是否正确，以及上游数据是否异常。",
        "fields": ["message"],
    },
    "AggregateError": {
        "category": "MultipleFailures",
        "template": "{error_count} 个并发任务失败。查看 errors 列表里的每个具体错误。"
                   "通常先修第一个错误，后续错误可能是级联失败。",
        "fields": ["error_count"],
    },
}


# ---------------------------------------------------------------------------
# Suggestion Generation
# ---------------------------------------------------------------------------

def generate_suggestion(
    error_type: str,
    message: str,
    context: dict[str, Any] | None = None,
) -> tuple[str, str]:
    """Generate diagnostic category and suggestion for an error.

    Args:
        error_type: Exception type name (e.g., "TimeoutError")
        message: Error message text
        context: Additional context (exception attributes, scope, etc.)

    Returns:
        Tuple of (diagnostic_category, suggestion_text)
    """
    context = context or {}

    # Look up registry entry
    entry = ERROR_SUGGESTION_REGISTRY.get(error_type)
    if entry is None:
        # Fallback for unknown error types
        return ("UnknownError", f"未知错误类型 '{error_type}'。检查错误消息：{message}")

    category = entry["category"]
    template = entry["template"]
    fields = entry.get("fields", [])
    rules = entry.get("rules", [])

    # Try rule-based matching first (more specific)
    for rule in rules:
        pattern = rule["match"]
        if re.search(pattern, message, re.IGNORECASE):
            return (category, rule["suggestion"])

    # Fall back to template-based suggestion
    try:
        # Build format kwargs from context
        format_kwargs = {"message": message}
        for field in fields:
            # Don't overwrite 'message' - it's already set from the message parameter
            if field == "message":
                continue
            if field in context:
                format_kwargs[field] = context[field]
            elif field == "error_count" and "errors" in context:
                format_kwargs[field] = len(context["errors"])
            else:
                format_kwargs[field] = f"<{field} not available>"

        suggestion = template.format(**format_kwargs)
    except (KeyError, ValueError) as e:
        # If template formatting fails, use fallback
        suggestion = f"{error_type}: {message}"

    return (category, suggestion)


# ---------------------------------------------------------------------------
# Data Flow Tracing
# ---------------------------------------------------------------------------

def build_data_flow(
    scope: dict[str, Any],
    call_stack: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Infer data flow from error context.

    Analyzes scope variables and call stack to trace where values came from.

    Args:
        scope: Local variables at error time
        call_stack: Call stack at error time

    Returns:
        List of data flow entries, each with:
        - variable: variable name (if from scope)
        - source: UUID or description of where value came from
        - via: how it got here (agent name, function, etc.)
    """
    flow = []

    # Rule 1: If scope has Message-type variables, trace their origin
    for name, value in scope.items():
        if _is_message_like(value):
            uuid = getattr(value, "uuid", None)
            agent_name = getattr(value, "agent_name", "unknown")
            if uuid:
                flow.append({
                    "variable": name,
                    "source": uuid,
                    "via": agent_name,
                })

    # Rule 2: If call stack has agent calls, trace agent outputs
    for frame in call_stack:
        func_name = frame.get("function", "")
        if func_name.startswith("agent:") or func_name.startswith("Agent "):
            flow.append({
                "source": "agent_output",
                "via": func_name,
                "origin": frame.get("location", ""),
            })

    return flow


def _is_message_like(value: Any) -> bool:
    """Check if value looks like a Message object (has uuid and role)."""
    return (
        hasattr(value, "uuid") and
        hasattr(value, "role") and
        hasattr(value, "content")
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def generate_diagnostics(
    error_type: str,
    message: str,
    scope: dict[str, Any] | None = None,
    call_stack: list[dict[str, Any]] | None = None,
    exception_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Generate complete diagnostic information for an error.

    This is the main entry point for error diagnostics. It combines:
    - Suggestion generation (template + rule-based)
    - Data flow tracing (scope + call stack analysis)

    Args:
        error_type: Exception type name
        message: Error message
        scope: Local variables at error time
        call_stack: Call stack at error time
        exception_context: Additional exception attributes (e.g., tokens_used)

    Returns:
        Dict with keys:
        - diagnostic_category: str
        - suggestion: str
        - data_flow: list[dict]
    """
    scope = scope or {}
    call_stack = call_stack or []
    exception_context = exception_context or {}

    # Generate suggestion
    category, suggestion = generate_suggestion(
        error_type, message, exception_context
    )

    # Build data flow
    data_flow = build_data_flow(scope, call_stack)

    return {
        "diagnostic_category": category,
        "suggestion": suggestion,
        "data_flow": data_flow,
    }
