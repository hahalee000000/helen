# 语义分析 (Semantic Analyzer)

> 模块 M4 | `helen/semantic/analyzer.py` + `symbols.py` | 测试: `tests/semantic/`

---

## 概述

SemanticAnalyzer 是 AST 的第一个 visitor，负责：
1. **符号表构建** — 收集所有声明
2. **作用域管理** — 跟踪变量可见性
3. **类型检查** — 验证类型兼容性
4. **规则验证** — break 必须在循环内、return 必须在函数内等

---

## 符号表与层级作用域

```python
class ScopeType(Enum):
    GLOBAL = "global"
    AGENT = "agent"
    FUNCTION = "function"
    BLOCK = "block"
    CATCH = "catch"
    LOOP = "loop"
```

### 作用域层级

```
global scope
├── let global_x = 1
├── agent Translator {          ← agent scope
│   │   description "..."
│   ├── let local_y = 2        ← block scope (agent body)
│   └── functions {
│       fn helper() {           ← function scope
│           let z = 3          ← block scope
│       }
│   }
└── main {                      ← block scope
    for x in [1,2,3] {          ← loop scope
        if x > 1 {              ← block scope
            ...
        }
    }
}
```

### 符号操作

```python
class SymbolTable:
    def declare(self, name: str, symbol: Symbol)    # 声明新符号
    def define(self, name: str)                     # 标记为已定义
    def resolve(self, name: str) -> Symbol | None   # 从内到外查找
    def enter_scope(self, type: ScopeType)          # 进入新作用域
    def exit_scope(self)                            # 退出当前作用域
    def current_scope(self) -> ScopeType            # 获取当前作用域类型
```

### 变量解析规则

1. 从**最内层作用域**开始查找
2. 逐层向外直到全局作用域
3. 找到即返回，未找到则报 `UNDECLARED_VARIABLE`

### Agent 边界

**跨 Agent 变量引用检测**：如果 Agent A 内部引用了 Agent B 的局部变量，报 `SCOPE_VIOLATION`。

---

## 类型检查

### 赋值检查

```helen
let x: int = 42        # ✅ 类型匹配
let y: int = "hello"   # ❌ E0331 SEMANTIC_TYPE_ERROR
```

### 函数返回检查

```helen
fn add(a: int, b: int): int {
    return a + b        # ✅ int 返回
}

fn bad(): int {
    return "hello"      # ❌ E0331 SEMANTIC_TYPE_ERROR
}
```

### LLM 输出默认 AnyType

```helen
llm act Translate "text"  # 结果类型为 any（动态）
let result = ...          # 可以赋值给任何类型
```

---

## 规则验证

| 规则 | 错误码 | 示例 |
|---|---|---|
| break 必须在循环内 | E0338 | `break` 在 if 中（非循环） |
| continue 必须在循环内 | E0339 | `continue` 在 fn 中 |
| return 必须在函数内 | E0340 | `return` 在 main 中 |
| match 必须有 default | E0345 | `match x { case 1: ... }` 无 default |
| llm if 必须有 default | E0344 | 无 default 分支 |
| catch-all 必须在最后 | E0343 | `catch { } catch TypeError { }` |
| catch 类型必须预定义 | E0342 | `catch MyCustomError { }` |
| const 不可重新赋值 | E0346 | `const x = 1; x = 2` |
| Agent 参数数量必须匹配 | E0347 | `call Agent(1,2,3)` 参数过多 |
| import 路径必须存在 | E0341 | `import "./nonexistent"` |

---

## 错误收集

SemanticAnalyzer 使用 `ErrorReporter` 收集所有错误（不中断分析）：

```python
class SemanticAnalyzer(Visitor[None]):
    def __init__(self, errors: ErrorReporter):
        self.errors = errors
        self.symbols = SymbolTable()

    def visit_var_decl(self, node):
        if self.symbols.resolve(node.name) is not None:
            self.errors.error(node.span, E0333, f"Duplicate '{node.name}'")
        self.symbols.declare(node.name, Symbol(node.name, ...))
```

---

## 分析流程

```
ProgramNode
  │
  ├── pass 1: 收集顶层声明
  │     ├── AgentDeclNode → symbols.declare(agent_name)
  │     ├── FunctionDeclNode → symbols.declare(fn_name)
  │     └── VarDeclNode → symbols.declare(var_name)
  │
  └── pass 2: 验证语句
        ├── 类型检查
        ├── 作用域验证
        ├── 控制流规则
        └── LLM 语句验证
```
