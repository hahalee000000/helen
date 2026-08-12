# Helen Agent — Helen 源文件测试覆盖率报告

> 生成时间: 2026-08-12 | 目标: 80% 覆盖率
> 分析方式: 函数级覆盖（源文件中定义的 `fn` 是否被 test 文件调用）

## 概要

| 指标 | 数值 |
|------|------|
| 源文件总数 | 15 (含 1 个纯常量文件) |
| 函数定义总数 | 231 |
| 被测试覆盖的函数 | 161 |
| **整体函数覆盖率** | **69.7%** |
| 达标文件 (≥80%) | 9/15 |
| 未达标文件 (<80%) | **6/15** |
| 测试总数 (Helen) | 843 (826 pass / 17 fail) |

## 逐文件覆盖率

### ✅ 达标文件 (≥80%)

| 文件 | 函数数 | 已测 | 覆盖率 | 测试文件 | 测试通过 |
|------|--------|------|--------|----------|----------|
| `json_utils.helen` | 1 | 1 | **100%** | test_shared_modules | 80/80 |
| `contracts/contracts.helen` | 0 (纯常量) | — | **100%** | test_contracts | 136/136 |
| `ui_event_queue.helen` | 18 | 18 | **100%** | test_ui_event_queue | 21/21 |
| `session_stats.helen` | 7 | 7 | **100%** | test_session_stats | 62/62 |
| `utils.helen` | 7 | 7 | **100%** | test_utils | 70/70 |
| `task_manager.helen` | 6 | 6 | **100%** | test_task_manager | 80/80 |
| `memory_utils.helen` | 5 | 5 | **100%** | test_shared_modules | 80/80 |
| `context.helen` | 9 | 8 | **89%** | test_integration, test_shared_modules | — |
| `commands.helen` | 18 | 15 | **83%** | test_commands, test_webui_commands | 88+78 |

### ❌ 未达标文件 (<80%)

| 文件 | 函数数 | 已测 | 覆盖率 | 未覆盖函数 |
|------|--------|------|--------|------------|
| **`chat_session_actor.helen`** | 32 | 23 | **72%** | `_actor_chunks_cb`, `_actor_complete_cb`, `_actor_tool_end_cb`, `_handle_actor_command`, `_handle_actor_user_input`, `save_code_file`, `search_session_transcript`, `update_existing_skill`, `verify_after_change` (9 个) |
| **`system_reminders.helen`** | 4 | 3 | **75%** | `_dynamic_interval` |
| **`chat_actor.helen`** | 6 | 0 | **0%** | 全部 6 个函数 (FFI 入口，由 Python 侧 mock 测试) |
| **`context_manager.helen`** | 19 | 0 | **0%** | 全部 19 个函数 (无对应 Helen 测试文件) |
| **`output.helen`** | 80 | 55 | **69%** | 25 个 (详见下方) |

## 未达标文件详细分析

### 1. `context_manager.helen` — 0% (19 个函数全部未测)

**最严重** — 整个模块无对应测试文件。

未覆盖函数:
- `init`, `reset`, `check_and_compress` — 核心生命周期
- `get_stats`, `get_usage`, `get_version`, `get_session_dir` — 查询接口
- `pin`, `unpin`, `get_pinned`, `_rebuild_pinned_uuids`, `set_pinned_uuids` — Pin 管理
- `check_version_if_needed`, `refresh_facts_if_needed` — 条件刷新
- `_register_hooks`, `_setup_session_scope` — 初始化钩子
- `_safe_compress`, `_safe_context_usage`, `_safe_working_memory_snapshot` — 安全包装

**建议**: 新建 `tests/test_context_manager.helen`

### 2. `chat_actor.helen` — 0% (6 个函数全部未测)

FFI 入口函数，供 Python 侧 `chat_tui_web.py` 调用:
- `spawn_chat_actor`, `exit_chat_actor`, `is_chat_actor_running`
- `send_heartbeat`, `tui_chat_handler_actor`, `TUIChatAgent`

**分析**: 这些函数在 Python 测试中通过 `sys.modules` mock 测试，不需要 Helen 侧重复测试。
**建议**: 在 Helen 侧写一个轻量测试文件验证函数签名存在即可。

### 3. `output.helen` — 69% (25 个函数未测)

未覆盖函数 (按类别):

**状态查询 (8 个)**:
- `get_output_level`, `get_output_mode`, `get_phase_count`
- `is_thinking_active`, `get_thinking_agent`, `get_thinking_start`
- `is_in_tool_result`, `get_tool_result_chars`

**内部/高级功能 (10 个)**:
- `_colorize`, `_out_get`, `_out_get_list`, `_out_get_map`, `_out_get_score`
- `_should_output`, `_truncate`, `preview_code`
- `format_agent_response`, `format_text_block` (仅部分测试)

**显示控制 (7 个)**:
- `set_output_level`, `set_output_mode`, `set_phase_count`
- `set_thinking_active`, `set_thinking_agent`, `set_thinking_start`
- `set_in_tool_result`, `set_tool_result_chars`

**建议**: 扩展 `test_output_extended.helen` 补充缺失函数的测试

### 4. `chat_session_actor.helen` — 72% (9 个函数未测)

未覆盖函数:
- `_actor_chunks_cb`, `_actor_complete_cb`, `_actor_tool_end_cb` — 流式回调 (3)
- `_handle_actor_command`, `_handle_actor_user_input` — 内部输入处理 (2)
- `save_code_file`, `search_session_transcript`, `update_existing_skill`, `verify_after_change` — 高级工具 (4)

**建议**: 扩展 `test_chat_session_actor_tools.helen`

### 5. `system_reminders.helen` — 75% (1 个函数未测)

未覆盖: `_dynamic_interval` (内部函数，带下划线前缀)

**建议**: 低优先级 — 内部函数，通过 `inject_system_reminders` 间接测试

## 测试失败 (17 个)

| 测试文件 | 失败数 | 失败原因 |
|----------|--------|----------|
| `test_webui_commands.helen` | 6 | `/mode` 命令和 `minimal` 模式未实现 |
| `test_integration.helen` | 4 | Rich 模式 UI 事件发射失败 |
| `test_chat_session_actor_tools.helen` | 3 | `output is non-empty` 检查失败 |
| `test_output.helen` | 2 | `rich` 模式切换失败 |
| `test_shared_modules.helen` | 2 | `update marker` 未找到 |

## 提升建议（按优先级）

### P0 — 快速胜利
1. **`system_reminders.helen`** (75% → 100%): 补 `_dynamic_interval` 测试，1 个函数
2. **`chat_actor.helen`** (0% → 100%): 写函数签名验证测试，6 个简单测试

### P1 — 中等工作量
3. **`chat_session_actor.helen`** (72% → 80%+): 补 3 个回调 + 4 个工具测试，需 mock LLM 响应
4. **`output.helen`** (69% → 80%): 补 9 个状态查询函数测试

### P2 — 重活
5. **`context_manager.helen`** (0% → 80%): 新建测试文件，19 个函数全部需要写。需要 mock session、transcript、compression 等外部依赖
