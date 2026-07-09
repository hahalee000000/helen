# Helen 多模态支持方案 v2

> 日期：2026-07-09
> 状态：提案（Proposal）
> 版本：v1.17 候选
> 替代：`reports/multimodal-proposal.md`（v1）

---

## 1. 问题陈述

Helen 的 `llm act` 目前仅支持纯文本，无法处理图片、视频、音频，也无法调用文生图、文生视频等生成服务。

**核心挑战不是功能缺失，而是协议不稳定：**

- **多模态输入**：OpenAI、Claude、Gemini 三家格式各不相同，且仍在演进
- **文生图**：`/v1/images/generations` 已成事实标准（OpenAI、Imagen、Stability 兼容），但细节差异仍存
- **文生视频**：Seedance、Kling、Runway、Pika 各自私有协议，轮询/Webhook 模式混杂，**没有统一标准**

在这种情况下，把任何特定协议固化进语法（如引入 `image()`、`video()` 等特殊关键字），都会在协议变化时迫使语言本身做出破坏性变更。

---

## 2. 设计原则

| 原则 | 含义 |
|------|------|
| **语法最小变更** | 不引入新的媒体专用关键字；复用 `llm act` 现有回调模式 |
| **协议无感知** | Helen 核心不内置任何 provider 的格式细节 |
| **回调即适配** | 所有 provider 差异通过用户提供的回调函数处理 |
| **统一模型** | 多模态输入、文生图、文生视频用同一套回调机制解决 |
| **向后兼容** | 纯文本 `llm act "..."` 完全不变 |
| **通用性** | 未来出现新模态或新协议，无需修改语言核心 |

---

## 3. 核心机制：两个新回调槽位

在 `on_chunk` / `on_complete` 之外，为 `llm act` 新增两个可选回调：

| 回调 | 触发时机 | 用途 |
|------|---------|------|
| `on_media` | 多模态内容需要编码发送给 LLM 时 | 将媒体内容转换为 provider 特定格式 |
| `on_generate` | 需要调用生成类 API（文生图/视频等）时 | 封装完整的生成 API 交互逻辑 |

**设计哲学**：Helen runtime 负责调度，不负责翻译。协议的细节由用户的回调代码决定。

---

## 4. 多模态输入（`on_media`）

### 4.1 基本思路

`media()` 是一个普通 stdlib 函数（不是语法关键字），返回 `MediaPart` 对象。当 `MediaPart` 出现在 `llm act` 的参数中时，runtime 收集所有媒体对象，调用 `on_media` 回调来构造 provider 特定的 content parts。

**如果用户不提供 `on_media`**，runtime 使用默认的 OpenAI 兼容格式（覆盖绝大多数场景）。

### 4.2 语法示例

```helen
// 最简单用法 — 默认适配器处理（OpenAI 兼容格式）
result = llm act "描述这张图片" media("./photo.png")

// 多图
result = llm act "比较这两张图" media("./a.png") media("./b.png")

// 指定 provider 触发对应的默认适配
result = llm act "描述这张图" media("./photo.png") provider("anthropic")

// 完全自定义适配（覆盖默认行为）
result = llm act "描述这张图" media("./photo.png")
    on_media fn(parts, provider) {
        if provider == "gemini" {
            return parts.map(fn(p) {
                {type: "inline_data", mime_type: p.mime, data: p.base64}
            })
        }
        // 默认 fallback：OpenAI 兼容格式
        return parts.map(fn(p) {
            {type: "image_url", image_url: {url: "data:{p.mime};base64,{p.base64}"}}
        })
    }
```

### 4.3 中文关键字

```helen
// media() 的中文别名
结果 = llm act "描述这张图" 媒体("./photo.png")

// 完整中文
结果 = llm act "描述这张图" 媒体("./photo.png")
    处理媒体 fn(parts, provider) { ... }
```

### 4.4 `media()` stdlib 函数

```helen
// 从文件路径（自动识别 MIME 类型）
img = media("./photo.png")              // → MediaPart{source: "file", path: "...", mime: "image/png"}

// 从 URL
img = media("https://example.com/a.png") // → MediaPart{source: "url", url: "...", mime: "image/png"}

// 从 base64
img = media_base64(encoded_data, "image/png")  // → MediaPart{source: "base64", data: "...", mime: "image/png"}

// 显式指定类型
vid = media("./clip.mp4", type: "video")
aud = media("./speech.mp3", type: "audio")
```

| 函数 | 返回类型 | 描述 |
|------|---------|------|
| `media(source, type?)` | `MediaPart` | 从路径/URL 构建媒体对象，自动识别类型 |
| `media_base64(data, mime, type?)` | `MediaPart` | 从 base64 数据构建媒体对象 |
| `is_media(value)` | `bool` | 判断值是否为 MediaPart |
| `media_type(value)` | `str?` | 返回媒体类型（image/video/audio），非媒体返回 null |

中文别名：`媒体()`, `媒体base64()`, `是媒体()`, `媒体类型()`

### 4.5 `MediaPart` 数据类型

```python
@dataclass(frozen=True)
class MediaPart:
    source: str          # "file" | "url" | "base64"
    content: bytes | str # 文件内容 / URL / base64 字符串
    mime: str            # "image/png", "video/mp4", "audio/mp3" 等
    media_type: str      # "image" | "video" | "audio"
    metadata: dict       # 额外参数（detail, alt 等）
```

`MediaPart` 是一等公民，可以赋值给变量、作为函数参数传递、存入列表。

---

## 5. 多模态输出（`on_generate`）

### 5.1 基本思路

文生图、文生视频等生成任务通过 `on_generate` 回调处理。**Helen 不引入新的 `generate image` / `generate video` 语法**，而是复用 `llm act`：

- `on_generate` 回调将生成能力**注册为工具**
- LLM 在工具循环中决定是否调用
- 调用时执行回调，返回结果（文本或 `MediaPart`）

这保持了 `llm act` 作为 LLM 工具循环的本质，生成只是多了一个可用工具。

### 5.2 语法示例

```helen
// 文生图 — 通过工具注册
result = llm act "生成一张月球上弹吉他的猫的图片，保存到 ./cat.png"
    provider("openai")
    on_generate fn(params) {
        // params 包含 LLM 传入的参数（由工具 schema 定义）
        resp = http_post("https://api.openai.com/v1/images/generations", {
            model: "dall-e-3",
            prompt: params.prompt,
            size: params.size || "1024x1024"
        })
        return media(resp.data[0].url, type: "image")
    }

// 文生视频 — 异步轮询
result = llm act "生成一段日落延时摄影视频，保存到 ./sunset.mp4"
    provider("seedance")
    on_generate fn(params) {
        // 创建任务
        task = http_post("https://api.seedance.com/v1/videos/text2video", {
            prompt: params.prompt,
            duration: params.duration || 5
        })
        // 轮询直到完成
        loop {
            status = http_get("https://api.seedance.com/v1/tasks/{task.id}")
            if status.status == "completed" {
                return media(status.video_url, type: "video")
            }
            if status.status == "failed" {
                throw GenerateError("视频生成失败: {status.error}")
            }
            sleep(5)
        }
    }

// 图片编辑（基于参考图）
result = llm act "把这张图的背景换成海滩" media("./original.png")
    on_generate fn(params, ref_media) {
        resp = http_post("https://api.example.com/v1/images/edits", {
            prompt: params.prompt,
            image: ref_media.base64
        })
        return media(resp.data[0].url, type: "image")
    }
```

### 5.3 `on_generate` 的工具注册机制

当 `on_generate` 存在时，runtime 自动将生成能力注册为一个工具：

```json
{
  "name": "generate_media",
  "description": "根据描述生成图片/视频。用户会在 prompt 中指定保存路径。",
  "parameters": {
    "type": "object",
    "properties": {
      "prompt": {"type": "string", "description": "生成内容的详细描述"},
      "size": {"type": "string", "description": "尺寸，如 1024x1024"},
      "duration": {"type": "integer", "description": "视频时长（秒）"}
    },
    "required": ["prompt"]
  }
}
```

LLM 在 `llm act` 的工具循环中，根据用户意图决定是否调用 `generate_media`。调用时执行 `on_generate` 回调，返回 `MediaPart` 或文本结果。

### 5.4 多个生成工具

同一个 `llm act` 可以注册多个不同的生成工具：

```helen
result = llm act "先用文字描述这张图的风格，然后生成一张新图"
    media("./reference.png")
    on_generate fn(params) {
        // 文生图工具
        resp = http_post("https://api.openai.com/v1/images/generations", {...})
        return media(resp.data[0].url, type: "image")
    }
    on_generate fn(params) {
        // 文生视频工具（同名时自动区分参数 schema）
        resp = http_post("https://api.seedance.com/v1/videos/text2video", {...})
        return media(resp.video_url, type: "video")
    }
    tools [web_search, read_file]
```

---

## 6. 输入 + 输出组合

多模态输入和输出可以自由组合：

```helen
// 看图生图：分析参考图 → 基于分析结果生成新图
agent style_transfer {
    description "风格迁移"
    model "gpt-4o"
    tools [write_file]

    main {
        result = llm act "分析这张图的风格，然后用 generate_media 工具生成一张同风格的新图，主题是'星空下的古城'"
            media("./reference.png")
            provider("openai")
            on_generate fn(params) {
                resp = http_post("https://api.openai.com/v1/images/generations", {
                    model: "dall-e-3",
                    prompt: params.prompt,
                    size: "1024x1024"
                })
                return media(resp.data[0].url, type: "image")
            }
        println(result)
    }
}

// 视频理解 + 文生图
agent video_to_poster {
    main {
        result = llm act "看完这段视频，提取最精彩的画面，用 generate_media 生成海报图"
            media("./clip.mp4", type: "video")
            on_generate fn(params) {
                resp = http_post("https://api.openai.com/v1/images/generations", {
                    model: "dall-e-3",
                    prompt: params.prompt
                })
                return media(resp.data[0].url, type: "image")
            }
        println(result)
    }
}
```

---

## 7. AST 与 Parser 变更

### 7.1 AST

`LlmActExprNode` 新增两个字段，变更极小：

```python
@dataclass(frozen=True)
class LlmActExprNode(ExpressionNode):
    prompt: ExpressionNode          # 原有（现在可返回包含 MediaPart 的混合结果）
    media: list[ExpressionNode]     # 新增：媒体表达式列表（可为空）
    on_chunk: ExpressionNode | None        # 原有
    on_complete: ExpressionNode | None     # 原有
    on_media: ExpressionNode | None        # 新增：多模态输入适配器
    on_generate: list[ExpressionNode]      # 新增：生成工具回调（可多个）
    provider: ExpressionNode | None        # 新增：provider 提示（可选）
```

### 7.2 Parser

在 `_llm_act_expr` 中，解析 prompt 后，循环识别以下子句（顺序不固定）：

```python
def _parse_llm_act_suffix(self):
    media = []
    on_chunk = None
    on_complete = None
    on_media = None
    on_generate = []
    provider = None

    while not self._at_end() and not self._check('newline', 'eof'):
        if self._check('media', '媒体') and self._peek(1).type == 'lparen':
            media.append(self._expression())       # media(...) 函数调用
        elif self._check('on_media', '处理媒体'):
            self._advance()
            on_media = self._fn_expression()       # on_media fn(...) {...}
        elif self._check('on_generate', '生成'):
            self._advance()
            on_generate.append(self._fn_expression())
        elif self._check('on_chunk'):
            self._advance()
            on_chunk = self._fn_expression()
        elif self._check('on_complete'):
            self._advance()
            on_complete = self._fn_expression()
        elif self._check('provider'):
            self._advance()
            provider = self._expression()
        else:
            break

    return LlmActExprNode(..., media, on_chunk, on_complete, on_media, on_generate, provider)
```

**关键**：没有引入任何媒体专用关键字（`image`/`video`/`audio` 都不是关键字）。`media()` 是普通函数调用，`on_media`/`on_generate` 是回调子句，和 `on_chunk`/`on_complete` 完全同构。

---

## 8. Runtime 变更

### 8.1 Interpreter（`llm_mixin.py`）

```python
def visit_llm_act_expr(self, node):
    prompt = self.evaluate(node.prompt)          # 可能是 str 或混合内容
    media_parts = [self.evaluate(m) for m in node.media]

    # 构造消息
    text_content = prompt if isinstance(prompt, str) else str(prompt)
    user_message = self._build_user_message(text_content, media_parts, node.on_media)

    # 注册生成工具
    tools = list(node.tools or [])
    for gen_fn in node.on_generate:
        tools.append(self._build_generate_tool(gen_fn, node.provider))

    # 正常工具循环（与现有逻辑完全一致）
    return self._run_tool_loop(user_message, tools, node.on_chunk, node.on_complete)

def _build_user_message(self, text, media_parts, on_media_fn):
    if not media_parts:
        return {"role": "user", "content": text}

    # 有媒体内容：调用 on_media 适配器，或使用默认
    if on_media_fn:
        content_parts = self.call_function(on_media_fn, [media_parts, self.current_provider])
    else:
        content_parts = self._default_media_adapter(media_parts, self.current_provider)

    return {"role": "user", "content": [{"type": "text", "text": text}] + content_parts}

def _default_media_adapter(self, media_parts, provider):
    """默认适配器：OpenAI 兼容格式，适用于绝大多数 provider"""
    parts = []
    for m in media_parts:
        if m.media_type == "image":
            url = m.content if m.source == "url" else f"data:{m.mime};base64,{m.content}"
            parts.append({"type": "image_url", "image_url": {"url": url}})
        elif m.media_type == "video":
            # 默认拆帧（OpenAI/Claude 风格）
            frames = self._extract_frames(m.content)
            for frame in frames:
                parts.append({"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{frame}"}})
        elif m.media_type == "audio":
            parts.append({"type": "input_audio", "input_audio": {"data": m.content, "format": m.mime}})
    return parts
```

### 8.2 `HttpLLMRuntime` 变更最小化

由于 `on_media` 回调已经在 interpreter 层把媒体内容转换为 provider 特定格式，`HttpLLMRuntime` 只需要支持 `content: str | list[dict]` 双格式即可，**不需要内置任何 provider 适配逻辑**：

```python
# http_llm.py 变更极小
def _send(self, messages, ...):
    # messages 中的 content 已经是 provider 需要的格式（由 on_media 处理）
    # 无需任何适配层
    ...
```

### 8.3 生成工具的注册与执行

```python
def _build_generate_tool(self, gen_fn, provider_hint):
    return Tool(
        name="generate_media",
        description="根据描述生成图片或视频",
        parameters={...},  # 标准 JSON Schema
        execute=lambda params: self._execute_generate(gen_fn, params, provider_hint)
    )

def _execute_generate(self, gen_fn, params, provider_hint):
    result = self.call_function(gen_fn, [params])
    if isinstance(result, MediaPart):
        # 保存媒体到本地，返回路径信息给 LLM
        path = self._save_media(result)
        return f"媒体已保存到: {path}"
    return str(result)
```

---

## 9. Provider 参考（Skill 文档内容）

各 provider 的标准回调写法作为 **skill 文档**提供，不内置于 runtime。用户 `load_skill "multimodal-providers"` 即可查阅复制。

### 9.1 多模态输入：各 provider 的 `on_media` 写法

**OpenAI（默认，无需自定义）：**
```helen
// 默认适配器已处理，直接这样写即可
result = llm act "描述这张图" media("./photo.png")
```

**Anthropic Claude：**
```helen
result = llm act "描述这张图" media("./photo.png")
    on_media fn(parts, provider) {
        return parts.map(fn(p) {
            if p.source == "url" {
                {type: "image", source: {type: "url", url: p.content}}
            } else {
                {type: "image", source: {type: "base64", media_type: p.mime, data: p.content}}
            }
        })
    }
```

**Google Gemini：**
```helen
result = llm act "描述这张图" media("./photo.png")
    on_media fn(parts, provider) {
        return parts.map(fn(p) {
            {inline_data: {mime_type: p.mime, data: p.content}}
        })
    }
```

### 9.2 文生图：各 provider 的 `on_generate` 写法

**OpenAI DALL-E：**
```helen
result = llm act "生成一张日出的图片，保存到 ./sunrise.png"
    on_generate fn(params) {
        resp = http_post("{env.LLM_BASE_URL}/images/generations", {
            model: "dall-e-3",
            prompt: params.prompt,
            size: params.size || "1024x1024",
            quality: params.quality || "standard"
        })
        return media(resp.data[0].url, type: "image")
    }
```

**Stability AI：**
```helen
result = llm act "生成一张水彩风格的山景，保存到 ./mountain.png"
    on_generate fn(params) {
        resp = http_post("https://api.stability.ai/v2beta/stable-image/generate/core", {
            prompt: params.prompt,
            output_format: "png"
        }, headers: {"Authorization": "Bearer {env.STABILITY_KEY}"})
        return media_base64(resp.image, "image/png", type: "image")
    }
```

### 9.3 文生视频：各 provider 的 `on_generate` 写法

**Seedance（火山引擎）— 轮询模式：**
```helen
result = llm act "生成一段海浪拍打的视频，10秒，保存到 ./waves.mp4"
    on_generate fn(params) {
        task = http_post("https://visual.volcengineapi.com/v1/videos/text2video", {
            prompt: params.prompt,
            duration: params.duration || 5
        }, headers: {"Authorization": "Bearer {env.SEEDANCE_KEY}"})

        loop {
            status = http_get("https://visual.volcengineapi.com/v1/tasks/{task.task_id}")
            if status.status == "completed" {
                return media(status.video_url, type: "video")
            }
            if status.status == "failed" {
                throw GenerateError("生成失败: {status.error}")
            }
            sleep(5)
        }
    }
```

**Kling（快手可灵）— Webhook 模式示例：**
```helen
result = llm act "生成一段城市夜景延时摄影，保存到 ./city.mp4"
    on_generate fn(params) {
        task = http_post("https://api.kling.com/v1/videos/generations", {
            prompt: params.prompt,
            callback_url: env.KLING_WEBHOOK_URL
        }, headers: {"Authorization": "Bearer {env.KLING_KEY}"})
        // Webhook 模式：结果通过回调 URL 推送，需要额外的接收逻辑
        // 这里简化为轮询兜底
        loop {
            status = http_get("https://api.kling.com/v1/tasks/{task.id}")
            if status.status == "succeeded" {
                return media(status.works[0].resource_resource, type: "video")
            }
            sleep(10)
        }
    }
```

---

## 10. History 与 TranscriptStore

### 10.1 `Message.content` 扩展

```python
@dataclass
class Message:
    role: str
    content: str | list[dict]   # 支持纯文本或 content parts 数组
    timestamp: float
    ...
```

### 10.2 TranscriptStore 序列化

**小媒体（< 1MB）**：直接内联到 JSONL
```json
{"role": "user", "content": [
    {"type": "text", "text": "描述这张图"},
    {"type": "image_url", "url": "data:image/png;base64,iVBOR..."}
]}
```

**大媒体（≥ 1MB）**：外部引用
```json
{"role": "user", "content": [
    {"type": "text", "text": "描述这张图"},
    {"type": "media_ref", "path": "~/.helen/sessions/<id>/media/001.png", "mime": "image/png"}
]}
```

这与原方案完全一致，不受回调机制影响。

---

## 11. 配置

```yaml
# ~/.helen/config.yaml
multimodal:
  max_media_size_mb: 20          # 单个媒体最大 20MB
  max_media_per_request: 10      # 每次最多 10 个媒体
  video_frame_interval: 1.0      # 默认视频抽帧间隔（秒）
  media_cache_dir: "~/.helen/media_cache"
  media_session_dir: "~/.helen/sessions/<id>/media/"  # 大媒体外部存储
```

---

## 12. 实现路线图

### Phase 1：基础框架（v1.17-alpha）
- [ ] `MediaPart` 数据类型
- [ ] `media()` / `media_base64()` / `is_media()` / `media_type()` stdlib 函数
- [ ] Parser 扩展：识别 `on_media` / `on_generate` / `provider` 子句
- [ ] Interpreter：`_build_user_message` + 默认 `on_media` 适配器
- [ ] 基础测试（50+ test cases）

### Phase 2：文生图支持（v1.17-beta）
- [ ] `on_generate` 工具注册机制
- [ ] 生成工具执行与结果处理
- [ ] 媒体结果保存到本地
- [ ] OpenAI DALL-E 示例验证

### Phase 3：TranscriptStore 集成（v1.17-rc）
- [ ] `Message.content` 支持 list[dict] 格式
- [ ] 大媒体外部存储引用
- [ ] JSONL 序列化/反序列化

### Phase 4：Skill 文档与示例（v1.17）
- [ ] `multimodal-providers` skill（各 provider 的标准回调写法）
- [ ] 示例程序集（图片描述、多图对比、文生图、文生视频）
- [ ] 中文别名支持

---

## 13. 完整示例

### 13.1 图片描述（最简单用法）

```helen
agent image_describer {
    description "图片描述生成器"
    model "gpt-4o"

    main {
        path = input("请输入图片路径: ")
        description = llm act "用中文详细描述这张图片的内容" media(path)
        println("描述: {description}")
    }
}
```

### 13.2 跨 Provider 图片分析（带自定义适配器）

```helen
// 同一个 agent，切换 model 时自动适配
agent cross_provider_vision {
    description "跨 provider 图片分析"

    main {
        analysis = llm act "分析这张图表的数据趋势" media("./chart.png")
            provider("anthropic")
            on_media fn(parts, provider) {
                // Claude 格式
                parts.map(fn(p) {
                    {type: "image", source: {type: "base64", media_type: p.mime, data: p.content}}
                })
            }
        println(analysis)
    }
}
```

### 13.3 文生图 Agent

```helen
agent image_creator {
    description "文生图助手"
    model "gpt-4o"
    tools [write_file]

    main {
        user_prompt = input("描述你想生成的图片: ")
        result = llm act "用户想要生成图片: {user_prompt}，请使用 generate_media 工具生成，并保存到 ./output.png"
            on_generate fn(params) {
                resp = http_post("{env.LLM_BASE_URL}/images/generations", {
                    model: "dall-e-3",
                    prompt: params.prompt,
                    size: "1024x1024"
                })
                img_data = http_get(resp.data[0].url)
                write_file("./output.png", img_data)
                return "图片已保存到 ./output.png"
            }
        println(result)
    }
}
```

### 13.4 视频理解 + 图片生成（组合）

```helen
agent video_poster_maker {
    description "从视频生成海报"
    model "gpt-4o"

    main {
        result = llm act "观看这段视频，提取最具代表性的画面描述，然后用 generate_media 工具生成海报图"
            media("./promo.mp4", type: "video")
            provider("openai")
            on_media fn(parts, provider) {
                // Gemini 原生视频格式（如果用 Gemini 模型）
                parts.map(fn(p) {
                    {inline_data: {mime_type: p.mime, data: p.content}}
                })
            }
            on_generate fn(params) {
                resp = http_post("{env.LLM_BASE_URL}/images/generations", {
                    model: "dall-e-3",
                    prompt: params.prompt,
                    size: "1024x1024"
                })
                return media(resp.data[0].url, type: "image")
            }
        println(result)
    }
}
```

### 13.5 发票 OCR

```helen
agent invoice_reader {
    description "发票识别"
    model "gpt-4o"

    main {
        result = llm act "提取这张发票中的所有信息，返回 JSON 格式" media("./invoice.jpg")
        data = json_parse(result)
        println("金额: {data['total_amount']}")
        println("日期: {data['date']}")
        println("购买方: {data['buyer']}")
    }
}
```

---

## 14. 设计取舍总结

| 取舍 | 选择（v2） | 原方案（v1） | 理由 |
|------|----------|------------|------|
| 媒体传入方式 | `media()` 普通函数 | `image()`/`video()` 解析器识别 | 不引入新关键字，语法变更最小 |
| Provider 适配 | `on_media` 用户回调 | runtime 内置 `_adapt_for_*` | 协议变化不影响语言核心 |
| 文生图/视频 | `on_generate` 工具回调 | 新增 `generate image/video` 语法 | 复用现有机制，不新增语法结构 |
| 未来新模态 | 用户写新回调即可 | 需要修改语言+runtime | 通用性显著更高 |
| 代码复杂度 | runtime 精简，逻辑在 skill | runtime 膨胀，维护成本高 | 符合 DSL 定位：提供原语，不封装协议 |
| 入门门槛 | 简单场景零回调，复杂场景查 skill | 始终用内置语法 | 渐进复杂度，符合 Helen 风格 |

---

## 15. 风险与缓解

| 风险 | 缓解措施 |
|------|---------|
| 用户不知道如何写 `on_media` | `multimodal-providers` skill 提供所有主流 provider 的完整模板 |
| 默认适配器不满足特殊需求 | `on_media` 允许完全覆盖默认行为 |
| `on_generate` 轮询逻辑复杂 | skill 文档提供标准轮询模板，用户直接复用 |
| `MediaPart` 序列化膨胀 | TranscriptStore 大媒体外部存储（与 v1 方案相同） |
| 工具注册 schema 不够灵活 | Phase 2 可扩展：允许用户在 `on_generate` 旁自定义工具参数 |

---

## 16. 与 v1 方案的核心差异

| 维度 | v1（原方案） | v2（本方案） |
|------|------------|------------|
| **语法变更量** | 新增 `image()`/`video()`/`audio()`/`generate image`/`generate video` 等解析器识别 | 仅新增 `on_media`/`on_generate` 两个回调子句 |
| **Provider 适配位置** | 硬编码在 runtime（`_adapt_for_claude` 等） | 用户回调 + skill 文档 |
| **新协议出现时** | 需要修改 Helen 代码发新版 | 用户更新 skill 或回调即可 |
| **文生视频** | 需要独立语法 `generate video`，各家协议不同难以统一 | 统一通过 `on_generate` 回调处理 |
| **核心抽象** | 媒体类型（image/video/audio）| 交互模式（输入适配 / 输出生成）|
| **符合 Helen 哲学** | 部分（函数式构造符合，provider 适配层不符合）| 完全（回调是一等公民，协议是用户关注点）|

---

## 17. 总结

本方案以「**回调即适配器**」为核心，仅扩展 `llm act` 两个可选回调槽位（`on_media` + `on_generate`），即统一解决多模态输入、文生图、文生视频三类问题。

关键创新点：
1. **`media()` 是普通函数**，不是语法关键字 — 解析器变更最小化
2. **`on_media` 替代 provider 适配层** — Helen 核心不硬编码任何协议细节
3. **`on_generate` 替代 `generate image/video` 新语法** — 协议未统一时，把适配权交给用户
4. **同一个 `llm act` 统一输入+输出** — 无新增语法结构，学习成本最低
5. **Skill 文档替代内置代码** — provider 参考写法随 skill 分发，随协议变化随时更新

Helen 作为 DSL 的职责是提供原语（media 类型、回调槽位），而非封装协议（provider 适配层）。协议在变，原语不变。
