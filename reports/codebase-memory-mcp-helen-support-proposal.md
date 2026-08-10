# Helen 语言支持扩展方案 — codebase-memory-mcp

> 日期: 2026-08-07 | 版本: v1.0 | 状态: 草案

---

## 1. 背景与目标

### 1.1 动机

Helen 是一门 AI-native Agent 编程语言（当前 v1.39.8，364 stdlib 函数，3671 测试）。codebase-memory-mcp 是一个基于 tree-sitter 的代码知识图谱引擎（支持 155+ 语言，22,686 nodes / 126,945 edges 的索引能力）。

将 Helen 语言纳入 codebase-memory-mcp 的支持范围，可以让 Helen 开发者获得：
- 函数/类/方法的结构化索引与搜索
- 调用图（CALLS 边）和依赖分析
- 跨文件引用追踪
- 热点函数识别（fan-in/fan-out）
- Cypher 图查询

### 1.2 目标

| 目标 | 优先级 | 说明 |
|---|---|---|
| `.helen` 文件被识别为 Helen 语言 | P0 | 语言检测层 |
| 函数/agent/方法定义被提取为 Def 节点 | P0 | 基础索引 |
| 函数调用被提取为 CALLS 边 | P0 | 调用图 |
| import 语句被提取为 IMPORTS 边 | P1 | 依赖图 |
| 变量/常量定义被提取 | P1 | 完整索引 |
| Helen 关键字不被误识别为标识符 | P1 | 精确性 |
| 中文标识符支持 | P2 | Helen 特色（CJK identifiers） |
| LSP 类型解析集成 | P3 | 精度增强（可选） |

### 1.3 Helen 语言特征摘要（影响 grammar 设计）

| 特征 | 说明 |
|---|---|
| 文件扩展名 | `.helen` |
| 关键字 | 99 个（48 英文 + 51 中文），双语等价 |
| 标识符 | 支持 CJK（中文/日文/韩文）字符 |
| 注释 | `//` 单行，`/* */` 多行 |
| 字符串 | `"..."` 双引号，支持 `\uNNNN` 转义 |
| 函数声明 | `fn name(params): ret_type { body }` |
| Agent 声明 | `agent Name(params) { description, tools, prompt, main {} }` |
| 变量 | `let x = expr` / `const x = expr` |
| 控制流 | `if`/`for`/`while`/`match`/`try-catch` |
| LLM 原语 | `llm act` / `llm if` |
| 并发 | `spawn Agent(...)`, `shared store`, `Channel` |
| 模块 | `import std.xxx.*` / `import "path.helen"` |
| 类型 | 14 种：int, float, str, bool, list, map, Optional, Union, Protocol, Agent, Literal... |
| Lambda | `fn(x) { x + 1 }` |
| 装饰器 | `@open agent`, `@strict agent`, `@sandbox agent`, `@atomic` |

---

## 2. codebase-memory-mcp 语言支持架构

通过分析 codebase-memory-mcp 源码（22,686 nodes），语言支持由以下 7 层组成：

```
┌───────────────────────────────────────────────────────────────┐
│ Layer 7: LSP 集成（cbm_run_py_lsp, cbm_run_go_lsp, ...）      │  可选
├───────────────────────────────────────────────────────────────┤
│ Layer 6: 提取器定制（extract_vars/extract_calls switch case） │  可选
├───────────────────────────────────────────────────────────────┤
│ Layer 5: CBMLangSpec（节点类型 → 语义概念映射表）              │  必须
├───────────────────────────────────────────────────────────────┤
│ Layer 4: 语言注册（EXT_TABLE + LANG_NAMES + FILENAME_TABLE）  │  必须
├───────────────────────────────────────────────────────────────┤
│ Layer 3: Grammar wrapper（grammar_helen.c + vendored parser） │  必须
├───────────────────────────────────────────────────────────────┤
│ Layer 2: CBMLanguage enum（cbm.h 加 CBM_LANG_HELEN）          │  必须
├───────────────────────────────────────────────────────────────┤
│ Layer 1: Tree-sitter grammar（tree-sitter-helen）             │  必须
└───────────────────────────────────────────────────────────────┘
```

### 2.1 关键文件清单

| 文件 | 作用 | 修改类型 |
|---|---|---|
| `internal/cbm/cbm.h` | CBMLanguage enum | 加一行 |
| `internal/cbm/lang_specs.h` | CBMLangSpec 结构体定义 | 不改 |
| `internal/cbm/lang_specs.c` | 语言规格表（节点类型映射） | 加一个 entry |
| `internal/cbm/grammar_helen.c` | tree-sitter grammar wrapper | 新建 |
| `internal/cbm/vendored/grammars/helen/` | vendored tree-sitter parser | 新建目录 |
| `src/discover/language.c` | EXT_TABLE + LANG_NAMES | 加两行 |
| `internal/cbm/extract_defs.c` | 变量提取 switch | 可选加 case |
| `internal/cbm/extract_calls.c` | 调用提取 | 可选加 case |
| `internal/cbm/helpers.c` | 关键字表 + 导出判定 | 加 Helen 分支 |
| `scripts/new-languages.json` | 语言元数据 | 加 Helen entry |
| `Makefile.cbm` | 构建配置 | 加 grammar 编译 |

### 2.2 现有语言参考（Python 为例）

以 Python 支持为参照，理解每层的实际内容：

| 层 | Python 实现 |
|---|---|
| L2 | `CBM_LANG_PYTHON` enum |
| L3 | `grammar_python.c` → vendored tree-sitter-python |
| L4 | `{".py", CBM_LANG_PYTHON}` + `[CBM_LANG_PYTHON] = "Python"` |
| L5 | function: `function_definition`, class: `class_definition`, call: `call`, import: `import_statement`/`import_from_statement` |
| L6 | `extract_vars_mainstream()`, `cbm_run_py_lsp()`, `python_keywords[]` |
| L7 | `cbm_run_py_lsp()` — 类型感知调用解析 |

---

## 3. 分阶段实施方案

### Phase 0: Tree-sitter-helen Grammar（前置依赖）

**目标**：能正确 parse `.helen` 文件为 CST（Concrete Syntax Tree）

**状态**：目前不存在 tree-sitter-helen。需要从头创建。

#### 3.1 Grammar 设计

**grammar.js 核心规则**（基于 Helen 的 58 个 AST 节点）：

```javascript
module.exports = grammar({
  name: 'helen',

  extras: $ => [/\s/, $.line_comment, $.block_comment],

  word: $ => $.identifier,  // 支持 CJK

  rules: {
    source_file: $ => repeat($._statement),

    // ── 声明 ──
    function_declaration: $ => seq(
      'fn', field('name', $.identifier),
      optional($.parameter_list),
      optional(seq(':', field('return_type', $._type))),
      $.block
    ),

    agent_declaration: $ => seq(
      repeat($.decorator),
      'agent', field('name', $.identifier),
      optional($.parameter_list),
      $.agent_body
    ),

    variable_declaration: $ => seq(
      choice('let', 'const'), field('name', $.identifier),
      optional(seq(':', $._type)),
      '=', field('value', $._expression)
    ),

    // ── 控制流 ──
    if_statement: $ => seq('if', field('condition', $._expression), $.block, optional(seq('else', $.block))),
    for_statement: $ => seq('for', $.identifier, 'in', $._expression, $.block),
    while_statement: $ => seq('while', $._expression, $.block),
    match_statement: $ => seq('match', $._expression, '{', repeat($.case_clause), '}'),

    // ── 表达式 ──
    call_expression: $ => seq(field('function', $._expression), field('arguments', $.argument_list)),
    llm_act_expression: $ => seq('llm', 'act', optional($._expression)),
    spawn_expression: $ => seq('spawn', $.identifier, $.argument_list),

    // ── Import ──
    import_statement: $ => seq('import', choice(
      seq($.string_literal, optional(seq('as', $.identifier))),
      seq('std', '.', $.identifier, '.', choice('*', seq('{', commaSep($.identifier), '}'))),
    )),

    // ── 标识符（CJK 支持）──
    identifier: $ => /[\p{L}\p{Nl}_][\p{L}\p{Nl}\p{Mn}\p{Mc}\p{Nd}_]*/u,
  }
});
```

#### 3.2 关键挑战

| 挑战 | 难度 | 解决方案 |
|---|---|---|
| 99 个双语关键字 | 中 | keywords 列表包含所有英文 + 中文关键字 |
| CJK 标识符 | 低 | Unicode property escape `\p{L}` |
| `fn` 双重语义（声明 vs lambda） | 中 | context-dependent：顶层 = 声明，表达式位置 = lambda |
| `main {}` 特殊块 | 低 | 作为 special_block 处理 |
| `shared store` 双词关键字 | 中 | 在 grammar 中用 `seq('shared', 'store')` |
| 字符串插值 `{{var}}` | 中 | template_string 规则 |
| 装饰器 `@open`, `@strict` | 低 | decorator 规则 |
| `llm act`/`llm if` 双词关键字 | 中 | `seq('llm', 'act')`/`seq('llm', 'if')` |

#### 3.3 工期估算

| 子步骤 | 工期 |
|---|---|
| grammar.js 编写 | 1 周 |
| 关键字表（99 个） | 1 天 |
| CJK 标识符测试 | 1 天 |
| 测试用例（覆盖所有语法结构） | 3-5 天 |
| 调试 + 修复 parse error | 3-5 天 |
| **小计** | **2-3 周** |

---

### Phase 1: 基础集成（Layer 2-4）

**目标**：`.helen` 文件被识别，tree-sitter 能 parse，基本 Def 提取

#### Step 1.1: CBMLanguage Enum

**文件**: `internal/cbm/cbm.h`

```c
// 在 CBM_LANG_COUNT 之前添加
CBM_LANG_HELEN,
```

#### Step 1.2: Grammar Wrapper

**文件**: `internal/cbm/grammar_helen.c`（新建）

```c
// Vendored tree-sitter grammar: helen
#include "vendored/grammars/helen/parser.c"
```

**目录**: `internal/cbm/vendored/grammars/helen/` — 放入 tree-sitter-helen 编译产物

#### Step 1.3: 语言注册

**文件**: `src/discover/language.c`

```c
// EXT_TABLE 中添加
{".helen", CBM_LANG_HELEN},

// LANG_NAMES 中添加
[CBM_LANG_HELEN] = "Helen",
```

#### Step 1.4: 构建配置

**文件**: `Makefile.cbm`

添加 `grammar_helen.c` 编译规则。

#### Step 1.5: 验证

```bash
make -f Makefile.cbm test  # 确认编译通过
echo 'fn hello() { print("hello") }' > /tmp/test.helen
cbm index /tmp/  # 确认 .helen 被识别
```

**工期**: 1-2 天

---

### Phase 2: 语义映射（Layer 5 — CBMLangSpec）

**目标**：函数/agent/调用/导入被正确提取为图节点和边

**文件**: `internal/cbm/lang_specs.c`

```c
// ── Helen node type arrays ──

static const char *helen_function_types[] = {
    "function_declaration",
    "lambda_expression",
    NULL
};

static const char *helen_class_types[] = {
    "agent_declaration",
    "shared_store_declaration",
    "protocol_declaration",
    "struct_declaration",
    NULL
};

static const char *helen_field_types[] = {
    "field_declaration",
    NULL
};

static const char *helen_module_types[] = {
    "source_file",
    NULL
};

static const char *helen_call_types[] = {
    "call_expression",
    "llm_act_expression",
    "llm_if_statement",
    "spawn_expression",
    "method_call",
    NULL
};

static const char *helen_import_types[] = {
    "import_statement",
    NULL
};

static const char *helen_import_from_types[] = {
    "import_from",  // import std.xxx.{...}
    NULL
};

static const char *helen_branching_types[] = {
    "if_statement",
    "for_statement",
    "while_statement",
    "match_statement",
    "match_expression",
    "try_statement",
    NULL
};

static const char *helen_variable_types[] = {
    "variable_declaration",      // let
    "const_declaration",         // const
    "parameter",                 // fn params
    "agent_parameter",           // agent params
    NULL
};

static const char *helen_assignment_types[] = {
    "assignment_statement",
    "augmented_assignment",
    NULL
};

static const char *helen_throw_types[] = {
    "throw_statement",
    NULL
};

static const char *helen_decorator_types[] = {
    "decorator",   // @open, @strict, @sandbox, @atomic
    NULL
};

// ── Lang spec entry ──

extern const TSLanguage *tree_sitter_helen(void);

[CBM_LANG_HELEN] = {
    .language = CBM_LANG_HELEN,
    .function_node_types = helen_function_types,
    .class_node_types = helen_class_types,
    .field_node_types = helen_field_types,
    .module_node_types = helen_module_types,
    .call_node_types = helen_call_types,
    .import_node_types = helen_import_types,
    .import_from_types = helen_import_from_types,
    .branching_node_types = helen_branching_types,
    .variable_node_types = helen_variable_types,
    .assignment_node_types = helen_assignment_types,
    .throw_node_types = helen_throw_types,
    .decorator_node_types = helen_decorator_types,
    .ts_factory = tree_sitter_helen,
},
```

**关键验证点**：

| 验证 | 测试代码 | 预期结果 |
|---|---|---|
| 函数提取 | `fn foo() { print("hi") }` | Def: foo, label=Function |
| Agent 提取 | `agent Bot { main {} }` | Def: Bot, label=Class |
| 调用提取 | `foo(1, 2)` | CALLS edge: caller → foo |
| LLM act 提取 | `llm act "prompt"` | CALLS edge (特殊节点) |
| Import 提取 | `import std.core.*` | IMPORTS edge |
| 变量提取 | `let x = 42` | Variable: x |
| 装饰器提取 | `@open agent Bot {}` | decorator_tags: ["@open"] |
| spawn 提取 | `spawn Worker("task")` | CALLS edge: → Worker |

**工期**: 2-3 天

---

### Phase 3: 提取器定制（Layer 6）

**目标**：精确提取 + 关键字过滤 + 中文标识符

#### 3.1 Helen 关键字表

**文件**: `internal/cbm/helpers.c`

```c
static const char *helen_keywords[] = {
    // 英文关键字 (48)
    "agent", "alias", "assert", "break", "catch", "const", "continue",
    "default", "else", "enum", "expect", "false", "fn", "for", "if",
    "impl", "import", "in", "let", "llm", "main", "match", "null",
    "protocol", "return", "shared", "spawn", "store", "throw", "true",
    "try", "type", "while",
    // v1.31+ 新增
    "transcript", "thinking-mode", "reasoning-effort", "max-tokens",
    // 中文关键字 (51)
    "智能体", "别名", "断言", "中断", "捕获", "常量", "继续",
    "默认", "否则", "枚举", "期望", "假", "函数", "循环", "如果",
    "实现", "导入", "在...中", "设", "大模型", "主程序", "匹配", "空",
    "协议", "返回", "共享", "分生", "存储", "抛出", "真",
    "尝试", "类型", "当",
    // v1.31+ 新增
    "记录", "思考模式", "推理强度", "最大tokens",
    NULL
};
```

在 `cbm_is_keyword()` 的 switch 中添加：

```c
case CBM_LANG_HELEN:
    keywords = helen_keywords;
    break;
```

#### 3.2 导出判定

Helen 所有函数默认导出（无 `_` 前缀约定），在 `cbm_is_exported()` 中：

```c
case CBM_LANG_HELEN:
    return (name[0] != '_');  // _ 前缀为私有
```

#### 3.3 变量提取

**文件**: `internal/cbm/extract_defs.c`

在 `extract_var_names()` 的 switch 中添加 Helen：

```c
case CBM_LANG_HELEN:
    // let/const 声明的 name 字段 + parameter 节点
    extract_vars_helen(ctx, node, a, kind);
    return;
```

#### 3.4 llm act / spawn 调用提取

**文件**: `internal/cbm/extract_calls.c`

Helen 的 `llm act` 和 `spawn Agent()` 不是普通函数调用，需要在调用提取中特殊处理：

```c
if (ctx->language == CBM_LANG_HELEN) {
    if (strcmp(kind, "llm_act_expression") == 0) {
        // 提取为对 "llm_act" 的调用（或特殊标签）
    }
    if (strcmp(kind, "spawn_expression") == 0) {
        // 提取为对 agent 名称的调用
    }
}
```

**工期**: 3-5 天

---

### Phase 4: LSP 集成（可选，Layer 7）

**目标**：类型感知的调用解析（跨文件引用、方法解析）

Helen 已有 `helen lsp` 命令（JSON-RPC over stdio）。可以添加 `cbm_run_helen_lsp()` 接入。

**工作项**：
1. 定义 Helen LSP 客户端协议适配
2. 实现 hover/definition 请求的发送和解析
3. 将 LSP 返回的类型信息注入 CALLS 边的 resolved_call

**工期**: 1-2 周（可选）

---

## 4. 验证方案

验证分为 **7 个层次**，从底层 grammar 到顶层端到端查询，逐层递进。每一层有明确的输入、预期输出和判定标准。

### 4.1 Grammar 正确性验证

**目标**：tree-sitter-helen 能正确 parse 所有合法 Helen 程序，拒绝非法程序。

**方法**：编写 `tests/test_helen_parse.c`，对每类语法结构验证 parse tree。

**验证模式**（与 codebase-memory-mcp 的 `test_py_lsp.c` 相同）：

```c
static CBMFileResult *extract_helen(const char *source) {
    return cbm_extract_file(source, (int)strlen(source), CBM_LANG_HELEN,
                            "test", "main.helen", 0, NULL, NULL);
}
```

**测试矩阵**：

| # | 测试名称 | 输入 | 验证点 |
|---|---|---|---|
| G1 | `helen_parse_fn_basic` | `fn foo() { return 1 }` | tree 无 ERROR 节点 |
| G2 | `helen_parse_fn_typed` | `fn foo(x: int): str { return "hi" }` | 参数类型 + 返回类型节点存在 |
| G3 | `helen_parse_agent` | `agent Bot(name: str) { description "bot" main { } }` | agent_declaration 节点 |
| G4 | `helen_parse_let_const` | `let x = 1\nconst y = "hi"` | variable_declaration 节点 |
| G5 | `helen_parse_if_for_while` | `if cond { } else { }\nfor x in list { }\nwhile cond { }` | 3 种控制流节点 |
| G6 | `helen_parse_match` | `match x { case 1 { "one" }\n case _ { "other" } }` | match_statement + case_clause |
| G7 | `helen_parse_llm_act` | `llm act "prompt"` | llm_act_expression 节点 |
| G8 | `helen_parse_llm_if` | `llm if cond { branch1 } else { branch2 }` | llm_if_statement 节点 |
| G9 | `helen_parse_spawn` | `spawn Agent("task")` | spawn_expression 节点 |
| G10 | `helen_parse_import_wildcard` | `import std.core.*` | import_statement 节点 |
| G11 | `helen_parse_import_selective` | `import std.str.{len, upper}` | import_statement + 选择列表 |
| G12 | `helen_parse_import_namespace` | `import std.str as S` | import_statement + alias |
| G13 | `helen_parse_import_file` | `import "utils.helen"` | import_statement + 文件路径 |
| G14 | `helen_parse_lambda` | `let f = fn(x) { x + 1 }` | lambda_expression 节点 |
| G15 | `helen_parse_shared_store` | `shared store Counter { count: int = 0\n fn inc() { count += 1 } }` | shared_store_declaration |
| G16 | `helen_parse_decorator` | `@open agent Bot { }` | decorator 节点 |
| G17 | `helen_parse_try_catch` | `try { } catch RuntimeError e { }\ncatch { }` | try_statement + catch_clause + catch_all |
| G18 | `helen_parse_cjk_identifier` | `let 变量 = 42\nfn 函数() { }` | identifier 节点包含 CJK 字符 |
| G19 | `helen_parse_bilingual_keywords` | `设 x = 1\n如果 x > 0 { 返回 x }` | 中文关键字被正确识别 |
| G20 | `helen_parse_fullwidth_punct` | `let x = "中文，标点。"` | 全角标点不影响 parse |
| G21 | `helen_parse_template_string` | `"""Hello {{name}}"""` | template_string 节点 |
| G22 | `helen_parse_protocol` | `protocol Drawable { fn draw() }` | protocol_declaration 节点 |
| G23 | `helen_parse_type_union` | `let x: int | str = 42` | union_type 节点 |
| G24 | `helen_parse_type_optional` | `let x: str? = null` | optional_type 节点 |
| G25 | `helen_parse_pipe` | `x |> fn(y) { y + 1 }` | pipe_expression 节点 |

**负面测试**（非法输入应产生 ERROR 或 parse_incomplete）：

| # | 测试名称 | 输入 | 验证点 |
|---|---|---|---|
| N1 | `helen_reject_missing_brace` | `fn foo() { return 1` | ERROR 节点存在 |
| N2 | `helen_reject_invalid_type` | `let x: !!! = 1` | ERROR 节点存在 |
| N3 | `helen_reject_unclosed_string` | `let x = "hello` | ERROR 节点存在 |

### 4.2 定义提取验证

**目标**：函数、agent、类、变量被正确提取为 Def 节点。

**方法**：`tests/test_helen_extraction.c`，调用 `extract_helen()` 后检查 `result->defs`。

**验证模式**（与 codebase-memory-mcp 的 Python 提取测试相同）：

```c
static int find_def(const CBMFileResult *r, const char *name, const char *label) {
    for (int i = 0; i < r->defs.count; i++) {
        const CBMDefinition *d = &r->defs.items[i];
        if (d->name && strcmp(d->name, name) == 0 &&
            d->label && strcmp(d->label, label) == 0)
            return i;
    }
    return -1;
}

#define REQUIRE_DEF(r, name, label) do { \
    int idx = find_def(r, name, label); \
    if (idx < 0) { \
        printf("  MISSING def: name=%s label=%s (have %d defs)\n", \
               name, label, (r)->defs.count); \
        for (int i = 0; i < (r)->defs.count; i++) { \
            printf("    [%d] %s (%s)\n", i, \
                   (r)->defs.items[i].name ?: "(null)", \
                   (r)->defs.items[i].label ?: "(null)"); \
        } \
    } \
    ASSERT(idx >= 0); \
} while (0)
```

**测试矩阵**：

| # | 测试名称 | 输入 | 验证点 |
|---|---|---|---|
| D1 | `helen_def_function` | `fn foo() { }` | Def: foo, label=Function |
| D2 | `helen_def_function_typed` | `fn bar(x: int): str { return "" }` | Def: bar, 参数列表含 x, 返回类型 str |
| D3 | `helen_def_agent_as_class` | `agent Bot(name: str) { main {} }` | Def: Bot, label=Class |
| D4 | `helen_def_shared_store` | `shared store C { v: int = 0 }` | Def: C, label=Class |
| D5 | `helen_def_protocol` | `protocol Draw { fn draw() }` | Def: Draw, label=Class/Interface |
| D6 | `helen_def_let_var` | `fn f() { let x = 42 }` | Def: x, label=Variable |
| D7 | `helen_def_const_var` | `const PI = 3.14` | Def: PI, label=Variable |
| D8 | `helen_def_lambda` | `let f = fn(x) { x + 1 }` | Def: f (lambda 被捕获为变量) |
| D9 | `helen_def_cjk_name` | `fn 计算() { }` | Def: 计算, label=Function |
| D10 | `helen_def_decorator` | `@open agent Bot { }` | Def: Bot, decorator_tags 含 "@open" |

### 4.3 调用提取验证

**目标**：函数调用、特殊调用（llm act/spawn）被提取为 CALLS 边。

| # | 测试名称 | 输入 | 验证点 |
|---|---|---|---|
| C1 | `helen_call_simple` | `fn f() { g() }\nfn g() { }` | CALLS: f → g |
| C2 | `helen_call_method` | `fn f() { obj.method() }` | CALLS: f → method |
| C3 | `helen_call_llm_act` | `fn f() { llm act "prompt" }` | CALLS: f → llm_act（或特殊标签） |
| C4 | `helen_call_spawn` | `fn f() { spawn Worker("t") }` | CALLS: f → Worker |
| C5 | `helen_call_nested` | `fn f() { g(h()) }` | CALLS: f → g, f → h |
| C6 | `helen_call_in_loop` | `fn f() { for i in list { g(i) } }` | CALLS: f → g, loop_depth > 0 |
| C7 | `helen_call_recursive` | `fn f() { f() }` | is_recursive = true |
| C8 | `helen_call_chained` | `fn f() { a.b().c() }` | CALLS: f → b, f → c |

### 4.4 Import 提取验证

| # | 测试名称 | 输入 | 验证点 |
|---|---|---|---|
| I1 | `helen_import_wildcard` | `import std.core.*` | IMPORTS: → std.core |
| I2 | `helen_import_selective` | `import std.str.{len, upper}` | IMPORTS: → std.str, 含 len/upper |
| I3 | `helen_import_namespace` | `import std.math as M` | IMPORTS: → std.math, alias=M |
| I4 | `helen_import_file` | `import "utils.helen"` | IMPORTS: → utils |

### 4.5 关键字过滤验证

**目标**：Helen 的 99 个双语关键字不被误识别为 Def 或 Variable。

| # | 测试名称 | 输入 | 验证点 |
|---|---|---|---|
| K1 | `helen_keyword_not_def` | 程序中使用 `fn`、`let`、`if` 等 | Def 列表中无关键字 |
| K2 | `helen_chinese_keyword_not_def` | 程序中使用 `函数`、`设`、`如果` 等 | Def 列表中无中文关键字 |
| K3 | `helen_builtin_not_def` | 使用 stdlib 函数名如 `print`、`len` | 不应提取为文件内 Def |
| K4 | `helen_cjk_identifier_is_def` | `let 变量 = 42` | "变量" 被正确识别为 Def |

### 4.6 Language Registry 不变量验证

**目标**：Helen 通过 codebase-memory-mcp 的语言注册表不变量检查。

**方法**：扩展 `tests/repro/repro_language_registry.c` 中的不变量检查。

参考 `repro_language_capability_ledger_covers_every_enum` 的模式：

```c
// 在 LANGUAGE_CAPABILITIES 表中添加 Helen entry
{CBM_LANG_HELEN, "Helen", CAP_CALL_WITHOUT_REFERENCE_VOCAB,
 "Initial support: tree-sitter grammar + def/call/import extraction"},
```

**不变量检查**：
1. Helen 有 CBMLangSpec entry（`cbm_lang_spec(CBM_LANG_HELEN) != NULL`）
2. `spec->language == CBM_LANG_HELEN`
3. `spec->function_node_types != NULL && spec->function_node_types[0] != NULL`
4. `spec->call_node_types != NULL`
5. `cbm_language_name(CBM_LANG_HELEN)` 返回 `"Helen"`
6. `cbm_language_for_extension(".helen")` 返回 `CBM_LANG_HELEN`
7. Capability ledger count 增加 1（更新硬编码的 partition 计数）

### 4.7 自举验证（Self-hosting）

**目标**：用 codebase-memory-mcp 索引 Helen 项目自身代码，验证结果合理性。

**方法**：

```bash
# 1. 用修改后的 codebase-memory-mcp 索引 Helen 项目
cbm index ~/helen/

# 2. 检查基本统计
cbm query "MATCH (n) RETURN labels(n)[0] AS label, count(*) ORDER BY count(*) DESC"
# 预期: Function 节点占多数，Class（agent）节点存在

# 3. 验证关键函数被索引
cbm query "MATCH (n:Function) WHERE n.name = '_shell_exec' RETURN n.file_path"
# 预期: helen/runtime/tools.py

# 4. 验证 .helen 文件被识别
cbm query "MATCH (n) WHERE n.file_path ENDS WITH '.helen' RETURN count(*)"
# 预期: > 0（chat_session_actor.helen 等文件）

# 5. 验证调用图
cbm query "MATCH (a)-[:CALLS]->(b) WHERE a.file_path ENDS WITH '.helen' RETURN count(*)"
# 预期: > 0

# 6. 验证 stdlib 模块提取
cbm query "MATCH (n:Module) WHERE n.name CONTAINS 'stdlib' RETURN count(*)"
# 预期: > 0
```

**量化指标**：

| 指标 | 目标值 | 说明 |
|---|---|---|
| .helen 文件识别率 | 100% | 所有 .helen 文件都被识别为 Helen 语言 |
| 函数定义提取率 | > 95% | 与 `grep "^fn " *.helen` 结果比对 |
| Agent 定义提取率 | 100% | 所有 `agent` 声明都被提取为 Class |
| 调用边准确率 | > 90% | 抽样验证 CALLS 边的 caller/callee 正确性 |
| 关键字误识别数 | 0 | Def 中无关键字 |
| CJK 标识符正确率 | 100% | 中文标识符被正确提取 |
| parse_incomplete 率 | < 5% | 大部分文件 parse 无 ERROR |
| 索引速度 | < 10s | Helen 全项目 ~46k 行 |

### 4.8 回归验证

**目标**：添加 Helen 支持不影响现有语言。

**方法**：

```bash
# 运行 codebase-memory-mcp 全量测试
make -f Makefile.cbm test

# 重点检查：
# 1. 现有语言的测试全部通过（test_py_lsp, test_go_lsp, test_c_lsp, ...）
# 2. repro 不变量测试通过（repro_language_registry）
# 3. 其他语言的索引结果不变（对比 node/edge count）
```

### 4.9 端到端查询验证

**目标**：MCP 工具（search_graph, trace_path, query_graph）能正确查询 Helen 项目。

**方法**：手动验证 + 自动化脚本。

| 查询 | MCP 工具 | 预期结果 |
|---|---|---|
| 搜索函数定义 | `search_graph("shell_exec")` | 找到 `_shell_exec` 定义 |
| 追踪调用者 | `trace_path("interpret", mode="calls", direction="inbound")` | 找到谁调用了 interpret |
| 追踪被调用者 | `trace_path("shell_exec", mode="calls", direction="outbound")` | 找到 shell_exec 调用了什么 |
| 架构概览 | `get_architecture()` | 正确展示 stdlib/interpreter/runtime 层次 |
| Cypher 查询 | `query_graph("MATCH (n:Function) RETURN n LIMIT 5")` | 返回 5 个函数节点 |
| 热点分析 | `query_graph("MATCH (n) WHERE n.in_degree > 10 RETURN n")` | 找到高 fan-in 函数 |

### 4.10 验证执行顺序

```
Phase 0 完成后:
  └── 4.1 Grammar 正确性（G1-G25, N1-N3）—— 确保 parse 无误

Phase 1 完成后:
  └── 4.8 回归验证（现有测试全通过）—— 确保不破坏其他语言

Phase 2 完成后:
  ├── 4.2 定义提取验证（D1-D10）
  ├── 4.3 调用提取验证（C1-C8）
  ├── 4.4 Import 提取验证（I1-I4）
  └── 4.5 关键字过滤验证（K1-K4）

Phase 3 完成后:
  ├── 4.6 Language Registry 不变量
  ├── 4.7 自举验证（索引 Helen 项目自身）
  └── 4.8 全量回归

最终验收:
  └── 4.9 端到端查询验证（MCP 工具可用）
```

---

## 5. 工作量估算

| 阶段 | 内容 | 工期 | 前置依赖 |
|---|---|---|---|
| **Phase 0** | tree-sitter-helen grammar | 2-3 周 | 无 |
| **Phase 1** | enum + wrapper + 注册 | 1-2 天 | Phase 0 |
| **Phase 2** | CBMLangSpec 节点映射 | 2-3 天 | Phase 1 |
| **Phase 3** | 提取器定制 + 关键字 | 3-5 天 | Phase 2 |
| **Phase 4** | LSP 集成（可选） | 1-2 周 | Phase 3 |
| **总计** | | **4-7 周** | |

### 关键路径

```
tree-sitter-helen (Phase 0, 2-3 周)
       ↓
   Phase 1 (1-2 天)
       ↓
   Phase 2 (2-3 天)
       ↓
   Phase 3 (3-5 天)
       ↓
   Phase 4 (可选, 1-2 周)
```

Phase 0 是关键路径上的瓶颈。Grammar 质量直接决定后续所有阶段的精度。

---

## 6. 风险与缓解

| 风险 | 影响 | 概率 | 缓解 |
|---|---|---|---|
| tree-sitter-helen 编写周期超预期 | Phase 0 延期 | 中 | 先用简化 grammar（只覆盖核心语法），迭代扩展 |
| 双语关键字导致 grammar 冲突 | parse error | 中 | 在 keywords 列表中英文和中文分别注册 |
| CJK 标识符与关键字歧义 | 误 parse | 低 | Unicode property escape 精确匹配 |
| `fn` 双重语义（声明 vs lambda） | parse 错误 | 中 | 使用 tree-sitter 的 GLR 模式或 context-dependent 规则 |
| codebase-memory-mcp 上游更新 | 合并冲突 | 低 | 遵循现有语言添加模式，最小化修改面 |
| `shared store`/`llm act` 等多词关键字 | grammar 复杂度 | 中 | 用 `seq()` 组合，测试覆盖 |

---

## 7. 替代方案

### 7.1 纯正则 Fallback（快速原型）

如果 tree-sitter grammar 周期不可接受，可以先用 codebase-memory-mcp 的正则 fallback 提取：

- 函数定义：`fn\s+(\w+)\s*\(`
- Agent 定义：`agent\s+(\w+)`
- 调用：`(\w+)\s*\(`
- Import：`import\s+`

**优点**：1-2 天出效果
**缺点**：无法处理嵌套、字符串内匹配、CJK 边界

### 7.2 基于 Python Grammar 映射

Helen 语法与 Python 有相似性。可以尝试：
- fork tree-sitter-python
- 修改语法规则适配 Helen
- 复用已有的 node type 映射

**优点**：减少 grammar 编写量
**缺点**：语义差异导致映射不精确，维护成本高

---

## 8. 验收标准

### 8.1 硬性门禁（必须全部通过）

| # | 验收项 | 判定方法 | 通过条件 |
|---|---|---|---|
| A1 | Grammar parse 无 ERROR | 4.1 中 G1-G22 全部通过 | 25 个语法测试 100% 通过 |
| A2 | 现有语言不回归 | `make -f Makefile.cbm test` | 所有现有测试通过 |
| A3 | Language Registry 不变量 | 4.6 repro 测试 | `repro_language_registry` suite 全通过 |
| A4 | 关键字零误识别 | 4.5 K1-K4 | Def 中无关键字 |
| A5 | CJK 标识符正确 | 4.1 G18 + 4.2 D9 | 中文标识符正确解析和提取 |
| A6 | `.helen` 文件识别 | `cbm_language_for_extension(".helen")` | 返回 `CBM_LANG_HELEN` |

### 8.2 质量指标（自举验证）

对 Helen 项目自身代码（~/helen/）索引后：

| 指标 | 目标值 | 测量方法 |
|---|---|---|
| .helen 文件识别率 | 100% | `find . -name "*.helen"` count vs 索引中 .helen 文件 count |
| 函数定义提取率 | > 95% | 提取的 Function Def count / `grep -r "^fn " *.helen` count |
| Agent 定义提取率 | 100% | 提取的 Class(agent) count / `grep -r "^agent " *.helen` count |
| 调用边准确率 | > 90% | 随机抽样 50 条 CALLS 边，人工验证 caller/callee |
| parse_incomplete 率 | < 5% | `parse_incomplete=true` 的文件 / 总 .helen 文件 |
| 索引速度 | < 10s | `time cbm index ~/helen/` |

### 8.3 端到端可用性

| 验证项 | 方法 | 通过条件 |
|---|---|---|
| search_graph 能找到 Helen 函数 | `search_graph("shell_exec")` | 返回 helen/runtime/tools.py 中的定义 |
| trace_path 能追踪调用 | `trace_path("interpret", direction="inbound")` | 返回 caller 列表 |
| query_graph 能查询 | `MATCH (n:Function) RETURN count(*)` | 返回 > 0 |
| get_architecture 正常 | `get_architecture()` | 展示 stdlib/interpreter/runtime 层次 |

---

## 9. 下一步行动

1. **立即可做**：创建 `scripts/new-languages.json` 的 Helen entry，确认构建管线
2. **Phase 0 启动**：开始 tree-sitter-helen grammar 编写
   - 参考 `tree-sitter-python` 和 `tree-sitter-rust`
   - 从 Helen 的 58 个 AST 节点类型出发定义 grammar rules
   - 先覆盖核心语法（fn/let/if/for/import/agent），再扩展
3. **Phase 1-3**：在 grammar 可用后快速推进（1-2 周）

---

*文档作者: Claude | 审阅状态: 待审阅*
