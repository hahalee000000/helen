# Phase 7: Agent 集成与声明扩展

> 将上下文管理增强集成到 Agent 执行流程，扩展 Agent 声明支持 `context {}` 配置

**日期**: 2026-07-06  
**状态**: 实施中  
**目标**: 让增强功能自动应用于所有 Agent

---

## 任务分解

### Task 1: 集成到 Agent 执行流程

**目标**: 在 `helen/interpreter/llm_mixin.py` 中自动应用渐进压缩和工作记忆

**涉及文件**:
- `helen/interpreter/llm_mixin.py` - 主要集成点
- `helen/interpreter/interpreter.py` - 初始化 WorkingMemory
- `helen/interpreter/agent_context.py` - 新建，Agent 上下文管理

**集成点**:
1. `_add_to_history()` - 每次添加消息后更新 WorkingMemory
2. `_prepare_history_for_llm()` - 应用渐进压缩和三通道构建
3. `_record_llm_response_to_history()` - 从工具调用更新 WorkingMemory

**预期效果**:
- WorkingMemory 自动跟踪活跃文件、最近决策、待办事项、错误历史
- 渐进压缩自动应用于历史
- 三通道上下文自动构建（系统指令 + 工作记忆 + 对话历史）

### Task 2: Agent 声明扩展

**目标**: 支持 `context {}` 配置块，让每个 Agent 可以独立配置上下文策略

**涉及文件**:
- `helen/core/ast.py` - 添加 `ContextConfigNode` 和 `AgentContextConfig` 字段
- `helen/core/parser.py` - 解析 `context {}` 块
- `helen/core/analyzer.py` - 验证 context 配置
- `helen/interpreter/llm_mixin.py` - 读取 context 配置

**新语法**:
```helen
agent CodeReviewer {
    description "代码审查"
    model "qwen3.7-plus"
    max-turns 20
    
    // 新增：context 配置块
    context {
        compression "graduated"
        cache-aware true
        working-memory true
        working-memory-tokens 5000
    }
    
    tools ["read_file", "shell_exec"]
    main {
        let review = llm act "审查这段代码"
        return review
    }
}
```

**配置选项**:
- `compression`: "none" | "traditional" | "graduated" (默认 "graduated")
- `cache-aware`: true | false (默认 true)
- `working-memory`: true | false (默认 true)
- `working-memory-tokens`: int (默认 5000)

---

## 实施步骤

### Step 1: 创建 AgentContext 管理器
- 新建 `helen/interpreter/agent_context.py`
- 实现 `AgentContextManager` 类，封装 WorkingMemory 和压缩策略

### Step 2: 集成到 Interpreter
- 在 `interpreter.py` 中初始化 `AgentContextManager`
- 在 `_add_to_history()` 中调用 `update_working_memory()`
- 在 `_record_llm_response_to_history()` 中从工具调用更新

### Step 3: 修改 _prepare_history_for_llm
- 应用渐进压缩（如果启用）
- 构建三通道上下文（如果启用 WorkingMemory）
- 返回最终的 messages 列表

### Step 4: 扩展 AST
- 添加 `ContextConfigNode` 类
- 在 `AgentDeclNode` 中添加 `context_config` 字段

### Step 5: 扩展 Parser
- 在 `_parse_agent_decl()` 中解析 `context {}` 块
- 解析所有配置选项

### Step 6: 在 LlmMixin 中使用配置
- 从 `AgentDeclNode.context_config` 读取配置
- 根据配置决定是否应用渐进压缩和 WorkingMemory

### Step 7: 编写测试
- 测试集成效果
- 测试 Agent 配置解析
- 测试配置应用到执行流程

---

## 预期效果

### 自动集成
- 所有 Agent 默认使用渐进压缩和 WorkingMemory
- 无需修改现有代码即可获得增强效果

### 可配置性
- 每个 Agent 可以独立配置上下文策略
- 简单 Agent 可以禁用高级功能以节省开销
- 复杂 Agent 可以启用所有功能以获得最佳效果

### 向后兼容
- 现有 Agent 代码无需修改
- 默认配置提供最佳实践
- 可选配置允许自定义

---

## 验证清单

- [ ] WorkingMemory 自动更新
- [ ] 渐进压缩自动应用
- [ ] 三通道上下文正确构建
- [ ] Agent 配置正确解析
- [ ] 配置正确应用到执行流程
- [ ] 现有测试全部通过
- [ ] 新测试覆盖所有新功能
