# 模块系统 (Import)

> 模块 M8 | `helen/runtime/import_resolver.py` | 测试: `tests/runtime/test_import_resolver.py`

---

## 概述

Helen 支持从外部文件导入 Agent、函数和数据。

```helen
import "./utils.helen"
import "./config.json" as cfg
import "./prompt.md"
```

---

## 多格式支持

| 扩展名 | 加载方式 | 返回内容 |
|---|---|---|
| `.helen` | 递归解析 | 注册 Agent/Function，不执行 main |
| `.json` | `json.loads()` | dict / list |
| `.yaml` / `.yml` | `yaml.safe_load()` | dict / list |
| `.md` / `.txt` | 纯文本读取 | str |

---

## 安全机制

### 路径安全检查

```python
def _is_safe_path(self, base_dir: str, resolved: str) -> bool:
    abs_base = os.path.abspath(base_dir)
    abs_resolved = os.path.abspath(resolved)
    return abs_resolved.startswith(abs_base + os.sep) or abs_resolved == abs_base
```

**拦截 `../` 遍历**：

```helen
import "../../secrets.helen"  # ❌ 路径越界
import "./utils.helen"        # ✅ 在当前目录或子目录
```

### 循环导入检测

```python
def resolve(self, path: str, from_file: str) -> ImportResult:
    resolved = self._resolve_path(path, from_file)
    if resolved in self._loaded:
        return None  # 循环导入，静默跳过
    self._loaded.add(resolved)
    # ... 加载文件
```

---

## Import 不执行 main

导入 `.helen` 文件时：

```python
def _parse_helen(self, path: str) -> ImportResult:
    tokens = self._lexer.scan_all()
    program = self._parser.parse(tokens)
    # 只注册 Agent 和 Function，不执行 main 块
    for stmt in program.statements:
        if isinstance(stmt, AgentDeclNode):
            self.agents[stmt.name] = stmt
        elif isinstance(stmt, FunctionDeclNode):
            self.functions[stmt.name] = stmt
```

**安全保证**：被导入文件的 `main { ... }` 不会自动执行。

---

## 相对路径解析

```python
def _resolve_path(self, path: str, from_file: str) -> str:
    base_dir = os.path.dirname(os.path.abspath(from_file))
    return os.path.normpath(os.path.join(base_dir, path))
```

基于**导入者文件所在目录**解析相对路径。

---

## Interpreter 集成

```python
def visit_import_stmt(self, node):
    result = self.import_resolver.resolve(node.path, self._current_file)
    # 合并导入的 Agent 和函数到本地注册表
    for name, agent in self.import_resolver.agents.items():
        if name not in self._agents:
            self._agents[name] = agent
```

导入的 Agent 和函数可以在当前文件中通过 `call` 使用。
