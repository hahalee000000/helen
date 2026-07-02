helen> fn add(a, b) { return a + b; }
helen> fn add(a, b) { return a + b + 1; }
Error: duplicate declaration of 'add'
helen> :undefine add
Removed 'add'.
helen> fn add(a, b) { return a + b + 1; }   // ✅ 现在可以重新定义
```

## 生成文档

```bash
$ helen doc hello.helen
# Helen Program Documentation

## Agents

(No agents defined)

## Functions

(No functions defined)

## Built-in Functions
- print(*args) → str — 打印值
- len(value) → int — 长度
...
```

JSON 输出:

```bash
$ helen doc hello.helen --format json
{"agents": [], "functions": [], "builtins": [...]}
```

## 练习

1. 创建一个打印你名字的 Helen 程序
2. 在 REPL 中计算 `1 + 2 * 3`
3. 故意写一个有语法错误的程序，观察错误输出

---

# 教程 02: 变量与类型

> let / const / 类型注解 / 基本运算

## 变量声明

### `let` — 可变变量

```helen
let x = 42
x = 100       // ✅ 可以修改
print(x)      // 100
```

### `const` — 不可变常量

```helen
const PI = 3.14159
PI = 3        // ❌ E0346 CONST_ASSIGNMENT
```

## 数据类型

### 基本类型

```helen
let number = 42         // int
let float_num = 3.14    // float
let text = "hello"      // str
let flag = true         // bool
let nothing = null      // null
```

### 集合类型

```helen
let numbers = [1, 2, 3]                     // list<int>
let mixed = [1, "two", true]                // list<any>
let person = {"name": "Alice", "age": 30}   // map<str, any>
```

## 类型注解

```helen
let name: str = "Alice"
let age: int = 30
let score: float = 95.5
let active: bool = true
```

### 可选类型

```helen
let email: str? = null      // 可以为空
email = "alice@example.com" // ✅
email = null                // ✅

let name: str = null        // ❌ str 不接受 null
```

### 联合类型

```helen
let id: int | str = 42      // 可以是 int 或 str
id = "ABC-123"              // ✅
id = true                   // ❌
```

## 运算

### 算术运算

```helen
let a = 10 + 3      // 13
let b = 10 - 3      // 7
let c = 10 * 3      // 30
let d = 10 / 3      // 3.333...
let e = 10 % 3      // 1
```

### 比较运算

```helen
let eq = 5 == 5     // true
let ne = 5 != 3     // true
let gt = 5 > 3      // true
let ge = 5 >= 5     // true
let lt = 3 < 5      // true
let le = 5 <= 5     // true
```

### 逻辑运算

Helen 使用 `&&`（与）、`||`（或）、`!`（非）作为逻辑操作符：

```helen
let and = true && false   // false
let or = true || false    // true
let not = !true           // false

// 实际使用示例
let x = 5
if x > 0 && x < 10 {
    print("x is between 0 and 10")
}

if !path_exists(file) {
    print("File not found")
}
```

**注意**：Helen 不使用 `and`、`or`、`not` 关键字，而是使用符号 `&&`、`||`、`!`。

### 字符串连接

```helen
let greeting = "Hello, " + "World!"    // "Hello, World!"
let message = "Score: " + 42           // "Score: 42"
```

## 列表操作

```helen
let nums = [1, 2, 3]
let first = nums[0]        // 1
let len = len(nums)        // 3
let range_nums = range(5)  // [0, 1, 2, 3, 4]
```

### 列表方法

Helen 的列表基于 Python list，自动支持所有常用方法：

```helen
let items = [1, 2, 3]

// 添加元素
items.append(4)           // [1, 2, 3, 4]
items.insert(0, 0)        // [0, 1, 2, 3, 4]
items.extend([5, 6])      // [0, 1, 2, 3, 4, 5, 6]

// 移除元素
items.pop()               // 移除并返回最后一个: 6
items.remove(0)           // 移除第一个值为 0 的元素
items.clear()             // 清空列表

// 查询
let idx = items.index(2)  // 返回元素 2 的索引
let cnt = items.count(3)  // 返回元素 3 出现的次数

// 排序与反转
let unsorted = [3, 1, 4, 1, 5]
unsorted.sort()           // [1, 1, 3, 4, 5]
unsorted.reverse()        // [5, 4, 3, 1, 1]

// 复制
let copy = items.copy()   // 浅拷贝
```

### 列表拼接

使用 `+` 操作符可以拼接两个列表，返回一个新列表（原列表不变）：

```helen
let a = [1, 2]
let b = [3, 4]
let c = a + b             // [1, 2, 3, 4]

// 常用于增量构建
let items = []
items = items + ["a"]     // ["a"]
items = items + ["b", "c"]  // ["a", "b", "c"]
```

> 注意：`+` 返回新列表，不修改原列表。如需原地修改，使用 `append()` 或 `extend()`。

**可用方法列表**：
| 方法 | 说明 |
|------|------|
| `append(x)` | 在末尾添加元素 |
| `extend(iterable)` | 扩展列表 |
| `insert(i, x)` | 在位置 i 插入元素 |
| `remove(x)` | 移除第一个值为 x 的元素 |
| `pop([i])` | 移除并返回位置 i 的元素（默认末尾） |
| `clear()` | 清空列表 |
| `index(x)` | 返回第一个值为 x 的索引 |
| `count(x)` | 返回 x 出现的次数 |
| `sort()` | 原地排序 |
| `reverse()` | 原地反转 |
| `copy()` | 浅拷贝 |

## 映射操作

```helen
let person = {"name": "Alice", "age": 30}
let name = person["name"]  // "Alice"
```

### 子脚本/字段赋值 (v1.10)

v1.10 添加了**子脚本赋值**和**字段赋值**支持，可以直接修改数组元素和对象字段：

#### 数组索引赋值

```helen
let arr = [1, 2, 3]
arr[0] = 10  // ✅ arr 变为 [10, 2, 3]
arr[1] = 20  // ✅ arr 变为 [10, 20, 3]

// 动态索引
let i = 2
arr[i] = 30  // ✅ arr 变为 [10, 20, 30]
```

#### 对象字段赋值

```helen
let person = {"name": "Alice", "age": 30}
person["age"] = 31  // ✅ person 变为 {"name": "Alice", "age": 31}
person.name = "Bob"  // ✅ person 变为 {"name": "Bob", "age": 31}
```

#### 嵌套访问

```helen
let matrix = [[1, 2], [3, 4]]
matrix[0][1] = 99  // ✅ matrix 变为 [[1, 99], [3, 4]]

let data = {"users": [{"name": "Alice"}, {"name": "Bob"}]}
data["users"][0]["name"] = "Charlie"  // ✅ 嵌套修改
```

#### 错误示例

```helen
const arr = [1, 2, 3]
arr[0] = 10  // ❌ E0346 CONST_ASSIGNMENT: const 不可修改

const obj = {"name": "Alice"}
obj.name = "Bob"  // ❌ E0346 CONST_ASSIGNMENT: const 不可修改
```

#### 实际示例

```helen
// 更新数组中的记录
let users = [
  {"name": "Alice", "score": 85},
  {"name": "Bob", "score": 90}
]

// 更新第一个用户的分数
users[0]["score"] = 95

// 添加新字段
users[1]["grade"] = "A"

print(users)
// [
//   {"name": "Alice", "score": 95},
//   {"name": "Bob", "score": 90, "grade": "A"}
// ]
```

## 类型检查

```helen
let x = 42
let t = type(x)            // "int"
let is_int = isinstance(x, "int")    // true
let is_str = isinstance(x, "str")    // false
```

## 练习

1. 声明一个 `const` 常量保存你的出生年份
2. 创建一个包含你信息的 map (name, age, city)
3. 计算圆的面积 (PI * r * r)，r = 5
4. 使用类型注解声明一个可选字符串变量

---

