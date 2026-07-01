# HLD 合规状态

> Helen High Level Design v1.2 | 17 模块全部实现

---

## 模块实现总览

| # | 模块 | HLD 章节 | 文件 | 行数 | 测试 | 状态 |
|---|---|---|---|---|---|---|
| M1 | Lexer | §3.2 | `core/lexer.py` `core/tokens.py` | 933 | 734 | ✅ |
| M2 | Parser | §3.3 | `core/parser.py` | 1022 | 1111 | ✅ |
| M3 | AST Node | §3.4 | `core/ast.py` `core/source.py` | 1155 | 845 | ✅ |
| M4 | SemanticAnalyzer | §3.5 | `semantic/analyzer.py` `symbols.py` | 851 | 1205 | ✅ |
| M5 | Interpreter | §3.6 | `interpreter/interpreter.py` `environment.py` `task.py` | 1278 | 2086 | ✅ |
| M6 | PromptBuilder | §3.7 | `runtime/prompt_builder.py` | 189 | 132 | ✅ |
| M7 | Runtime API | §3.8 | `runtime/__init__.py` `llm_runtime.py` `memory.py` `config.py` `tools.py` `fuzzy_match.py` | 1,960+ | 331 | ✅ |
| M8 | ImportResolver | §3.9 | `runtime/import_resolver.py` | 239 | 237 | ✅ |
| M9 | Type System | §3.10 | `semantic/types.py` | 323 | 296 | ✅ |
| M10 | Error Handler | §3.11 | `core/errors.py` `cli/formatter.py` | 300 | 320 | ✅ |
| M11 | CLI | §5.2 | `cli/__main__.py` `repl.py` `docgen.py` | 672 | 470 | ✅ |
| M12 | LSP | §5.1 | `lsp/server.py` | 529 | 393 | ✅ |
| M13 | VS Code Extension | §6.2 | `extensions/vscode/*` | 206 | 20 | ✅ |
| M14 | Test Framework | §5.3 | `pyproject.toml` `conftest.py` | 27 | 811 tests | ✅ |
| M15 | Standard Library | §4.1 | `stdlib/__init__.py` | 247 | 279 | ✅ |
| M16 | HistoryManager | §3.12 | `runtime/history.py` | 151 | 139 | ✅ |
| M17 | StructuredOutput | §3.8.1 | `runtime/structured.py` | 193 | 100 | ✅ |

**总计**: 9,500+ 行 Python 代码 | 904 测试 | flake8 0 errors

---

## 关键合规项

| HLD 要求 | 实现 | 验证方式 |
|---|---|---|
| 39 关键字 (§3.2) | 42 关键字 (含 true/false/null) | `tokens.py` 测试 |
| Maximal Munch | 正则优先级排序 | lexer 测试 |
| Pratt Parsing 10 级 | 10 级优先级表 | parser 测试 |
| 46 Visitor 方法 | 46/46 实现 | ast.py 抽象方法检查 |
| SourceSpan 全链路 | Token→AST→Error→Formatter | 全链路测试 |
| 42 ErrorCode | 42 codes (300-350) | errors.py 枚举 |
| Agent 隔离调用 | 独立 Environment() | test_agent_isolation |
| import 不执行 main | 仅注册 Agent/Fn | test_import_execution |
| 路径安全检查 | `_is_safe_path()` | test_import_resolver |
| 循环导入检测 | `_loaded` 集合 | test_import_resolver |
| Token 预算 (§3.12) | check_budget() | test_history |
| conversation_summary 4096 上限 | build_conversation_summary() | test_history |
| LSP JSON-RPC 2.0 | Content-Length header | test_server |
| HLD 3.11.2 错误格式 | format_error() | test_formatter |
| 两层渐进式披露 | Skill Index + load_skill | test_prompt_builder |
| 模板防注入 | 单次替换，值含 {{ 不渲染 | test_prompt_builder |
| 独立配置系统 | `~/.helen/config.yaml` + `.env` 4 级优先级 | test_config |
| 内置工具注册表 | 6 工具 (web_search/web_fetch/read_file/write_file/shell_exec/calculate) | test_tools |
| Function Calling 循环 | 多轮工具调用 + nudge 机制 | test_http_llm |

---

## 已知偏差

| 偏差 | 影响 | 计划 |
|---|---|---|
| `_get_context()` v1 使用 HistoryManager | 功能完整 | — |
| `cancel_llm_call` 接口完整 | 已实现 threading.Event 机制 | — |
| LSP go-to-definition 正则实现 | 功能可用，非 AST 级精确定位 | 未来优化 |
| async call v1 同步执行 | 语义正确，无真正并发 | 未来改为异步 |
| VS Code Extension 仅语法高亮 | 无 LSP 集成 | 未来添加 LSP 客户端 |

**所有偏差均非阻塞性**，不影响语言核心功能。
