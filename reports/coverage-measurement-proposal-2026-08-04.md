# Helen 语言测试覆盖率测量方案

**日期**: 2026-08-04  
**版本**: v1.0  
**状态**: 方案设计阶段

---

## 目录

1. [背景与目标](#背景与目标)
2. [各语言覆盖率方案分析](#各语言覆盖率方案分析)
3. [对 Helen 的关键启示](#对-helen-的关键启示)
4. [Helen 现有基础设施复用分析](#helen-现有基础设施复用分析)
5. [推荐的实现方案](#推荐的实现方案)
6. [安全性设计](#安全性设计)
7. [实施路线图](#实施路线图)
8. [总结与建议](#总结与建议)

---

## 背景与目标

### 问题陈述

Helen 语言目前缺乏真正的测试覆盖率测量工具。现有的 `score_test_coverage` 只统计测试文件数量，无法测量实际代码覆盖情况。

### 目标

设计并实现一个**安全、高效、易用**的测试覆盖率测量工具，支持：

- **函数覆盖率**：哪些函数被测试调用
- **行覆盖率**：哪些代码行被执行
- **分支覆盖率**：哪些条件分支被走到
- **可视化报告**：生成 HTML/JSON/文本格式报告

### 设计原则

1. **安全性优先**：默认关闭，显式启用，最小化日志
2. **性能可控**：只在测试时启用，零开销设计
3. **易于使用**：一条命令完成覆盖率测量
4. **可扩展性**：支持未来添加新的覆盖率维度

---

## 各语言覆盖率方案分析

### 1. Python：coverage.py + pytest

#### 核心机制

使用 CPython 解释器提供的 `sys.settrace()` API，这是一个专门为实现调试器、性能分析器、覆盖率工具设计的钩子机制。

```python
import sys

def tracer(frame, event, arg):
    # event: 'call', 'line', 'return', 'exception'
    if event == 'line':
        filename = frame.f_code.co_filename
        lineno = frame.f_lineno
        # 记录这一行被执行了
    return tracer

sys.settrace(tracer)
# ... 运行你的代码 ...
sys.settrace(None)
```

#### 三个测量核心

| 核心 | 实现语言 | 特点 |
|------|---------|------|
| **ctrace** | C 语言 | 最快，推荐用于生产环境 |
| **pytrace** | 纯 Python | 较慢，但更容易调试 |
| **sysmon** | Python 3.12+ | 使用新的 `sys.monitoring` API（PEP 669），性能更好 |

#### 两阶段架构

**阶段 1：执行阶段**
- 在代码运行时，跟踪函数记录每一行的执行情况
- 数据存储到 `.coverage` 文件中

**阶段 2：分析阶段**
- 执行完成后，解析源代码和 AST（抽象语法树）
- 确定所有可能被执行的行
- 与实际执行的行对比，生成报告

#### 优缺点

**优点**：
- ✅ 精确度高，可以追踪每一行
- ✅ 不需要修改源代码
- ✅ 支持动态特性（反射、eval 等）

**缺点**：
- ❌ 性能开销大（3-10 倍 slowdown）
- ❌ 仅支持 CPython，不支持 PyPy/Jython
- ❌ 与其他使用 sys.settrace 的工具冲突

### 2. JavaScript：Istanbul / nyc

#### 两种主要方法

##### A. 源代码插桩（传统方法）

使用 Babel 在编译时注入计数器变量：

```javascript
// 原始代码
function add(a, b) {
    return a + b;
}

// 插桩后的代码
var cov_xxx = function () {
    var coverageData = global["__coverage__"];
    cov.f[0]++;  // 函数计数器
    cov.s[0]++;  // 语句计数器
    return a + b;
};
```

##### B. V8 原生覆盖率（现代方法）

V8 引擎内置计数器支持，无需源代码插桩：
- 在 Ignition 字节码解释器中维护块级计数器
- 使用 `IncBlockCounter(slot)` 指令递增计数器
- 通过 V8 Inspector 协议收集覆盖率数据

#### 优缺点

**优点**：
- ✅ V8 原生支持性能极好
- ✅ 不需要修改源代码（V8 方案）
- ✅ 支持现代 JavaScript 特性

**缺点**：
- ❌ 源代码插桩方案需要构建步骤
- ❌ 依赖特定运行时引擎（V8）

### 3. Java：JaCoCo

#### 核心机制

使用 ASM 库在 JVM 字节码级别插入探针。

#### 两种插桩模式

**在线（运行时）插桩**：
```bash
java -javaagent:jacocoagent.jar=destfile=jacoco.exec -jar myapp.jar
```
- 通过 Java Agent 在类加载时拦截并插桩

**离线（构建时）插桩**：
- 在构建时预先插桩类文件
- 运行时不需要 Agent

#### 探针工作原理

1. **控制流分析**：分析每个方法的控制流图（CFG）
2. **探针插入**：在 CFG 的战略位置插入布尔探针数组
3. **运行时跟踪**：每个插桩的类添加：
   ```java
   private static boolean[] $jacocoData;  // 存储哪些探针被触发
   private static void $jacocoInit();     // 初始化探针数组
   ```
4. **数据收集**：JVM 关闭时，探针数据刷新到 `.exec` 文件

#### 优缺点

**优点**：
- ✅ 精确度高，可以追踪指令、分支、行、方法
- ✅ 不需要修改源代码
- ✅ 支持动态类加载

**缺点**：
- ❌ 实现复杂，需要字节码操作
- ❌ 性能开销（虽然比 Python 小）
- ❌ 需要 JVM 环境

### 4. Go：go test -cover

#### 核心机制

**源代码重写**：在编译前插入计数器代码。

```go
// 原始代码
x = 1

// 重写后的代码
GoCover.Counter[0]++; x = 1
```

#### 三种计数器模式

| 模式 | 类型 | 用途 |
|------|------|------|
| **set** | 布尔值 | 这个块是否被执行？ |
| **count** | 整数 | 这个块被执行了多少次？ |
| **atomic** | 原子整数 | 并发安全计数 |

#### 工作流程

1. **源代码重写**：在编译前插入计数器
2. **编译**：重写后的源代码正常编译
3. **执行测试**：作为测试的一部分运行
4. **输出 Profile**：测试运行后，覆盖率数据写入 `coverage.out` 文件

#### 优缺点

**优点**：
- ✅ 实现简单，易于理解
- ✅ 性能开销小（只在测试时）
- ✅ 不需要复杂的运行时支持
- ✅ Go 1.20+ 支持整个应用程序的覆盖率

**缺点**：
- ❌ 需要修改源代码（临时文件）
- ❌ 不支持动态生成的代码
- ❌ 需要编译器支持

### 5. C/C++：gcov

#### 核心机制

**编译器级插桩**：GCC 在编译时插入控制流图边计数器。

```bash
gcc --coverage -o myprogram myprogram.c
# 等价于：gcc -fprofile-arcs -ftest-coverage
```

#### 工作流程

1. **编译时**：生成 `.gcno` 文件（控制流图结构）
2. **运行时**：生成 `.gcda` 文件（执行计数）
3. **报告生成**：`gcov` 工具读取两个文件，生成报告

#### 优缺点

**优点**：
- ✅ 性能开销极小
- ✅ 精确度高
- ✅ 集成在编译器中

**缺点**：
- ❌ 需要编译器支持
- ❌ 实现复杂
- ❌ 需要额外的工具链

---

## 对 Helen 的关键启示

### 启示 1：Helen 最适合 Go 方案（源代码重写）

**原因分析**：

| 特性 | Helen 现状 | 适合度 |
|------|-----------|--------|
| 解释型语言 | ✅ 有完整的 AST | 高 |
| 无复杂字节码 | ✅ 不需要字节码操作 | 高 |
| 编译时可控 | ✅ 可以在解释前修改 AST | 高 |
| 动态特性有限 | ✅ 无 eval/反射，简化处理 | 高 |

**实现思路**：

```helen
// 原始代码
fn add(a, b) {
    return a + b
}

// 重写后（自动插入计数器）
fn add(a, b) {
    __coverage_counter["add:1"] += 1  // 函数入口
    __coverage_counter["add:2"] += 1  // return 语句
    return a + b
}
```

### 启示 2：三种技术路线对比

| 路线 | 代表语言 | 核心思想 | Helen 适用度 |
|------|---------|---------|-------------|
| **运行时钩子** | Python | 解释器级别插桩 | ⭐⭐⭐ 中（有性能开销） |
| **源代码重写** | Go | 编译前插入计数器 | ⭐⭐⭐⭐⭐ 高（简单高效） |
| **字节码插桩** | Java | 字节码级别探针 | ⭐ 低（Helen 无字节码） |
| **引擎原生** | JavaScript | 引擎内置计数器 | ⭐⭐ 低（需要引擎支持） |

### 启示 3：安全性设计的关键点

从各语言实践中学到的安全教训：

| 风险 | 解决方案 | Helen 中的应用 |
|------|---------|---------------|
| 性能开销 | 默认关闭，显式启用 | 只在 `helen test --coverage` 时启用 |
| 信息泄露 | 最小化日志内容 | 只记录函数名和行号，不记录参数值 |
| 磁盘耗尽 | 大小限制 + 自动清理 | 设置最大日志大小，提供清理命令 |
| 并发冲突 | 原子计数器或锁 | 使用线程安全的计数器 |

### 启示 4：可复用现有基础设施

Helen 已经有完善的可观测性基础设施：
- ✅ `ExecutionTracer` - 执行轨迹记录
- ✅ `CallStackTracker` - 调用栈跟踪
- ✅ `trace_on()` / `trace_off()` - 开关控制
- ✅ `LLMAuditLogger` - LLM 调用审计

**这些可以直接复用为覆盖率基础设施！**

---

## Helen 现有基础设施复用分析

### 1. ExecutionTracer - 执行轨迹记录器

#### 现有功能

```python
class ExecutionTracer:
    def __init__(self, max_entries: int = 10000):
        self._entries: list[TraceEntry] = []
        self._max_entries = max_entries
        self._enabled = False
    
    def trace(self, event_type: str, span: SourceSpan | None,
              data: dict[str, Any] | None = None) -> None:
        """记录跟踪条目"""
        if not self._enabled:
            return
        
        if len(self._entries) >= self._max_entries:
            self._entries.pop(0)  # 丢弃最旧的条目
        
        entry = TraceEntry(
            timestamp=time.time(),
            event_type=event_type,
            location=CallFrame.format_location(span),
            data=data or {},
        )
        self._entries.append(entry)
```

#### 可以复用的部分

- ✅ **事件类型系统**：stmt, branch, call, return
- ✅ **位置信息记录**：file:line:col
- ✅ **开关控制机制**：enabled 属性
- ✅ **内存管理**：max_entries 限制，防止内存溢出
- ✅ **序列化支持**：to_list() 方法

#### 需要扩展的部分

- ❌ **持久化存储**：当前只在内存中，需要保存到文件
- ❌ **覆盖率专用事件类型**：需要添加 `coverage_counter` 等
- ❌ **聚合统计**：当前只记录轨迹，不统计执行次数
- ❌ **覆盖率报告生成**：需要添加报告生成逻辑

#### 改造方案

```python
class CoverageTracer(ExecutionTracer):
    """覆盖率专用跟踪器（扩展现有 ExecutionTracer）"""
    
    def __init__(self, output_file: str | None = None):
        super().__init__()
        self._line_counters = defaultdict(int)  # 行号 -> 执行次数
        self._function_counters = defaultdict(int)  # 函数名 -> 调用次数
        self._branch_counters = defaultdict(int)  # 分支ID -> 执行次数
        self._output_file = output_file
    
    def trace_coverage(self, event_type: str, span: SourceSpan):
        """记录覆盖率事件"""
        if not self._enabled:
            return
        
        location = f"{span.file}:{span.start_line}"
        
        if event_type == "stmt":
            self._line_counters[location] += 1
        elif event_type == "call":
            func_name = span.data.get("function", "<unknown>")
            self._function_counters[f"{location}:{func_name}"] += 1
        elif event_type == "branch":
            branch_id = span.data.get("branch_id", 0)
            self._branch_counters[f"{location}:{branch_id}"] += 1
    
    def get_coverage_report(self) -> dict:
        """生成覆盖率报告"""
        return {
            "line_coverage": dict(self._line_counters),
            "function_coverage": dict(self._function_counters),
            "branch_coverage": dict(self._branch_counters),
            "total_lines": len(self._line_counters),
            "covered_lines": sum(1 for c in self._line_counters.values() if c > 0),
            "total_functions": len(self._function_counters),
            "covered_functions": sum(1 for c in self._function_counters.values() if c > 0),
        }
    
    def save_to_file(self):
        """保存覆盖率数据到文件"""
        if not self._output_file:
            return
        
        data = self.get_coverage_report()
        with open(self._output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
```

### 2. CallStackTracker - 调用栈跟踪器

#### 现有功能

```python
class CallStackTracker:
    def __init__(self, max_depth: int = 100):
        self._stack: list[CallFrame] = []
        self._max_depth = max_depth
        self._enabled = False
    
    def push(self, function_name: str, span: SourceSpan | None,
             args: dict[str, Any] | None = None) -> None:
        """推入新的调用帧"""
        if not self._enabled:
            return
        
        if len(self._stack) >= self._max_depth:
            return  # 防止栈溢出
        
        frame = CallFrame(
            function_name=function_name,
            location=CallFrame.format_location(span),
            args=args or {},
        )
        self._stack.append(frame)
    
    def pop(self) -> CallFrame | None:
        """弹出栈顶帧"""
        if not self._enabled or not self._stack:
            return None
        return self._stack.pop()
```

#### 可以复用的部分

- ✅ **函数调用跟踪**：push/pop 机制
- ✅ **调用关系记录**：可以追踪调用链
- ✅ **深度限制**：防止栈溢出

#### 覆盖率应用

```python
class CoverageCallStackTracker(CallStackTracker):
    """覆盖率版本的调用栈跟踪器"""
    
    def __init__(self):
        super().__init__()
        self._covered_functions = set()  # 已调用的函数集合
    
    def push(self, function_name: str, span: SourceSpan | None,
             args: dict[str, Any] | None = None) -> None:
        """记录函数调用（用于覆盖率统计）"""
        # 记录被调用的函数
        if span and span.file:
            func_key = f"{span.file}:{function_name}:{span.start_line}"
            self._covered_functions.add(func_key)
        
        # 调用父类方法
        super().push(function_name, span, args)
    
    def get_function_coverage(self) -> set:
        """获取函数覆盖率"""
        return self._covered_functions
```

### 3. trace_on() / trace_off() - 开关控制

#### 现有功能

```python
def _trace_on() -> str:
    """启用执行跟踪"""
    if _interpreter is None:
        return "No interpreter active"
    _interpreter.observability.tracer.enabled = True
    return "Execution tracing enabled"

def _trace_off() -> str:
    """禁用执行跟踪"""
    if _interpreter is None:
        return "No interpreter active"
    _interpreter.observability.tracer.enabled = False
    return "Execution tracing disabled"

def _get_trace(n: int = 50) -> str:
    """获取最近 n 条跟踪条目"""
    if _interpreter is None:
        return "No interpreter active"
    return _interpreter.observability.tracer.format_trace(last_n=n)
```

#### 可以复用的部分

- ✅ **用户友好的开关 API**：trace_on/trace_off
- ✅ **精确控制**：可以在测试中精确控制何时跟踪
- ✅ **状态查询**：get_trace 可以查看跟踪状态

#### 覆盖率应用

```python
# 添加覆盖率专用开关

def _coverage_on(output_file: str = "coverage.json") -> str:
    """启用覆盖率跟踪"""
    if _interpreter is None:
        return "No interpreter active"
    
    # 创建覆盖率跟踪器
    coverage_tracker = CoverageTracer(output_file=output_file)
    coverage_tracker.enabled = True
    _interpreter.coverage_tracker = coverage_tracker
    
    return f"Coverage tracking enabled, output: {output_file}"

def _coverage_off() -> str:
    """禁用覆盖率跟踪并生成报告"""
    if _interpreter is None or _interpreter.coverage_tracker is None:
        return "Coverage tracking not active"
    
    # 保存覆盖率数据
    _interpreter.coverage_tracker.save_to_file()
    _interpreter.coverage_tracker.enabled = False
    
    # 生成报告
    report = _interpreter.coverage_tracker.get_coverage_report()
    _interpreter.coverage_tracker = None
    
    return f"Coverage report generated: {report}"

def _coverage_report(format: str = "text") -> str:
    """生成覆盖率报告"""
    if _interpreter is None or _interpreter.coverage_tracker is None:
        return "Coverage tracking not active"
    
    report = _interpreter.coverage_tracker.get_coverage_report()
    
    if format == "json":
        return json.dumps(report, indent=2, ensure_ascii=False)
    elif format == "text":
        return _format_text_report(report)
    else:
        return f"Unsupported format: {format}"
```

### 4. 在解释器中的集成点

#### 函数调用跟踪

```python
# helen/interpreter/interpreter.py

class Interpreter:
    def visit_function_call(self, node: CallNode, args: list[Any]) -> Any:
        """访问函数调用"""
        # 记录覆盖率（如果启用）
        if hasattr(self, 'coverage_tracker') and self.coverage_tracker:
            func_name = node.callee.name if hasattr(node.callee, 'name') else str(node.callee)
            self.coverage_tracker.trace_coverage(
                "call",
                node.span,
                {"function": func_name}
            )
        
        # ... 原有逻辑
```

#### 语句执行跟踪

```python
# helen/interpreter/interpreter.py

class Interpreter:
    def visit_statement(self, node: StatementNode) -> Any:
        """访问语句"""
        # 记录覆盖率（如果启用）
        if hasattr(self, 'coverage_tracker') and self.coverage_tracker:
            self.coverage_tracker.trace_coverage("stmt", node.span)
        
        # ... 原有逻辑
```

#### 分支执行跟踪

```python
# helen/interpreter/interpreter.py

class Interpreter:
    def visit_if_statement(self, node: IfStatementNode) -> Any:
        """访问 if 语句"""
        condition = self.visit_expression(node.condition)
        
        # 记录分支覆盖率
        if hasattr(self, 'coverage_tracker') and self.coverage_tracker:
            branch_id = 1 if condition else 0
            self.coverage_tracker.trace_coverage(
                "branch",
                node.span,
                {"branch_id": branch_id, "condition": bool(condition)}
            )
        
        # ... 原有逻辑
```

---

## 推荐的实现方案

### 方案概述

**混合方案**：AST 重写 + 可观测性基础设施复用

```
┌─────────────────────────────────────────┐
│  1. 测试启动（helen test --coverage）    │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│  2. AST 重写阶段（可选）                │
│     - 解析所有源文件和测试文件           │
│     - 在每个函数/语句前插入计数器调用    │
│     - 生成临时文件（带计数器）           │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│  3. 执行阶段                            │
│     - 运行测试（或重写后的测试）         │
│     - CoverageTracer 自动记录执行        │
│     - 计数器累加                         │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│  4. 报告生成阶段                        │
│     - 收集所有计数器                     │
│     - 对比源代码 AST，计算未覆盖部分     │
│     - 生成 HTML/JSON/文本报告            │
└─────────────────────────────────────────┘
```

### 详细实现步骤

#### Step 1：创建 CoverageTracker 类

**文件**: `helen/runtime/coverage.py`

```python
"""测试覆盖率跟踪器"""

from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from helen.core.source import SourceSpan


@dataclass
class CoverageData:
    """覆盖率数据"""
    lines: dict[str, int] = field(default_factory=dict)  # file:line -> count
    functions: dict[str, int] = field(default_factory=dict)  # file:func:line -> count
    branches: dict[str, int] = field(default_factory=dict)  # file:line:branch_id -> count


class CoverageTracker:
    """测试覆盖率跟踪器
    
    扩展现有的 ExecutionTracer，添加覆盖率专用功能。
    """
    
    def __init__(self, output_file: str | None = None, max_size_mb: int = 100):
        """初始化覆盖率跟踪器
        
        Args:
            output_file: 覆盖率数据输出文件路径
            max_size_mb: 最大数据大小（MB），防止磁盘耗尽
        """
        self._data = CoverageData()
        self._output_file = output_file
        self._max_size = max_size_mb * 1024 * 1024
        self._current_size = 0
        self._enabled = False
        
        # 源代码信息（用于生成报告）
        self._source_files: dict[str, list[str]] = {}  # file -> lines
        self._all_functions: set[str] = set()  # 所有函数
        self._all_branches: set[str] = set()  # 所有分支
    
    @property
    def enabled(self) -> bool:
        """是否启用"""
        return self._enabled
    
    @enabled.setter
    def enabled(self, value: bool) -> None:
        """启用或禁用"""
        self._enabled = value
        if not value and self._output_file:
            self.save_to_file()
    
    def record_line(self, span: SourceSpan) -> None:
        """记录行执行
        
        Args:
            span: 源代码位置
        """
        if not self._enabled or not span or not span.file:
            return
        
        # 检查大小限制
        if self._current_size >= self._max_size:
            return  # 静默丢弃，避免崩溃
        
        location = f"{span.file}:{span.start_line}"
        self._data.lines[location] = self._data.lines.get(location, 0) + 1
        self._current_size += len(location) + 10  # 粗略估计
    
    def record_function(self, span: SourceSpan, func_name: str) -> None:
        """记录函数调用
        
        Args:
            span: 函数定义位置
            func_name: 函数名
        """
        if not self._enabled or not span or not span.file:
            return
        
        if self._current_size >= self._max_size:
            return
        
        location = f"{span.file}:{func_name}:{span.start_line}"
        self._data.functions[location] = self._data.functions.get(location, 0) + 1
        self._all_functions.add(location)
        self._current_size += len(location) + 10
    
    def record_branch(self, span: SourceSpan, branch_id: int) -> None:
        """记录分支执行
        
        Args:
            span: 分支位置
            branch_id: 分支ID（0=false, 1=true）
        """
        if not self._enabled or not span or not span.file:
            return
        
        if self._current_size >= self._max_size:
            return
        
        location = f"{span.file}:{span.start_line}:{branch_id}"
        self._data.branches[location] = self._data.branches.get(location, 0) + 1
        self._all_branches.add(f"{span.file}:{span.start_line}")  # 记录分支位置
        self._current_size += len(location) + 10
    
    def register_source_file(self, file_path: str, lines: list[str]) -> None:
        """注册源代码文件（用于报告生成）
        
        Args:
            file_path: 文件路径
            lines: 文件内容行列表
        """
        self._source_files[file_path] = lines
    
    def register_function(self, file_path: str, func_name: str, line: int) -> None:
        """注册函数定义（用于报告生成）
        
        Args:
            file_path: 文件路径
            func_name: 函数名
            line: 行号
        """
        self._all_functions.add(f"{file_path}:{func_name}:{line}")
    
    def register_branch(self, file_path: str, line: int) -> None:
        """注册分支定义（用于报告生成）
        
        Args:
            file_path: 文件路径
            line: 行号
        """
        self._all_branches.add(f"{file_path}:{line}")
    
    def get_coverage_report(self) -> dict[str, Any]:
        """生成覆盖率报告
        
        Returns:
            覆盖率报告字典
        """
        # 行覆盖率
        total_lines = sum(len(lines) for lines in self._source_files.values())
        covered_lines = len([loc for loc, count in self._data.lines.items() if count > 0])
        line_coverage = covered_lines / total_lines if total_lines > 0 else 0.0
        
        # 函数覆盖率
        total_functions = len(self._all_functions)
        covered_functions = len([loc for loc, count in self._data.functions.items() if count > 0])
        function_coverage = covered_functions / total_functions if total_functions > 0 else 0.0
        
        # 分支覆盖率
        total_branches = len(self._all_branches)
        covered_branches = len([
            loc for loc in self._all_branches
            if any(
                self._data.branches.get(f"{loc}:0", 0) > 0 or
                self._data.branches.get(f"{loc}:1", 0) > 0
                for _ in [1]
            )
        ])
        branch_coverage = covered_branches / total_branches if total_branches > 0 else 0.0
        
        # 总体覆盖率
        total_coverage = (line_coverage + function_coverage + branch_coverage) / 3
        
        return {
            "summary": {
                "line_coverage": f"{line_coverage:.1%}",
                "function_coverage": f"{function_coverage:.1%}",
                "branch_coverage": f"{branch_coverage:.1%}",
                "total_coverage": f"{total_coverage:.1%}",
            },
            "details": {
                "lines": {
                    "total": total_lines,
                    "covered": covered_lines,
                    "uncovered": total_lines - covered_lines,
                },
                "functions": {
                    "total": total_functions,
                    "covered": covered_functions,
                    "uncovered": total_functions - covered_functions,
                },
                "branches": {
                    "total": total_branches,
                    "covered": covered_branches,
                    "uncovered": total_branches - covered_branches,
                },
            },
            "data": {
                "line_counters": dict(self._data.lines),
                "function_counters": dict(self._data.functions),
                "branch_counters": dict(self._data.branches),
            },
        }
    
    def save_to_file(self) -> None:
        """保存覆盖率数据到文件"""
        if not self._output_file:
            return
        
        data = {
            "lines": dict(self._data.lines),
            "functions": dict(self._data.functions),
            "branches": dict(self._data.branches),
            "source_files": {k: len(v) for k, v in self._source_files.items()},
            "all_functions": list(self._all_functions),
            "all_branches": list(self._all_branches),
        }
        
        with open(self._output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    def generate_html_report(self, output_dir: str = "coverage_html") -> str:
        """生成 HTML 覆盖率报告
        
        Args:
            output_dir: 输出目录
        
        Returns:
            报告文件路径
        """
        # TODO: 实现 HTML 报告生成
        # 可以参考 coverage.py 的 HTML 报告格式
        pass
    
    def generate_text_report(self) -> str:
        """生成文本覆盖率报告
        
        Returns:
            格式化的文本报告
        """
        report = self.get_coverage_report()
        
        lines = [
            "=" * 60,
            "HELEN TEST COVERAGE REPORT",
            "=" * 60,
            "",
            "Summary:",
            f"  Line Coverage:     {report['summary']['line_coverage']}",
            f"  Function Coverage: {report['summary']['function_coverage']}",
            f"  Branch Coverage:   {report['summary']['branch_coverage']}",
            f"  Total Coverage:    {report['summary']['total_coverage']}",
            "",
            "Details:",
            f"  Lines:     {report['details']['lines']['covered']}/{report['details']['lines']['total']}",
            f"  Functions: {report['details']['functions']['covered']}/{report['details']['functions']['total']}",
            f"  Branches:  {report['details']['branches']['covered']}/{report['details']['branches']['total']}",
            "=" * 60,
        ]
        
        return "\n".join(lines)
```

#### Step 2：在解释器中集成

**文件**: `helen/interpreter/interpreter.py`

```python
class Interpreter:
    def __init__(self, ...):
        # ... 原有初始化
        
        # 覆盖率跟踪器（可选）
        self.coverage_tracker: CoverageTracker | None = None
    
    def visit_function_call(self, node: CallNode, args: list[Any]) -> Any:
        """访问函数调用"""
        # 记录覆盖率（如果启用）
        if self.coverage_tracker and self.coverage_tracker.enabled:
            func_name = node.callee.name if hasattr(node.callee, 'name') else str(node.callee)
            if hasattr(node.callee, 'span'):
                self.coverage_tracker.record_function(node.callee.span, func_name)
        
        # ... 原有逻辑
    
    def visit_statement(self, node: StatementNode) -> Any:
        """访问语句"""
        # 记录覆盖率（如果启用）
        if self.coverage_tracker and self.coverage_tracker.enabled and hasattr(node, 'span'):
            self.coverage_tracker.record_line(node.span)
        
        # ... 原有逻辑
    
    def visit_if_statement(self, node: IfStatementNode) -> Any:
        """访问 if 语句"""
        condition = self.visit_expression(node.condition)
        
        # 记录分支覆盖率
        if self.coverage_tracker and self.coverage_tracker.enabled and hasattr(node, 'span'):
            branch_id = 1 if condition else 0
            self.coverage_tracker.record_branch(node.span, branch_id)
        
        # ... 原有逻辑
```

#### Step 3：添加 stdlib 函数

**文件**: `helen/stdlib/__init__.py`

```python
def _coverage_on(output_file: str = "coverage.json") -> str:
    """启用覆盖率跟踪
    
    Args:
        output_file: 覆盖率数据输出文件
    
    Returns:
        状态消息
    """
    if _interpreter is None:
        return "Error: No interpreter active"
    
    from helen.runtime.coverage import CoverageTracker
    
    # 创建覆盖率跟踪器
    coverage_tracker = CoverageTracker(output_file=output_file)
    coverage_tracker.enabled = True
    _interpreter.coverage_tracker = coverage_tracker
    
    return f"✓ Coverage tracking enabled, output: {output_file}"


def _coverage_off() -> str:
    """禁用覆盖率跟踪并生成报告
    
    Returns:
        状态消息
    """
    if _interpreter is None:
        return "Error: No interpreter active"
    
    if not hasattr(_interpreter, 'coverage_tracker') or _interpreter.coverage_tracker is None:
        return "Error: Coverage tracking not active"
    
    # 保存覆盖率数据
    _interpreter.coverage_tracker.save_to_file()
    
    # 生成报告
    report = _interpreter.coverage_tracker.generate_text_report()
    
    # 禁用跟踪器
    _interpreter.coverage_tracker.enabled = False
    _interpreter.coverage_tracker = None
    
    return f"✓ Coverage report generated:\n{report}"


def _coverage_report(format: str = "text") -> str:
    """生成覆盖率报告
    
    Args:
        format: 报告格式（text, json, html）
    
    Returns:
        格式化的报告
    """
    if _interpreter is None:
        return "Error: No interpreter active"
    
    if not hasattr(_interpreter, 'coverage_tracker') or _interpreter.coverage_tracker is None:
        return "Error: Coverage tracking not active"
    
    if format == "json":
        import json
        report = _interpreter.coverage_tracker.get_coverage_report()
        return json.dumps(report, indent=2, ensure_ascii=False)
    elif format == "text":
        return _interpreter.coverage_tracker.generate_text_report()
    elif format == "html":
        output_path = _interpreter.coverage_tracker.generate_html_report()
        return f"✓ HTML report generated: {output_path}"
    else:
        return f"Error: Unsupported format: {format}"


# 注册到 stdlib
STDLIB_FUNCTIONS.extend([
    # ... 其他函数
    BuiltinFunction("coverage_on", "启用覆盖率跟踪", "coverage_on(output_file?)", _coverage_on, "coverage"),
    BuiltinFunction("coverage_off", "禁用覆盖率跟踪并生成报告", "coverage_off()", _coverage_off, "coverage"),
    BuiltinFunction("coverage_report", "生成覆盖率报告", "coverage_report(format?)", _coverage_report, "coverage"),
])
```

#### Step 4：CLI 集成

**文件**: `helen/cli/__main__.py`

```python
def test_command(args: list[str]) -> int:
    """运行测试"""
    # 解析参数
    coverage_enabled = "--coverage" in args
    coverage_output = None
    
    if coverage_enabled:
        args.remove("--coverage")
        # 检查是否有输出文件参数
        for i, arg in enumerate(args):
            if arg.startswith("--coverage="):
                coverage_output = arg.split("=", 1)[1]
                args.pop(i)
                break
    
    # ... 原有测试逻辑
    
    # 如果启用覆盖率，在解释器中启用跟踪
    if coverage_enabled:
        from helen.stdlib import _coverage_on, _coverage_off
        _coverage_on(coverage_output or "coverage.json")
    
    # 运行测试
    # ...
    
    # 生成覆盖率报告
    if coverage_enabled:
        from helen.stdlib import _coverage_off
        print(_coverage_off())
    
    return 0
```

### AST 重写方案（可选优化）

如果需要更精确的覆盖率，可以在解释前重写 AST：

**文件**: `helen/coverage/ast_rewriter.py`

```python
"""AST 重写器：在 AST 中插入覆盖率计数器"""

from helen.core.ast import (
    ProgramNode, StatementNode, FunctionDeclNode,
    CallNode, VariableNode, StringLiteral, NumberLiteral,
    SourceSpan
)


class CoverageASTRewriter:
    """在 AST 中插入覆盖率计数器"""
    
    def rewrite(self, program: ProgramNode) -> ProgramNode:
        """重写整个程序
        
        Args:
            program: 原始程序 AST
        
        Returns:
            重写后的程序 AST
        """
        new_statements = []
        for stmt in program.statements:
            new_stmt = self._rewrite_statement(stmt)
            new_statements.append(new_stmt)
        
        return ProgramNode(new_statements, program.span)
    
    def _rewrite_statement(self, stmt: StatementNode) -> StatementNode:
        """重写单个语句
        
        在语句前插入覆盖率计数器调用。
        """
        if isinstance(stmt, FunctionDeclNode):
            # 在函数开头插入计数器
            counter_call = self._create_counter_call("function", stmt.span, stmt.name)
            new_body = [counter_call] + list(stmt.body)
            
            return FunctionDeclNode(
                stmt.name,
                stmt.params,
                stmt.return_type,
                new_body,
                stmt.span
            )
        
        # 对于其他语句，在前面插入行计数器
        # TODO: 实现其他语句类型的重写
        
        return stmt
    
    def _create_counter_call(self, event_type: str, span: SourceSpan, name: str = "") -> CallNode:
        """创建覆盖率计数器调用
        
        生成：__coverage_record("function", "file.helen", 10, "func_name")
        """
        return CallNode(
            callee=VariableNode("__coverage_record", span),
            args=[
                StringLiteral(event_type, span),
                StringLiteral(span.file or "", span),
                NumberLiteral(span.start_line, span),
                StringLiteral(name, span),
            ],
            span=span
        )
```

---

## 安全性设计

### 1. 默认关闭，显式启用

**原则**：覆盖率跟踪默认不启用，只有显式请求时才开启。

**实现**：

```bash
# 普通测试（无覆盖率，零开销）
helen test tests/

# 启用覆盖率（有开销）
helen test --coverage tests/

# 指定输出文件
helen test --coverage=coverage.json tests/
```

**代码实现**：

```python
class Interpreter:
    def __init__(self, ...):
        # ... 原有初始化
        
        # 覆盖率跟踪器默认为 None（不启用）
        self.coverage_tracker: CoverageTracker | None = None
```

### 2. 最小化日志内容

**原则**：只记录位置信息，不记录参数值、返回值等敏感数据。

**实现**：

```python
class CoverageTracker:
    def record_function(self, span: SourceSpan, func_name: str) -> None:
        """记录函数调用"""
        # ✅ 安全：只记录函数名和位置
        location = f"{span.file}:{func_name}:{span.start_line}"
        self._data.functions[location] = self._data.functions.get(location, 0) + 1
        
        # ❌ 不安全：不要记录参数值
        # self._data.function_args[location] = args
    
    def record_line(self, span: SourceSpan) -> None:
        """记录行执行"""
        # ✅ 安全：只记录位置
        location = f"{span.file}:{span.start_line}"
        self._data.lines[location] = self._data.lines.get(location, 0) + 1
        
        # ❌ 不安全：不要记录变量值
        # self._data.line_vars[location] = local_vars
```

### 3. 资源限制

**原则**：设置大小限制，防止磁盘耗尽。

**实现**：

```python
class CoverageTracker:
    def __init__(self, output_file: str | None = None, max_size_mb: int = 100):
        self._output_file = output_file
        self._max_size = max_size_mb * 1024 * 1024  # 默认 100 MB
        self._current_size = 0
    
    def record_line(self, span: SourceSpan) -> None:
        """记录行执行（带大小限制）"""
        if not self._enabled or not span or not span.file:
            return
        
        # 检查大小限制
        if self._current_size >= self._max_size:
            # 静默丢弃，避免崩溃
            return
        
        location = f"{span.file}:{span.start_line}"
        self._data.lines[location] = self._data.lines.get(location, 0) + 1
        
        # 更新当前大小（粗略估计）
        self._current_size += len(location) + 10
```

### 4. 自动清理

**原则**：提供清理旧覆盖率数据的命令。

**实现**：

```python
def _coverage_clean(days: int = 7) -> str:
    """清理旧的覆盖率数据文件
    
    Args:
        days: 保留最近多少天的数据
    
    Returns:
        清理结果消息
    """
    import os
    from pathlib import Path
    from datetime import datetime, timedelta
    
    # 查找所有覆盖率文件
    coverage_files = list(Path.cwd().glob("coverage*.json"))
    
    # 计算截止时间
    cutoff = datetime.now() - timedelta(days=days)
    
    deleted = 0
    for file in coverage_files:
        if datetime.fromtimestamp(file.stat().st_mtime) < cutoff:
            file.unlink()
            deleted += 1
    
    return f"✓ Deleted {deleted} coverage file(s) older than {days} day(s)"


# 注册到 stdlib
STDLIB_FUNCTIONS.extend([
    BuiltinFunction("coverage_clean", "清理旧的覆盖率数据", "coverage_clean(days?)", _coverage_clean, "coverage"),
])
```

### 5. 安全审计

**原则**：记录覆盖率跟踪的启用/禁用事件。

**实现**：

```python
class CoverageTracker:
    def __init__(self, ...):
        # ... 原有初始化
        self._audit_log: list[dict] = []
    
    @enabled.setter
    def enabled(self, value: bool) -> None:
        """启用或禁用（带审计日志）"""
        import time
        
        old_value = self._enabled
        self._enabled = value
        
        # 记录审计日志
        self._audit_log.append({
            "timestamp": time.time(),
            "action": "enable" if value else "disable",
            "previous_state": old_value,
        })
        
        if not value and self._output_file:
            self.save_to_file()
```

---

## 实施路线图

### Phase 1：函数覆盖率（1-2 周）

**目标**：实现基础的函数覆盖率测量。

**任务**：

1. **创建 CoverageTracker 类**（2-3 天）
   - 实现基本的计数器数据结构
   - 实现 enable/disable 开关
   - 实现 save_to_file 持久化

2. **在解释器中集成**（2-3 天）
   - 在 visit_function_call 中记录函数调用
   - 添加 coverage_tracker 属性到 Interpreter

3. **添加 stdlib 函数**（1-2 天）
   - 实现 coverage_on/coverage_off
   - 实现 coverage_report（文本格式）

4. **CLI 集成**（1-2 天）
   - 添加 --coverage 参数到 test 命令
   - 自动生成报告

5. **测试和文档**（2-3 天）
   - 编写单元测试
   - 编写用户文档
   - 编写示例

**交付物**：
- ✅ 可以测量函数覆盖率
- ✅ 生成文本报告
- ✅ CLI 命令 `helen test --coverage`

### Phase 2：行覆盖率（2-3 周）

**目标**：实现行级别的覆盖率测量。

**任务**：

1. **扩展 CoverageTracker**（3-4 天）
   - 添加行计数器
   - 实现行覆盖率计算
   - 优化性能

2. **在解释器中集成**（3-4 天）
   - 在 visit_statement 中记录行执行
   - 处理各种语句类型

3. **源代码注册**（2-3 天）
   - 实现 register_source_file
   - 读取源代码用于报告生成

4. **HTML 报告生成**（4-5 天）
   - 实现 generate_html_report
   - 生成带颜色标记的源代码视图
   - 实现交互式报告

5. **测试和优化**（3-4 天）
   - 编写集成测试
   - 性能优化
   - 边界情况处理

**交付物**：
- ✅ 可以测量行覆盖率
- ✅ 生成 HTML 报告（带源代码视图）
- ✅ 性能优化（< 20% 开销）

### Phase 3：分支覆盖率（3-4 周）

**目标**：实现分支级别的覆盖率测量。

**任务**：

1. **扩展 CoverageTracker**（3-4 天）
   - 添加分支计数器
   - 实现分支覆盖率计算
   - 处理复杂条件表达式

2. **在解释器中集成**（4-5 天）
   - 在 visit_if_statement 中记录分支
   - 处理 match 语句
   - 处理循环语句

3. **AST 分析**（3-4 天）
   - 实现分支识别算法
   - 处理嵌套条件
   - 处理短路求值

4. **报告增强**（3-4 天）
   - 在 HTML 报告中显示分支覆盖
   - 添加分支覆盖率统计
   - 实现分支覆盖可视化

5. **测试和优化**（4-5 天）
   - 编写复杂的分支测试用例
   - 性能优化
   - 边界情况处理

**交付物**：
- ✅ 可以测量分支覆盖率
- ✅ HTML 报告显示分支覆盖
- ✅ 完整的覆盖率报告（函数 + 行 + 分支）

### Phase 4：高级功能（可选，2-3 周）

**目标**：实现高级特性和优化。

**任务**：

1. **AST 重写优化**（1-2 周）
   - 实现 CoverageASTRewriter
   - 在编译前插入计数器
   - 提高精确度

2. **增量覆盖率**（3-5 天）
   - 实现增量覆盖率计算
   - 对比不同版本的覆盖率变化
   - 生成差异报告

3. **覆盖率目标**（3-5 天）
   - 实现覆盖率目标设置
   - 未达标时报警
   - CI/CD 集成

4. **性能优化**（3-5 天）
   - 优化计数器数据结构
   - 减少内存占用
   - 提高报告生成速度

**交付物**：
- ✅ AST 重写（可选）
- ✅ 增量覆盖率报告
- ✅ 覆盖率目标检查
- ✅ 性能优化（< 10% 开销）

---

## 总结与建议

### 核心结论

1. **Helen 的 trace 和可观测功能非常有帮助！**
   - ✅ 现成的基础设施（ExecutionTracer、CallStackTracker）
   - ✅ 用户友好的 API（trace_on/trace_off）
   - ✅ 内存管理和安全机制
   - 可以直接复用，比从零开始高效得多

2. **推荐的实现方案：混合方案**
   - 复用现有 ExecutionTracer 基础设施
   - 扩展为 CoverageTracker
   - 可选的 AST 重写优化

3. **安全性设计是关键**
   - 默认关闭，显式启用
   - 最小化日志内容
   - 资源限制和自动清理
   - 安全审计

### 实施建议

**优先级排序**：

| 阶段 | 功能 | 优先级 | 工作量 |
|------|------|--------|--------|
| Phase 1 | 函数覆盖率 | P0 高 | 1-2 周 |
| Phase 2 | 行覆盖率 | P1 中 | 2-3 周 |
| Phase 3 | 分支覆盖率 | P2 低 | 3-4 周 |
| Phase 4 | 高级功能 | P3 可选 | 2-3 周 |

**建议从 Phase 1 开始**：
- 快速交付，验证方案可行性
- 收集用户反馈
- 为后续阶段奠定基础

### 技术风险

| 风险 | 可能性 | 影响 | 缓解措施 |
|------|--------|------|---------|
| 性能开销过大 | 中 | 高 | 优化数据结构，使用增量更新 |
| 内存占用过高 | 中 | 中 | 设置大小限制，定期清理 |
| 精确度不够 | 低 | 中 | 可选的 AST 重写方案 |
| 实现复杂度高 | 中 | 中 | 分阶段实施，逐步迭代 |

### 成功标准

- ✅ **功能完整**：支持函数、行、分支覆盖率
- ✅ **性能良好**：开销 < 20%
- ✅ **易于使用**：一条命令完成
- ✅ **安全可靠**：无信息泄露，无资源耗尽
- ✅ **用户满意**：报告清晰，易于理解

---

## 附录

### A. 参考资料

1. **Python coverage.py**: https://coverage.readthedocs.io/
2. **Go cmd/cover**: https://go.dev/blog/cover
3. **JaCoCo**: https://www.jacoco.org/
4. **Istanbul.js**: https://istanbul.js.org/
5. **gcov**: https://gcc.gnu.org/onlinedocs/gcc/Instrumentation-Options.html

### B. 术语表

| 术语 | 说明 |
|------|------|
| **覆盖率** | 衡量测试代码覆盖源代码程度的指标 |
| **行覆盖率** | 被执行的代码行占总代码行的比例 |
| **函数覆盖率** | 被调用的函数占总函数的比例 |
| **分支覆盖率** | 被执行的分支占总分支的比例 |
| **插桩** | 在代码中插入计数器或跟踪代码的过程 |
| **AST** | 抽象语法树（Abstract Syntax Tree） |
| **AST 重写** | 在编译或解释前修改 AST 的技术 |

### C. 相关文件

- `helen/runtime/observability.py` - 现有可观测性基础设施
- `helen/interpreter/interpreter.py` - 解释器主文件
- `helen/stdlib/__init__.py` - stdlib 函数注册
- `helen/cli/__main__.py` - CLI 入口

### D. 变更日志

| 日期 | 版本 | 变更 |
|------|------|------|
| 2026-08-04 | v1.0 | 初始方案文档 |

---

**文档维护者**: Helen 开发团队  
**最后更新**: 2026-08-04
