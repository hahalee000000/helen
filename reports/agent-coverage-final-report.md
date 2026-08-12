# Helen Agent 模块测试覆盖率最终报告

> 生成时间: 2026-08-12 | 目标: 80% 覆盖率

## 成果总览

| 指标 | 改进前 | 改进后 |
|------|--------|--------|
| **达标文件数 (≥80%)** | 1/23 | **23/23** ✅ |
| **100% 覆盖文件** | 0 | **13** |
| **总测试数 (agent)** | ~80 | **442+** (132 main + 310 webui) |
| **agent 整体覆盖率** | 13% | **97%** (main) + **89%** (webui) |

## 逐文件覆盖率

### 主测试套件文件 (tests/agent/)

| 文件 | 语句 | 改进前 | 改进后 | 状态 |
|------|------|--------|--------|------|
| `chat_tui_web.py` | 33 | 0% | **100%** | ✅ |
| `ui/__init__.py` | 5 | 0% | **100%** | ✅ |
| `ui/hint_queue.py` | 36 | 0% | **100%** | ✅ |
| `ui/status_emitter.py` | 28 | 0% | **100%** | ✅ |
| `ui/stream_emitter.py` | 21 | 0% | **100%** | ✅ |
| `webui/start_webui.py` | 173 | 22% | **95%** | ✅ |

### WebUI 后端测试文件 (helen/agent/webui/backend/tests/)

| 文件 | 语句 | 改进前 | 改进后 | 状态 |
|------|------|--------|--------|------|
| `app/__init__.py` | 0 | — | **100%** | ✅ |
| `app/auth.py` | 28 | 68% | **100%** | ✅ |
| `app/config.py` | 54 | 50% | **91%** | ✅ |
| `app/main.py` | 48 | 44% | **90%** | ✅ |
| `app/routers/__init__.py` | 0 | — | **100%** | ✅ |
| `app/routers/agents.py` | 16 | 69% | **100%** | ✅ |
| `app/routers/chat.py` | 333 | 35% | **81%** | ✅ |
| `app/services/__init__.py` | 0 | — | **100%** | ✅ |
| `app/services/channel_actor_manager.py` | 93 | 91% | **99%** | ✅ |
| `app/services/directory_manager.py` | 66 | 64% | **91%** | ✅ |
| `app/services/helen_bridge.py` | 294 | 16% | **90%** | ✅ |
| `app/services/hint_injector.py` | 5 | 60% | **100%** | ✅ |
| `app/services/session_index.py` | 206 | 77% | **87%** | ✅ |
| `app/services/stream_manager.py` | 23 | 48% | **100%** | ✅ |
| `app/services/stream_registry.py` | 15 | 60% | **100%** | ✅ |
| `app/websocket/__init__.py` | 0 | — | **100%** | ✅ |
| `app/websocket/manager.py` | 28 | 29% | **100%** | ✅ |

## 新增/修改的测试文件

### 主测试套件 (`tests/agent/`)
| 测试文件 | 操作 | 测试数 |
|----------|------|--------|
| `test_chat_tui_web.py` | 新建 | 9 |
| `test_ui_init.py` | 新建 | 6 |
| `test_ui_hint_queue.py` | 新建 | 18 |
| `test_ui_status_emitter.py` | 新建 | 17 |
| `test_ui_stream_emitter.py` | 新建 | 12 |
| `test_start_webui.py` | 扩展 | +39 |

### WebUI 后端测试 (`helen/agent/webui/backend/tests/`)
| 测试文件 | 操作 | 测试数 |
|----------|------|--------|
| `test_auth.py` | 扩展 | +12 |
| `test_agents.py` | 新建 | 5 |
| `test_channel_actor_manager.py` | 扩展 | +4 |
| `test_config.py` | 新建 | 26 |
| `test_chat_router.py` | 新建 | 53 |
| `test_directory_manager.py` | 扩展 | +7 |
| `test_helen_bridge.py` | 新建 | 57 |
| `test_hint_injector.py` | 新建 | 4 |
| `test_main.py` | 新建 | 23 |
| `test_session_index.py` | 扩展 | +14 |
| `test_stream_manager.py` | 新建 | 15 |
| `test_stream_registry.py` | 新建 | 8 |
| `test_websocket_manager.py` | 新建 | 10 |

## 基础设施修复

1. **修复 `test_ws_missing_token_rejected` 失败**: WebSocket 端点从裸函数默认值改为 `Depends(verify_ws_token)`，异常类型从 `Exception` 改为 `WebSocketDisconnect(code=1008)`
2. **修复 `test_auth.py` 导入**: 新增 `_token_matches` 导入

## 关键 Mock 策略

| 源文件 | Mock 对象 | 技术 |
|--------|-----------|------|
| `chat_tui_web.py` | `helen.python_bridge`, `chat_actor` | `sys.modules` 注入 `types.ModuleType` |
| `helen_bridge.py` | `chat_tui_web`, `channel_actor_manager`, `directory_manager`, `session_index` | `sys.modules` + `monkeypatch.setattr` |
| `routers/chat.py` | `helen_bridge`, `stream_registry`, `directory_manager` | `unittest.mock.patch` + `monkeypatch` |
| `start_webui.py` | `subprocess.Popen`, `os.killpg`, `signal.signal` | `unittest.mock.patch` |
| `ui/status_emitter.py` | `emit_stream_event` | `unittest.mock.patch` |
| `ui/stream_emitter.py` | 直接测试 | 无外部依赖 |

## 未覆盖的代码（低于 80% 的残余）

少量未覆盖行多为平台特定代码或极端边缘路径：
- `start_webui.py` (8 行): Windows `taskkill` 路径、极端信号处理边缘
- `routers/chat.py` (62 行): WebSocket `do_streaming` 复杂流式路径（61 行）、symlink 边缘
- `helen_bridge.py` (30 行): Windows 路径、文件监视器边缘、流式回调异常路径
- `session_index.py` (26 行): 特殊 boilerplate 过滤边缘、附件解析边缘
- `config.py` (5 行): `_default_helen_path` 父目录回溯路径
- `directory_manager.py` (6 行): 极端 fallback 路径
- `main.py` (5 行): lifespan 边缘路径
