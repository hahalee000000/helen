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

### v1.10 Agent 作用域隔离

`agent main {}` 在**完全隔离的环境**中运行，语义分析器强制以下规则：

#### 可见性规则

| 变量类型 | 在 agent main 中可见？ | 说明 |
|---------|---------------------|------|
| 模块级 `let` | ❌ 不可见 | 编译时错误 |
| 模块级 `const` | ✅ 可见 | 只读访问 |
| `shared let` | ✅ 可见 | 可读写 |
| agent 局部变量 | ✅ 可见 | agent 作用域内 |
| agent main 局部变量 | ✅ 可见 | main 作用域内 |

#### 示例

```helen
// 模块级变量
let moduleVar = "模块级"      // ❌ agent main 中不可见
const MODULE_CONST = "常量"   // ✅ 只读可见
shared let sharedVar = 0      // ✅ 可读写

agent MyAgent {
  let agentVar = "agent 级"   // ✅ agent 作用域
  
  main {
    // moduleVar              // ❌ E0350 SCOPE_VIOLATION
    let x = MODULE_CONST      // ✅ 只读访问
    sharedVar += 1            // ✅ 可修改
    
    let localVar = "局部"     // ✅ main 作用域
    
    fn closure() {
      // 闭包可以捕获局部变量
      print(localVar)         // ✅
    }
  }
}
```

#### 语义分析实现

```python
def visit_agent_main(self, node):
    self.symbols.enter_scope(ScopeType.AGENT_MAIN)
    
    # 标记模块级 let 为不可见
    for symbol in self.global_scope_lets:
        symbol.visible_in_agent_main = False
    
    # 分析 main 块
    for stmt in node.statements:
        self.analyze(stmt)
    
    self.symbols.exit_scope()
```

### v1.10 shared let 语义

`shared let` 声明跨 agent 可见的可变变量：

#### 符号表处理

```python
def visit_var_decl(self, node):
    if node.is_shared:  # shared let
        symbol = Symbol(
            name=node.name,
            type=self.infer_type(node.value),
            scope=ScopeType.GLOBAL,
            shared=True,
            mutable=True
        )
        # shared let 在所有 agent main 中可见
        self.global_shared_vars.append(symbol)
    else:
        # 普通 let/const
        ...
```

#### 导入跟踪

导入的 `shared let` 被正确跟踪：

```helen
// module_a.helen
shared let counter = 0

// module_b.helen
import "./module_a.helen"

agent Worker {
  main {
    counter += 1  // ✅ 可以访问导入的 shared let
  }
}
```

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
| 模块级 let 在 agent main 中不可见 | E0350 | `let x = 1; agent A { main { x } }` |
| shared let 必须在模块级声明 | E0351 | `agent A { shared let x = 1 }` |
| 子脚本赋值目标必须是可变的 | E0352 | `const arr = [1,2]; arr[0] = 3` |

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
