# Helen 语言不足分析与完善方案

> 基于 HelenChat 开发过程中的实际体验

## 一、已修复的问题

### 1.1 流式输出 ✅
**问题**：`llm act` 等待完整响应，用户体验差  
**修复**：改用 `llm stream`（支持工具调用 + 流式输出）  
**状态**：已修复并测试通过

---

## 二、stdlib 功能缺失

### 2.1 文件操作函数缺失

| 缺失功能 | 当前 workaround | 建议 |
|---------|----------------|------|
| `write_file(path, content)` | 用 Python FFI `io.open()` | 添加到 stdlib |
| `append_file(path, content)` | 手动 read + write | 添加到 stdlib |
| `mkdir(path)` | 用 `os.makedirs()` | 添加到 stdlib |
| `mkdir_p(path)` | 检查 + makedirs | 添加到 stdlib |

**建议实现**：

```python
# helen/stdlib/__init__.py

def _write_file(path: str, content: str) -> str:
    """Write content to a file. Creates parent directories if needed."""
    import pathlib
    p = pathlib.Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    return f"Wrote {len(content)} bytes to {path}"

def _append_file(path: str, content: str) -> str:
    """Append content to a file. Creates file and parent dirs if needed."""
    import pathlib
    p = pathlib.Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "a", encoding="utf-8") as f:
        f.write(content)
    return f"Appended {len(content)} bytes to {path}"

def _mkdir(path: str) -> str:
    """Create a directory. Parent directories must exist."""
    import pathlib
    pathlib.Path(path).mkdir(parents=False, exist_ok=True)
    return f"Created directory: {path}"

def _mkdir_p(path: str) -> str:
    """Create a directory and all parent directories."""
    import pathlib
    pathlib.Path(path).mkdir(parents=True, exist_ok=True)
    return f"Created directory tree: {path}"
```

**注册到 stdlib**：

```python
BuiltinFunction("write_file", "Write to file", "write_file(path, content)", _write_file, "io"),
BuiltinFunction("append_file", "Append to file", "append_file(path, content)", _append_file, "io"),
BuiltinFunction("mkdir", "Create directory", "mkdir(path)", _mkdir, "io"),
BuiltinFunction("mkdir_p", "Create directory tree", "mkdir_p(path)", _mkdir_p, "io"),
```

### 2.2 字符串操作缺失

| 缺失功能 | 当前 workaround | 建议 |
|---------|----------------|------|
| 字符串切片 `s[start:end]` | 用 `replace()` 去除前缀 | 添加切片语法或函数 |
| `substring(s, start, end)` | 无 | 添加函数 |
| `trim_prefix(s, prefix)` | `replace(s, prefix, "")` | 添加函数（更语义化） |

**建议实现**：

```python
def _substring(s: str, start: int, end: int = None) -> str:
    """Extract substring. If end is None, extracts from start to end of string."""
    if end is None:
        return s[start:]
    return s[start:end]

def _trim_prefix(s: str, prefix: str) -> str:
    """Remove prefix from string if it exists."""
    if s.startswith(prefix):
        return s[len(prefix):]
    return s
```

### 2.3 路径操作缺失

| 缺失功能 | 当前 workaround | 建议 |
|---------|----------------|------|
| `path_join(*parts)` | 用字符串拼接 | 添加函数 |
| `path_dirname(path)` | 用 Python FFI `os.path.dirname()` | 添加函数 |
| `path_basename(path)` | 用 Python FFI `os.path.basename()` | 添加函数 |
| `path_exists(path)` | 用 Python FFI `os.path.exists()` | 添加函数 |

**建议实现**：

```python
def _path_join(*parts: str) -> str:
    """Join path components."""
    import os.path
    return os.path.join(*parts)

def _path_dirname(path: str) -> str:
    """Return directory name."""
    import os.path
    return os.path.dirname(path)

def _path_basename(path: str) -> str:
    """Return base name."""
    import os.path
    return os.path.basename(path)

def _path_exists(path: str) -> bool:
    """Check if path exists."""
    import os.path
    return os.path.exists(path)
```

---

## 三、Python FFI 问题

### 3.1 keyword args 传递失败

**问题**：
```helen
p.mkdir(parents=true, exist_ok=true)  // ❌ RuntimeError: File exists
```

**原因**：Helen FFI 可能不支持 keyword args 或类型转换有问题

**临时 workaround**：
```helen
if (!os.path.exists(dir)) {
    os.makedirs(dir)  // 不用 exist_ok
}
```

**建议修复**：
1. 检查 `helen/ffi/python_object.py` 的 `call()` 方法
2. 验证 keyword args 是否正确传递到 Python
3. 验证 `true` 是否正确转换为 Python `True`

---

## 四、语言特性建议

### 4.1 字符串切片语法

**建议**：支持 `s[start:end]` 语法

```helen
let s = "Hello, World!"
let sub = s[0:5]  // "Hello"
let rest = s[7:]  // "World!"
```

**实现**：在 parser 中添加 slice 语法支持，在 interpreter 中实现切片逻辑。

### 4.2 多行字符串改进

**现状**：支持 `"""..."""` 多行字符串  
**建议**：支持字符串插值

```helen
let name = "Helen"
let greeting = "Hello, {{name}}!"  // "Hello, Helen!"
```

### 4.3 错误处理改进

**现状**：错误信息不够详细  
**建议**：添加 try-catch 语法

```helen
try {
    let content = read_file("nonexistent.txt")
} catch (e) {
    print("Error: " + e.message)
}
```

---

## 五、优先级排序

### P0（立即修复）
1. ✅ 流式输出（已完成）
2. 添加 `write_file` 到 stdlib
3. 添加 `mkdir_p` 到 stdlib

### P1（近期修复）
4. 添加 `append_file` 到 stdlib
5. 添加 `substring` 函数
6. 添加路径操作函数

### P2（长期改进）
7. 字符串切片语法 `s[start:end]`
8. 修复 Python FFI keyword args
9. try-catch 错误处理
10. 字符串插值

---

## 六、HelenChat 改进后的代码

使用新的 stdlib 函数后，HelenChat 可以简化为：

```helen
// 不再需要 Python FFI
fn write_text(file_path, content) {
    write_file(file_path, content)  // 直接调用 stdlib
}

fn append_text(file_path, content) {
    append_file(file_path, content)  // 直接调用 stdlib
}

fn read_text(file_path) {
    return read_file(file_path)  // 已有
}

// 主循环
main {
    mkdir_p("memory")  // 直接调用 stdlib
    
    if (!path_exists("memory/MEMORY.md")) {
        write_file("memory/MEMORY.md", "# Memory\n")
    }
    
    // ...
}
```

---

## 七、实施计划

### Phase 1：stdlib 增强（1-2 天）
1. 实现文件操作函数（write_file, append_file, mkdir, mkdir_p）
2. 实现路径操作函数（path_join, path_dirname, path_basename, path_exists）
3. 实现字符串函数（substring, trim_prefix）
4. 编写测试
5. 更新文档

### Phase 2：语言特性（3-5 天）
1. 实现字符串切片语法
2. 修复 Python FFI keyword args
3. 添加 try-catch（可选）

### Phase 3：HelenChat 重构（1 天）
1. 使用新的 stdlib 函数
2. 移除 Python FFI 依赖
3. 测试流式输出 + 工具调用

---

## 八、总结

HelenChat 开发暴露了 Helen 在以下方面的不足：

1. **stdlib 功能不完整**：缺少基本的文件写入、目录创建、字符串切片等功能
2. **Python FFI 不够健壮**：keyword args 传递有问题
3. **语言特性有待完善**：缺少字符串切片语法、try-catch 等

通过添加这些功能，Helen 将变得更加易用和强大，能够更快速地开发复杂的 AI agent 应用。
