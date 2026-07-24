# Tutorial 03: Functions

> fn declarations / parameters / return values / function calls

## Basic Functions

```helen
fn greet(name) {
    print("Hello, " + name + "!")
}

main {
    greet("Alice")    // Hello, Alice!
}
```

## Return Values

```helen
fn add(a, b) {
    return a + b
}

main {
    let result = add(3, 5)
    print(result)    // 8
}
```

### No Return Value

```helen
fn say_hello() {
    print("Hello!")
    // Implicitly returns null
}
```

## Parameter Type Annotations

```helen
fn add(a: int, b: int): int {
    return a + b
}

fn greet(name: str): str {
    return "Hello, " + name
}
```

## Parameter Type Checking

When function parameters have type annotations, Helen performs type checking at call time:

### Compile-time Checking (Literals)

If literal values are passed at the call site, type errors are caught at compile time:

```helen
fn add(a: int, b: int): int {
    return a + b
}

add(1.5, 2.7)    // ❌ Compile error: argument 1 type 'FloatType' is not compatible with parameter type 'IntType'
add(1, 2)        // ✅ Correct
```

### Runtime Checking (Variables)

If variables are passed at the call site, type checking is performed at runtime:

```helen
fn add(a: int, b: int): int {
    return a + b
}

let x = 1.5
add(x, 2)        // ❌ Runtime error: argument 1 type 'FloatType' is not compatible with parameter type 'IntType'

let y = 10
add(y, 2)        // ✅ Correct
```

### Type Compatibility Rules

- `int` can be passed to `float` parameters (int is a subtype of float)
- `float` **cannot** be passed to `int` parameters
- Any type can be passed to `any` parameters

```helen
fn processFloat(x: float): float {
    return x * 2
}

processFloat(10)     // ✅ int can be converted to float
processFloat(10.5)   // ✅ float matches directly

fn processInt(x: int): int {
    return x + 1
}

processInt(10)       // ✅ int matches directly
processInt(10.5)     // ❌ float cannot be converted to int
```

## Recursion

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

## Functions as Values

```helen
fn double(x) {
    return x * 2
}

fn apply(op, value) {
    // In v1, functions are referenced by name
    // Note: cannot use 'fn' as a parameter name (it is a keyword)
    print(double(value))
}
```

## Agent Internal Functions

Agents can define internal functions in a `functions` block:

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
            // Data transformation logic
            return data
        }
    }

    prompt """
    Process the given data after validation.
    """
}
```

## Scope

```helen
let global_x = 100

fn test() {
    let local_x = 200
    print(global_x)    // ✅ Can access global variable
    print(local_x)     // ✅ Can access local variable
}

main {
    print(global_x)    // ✅ 100
    test()
}
```

**Note**: `local_x` is only visible inside the `test()` function and cannot be accessed in `main`.

## Closures and Anonymous Functions (v1.7+)

Helen supports closures and anonymous functions, allowing you to create inline functions and capture variables from outer scopes.

### Anonymous Functions

Use `fn(params) { body }` syntax to create anonymous functions:

```helen
// Assign an anonymous function to a variable
let add = fn(a, b) { return a + b }
print(add(2, 3))  // 5

// Pass directly as an argument
let doubled = map([1, 2, 3], fn(x) { return x * 2 })
print(doubled)  // [2, 4, 6]

let evens = filter([1, 2, 3, 4, 5], fn(x) { return x % 2 == 0 })
print(evens)  // [2, 4]
```

### Closures

Closures can capture the environment at the point of definition, accessing outer variables in subsequent calls:

```helen
// Closure captures outer variable
fn make_adder(x) {
    return fn(y) { return x + y }
}

let add5 = make_adder(5)
print(add5(10))  // 15
print(add5(20))  // 25

// Closures in practical applications
fn make_multiplier(factor) {
    return fn(x) { return x * factor }
}

let double = make_multiplier(2)
let triple = make_multiplier(3)

print(double(5))   // 10
print(triple(5))   // 15
```

### Working with Higher-order Functions

Closures work well with higher-order functions like `map`, `filter`, and `reduce`:

```helen
let nums = [1, 2, 3, 4, 5]

// Use closures for data transformation
let squared = map(nums, fn(n) { return n * n })
print(squared)  // [1, 4, 9, 16, 25]

// Use closures for filtering
let large = filter(nums, fn(n) { return n > 3 })
print(large)  // [4, 5]

// Use closures for aggregation
let sum = reduce(nums, fn(acc, n) { return acc + n }, 0)
print(sum)  // 15

// Chained calls
let result = nums
    |> filter(fn(n) { return n % 2 == 0 })
    |> map(fn(n) { return n * 10 })
print(result)  // [20, 40]
```

### Caveats

- Closures capture variable **references**, not values
- Anonymous functions can access all outer variables at the point of definition
- Closures can be used to create factory functions, callback functions, and other patterns

## Function Aliases (v1.10)

The `alias` statement can create additional names for existing functions (stdlib or user-defined).

### Basic Syntax

```helen
alias <canonical> as <alias_name>
```

### Aliasing stdlib Functions

Helen's stdlib already includes 255 Chinese aliases (`长度`, `打印`, `排序`, etc.) that can be used directly. You can also use `alias` to add custom aliases:

```helen
alias len as 我的长度
alias print as 输出

主函 {
    我的长度([1, 2, 3])   // 3
    输出("hello")
}
```

### Aliasing User Functions

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

### Chinese Keyword `别名`

The Chinese equivalent of `alias`:

```helen
别名 len as 长度
别名 greet as 打招呼
```

### Scope

Aliases follow normal variable scoping rules:
- Top-level aliases are visible throughout the module
- Aliases inside a block are only visible within that block and its nested scopes
- Aliases are snapshot bindings: `alias f as g` makes g point to f at that moment; subsequent redefinitions of f do not affect g

```helen
函数 foo() { 返回 1 }
alias foo as bar
函数 foo() { 返回 2 }   // Redefine foo

主函 {
    foo()   // 2 - uses the new foo
    bar()   // 1 - bar still points to the old foo
}
```

### Error Handling

Aliasing a nonexistent name produces an error during semantic analysis:

```helen
alias nonexistent as foo   // ❌ Error: cannot alias 'nonexistent': name not found
```

## Exercises

1. Write a recursive function to compute Fibonacci numbers
2. Write a function that accepts a list and returns the maximum value
3. Write a function that determines whether a string is a palindrome
4. Use closures to implement a counter function `make_counter()` that returns an incrementing value on each call
5. Use `map` and anonymous functions to convert all strings in a list to uppercase

---
