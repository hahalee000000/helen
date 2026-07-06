# 跨文档一致性检查方法论

> 生成于 2026-06-01 系统性分段检查会话
> 基准: HLD v1.2.1, 详细设计 4 文档

## 检查框架

系统性分段检查按 **60 项** 结构化对比执行，覆盖 4 份详细设计文档 + 跨文档一致性：

| 维度 | 数量 | 文档分布 |
|------|------|---------|
| Phase0 | 25 项 | Token/Lexer/AST/Errors |
| P1 Parser | 7 项 | Parser/Pratt/Statements |
| P2-3 | 10 项 | Analyzer/Interpreter/Runtime |
| Remaining | 8 项 | Import/TypeChecker/CLI/Errors |
| 跨文档 | 10 项 | 全局一致性 |

## 跨文档一致性检查清单

### 1. AST 字段类型矩阵

对每个 AST 节点，提取 Phase 0 的字段类型定义，对比 P1 Parser 创建代码和 P2-3/Remaining 消费代码：

```python
# 检查矩阵模板
node_field_matrix = {
    "VarDeclNode": {
        "name": {"phase0": "Token", "p1": "Token.lexeme→str", "p23_analyzer": "Token.lexeme", "p23_interpreter": "Token.lexeme"},
        "initializer": {"phase0": "Expr|None", "p1": "Expr", "p23_analyzer": "Expr|None", "p23_interpreter": "Expr|None"},
    },
    "FunctionDeclNode": {
        "body": {"phase0": "MainBlockNode", "p1": "list[StatementNode]"},  # ← CONFLICT!
    },
    "MapLiteralNode": {
        "entries": {"phase0": "list[tuple[Expr,Expr]]", "p1": "list[MapEntryNode]"},  # ← CONFLICT!
    },
    "BinaryOpNode": {
        "operator": {"phase0": "Token", "p23_interpreter": "used as str"},  # ← BUG!
    },
}
```

### 2. 错误码统一性

分别提取各文档的 ErrorCode 定义，构建统一映射表：

| 错误码 | Phase0 | Remaining | P2-3 Analyzer | 状态 |
|--------|--------|-----------|---------------|------|
| 100 | ERR_100 | LEXICAL_INVALID_CHAR | - | 两套定义 |
| 200 | ERR_200 | SYNTAX_ERROR | ERR_200 | 两套定义 |
| 300 | ERR_300 | SEMANTIC_UNDECLARED_VAR | 300 | 三套定义 |
| 302 | ERR_302 | SEMANTIC_TYPE_MISMATCH | ERR_TYPE_MISMATCH | 三套定义 |

### 3. Token/Operator 访问模式

| 模式 | 正确 | 错误 | 位置 |
|------|------|------|------|
| `node.operator` 比较 | `node.operator.lexeme == '!'` | `node.operator == '!'` | P2-3 Interpreter |
| `node.operator` 字典查找 | `ops[node.operator.lexeme]` | `ops[node.operator]` | P2-3 Interpreter |
| `catch_clause.exception_type` | `exc_type_map[catch_clause.exception_type.lexeme]` | `exc_type_map[catch_clause.exception_type]` | P2-3 Interpreter |

### 4. 字段名一致性

| Phase 0 定义名 | P1/P2-3 中错误变体 | 影响范围 |
|---------------|-------------------|---------|
| `then_branch` | `then_body` | P1 Parser, Remaining TypeChecker |
| `else_branch` | `else_body` | P1 Parser, Remaining TypeChecker |
| `initializer` | `value`, `init` | P2-3 Analyzer/Interpreter |
| `iterator` | `name_token` (未定义) | P1 Parser |
