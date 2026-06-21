# Helen 语言不足记录

> 在开发 Helen Programming Agent 过程中发现的 Helen 语言限制和不足。
> 用于指导 Helen 语言的后续改进。

---

## 1. 控制流限制

### 1.1 不支持 `or` 关键字

**问题**：if 条件中不能使用 `or` 连接多个条件。

**示例**：
```helen
// ❌ 不支持
if x == 1 or x == 2 or x == 3 {
    // ...
}

// ✅ 必须用嵌套 if
if x == 1 {
    // ...
}
if x == 2 {
    // ...
}
```

**影响**：代码冗长，可读性差。

**建议**：添加 `or` / `||` 支持。

---

### 1.2 不支持 `and` 关键字

**问题**：if 条件中不能使用 `and` 连接多个条件。

**示例**：
```helen
// ❌ 不支持
if x > 0 and x < 10 {
    // ...
}

// ✅ 必须用嵌套 if
if x > 0 {
    if x < 10 {
        // ...
    }
}
```

**影响**：复杂条件需要多层嵌套。

**建议**：添加 `and` / `&&` 支持。

---

### 1.3 不支持 `else if`

**问题**：没有 `else if` 语法，必须用嵌套 if 或 match。

**示例**：
```helen
// ❌ 不支持
if x == 1 {
    // ...
} else if x == 2 {
    // ...
} else {
    // ...
}

// ✅ 必须用嵌套 if 或 match
if x == 1 {
    // ...
} else {
    if x == 2 {
        // ...
    } else {
        // ...
    }
}
```

**影响**：多分支逻辑代码冗长。

**建议**：添加 `else if` 支持。

---

## 2. 变量名限制

### 2.1 保留字过多

**问题**：`match`、`skills`、`user` 等常见词是保留字，不能用作变量名。

**示例**：
```helen
// ❌ 报错
let match = regex_search(text, pattern)
let skills = get_skills()
let user = get_user()

// ✅ 必须用其他名字
let matched = regex_search(text, pattern)
let skill_list = get_skills()
let usr = get_user()
```

**影响**：命名不自然，需要记忆大量保留字。

**建议**：减少保留字，或提供命名指南。

---

## 3. 函数限制

### 3.1 不支持闭包

**问题**：函数不能捕获定义时的环境（词法作用域），使用动态作用域。

**示例**：
```helen
let x = 10

fn foo() {
    return x  // 期望返回 10
}

fn bar() {
    let x = 99
    return foo()  // 实际返回 99（动态作用域），而非 10
}
```

**影响**：无法实现真正的回调、部分应用、工厂模式。

**建议**：实现词法作用域闭包。

---

### 3.2 不支持匿名函数作为参数

**问题**：不能将匿名函数传递给高阶函数。

**示例**：
```helen
// ❌ 不支持
map([1, 2, 3], fn(x) { return x * 2 })

// ✅ 必须先定义命名函数
fn double(x) { return x * 2 }
map([1, 2, 3], double)
```

**影响**：高阶函数使用不便，代码分散。

**建议**：支持箭头函数 `x => x * 2` 或匿名函数。

---

### 3.3 Agent 的 functions 块只能有 fn 声明

**问题**：Agent 的 `functions {}` 块中只能有 `fn` 声明，不能有 `let` 语句。

**示例**：
```helen
agent MyAgent(input: str) {
    functions {
        // ❌ 不能在这里写 let
        let config = load_config()
        
        fn process() -> str {
            // ✅ 只能在这里写 let
            let result = do_something()
            return result
        }
    }
}
```

**影响**：无法在函数间共享配置/状态。

**建议**：允许 functions 块中有顶层 let 声明。

---

## 4. 内置函数限制

### 4.1 没有 `shell_exec` 函数

**问题**：执行 shell 命令需要用 `exec(cmd, true)`，不是直觉的 `shell_exec(cmd)`。

**示例**：
```helen
// ❌ 不存在
let result = shell_exec("ls -la")

// ✅ 必须用 exec
let result = exec("ls -la", true)
let output = result["stdout"]
```

**影响**：API 不直观。

**建议**：添加 `shell_exec(cmd)` 便捷函数。

---

### 4.2 `exec` 返回 dict 而非字符串

**问题**：`exec` 返回 `{returncode, stdout, stderr}` dict，需要手动提取 stdout。

**示例**：
```helen
let result = exec("echo hello", true)
let output = result["stdout"]  // 需要手动提取
```

**影响**：简单场景代码冗长。

**建议**：添加 `shell_exec(cmd)` 直接返回 stdout 字符串。

---

## 5. 数据结构限制

### 5.1 List 方法有限

**问题**：List 没有 `pop()`、`insert()`、`remove()` 等方法。

**示例**：
```helen
let list = [1, 2, 3]
// ❌ 没有 pop()
let last = list.pop()

// ❌ 没有 insert()
list.insert(0, 0)
```

**影响**：列表操作受限。

**建议**：添加常用列表方法。

---

## 6. 模式匹配限制

### 6.1 match 语句功能有限

**问题**：match 只能匹配字面量，不能匹配模式/范围。

**示例**：
```helen
// ❌ 不支持范围匹配
match x {
    case 1..10: print("small")
    case 11..100: print("medium")
    default: print("large")
}

// ❌ 不支持模式匹配
match point {
    case {x: 0, y: 0}: print("origin")
    default: print("other")
}
```

**影响**：复杂条件判断需要用 if-else。

**建议**：增强 match 语句，支持范围和模式匹配。

---

## 7. 错误处理限制

### 7.1 没有 try-catch 表达式

**问题**：try-catch 是语句，不是表达式，不能返回值。

**示例**：
```helen
// ❌ 不能这样写
let result = try {
    risky_operation()
} catch e {
    default_value()
}
```

**影响**：错误处理代码冗长。

**建议**：支持 try-catch 表达式。

---

## 总结

| 类别 | 问题数 | 优先级 |
|------|:------:|:------:|
| 控制流 | 3 | P0 |
| 变量名 | 1 | P1 |
| 函数 | 3 | P0 |
| 内置函数 | 2 | P1 |
| 数据结构 | 1 | P2 |
| 模式匹配 | 1 | P2 |
| 错误处理 | 1 | P2 |

**最紧急**：
1. 支持 `and` / `or` / `else if`
2. 实现闭包
3. 支持匿名函数
