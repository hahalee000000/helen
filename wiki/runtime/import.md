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

---

## v1.10 shared let 导入跟踪

### 概述

v1.10 添加了 `shared let` 关键字，用于声明跨 agent 可见的可变变量。导入的 `shared let` 被正确跟踪，可以在导入模块的 agent 中访问和修改。

### 导入行为

导入 `.helen` 文件时，`shared let` 变量会被跟踪并导入：

```python
def _parse_helen(self, path: str) -> ImportResult:
    tokens = self._lexer.scan_all()
    program = self._parser.parse(tokens)
    
    # 注册 Agent 和 Function
    for stmt in program.statements:
        if isinstance(stmt, AgentDeclNode):
            self.agents[stmt.name] = stmt
        elif isinstance(stmt, FunctionDeclNode):
            self.functions[stmt.name] = stmt
        elif isinstance(stmt, VarDeclNode) and stmt.is_shared:
            # v1.10: 跟踪 shared let
            self.shared_vars[stmt.name] = {
                'value': self._evaluate_const(stmt.value),
                'mutable': True,
                'source': path
            }
```

### 示例

**module_a.helen**:
```helen
shared let counter = 0
shared let config = {
  "debug": true,
  "max_retries": 3
}

agent Worker {
  main {
    counter += 1
    print("Counter: " + str(counter))
  }
}
```

**module_b.helen**:
```helen
import "./module_a.helen"

agent Manager {
  main {
    // 可以访问导入的 shared let
    counter += 10  // ✅ 合法
    config["debug"] = false  // ✅ 合法
    
    // 调用导入的 agent
    call Worker()
  }
}
```

### 作用域规则

导入的 `shared let` 遵循以下规则：

| 变量类型 | 在导入模块中可见？ | 可修改？ |
|---------|------------------|---------|
| 模块级 `let` | ❌ 不可见 | - |
| 模块级 `const` | ✅ 可见 | ❌ 只读 |
| `shared let` | ✅ 可见 | ✅ 可读写 |

### 模块函数作用域解析 (v1.10)

导入模块的函数在调用时，可以访问其**自身模块**的 `const` 和 `shared let`，无论是否使用别名导入。

**非别名导入**：函数和变量直接注入全局命名空间。

```helen
// module.helen
const MAX = 100
shared let counter = 0

fn inc() { counter = counter + 1 }
fn total(): int { return MAX + counter }

// main.helen
import "./module.helen"
main {
    inc()
    print(total())       // ✅ 101 — 函数可见模块的 const 和 shared let
    print(counter)       // ✅ 1 — shared let 直接可见
    print(MAX)           // ✅ 100 — const 直接可见
}
```

**别名导入**：通过模块对象访问。

```helen
// output.helen
const OUTPUT_NORMAL = 1
shared let _use_colors = true

fn _colorize(text: str): str {
    if _use_colors {
        return "[C]" + text + "[/C]"
    }
    return text
}

fn set_use_colors(enabled: bool) {
    _use_colors = enabled
}

// main.helen
import "./output.helen" as output
main {
    print(output.OUTPUT_NORMAL)          // ✅ 1 — const 通过别名访问
    print(output._use_colors)            // ✅ true — shared let 通过别名访问
    print(output._colorize("hello"))     // ✅ "[C]hello[/C]" — 函数可见模块变量
    output.set_use_colors(false)
    print(output._colorize("hello"))     // ✅ "hello" — shared let 已修改
}
```

**实现原理**：导入时为每个模块创建独立的模块级 `Environment`，其中定义了该模块的 `const` 和 `shared let`。调用模块函数时，该 Environment 作为父作用域传入，确保函数能看到模块级变量。

### 循环导入处理

如果存在循环导入，`shared let` 的处理与普通变量一致：

```python
def resolve(self, path: str, from_file: str) -> ImportResult:
    resolved = self._resolve_path(path, from_file)
    if resolved in self._loaded:
        return None  # 循环导入，跳过
    self._loaded.add(resolved)
    # ... 加载并跟踪 shared let
```

### 错误处理

导入不存在的 `shared let` 会报错：

```helen
import "./module_a.helen"

agent MyAgent {
  main {
    let x = nonexistent_var  // ❌ E0333 UNDECLARED_VARIABLE
  }
}
```

---

**最后更新**: 2026-07-01  
**版本**: v1.10
