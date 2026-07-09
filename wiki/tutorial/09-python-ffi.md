# 教程 09: Python FFI

> 导入 Python 库 / 调用 Python 函数 / 类型自动转换

---

## 概述

Helen 支持通过 Python FFI（外部函数接口）直接导入和使用 Python 库。这让 Helen 可以访问 Python 的整个生态系统（40 万+ 包），包括数值计算、网络请求、数据处理等。

**核心特性：**
- ✅ 使用 `import` 语法导入 Python 模块
- ✅ 自动类型转换（Helen ↔ Python）
- ✅ 调用 Python 函数、访问属性和常量
- ✅ 支持嵌套模块（如 `os.path`）
- ✅ 复杂对象自动包装

---

## 基本用法

### 导入 Python 模块

```helen
import "math" as math
import "json" as json
import "os.path" as path
```

**语法规则：**
- 无文件扩展名 → Python 模块
- `.py` 扩展名 → Python 模块
- `.helen` → Helen 文件
- `.json`/`.md`/`.yaml` → 数据文件

### 调用 Python 函数

```helen
import "math" as math

main {
    let sqrt_result = math.sqrt(16)
    print(sqrt_result)    // 4.0
    
    let power = math.pow(2, 10)
    print(power)          // 1024.0
}
```

### 访问 Python 常量

```helen
import "math" as math

main {
    let pi = math.pi
    print(pi)             // 3.141592653589793
    
    let e = math.e
    print(e)              // 2.718281828459045
}
```

---

## 类型转换

### Helen → Python（自动）

| Helen 类型 | Python 类型 |
|-----------|------------|
| `int` | `int` |
| `float` | `float` |
| `str` | `str` |
| `bool` | `bool` |
| `null` | `None` |
| `list` | `list`（递归转换） |
| `map` | `dict`（递归转换） |

### Python → Helen（自动）

| Python 类型 | Helen 类型 |
|------------|-----------|
| `int` | `int` |
| `float` | `float` |
| `str` | `str` |
| `bool` | `bool` |
| `None` | `null` |
| `list` | `list`（递归转换） |
| `dict` | `map`（递归转换） |
| `tuple` | `list` |
| 复杂对象 | 包装为 `PythonObject` |

### 示例：JSON 处理

```helen
import "json" as json

main {
    // Helen map → Python dict → JSON string
    let data = {"name": "Alice", "age": 30, "active": true}
    let json_str = json.dumps(data)
    print(json_str)
    // {"name": "Alice", "age": 30, "active": true}
    
    // JSON string → Python dict → Helen map
    let parsed = json.loads(json_str)
    print(parsed["name"])    // Alice
}
```

---

## 嵌套模块

支持导入嵌套模块（如 `os.path`）：

```helen
import "os.path" as path

main {
    let joined = path.join("home", "user", "docs")
    print(joined)    // home/user/docs
    
    let ext = path.splitext("file.txt")
    print(ext)       // ["file", ".txt"]
}
```

---

## 实际示例

### 示例 1：数学计算

```helen
import "math" as math

main {
    // 三角函数
    let angle = math.pi / 4
    let sin_val = math.sin(angle)
    let cos_val = math.cos(angle)
    print("sin(π/4) = " + str(sin_val))
    print("cos(π/4) = " + str(cos_val))
    
    // 对数
    let log_val = math.log(100, 10)
    print("log₁₀(100) = " + str(log_val))
    
    // 取整
    print(math.floor(3.7))    // 3
    print(math.ceil(3.2))     // 4
}
```

### 示例 2：文件路径操作

```helen
import "os.path" as path

main {
    let filepath = "/home/user/documents/report.txt"
    
    // 提取文件名
    let basename = path.basename(filepath)
    print(basename)    // report.txt
    
    // 提取目录
    let dirname = path.dirname(filepath)
    print(dirname)     // /home/user/documents
    
    // 分离扩展名
    let parts = path.splitext(filepath)
    print(parts[0])    // /home/user/documents/report
    print(parts[1])    // .txt
}
```

### 示例 3：数据处理

```helen
import "json" as json

main {
    // 创建数据
    let users = [
        {"name": "Alice", "age": 30},
        {"name": "Bob", "age": 25},
        {"name": "Charlie", "age": 35}
    ]
    
    // 序列化为 JSON
    let json_data = json.dumps(users)
    print(json_data)
    
    // 解析 JSON
    let parsed = json.loads(json_data)
    for user in parsed {
        print(user["name"] + " is " + str(user["age"]) + " years old")
    }
}
```

### 示例 4：在 Agent 中使用 Python 库

```helen
import "math" as math

agent DataAnalyzer(data: list) {
    description "Analyze numerical data"
    prompt """
    Analyze the following data: {{data}}
    """
    
    functions {
        fn calculate_stats() -> map {
            let n = len(data)
            let sum = 0
            for value in data {
                sum = sum + value
            }
            let mean = sum / n
            
            // 使用 Python 的 math.sqrt
            let variance = 0
            for value in data {
                let diff = value - mean
                variance = variance + diff * diff
            }
            variance = variance / n
            let std_dev = math.sqrt(variance)
            
            return {
                "mean": mean,
                "std_dev": std_dev,
                "min": min(data),
                "max": max(data)
            }
        }
    }
    
    main {
        let stats = calculate_stats()
        return "Mean: " + str(stats["mean"]) + 
               ", Std Dev: " + str(stats["std_dev"])
    }
}

main {
    let data = [10, 20, 30, 40, 50]
    let analyzer = DataAnalyzer(data)
    let result = analyzer()
    print(result)
}
```

---

## 错误处理

### 导入不存在的模块

```helen
import "nonexistent_module" as bad

main {
    // 运行时错误：Cannot import Python module 'nonexistent_module'
}
```

### 访问不存在的属性

```helen
import "math" as math

main {
    let value = math.nonexistent_function()
    // 运行时错误：'math' has no property 'nonexistent_function'
}
```

### 使用 try-catch 处理

```helen
import "math" as math

main {
    try {
        let result = math.sqrt(-1)
        print(result)
    } catch RuntimeError err {
        print("Error: " + err.message)
    }
}
```

---

## 性能注意事项

- **类型转换**：简单类型（int/float/str）转换开销极低
- **复杂对象**：大型 list/dict 转换有一定开销，建议批量处理
- **函数调用**：每次调用都有跨语言开销，避免在紧密循环中频繁调用

---

## 与 Helen 原生功能的对比

| 功能 | Helen 原生 | Python FFI |
|------|-----------|-----------|
| 字符串处理 | ✅ 36 个 string 函数 | ✅ 可用 Python re 等 |
| 数学计算 | ✅ 15 个 math 函数 | ✅ 可用 numpy/scipy |
| 文件操作 | ✅ 16 个 file 函数 | ✅ 可用 os/pathlib |
| 网络请求 | ✅ 9 个 network 函数 | ✅ 可用 requests（高级场景） |
| 数据处理 | ✅ 25 个 data 函数（JSON/CSV/HTML/XML） | ✅ 可用 pandas（大数据集） |
| 机器学习 | ❌ 无 | ✅ 可用 torch/tensorflow |

**建议**：优先使用 Helen 原生功能（255 个内置函数覆盖常见需求），需要高级功能（如大数据处理、机器学习）时使用 Python FFI。

---

## 练习

1. 导入 `math` 模块，计算圆的面积（半径 = 5）
2. 导入 `json` 模块，将 map 转换为 JSON 字符串并解析回来
3. 导入 `os.path` 模块，提取文件路径的目录和文件名
4. 创建一个 Agent，使用 Python 的 `math` 模块进行复杂计算

---

> **下一步**: 学习 [[tutorial/15-python-bridge|Python Bridge]] — 让 Python 直接使用 Helen Agent
