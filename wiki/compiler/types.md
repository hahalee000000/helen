# 类型系统

> 模块 M9 | `helen/semantic/types.py` | 14 种类型 | 测试: `tests/semantic/test_types.py`

---

## 类型层次

```
Type (ABC)
├── AnyType                    ← 动态类型，LLM 输出默认
├── BoolType                   ← true / false
├── NumberType (ABC)
│   ├── IntType                ← 42
│   └── FloatType              ← 3.14
├── StringType                 ← "hello"
├── NullType                   ← null
├── OptionalType(inner: Type)  ← T?
├── ListType(element: Type)    ← list<T>
├── MapType(key: Type, value: Type)  ← map<K, V>
├── UnionType(members: list[Type])   ← A | B
├── LiteralType(value: Any)    ← 字面量类型
└── AgentType(name: str)       ← Agent<Name>
```

---

## 类型检查规则

### 赋值兼容性

```
AnyType      ← 任何类型可赋值给 AnyType
T            ← T 可赋值给 T
T?           ← T 或 null 可赋值给 T?
A | B        ← A 或 B 可赋值给 A | B
list<T>      ← 元素类型必须匹配
map<K, V>    ← 键和值类型必须匹配
```

### 运算符类型约束

| 运算符 | 左操作数 | 右操作数 | 结果类型 |
|---|---|---|---|
| `+` | Number \| String | Number \| String | Number \| String |
| `-` `*` `/` `%` | Number | Number | Number |
| `==` `!=` | Any | Any | BoolType |
| `>` `>=` `<` `<=` | Number | Number | BoolType |
| `!` | Any | — | BoolType |
| `-` (unary) | Number | — | Number |

### 函数参数检查

```helen
fn add(a: int, b: int): int {
    return a + b
}

add(1, 2)       # ✅ 参数类型匹配
add("a", "b")   # ❌ 类型不匹配
add(1)          # ❌ 参数数量不足
```

---

## 渐进式类型检查

Helen 支持三种类型严格程度：

| 模式 | 行为 | 适用场景 |
|---|---|---|
| **动态** | 无类型注解，全为 AnyType | 快速原型 |
| **注解** | 有类型注解时检查 | 生产代码 |
| **严格** | 所有变量必须注解 | 强类型项目 |

v1 实现默认为**注解模式**：有类型注解时执行检查，否则推断为 AnyType。

---

## 类型推断

```helen
let x = 42          # 推断为 int
let y = "hello"     # 推断为 str
let z = true        # 推断为 bool
let w = [1, 2, 3]   # 推断为 list<int>
let m = {"a": 1}    # 推断为 map<str, int>
```

---

## 可选类型 `T?`

```helen
let name: str? = null    # ✅ 可为空
let name: str = null     # ❌ str 不接受 null

let x: int? = 42
let y: int = x           # ❌ int? 不能直接赋值给 int
```

---

## 联合类型 `A | B`

```helen
let x: int | str = 42    # ✅
x = "hello"              # ✅
x = true                 # ❌ bool 不在联合类型中
```

---

## 类型方法

```python
class Type(ABC):
    def __str__(self) -> str                  # 人类可读表示
    def __eq__(self, other) -> bool           # 类型相等
    def is_compatible_with(self, other) -> bool  # 赋值兼容性
    def is_subtype_of(self, other) -> bool    # 子类型关系
```

### 关键实现

```python
def is_compatible_with(self, other: Type) -> bool:
    if isinstance(other, AnyType):
        return True                    # 任何类型兼容 AnyType
    if isinstance(self, OptionalType):
        if isinstance(other, NullType):
            return True                # null 兼容 T?
        return self.inner.is_compatible_with(other)
    if isinstance(other, UnionType):
        return any(self.is_compatible_with(m) for m in other.members)
    return self == other
```
