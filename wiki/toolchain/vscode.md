# VS Code 扩展

> 模块 M13 | `vscode-extension/` | 测试: `tests/extension/test_vscode_extension.py`

---

## 概述

Helen VS Code 扩展提供完整的 IDE 支持：
- 🎨 语法高亮
- 🔍 Language Server Protocol (LSP) 集成
- ⚡ 实时诊断
- 💡 代码补全
- 🚀 跳转定义

---

## 文件结构

```
vscode-extension/
├── package.json                      # 扩展清单
├── language-configuration.json       # 语言配置
├── tsconfig.json                     # TypeScript 配置
├── src/
│   └── extension.ts                  # LSP 客户端入口
└── syntaxes/
    └── helen.tmLanguage.json        # TextMate 语法
```

---

## 安装

### 前置条件

1. **安装 Helen**：
```bash
# 推荐：从 PyPI 安装
pip install helen-lang

# 或者从源码安装（开发者）
git clone https://github.com/hahalee000000/helen.git
cd helen
pip install -e .
```

2. **验证安装**：
```bash
helen --version   # Helen 1.20.0
helen lsp         # 应启动 LSP 服务器（按 Ctrl+C 退出）
```

### 从源码安装扩展

```bash
cd vscode-extension
npm install
npm run compile
npx vsce package
# 在 VS Code 中安装生成的 .vsix 文件
```

### 从源码目录安装（开发模式）

```bash
# 复制扩展目录到 VS Code 扩展目录
# Linux/macOS:
cp -r vscode-extension ~/.vscode/extensions/helen-language

# Windows:
xcopy /E /I vscode-extension %USERPROFILE%\.vscode\extensions\helen-language
```

---

## 功能

### 语法高亮

自动为 `.helen` 文件提供语法高亮：

| Scope | 匹配内容 | 颜色主题建议 |
|---|---|---|
| `keyword.control.helen` | if/else/for/while/break/continue/return/match/case/default/try/catch/finally/in/as | 关键字色 |
| `keyword.declaration.helen` | let/const/fn/agent/protocol/impl/functions/main | 声明色 |
| `keyword.other.helen` | import/as/call/await/async/llm/act/stream/is | 特殊关键字色 |
| `keyword.agent.property.helen` | description/model/tools/sub-agents/temperature/max-turns/streaming/prompt/memory | 修饰符色 |
| `support.type.helen` | string/int/float/bool/list/dict/any/number/void | 类型色 |
| `string.quoted.double.helen` | `"..."` | 字符串色 |
| `comment.line.double-slash.helen` | `// ...` | 注释色 |
| `comment.block.helen` | `/* ... */` | 块注释色 |
| `constant.language.boolean.helen` | true/false | 布尔色 |
| `constant.language.null.helen` | null | 空值色 |
| `constant.numeric.integer.helen` | `42` | 数字色 |
| `constant.numeric.float.helen` | `3.14` | 浮点色 |
| `keyword.operator.*.helen` | `+ - * / % == != > < >= <= && \|\| ! = ..` | 运算符色 |
| `entity.name.function.helen` | `fn_name(` | 函数名色 |
| `entity.name.type.agent.helen` | `agent Name` | Agent 名色 |

### Language Server (LSP)

#### 实时诊断

- 语法错误即时显示
- 语义错误检查
- 类型错误提示

#### 代码补全

- 关键字补全（40+ 关键字）
- 类型补全（string, int, float, bool, list, dict, any）
- stdlib 函数补全（print, len, str_upper, regex_match 等）

#### 跳转定义

支持跳转到：
- Agent 声明
- 函数声明
- 变量声明（let/const）

使用 `Ctrl+Click`（或 `Cmd+Click` on macOS）跳转到定义。

---

## 配置

### 扩展设置

在 VS Code 设置中（`Ctrl+,`）搜索 `helen`：

| 设置 | 说明 | 默认值 |
|------|------|--------|
| `helen.lsp.path` | LSP 服务器可执行文件路径 | `"helen"` |
| `helen.lsp.args` | LSP 服务器参数 | `["lsp"]` |
| `helen.lsp.enabled` | 启用/禁用 Language Server | `true` |

### 示例配置

如果 Helen 安装在自定义位置：

```json
{
  "helen.lsp.path": "/home/user/helen/venv/bin/helen",
  "helen.lsp.args": ["lsp"]
}
```

---

## 命令

### Helen: Restart Language Server

重启 Language Server。

**使用方法**：
1. 按 `Ctrl+Shift+P` 打开命令面板
2. 输入 `Helen: Restart Language Server`
3. 按 Enter

---

## 状态栏

扩展在状态栏右侧显示 "Helen" 指示器：
- 点击可重启 Language Server
- 鼠标悬停显示 "Helen Language Server"

---

## 语言配置

### 括号配对

```json
"brackets": [["{", "}"], ["[", "]"], ["(", ")"]]
```

### 自动闭合

```json
"autoClosingPairs": [
    { "open": "{", "close": "}" },
    { "open": "\"", "close": "\"" },
    { "open": "'", "close": "'" },
    { "open": "/*", "close": "*/" }
]
```

### 注释

```json
"comments": {
    "lineComment": "//",
    "blockComment": ["/*", "*/"]
}
```

### 缩进

```json
"indentationRules": {
    "increaseIndentPattern": "^.*\\{[^}\"']*$",
    "decreaseIndentPattern": "^\\s*[\\}\\]\\)].*$"
}
```

---

## 故障排除

### Language Server 未启动

1. **检查 Helen 安装**：
   ```bash
   which helen
   helen help
   ```

2. **检查 VS Code 设置**：
   - 打开设置（`Ctrl+,`）
   - 搜索 "helen"
   - 验证 `helen.lsp.path` 正确

3. **检查输出面板**：
   - 查看 → 输出
   - 从下拉菜单选择 "Helen Language Server"
   - 查看错误消息

### 语法高亮不工作

1. 确保文件扩展名为 `.helen`
2. 检查语言模式（右下角）
3. 手动设置语言：`Ctrl+Shift+P` → "Change Language Mode" → "Helen"

### 补全不工作

1. 等待 Language Server 初始化（检查状态栏）
2. 检查输出面板中的错误
3. 尝试重启 Language Server

---

## 开发

### 构建

```bash
cd vscode-extension
npm install
npm run compile
```

### 打包

```bash
npx vsce package
# 生成 helen-language-1.8.0.vsix
```

### 测试

```bash
# 在 VS Code 中按 F5 启动扩展开发宿主
# 在新窗口中打开 .helen 文件
```

---

## 示例代码

```helen
// 定义 AI agent
agent code_reviewer {
    description = "Reviews code for quality"
    model = "gpt-4"
    temperature = 0.3
    
    functions {
        fn review(code: string) -> dict {
            let issues = []
            return {"issues": issues, "score": 85}
        }
    }
}

// 模式匹配
fn categorize(error: dict) -> string {
    let code = error["code"] ?? 0
    return match code {
        case 1..100 { "error-patterns" }
        case 101..200 { "code-quality" }
        default { "general" }
    }
}

// 协议（接口）
protocol Validator {
    fn validate(data: any) -> bool
}

// 主入口
fn main() {
    let result = code_reviewer.review("print('hello')")
    print(result)
}
```

---

## 语言参考

完整的 Helen 语言文档：
- [Helen GitHub 仓库](https://github.com/hahalee00000/helen)
- [Helen 高级设计文档](https://github.com/hahalee00000/helen/blob/main/documents/Helen_High_Level_Design_v1.2.md)

### 关键特性

- **Agent 声明** - 带 LLM 配置的 AI agent
- **模式匹配** - `match/case` 表达式
- **协议** - `protocol/impl` 接口
- **错误处理** - `try/catch/finally`
- **并发** - `spawn` / Channel 消息队列
- **标准库** - 常用工具函数

---

## 贡献

欢迎贡献！请在 [GitHub](https://github.com/hahalee00000/helen) 上提交 issue 或 PR。

---

**Helen** - The Agent Programming Language 🚀
