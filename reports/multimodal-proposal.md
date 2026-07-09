# Helen `llm act` 多模态支持方案

> 日期：2026-07-08
> 状态：提案（Proposal）
> 版本：v1.17 候选

---

## 1. 问题陈述

当前 Helen 的 `llm act` 仅支持纯文本 prompt，无法处理图片、视频、音频等多媒体内容。而主流 LLM（GPT-4o、Claude 3.5 Sonnet、Gemini 1.5）均已支持多模态输入。本文总结业界主流方案，结合 Helen 当前架构，提出完整的多模态支持方案。

---

## 2. 当前架构分析

### 2.1 `llm act` 完整执行链

```
源码: llm act "描述这张图片" image("./photo.png")
      ↓
Lexer/Parser: LlmActExprNode(prompt, on_chunk, on_complete)
      ↓
Interpreter: visit_llm_act_expr()
  ├── 评估 prompt → str
  ├── 构建 system_prompt（4段模板）
  ├── 构建 user_prompt = prompt（字符串）
  ├── 记录 history（Message content=str）
  ├── 准备历史消息 [{role, content:str}]
  └── 调用 llm_runtime.act(prompt, tools, model, ...)
      ↓
HttpLLMRuntime.act() / act_stream()
  ├── 构建 messages = [
  │     {role:system, content:str},
  │     ...history...,
  │     {role:user, content:str}  ← 当前只支持字符串
  │   ]
  ├── POST {base_url}/chat/completions
  └── 返回 LLMResponse(content=str, tool_calls, usage)
```

### 2.2 需要修改的关键数据点

| 层 | 文件 | 当前状态 | 需要变更 |
|---|---|---|---|
| AST | `ast.py` | `LlmActExprNode(prompt, on_chunk, on_complete)` | 新增 `media` 字段 |
| Parser | `parser.py` | 仅解析 prompt 表达式 | 解析 `image()`/`video()` 等 |
| Interpreter | `llm_mixin.py` | prompt 评估为字符串 | 评估为 content parts 数组 |
| LLMRuntime | `llm_runtime.py` | `act(prompt: str, ...)` | `act(prompt: str\|ContentParts, ...)` |
| HttpLLM | `http_llm.py` | `content: str` | `content: str \| [ContentPart]` |
| History | `history.py` | `Message.content: str` | 支持多模态内容 |
| TranscriptStore | `transcript_store.py` | 纯文本序列化 | 支持多模态序列化 |
| Stdlib | `stdlib/` | 无多媒体函数 | 新增 `image()`/`video()`/`audio()` |

---

## 3. 业界主流方案总结

### 3.1 OpenAI（GPT-4o / GPT-4V）

```json
{
  "role": "user",
  "content": [
    {"type": "text", "text": "这张图片里有什么？"},
    {"type": "image_url", "image_url": {"url": "data:image/png;base64,iVBOR..."}}
  ]
}
```

- **图片传入方式**：base64 data URI 或 HTTP URL
- **视频支持**：无原生支持，需拆帧后传多张图片
- **Token 计算**：根据图片分辨率和 detail 参数（low/high/auto）计算

### 3.2 Anthropic Claude 3.5

```json
{
  "role": "user",
  "content": [
    {"type": "text", "text": "描述这张图片"},
    {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": "..."}}
  ]
}
```

- **图片传入方式**：base64 内联（首选）或 URL
- **视频支持**：拆帧 + 音频轨道分离
- **限制**：单图最大 5MB，最多 20 张图
- **Token 计算**：基于图片像素数（width × height / 750）

### 3.3 Google Gemini 1.5

```json
{
  "role": "user",
  "parts": [
    {"text": "这段视频说了什么？"},
    {"inline_data": {"mime_type": "video/mp4", "data": "base64..."}}
  ]
}
```

- **原生视频支持**：直接传 video/mp4 的 base64
- **音频支持**：audio/mp3, audio/wav
- **优势**：真正的原生多模态，无需拆帧

### 3.4 主流框架抽象

**LangChain**：`HumanMessage(content=[{"type": "image_url", "image_url": {...}}])`
**LlamaIndex**：`ImageNode` + `TextNode` 组合

### 3.5 通用设计模式

| 模式 | 描述 | 代表 |
|------|------|------|
| Content Parts 数组 | `content` 从字符串升级为 `[{type, ...}]` 数组 | OpenAI, Claude, Gemini |
| 双模兼容 | 纯文本时仍可用字符串，多模态时用数组 | 所有主流 API |
| 媒体类型枚举 | `image_url`, `image_base64`, `video`, `audio` | 各 API 略有不同 |
| URL + Base64 双通道 | 大图用 URL 引用，小图用 base64 内联 | OpenAI, Claude |

---

## 4. Helen 多模态解决方案

### 4.1 设计原则

1. **渐进增强**：纯文本用法完全不变，`llm act "hello"` 依然工作
2. **函数式媒体构造**：通过 stdlib 函数 `image()`、`video()`、`audio()` 构建媒体对象
3. **OpenAI 兼容**：Content Parts 格式对齐 OpenAI 标准，同时适配 Claude/Gemini
4. ** Helen 风格**：支持中英文双语关键字

### 4.2 语法设计

#### 4.2.1 基础用法

```helen
// 纯文本（不变）
result = llm act "翻译这段话"

// 单张图片
result = llm act "描述这张图片" image("./photo.png")

// 多张图片
result = llm act "比较这两张图" image("./a.png") image("./b.png")

// 图片 + 文本混合
result = llm act "这张发票的金额是多少？" image("./invoice.jpg")

// 从 URL 加载
result = llm act "网页截图里有什么" image("https://example.com/screenshot.png")

// 视频
result = llm act "描述这段视频" video("./demo.mp4")

// 音频
result = llm act "这段音频说了什么" audio("./meeting.mp3")
```

#### 4.2.2 Base64 内联

```helen
// 从 base64 字符串
encoded = read_file_base64("./photo.png")
result = llm act "描述这张图片" image_base64(encoded, "image/png")
```

#### 4.2.3 带参数的媒体

```helen
// 图片带 detail 参数（OpenAI）
result = llm act "详细描述" image("./photo.png", detail: "high")

// 图片带描述（alt text，用于 accessibility）
result = llm act "分析图表" image("./chart.png", alt: "2024年销售趋势图")
```

#### 4.2.4 Agent 中使用

```helen
agent vision_assistant {
    description "图片分析助手"
    model "gpt-4o"
    
    main {
        img = image("./uploads/photo.png")
        analysis = llm act "分析这张图片的内容" img
        return analysis
    }
}
```

#### 4.2.5 中文关键字

```helen
结果 = llm act "描述这张图片" 图片("./photo.png")
结果 = llm act "这段视频讲了什么" 视频("./demo.mp4")
结果 = llm act "这段音频说了什么" 音频("./meeting.mp3")
```

### 4.3 新增 Stdlib 函数

| 函数 | 返回类型 | 描述 |
|------|---------|------|
| `image(source, detail?, alt?)` | `MediaPart` | 构建图片内容块（自动识别 URL/path/base64） |
| `video(source, mime_type?)` | `MediaPart` | 构建视频内容块 |
| `audio(source, mime_type?)` | `MediaPart` | 构建音频内容块 |
| `image_base64(data, mime_type)` | `MediaPart` | 从 base64 构建图片 |
| `media_url(url)` | `MediaPart` | 从 URL 构建通用媒体块 |
| `is_media(value)` | `bool` | 判断值是否为 MediaPart |
| `media_type(value)` | `str` | 返回媒体类型（image/video/audio） |

中文别名：`图片()`, `视频()`, `音频()`, `图片base64()`, `媒体URL()`, `是媒体()`, `媒体类型()`

### 4.4 AST 变更

```python
@dataclass(frozen=True)
class LlmActExprNode(ExpressionNode):
    prompt: ExpressionNode | None     # 原有
    media: list[ExpressionNode]       # 新增：媒体表达式列表
    on_chunk: ExpressionNode | None   # 原有
    on_complete: ExpressionNode | None # 原有
```

### 4.5 Parser 变更

在 `_llm_act_expr` 和 `_llm_act_stmt` 中，解析 prompt 后，循环识别 `image()`、`video()`、`audio()` 等函数调用：

```python
def _llm_act_expr(self):
    self._consume('llm')
    self._consume('act')
    prompt = self._expression() if not self._check('on_chunk', 'on_complete', 'image', 'video', 'audio', '\n') else None
    media = []
    while self._check('image', 'video', 'audio', '图片', '视频', '音频'):
        media.append(self._media_expr())
    on_chunk = ...
    on_complete = ...
    return LlmActExprNode(prompt, media, on_chunk, on_complete)
```

### 4.6 HttpLLMRuntime 变更

#### 4.6.1 Message Content 格式升级

从 `content: str` 升级为支持两种格式：

```python
# 纯文本（向后兼容）
{"role": "user", "content": "hello"}

# 多模态（Content Parts 数组）
{"role": "user", "content": [
    {"type": "text", "text": "描述这张图片"},
    {"type": "image_url", "image_url": {"url": "https://..."}}
]}
```

#### 4.6.2 多模态内容构建

```python
def _build_content_parts(prompt: str, media: list[MediaPart]) -> list[dict]:
    parts = [{"type": "text", "text": prompt}]
    for m in media:
        if m.type == "image":
            if m.source.startswith(("http://", "https://")):
                parts.append({"type": "image_url", "image_url": {"url": m.source}})
            else:
                b64 = _file_to_base64(m.source)
                mime = _guess_mime(m.source)
                parts.append({
                    "type": "image_url",
                    "image_url": {"url": f"data:{mime};base64,{b64}"}
                })
        elif m.type == "video":
            # OpenAI 不支持原生视频，需拆帧
            # Claude 需要拆帧 + 分离音频
            frames = _extract_video_frames(m.source)
            for frame in frames:
                parts.append({"type": "image_url", "image_url": {"url": frame}})
        elif m.type == "audio":
            parts.append({
                "type": "input_audio",
                "input_audio": {"data": _file_to_base64(m.source), "format": m.mime}
            })
    return parts
```

#### 4.6.3 提供商适配

```python
def _adapt_for_provider(self, parts: list[dict], provider: str) -> list[dict]:
    """适配不同 LLM 提供商的多模态格式"""
    if provider == "anthropic":
        return self._adapt_for_claude(parts)
    elif provider == "google":
        return self._adapt_for_gemini(parts)
    else:
        return self._adapt_for_openai(parts)

def _adapt_for_claude(self, parts):
    """OpenAI 格式 → Claude 格式"""
    result = []
    for p in parts:
        if p["type"] == "text":
            result.append({"type": "text", "text": p["text"]})
        elif p["type"] == "image_url":
            url = p["image_url"]["url"]
            if url.startswith("data:"):
                mime, data = _parse_data_uri(url)
                result.append({
                    "type": "image",
                    "source": {"type": "base64", "media_type": mime, "data": data}
                })
            else:
                result.append({"type": "image", "source": {"type": "url", "url": url}})
    return result
```

### 4.7 工具返回多模态

工具执行结果也可以返回图片（如 `read_file` 读取图片、`web_fetch` 抓取截图）：

```helen
agent screenshot_analyzer {
    description "分析网页截图"
    tools [web_fetch, read_file]
    
    main {
        // 工具返回的截图自动作为图片内容块传入
        analysis = llm act "分析这个网页的截图" image("./screenshot.png")
        return analysis
    }
}
```

### 4.8 History 与 TranscriptStore 变更

#### 4.8.1 Message.content 类型扩展

```python
@dataclass
class Message:
    role: str
    content: str | list[ContentPart]   # 扩展
    timestamp: float
    # ...
```

#### 4.8.2 序列化格式

JSONL 后端：
```json
{"role": "user", "content": [{"type": "text", "text": "描述"}, {"type": "image_url", "url": "data:..."}]}
```

对于大图片，TranscriptStore 应支持外部存储引用：
```json
{"role": "user", "content": [{"type": "text", "text": "描述"}, {"type": "image_ref", "path": "~/.helen/sessions/xxx/media/001.png"}]}
```

#### 4.8.3 Token 估算（基于各提供商官方公式）

```python
def estimate_image_tokens(width: int, height: int, provider: str, detail: str = "high") -> int:
    """根据提供商估算图片 token 消耗"""
    if provider == "openai":
        if detail == "low":
            return 85  # 固定 85 tokens
        # detail: high — 基于 512×512 tile
        # 1. 缩放使最长边 ≤ 2048px，最短边 ≤ 768px
        # 2. 计算 tile 数
        scale = min(2048 / max(width, height), 768 / min(width, height), 1.0)
        w, h = int(width * scale), int(height * scale)
        tiles = math.ceil(w / 512) * math.ceil(h / 512)
        return 85 + 170 * tiles

    elif provider == "anthropic":
        # Claude: 28×28 pixel patches
        return math.ceil(width / 28) * math.ceil(height / 28)
        # 简化近似: (width × height) / 750

    elif provider == "google":
        # Gemini: 258 tokens per 384×384 tile
        tiles = math.ceil(width / 384) * math.ceil(height / 384)
        return 258 * tiles

def estimate_video_tokens(duration_sec: int, fps: int, provider: str) -> int:
    """估算视频 token 消耗"""
    if provider == "google":
        # Gemini: 258 tokens/frame (medium), 66-70 tokens/frame (low)
        return duration_sec * fps * 258
    else:
        # OpenAI/Claude: 需要拆帧，每帧按图片计算
        return duration_sec * fps * 256  # 每帧约 256 tokens

def estimate_audio_tokens(duration_sec: int, provider: str) -> int:
    """估算音频 token 消耗"""
    if provider == "openai":
        return int(duration_sec * 10)   # 1 token per 100ms
    elif provider == "google":
        return int(duration_sec * 32)   # 32 tokens per second
    else:
        return 0  # Claude 暂不支持原生音频
```

#### 4.8.4 各提供商成本对比（每张图片）

| 提供商 / 模型 | Tokens/张 | 成本/张 | 相对成本 |
|-------------|----------|--------|---------|
| **Gemini 2.5 Flash** | 258-560 | ~$0.0001-0.002 | 🟢 最便宜（10-40×） |
| **GPT-4o (low detail)** | 85 | ~$0.0002 | 🟢 很便宜 |
| **GPT-4o (high detail)** | 765-1,105 | ~$0.002-0.003 | 🟡 中等 |
| **Claude 3.5 Haiku** | ~1,300-6,636 | ~$0.001-0.007 | 🟡 中等 |
| **Claude 3.5 Sonnet** | ~1,300-6,636 | ~$0.004-0.020 | 🔴 最贵 |

**关键发现：**
- Gemini 图片处理成本是竞争对手的 1/10 到 1/40
- Claude 同一张图片生成的 token 是 OpenAI 的 3-6 倍
- GPT-4o-mini 有 33.33× token 乘数，视觉任务反而比 GPT-4o 更贵
- 建议：视觉密集任务用 Gemini，精度优先用 GPT-4o/Claude

#### 4.8.5 各提供商能力矩阵

| 能力 | OpenAI | Claude | Gemini |
|------|--------|--------|--------|
| 图片输入 | ✅ base64/URL | ✅ base64/URL | ✅ base64/URL/File API |
| 视频输入 | ❌ 需拆帧 | ❌ 需拆帧 | ✅ 原生支持（最长1小时） |
| 音频输入 | ✅ `input_audio` | ❌ | ✅ 原生支持 |
| 最大图片 | 2048px 最长边 | 8000×8000px | 无明确限制 |
| 图片大小限制 | ~20MB | 5MB | 100MB inline / 2GB File API |
| 成本优化参数 | `detail: low/high` | 自动缩放 | `media_resolution: low/medium` |

### 4.9 配置扩展

```yaml
# ~/.helen/config.yaml
multimodal:
  enabled: true
  max_image_size_mb: 20          # 单图最大 20MB
  max_images_per_request: 10     # 每次最多 10 张图
  video_frame_interval: 1.0      # 视频抽帧间隔（秒）
  auto_compress_images: true     # 自动压缩超大图片
  media_cache_dir: "~/.helen/media_cache"  # 媒体缓存目录
```

---

## 5. 实现路线图

### Phase 1：图片支持（v1.17-alpha）
- [ ] `image()` stdlib 函数 + `MediaPart` 数据类型
- [ ] Parser 支持 `image()` 作为 `llm act` 的参数
- [ ] HttpLLMRuntime 多模态 content 构建
- [ ] OpenAI 格式适配
- [ ] 基础测试（50+ test cases）

### Phase 2：视频与音频（v1.17-beta）
- [ ] `video()` / `audio()` stdlib 函数
- [ ] 视频拆帧工具（基于 ffmpeg 或纯 Python）
- [ ] 音频 token 估算
- [ ] Gemini 原生视频支持

### Phase 3：Claude/Gemini 适配（v1.17-rc）
- [ ] Anthropic Claude 多模态格式适配
- [ ] Google Gemini 多模态格式适配
- [ ] 提供商能力检测（是否支持 vision）

### Phase 4：Transcript 与 History（v1.17）
- [ ] Message.content 多模态序列化
- [ ] TranscriptStore 媒体引用存储
- [ ] History 多模态压缩策略
- [ ] Token 计算扩展

### Phase 5：中文与工具链（v1.17）
- [ ] 中文关键字：`图片()`、`视频()`、`音频()`
- [ ] 工具返回多模态内容
- [ ] REPL `:media` 命令预览媒体
- [ ] 文档与示例

---

## 6. 设计取舍

| 取舍 | 选择 | 理由 |
|------|------|------|
| 函数式 vs 内联语法 | 函数式 `image()` | Helen 已有函数调用风格，无需新语法；易于扩展 |
| Base64 vs URL | 两者都支持 | 小图内联减少延迟，大图/网络图用 URL |
| 视频拆帧 vs 原生 | 拆帧 + 原生双模式 | 拆帧兼容 OpenAI，原生支持 Gemini |
| Token 计算 | 估算而非精确 | 各提供商算法不同，估算够用，精确计算交给 API |
| 媒体存储 | 外部引用 + 内联混合 | TranscriptStore 不膨胀，小媒体内联快速 |

---

## 7. 最佳实践

### 7.1 Base64 vs URL

| 方面 | Base64 | URL |
|------|--------|-----|
| 大小开销 | +33% 编码膨胀 | 无开销 |
| 适用场景 | 小图、本地文件、隐私敏感 | 大图、CDN 托管 |
| 最大大小 | ~20MB（JSON 限制） | 无实际限制 |
| 缓存 | 不可缓存 | CDN 可缓存 |
| Token 成本 | 相同 | 相同 |

**建议：** 公网/CDN 图片用 URL，本地/私密图片用 base64。Helen 的 `image()` 函数自动判断：以 `http://`/`https://` 开头用 URL，否则读文件转 base64。

### 7.2 分辨率优化

**策略：** 发送前预缩放到最佳尺寸，减少 token 消耗。

```python
# OpenAI 最佳尺寸
# pre-scale to ~1086×768 → quality/cost 最优
# 小于 512×512 也至少消耗 255 tokens（1 tile 最低消费）

# Claude 最佳尺寸
# 最长边 > 1568px 自动缩放，建议预缩放到 ~1500px

# Gemini 最佳尺寸
# media_resolution: "low" → 66-70 tokens/frame（vs 258 medium，4× 差距）
```

### 7.3 Vision 降级策略

```helen
// 当模型不支持 vision 时自动降级
agent smart_vision {
    model "gpt-4o-mini"  // 不支持 vision
    
    main {
        // 自动检测：若模型不支持 vision，
        // 先用图片描述模型转文本，再传给目标模型
        result = llm act "分析这张图" image("./chart.png")
        // 内部流程：
        // 1. 检测 gpt-4o-mini 不支持 vision
        // 2. 自动调用 gpt-4o 生成图片描述
        // 3. 将描述作为文本传给 gpt-4o-mini
    }
}
```

### 7.4 安全考虑

| 风险 | 缓解措施 |
|------|---------|
| 图片注入攻击 | 验证图片内容，不仅检查 MIME 类型 |
| URL SSRF | 验证 URL，阻止内网 IP |
| Base64 大小限制 | 强制最大 20MB 防止 DoS |
| 图片中 PII | 处理前脱敏 |

---

## 8. 风险与缓解（实现层面）

| 风险 | 缓解措施 |
|------|---------|
| 大图片导致 context 爆炸 | `max_image_size_mb` 限制 + 自动压缩 |
| 模型不支持 vision | 能力检测 + 降级为纯文本 + 警告 |
| Base64 序列化膨胀 | TranscriptStore 外部引用 |
| 视频帧数过多 | `video_frame_interval` 控制抽帧密度 |
| 向后兼容 | 纯文本路径完全不变，`content: str` 依然有效 |

---

## 9. 示例程序

### 9.1 图片描述生成器

```helen
agent image_describer {
    description "生成图片描述"
    model "gpt-4o"
    
    main {
        path = input("请输入图片路径: ")
        img = image(path)
        description = llm act "用中文详细描述这张图片的内容" img
        println("描述: {description}")
    }
}
```

### 9.2 多图对比分析

```helen
agent compare_images {
    description "对比分析两张图片"
    model "claude-3-5-sonnet"
    
    main {
        img1 = image("./before.png")
        img2 = image("./after.png")
        result = llm act "对比这两张图片，列出所有不同之处" img1 img2
        println(result)
    }
}
```

### 9.3 视频摘要

```helen
agent video_summarizer {
    description "视频内容摘要"
    model "gemini-1.5-pro"
    
    main {
        vid = video("./presentation.mp4")
        summary = llm act "用 3 句话总结这段视频的主要内容" vid
        println("摘要: {summary}")
    }
}
```

### 9.4 发票 OCR

```helen
// 发票识别
result = llm act "提取发票信息，返回JSON格式" image("./invoice.jpg")
data = json_parse(result)
println("金额: {data['total_amount']}")
println("日期: {data['date']}")
```

---

## 10. 扩展方向：多模态输出（文生图/文生视频）与 RAG（v1.18+）

当前方案（v1.17）解决「多模态输入」（媒体 → LLM 理解）。多模态输出（文本 → 生成媒体）是方向完全不同的扩展。

### 10.1 多模态输出：业界协议现状

#### 图像生成：`/v1/images/generations` 已成事实标准

```json
POST /v1/images/generations
{
  "model": "dall-e-3",
  "prompt": "A sunset over mountains",
  "size": "1024x1024",
  "quality": "hd",
  "n": 1
}
// Response:
{"data": [{"url": "https://...generated-image.png"}]}
```

采用此标准的服务商：OpenAI DALL-E、Azure OpenAI、Google Imagen（`/v1beta/openai/images/generations`）、LocalAI、Stability AI（兼容模式）等。

#### 视频生成：尚无统一标准

| 服务商 | 协议 | 异步模式 | 定价参考 |
|--------|------|---------|---------|
| **Seedance（火山引擎）** | 自有 REST API | 轮询 + Webhook | ~¥1/秒（15s ≈ ¥15） |
| **Kling（快手可灵）** | 自有 REST API | 轮询 + Webhook | 按次计费 |
| **Runway Gen-3** | 自有 REST API | 轮询 | ~$0.05/秒 |
| **Pika** | 自有 REST API | 轮询 | 按次计费 |
| **Midjourney** | 无官方 API | 第三方轮询 | N/A |

#### 异步处理三大模式

| 模式 | 机制 | 使用者 |
|------|------|--------|
| **轮询** | POST → task_id → GET /tasks/{id} | Kling, Runway, Pika, Seedance |
| **Webhook** | POST + callback_url → 主动推送 | Replicate, fal.ai, Seedance |
| **SSE/流式** | 极少用于媒体生成 | 主要用于文本 |

### 10.2 Helen 多模态输出设计设想（v1.18）

```helen
// 文生图 — 类似 llm act 的语法风格
img = generate image "一只在月球上弹吉他的猫" size("1024x1024") quality("hd")
save(img, "./cat_moon.png")

// 文生视频
video = generate video "日落延时摄影，从城市到天边" duration(10) model("seedance")
save(video, "./sunset.mp4")

// 图片编辑（基于参考图）
edited = generate image "把背景换成海滩" from("./original.png")
save(edited, "./edited.png")

// 中文
图片 = 生成图片 "星空下的古城" 尺寸("1024x1024")
视频 = 生成视频 "海浪拍打礁石" 时长(10) 模型("可灵")
```

### 10.3 与多模态输入的关系

```helen
// 输入 + 输出组合：看图生图
agent style_transfer {
    main {
        // 输入：理解参考图片
        desc = llm act "描述这张图的风格" image("./reference.png")
        // 输出：基于描述生成新图
        result = generate image desc size("1024x1024")
        save(result, "./styled.png")
    }
}
```

### 10.4 实现架构

```
Helen 侧统一接口：
  generate image <prompt> [options]
  generate video <prompt> [options]

内部适配器层：
  ├── OpenAIAdapter     → POST /v1/images/generations
  ├── SeedanceAdapter   → POST /v1/videos/text2video → 轮询/Webhook
  ├── KlingAdapter      → POST /v1/videos/generations → 轮询
  ├── RunwayAdapter     → POST /v1/generations → 轮询
  └── StabilityAdapter  → POST /v2beta/stable-image/generate

共享基础设施（复用 v1.17）：
  - 提供商配置 & 认证
  - 错误处理 & 重试
  - 媒体缓存（~/.helen/media_cache/）
```

### 10.5 多模态 RAG（v1.19+）

LlamaIndex 的多模态 RAG 核心模式：

| 模式 | 架构 | 适用场景 |
|------|------|---------|
| 双向量库 | Text Store (OpenAI) + Image Store (CLIP) + 融合检索 | 文档+图片混合检索 |
| 统一向量空间 | Cohere Embed 4 统一 text+image 到同一空间 | 简化架构，无需双库 |
| ColPali 页面即图片 | VLM 直接对页面编码，无需 OCR | 复杂排版文档 |

```helen
// 未来 Helen RAG API 设想
import knowledge_base

kb = knowledge_base("./docs", embed_model: "cohere-embed-4")
results = kb.query("架构图中的微服务划分" top_k: 5)
// results 包含 TextNode + ImageNode

context = kb.format_context(results)
answer = llm act "根据以下资料回答问题" context
```

### 10.6 完整实现层次

```
Level 0 (v1.17)：llm act 多模态输入 — 本方案核心
Level 1 (v1.18)：generate image/video 多模态输出 — 文生图/视频
Level 2 (v1.19)：知识库 + 检索（RAG 基础）
Level 3 (v1.20)：多模态 RAG — 自动图文检索 + 组装
Level 4 (v1.21)：ColPali 集成 — 无需 OCR 的文档理解
```

---

## 11. 总结

本方案以「函数式媒体构造 + Content Parts 数组 + 提供商适配」为核心，在保持 Helen 简洁风格的同时，全面支持图片、视频、音频的多模态处理。方案设计为 5 个阶段渐进实施，每个阶段独立可用，风险可控。

关键创新点：
1. **`image()` 函数式构造** — 无需新语法，符合 Helen 函数调用风格
2. **双模兼容** — 纯文本路径完全不变，向后 100% 兼容
3. **提供商适配层** — 统一 Helen 侧接口，自动适配 OpenAI/Claude/Gemini 格式差异
4. **TranscriptStore 媒体引用** — 大媒体外部存储，避免会话文件膨胀
