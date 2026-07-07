# 上下文压缩研究资料 (Context Compression Research)

> **最后更新**: 2026-07-07
> 本文档记录 Helen 上下文管理系统借鉴的学术研究和技术文章，供后续改进参考。

---

## 一、核心借鉴

Helen 的渐进压缩管线（特别是 Layer 4 Context Collapse 和 Layer 5 Auto-Compact）借鉴了以下研究成果：

| 算法/框架 | 来源 | Helen 借鉴点 | 实现位置 |
|-----------|------|--------------|----------|
| **RCC** (Recurrent Context Compression) | [OpenReview 2024] | 分段摘要，保留时序结构 | `graduated_compression.py::_context_collapse` |
| **CogCanvas** | [arXiv 2025] | 保留时间细节，避免信息丢失 | `graduated_compression.py::_summarize_block` |
| **DAST** (Dynamic Allocation) | [ACL 2025] | 动态分配压缩 tokens（未来改进方向） | 未实现 |

---

## 二、重要论文

### 2.1 Recurrent Context Compression (RCC)

**标题**: Recurrent Context Compression: Efficiently Expanding the Context Window of LLM

**来源**: OpenReview / arXiv (2024)

**链接**: https://openreview.net/forum?id=GYk0thSY1M

**核心思想**:
- 迭代式压缩，重复压缩上下文以保留重要信息
- 使用有界内存表示无限交互流
- 每次压缩都基于之前的压缩结果，形成"递归摘要"

**Helen 借鉴**:
```python
# Layer 4: Context Collapse 采用分段摘要
# 将旧消息分成多个时间块，每块独立摘要
block_size = 10
blocks = []
for i in range(0, len(old_msgs), block_size):
    block = old_msgs[i:i + block_size]
    blocks.append((i, i + len(block), block))

# 每个块生成独立摘要，保留时间线
for block_idx, (start, end, block) in enumerate(blocks):
    block_summary = _summarize_block(block, start, end)
```

**与 RCC 的区别**:
- RCC 使用 LLM 进行递归摘要（有成本）
- Helen Layer 4 使用零成本结构摘要（正则提取）
- Helen Layer 5 可选启用 LLM 语义摘要

---

### 2.2 CogCanvas: Compression-Resistant Cognitive Artifacts

**标题**: CogCanvas: Compression-Resistant Cognitive Artifacts for Long Summarization

**来源**: arXiv (Dec 2025)

**链接**: https://arxiv.org/html/2601.00821v1

**核心思想**:
- 解决摘要过程中时间细节丢失的问题
- 提出"认知工件"概念：保留任务进展的关键节点
- 强调时序结构对长对话理解的重要性

**Helen 借鉴**:
```python
# Layer 4: 保留时间标记
def _summarize_block(block, start_idx, end_idx):
    parts = [f"  [{start_idx}-{end_idx}]"]  # 时间标记
    
    # 提取文件引用（任务进展节点）
    file_refs = set()
    for msg in block:
        matches = re.finditer(r'[\w./-]+\.(?:py|js|ts|...)', msg.content)
        for m in matches:
            file_refs.add(m.group())
    
    # 提取工具使用（行动记录）
    tool_counts = {}
    for msg in block:
        if msg.role == "assistant" and msg.tool_calls:
            for tc in msg.tool_calls:
                name = tc.get("name", "unknown")
                tool_counts[name] = tool_counts.get(name, 0) + 1
```

**输出示例**:
```
[Context Collapse: 30 turns archived as timeline]
  [0-10] Files: main.py, utils.py | Tools: read_file(3) | Tasks: Fix auth bug
  [10-20] Files: auth.py | Tools: shell_exec(2) | Tasks: Run tests
[Global] Turns: 15u/15a | Tool calls: 12 | Errors: 2
```

---

### 2.3 DAST: Dynamic Allocation of Compression Tokens

**标题**: DAST: Context-Aware Compression in LLMs via Dynamic Allocation

**来源**: ACL 2025 Findings

**链接**: https://aclanthology.org/2025.findings-acl.1055.pdf

**核心思想**:
- 动态分配压缩 tokens，基于 LLM 对上下文重要性的理解
- 不同部分获得不同的压缩比例
- 关键信息获得更多 tokens，冗余信息被激进压缩

**Helen 现状**:
- 当前未实现（需要 LLM 参与压缩决策）
- 未来可作为 Layer 5 的增强选项

**潜在实现方向**:
```python
# 伪代码：动态分配压缩
def _dynamic_compress(history, llm_client):
    # 1. LLM 评估每条消息的重要性
    importance_scores = llm_client.evaluate_importance(history)
    
    # 2. 根据重要性分配 tokens
    for msg, score in zip(history, importance_scores):
        if score > 0.8:  # 高重要性
            keep_full(msg)
        elif score > 0.5:  # 中等重要性
            keep_summary(msg)
        else:  # 低重要性
            drop_or_minimal(msg)
```

---

### 2.4 Context Codec: Formal Framework

**标题**: A Formal Framework for Verifiable LLM Context Compression

**来源**: arXiv (May 2026)

**链接**: https://arxiv.org/html/2605.17304v1

**核心思想**:
- 提出 commitment-level 的形式化框架
- 使用数学方法验证压缩的正确性
- 保证压缩后的上下文保留关键信息

**Helen 相关性**:
- 理论性强，短期不直接应用
- 长期可用于验证压缩管线的正确性

---

### 2.5 AUTOSUMM: Comprehensive Framework

**标题**: AUTOSUMM: A Comprehensive Framework for LLM-Based Summarization

**来源**: ACL 2025 Industry

**链接**: https://aclanthology.org/2025.acl-industry.35.pdf

**核心思想**:
- 针对客户-顾问对话的自动摘要框架
- 多层次摘要策略
- 工业级应用案例

**Helen 相关性**:
- `LLMSummarizer` 的设计参考了类似的多层次策略
- 结构化摘要格式（任务目标、关键决策、文件变更等）

---

## 三、技术文章

### 3.1 Semantic Compression (Quarkiverse/LangChain4J)

**链接**: https://docs.quarkiverse.io/quarkus-langchain4j/dev/guide-semantic-compression.html

**核心思想**:
- 语义压缩作为截断的替代方案
- 使用 LLM 生成摘要保留关键上下文
- 适用于长对话场景

**Helen 借鉴**:
- Layer 5 Auto-Compact 实现了类似的语义压缩
- 通过 `llm_client` 参数可选启用

---

### 3.2 You Don't Need RAG. You Need Semantic Compression.

**链接**: https://pub.towardsai.net/you-dont-need-rag-you-need-semantic-compression-74d41d65bac1

**来源**: Towards AI (Mar 2026)

**核心思想**:
- 当源材料远超上下文窗口时，语义压缩优于 RAG
- 多主题覆盖时需要源归属
- 压缩比与信息保留的权衡

**Helen 相关性**:
- 验证了 Helen 的渐进压缩策略
- Layer 1-4 零成本 + Layer 5 语义压缩的混合策略

---

### 3.3 Compressing Context (Factory.ai)

**链接**: https://factory.ai/news/compressing-context

**来源**: Factory.ai (Jul 2025)

**核心思想**:
- 使用摘要模型实时压缩对话
- 保持在上下文窗口内
- 工业实践经验

**Helen 借鉴**:
- `AgentContextManager` 的实时压缩机制
- `prepare_context()` 在每次 LLM 调用前应用压缩

---

## 四、综述论文

### 4.1 Context Compression for LLM Agents: A Survey

**链接**: https://www.preprints.org/manuscript/202605.2065

**来源**: Preprints.org (May 2026)

**核心内容**:
- 全面调查 LLM Agent 的上下文压缩方法
- 涵盖观察压缩（工具输出、HTML DOM、日志、截图）
- 分析失败模式和最佳实践

**Helen 定位**:
- Helen 的渐进压缩管线属于"记忆状态压缩"类别
- 5 层策略覆盖了从零成本到高成本的全谱

---

### 4.2 Prompt Compression in LLMs — Making Every Token Count

**链接**: https://medium.com/@sahin.samia/prompt-compression-in-large-language-models-llms-making-every-token-count-078a2d1c7e03

**来源**: Medium (Feb 2025)

**核心内容**:
- 去除冗余、简化句子结构
- 利用专门的压缩技术最小化 token 使用
- 实用技巧汇总

---

## 五、压缩比对比

根据研究文献，不同压缩策略的典型效果：

| 压缩级别 | 压缩比 | 准确率影响 | 适用场景 |
|---------|--------|-----------|---------|
| 轻度压缩 (Light) | 2-3× | <5% 准确率损失 | 大多数场景 |
| 中度压缩 (Moderate) | 5-7× | 中等准确率损失 | 成本敏感场景 |
| 激进压缩 (Aggressive) | 10×+ | 显著准确率损失 | 极长对话 |

**Helen 策略**:
- Layer 1-3: 轻度压缩（保留大部分信息）
- Layer 4: 中度压缩（时间线摘要）
- Layer 5: 激进压缩（LLM 语义摘要，10×+ 压缩比）

---

## 六、未来改进方向

基于研究资料，以下是 Helen 上下文管理的潜在改进方向：

### 6.1 短期（易实现）

- [ ] **自适应压缩阈值**: 根据对话类型动态调整 Layer 触发阈值
- [ ] **压缩质量评估**: 添加压缩前后的信息保留度指标

### 6.2 中期（需要实验）

- [ ] **DAST 集成**: 使用 LLM 评估消息重要性，动态分配压缩 tokens
- [ ] **多层次摘要**: 结合 AUTOSUMM 的多层次策略，生成更精细的摘要

### 6.3 长期（研究性质）

- [ ] **形式化验证**: 参考 Context Codec，验证压缩正确性
- [ ] **认知工件保留**: 深化 CogCanvas 思想，保留更多任务进展节点

---

## 七、引用格式

如需引用 Helen 的上下文压缩系统，请使用：

```bibtex
@misc{helen-context-compression,
  title = {Helen Context Management System},
  author = {Helen Team},
  year = {2026},
  note = {Inspired by RCC, CogCanvas, and DAST research},
  url = {https://github.com/your-repo/helen/wiki/runtime/context-management}
}
```

---

**最后更新**: 2026-07-07  
**维护者**: Helen Team  
**状态**: 活跃维护
