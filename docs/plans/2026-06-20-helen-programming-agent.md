# Helen Programming Agent 实施计划

> **目标：** 构建一个垂直于Helen编程的自进化智能体，深度集成到开发工作流中，形成"学习-编程-反馈-进化"闭环。

**日期：** 2026-06-20  
**状态：** 规划阶段  
**优先级：** P0（AI原生核心特性）

---

## 1. 背景与动机

### 1.1 现状分析

Helen目前有两个AI辅助实现：

| 实现 | 位置 | 能力 | 局限 |
|------|------|------|------|
| **REPL `:ask`** | `helen/cli/repl.py` | 基于知识库回答Helen语法/调试问题 | 无状态、无记忆、无代码操作能力 |
| **HelenChat** | `examples/helenchat/` | 通用AI助手（工具调用、规划、技能、记忆） | 通用型，不聚焦编程，与语言核心解耦 |

### 1.2 核心Gap

**缺少一个专注于"辅助Helen编程"的自进化智能体**

- `:ask`每次都是无状态问答，不会记住项目上下文
- `helenchat`是通用助手，无法深度理解Helen代码结构
- 编程辅助需要代码操作能力（读文件、改代码、跑测试），而非通用工具集

### 1.3 为什么有必要

1. **Dogfooding**：Helen号称"AI原生语言"，自己的开发体验必须深度集成AI
2. **学习闭环**：编程辅助需要项目记忆（用户偏好、测试框架、常见错误模式）
3. **垂直优化**：不需要通用智能体的复杂性，只需要编程相关的精准能力

---

## 2. 设计原则

### 2.1 做减法，不做加法

**不是"又一个Hermes"，而是"Helen编程的Copilot"**

| 需要 | 不需要 |
|------|--------|
| ✅ 项目级记忆 | ❌ Web搜索、浏览器控制 |
| ✅ 代码感知（读文件、理解AST） | ❌ 多平台消息集成 |
| ✅ 技能学习（从修复中提取模式） | ❌ Cron定时任务 |
| ✅ 测试驱动（自动跑测试、看报错） | ❌ 子智能体编排 |
| ✅ Git集成（自动提交+推送） | ❌ 通用文件操作 |

### 2.2 自进化机制

智能体应该能从交互中学习：

1. **错误模式学习**：修复错误后，提取模式存入技能库
2. **项目偏好学习**：记住用户喜欢的代码风格、测试框架
3. **主动提示**：下次遇到类似错误时，主动提示已知解决方案

---

## 3. 实施计划

### Phase 1: 增强REPL `:ask` → `:agent`（2周）

**目标：** 在现有REPL基础上，添加项目记忆和代码操作能力

#### Task 1.1: 项目记忆系统

**文件：**
- 创建：`helen/agent/project_memory.py`
- 测试：`tests/agent/test_project_memory.py`

**功能：**
```python
class ProjectMemory:
    """项目级记忆，存储在项目目录的 .helen/agent/ 下"""
    
    def __init__(self, project_root: Path):
        self.memory_dir = project_root / ".helen" / "agent"
        self.memory_file = self.memory_dir / "MEMORY.md"
        self.preferences_file = self.memory_dir / "PREFERENCES.md"
    
    def remember(self, key: str, value: str):
        """记住一个事实（如：项目使用pytest，用户喜欢type hints）"""
        pass
    
    def recall(self, query: str) -> str:
        """回忆相关记忆"""
        pass
    
    def list_memories(self) -> List[Dict]:
        """列出所有记忆"""
        pass
```

**测试用例：**
- 记忆写入和读取
- 记忆持久化（重启后仍然存在）
- 记忆搜索（基于关键词）

#### Task 1.2: 代码感知工具

**文件：**
- 创建：`helen/agent/code_tools.py`
- 测试：`tests/agent/test_code_tools.py`

**功能：**
```python
class CodeTools:
    """代码操作工具集（限定在项目目录内）"""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
    
    def read_file(self, relative_path: str) -> str:
        """读取项目内文件"""
        pass
    
    def list_files(self, pattern: str = "**/*.helen") -> List[str]:
        """列出项目内文件"""
        pass
    
    def search_code(self, pattern: str, file_glob: str = "*.helen") -> List[Dict]:
        """在代码中搜索模式"""
        pass
    
    def get_ast(self, file_path: str) -> Dict:
        """获取文件的AST结构"""
        pass
```

**安全措施：**
- 所有路径操作限定在`project_root`内
- 防止路径遍历攻击（`..`检查）
- 文件大小限制（>1MB拒绝读取）

#### Task 1.3: 测试运行工具

**文件：**
- 创建：`helen/agent/test_runner.py`
- 测试：`tests/agent/test_test_runner.py`

**功能：**
```python
class TestRunner:
    """运行Helen测试并解析结果"""
    
    def run_tests(self, test_file: Optional[str] = None) -> TestResult:
        """运行测试（全部或指定文件）"""
        pass
    
    def get_failed_tests(self) -> List[FailedTest]:
        """获取失败的测试列表"""
        pass
    
    def get_error_context(self, test: FailedTest) -> str:
        """获取失败测试的上下文（源代码+错误信息）"""
        pass
```

#### Task 1.4: REPL集成 `:agent`命令

**文件：**
- 修改：`helen/cli/repl.py`
- 测试：`tests/cli/test_repl_agent.py`

**功能：**
```
:agent <question>          # 向智能体提问（带项目上下文）
:agent remember <fact>     # 记住一个事实
:agent recall              # 列出所有记忆
:agent run_tests           # 运行测试并分析失败
:agent fix <test_name>     # 尝试修复失败的测试
```

**实现要点：**
- 加载项目记忆作为上下文
- 注入代码工具到智能体
- 流式输出响应（使用现有`llm stream`）

#### Phase 1 验收标准

- [ ] 可以在REPL中使用`:agent`命令
- [ ] 智能体能记住项目信息（如测试框架、代码风格）
- [ ] 智能体能读取项目代码并回答问题
- [ ] 智能体能运行测试并分析失败原因
- [ ] 记忆持久化（重启REPL后仍然存在）

---

### Phase 2: 自进化能力（2周）

**目标：** 智能体能从交互中学习，形成技能库

#### Task 2.1: 错误模式提取

**文件：**
- 创建：`helen/agent/pattern_extractor.py`
- 测试：`tests/agent/test_pattern_extractor.py`

**功能：**
```python
class PatternExtractor:
    """从错误修复中提取模式"""
    
    def extract_pattern(
        self, 
        error: str, 
        fix: str, 
        context: str
    ) -> ErrorPattern:
        """从错误和修复中提取模式"""
        pass
    
    def find_similar_patterns(self, error: str) -> List[ErrorPattern]:
        """查找相似的历史错误模式"""
        pass
```

**存储格式：**
```yaml
# .helen/agent/patterns/undefined-variable.yaml
patterns:
  - error: "Undefined variable 'x'"
    cause: "变量未声明就使用"
    fix: "在使用前添加 'let x = ...' 声明"
    example: |
      // 错误
      print(x)
      
      // 正确
      let x = 10
      print(x)
    frequency: 15
    last_seen: 2026-06-20
```

#### Task 2.2: 主动提示系统

**文件：**
- 创建：`helen/agent/proactive_hint.py`
- 测试：`tests/agent/test_proactive_hint.py`

**功能：**
```python
class ProactiveHint:
    """主动提示已知解决方案"""
    
    def check_error(self, error: str) -> Optional[Hint]:
        """检查错误是否有已知解决方案"""
        pass
    
    def suggest_fix(self, error: str, context: str) -> str:
        """基于历史模式建议修复方案"""
        pass
```

**集成点：**
- 在REPL错误输出后自动检查是否有已知模式
- 在`:agent fix`时优先使用历史模式

#### Task 2.3: 技能库管理

**文件：**
- 创建：`helen/agent/skill_library.py`
- 测试：`tests/agent/test_skill_library.py`

**功能：**
```python
class SkillLibrary:
    """管理从交互中学到的技能"""
    
    def save_skill(self, name: str, content: str):
        """保存一个技能（如：如何配置LLM、如何写测试）"""
        pass
    
    def load_skill(self, name: str) -> str:
        """加载一个技能"""
        pass
    
    def list_skills(self) -> List[str]:
        """列出所有技能"""
        pass
```

**技能示例：**
```markdown
# 如何配置Helen LLM

## 步骤
1. 创建 `~/.helen/config.yaml`
2. 添加以下内容：
   ```yaml
   llm:
     provider: openai
     api_key: sk-xxx
     model: gpt-4
   ```
3. 验证：`helen repl` 然后 `:ask test`

## 常见问题
- API key无效：检查是否复制完整
- 模型不存在：检查模型名称拼写
```

#### Phase 2 验收标准

- [ ] 智能体能从错误修复中提取模式
- [ ] 智能体能识别相似错误并提示已知解决方案
- [ ] 技能库能保存和加载编程技能
- [ ] 模式库持久化（存储在`.helen/agent/patterns/`）

---

### Phase 3: 深度集成（2周）

**目标：** 与编辑器和Git深度集成

#### Task 3.1: LSP集成（可选，依赖LSP实现进度）

**文件：**
- 创建：`helen/lsp/agent_integration.py`

**功能：**
- 在编辑器中实时提供AI建议
- 鼠标悬停显示错误解释和修复建议
- 代码补全时考虑项目上下文

#### Task 3.2: Git自动提交

**文件：**
- 创建：`helen/agent/git_integration.py`
- 测试：`tests/agent/test_git_integration.py`

**功能：**
```python
class GitIntegration:
    """Git自动提交和推送"""
    
    def commit_with_message(self, message: str):
        """提交更改（自动生成commit message）"""
        pass
    
    def push_to_remote(self):
        """推送到远程仓库"""
        pass
    
    def create_pr(self, title: str, description: str):
        """创建Pull Request"""
        pass
```

**集成点：**
- `:agent commit`：自动分析更改并生成commit message
- `:agent push`：提交并推送
- `:agent pr`：创建PR（使用GitHub API）

#### Task 3.3: 多会话同步

**文件：**
- 创建：`helen/agent/session_sync.py`

**功能：**
- 多个REPL会话共享记忆
- 记忆冲突解决（最后写入优先）
- 会话历史查询

#### Phase 3 验收标准

- [ ] 智能体能自动提交代码（生成合理的commit message）
- [ ] 智能体能推送到远程仓库
- [ ] （可选）LSP集成提供实时AI建议
- [ ] 多会话记忆同步

---

## 4. 技术细节

### 4.1 目录结构

```
helen/
├── agent/
│   ├── __init__.py
│   ├── project_memory.py       # 项目记忆
│   ├── code_tools.py           # 代码操作工具
│   ├── test_runner.py          # 测试运行器
│   ├── pattern_extractor.py    # 错误模式提取
│   ├── proactive_hint.py       # 主动提示
│   ├── skill_library.py        # 技能库
│   ├── git_integration.py      # Git集成
│   └── session_sync.py         # 会话同步
└── cli/
    └── repl.py                 # 添加:agent命令

.helen/
└── agent/
    ├── MEMORY.md               # 项目记忆
    ├── PREFERENCES.md          # 用户偏好
    ├── patterns/               # 错误模式库
    │   ├── undefined-variable.yaml
    │   └── type-mismatch.yaml
    └── skills/                 # 技能库
        ├── configure-llm.md
        └── write-tests.md
```

### 4.2 安全考虑

1. **路径遍历防护**：所有文件操作限定在`project_root`内
2. **文件大小限制**：>1MB的文件拒绝读取
3. **命令注入防护**：Git命令使用列表参数，不用shell=True
4. **API密钥保护**：不在日志中输出API密钥

### 4.3 性能优化

1. **记忆索引**：使用SQLite存储记忆，支持快速搜索
2. **模式匹配**：使用向量相似度查找相似错误（可选，依赖embedding库）
3. **懒加载**：技能库按需加载，不一次性读入内存

---

## 5. 验收标准（整体）

### 功能验收

- [ ] 可以在REPL中使用`:agent`命令与智能体交互
- [ ] 智能体能记住项目信息（测试框架、代码风格、依赖）
- [ ] 智能体能读取项目代码并回答问题
- [ ] 智能体能运行测试并分析失败原因
- [ ] 智能体能从错误修复中学习模式
- [ ] 智能体能识别相似错误并提示已知解决方案
- [ ] 智能体能自动提交代码并推送

### 性能验收

- [ ] 记忆搜索响应时间 < 100ms
- [ ] 模式匹配响应时间 < 500ms
- [ ] 测试运行不阻塞REPL主线程

### 安全验收

- [ ] 路径遍历攻击测试通过
- [ ] 命令注入测试通过
- [ ] API密钥不泄露测试通过

---

## 6. 风险与缓解

### 风险1：记忆膨胀

**问题：** 长期使用的项目可能积累大量记忆，导致上下文过长

**缓解：**
- 定期清理低频记忆（>90天未使用）
- 使用摘要压缩旧记忆
- 记忆分页加载

### 风险2：模式误匹配

**问题：** 错误模式匹配不准确，给出错误的修复建议

**缓解：**
- 模式匹配时显示置信度
- 用户确认后才应用修复
- 记录误匹配反馈，优化匹配算法

### 风险3：Git操作失败

**问题：** 自动提交可能遇到冲突、权限问题

**缓解：**
- 提交前检查git状态
- 失败时回滚并提示用户
- 提供手动解决的指导

---

## 7. 后续扩展

### 7.1 多智能体协作

- **代码审查智能体**：自动审查PR，提出改进建议
- **测试生成智能体**：根据代码自动生成测试用例
- **文档生成智能体**：根据代码自动生成文档

### 7.2 云端同步

- 记忆和模式库云端备份
- 团队共享模式库
- 跨设备同步

### 7.3 可视化界面

- Web界面查看记忆和模式库
- 图形化编辑技能
- 模式库统计分析

---

## 8. 实施时间线

| 阶段 | 时间 | 里程碑 |
|------|------|--------|
| Phase 1 | 第1-2周 | REPL `:agent`命令可用，项目记忆+代码工具 |
| Phase 2 | 第3-4周 | 自进化能力，错误模式提取+主动提示 |
| Phase 3 | 第5-6周 | Git集成+LSP集成（可选） |
| 测试 | 第7周 | 全面测试+文档完善 |
| 发布 | 第8周 | v1.0发布 |

---

## 9. 参考资源

- Hermes Agent架构：https://github.com/NousResearch/hermes-agent
- Helen语言文档：`~/helen/docs/tutorial.md`
- 现有`:ask`实现：`~/helen/helen/cli/repl.py`
- 现有HelenChat：`~/helen/examples/helenchat/`

---

**下一步：** 从Phase 1 Task 1.1开始实施，先构建项目记忆系统。
