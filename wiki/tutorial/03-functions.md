# 教程 03: 函数

> fn 声明 / 参数 / 返回值 / 函数调用

## 基本函数

```helen
fn greet(name) {
    print("Hello, " + name + "!")
}

main {
    greet("Alice")    // Hello, Alice!
}
```

## 返回值

```helen
fn add(a, b) {
    return a + b
}

main {
    let result = add(3, 5)
    print(result)    // 8
}
```

### 无返回值

```helen
fn say_hello() {
    print("Hello!")
    // 隐式返回 null
}
```

## 参数类型注解

```helen
fn add(a: int, b: int): int {
    return a + b
}

fn greet(name: str): str {
    return "Hello, " + name
}
```

## 参数类型检查

当函数参数有类型注解时，Helen 会在调用时进行类型检查：

### 编译时检查（字面量）

如果调用时传递的是字面量，类型错误会在编译时被捕获：

```helen
fn add(a: int, b: int): int {
    return a + b
}

add(1.5, 2.7)    // ❌ 编译错误：argument 1 type 'FloatType' is not compatible with parameter type 'IntType'
add(1, 2)        // ✅ 正确
```

### 运行时检查（变量）

如果调用时传递的是变量，类型检查会在运行时进行：

```helen
fn add(a: int, b: int): int {
    return a + b
}

let x = 1.5
add(x, 2)        // ❌ 运行时错误：argument 1 type 'FloatType' is not compatible with parameter type 'IntType'

let y = 10
add(y, 2)        // ✅ 正确
```

### 类型兼容性规则

- `int` 可以传递给 `float` 参数（int 是 float 的子类型）
- `float` **不能**传递给 `int` 参数
- 任何类型可以传递给 `any` 参数

```helen
fn processFloat(x: float): float {
    return x * 2
}

processFloat(10)     // ✅ int 可以转换为 float
processFloat(10.5)   // ✅ float 直接匹配

fn processInt(x: int): int {
    return x + 1
}

processInt(10)       // ✅ int 直接匹配
processInt(10.5)     // ❌ float 不能转换为 int
```

## 递归

```helen
fn factorial(n: int): int {
    if n <= 1 {
        return 1
    }
    return n * factorial(n - 1)
}

main {
    print(factorial(5))    // 120
}
```

## 函数作为值

```helen
fn double(x) {
    return x * 2
}

fn apply(op, value) {
    // 在 v1 中，函数通过名称引用
    // 注意：不能用 'fn' 作为参数名（它是关键字）
    print(double(value))
}
```

## Agent 内部函数

Agent 可以在 `functions` 块中定义内部函数:

```helen
agent DataProcessor {
    description "Process and analyze data"

    functions {
        fn validate(data) {
            if len(data) == 0 {
                return false
            }
            return true
        }

        fn transform(data) {
            // 数据转换逻辑
            return data
        }
    }

    prompt """
    Process the given data after validation.
    """
}
```

## 作用域

```helen
let global_x = 100

fn test() {
    let local_x = 200
    print(global_x)    // ✅ 可以访问全局变量
    print(local_x)     // ✅ 可以访问局部变量
}

main {
    print(global_x)    // ✅ 100
    test()
}
```

**注意**: `local_x` 只在 `test()` 函数内部可见，在 `main` 中无法访问。

## 闭包与匿名函数（v1.7+）

Helen 支持闭包（closures）和匿名函数（anonymous functions），允许你创建内联函数并捕获外部作用域的变量。

### 匿名函数

使用 `fn(params) { body }` 语法创建匿名函数：

```helen
// 匿名函数赋值给变量
let add = fn(a, b) { return a + b }
print(add(2, 3))  // 5

// 直接作为参数传递
let doubled = map([1, 2, 3], fn(x) { return x * 2 })
print(doubled)  // [2, 4, 6]

let evens = filter([1, 2, 3, 4, 5], fn(x) { return x % 2 == 0 })
print(evens)  // [2, 4]
```

### 闭包

闭包可以捕获定义时的环境，在后续调用中访问外部变量：

```helen
// 闭包捕获外部变量
fn make_adder(x) {
    return fn(y) { return x + y }
}

let add5 = make_adder(5)
print(add5(10))  // 15
print(add5(20))  // 25

// 闭包在实际应用中
fn make_multiplier(factor) {
    return fn(x) { return x * factor }
}

let double = make_multiplier(2)
let triple = make_multiplier(3)

print(double(5))   // 10
print(triple(5))   // 15
```

### 与高阶函数配合

闭包与 `map`、`filter`、`reduce` 等高阶函数配合使用：

```helen
let nums = [1, 2, 3, 4, 5]

// 使用闭包进行数据转换
let squared = map(nums, fn(n) { return n * n })
print(squared)  // [1, 4, 9, 16, 25]

// 使用闭包进行过滤
let large = filter(nums, fn(n) { return n > 3 })
print(large)  // [4, 5]

// 使用闭包进行聚合
let sum = reduce(nums, fn(acc, n) { return acc + n }, 0)
print(sum)  // 15

// 链式调用
let result = nums
    |> filter(fn(n) { return n % 2 == 0 })
    |> map(fn(n) { return n * 10 })
print(result)  // [20, 40]
```

### 注意事项

- 闭包捕获的是变量的**引用**，不是值
- 匿名函数可以访问定义时的所有外部变量
- 闭包可以用于创建工厂函数、回调函数等模式

## 函数别名 (v1.10)

`alias` 语句可以给现有的函数（stdlib 或用户定义）创建额外的名字。

### 基本语法

```helen
alias <canonical> as <alias_name>
```

### 给 stdlib 起别名

Helen 的 stdlib 已经内置 255 个中文别名（`长度`、`打印`、`排序` 等），可以直接使用。也可以用 `alias` 添加自定义别名：

```helen
alias len as 我的长度
alias print as 输出

主函 {
    我的长度([1, 2, 3])   // 3
    输出("hello")
}
```

### 给用户函数起别名

```helen
函数 greet(name: str): str {
    返回 "Hello, " + name
}

alias greet as 打招呼
alias greet as say_hello

主函 {
    打招呼("Helen")       // "Hello, Helen"
    say_hello("World")    // "Hello, World"
}
```

### 中文关键字 `别名`

`alias` 的中文等价形式：

```helen
别名 len as 长度
别名 greet as 打招呼
```

### 作用域

别名遵守正常的变量作用域规则：
- 顶层 alias 在整个模块可见
- 块内的 alias 只在该块及其嵌套作用域可见
- 别名是快照绑定：`alias f as g` 时 g 指向当时的 f，后续重新定义 f 不影响 g

```helen
函数 foo() { 返回 1 }
alias foo as bar
函数 foo() { 返回 2 }   // 重新定义 foo

主函 {
    foo()   // 2 - 使用新的 foo
    bar()   // 1 - bar 仍指向旧的 foo
}
```

### 错误处理

给不存在的名字起别名会在语义分析阶段报错：

```helen
alias nonexistent as foo   // ❌ Error: cannot alias 'nonexistent': name not found
```

## 练习

1. 编写一个计算斐波那契数列的递归函数
2. 编写一个函数，接受列表并返回最大值
3. 编写一个函数，判断一个字符串是否为回文
4. 使用闭包实现一个计数器函数 `make_counter()`，每次调用返回递增的值
5. 使用 `map` 和匿名函数将列表中的所有字符串转换为大写

---

