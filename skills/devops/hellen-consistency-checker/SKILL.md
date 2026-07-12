---
name: hellen-consistency-checker
trigger: "When checking or fixing Hellen language design document consistency"
description: >
  Systematic, section-by-section consistency checker for Hellen detailed design documents.
  Reads documents front-to-back, validates each section against all preceding ones, and applies fixes.
metadata:
  hermes:
    tags: [helen, consistency, documentation, hld, design-docs, verification]
---

# Hellen 一致性检查器

## 核心原则

**HLD 是唯一真相源（Single Source of Truth）**。所有详细设计文档必须与概要设计 v1.2.1 一致。

**文档优先级**：HLD > Phase 0（AST 定义）> P1 Parser > P2-3 > Remaining

**修改策略**：当两个文档不一致时，以优先级高的为准，修改优先级低的文档。

## 文档清单与阅读顺序

```
1. ~/documents/Hellen_High_Level_Design_v1.2.md       → 提取基准规范
2. ~/hellen/docs/phase0-design.md                     → 对照 HLD 检查
3. ~/hellen/docs/hellen-detailed-design-p1-parser.md  → 对照 HLD + Phase 0 检查
4. ~/hellen/docs/hellen-detailed-design-p2-p3.md      → 对照 HLD + Phase 0 + P1 检查
5. ~/hellen/docs/hellen-detailed-design-remaining.md  → 对照所有前序文档检查
```

## 执行流程

### Phase A：提取基准规范（从 HLD）

从 HLD 中提取以下基准信息，写入临时文件 `/tmp/hellen_baseline.json`：

```python
# 提取以下维度：
baseline = {
    "keywords": {  # 27 个关键字及分类
        "list": ["agent", "description", "model", ...],
        "count": 27,
        "contextual": ["llm"],  # 上下文关键字
        "hyphenated": ["sub-agents", "max-turns"],
    },
    "ast_nodes": {  # 每个节点的关键字段
        "VarDeclNode": {"fields": ["name", "mutable", "type_annotation", "initializer", "span"]},
        "BinaryOpNode": {"fields": ["left", "operator", "right", "span"]},
        "UnaryOpNode": {"fields": ["operator", "right", "span"]},
        "LlmIfStmtNode": {"fields": ["description", "branches", "span"]},
        "LlmActStmtNode": {"fields": ["has_await", "span"]},
        "TryStmtNode": {"fields": ["try_body", "catch_clauses", "catch_all", "finally_body", "span"]},
        "CatchClauseNode": {"fields": ["exception_type", "var_name", "body", "span"]},
        "AsyncCallStmtNode": {"fields": ["agent_name", "arguments", "span"]},
        "ForStmtNode": {"fields": ["iterator", "iterable", "body", "span"]},
        "AgentDeclNode": {"fields": ["name", "params", "declarations", "prompt", "logic", "span"]},
        "ImportStmtNode": {"fields": ["path", "alias", "span"]},
        # ... 提取 HLD 3.4.2 中所有节点
    },
    "error_codes": {  # 完整错误码表
        100: "LEXICAL_INVALID_CHAR",
        200: "SYNTAX_ERROR",
        211: "LLM_IF_NO_DEFAULT",
        300: "SEMANTIC_UNDECLARED_VAR",
        # ... 提取 HLD + Remaining 中的完整映射
    },
    "source_span": {
        "module": "hellen.core.source",
        "file": "source.py",
    },
    "naming_conventions": {
        "visitor_methods": "snake_case (visit_llm_if_stmt)",
        "ast_suffix": "Node (IfStmtNode, not IfStmt)",
        "span_field": "span (not source)",
        "operator_field": "operator (not op)",
    },
    "scanner_api": {
        "method": "scan_all()",
    },
    "token_fields": {
        "col": "col (not column)",
        "end_col": "end_col (not end_column)",
    },
}
```

### Phase B：逐文档检查与修复

对每个文档（按顺序），执行以下检查循环：

#### B1. Phase 0 (`phase0-design.md`)

**按文档内顺序，逐 section 检查：**

| Section | 检查项 | 修复规则 |
|---------|--------|----------|
| 1.1 TokenType | 27 个关键字完整？连字符关键字正确？ | 与 HLD 9.1 对比 |
| 1.2 Token | 字段名 col/end_col 正确？ | 修正 column→col |
| 1.3 SourceSpan | 是否在 source.py 中？tokens.py 是否正确导入？ | 统一为 from .source import |
| 1.4 Lexer (Scanner) | scan_all() 方法名正确？ | 统一方法名 |
| 2. AST 节点 | 所有节点字段与 baseline 一致？无重复定义？ | 对齐字段名，删除重复 |
| 3. errors.py | 错误码 100-314 与 baseline 一致？ | 对齐编号和名称 |
| 4. ASTPrinter | 无重复 visit 方法？节点类型引用正确？ | 删除重复，修正类型 |

**检查命令模式**：
```bash
# 重复定义检查
grep -n "def visit_\w\+(" file | sort | uniq -d

# 字段名检查
grep -n '\.source\b\|\.op\b\|\.column\b\|scanner\.scan()' file

# 错误码一致性
grep -n "ERR_\d\+\s*=" file
```

#### B2. P1 Parser (`hellen-detailed-design-p1-parser.md`)

**按文档内顺序，逐 section 检查：**

| Section | 检查项 | 修复规则 |
|---------|--------|----------|
| Parser 类定义 | import 路径正确？导入 SourceSpan 从 source.py？ | 修正导入 |
| Pratt 规则 | 优先级与 HLD 3.3.2 一致？ | 对比 HLD 操作符优先级表 |
| 声明解析 | 创建的 AST 节点字段名与 Phase 0 一致？ | 对齐：var_type→type_annotation, init→initializer |
| 语句解析 | try/catch/llm/async 创建的节点字段一致？ | 对齐：source→span, op→operator, catches→catch_clauses |
| 表达式解析 | BinaryOpNode/UnaryOpNode 字段一致？ | 对齐：op→operator, source→span |
| 错误处理 | ErrorCode 引用与 baseline 一致？ | 对齐错误码常量名 |
| 测试用例 | scanner.scan() → scan_all()？ | 统一方法名 |
| Token 访问 | token.column → token.col？ | 统一字段名 |

#### B3. P2-3 (`hellen-detailed-design-p2-p3.md`)

**按文档内顺序，逐 section 检查：**

| Section | 检查项 | 修复规则 |
|---------|--------|----------|
| 类型系统 | 类型层次与 HLD 3.10.2 一致？ | 对比 HLD 类型树 |
| Symbol/SymbolTable | 作用域类型与 HLD 3.5.2 一致？ | 对比 HLD 作用域层级 |
| 错误码常量 | 300-314 与 baseline 一致？ | 对齐编号 |
| SemanticAnalyzer | 字段访问与 Phase 0 定义一致？ | node.initializer (非 node.value) |
| visit_llm_if_stmt | 语义正确（LLM 路由，非普通 if）？ | 访问 description + branches |
| visit_llm_act_stmt | 结构正确（has_await，非 target/arguments）？ | 移除错误字段访问 |
| visit_async_call_stmt | 使用 agent_name + arguments？ | 不使用 node.body |
| Environment | const 保护逻辑正确？ | 对比 HLD |
| Interpreter | visit_* 方法字段访问与 Phase 0 一致？ | 全面对齐 |
| 异常层次 | 与 HLD 3.6.4 一致？ | 对比异常继承树 |
| 错误码表 | 与 baseline 一致？ | 对齐完整表 |

#### B4. Remaining (`hellen-detailed-design-remaining.md`)

| Section | 检查项 | 修复规则 |
|---------|--------|----------|
| 目录结构 | 与 HLD 2.1 三层架构一致？ | 对比架构图 |
| Import Resolver | 支持的文件格式与 HLD 3.9.1 一致？ | 对比解析策略表 |
| Type Checker | 模式与 HLD 3.10.1 一致？ | 对比渐进式类型表 |
| CLI | 子命令与 HLD Phase 6 一致？ | 对比实施计划 |
| 错误码表 | 完整表与 baseline 一致？ | 对齐所有编号 |
| 测试框架 | 测试目录与 HLD 6.2 一致？ | 对比测试设计 |
| LSP/VSCode | 关键字列表与 HLD 9.1 一致？ | 对比完整关键字表 |

### Phase D：单文档内部一致性检查

> **关键发现**：跨文档一致只是第一步。单份文档内部也存在大量前后不一致，必须逐文档自检。

对每份文档，执行以下内部一致性检查：

#### D1. 定义与使用一致

| 检查项 | 方法 | 实战案例 |
|--------|------|---------|
| 拼写错误 | grep 枚举成员名，检查是否有双写（如 `NULL_KW_KW`） | Phase 0: `NULL_KW_KW` → `NULL_KW` |
| 类名唯一性 | `grep "class \w+Node"` 检查重复定义 | Phase 0: PromptDefNode 定义了 2 次 |
| 类名引用一致 | grep 测试/代码中的类名，确认与定义一致 | Phase 0: 测试导入 `IfStmt` 但类是 `IfStmtNode` |
| 枚举引用存在 | 提取所有 `TokenType.X` / `ErrorCode.X` 引用，对比枚举定义 | Phase 0: `ASSIGN_EQUAL`、`AND_AMPERSAND` 未定义 |

#### D2. 测试用例与代码一致

| 检查项 | 方法 | 实战案例 |
|--------|------|---------|
| 构造函数参数完整 | 对比 dataclass 字段 vs 测试用例中的参数 | Phase 0: test_let/test_const 缺 `mutable` 参数 |
| 方法签名匹配 | 对比方法定义 vs 调用处的参数名 | Remaining: CLI 用 `environment=env` 但 Interpreter 定义是 `env` |
| 返回值类型一致 | 同一类方法返回类型应一致 | P2-3: visit_llm_if_stmt 返回 ANY，visit_llm_act_stmt 返回 LLMResponse |

#### D3. 接口与实现一致

| 检查项 | 方法 | 实战案例 |
|--------|------|---------|
| 抽象方法全覆盖 | 提取 ABC 的 @abstractmethod，检查所有子类是否实现 | P2-3: InMemoryProvider/FileMemoryProvider 缺 search |
| 接口参数名匹配 | 抽象方法参数名 vs 实现方法参数名 | P2-3: MemoryProvider 的 search 参数与 HLD 对齐 |
| 异常命名冲突 | 检查自定义异常是否与 Python 内置冲突 | P2-3: `class RuntimeError` 冲突 → `HellenRuntimeError` |

#### D4. 逻辑 Bug 检查

| 检查项 | 方法 | 实战案例 |
|--------|------|---------|
| None 初始化 + 方法调用 | grep `= None` 后紧跟 `.append()` / `.extend()` 的代码 | P1: `else_body: Optional[...] = None` 后调用 `else_body.append()` |
| 缺失必需字段 | 对比 dataclass 必需字段 vs 创建代码是否全部传递 | P1: LlmActStmtNode 缺 `has_await` 字段 |
| 错误码引用存在 | 提取所有 `ErrorCode.XXX` 引用，对比枚举定义 | Remaining: `IMPORT_CYCLE`、`TYPE_MISMATCH` 未定义 |

#### D5. 命名规范内部一致

| 检查项 | 方法 | 实战案例 |
|--------|------|---------|
| 字段名统一 | 同类功能在不同模块中使用相同字段名 | Remaining: HellenError 用 `source` vs Phase 0 用 `span` → 统一为 `span` |
| Symbol 字段 | Symbol 的字段名与 Token 字段名对齐 | P2-3: Symbol 用 `column` vs Token 用 `col` → 统一为 `col` |

### Phase B+1：代码-vs-设计一致性检查（Code-to-Design Compliance）

设计文档与代码之间的一致性与设计文档之间的一致性同等重要。当设计文档已更新后，**必须**重新检查代码是否符合设计。

**核心原则**：HLD 是真相源，但**代码往往比旧设计更精确**。详见 Pattern 37（分类优先策略）。

**执行流程**：
1. **提取代码结构**：用 `execute_code` + `ast` 模块或正则提取代码中的 TokenType、AST 节点字段、Visitor 方法
2. **与设计逐节点对比**：方法级提取（get_dataclass_fields），非文档级 grep
3. **分类不一致项**：fix code / fix design / accept as improvement（见 Pattern 37）
4. **批量修复**：根据分类结果修复代码或设计
5. **运行测试**：每次代码修改后运行 `pytest` 确认无回归
6. **迭代验证**：至少 5 轮直到完全对齐

**检查维度**：
- TokenType 枚举集合及关键字映射
- AST 节点字段名和类型
- Visitor 抽象方法列表
- 缺失的 API 方法（如 scan_one）
- 导入路径正确性

**验证脚本模式**：
```python
def get_dataclass_fields(text, class_name):
    \"\"\"Precisely extract dataclass fields from a code block.\"\"\"
    pattern = rf'@dataclass\([^)]*\)\nclass {class_name}\([^)]*\):[^\n]*\n(.*?)(?=\n    def |\n\n@dataclass|\n@dataclass|\nclass |\Z)'
    match = re.search(pattern, text, re.DOTALL)
    if match:
        body = match.group(1)
        fields = {}
        for line in body.split('\n'):
            line = line.strip()
            if line and ':' in line and not line.startswith('def ') and not line.startswith('#'):
                parts = line.split(':', 1)
                if len(parts) == 2:
                    name = parts[0].strip()
                    if re.match(r'^[a-z_]\w*$', name):
                        fields[name] = parts[1].strip().rstrip(',')
        return fields
    return {}
```

详见 `references/code-to-design-compliance.md`。

### Phase C：交叉验证

完成所有文档的逐 section 检查后，执行以下交叉验证：

1. **AST 节点字段矩阵**：提取每个文档中所有 AST 节点的字段名，构建对比矩阵，确保一致
2. **错误码编号矩阵**：提取 100-506 全部错误码，确保三文档（Phase 0 / P2-3 / Remaining）完全一致
3. **Visitor 方法列表**：确保所有文档的 visit_* 方法名都是 snake_case
4. **导入路径检查**：确保 SourceSpan 全部从 source.py 导入
5. **方法名检查**：确保 Scanner 统一使用 scan_all()

### 修复命令模板

```bash
# 全局替换示例（根据具体不一致项调整）

# AST 字段名对齐
sed -i 's/node\.value\b/node.initializer/g' file.md
sed -i 's/node\.then_body/node.then_branch/g' file.md
sed -i 's/node\.else_body/node.else_branch/g' file.md
sed -i 's/node\.body/node.try_body/g' file.md          # 仅在 TryStmtNode 上下文中
sed -i 's/node\.catches/node.catch_clauses/g' file.md
sed -i 's/node\.finally_block/node.finally_body/g' file.md
sed -i 's/node\.op\b/node.operator/g' file.md
sed -i 's/\.source=self\./\.span=self./g' file.md

# Token 字段名对齐
sed -i 's/token\.column/token.col/g' file.md
sed -i 's/token\.end_column/token.end_col/g' file.md

# Scanner 方法名
sed -i 's/scanner\.scan()/scanner.scan_all()/g' file.md

# 导入路径
sed -i 's/from \.tokens import.*SourceSpan/from .source import SourceSpan/g' file.md
```

### 注意事项

1. **不要过度修改**：只改真正不一致的部分。不同文档可以有合理的差异（如语义分析器有自己的错误处理逻辑）。
2. **保持文档可读性**：修改后确保代码块仍然是合法的 Python/Markdown。
3. **每次修改后验证**：使用 grep 确认修改效果，确认没有引入新的不一致。
4. **记录修改**：在 CONSISTENCY_REPORT.md 中记录每次修复。
5. **区分设计差异与不一致**：如果两个文档的差异是合理的设计选择（如语义分析器比 Parser 多做了类型推断），不要强行统一。

---

## 常见不一致模式（实战经验）

> 以下是实际检查中发现的高频不一致模式，按严重程度排列。

### 🔴 模式 1：AST 字段名漂移（最常见，占比 ~40%）

不同文档对同一 AST 节点字段使用不同名称。高频漂移对：

| HLD / Phase 0 正确名 | 错误变体 | 出现在 |
|----------------------|----------|--------|
| `node.initializer` (VarDeclNode) | `node.init`, `node.value` | P2-3 Analyzer/Interpreter, Remaining |
| `node.value` (LiteralNode, ReturnStmtNode) | `node.initializer` | P2-3 Analyzer/Interpreter |
| `node.operator` (BinaryOpNode, UnaryOpNode) | `node.op` | P2-3 Analyzer, Remaining TypeChecker |
| `node.target` (IndexNode, MatchStmtNode) | `node.container`, `node.expression` | P2-3 Analyzer/Interpreter, P1 Parser |
| `node.right` (UnaryOpNode) | `node.expression` | P2-3 Analyzer/Interpreter |
| `node.then_branch` (IfStmtNode) | `node.then_body` | P1 Parser |
| `node.else_branch` (IfStmtNode) | `node.else_body` | P1 Parser |
| `node.iterator` (ForStmtNode) | `node.var_name` | P1 Parser |
| `node.arguments` (AsyncCallStmtNode) | `node.args` | P1 Parser |
| `node.elements` (ListLiteralNode) | `node.items` | Remaining TypeChecker |
| `node.right` (UnaryOpNode) | `node.expression` | P2-3 Analyzer/Interpreter |
| `node.statements` (ProgramNode) | `node.body` | P2-3 Analyzer/Interpreter |
| `Token.col` | `Token.column` | P1 Parser `_span_from_to` |
| `Token.end_col` | `Token.end_column` | P1 Parser `_span_from_to` |
| `node.branches` (LlmIfStmtNode) | `node.then_branch`, `node.else_branch` | P2-3 Analyzer |

**检查方法**：对每个 AST 节点，在 Phase 0 确认字段名后，grep 所有下游文档中的 `node.<字段名>` 访问。

### 🔴 模式 2：body 字段类型错位（单节点 vs 列表）

Phase 0 定义某些节点的 `body` 为单节点（`MainBlockNode | Stmt`），但 P2-3 的 visitor 中将其作为 `list[Stmt]` 遍历：

```python
# ❌ 错误：Phase 0 定义 body 是单节点
for stmt in node.body:        # 会遍历 MainBlockNode 的 __dict__ 而非语句列表
    self.visit(stmt)

# ✅ 正确：通过 visit 分发
self.visit(node.body)
```

**受影响节点**：`IfStmtNode.then_branch`, `IfStmtNode.else_branch`, `ForStmtNode.body`, `WhileStmtNode.body`, `TryStmtNode.finally_body`。

**检查方法**：grep `for stmt in node\.` 并对比 Phase 0 中对应字段的类型定义。

### 🔴 模式 3：SourceSpan 遗漏

HLD 3.4.1 明确所有 AST 节点携带 `source: SourceSpan`。以下节点在 Phase 0 中缺少 `span` 字段：
- `CatchClauseNode`（有 exception_type, var_name, body，缺 span）
- `CatchAllNode`（有 body，缺 span）
- `FinallyBlockNode`（有 body，缺 span）

**检查方法**：提取 Phase 0 中所有 `@dataclass` 节点类，检查每个类是否包含 `span: SourceSpan` 字段。

### 🟡 模式 4：PromptDefNode 重复定义

Phase 0 文档中 `PromptDefNode` 在第 1546 行和第 1685 行各定义了一次。检查时 grep `class PromptDefNode` 确认唯一性。

### 🟡 模式 7：Token 字段名在辅助方法中漂移

Parser 文档的 `_span_from_to` 等辅助方法中使用了 `token.column` / `token.end_column`，但 Phase 0 Token 定义字段为 `col` / `end_col`。

**检查方法**：grep `\.column\b` 和 `\.end_column\b` 在 Parser 文档中出现的位置。

### 🟡 模式 8：LlmIfStmtNode 字段结构漂移

Phase 0 定义：`LlmIfStmtNode(description: str, branches: list[LlmBranchNode], span)` — 分支名列表 + 分支体。
HLD EBNF：`Branch → "branch" IDENTIFIER block` — 分支名 + 执行体。

P2-3 Analyzer 错误假设了 if-else 结构：`node.then_branch`、`node.else_branch`（当成普通 if 语句）。

**检查方法**：grep `node\.then_branch` 和 `node\.else_branch` 在 P2-3 中对 LlmIfStmtNode 的访问。

### 🟡 模式 9：visit_program 使用 node.body 而非 node.statements

Phase 0 和 P1 Parser 中 `ProgramNode` 使用 `statements: list[ASTNode]`，但 P2-3 的 visitor 中使用 `node.body`。

**检查方法**：grep `node\.body` 在 visit_program 方法中的使用。

### 🔴 模式 10：None 初始化后立即调用方法（逻辑 Bug）

变量初始化为 `None` 但后续直接调用列表方法：

```python
# ❌ Bug：else_body 初始化为 None，然后调用 .append()
else_body: Optional[list[StatementNode]] = None
if self._match(TokenType.ELSE):
    else_body.append(self._statement())  # AttributeError: NoneType has no append

# ✅ 修复：初始化为空列表，最后判断
else_body: list[StatementNode] = []
if self._match(TokenType.ELSE):
    else_body.append(self._statement())
# ... 创建节点时
else_branch=else_body if else_body else None,
```

**检查方法**：grep `= None` 后紧跟 `\.append\(` / `\.extend\(` 的代码块。

### 🔴 模式 11：Python 内置类名冲突

自定义异常/类与 Python 内置类同名：

```python
# ❌ 冲突：RuntimeError 是 Python 内置异常
class RuntimeError(AnyError):
    ERR_CODE = 400

# ✅ 修复：加前缀避免冲突
class HellenRuntimeError(AnyError):
    ERR_CODE = 400
```

**检查方法**：grep `class (RuntimeError|TypeError|ValueError|Exception|AttributeError|IndexError)\b` 在文档中出现的位置。

### 🔴 模式 12：ErrorCode 枚举引用未定义

代码/测试中引用了枚举中不存在的成员：

```python
# ❌ ErrorCode 中没有 SYNTAX_ERROR
self.error_reporter.report(ErrorCode.SYNTAX_ERROR, ...)

# ✅ 使用已定义的成员
self.error_reporter.report(ErrorCode.ERR_200, ...)  # 或使用符号名
```

**常见缺失 ErrorCode**：
- ImportResolver 引用的 `IMPORT_CYCLE`、`IMPORT_UNSUPPORTED`、`IMPORT_PATH_TRAVERSAL`
- TypeChecker 引用的 `TYPE_MISMATCH`、`RETURN_TYPE_MISMATCH`（应使用 `SEMANTIC_TYPE_MISMATCH`）

**检查方法**：提取所有 `ErrorCode\.\w+` 引用，与 `class ErrorCode` 中定义的成员对比。

### 🟡 模式 13：CLI/REPL 构造函数参数不匹配

CLI 调用构造函数时使用错误的参数名或额外参数：

```python
# ❌ CLI 调用
interpreter = Interpreter(
    environment=env,           # 定义中是 env
    project_root=Path(...),    # 定义中不接受此参数
    error_reporter=reporter,   # 定义中不接受此参数
)

# ✅ 正确调用
interpreter = Interpreter(runtime=runtime, env=env)
```

**检查方法**：提取 CLI/REPL 中所有类实例化代码，对比类 `__init__` 的签名。

### 🟡 模式 14：测试导入错误/重复

测试代码的 import 语句中有错误类名或重复导入：

```python
# ❌ 错误类名 + 重复导入
from hellen.core.ast import (
    VarDeclNode, VarDeclNode, IfStmt, ForStmtNode,  # IfStmt 应为 IfStmtNode
    ...
)

# ✅ 正确
from hellen.core.ast import (
    VarDeclNode, IfStmtNode, ForStmtNode, ...
)
```

**检查方法**：grep `from.*import` 后检查每个导入名是否在源文件中定义。

### 🟡 模式 15：HellenError 字段名与 Phase 0 不一致

Remaining 文档中 `HellenError` 使用 `source` 字段，但 Phase 0 使用 `span`：

```python
# ❌ Remaining
@dataclass
class HellenError:
    source: Optional[SourceSpan] = None

# ✅ 统一为 span
@dataclass
class HellenError:
    span: Optional[SourceSpan] = None
```

连带影响：`ErrorReporter.report()`、`format_error()`、LSP `_diagnostics()` 中所有 `source` → `span`。

**检查方法**：grep `error\.source\.` 和 `self\.source` 在 HellenError/HellenWarning/ErrorReporter 上下文中。

### 🟡 模式 16：FunctionDeclNode 参数类型统一为 AgentParamNode

P1 Parser 中 `FunctionDeclNode` 的 `params` 使用 `AgentParamNode`（含 name、type_annotation、default_value 三字段），与 Agent 参数共享同一类型。`body` 字段为 `FnBlockNode`（含 `body: list[StatementNode]`）。

**Phase 1 已确认此设计**：函数和 Agent 参数共享 `AgentParamNode`，276 测试全部通过。

**检查方法**：确认 `FunctionDeclNode.params` 为 `list[AgentParamNode]`，`FunctionDeclNode.body` 为 `FnBlockNode`。

### 🔴 模式 17：跨文档 AST 节点字段类型冲突

不同文档对同一 AST 节点的同一字段定义了**不兼容的类型**，这是最隐蔽的 P0 级不一致：

| 节点.字段 | Phase 0 定义 | P1 Parser 传入 | 后果 |
|-----------|-------------|---------------|------|
| `FunctionDeclNode.body` | `MainBlockNode` | `list[StatementNode]` | Parser 产出 AST 与 AST 定义类型不匹配 |
| `MapLiteralNode.entries` | `list[tuple[Expr, Expr]]` | `list[MapEntryNode]` | Parser 传入 MapEntryNode 列表，但 AST 定义期望 tuple 列表 |

**检查方法**：对每个 AST 节点，提取 Phase 0 的字段类型定义，然后 grep P1 Parser 中该节点的创建代码，对比传入值的类型。

### 🔴 模式 18：Token 对象与字符串/字典的直接操作（Interpreter 逻辑 Bug）

Phase 0 定义 `BinaryOpNode.operator` 和 `UnaryOpNode.operator` 为 `Token` 类型，但 P2-3 Interpreter 中直接将 Token 对象与字符串比较或用作字典 key：

```python
# ❌ op 是 Token 对象，与字符串比较永远为 False；用作字典 key 会 KeyError
op = node.operator
if op == '!': return not operand     # Token('!') != '!'
ops = {"+": ..., "-": ...}
return ops[op](left, right)          # Token('+') 不在 ops 中

# ✅ 正确：通过 .lexeme 获取字符串
op = node.operator.lexeme
if op == '!': return not operand
return ops[op](left, right)
```

**检查方法**：grep `node\.operator` 在 P2-3 文档中的使用，确认是否都通过 `.lexeme` 或 `.type` 访问。

### 🔴 模式 19：CatchClauseNode.exception_type 类型不匹配

Phase 0 定义 `exception_type: Token|None`，但 P2-3 Interpreter 的 `_exception_matches` 方法期望接收字符串，直接传入 Token 对象导致查找永远返回默认值。

**检查方法**：grep `exception_type` 在 P2-3 Interpreter 中的使用，确认是否正确转换为字符串（`.lexeme`）。

### 🔴 模式 20：CatchAllNode 无 var_name 但 Interpreter 访问

Phase 0 `CatchAllNode` 只有 `body` 和 `span` 字段（无 `var_name`），但 P2-3 Interpreter 尝试访问 `catch_all_clause.var_name`，运行时会抛 `AttributeError`。

**检查方法**：grep `catch_all.*var_name` 在 P2-3 文档中的使用。

### 🟡 模式 21：三套完全不同的 ErrorCode 枚举定义

Phase0、Remaining、P2-3 Analyzer 各自定义了不同的 ErrorCode：

| 文档 | 风格 | 示例 |
|------|------|------|
| Phase0 | 数值元组 | `ERR_100 = ("E100", "UnexpectedCharacter", "...")` |
| Remaining | 描述性 auto() | `LEXICAL_INVALID_CHAR = auto()` |
| P2-3 Analyzer | 整数常量 | `ERR_UNDEFINED_VARIABLE = 300` |

**修正建议**：统一为 Remaining 的描述性名称风格，Phase0 重写 ErrorCode，P2-3 改为枚举引用。

**检查方法**：分别 grep `class ErrorCode` 和独立 `ERR_\w+\s*=` 在各文档中的定义，对比成员列表。

### 🟡 模式 22：两套不同的 HellenError 数据类

Phase0: `HellenError(code, message, span, hint)` vs Remaining: `HellenError(code, message, span|None, level, detail)`。

**修正建议**：统一为 Remaining 版本（更丰富），更新 Phase0。

### 🟡 模式 23：CLI cmd_run 中 runtime 变量未定义

`cmd_run` 第 952 行使用 `Interpreter(runtime=runtime, env=env)` 但 `runtime` 变量从未创建。

### 🟡 模式 24：P1 _for_stmt 中 name_token 变量未定义

`_for_stmt` 第 821 行 `iterator=name_token` 但该变量在方法中未定义（只有 `var_name` 字符串）。

## 自动化交叉验证工作流

对于大规模多文档修复（20+ 处不一致），使用 `execute_code` + 正则的自动化验证流程：

```python
# 1. 读取所有文档
with open(hld_path) as f: hld = f.read()
with open(phase0_path) as f: phase0 = f.read()
# ... 读取所有文档

# 2. 逐项检查（使用 regex 匹配精确上下文）
# AST 字段检查
if re.search(r'node\.initializer\b', analyzer_literal_section):
    issues.append("P2-3 Analyzer: visit_literal still uses node.initializer")

# 重复类定义检查
if phase0.count("class PromptDefNode") != 1:
    issues.append("Phase 0: PromptDefNode appears N times")

# Token 字段检查
if "start.column" in p1:
    issues.append("P1 Parser: _span_from_to still uses 'start.column'")

# 3. 报告结果
if issues:
    print(f"❌ Found {len(issues)} remaining issues")
else:
    print("✅ ALL CHECKS PASSED")
```

**关键原则**：
- 使用 `\b` 边界避免误匹配（如 `node.init\b` 不会匹配 `node.initializer`）
- 检查时分隔文档区域（用 split 定位到具体方法/类）
- 最后统一运行所有检查，而非逐条修复后立即验证

### Pattern 33：类/方法完整性检查（Missing Class/Method Detection）

概要设计和详细设计之间存在"引用但不存在"的隐性不一致：

| 类型 | 案例 | 检测方法 |
|------|------|---------|
| Visitor 接口引用了但类不存在 | `Visitor.visit_program` 引用 `ProgramNode`，但 Phase 0 中没有 `class ProgramNode` | `get_class_body(doc, 'ProgramNode')` 返回空 |
| TypeChecker 缺少 visit 方法 | Remaining 只有 11 个 `visit_*`，缺少 `visit_try_stmt`/`visit_match_stmt`/`visit_llm_*` 等 12 个 | 提取 Visitor ABC 的全部抽象方法，对比下游文档的实现 |
| 重复方法定义 | P2-3 中 `def visit_var_decl` 出现 3 次（1 个不完整的残桩紧挨着完整实现） | `doc.count('def visit_var_decl') > 2` |

**检查方法**：
```python
# 1. 检查所有引用的类是否存在
for cls in ['ProgramNode', 'LlmBranchNode', 'MatchArm']:
    if not get_class_body(phase0, cls):
        issues.append(f"Phase0: {cls} referenced but not defined")

# 2. 检查 Visitor 覆盖率
visitor_methods = set(re.findall(r'def (visit_\w+)', visitor_section))
impl_methods = set(re.findall(r'def (visit_\w+)', analyzer_section))
missing = visitor_methods - impl_methods
if missing:
    issues.append(f"Missing visitor implementations: {missing}")

# 3. 检查重复定义
for method in visitor_methods:
    count = doc.count(f'def {method}')
    if count > 2:  # 允许 1 sync + 1 async
        issues.append(f"Duplicate definition: {method} ({count} times)")
```

### Pattern 34：方法级验证优于文档级 Grep（参见 references/method-level-verification-pattern.md）

文档级 grep（`"node.initializer" in doc`）产生**假阳性**：
- `visit_var_decl` 正确使用 `node.initializer` 掩盖了 `visit_return_stmt` 的错误使用 `node.value`
- `visit_llm_if_stmt` 完全使用了错误的 AST 结构（当成 `IfStmtNode` 而非 `LlmIfStmtNode`），但文档级 grep 完全无法发现

**必须使用方法级提取**：
```python
# ❌ 文档级 grep — 假阳性
assert "node.initializer" in p23  # 通过，但 visit_llm_if_stmt 仍用 then_branch

# ✅ 方法级检查 — 精确到每个方法
body = get_method_body(p23, 'visit_llm_if_stmt')
assert "node.branches" in body  # 发现结构性错误
assert "node.then_branch" not in body  # 确认无错误字段
```

完整的验证函数和边界检测规则见 `references/method-level-verification-pattern.md`。

## Iterative Convergence Workflow (MANDATORY)

> **用户要求**：每次检查修正后要再次检查并修正，直到详细设计完全符合概要设计或是合理的详细设计。

This is NOT a single-pass process. Follow this convergence loop:

```
Round 1: Run all checks → collect issues → batch fix all issues
Round 2: Re-run ALL checks → verify fixes → collect remaining issues
Round 3: Fix remaining issues → re-run ALL checks
... repeat until 0 issues ...
```

**Benchmark**: A typical 4-document cross-check with 20-100 initial issues takes 4-6 rounds to converge.

**Critical rules**:
1. **NEVER stop after one round** — always re-run the full check suite after fixes
2. **Fix in batches** — group all issues by document, fix each document completely, then re-check
3. **Use METHOD-LEVEL extraction, NOT document-level grep** — extract each method body with `get_method_body()` and check must_have/must_not_have patterns. Document-level grep (`"node.initializer" in doc`) produces false positives that mask structural errors. See `references/method-level-verification-pattern.md`.
4. **Watch for false positives** — Python string slicing in verification can miss content just beyond the slice boundary. Use proper boundary detection:
   ```python
   # ❌ Bad: Arbitrary slice may miss content at position 520+
   class_section = content[start:start+500]
   assert "field_name" in class_section

   # ✅ Good: Find next boundary (next @dataclass or def accept)
   class_section = content[start:content.find("\n\n@dataclass", start)]
   assert "field_name" in class_section

   # ✅ Better: Use regex with word boundary
   assert re.search(r'\bfield_name\b', class_section)
   ```

### 🟡 模式 35：AST 结构变更的爆炸半径（Blast Radius）

AST 节点字段变更的影响范围远超预期，波及 7 个层级：

1. **AST 定义**（`core/ast.py`）— 真相源
2. **Parser**（`core/parser.py`）— 构造 AST 的代码
3. **Semantic Analyzer** — visit 方法访问字段
4. **Type Checker** — visit 方法访问字段
5. **Interpreter** — visit 方法访问字段
6. **ASTPrinter** — 序列化 AST
7. **所有测试文件** — 直接构造 AST 节点

**典型案例**：`ProgramNode(imports, agents, functions, main)` → `ProgramNode(statements)` 导致 50+ 测试失败，涉及 10+ 文件。

**修复策略**：AST 定义 → Parser → Visitors（Analyzer/TypeChecker/Interpreter/ASTPrinter）→ 测试辅助函数 → 单个测试断言 → 运行 pytest 迭代。

详见 `references/code-to-design-compliance.md`。

## Related: Code-to-Design Compliance Checking

After design documents are updated, the **implementation code must be re-checked against the design**. Design-doc-vs-design-doc consistency is only half the battle; code-vs-design is equally critical.

For the AST structure change blast radius, fix strategy, and checklist, see `references/code-to-design-compliance.md`. That reference covers:
- The 7-layer blast radius of AST changes
- ProgramNode refactoring case study (50+ test failures)
- Step-by-step fix order: AST → Parser → Visitors → Tests
- Method extraction patterns for code verification

For automated extraction of TokenType, AST nodes, error codes from Python code, see `references/code-to-design-compliance-check.md`. That file contains the 2026-06-01 Phase 0 compliance session results with detailed classification of 29 discrepancies (93% required design updates, not code fixes).

For regex extraction pitfalls and the golden extraction template, see `references/code-extraction-pitfalls.md`. Covers: local-variable-as-field false positives, @dataclass without args, non-ASCII docstring noise, and the reliable `extract_dataclass_fields()` function.

## Related: Cross-Document Consistency Methodology

For the structured 60-item cross-document consistency check framework (AST field type matrix, error code unification, token access pattern checks), see `references/cross-doc-consistency-method.md`.

For the iterative convergence results from the 2026-06-01 session (6 rounds, 32/32 checks, false positive analysis), see `references/session-2026-06-01-iteration-results.md`.

For the 2026-06-01 Round 2 session (5 rounds, 34/34 checks, Patterns 30-32 discovery), see `references/session-2026-06-01-round2-results.md`.

For the 2026-06-01 Round 2 code-vs-design compliance session (2 rounds, 12/12 checks, ASTPrinter + HellenError fixes), see `references/session-2026-06-01-round2-compliance.md`.

For the method-level verification methodology (get_class_body, get_method_body, check_method with must_have/must_not_have), see `references/method-level-verification-pattern.md`. This is the MOST RELIABLE approach — document-level grep produces false positives that mask structural errors.

For the 2026-06-01 code-to-design compliance session (ProgramNode + IfStmtNode + FunctionDeclNode AST refactoring, 7-layer blast radius, step-by-step fix strategy), see `references/code-compliance-2026-06-01.md`. This covers the actual code changes applied across `core/ast.py`, `core/parser.py`, `semantic/analyzer.py`, `semantic/type_checker.py`, and 10+ test files.

For the 2026-06-01 Round 2 code-vs-design compliance session (2 rounds, 12/12 checks, ASTPrinter + HellenError fixes, keyword regex fix), see `references/session-2026-06-01-round2-compliance.md`.

For the Phase 2 codebase structure and architecture (symbols.py, types.py, analyzer.py, error code organization, type compatibility rules, AST node details), see `references/phase2-codebase-structure.md`.

## Parallel Fix Workflow (New 2026-06-01)

When fixing 20+ inconsistencies across 4+ documents, use **parallel delegation** to fix different documents simultaneously:

```python
# Instead of sequential fix (Phase0 → P1 → P2-3 → Remaining),
# use delegate_task with 3 concurrent subagents:

# Subagent 1: Fix Phase0 (AST definitions + ErrorCode + HellenError)
# Subagent 2: Fix P1 Parser + P2-3 (interpreter bugs + operator types)
# Subagent 3: Fix Remaining (TypeChecker fields + CLI runtime)

# Each subagent gets targeted context: the specific line numbers and old/new text.
# The parent agent coordinates and verifies after all subagents complete.
```

**Key insight**: Different documents can be fixed independently when they don't have cross-references. Phase0 (AST definitions) must be fixed first since all other docs depend on it. But P1 Parser, P2-3, and Remaining can be fixed in parallel once Phase0 is done.

### Pattern 25: Missing supporting class definitions

When unifying `MapLiteralNode.entries` from `list[tuple[Expr, Expr]]` to `list[MapEntryNode]`, you must also **add the `MapEntryNode` class definition** to the AST document. Don't just change the type reference — the referenced class must exist:

```python
# Phase0 AST must include:
@dataclass(frozen=True)
class MapEntryNode:
    """Map 字面量条目：key: value。"""
    key: Expr
    value: Expr
    span: SourceSpan
```

**Check method**: After changing a field type to reference a class, grep `class <ClassName>` to confirm it's defined in the same document or imported.

### Pattern 26: CLI command function uses undefined variables

CLI subcommand functions (`cmd_run`, `cmd_check`) often reference variables that are never created in the function scope:

```python
def cmd_run(args) -> None:
    # ... lexer, parser, analyzer ...
    
    # ❌ runtime never defined in this function
    interpreter = Interpreter(runtime=runtime, env=env)
    
    # ✅ Fix: Create MockRuntime or import real LLMRuntime
    class MockRuntime(RuntimeABC):
        # implement all abstract methods
        ...
    runtime = MockRuntime()
```

**Check method**: After every class instantiation in CLI functions, verify all constructor arguments are defined earlier in the function scope. Grep for `= MockRuntime()` or `= LLMRuntime()` to confirm runtime is created.

### Pattern 27: then_body/else_body vs then_branch/else_branch field naming

IfStmtNode uses `then_branch` and `else_branch` (single nodes, not lists), but TypeChecker and other visitors may incorrectly use `then_body`/`else_body` and iterate over them as lists:

```python
# ❌ Wrong field name + wrong type assumption
for stmt in node.then_body:
    self.visit(stmt)

# ✅ Correct: single node, use visit() to dispatch
if node.then_branch:
    self.visit(node.then_branch)
if node.else_branch:
    self.visit(node.else_branch)
```

**Check method**: Grep `node\.then_body\|node\.else_body` across all documents. Also check ForStmtNode/WhileStmtNode `body` field — if defined as single node, don't iterate with for loop.

### Pattern 28: ErrorCode + HellenError cross-document unification recipe

When three documents define ErrorCode differently (numeric tuples, descriptive auto(), integer constants), use this unification recipe:

1. **Choose one style**: Descriptive names + `auto()` (best readability)
2. **Replace Phase0 ErrorCode enum**: Rewrite entire enum section with new names
3. **Replace Remaining ErrorCode enum**: Copy Phase0's enum (exact match)
4. **Fix all ERR_\d+ references**: Use a mapping dict + regex replace:
   ```python
   err_map = {
       'ERR_300': 'SEMANTIC_UNDECLARED_VAR',
       'ERR_301': 'SEMANTIC_DUPLICATE_DECL',
       # ... all mappings
   }
   for old, new in err_map.items():
       content = content.replace(old, new)
   ```
5. **Verify**: `re.findall(r'ERR_\d+', content)` should return empty for all documents
6. **Unify HellenError**: Copy Phase0's `@dataclass class HellenError` block to Remaining (exact match)

**Result**: 75 error codes unified across 3 documents, 0 ERR_\d+ references remaining.

### Pattern 29: False positives from arbitrary string slicing and `\n\n` boundary in verification

When writing automated verification scripts, Python string slicing with arbitrary lengths can produce false negatives:

```python
# ❌ False negative: 'initializer' is at position 520, slice cuts at 500
var_section = phase0.split("class VarDeclNode")[1][:500]
assert "initializer: Expr" in var_section  # FAILS but field IS present!

# ✅ Correct: slice to next structural boundary
var_section = phase0.split("class VarDeclNode")[1]
var_section = var_section[:var_section.find("\n\n\n")]  # or next @dataclass
assert "initializer: Expr" in var_section  # PASSES

# ✅ Best: use regex on the full relevant section
section = phase0[phase0.find("class VarDeclNode"):phase0.find("def accept", phase0.find("class VarDeclNode"))]
assert re.search(r'initializer:\s*Expr\s*\|\s*None', section)
```

**🔴 CRITICAL: `\n\n` is NOT a reliable class boundary.** Docstrings in Python code blocks are often followed by `\n\n`, which causes premature truncation:

```python
# ❌ BUG: This cuts at the docstring's closing """, not the class end
end = doc.find('\n\n', idx + 20)
class_body = doc[idx:end]  # Only gets the class declaration + docstring, NOT the fields!

# ✅ Correct: Find the NEXT class or dataclass definition
end = doc.find('\nclass ', idx + 20)
if end == -1:
    end = doc.find('\n@dataclass', idx + 20)
if end == -1:
    end = len(doc)  # Last class in document
class_body = doc[idx:end]  # Now contains the full class including fields
```

**Lesson**: When verifying AST field presence in class definitions, always slice to a structural boundary (next `class X`, next `@dataclass`, next `def accept` at top level), NEVER to `\n\n` or an arbitrary character count. The same rule applies to method extraction — use next `def ` at same indentation level, not `\n\n`.

### Pattern 36：类型别名漂移（Type Alias Drift）

设计文档中使用类型别名（如 `Expr`, `Stmt`），但实际代码使用具体类名（`ExpressionNode`, `StatementNode`）。这是代码-vs-设计检查中最高频的假阳性来源：

| 设计别名 | 代码真实类名 | 影响 |
|---------|------------|------|
| `Expr` | `ExpressionNode` | 出现在 30+ 处字段类型定义 |
| `Stmt` | `StatementNode` | 出现在 20+ 处字段类型定义 |

**检查方法**：
```python
# 先统一替换别名再对比
design = design.replace(': Expr\n', ': ExpressionNode\n')
design = design.replace('list[Expr]', 'list[ExpressionNode]')
design = design.replace('(Stmt)', '(StatementNode)')
# 然后进行字段对比
```

**修复规则**：统一为代码中的具体类名（`ExpressionNode`, `StatementNode`），设计文档不使用别名。

### Pattern 37：代码-vs-设计分类优先策略（Classify Before Fix）

当进行**代码-vs-设计**一致性检查（而非设计-vs-设计）时，**不要假设"设计是真相，代码需要修复"**。实际经验表明，代码往往比设计更精确、更完善。

**分类步骤**：对每个不一致项，先分类再修复：

| 分类 | 决策 | 典型案例 |
|------|------|---------|
| **代码更优** | 修改设计以匹配代码 | `operand` vs `right`（UnaryOpNode 中 operand 更清晰）|
| **设计正确** | 修改代码以匹配设计 | 缺失的 API 方法（如 `scan_one()`） |
| **合理差异** | 保持现状，记录原因 | 代码添加了 SEMICOLON、CASE 等设计未定义的 Token |

**判断标准**：
- 如果代码使用了更清晰的命名（`property` vs `name`, `module` vs `path`）→ **代码更优**
- 如果代码缺少设计明确要求的功能 → **设计正确**
- 如果代码添加了合理的新特性 → **合理差异**

**2026-06-01 实战结果**：Phase 0 的 29 个不一致项中，27 项是"代码更优"（需改设计），1 项是"设计正确"（需改代码），1 项是"合理差异"。默认假设"设计总是对的"会导致 93% 的错误修复方向。

### Pattern 38：Visitor 方法清理——注意非 ABC 区域的方法残留

在大型设计文档中，旧的 visitor 方法（如 `visit_await`, `visit_fn_decl`）可能残留在 ASTPrinter 或其他非 Visitor ABC 区域。简单的 `def visit_\w+` 计数会把这些计入 Visitor 方法总数，导致假阳性。

**检查方法**：
```python
# 精确限定在 Visitor ABC 范围内
visitor_start = doc.find('class Visitor(ABC')
visitor_end = doc.find('\nclass ASTNode', visitor_start)
visitor_section = doc[visitor_start:visitor_end]
visitor_methods = set(re.findall(r'def (visit_\w+)\(self', visitor_section))
```

**清理策略**：从 ASTPrinter 等区域删除不属于 Visitor ABC 的旧方法定义。

Phase 0 定义所有 AST 节点携带 `span: SourceSpan` 字段，但 P2-3 和 Remaining 的 TypeChecker/Interpreter 方法中常使用 `node.source` 来传递错误位置：

```python
# ❌ 错误：AST 节点没有 source 字段，只有 span
self._error(ErrorCode.SEMANTIC_TYPE_MISMATCH, "...", node.source)

# ✅ 正确
self._error(ErrorCode.SEMANTIC_TYPE_MISMATCH, "...", node.span)
```

**检查方法**：`grep 'node\.source\b'` 在 P2-3/Remaining 中（排除 `node.source_file` 和 `source:` 字段定义）。所有 AST 节点访问应使用 `node.span`。

**注意**：与模式 15（HellenError 类字段名）不同，这是 AST 节点实例的属性访问漂移。两者都需修正但发生在不同位置。

### 🔴 模式 31：LLM 语句 Interpreter 方法的完整 AST 结构错位

`visit_llm_if_stmt` 的 Interpreter（async）版本最容易假设错误的 AST 结构，因为 LLM 语句的 AST 设计与传统控制流完全不同：

| 节点 | Phase 0 正确结构 | Interpreter 常见错误假设 |
|------|-----------------|------------------------|
| `LlmIfStmtNode` | `description: str`, `branches: list[LlmBranchNode]` | `prompt`, `then_branch`, `else_branch`（当成普通 if） |
| `LlmBranchNode` | `name: str`, `body: list[Stmt]` | 无对应 — Interpreter 直接访问 then/else |

**关键区别**：`llm if` 不是条件分支，而是 **LLM 路由** — 将输入分类到预定义分支。它的执行语义是：调用 LLM → 获取分支名 → 执行匹配分支。

**检查方法**：
1. 在 P2-3 中 `grep 'def.*visit_llm_if_stmt'`
2. 分别检查 sync（Analyzer）和 async（Interpreter）版本
3. 确认 Interpreter 版本访问 `node.description`、`node.branches`，而非 `node.then_branch`

### 🟡 模式 32：P2-3 中 sync（Analyzer）与 async（Interpreter）visitor 方法的验证

P2-3 文档为同一个 AST 节点定义了两个版本的 visitor 方法：
- **sync `def visit_*`**：Semantic Analyzer 版本 — 只做类型检查和符号表构建
- **async `async def visit_*`**：Interpreter 版本 — 实际执行 AST 遍历

验证时必须**分别检查两个版本**，因为：
- Analyzer 版本可能不需要访问运行时字段（如 `node.has_await`、`node.description`）
- Interpreter 版本必须正确访问所有 AST 字段
- 两个版本可能出现不同的不一致

**检查方法**：
```python
for prefix in ['def ', 'async def ']:
    idx = doc.find(f'{prefix}visit_llm_if_stmt')
    # 分别验证两个版本
```

**实战案例**：`visit_llm_act_stmt` 的 Analyzer 版本只返回 `ANY`（不访问 `has_await`），但 Interpreter 版本需要处理 `has_await`。如果只检查第一个出现的 `def visit_llm_act_stmt`（Analyzer 版本），会误报"缺少 `has_await`"。

### 🟡 模式 39：Keyword 映射提取假阳性

设计文档和代码中的 keyword mapping 使用不同格式（cls.X vs TokenType.X），但某些正则提取方式会产生全量假阳性。必须使用 "key": cls.TOKEN 格式的精确正则，而非提取所有双引号内容。

### 🟡 模式 40：ASTPrinter 方法系统性滞后

代码中新增 AST 节点后，ASTPrinter 的 visitor 方法会同步添加到代码，但**设计文档几乎总是遗漏**。实战中 code 有 46 个 ASTPrinter 方法，设计文档只有 26 个（缺失 20 个）。

**受影响的典型方法**：visit_agent_param, visit_call_arg, visit_declaration, visit_fn_block, visit_literal_type, visit_map_entry, visit_optional_type, visit_type, visit_union_type, visit_program, visit_prompt_def, visit_catch_all, visit_catch_clause, visit_finally_block, visit_function_decl, visit_llm_branch, visit_async_call_stmt, visit_case。

**检查方法**：分别提取代码和设计文档中 class ASTPrinter 后的所有 def visit_\w+ 方法，做集合差集。

**修复策略**：从代码中复制缺失方法的实现到设计文档。

### 🟡 模式 41：HellenError 设计文档过度设计

设计文档中的 HellenError 类常包含代码中不存在的 speculative 字段和方法。本会话中发现设计文档有 hint 字段和 from_code() 方法，但代码只有 code/message/span 三字段。

**修复策略**：以代码为准，移除设计文档中多余的字段和方法。

### Pattern 42：代码-vs-设计检查的修复方向（Fix Direction）

**核心原则**：代码必须符合设计文档，设计文档是真相源。

当进行**代码-vs-设计**一致性检查时：

| 情况 | 修复方向 | 理由 |
|------|---------|------|
| 代码缺少设计要求的字段/方法 | 修复代码 | 代码实现不完整 |
| 代码有设计未定义的 Token/节点 | 修复代码（删除）或更新设计（接受改进） | 需判断是否合理改进 |
| 代码使用了比设计更清晰的命名 | 更新设计以匹配代码 | 代码是实际运行的真相源 |

**⚠️ 重要警示**：在执行修复前，**必须先用正确的提取方法验证不一致项的真实性**。正则提取的假阳性（见 `references/code-extraction-pitfalls.md`）远多于真正的代码 bug。2026-06-01 实战中，10/10 检查项全部通过，之前报告的"不一致" 100% 是提取错误。

**正确的工作流**：
1. 用黄金提取模板（见 `references/code-extraction-pitfalls.md`）提取代码结构
2. 与设计文档逐项对比
3. 对每个真实不一致项，先分类（代码更优 / 设计正确 / 合理差异）再修复
4. 修复后重新运行完整检查，迭代直到 0 问题

### Pattern 43：代码-vs-设计检查的迭代轮次基准

| 检查类型 | 典型轮次 | 说明 |
|---------|---------|------|
| 4 文档交叉检查 | 4-6 轮 | 多文档之间的大量不一致 |
| 代码-vs-设计（代码优良） | 2 轮 | 第 1 轮发现 2-4 个问题，第 2 轮验证通过 |
| 代码-vs-设计（代码需重构） | 3-5 轮 | 代码本身也需要修改，涉及测试回归 |

**2026-06-01 实战**：Phase 0 代码-vs-设计检查，第 1 轮发现 4 个问题（ASTPrinter 缺 20 方法、HellenError hint 字段多余），第 2 轮全部通过。

### Pattern 44：跨 Phase 一致性检查的 7 维度框架

进行 Phase N 成果验证时，必须同时检查两个层面：
1. **Phase N vs HLD**：交付物是否符合概要设计规范要求
2. **Phase N vs Phase 0→(N-1)**：是否与前期成果在基础设施层面保持一致

**7 个必检维度**：

| 维度 | 检查内容 | 验证命令 |
|------|---------|---------|
| **TokenType** | 新关键字是否存在于枚举中 | `python -c "from hellen.core.tokens import TokenType; print([t for t in TokenType if t.name in ('NEW', 'KEYS')])"` |
| **AST 节点** | 新节点类有正确字段 + span | `read_file('core/ast.py')` 检查 `@dataclass` |
| **Visitor 模式** | 46/46 方法完整实现 | `python -c "from hellen.core.ast import Visitor; print(len([m for m in dir(Visitor) if m.startswith('visit_')]))"` |
| **ErrorCode** | 42 个 codes 完整，新 codes 在正确范围 | `python -c "from hellen.core.errors import ErrorCode; print(len(list(ErrorCode)))"` |
| **异常层次** | 新异常不与现有层次冲突 | 检查 `cls.__bases__` |
| **SourceSpan** | 所有新节点携带 span | 检查 dataclass 定义 |
| **跨 Phase 兼容** | 已有节点字段无漂移 | 对比 `AgentDeclNode` 等核心节点字段 vs 前期 |

**Phase 编号陷阱**：HLD §5.1 的 Phase 编号与代码实际交付编号可能不一致。验证时应以 HLD 模块需求（M5/M8/etc）为基准，而非 Phase 编号。例如代码标注的"Phase 6"实际交付的是 HLD Phase 4 的剩余内容（Import Resolver + Agent async/await），而 HLD 定义的真实 Phase 6 是 CLI + VS Code。
