# 多模态支持 (v1.17)

Helen v1.17 引入了基于回调的多模态支持，采用**回调即适配器**的设计模式，使 Helen 能够处理图像、视频、音频等多种媒体类型，同时保持与各种 LLM provider 的兼容性。

## 设计原则

多模态支持的核心原则是：**协议差异由用户回调处理，Helen 核心不内置 provider 特定格式**。

这种设计带来以下优势：

- **协议无关**：Helen 核心不绑定任何特定 provider 的媒体格式
- **可扩展性**：新增模态或 provider 无需修改语言核心
- **灵活性**：用户可以根据需要自定义媒体处理逻辑
- **向后兼容**：纯文本程序无需任何修改

## 核心概念

### MediaPart 数据类型

`MediaPart` 是一等公民数据类型，表示媒体内容：

```helen
# 从文件创建
let img = media("file:///path/to/image.png")

# 从 URL 创建
let remote_img = media("https://example.com/image.jpg")

# 从 base64 创建
let b64_data = read_file_base64("image.png")
let inline_img = media_base64(b64_data, "image/png")

# 检查是否为 MediaPart
是媒体(img)  # 返回: 真

# 获取媒体类型
媒体类型(img)  # 返回: "image"
```

### MediaPart 字段

每个 `MediaPart` 对象包含以下字段：

- `source`: 来源类型（"file"、"url"、"base64"）
- `content`: 内容（文件路径、URL 或 base64 字符串）
- `mime`: MIME 类型（如 "image/png"）
- `media_type`: 媒体类型（"image"、"video"、"audio"）
- `metadata`: 额外元数据（字典）

## llm act 多模态语法

### 基本用法

在 `llm act` 中传递媒体：

```helen
agent 图像分析 {
    description "分析图像内容"
    
    main {
        let img = media("photo.jpg")
        let result = llm act "描述这张图片" media(img)
        print(result)
    }
}
```

### 多个媒体

可以传递多个媒体对象：

```helen
let img1 = media("image1.png")
let img2 = media("image2.png")
let result = llm act "比较这两张图片" media(img1, img2)
```

### on_media 回调（媒体适配器）

`on_media` 回调用于将 `MediaPart` 列表转换为特定 provider 所需的格式：

```helen
agent 自定义媒体处理 {
    main {
        let img = media("diagram.png")
        
        let result = llm act "解释这个图表" 
            media(img)
            on_media fn(parts, provider) {
                # 自定义转换逻辑
                如果 provider == "openai" {
                    返回 parts.map(fn(part) {
                        返回 {"type": "image_url", "image_url": {"url": part.content}}
                    })
                } 否则 {
                    # 其他 provider 的格式
                    返回 parts.map(fn(part) {
                        返回 {"type": "image", "source": part.content}
                    })
                }
            }
    }
}
```

**参数说明**：
- `parts`: `MediaPart` 对象列表
- `provider`: 当前使用的 provider 名称（如 "openai"、"claude"）
- **返回值**: 转换后的内容部分列表（provider 特定格式）

**默认行为**：如果不指定 `on_media`，Helen 使用默认的 OpenAI 兼容适配器。

### on_generate 回调（媒体生成）

`on_generate` 回调将媒体生成能力注册为工具，让 LLM 决定何时调用：

```helen
agent 图像生成器 {
    description "根据描述生成图像"
    
    main {
        let result = llm act "创建一张日落风景图"
            on_generate fn(params) {
                # params 包含: prompt, size, model 等
                let prompt = params["prompt"]
                
                # 调用图像生成 API
                let image_url = call_image_generation_api(prompt)
                
                # 返回生成的媒体
                返回 media("url://" + image_url)
            }
        
        print("生成的图像: " + result)
    }
}
```

**工作原理**：
1. `on_generate` 将生成能力注册为 LLM 可调用的工具
2. LLM 在工具循环中决定是否调用生成工具
3. 调用时执行回调函数，返回生成的 `MediaPart`
4. 生成的媒体自动添加到对话上下文中

**支持场景**：
- 文生图（text-to-image）
- 文生视频（text-to-video）
- 任何可通过 API 生成的媒体类型

### provider 子句

指定使用的 provider（影响默认适配器行为）：

```helen
let result = llm act "分析这张图片"
    media(img)
    provider("claude")
```

### 流式回调

多模态也支持流式输出回调：

```helen
let result = llm act "详细描述这张图片"
    media(img)
    on_chunk fn(chunk) {
        print(chunk, flush=false)
    }
    on_complete fn(full_text) {
        print("\n完成!")
    }
```

## 中文别名

所有多模态相关函数都支持中文别名：

| 英文 | 中文 |
|------|------|
| `media()` | `媒体()` |
| `media_base64()` | `媒体base64()` |
| `is_media()` | `是媒体()` |
| `media_type()` | `媒体类型()` |
| `on_media fn(...)` | `处理媒体 fn(...)` |
| `on_generate fn(...)` | `生成 fn(...)` |

## 完整示例

### 图像分析 Agent

```helen
agent 图像分析助手 {
    description "专业的图像分析助手，能够理解和描述图像内容"
    model "qwen-vl-max"
    
    main {
        # 从用户获取图像路径
        let image_path = input("请输入图像路径: ")
        
        # 创建 MediaPart
        let img = media(image_path)
        
        # 分析图像
        let analysis = llm act "请详细描述这张图片的内容、风格和可能的用途"
            media(img)
        
        print("\n分析结果:\n" + analysis)
    }
}
```

### 多图像比较 Agent

```helen
agent 图像比较器 {
    description "比较多个图像的差异"
    
    main {
        let img1 = media("before.png")
        let img2 = media("after.png")
        
        let comparison = llm act "比较这两张图片，指出主要的变化和差异"
            media(img1, img2)
        
        print(comparison)
    }
}
```

### 图像生成 Agent

```helen
agent 创意图像生成器 {
    description "根据文字描述生成图像"
    
    main {
        let description = input("描述你想生成的图像: ")
        
        let result = llm act description
            on_generate fn(params) {
                # 这里应该调用实际的图像生成 API
                # 示例使用占位符
                let prompt = params["prompt"]
                let api_response = call_dalle_api(prompt, size="1024x1024")
                
                # 返回生成的图像
                返回 media(api_response["url"])
            }
        
        print("生成的图像: " + result)
    }
}
```

### 自定义 Provider 适配

```helen
agent 自定义媒体处理 {
    main {
        let img = media("chart.png")
        
        let result = llm act "分析这个图表"
            media(img)
            provider("custom_provider")
            on_media fn(parts, provider) {
                # 为自定义 provider 转换格式
                返回 parts.map(fn(part) {
                    返回 {
                        "type": "media",
                        "mime_type": part.mime,
                        "data": part.content,
                        "encoding": "base64"
                    }
                })
            }
    }
}
```

## TranscriptStore 集成

多模态内容完全集成到 TranscriptStore SSOT：

- **自动持久化**：所有多模态对话自动保存到 `~/.helen/sessions/`
- **大媒体外部存储**：≥1MB 的 base64 媒体自动提取到外部文件（Phase 3）
- **会话恢复**：重启 Helen 后可以完整恢复包含媒体的对话
- **压缩安全**：上下文压缩正确处理多模态内容

配置外部存储阈值（`~/.helen/config.yaml`）：

```yaml
multimodal:
  max_media_size_mb: 20              # 单个媒体最大 20MB
  max_media_per_request: 10          # 每次最多 10 个媒体
  media_external_threshold_mb: 1.0   # ≥1MB 提取到外部文件
  media_cache_dir: "~/.helen/media_cache"
  video_frame_interval: 1.0          # 视频抽帧间隔（秒）
```

## 最佳实践

### 1. 使用默认适配器

大多数情况下，使用默认的 OpenAI 兼容适配器即可：

```helen
# 推荐：使用默认适配器
let result = llm act "分析图片" media(img)

# 仅在需要自定义时使用 on_media
let result = llm act "分析图片" 
    media(img)
    on_media fn(parts, provider) { ... }
```

### 2. 合理管理大媒体

大媒体文件会自动外部存储，但可以手动控制：

```helen
# 小图像（<1MB）：内联存储
let small_img = media("icon.png")

# 大图像（≥1MB）：自动外部存储
let large_img = media("high_res_photo.png")
```

### 3. 错误处理

处理可能的媒体加载错误：

```helen
尝试 {
    let img = media("可能不存在的文件.png")
    let result = llm act "分析" media(img)
} 捕获 err {
    print("媒体加载失败: " + err.消息)
}
```

### 4. 批量处理

处理多个媒体时，注意 provider 限制：

```helen
# 默认每次最多 10 个媒体
let images = [media("img1.png"), media("img2.png"), ...]
让 result = llm act "分析这些图片" media(images...)
```

## 限制和注意事项

1. **Provider 支持**：并非所有 LLM provider 都支持多模态，需要确认 provider 能力
2. **文件大小**：默认单个媒体最大 20MB，可在配置中调整
3. **网络媒体**：URL 媒体需要网络访问，可能需要处理超时
4. **格式兼容**：不同 provider 支持的媒体格式不同，需要适当转换

## 相关资源

- [TranscriptStore 用户指南](../docs/transcript_store_user_guide.md)
- [helen-syntax skill](../skills/software-development/helen-syntax/SKILL.md)
- [helen-stdlib skill](../skills/software-development/helen-stdlib/SKILL.md)
- [多模态提案](../reports/multimodal-proposal.md)
