# Wiki 和教程更新总结

## 更新日期
2026-08-04

## 更新原因
配置系统简化和交互式设置向导功能实现后，需要更新相关文档以反映新的配置方式。

## 主要变更

### 1. wiki/tutorial/01-getting-started.md

**更新内容：**
- ✅ 移除了 `.env` 格式配置说明
- ✅ 移除了多源配置优先级表（hermes/.env, helen/.env, config.yml, config.yaml）
- ✅ 更新了 `helen init` 命令输出示例，展示交互式向导
- ✅ 添加了环境变量配置说明（HELEN_BASE_URL, HELEN_API_KEY, HELEN_MODEL）
- ✅ 添加了配置检查行为说明（TTY 模式 vs 非 TTY 模式）
- ✅ 添加了跳过配置检查的命令列表

**关键改进：**
```markdown
### Post-Installation Configuration

Helen automatically checks for LLM configuration on first run. If not configured, 
it will prompt you with an interactive setup wizard:

$ helen
⚠️  Helen is not configured
🚀 Helen Setup Wizard
...
```

### 2. wiki/toolchain/cli.md

**更新内容：**
- ✅ 更新了 `helen init` 命令文档，展示交互式向导
- ✅ 移除了 `.env` 格式配置示例
- ✅ 移除了配置加载优先级表
- ✅ 添加了环境变量配置说明
- ✅ 添加了"自动配置检查"章节

**关键改进：**
```markdown
### Automatic Configuration Check

Helen automatically checks for configuration before running commands:

- **Interactive terminal (TTY)**: If not configured, runs the setup wizard automatically
- **Non-interactive mode**: Shows error message. Use environment variables instead
- **Commands that skip config check**: `--version`, `--help`, `init`, `check`, `doc`, `quality`, `lsp`, `template`
```

### 3. wiki/runtime/llm-runtime.md

**更新内容：**
- ✅ 简化了配置加载说明
- ✅ 移除了多源配置优先级表
- ✅ 移除了提供商特定环境变量（DASHSCOPE_*, OPENAI_*）
- ✅ 只保留 HELEN_* 环境变量说明
- ✅ 添加了交互式设置向导说明

**关键改进：**
```markdown
**Configuration loading:** Via `helen.runtime.config` module, loads from two sources:

1. **Configuration file**: `~/.helen/config.yaml` (YAML format)
2. **Environment variables** (override config file): `HELEN_BASE_URL`, `HELEN_API_KEY`, `HELEN_MODEL`

Environment variables take precedence over config file values.
```

### 4. wiki/tutorial/06-llm-statements.md

**更新内容：**
- ✅ 移除了 `~/.helen/.env` 配置引用
- ✅ 移除了 `~/.hermes/.env` 向后兼容说明
- ✅ 更新了配置示例，使用环境变量替代 .env 文件
- ✅ 添加了交互式向导提示说明

**关键改进：**
```markdown
**Notes:**
- Automatically reads configuration from `~/.helen/config.yaml` or environment 
  variables (`HELEN_API_KEY`, `HELEN_BASE_URL`, `HELEN_MODEL`)
- If not configured, Helen will prompt you with an interactive setup wizard
```

## 文档一致性检查

### 已检查但未修改的文件
- `wiki/interpreter/execution.md` - 只包含 "environment" 变量引用（执行环境，非配置文件）
- `wiki/interpreter/spawn.md` - 只包含 "env_snapshot" 引用（执行环境快照）
- `wiki/appendix/changelog.md` - 历史记录，保持不变
- `wiki/appendix/hld-compliance.md` - 架构文档，保持不变
- `wiki/overview/architecture.md` - 架构文档，保持不变

### 已确认无需修改的文件
- `README.md` - 只提到 config.yaml，无 .env 引用
- 其他 wiki 文件 - 不包含配置相关内容

## 迁移指南

### 对于现有用户

**如果使用 config.yaml（无影响）：**
```bash
# 配置继续正常工作，无需任何更改
~/.helen/config.yaml
```

**如果使用 .env 文件（需要迁移）：**
```bash
# 旧方式（不再支持）
~/.helen/.env
HELEN_API_KEY=***

# 新方式 1：使用 config.yaml
~/.helen/config.yaml
llm:
  api_key: "***"

# 新方式 2：使用环境变量
export HELEN_API_KEY=***
```

**如果使用 config.yml（需要迁移）：**
```bash
# 旧方式（不再支持）
~/.helen/config.yml

# 新方式：重命名为 config.yaml
mv ~/.helen/config.yml ~/.helen/config.yaml
```

**如果使用提供商特定环境变量（需要更改）：**
```bash
# 旧方式（不再支持）
export DASHSCOPE_API_KEY=***
export OPENAI_API_KEY=***

# 新方式
export HELEN_API_KEY=***
```

## 文档质量检查

### 已验证
- ✅ 所有配置示例使用新格式
- ✅ 所有环境变量使用 HELEN_* 前缀
- ✅ 移除了所有 .env 和 config.yml 引用
- ✅ 添加了交互式向导说明
- ✅ 添加了配置检查行为说明
- ✅ 添加了跳过配置检查的命令列表

### 待改进（未来工作）
- 可以考虑添加配置迁移脚本
- 可以添加更多配置示例（不同 LLM 提供商）
- 可以添加故障排除指南

## 总结

本次文档更新确保了所有 wiki 和教程与新的配置系统保持一致，移除了对已弃用配置格式（.env, config.yml）的引用，并添加了新特性（交互式向导、自动配置检查）的说明。

所有文档现在都反映以下配置方式：
1. **配置文件**：`~/.helen/config.yaml`
2. **环境变量**：`HELEN_BASE_URL`, `HELEN_API_KEY`, `HELEN_MODEL`

配置检查行为：
- **TTY 模式**：自动启动交互式向导
- **非 TTY 模式**：显示错误并退出
- **跳过检查的命令**：--version, --help, init, check, doc, quality, lsp, template
