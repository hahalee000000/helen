# 同步 helen/agent 到 helenagent 简版 (v1.0)

## 背景
`../helenagent` 已重构为更简洁的 v1.0:移除 Web SQLite DB(transcript 作唯一数据源)、新增 memento 文件持久化主/子 session_id 的 session 恢复机制、清理过时文件。`helen/agent/` 落后,需同步。

`helen/agent/webui/frontend/node_modules/` 有 **12928 个文件被 git 跟踪**(历史遗留),helenagent 已用 .gitignore 忽略。pyproject.toml 已将 node_modules 排除出 wheel,所以只影响 git 仓库体积,不影响发布包。

## 变更清单

### A. 覆盖修改的源文件(helenagent -> helen/agent)
**根目录**:`chat_session_actor.helen`、`chat_tui.helen`、`chat_tui_web.py`、`commands.helen`、`utils.helen`、`README.md`

**webui/backend/app/**:`config.py`、`main.py`、`routers/chat.py`、`services/helen_bridge.py`、`services/session_index.py`、`websocket/manager.py`;`webui/backend/requirements.txt`

**webui/frontend/src/**:`App.tsx`、`components/chat/ChatWindow.tsx`、`components/layout/Layout.tsx`、`hooks/useChat.ts`、`services/api.ts`、`services/api.test.ts`、`services/websocket.ts`、`stores/chatStore.ts`、`types/index.ts`

**webui/start-backend.sh**

### B. 删除(简版已移除 - DB 摘除)
- `webui/backend/app/database.py`
- `webui/backend/app/models/`(`__init__.py`、`message.py`、`session.py`)
- `webui/frontend/src/pages/TranscriptPage.tsx`
- `webui/frontend/src/pages/TranscriptPage.test.tsx`

### C. 新增(简版新文件)- 默认精简集
- `webui/backend/.env.example`(配置模板,替代直接跟踪 .env)
- `webui/.gitignore`(正确忽略 node_modules/db/env)
- `webui/README.md`、`webui/QUICKSTART.md`(用户文档)
- `webui/test-new-session.sh`(会话测试脚本)
- `tests/` -> `helen/agent/tests/`(Helen 测试套件:`test_*.helen`、`run_tests.sh`、`benchmark.helen` 等)
- `webui/backend/tests/`(Python 后端测试:`test_directory_manager.py`、`test_session_index.py`、`test_transcript_endpoints.py`、`test_upload.py`、`conftest.py`)
- `helen/agent/.gitignore`(agent 根忽略运行时数据:`.helen/sessions`、`webui.db`、`chat_sessions/` 等)

### D. 取消跟踪 node_modules(已确认)
- `git rm -r --cached helen/agent/webui/frontend/node_modules/`(12928 文件移出 git,磁盘文件保留)
- 由 `webui/.gitignore` 的 `node_modules/` 规则覆盖
- 前端开发仍可 `npm install` 重建;发布 wheel 不受影响(本就排除)

### E. 不带过来(repo 元数据 / 非 agent 源)
- `helenagent/CLAUDE.md`(**含代理凭证**,repo 专属指导,helen 有自己的根 CLAUDE.md)
- `helenagent/.plan.md`(规划草稿)
- `helenagent/wiki/`(helenagent 自己的 wiki;helen 有自己的 `wiki/`)
- `helenagent/project/`(示例/用户程序:brainstorm、bubble_sort、paper_writer 等)
- `helenagent/reports/`(10 篇内部架构分析文档 - 默认跳过,如需可后补)
- `webui/BUGFIX_BUTTON_DISABLED.md`、`webui/backend/docs/`(过程性修复笔记 - 默认跳过)
- `webui/backend/scripts/`(空目录,git 不跟踪空目录)

### F. 保持不变(diff 为空)
- `.helen/skills/`(完全一致)
- `contracts/`、`ui/`、`context.helen`、`context_manager.helen`、`json_utils.helen`、`memory_utils.helen`、`output.helen`、`session_stats.helen`、`system_reminders.helen`、`task_manager.helen`、`ui_bridge.helen`、`ui_event_queue.helen`、`start-web.sh`、`contracts/contracts.helen`
- `.env`(未跟踪的运行时配置,留作原样;用户从 `.env.example` 复制生成)

## 执行方式
用 `rsync -a` 从 `../helenagent/` 同步 A+C 的文件(排除 E 中各项 + node_modules + .git + .helen 运行时 + __pycache__),然后 `git rm` B 中的文件,`git rm -r --cached` node_modules,最后 `git add -A helen/agent/`。

## 验证
1. `git status` 确认增删改符合预期
2. `grep -r "database\|models" helen/agent/webui/backend/app/` 确认后端不再 import 已删的 DB 模块
3. 构建 wheel,确认体积合理(~725KB,node_modules 仍被排除)
4. 可行则跑 `webui/backend/tests/` Python 测试

## 提交
单次 commit,信息描述同步到 helenagent v1.0 简版 + 取消跟踪 node_modules。含 Co-Authored-By。
