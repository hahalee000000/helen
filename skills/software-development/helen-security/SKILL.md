---
name: helen-security
description: "Helen 安全最佳实践 — 安全沙箱、路径验证、SSRF 防护、命令注入防护"
version: 1.0.0
author: Helen Team
license: MIT
tags: [helen, security, sandbox, validation]
---

# Helen 安全最佳实践

Helen 运行时内置**安全沙箱**（`helen/runtime/security.py`），为所有系统交互提供防护层。

## 安全架构

```
Helen 程序
    │
    ▼
┌─────────────────────┐
│   安全沙箱           │  ← 所有系统调用经过此层
│  validate_path()    │
│  validate_url()     │
│  validate_command() │
└──────────┬──────────┘
           │
           ▼
      操作系统资源
```

## 路径安全

### 规则

| 规则 | 说明 |
|------|------|
| 基础目录限制 | 路径必须在 `base_dir` 内，阻止 `../` 遍历 |
| 敏感路径阻止 | `/etc/shadow`、`/proc`、`/sys`、`/dev` 被禁止 |
| 符号链接解析 | 先解析符号链接再验证，防止绕过 |
| 绝对路径检查 | 绝对路径也需要通过安全检查 |

### 示例

```helen
# ✅ 安全的路径
read_file("./data/config.json")
write_file("./output/result.txt", content)

# ❌ 被阻止的路径
read_file("/etc/shadow")           # SecurityError: sensitive path
read_file("../../etc/passwd")      # SecurityError: path traversal
read_file("/proc/self/environ")    # SecurityError: sensitive directory
```

### 最佳实践

1. **使用相对路径**：始终使用相对于项目根目录的路径
2. **验证用户输入**：如果路径来自用户输入，先验证格式
3. **避免符号链接**：如果可能，禁用符号链接或验证目标

```helen
# 安全的文件上传处理
fn handle_upload(filename: str, content: str) {
    # 验证文件名（只允许字母数字和点）
    if not regex_match(filename, r"^[\w.]+$") {
        throw ValueError("Invalid filename")
    }
    
    # 限制在 uploads 目录内
    let safe_path = "./uploads/" + filename
    write_file(safe_path, content)
}
```

## URL 过滤（SSRF 防护）

### 规则

| 规则 | 说明 |
|------|------|
| 协议限制 | 仅允许 `http://` 和 `https://` |
| 私有 IP 阻止 | `10/8`、`172.16/12`、`192.168/16`、`127/8` 被禁止 |
| IPv6 保护 | 阻止 `::1`（回环）、`fc00::/7`（ULA）、`fe80::/10`（link-local） |
| DNS 重绑定 | 解析后再次验证 IP（防止 DNS rebinding 攻击） |

### 示例

```helen
# ✅ 安全的 URL
http_get("https://api.example.com/data")
http_post("https://httpbin.org/post", body="test")

# ❌ 被阻止的 URL（SSRF 防护）
http_get("http://169.254.169.254/latest/meta-data/")  # AWS 元数据
http_get("http://127.0.0.1:8080/admin")               # 本地服务
http_get("http://192.168.1.1/router")                 # 内网设备
http_get("file:///etc/passwd")                        # 文件协议
```

### 最佳实践

1. **白名单域名**：如果可能，只允许访问已知安全的域名
2. **验证响应**：检查响应的 Content-Type 和大小
3. **超时设置**：为所有 HTTP 请求设置超时

```helen
# 安全的 API 调用
fn call_external_api(url: str) {
    # 验证 URL 格式
    let parsed = url_parse(url)
    if parsed["scheme"] != "https" {
        throw ValueError("Only HTTPS allowed")
    }
    
    # 白名单检查
    let allowed_hosts = ["api.example.com", "data.service.com"]
    if parsed["host"] not in allowed_hosts {
        throw ValueError("Host not in whitelist")
    }
    
    # 发起请求（自动 SSRF 防护）
    let response = http_get(url)
    return json_parse(response["body"])
}
```

## 命令安全

### 阻止的命令

| 命令 | 原因 |
|------|------|
| `rm -rf /` | 删除根目录 |
| `mkfs.*` | 格式化磁盘 |
| `dd if=/dev/zero of=/dev/sda` | 覆盖磁盘 |
| `:(){ :\|:& };:` | Fork bomb |
| `chmod -R 777 /` | 权限破坏 |
| `wget ... \| sh` | 远程代码执行 |

### shell_exec 安全模式

```helen
# ✅ 推荐：列表参数模式（默认，防注入）
let result = shell_exec(["ls", "-la", "/tmp"])
let output = shell_exec(["grep", "error", "/var/log/app.log"])

# ⚠️ 危险：shell=True 模式（需要显式启用）
# 仅在完全信任输入时使用
let result = shell_exec("ls -la /tmp", shell=True)
```

### 最佳实践

1. **始终使用列表参数**：避免 `shell=True`
2. **验证输入**：如果命令参数来自用户输入，严格验证
3. **限制命令**：只允许白名单命令
4. **超时设置**：为所有命令设置超时

```helen
# 安全的命令执行包装器
fn safe_exec(command: list[str], allowed_commands: list[str]) {
    # 验证命令在白名单中
    let cmd_name = command[0]
    if cmd_name not in allowed_commands {
        throw ValueError("Command not allowed: " + cmd_name)
    }
    
    # 验证参数（禁止 shell 元字符）
    for arg in command[1:] {
        if regex_match(arg, r"[;&|`$]") {
            throw ValueError("Invalid character in argument")
        }
    }
    
    # 执行命令（自动安全检查）
    return shell_exec(command)
}

# 使用
let result = safe_exec(
    ["grep", "-i", "error", "/var/log/app.log"],
    ["grep", "ls", "cat", "wc"]
)
```

## 资源限制

| 资源 | 限制 | 常量 | 说明 |
|------|------|------|------|
| 文件读取大小 | 16 MB | `MAX_READ_SIZE` | 防止内存耗尽 |
| 文件写入大小 | 64 MB | `MAX_WRITE_SIZE` | 防止磁盘填满 |
| HTTP 下载大小 | 100 MB | `MAX_DOWNLOAD_SIZE` | 防止带宽耗尽 |
| HTTP 响应大小 | 8 MB | `MAX_RESPONSE_SIZE` | 防止内存耗尽 |
| 命令超时 | 300 秒 | `MAX_COMMAND_TIMEOUT` | 防止挂起 |
| HTTP 请求超时 | 30 秒 | `DEFAULT_REQUEST_TIMEOUT` | 防止挂起 |

### 最佳实践

1. **分块处理大文件**：不要一次性读取大文件
2. **设置超时**：为所有 I/O 操作设置超时
3. **限制上传大小**：验证上传文件的大小

```helen
# 安全的文件处理
fn process_large_file(path: str) {
    # 检查文件大小
    let size = file_size(path)
    if size > 10 * 1024 * 1024 {  # 10 MB
        throw ValueError("File too large")
    }
    
    # 读取文件（自动 16MB 限制）
    let content = read_file(path)
    
    # 处理...
    return content
}
```

## 环境变量保护

`env_list()` 函数自动掩码敏感环境变量：

```helen
let env = env_list()
# 输出:
# {
#   "HOME": "/home/user",
#   "PATH": "/usr/bin:/bin",
#   "API_KEY": "********",        # 自动掩码
#   "DATABASE_PASSWORD": "********"  # 自动掩码
# }
```

### 掩码规则

键名包含以下字符串的值会被替换为 `********`：
- `PASSWORD`
- `SECRET`
- `TOKEN`
- `API_KEY`
- `PRIVATE_KEY`
- `CREDENTIAL`

### 最佳实践

1. **不要日志记录环境变量**：即使掩码，也避免完整输出
2. **使用专用配置**：敏感配置使用单独的配置文件
3. **限制环境变量访问**：只读取需要的环境变量

```helen
# ✅ 安全的配置访问
fn get_database_config() {
    return {
        "host": env_get("DB_HOST", "localhost"),
        "port": int(env_get("DB_PORT", "5432")),
        "name": env_get("DB_NAME", "myapp"),
        # 密码通过安全通道传递，不从环境变量读取
    }
}

# ❌ 不安全：日志记录所有环境变量
# print(env_list())  # 即使掩码，也可能泄露信息
```

## 进程安全

### 规则

| 功能 | 限制 |
|------|------|
| `kill(pid, signal)` | PID ≤ 1 或当前进程被阻止 |
| 允许的信号 | 仅 SIGTERM、SIGINT、SIGHUP、SIGUSR1、SIGUSR2 |

### 示例

```helen
# ✅ 安全的信号发送
kill(child_pid, SIGTERM)  # 优雅终止

# ❌ 被阻止的操作
kill(1, SIGKILL)           # SecurityError: cannot kill init
kill(current_pid, SIGKILL) # SecurityError: cannot kill self
kill(1234, SIGKILL)        # SecurityError: signal not allowed
```

## 安全错误处理

安全违规抛出 `SecurityError` 异常：

```helen
try {
    read_file("/etc/shadow")
} catch SecurityError as e {
    print("安全违规: " + e.message)
    # 输出: 安全违规: Path '/etc/shadow' is in sensitive directory
    
    # 记录日志（不包含敏感路径）
    log_error("Security violation", category="security")
}
```

### 最佳实践

1. **捕获 SecurityError**：所有系统操作都应该捕获安全异常
2. **不要泄露细节**：错误消息不要包含敏感路径或 URL
3. **记录日志**：记录安全事件用于审计

```helen
# 安全的错误处理
fn safe_file_operation(path: str) {
    try {
        return read_file(path)
    } catch SecurityError as e {
        # 记录安全事件（不包含路径）
        log_error("Security violation in file operation", category="security")
        
        # 返回通用错误消息
        throw RuntimeError("File operation not permitted")
    } catch FileNotFoundError as e {
        throw RuntimeError("File not found")
    }
}
```

## 安全检查清单

开发 Helen 程序时，遵循以下安全检查清单：

- [ ] **路径验证**：所有文件路径使用相对路径或验证后的绝对路径
- [ ] **URL 白名单**：只允许访问已知安全的域名
- [ ] **命令列表参数**：始终使用列表参数模式调用 `shell_exec`
- [ ] **输入验证**：所有用户输入在使用前验证格式
- [ ] **超时设置**：为所有 I/O 操作设置超时
- [ ] **错误处理**：捕获 `SecurityError` 并记录日志
- [ ] **环境变量**：不日志记录敏感环境变量
- [ ] **资源限制**：检查文件大小和下载大小

## 总结

Helen 安全沙箱提供多层防护：

1. ✅ **路径验证** — 阻止敏感文件访问和目录遍历
2. ✅ **URL 过滤** — SSRF 防护，阻止私有网络访问
3. ✅ **命令安全** — 阻止危险命令，默认防注入
4. ✅ **资源限制** — 防止资源耗尽攻击
5. ✅ **环境掩码** — 保护敏感凭据
6. ✅ **进程保护** — 限制信号和 PID 操作

这些安全机制对所有 Helen 程序透明生效，无需额外配置。但开发者仍应遵循最佳实践，编写安全的代码。
