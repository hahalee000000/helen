# 教程 04: 控制流

> if / for / while / match / try-catch

## 条件分支

### if / else

```helen
let score = 85

if (score >= 90) {
    print("A")
} else if (score >= 80) {
    print("B")
} else if (score >= 70) {
    print("C")
} else {
    print("F")
}
```

**注意**: `if` 条件必须用括号包裹：`if (cond) { ... }`。

### Truthy 规则

```helen
if 0 { print("不会执行") }        // 0 → false
if "" { print("不会执行") }       // 空字符串 → false
if [] { print("不会执行") }       // 空列表 → false
if null { print("不会执行") }     // null → false
if 1 { print("会执行") }          // 非零 → true
if "hello" { print("会执行") }    // 非空字符串 → true
if [1] { print("会执行") }        // 非空列表 → true
```

### 短路求值 (v1.10)

`&&` 和 `||` 运算符支持**短路求值**，避免不必要的计算：

首先定义一些示例函数：

```helen
fn expensiveFunction(): str {
    // 模拟耗时操作
    return "result"
}

fn getUser(): map? {
    return {"name": "Alice"}
}

fn isValid(): bool {
    return true
}

fn processData(): str {
    return "processed"
}

fn loadConfig(): map? {
    return null
}

fn defaultConfig(): map {
    return {"debug": false}
}

fn createDefaultUser(): map {
    return {"name": "Guest"}
}
```

#### && 短路

```helen
// 如果左侧为 false，右侧不会执行
let result = false && expensiveFunction()  // expensiveFunction() 不会执行

// 实际应用：安全访问
let user = getUser()
let name = user != null && user.getName()  // 如果 user 为 null，不会调用 getName()

// 条件执行
let valid = isValid() && processData()  // 只在 valid 时处理
```

#### || 短路

```helen
// 如果左侧为 true，右侧不会执行
let result = true || expensiveFunction()  // expensiveFunction() 不会执行

// 实际应用：默认值
let config = loadConfig() || defaultConfig()  // 只在加载失败时使用默认值

let user = getUser() || createDefaultUser()  // 如果获取失败，创建默认用户
```

#### 优先级

```helen
// && 优先级高于 ||
let result = a || b && c  // 等价于 a || (b && c)

// 使用括号明确意图
let result = (a || b) && c  // 明确分组
```

#### 实际示例

```helen
// 安全的列表访问
let items = [1, 2, 3]
let first = len(items) > 0 && items[0]  // 避免空列表错误

// 缓存检查
let cached = cache.get(key)
let result = cached != null || computeExpensive()

// 权限检查
let canAccess = isLoggedIn() && hasPermission("admin")
```

## 循环

### for ... in

```helen
for item in ["apple", "banana", "cherry"] {
    print(item)
}
// apple
// banana
// cherry
```

### 带索引遍历

```helen
let fruits = ["apple", "banana", "cherry"]
for fruit in fruits {
    print(fruit)
}
```

### range 遍历

```helen
for i in range(5) {
    print(i)    // 0, 1, 2, 3, 4
}

for i in range(1, 6) {
    print(i)    // 1, 2, 3, 4, 5
}

for i in range(0, 10, 2) {
    print(i)    // 0, 2, 4, 6, 8
}
```

### while

```helen
let count = 0
while (count < 5) {
    print(count)
    count = count + 1
}
```

**注意**: `while` 条件必须用括号包裹：`while (cond) { ... }`。使用 `count = count + 1`（赋值）而非 `let count = count + 1`（新声明），后者会创建局部变量导致死循环。

### break / continue

```helen
for i in range(10) {
    if i == 3 {
        continue    // 跳过 3
    }
    if i == 7 {
        break       // 在 7 退出
    }
    print(i)
}
// 0, 1, 2, 4, 5, 6
```

## 模式匹配

```helen
let status = "success"

match status {
    case "success" { print("OK") }
    case "error" { print("Failed") }
    default { print("Unknown") }
}
```

**注意**: `case` 和 `default` 后面使用 `{ }` 包裹代码块，不是 `:`。

### 数字匹配

```helen
let code = 404

match code {
    case 200 { print("OK") }
    case 404 { print("Not Found") }
    case 500 { print("Server Error") }
    default { print("Other") }
}
```

### 范围匹配

使用 `..` 运算符匹配数值范围（包含边界）：

```helen
let score = 85

match score {
    case 90..100 { print("A") }
    case 80..89 { print("B") }
    case 70..79 { print("C") }
    case 60..69 { print("D") }
    default { print("F") }
}
// 输出: B
```

**注意**：范围运算符 `..` 不会与浮点数混淆。`1..10` 被解析为范围，`1.5` 被解析为浮点数。

### 守卫条件

使用 `if` 添加额外条件判断：

```helen
let x = 25

match x {
    case 21..30 if x == 25 { print("exactly 25") }
    case 21..30 { print("other in range") }
    default { print("out of range") }
}
// 输出: exactly 25
```

守卫条件在范围匹配之后求值，只有两者都满足才会执行对应的 case 块。

## 异常处理

### throw 抛出异常

使用 `throw` 语句主动抛出预定义类型的异常：

```helen
// 带消息 - 用 try-catch 捕获
try {
    throw RuntimeError("something went wrong")
} catch RuntimeError err {
    print("Caught: " + err.message)
}

// 无消息（使用默认消息）
try {
    throw LLMError
} catch LLMError err {
    print("Caught LLM error")
}
```

在函数中使用 throw 进行参数验证：

```helen
fn validate_age(age: int) {
    if (age < 0) {
        throw RuntimeError("age cannot be negative")
    }
    if (age > 150) {
        throw RuntimeError("age seems unrealistic")
    }
    return age
}

try {
    let result = validate_age(-5)
} catch RuntimeError err {
    print("Validation failed: " + err.message)
}
```

**预定义异常类型**：

| 类型 | 说明 |
|------|------|
| `RuntimeError` | 运行时错误 |
| `LLMError` | LLM 相关错误（基类） |
| `TimeoutError` | LLM 调用超时（继承 LLMError） |
| `ModelError` | 模型不可用或配额耗尽（继承 LLMError） |
| `ToolError` | 工具调用失败 |
| `AggregateError` | 多个并发 Agent 任务失败（spawn 场景） |

**异常继承**：`catch LLMError` 也会捕获 `TimeoutError` 和 `ModelError`。

### try / catch

```helen
try {
    let result = validate_age(-5)
    print(result)
} catch RuntimeError err {
    print("Runtime error: " + err.message)
} catch TimeoutError err {
    print("Timeout: " + err.message)
}
```

**语法**: `catch Type varname { ... }`，类型名后直接跟变量名，不需要 `as` 关键字。

### catch-all

```helen
try {
    risky_operation()
} catch {
    // 捕获任何未匹配的错误
    print("Something went wrong")
}
```

### finally

```helen
try {
    open_file()
    process_data()
} catch RuntimeError err {
    print("Error: " + err.message)
} finally {
    close_file()    // 始终执行
}
```

### catch 顺序

```helen
// ✅ 具体类型在前，catch-all 在后
try {
    ...
} catch TimeoutError err {
    ...
} catch LLMError err {
    ...
} catch RuntimeError err {
    ...
} catch {
    ...
}

// ❌ catch-all 必须在最后
try {
    ...
} catch {
    ...
} catch TimeoutError err {    // E0343
    ...
}
```

### 完整示例：自定义验证

```helen
fn divide(a: int, b: int): int {
    if (b == 0) {
        throw RuntimeError("division by zero")
    }
    return a / b
}

try {
    let result = divide(10, 0)
    print("Result: " + str(result))
} catch RuntimeError err {
    print("Cannot divide: " + err.message)
}
// 输出: Cannot divide: division by zero
```

### 捕获标准库异常 (v1.9+)

标准库函数抛出的 Python 异常（`TypeError`、`ValueError`、`FileNotFoundError` 等）会被自动包装为 `RuntimeError`，可用 try-catch 捕获：

```helen
try {
    let x = len(42)        // Python TypeError
} catch RuntimeError err {
    print(err.message)     // "Python TypeError: object of type 'int' has no len()"
}

try {
    let data = read_file("/nonexistent/path")  // Python FileNotFoundError
} catch RuntimeError err {
    // 通过 err.message 前缀区分类型
    if (startswith(err.message, "Python FileNotFoundError")) {
        print("File not found")
    }
}
```

## 综合示例：FizzBuzz

```helen
main {
    for i in range(1, 101) {
        if (i % 15 == 0) {
            print("FizzBuzz")
        } else if (i % 3 == 0) {
            print("Fizz")
        } else if (i % 5 == 0) {
            print("Buzz")
        } else {
            print(i)
        }
    }
}
```

**注意**: 上面的 `main { }` 需要在 `agent` 内部使用。顶层程序直接写 `for`/`if` 等语句即可。

## 练习

1. 使用 for 循环计算 1 到 100 的和
2. 使用 while 循环实现二分查找
3. 编写一个函数，使用 match 判断星期几 (1-7)
4. 编写 try-catch 处理除零错误

---

