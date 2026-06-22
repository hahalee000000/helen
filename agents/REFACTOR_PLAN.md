# Helen Programming Agent 重构计划

## 日期: 2026-06-22
## 版本: v3.0

---

## 一、Helen语言限制分析

### 1.1 模块导入限制 ❌

**问题**: Helen不支持跨文件函数导入

**验证**:
```helen
// test_module.helen
fn add(a: int, b: int) -> int {
    return a + b
}

// test_import.helen
import "/tmp/test_module.helen"

main {
    let result = add(5, 3)  // Error: undeclared variable 'add'
}
```

**错误**: `[E0332] undeclared variable 'add'`

**原因**: 
- `import`语句被解析,但SemanticAnalyzer未正确处理
- ImportResolver未将导入函数加载到当前作用域
- 缺少模块命名空间机制

**影响**: 
- 无法实现真正的模块化
- 必须重复定义函数或使用单文件架构
- 代码复用困难

### 1.2 命名空间缺失 ❌

**问题**: 没有模块级别的命名空间隔离

**影响**:
- 所有函数在全局命名空间
- 容易产生命名冲突
- 无法实现`utils.math.add()`这样的调用

### 1.3 类型系统限制 ⚠️

**问题**: 
- 大量使用`map`类型,缺少类型约束
- 没有泛型支持(已在v1.8取消)
- 缺少接口/协议的类型检查

**影响**:
- 运行时才能发现类型错误
- 缺少编译时类型安全

### 1.4 错误处理 ⚠️

**问题**: 
- 大量使用map返回`{status: "error", message: "..."}`
- 未充分利用Helen的try-catch机制
- 缺少统一的错误类型

**影响**:
- 错误处理代码冗长
- 缺少结构化的错误信息

---

## 二、现有Agent问题分析

### 2.1 代码重复 🔴

**问题**: `contracts.helen`和`programming_agent.helen`有大量重复代码

**示例**:
- `search_skills_for_context()`在两个文件中都有定义
- 注释明确说明:"For now, we duplicate the needed functions here until Helen supports module-level imports properly"

**影响**:
- 维护困难
- 容易不一致
- 违反DRY原则

### 2.2 架构混乱 🟡

**问题**: 
- `programming_agent.helen`既是agent定义又包含辅助函数
- 职责不清晰
- 缺少清晰的分层

**当前结构**:
```
programming_agent.helen
├── Helper Functions (重复)
├── Agent Definition
│   ├── functions block
│   └── main block
└── Entry Point
```

**问题**:
- Helper Functions应该在独立模块
- Agent应该只关注编排逻辑
- 缺少清晰的依赖关系

### 2.3 测试覆盖不足 🟡

**问题**:
- 现有测试主要是语法检查和文件存在性检查
- 缺少行为测试
- 缺少集成测试
- 缺少错误处理测试

**现有测试**:
```python
def test_agent_file_exists():  # 只检查文件存在
def test_agent_has_required_sections():  # 只检查关键字
def test_skill_manager_syntax():  # 只检查语法
```

**缺失测试**:
- 函数行为测试
- 错误处理测试
- 集成工作流测试
- 边界条件测试

### 2.4 错误处理不完善 🟡

**问题**:
- 大量使用map返回状态
- 未使用try-catch机制
- 错误信息不统一

**示例**:
```helen
fn skill_manager_create(...) -> map {
    if name == "" {
        return {"status": "error", "message": "name cannot be empty", "path": ""}
    }
    // ...
}
```

**问题**:
- 每个函数都需要检查status
- 缺少统一的错误类型
- 错误处理代码冗长

---

## 三、重构目标

### 3.1 架构改进

**目标**: 清晰的分层架构

```
agents/
├── contracts/
│   └── contracts.helen          # 契约定义(仅签名,无实现)
├── core/
│   ├── skill_manager.helen      # Skill CRUD操作
│   ├── skill_matcher.helen      # Skill搜索匹配
│   ├── skill_learner.helen      # 从修复中学习
│   └── skill_evolver.helen      # 演进现有skill
├── programming_agent.helen      # 主编排器(仅编排逻辑)
└── utils/
    ├── file_utils.helen         # 文件操作工具
    ├── string_utils.helen       # 字符串处理工具
    └── validation.helen         # 输入验证工具
```

**改进**:
- 消除代码重复
- 清晰的职责分离
- 更好的可维护性

### 3.2 契约优先

**目标**: 使用Helen的protocol特性定义清晰接口

**示例**:
```helen
protocol SkillManager {
    fn create(name: str, category: str, content: str) -> map
    fn read(name: str, category: str) -> map
    fn update(name: str, category: str, content: str) -> map
    fn delete(name: str, category: str) -> map
    fn list() -> map
}
```

**改进**:
- 明确的接口契约
- 编译时检查(部分)
- 更好的文档

### 3.3 统一错误处理

**目标**: 使用try-catch替代map状态检查

**示例**:
```helen
fn create_skill(name: str, category: str, content: str) -> map {
    try {
        validate_name(name)
        validate_category(category)
        let path = build_skill_path(name, category)
        write_file(path, content)
        return {"status": "success", "path": path}
    } catch ValidationError e {
        return {"status": "error", "message": e.message}
    } catch IOError e {
        return {"status": "error", "message": "IO error: " + e.message}
    }
}
```

**改进**:
- 更清晰的错误处理
- 结构化的错误信息
- 减少重复代码

### 3.4 测试驱动

**目标**: 完整的测试覆盖

**测试层次**:
1. **单元测试**: 每个函数的行为测试
2. **集成测试**: 模块间交互测试
3. **端到端测试**: 完整工作流测试
4. **错误测试**: 错误处理测试

**示例**:
```python
class TestSkillManager:
    def test_create_skill_success(self):
        """Should create skill with valid inputs."""
        
    def test_create_skill_empty_name(self):
        """Should return error for empty name."""
        
    def test_create_skill_invalid_category(self):
        """Should return error for invalid category."""
        
    def test_create_skill_file_exists(self):
        """Should return error if skill already exists."""
```

---

## 四、实施计划

### 阶段1: 契约定义 (Day 1)

**任务**:
1. 定义清晰的接口契约
2. 使用protocol特性
3. 编写契约文档

**交付物**:
- `contracts/contracts.helen` (更新)
- 契约文档

### 阶段2: 测试编写 (Day 2-3)

**任务**:
1. 编写单元测试
2. 编写集成测试
3. 编写错误处理测试

**交付物**:
- `tests/agents/test_skill_manager.py`
- `tests/agents/test_skill_matcher.py`
- `tests/agents/test_skill_learner.py`
- `tests/agents/test_skill_evolver.py`
- `tests/agents/test_programming_agent.py` (更新)

### 阶段3: 核心实现 (Day 4-6)

**任务**:
1. 实现`skill_manager.helen`
2. 实现`skill_matcher.helen`
3. 实现`skill_learner.helen`
4. 实现`skill_evolver.helen`

**交付物**:
- 4个核心模块
- 所有测试通过

### 阶段4: 编排器实现 (Day 7)

**任务**:
1. 重构`programming_agent.helen`
2. 消除代码重复
3. 实现清晰的编排逻辑

**交付物**:
- 更新后的`programming_agent.helen`
- 集成测试通过

### 阶段5: 工具模块 (Day 8)

**任务**:
1. 提取公共工具函数
2. 实现`utils/`模块
3. 重构现有代码使用工具模块

**交付物**:
- `utils/file_utils.helen`
- `utils/string_utils.helen`
- `utils/validation.helen`

### 阶段6: 文档与优化 (Day 9-10)

**任务**:
1. 更新文档
2. 代码审查
3. 性能优化

**交付物**:
- 更新的README
- 代码质量报告
- 性能基准测试

---

## 五、Helen语言改进建议

基于重构过程中发现的问题,建议Helen语言增加以下特性:

### 5.1 模块导入系统 (P0)

**需求**:
```helen
// 基本导入
import "path/to/module.helen"

// 命名空间导入
import "path/to/module.helen" as utils

// 选择性导入
import { add, multiply } from "path/to/math.helen"
```

**实现建议**:
1. 在SemanticAnalyzer中处理ImportStmtNode
2. 使用ImportResolver加载导入的函数
3. 支持命名空间前缀

### 5.2 模块命名空间 (P1)

**需求**:
```helen
import "math.helen" as math

main {
    let result = math.add(5, 3)
}
```

**实现建议**:
1. 为每个模块创建独立的符号表
2. 支持`module.function()`语法
3. 避免命名冲突

### 5.3 结构化错误类型 (P1)

**需求**:
```helen
error ValidationError {
    message: str
    field: str
}

error IOError {
    message: str
    path: str
}

fn validate(name: str) {
    if name == "" {
        throw ValidationError(message="name cannot be empty", field="name")
    }
}
```

**实现建议**:
1. 扩展错误系统
2. 支持自定义错误类型
3. 支持错误字段

### 5.4 类型别名 (P2)

**需求**:
```helen
type SkillResult = map {
    status: str,
    message: str,
    path: str?
}

fn create_skill(...) -> SkillResult {
    // ...
}
```

**实现建议**:
1. 支持type别名定义
2. 支持结构类型检查
3. 提供更好的类型文档

---

## 六、风险与缓解

### 6.1 风险: 模块导入不支持

**缓解**: 
- 使用单文件架构
- 通过代码生成减少重复
- 使用宏或模板(如果支持)

### 6.2 风险: 测试覆盖不足

**缓解**:
- 优先编写关键路径测试
- 使用覆盖率工具
- 代码审查

### 6.3 风险: 性能下降

**缓解**:
- 基准测试
- 性能分析
- 优化关键路径

---

## 七、成功标准

### 7.1 功能标准

- [ ] 所有现有功能保持
- [ ] 代码重复减少80%
- [ ] 测试覆盖率>80%
- [ ] 所有测试通过

### 7.2 质量标准

- [ ] 代码质量评分>8.5/10
- [ ] 无严重安全问题
- [ ] 文档完整
- [ ] 性能无下降

### 7.3 交付标准

- [ ] 10天内完成
- [ ] 代码审查通过
- [ ] 文档更新
- [ ] 推送到GitHub

---

## 八、附录

### 8.1 参考资源

- Helen语言规范
- 契约优先开发方法
- TDD最佳实践
- 模块化设计模式

### 8.2 相关文档

- `agents/README.md`
- `docs/tutorial.md`
- `skills/software-development/helen-language-development/SKILL.md`

---

**下一步**: 开始阶段1 - 契约定义
