# shell_exec brace expansion 修复报告

## 问题描述

**症状**：`shell_exec("mkdir -p ./project/{src,tests,contracts}")` 创建了一个字面名为 `{src,tests,contracts}` 的目录，而不是预期的 `src`、`tests`、`contracts` 三个目录。

**原因**：`subprocess.run()` 默认使用 `/bin/sh` 作为 shell，而 `/bin/sh` 不支持 brace expansion `{}` 语法。

## 根本原因

```python
# 之前的实现
result = subprocess.run(
    cmd, shell=shell, capture_output=True, text=True,
    timeout=timeout,
)
# 问题：shell=True 时默认使用 /bin/sh，不支持 brace expansion
```

**测试验证**：
```bash
# 使用 /bin/sh（默认）
mkdir -p test_sh/{a,b,c}
# 结果：创建了 {a,b,c} 字面目录

# 使用 /bin/bash
mkdir -p test_bash/{a,b,c}
# 结果：正确创建了 a、b、c 三个目录
```

## 解决方案

在 `subprocess.run()` 中指定 `executable='/bin/bash'`：

```python
# 修复后的实现
result = subprocess.run(
    cmd, shell=shell, capture_output=True, text=True,
    timeout=timeout, executable='/bin/bash' if shell else None,
)
# 修复：使用 /bin/bash 支持 brace expansion
```

**关键改动**：
- `executable='/bin/bash' if shell else None`
- 当 `shell=True` 时使用 bash，`shell=False` 时不指定（使用默认）

## 实施细节

### 修改文件

| 文件 | 改动 | 说明 |
|------|------|------|
| `helen/runtime/tools.py` | +1 行 | 添加 `executable='/bin/bash'` 参数 |
| `tests/runtime/test_tools_coverage.py` | +13 行 | 新增 `test_brace_expansion` 测试 |
| `skills/software-development/helen-stdlib/SKILL.md` | +1 行 | 更新文档说明使用 bash |
| `wiki/appendix/changelog.md` | +1 行 | 更新 changelog |

### 新增测试

```python
def test_brace_expansion(self):
    """Test bash brace expansion works with default shell=True"""
    import tempfile
    import os
    with tempfile.TemporaryDirectory() as tmpdir:
        test_dir = os.path.join(tmpdir, "test_brace")
        result = json.loads(_shell_exec(f"mkdir -p {test_dir}/{{a,b,c}}"))
        assert result["exit_code"] == 0
        # Should create three separate directories, not one literal {a,b,c}
        assert os.path.exists(os.path.join(test_dir, "a"))
        assert os.path.exists(os.path.join(test_dir, "b"))
        assert os.path.exists(os.path.join(test_dir, "c"))
        assert not os.path.exists(os.path.join(test_dir, "{a,b,c}"))
```

## 测试结果

```
✅ 10/10 TestShellExec 测试通过（新增 1 个）
✅ 2400 个测试全部通过（排除性能测试）
✅ 无回归
```

## 支持的 bash 特性

修复后，`shell_exec` 现在支持所有 bash 特性：

| 特性 | 示例 | 状态 |
|------|------|------|
| Brace expansion | `mkdir -p {src,tests,contracts}` | ✅ 支持 |
| 命令链接 | `cmd1 && cmd2` | ✅ 支持 |
| 管道 | `cmd1 \| cmd2` | ✅ 支持 |
| 重定向 | `echo > file` | ✅ 支持 |
| 命令替换 | `echo $(cmd)` | ✅ 支持 |
| 变量扩展 | `echo $HOME` | ✅ 支持 |
| 通配符 | `ls *.txt` | ✅ 支持 |

## 兼容性考虑

### 跨平台

- **Linux/macOS**：✅ 完全支持（`/bin/bash` 标准位置）
- **Windows**：⚠️ 可能需要调整（Windows 没有 `/bin/bash`）

**建议**：如果需要 Windows 支持，可以：
1. 检测操作系统
2. Windows 使用 `cmd.exe` 或 PowerShell
3. 或者提供 `shell_executable` 参数让应用指定

### 向后兼容

- ✅ 现有代码不受影响（`shell=False` 仍然使用 `shlex.split`）
- ✅ 简单命令仍然正常工作
- ✅ 只是增强了 bash 特性支持

## 安全性

**风险**：使用 bash 可能引入额外的安全风险（bash 比 sh 功能更强大）

**缓解措施**：
1. 文档明确警告 shell injection 风险
2. 提供 `shell=False` 选项用于安全敏感场景
3. AI 生成的命令通常不包含用户输入，风险可控

## 总结

✅ **修复完成**

- 问题：`/bin/sh` 不支持 brace expansion
- 解决：使用 `/bin/bash` 作为默认 shell
- 影响：支持所有 bash 特性
- 测试：新增 1 个测试，所有测试通过
- 风险：低（向后兼容，文档警告）

**关键学习**：
- `subprocess.run` 默认使用 `/bin/sh`，不是 bash
- Brace expansion 是 bash 特性，不是 POSIX sh 标准
- 对于复杂 shell 语法，需要明确指定 bash
