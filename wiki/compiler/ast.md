# AST 节点定义

> 模块 M3 | `helen/core/ast.py` | 50 节点类 | Visitor 模式 47 方法

---

## Visitor 模式

```python
R = TypeVar("R")

class Visitor(ABC, Generic[R]):
    @abstractmethod
    def visit_literal(self, node: LiteralNode) -> R: ...
    @abstractmethod
    def visit_variable(self, node: VariableNode) -> R: ...
    @abstractmethod
    def visit_binary_op(self, node: BinaryOpNode) -> R: ...
    # ... 共 46 个抽象方法
```

**三个编译阶段共享同一 Visitor 接口**：

| 阶段 | Visitor 实现 | 返回类型 |
|---|---|---|
| 语义分析 | `SemanticAnalyzer` | `None` (副作用：填充符号表) |
| 解释执行 | `Interpreter` | `object` (运行时值) |
| 文档生成 | `DocGenerator` | `dict` (文档结构) |

---

## 节点层次结构

```
ASTNode (ABC, frozen dataclass)
├── StatementNode (ABC)          ← 语句
│   ├── ExprStmtNode             ← 表达式语句
│   ├── VarDeclNode              ← 变量声明
│   ├── IfStmtNode               ← 条件语句
│   ├── ForStmtNode              ← 遍历循环
│   ├── WhileStmtNode            ← 条件循环
│   ├── BreakStmtNode            ← break
│   ├── ContinueStmtNode         ← continue
│   ├── ReturnStmtNode           ← return
│   ├── MatchStmtNode            ← 模式匹配
│   ├── TryStmtNode              ← 异常处理
│   ├── FunctionDeclNode         ← 函数声明
│   ├── AsyncCallStmtNode        ← 异步调用
│   ├── ImportStmtNode           ← 导入
│   ├── AgentDeclNode            ← Agent 声明
│   ├── MainBlockNode            ← 主程序块
│   ├── LlmActStmtNode           ← LLM act
│   ├── LlmIfStmtNode            ← LLM if
│   ├── FnBlockNode              ← 函数块
│   ├── CatchClauseNode          ← catch 子句
│   ├── CatchAllNode             ← catch-all
│   ├── FinallyBlockNode         ← finally 块
│   ├── CaseNode                 ← case 分支
│   ├── PromptDefNode            ← prompt 定义
│   ├── AgentParamNode           ← Agent 参数
│   ├── DeclarationNode          ← 通用声明
│   └── LlmBranchNode            ← LLM 分支
│
├── ExpressionNode (ABC)         ← 表达式
│   ├── LiteralNode              ← 字面量
│   ├── VariableNode             ← 变量引用
│   ├── BinaryOpNode             ← 二元运算
│   ├── UnaryOpNode              ← 一元运算
│   ├── GroupingNode             ← 括号分组
│   ├── CallNode                 ← 函数调用
│   ├── AccessNode               ← 属性访问
│   ├── IndexNode                ← 索引访问
│   ├── ListLiteralNode          ← 列表字面量
│   ├── MapLiteralNode           ← 映射字面量
│   ├── CallArgNode              ← 调用参数
│   ├── MapEntryNode             ← 映射条目
│   ├── TemplateRefNode          ← 模板引用
│   └── LlmActArgNode            ← LLM act 参数
│
├── TypeNode (ABC)               ← 类型
│   ├── OptionalTypeNode         ← 可选 T?
│   ├── UnionTypeNode            ← 联合 A|B
│   └── LiteralTypeNode          ← 字面量类型
│
└── ProgramNode                  ← 程序根节点
```

---

## 关键节点详解

### ProgramNode

```python
@dataclass(frozen=True)
class ProgramNode(ASTNode):
    span: SourceSpan
    statements: list[StatementNode]
```

程序根节点，包含所有顶层声明和 main 块。

### AgentDeclNode

```python
@dataclass(frozen=True)
class AgentDeclNode(StatementNode):
    span: SourceSpan
    name: str
    settings: dict[str, Any]           # model/temperature/max-turns 等
    params: list[AgentParamNode]       # 参数列表
    prompt: str | None                 # prompt 文本
    declarations: list[StatementNode]  # 内部声明
    logic: list[StatementNode]         # 内部逻辑
    context_config: ContextConfigNode | None  # Phase 7: 上下文配置
```

### ContextConfigNode (Phase 7)

```python
@dataclass(frozen=True)
class ContextConfigNode(StatementNode):
    span: SourceSpan
    compression: str = "graduated"      # 压缩策略: "none" / "graduated" / "traditional"
    cache_aware: bool = True            # 缓存感知
    working_memory: bool = True         # 工作记忆
    working_memory_tokens: int = 5000   # 工作记忆词元预算
```

用于 agent 的 `context {}` 配置块，控制上下文管理策略。

**语法示例**：

```helen
agent SmartAssistant {
    context {
        compression "graduated"
        cache-aware true
        working-memory true
        working-memory-tokens 5000
    }
}
```

### LlmActStmtNode

```python
@dataclass(frozen=True)
class LlmActStmtNode(StatementNode):
    span: SourceSpan
    target: str                        # 目标 (函数名/表达式)
    arguments: dict[str, ExpressionNode]  # 命名参数
    description: str                   # 描述
```

### LlmIfStmtNode

```python
@dataclass(frozen=True)
class LlmIfStmtNode(StatementNode):
    span: SourceSpan
    description: str
    branches: list[LlmBranchNode]      # case + default
```

---

## 每个节点携带 SourceSpan

```python
@dataclass(frozen=True)
class ASTNode(ABC):
    span: SourceSpan  # 所有子类的第一个字段
```

SourceSpan 从 Lexer 开始，贯穿 Parser、AST、SemanticAnalyzer 到 ErrorFormatter，确保每个错误都能精确定位到源码位置。

---

## 节点不可变

所有 AST 节点使用 `@dataclass(frozen=True)`：

- 不可修改 → 编译阶段之间安全传递
- 可哈希 → 可作为字典键或集合元素
- 线程安全 → 支持并行分析（未来扩展）

---

## accept 方法

每个节点实现 `accept(visitor: Visitor[R]) -> R`：

```python
def accept(self, visitor: Visitor[R]) -> R:
    return visitor.visit_binary_op(self)
```

这实现了**双分派**：节点知道调用哪个 visit 方法，Visitor 知道如何处理节点。
