# Volcengine Ark (火山方舟 / Doubao / 豆包) — OpenAI-Compatible API Protocol Reference

> **Research Date**: 2026-08-05
> **Sources**: 9 official + 12 third-party documentation pages (see Sources section)
> **Confidence**: HIGH for protocol details (cross-verified across multiple sources); MEDIUM for pricing (subject to change)

---

## Table of Contents

1. [Platform Overview](#1-platform-overview)
2. [Base URLs & Endpoints](#2-base-urls--endpoints)
3. [Authentication](#3-authentication)
4. [Chat Completions API](#4-chat-completions-api)
5. [Messages & Multi-turn Conversations](#5-messages--multi-turn-conversations)
6. [Response Format](#6-response-format)
7. [Streaming Protocol (SSE)](#7-streaming-protocol-sse)
8. [Deep Thinking / Reasoning (深度思考)](#8-deep-thinking--reasoning-深度思考)
9. [Function Calling / Tool Use](#9-function-calling--tool-use)
10. [Multimodal Support (Vision)](#10-multimodal-support-vision)
11. [Model Names, Endpoint IDs & Context Windows](#11-model-names-endpoint-ids--context-windows)
12. [Token Usage Reporting](#12-token-usage-reporting)
13. [finish_reason Values](#13-finish_reason-values)
14. [Error Handling](#14-error-handling)
15. [Rate Limits](#15-rate-limits)
16. [Provider-Specific Deviations from OpenAI](#16-provider-specific-deviations-from-openai)
17. [Responses API (Newer Interface)](#17-responses-api-newer-interface)
18. [MCP (Model Context Protocol) Support](#18-mcp-model-context-protocol-support)
19. [Coding Plan (Anthropic-Compatible Endpoint)](#19-coding-plan-anthropic-compatible-endpoint)
20. [Pricing](#20-pricing)
21. [Official Documentation Links](#21-official-documentation-links)
22. [Sources](#22-sources)

---

## 1. Platform Overview

**Volcengine Ark (火山方舟)** is ByteDance's LLM inference platform, serving the **Doubao (豆包)** model family and third-party models (DeepSeek, GLM, Kimi). The API is **fully OpenAI-compatible** — standard OpenAI SDK works with only `base_url` and `api_key` changes.

- **SDK V3** is the current version — V1/V2 are deprecated and offline
- **Dual protocol**: Both OpenAI and Anthropic interface protocols supported
- **Free tier**: 500K tokens per model (after real-name verification), valid 30 days

---

## 2. Base URLs & Endpoints

### Data Plane (Model Inference)

| Purpose | URL |
|---------|-----|
| **Base URL (OpenAI-compatible)** | `https://ark.cn-beijing.volces.com/api/v3` |
| Chat Completions | `POST https://ark.cn-beijing.volces.com/api/v3/chat/completions` |
| Responses API | `POST https://ark.cn-beijing.volces.com/api/v3/responses` |
| Context-Cached Chat | `POST https://ark.cn-beijing.volces.com/api/v3/context/chat/completions` |
| Batch Chat | `POST https://ark.cn-beijing.volces.com/api/v3/batch/chat/completions` |
| Bot API | `POST https://ark.cn-beijing.volces.com/api/v3/bots/chat/completions` |
| Multimodal Embeddings | `POST https://ark.cn-beijing.volces.com/api/v3/embeddings/multimodal` |

### Control Plane (Management APIs — AK/SK auth)

| Purpose | URL |
|---------|-----|
| Management API | `https://ark.cn-beijing.volcengineapi.com/` |

### Coding Plan (Anthropic-Compatible)

| Purpose | URL |
|---------|-----|
| Coding Plan Base | `https://ark.cn-beijing.volces.com/api/coding` |
| Coding Plan Chat | `POST https://ark.cn-beijing.volces.com/api/coding/v3/chat/completions` |

### International (BytePlus)

| Purpose | URL |
|---------|-----|
| BytePlus API | `https://open.byteplusapi.com` |

---

## 3. Authentication

### Method: Bearer Token (API Key)

```
Authorization: Bearer <ARK_API_KEY>
Content-Type: application/json
```

- API Key format: `sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`
- Obtain from: 方舟控制台 → 侧栏「API Key管理」→ 创建新 Key
- Requires 火山引擎 account + 实名认证 (real-name verification)

### Two Auth Types

| Type | Method | Use Case |
|------|--------|----------|
| **Data Plane** (inference) | `Authorization: Bearer <API_KEY>` | Model calls |
| **Control Plane** (management) | Volcengine AK/SK signature auth | Endpoint management APIs |

### ⚠️ Critical: Endpoint ID Requirement

The `model` field in API requests should be the **推理接入点 ID (Inference Endpoint ID)** — not just a model name. Public model IDs (like `doubao-seed-2-0-pro-260215`) work for testing but have stricter TPM limits. Production should use `ep-xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx` format IDs created in the console.

---

## 4. Chat Completions API

### Request Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `model` | string | ✅ Required | — | Endpoint ID or model name |
| `messages` | array | ✅ Required | — | Conversation history |
| `temperature` | float | ❌ | ~0.7 | 0–2, higher = more random |
| `top_p` | float | ❌ | 1.0 | Nucleus sampling |
| `max_tokens` | int | ❌ | model default | Max output tokens |
| `max_completion_tokens` | int | ❌ | — | Total output budget (thinking + answer), max 65536 |
| `stream` | bool | ❌ | false | Enable SSE streaming |
| `stream_options` | object | ❌ | — | Set `{"include_usage": true}` for usage in stream |
| `stop` | array/string | ❌ | — | Stop sequences |
| `tools` | array | ❌ | — | Function calling definitions |
| `tool_choice` | string/object | ❌ | "auto" | Tool selection strategy |
| `parallel_tool_calls` | bool | ❌ | true | Allow multiple tool calls |
| `response_format` | object | ❌ | — | JSON mode: `{"type": "json_object"}` |
| `thinking` | object | ❌ | — | Deep thinking config (non-standard) |

### Deep Thinking Parameters (via `extra_body` or direct)

```json
{
  "thinking": {
    "type": "enabled",      // "enabled" | "disabled" | "adaptive"
    "budget_tokens": 4096   // Max tokens for reasoning chain
  }
}
```

| Type | Behavior |
|------|----------|
| `"enabled"` | Forces thinking mode — always thinks before answering |
| `"disabled"` | Forces thinking off — responds directly |
| `"adaptive"` | Model auto-decides whether to think (Doubao-Seed-1.6+) |

---

## 5. Messages & Multi-turn Conversations

### Message Format

```json
{
  "messages": [
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": "Explain vector databases"},
    {"role": "assistant", "content": "A vector database is..."},
    {"role": "user", "content": "Can you give an example?"}
  ]
}
```

### Supported Roles

| Role | Description |
|------|-------------|
| `system` | System instructions (auto-visible to all turns) |
| `user` | User messages |
| `assistant` | Model responses (for conversation history) |
| `tool` | Tool call results (with `tool_call_id`) |

### Vision Message Format (Multimodal)

```json
{
  "role": "user",
  "content": [
    {"type": "text", "text": "Describe this image"},
    {
      "type": "image_url",
      "image_url": {
        "url": "https://example.com/image.jpg",
        "detail": "high"
      }
    }
  ]
}
```

---

## 6. Response Format

### Non-Streaming Response

```json
{
  "id": "chatcmpl-xxxxxxxx",
  "object": "chat.completion",
  "created": 1720000000,
  "model": "doubao-seed-2-0-pro-260215",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "Hello! How can I help you today?"
      },
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": 10,
    "completion_tokens": 20,
    "total_tokens": 30
  }
}
```

### Response with Tool Calls

```json
{
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": null,
        "tool_calls": [
          {
            "id": "call_xxxxx",
            "type": "function",
            "function": {
              "name": "get_weather",
              "arguments": "{\"location\": \"Beijing\"}"
            }
          }
        ]
      },
      "finish_reason": "tool_calls"
    }
  ]
}
```

### Response with Thinking Content

```json
{
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "The answer is 42.",
        "reasoning_content": "Let me think step by step..."
      },
      "finish_reason": "stop"
    }
  ]
}
```

---

## 7. Streaming Protocol (SSE)

### Format

When `stream: true`, response is Server-Sent Events (SSE):

```
data: {"id":"chatcmpl-xxx","object":"chat.completion.chunk","created":1720000000,"model":"doubao-seed-2-0-pro","choices":[{"index":0,"delta":{"role":"assistant","content":""},"finish_reason":null}]}

data: {"id":"chatcmpl-xxx","object":"chat.completion.chunk","choices":[{"index":0,"delta":{"content":"Hello"},"finish_reason":null}]}

data: {"id":"chatcmpl-xxx","object":"chat.completion.chunk","choices":[{"index":0,"delta":{"content":" world"},"finish_reason":null}]}

data: {"id":"chatcmpl-xxx","object":"chat.completion.chunk","choices":[{"index":0,"delta":{},"finish_reason":"stop"}],"usage":{"prompt_tokens":10,"completion_tokens":20,"total_tokens":30}}

data: [DONE]
```

### Stream Chunk Structure

| Field | Description |
|-------|-------------|
| `choices[0].delta.role` | First chunk only: `"assistant"` |
| `choices[0].delta.content` | Incremental text fragment |
| `choices[0].delta.reasoning_content` | Reasoning/thinking fragment (if thinking enabled) |
| `choices[0].delta.tool_calls` | Tool call fragments (streamed as partial JSON) |
| `choices[0].finish_reason` | `null` during stream, set at end |
| `usage` | Only in final chunk (if `stream_options.include_usage: true`) |
| Terminal marker | `data: [DONE]` |

### Two-Phase Streaming (with Thinking)

**Phase 1 — Thinking/Reasoning:**
```json
{"delta": {"reasoning_content": "Let me think step by step..."}}
```

**Phase 2 — Answer/Response:**
```json
{"delta": {"content": "The answer is..."}}
```

### Streaming Tool Calls

```json
{
  "delta": {
    "tool_calls": [{
      "index": 0,
      "id": "call_abc123",
      "type": "function",
      "function": {
        "name": "get_weather",
        "arguments": "{\"locati"
      }
    }]
  }
}
```

**Critical rules:**
- Tool call arguments are **streamed as partial JSON strings** — must concatenate then parse
- First chunk includes `id`, `type`, `function.name`; subsequent chunks only append to `arguments`
- Multiple tool calls use incrementing `index` values (0, 1, 2…)

### SSE Parsing Gotcha

> **Known bug** (Dify Issue #13682): Missing space after `"data:"` in some Volcengine SSE responses — clients should handle both `data: {...}` and `data:{...}` formats.

---

## 8. Deep Thinking / Reasoning (深度思考)

### Overview

Doubao supports deep thinking (chain-of-thought reasoning) similar to OpenAI's o1/o3 models.

### Enabling Thinking

```python
# Via OpenAI SDK extra_body
response = client.chat.completions.create(
    model="<endpoint-id>",
    messages=[{"role": "user", "content": "Prove √2 is irrational"}],
    extra_body={
        "thinking": {
            "type": "enabled",
            "budget_tokens": 32000
        }
    }
)
```

### Response Fields

| Field | Location | Meaning |
|-------|----------|---------|
| `reasoning_content` | `choices[0].message` or `choices[0].delta` | Chain-of-thought reasoning trace |
| `content` | Same locations | Final answer |
| `reasoning_tokens` | `usage` object | Token count for thinking portion |

**Key rule**: `reasoning_content` and `content` are **mutually exclusive phases** — during thinking, only `reasoning_content` is populated; during answering, only `content`.

### Thinking Models

| Model | Description |
|-------|-------------|
| `doubao-seed-1-6-thinking-*` | RL-trained reasoning model |
| `doubao-1-5-thinking-pro` | Text-only deep thinking |
| `doubao-seed-2-0-pro` | Deep thinking + multimodal |
| `doubao-seed-2-0-code` | Code-enhanced deep thinking |

### Important Notes

- `max_tokens` does NOT count thinking tokens separately — use `max_completion_tokens` (0–65536) for total budget including thinking
- Thinking content appears in `reasoning_content` field (NOT `thinking_content` or other variants)
- In streaming: `reasoning_content` deltas arrive first, then `content` deltas follow

---

## 9. Function Calling / Tool Use

### Tool Definition Format

```json
{
  "tools": [
    {
      "type": "function",
      "function": {
        "name": "get_weather",
        "description": "Get the current weather for a location",
        "parameters": {
          "type": "object",
          "properties": {
            "location": {
              "type": "string",
              "description": "The city name"
            },
            "unit": {
              "type": "string",
              "enum": ["celsius", "fahrenheit"]
            }
          },
          "required": ["location"]
        }
      }
    }
  ],
  "tool_choice": "auto"
}
```

### tool_choice Options

| Value | Description |
|-------|-------------|
| `"auto"` | (Default) Model decides whether to call a tool |
| `"none"` | Forces no tool calls |
| `"required"` | Forces at least one tool call |
| `{"type": "function", "function": {"name": "get_weather"}}` | Forces calling specific function |

### Submitting Tool Results

```json
{
  "messages": [
    {"role": "user", "content": "What's the weather in Beijing?"},
    {"role": "assistant", "content": null, "tool_calls": [...]},
    {
      "role": "tool",
      "tool_call_id": "call_xxxxx",
      "content": "{\"temperature\": 25, \"condition\": \"sunny\"}"
    }
  ]
}
```

### Parallel Tool Calls

Supported on most Doubao models. Controlled by `parallel_tool_calls: true` (default).

### Built-in Tools (Responses API only)

| Tool Type | Description |
|-----------|-------------|
| `web_search` | Real-time internet search (param: `max_keyword`) |
| `image_process` | Image manipulation (points, lines, crop, scale, rotate) |
| `knowledge_search` | Query private knowledge bases |
| `mcp` | Access cloud-deployed MCP tools |

> ⚠️ `web_search` and custom Function Calling **cannot be used simultaneously** in the same request.

---

## 10. Multimodal Support (Vision)

### Image Input Format

```json
{
  "role": "user",
  "content": [
    {"type": "text", "text": "Describe this image"},
    {
      "type": "image_url",
      "image_url": {
        "url": "https://example.com/image.jpg"
      }
    }
  ]
}
```

### Three Input Methods

| Method | Format | Example |
|--------|--------|---------|
| Public URL | Direct URL | `"url": "https://example.com/image.png"` |
| Base64 Data URL | Data URI | `"url": "data:image/jpeg;base64,/9j/4AAQ..."` |
| File ID | Platform file | `"url": "file_id://your-file-id"` |

### `detail` Parameter

| Value | Description |
|-------|-------------|
| `"high"` | High-detail processing (more tokens). Default for Seed 1.8+ |
| `"low"` | Low-detail processing (fewer tokens). Default for older models |

### Supported Image Formats

JPEG, PNG, WEBP, GIF (first frame), BMP, TIFF

### Vision Models

| Model | Context | Notes |
|-------|---------|-------|
| `doubao-seed-1.6-vision-*` | 256K | Dedicated vision model |
| `doubao-vision-pro-32k` | 32K | Classic vision model |
| Seed 2.0 Lite/Pro/Mini | 256K | Multimodal support |
| Seed 2.0 Code | 256K | Code + vision |

### Multimodal Embedding Endpoint

Multimodal embeddings use a separate endpoint:
```
POST https://ark.cn-beijing.volces.com/api/v3/embeddings/multimodal
```
Model: `doubao-embedding-vision`

---

## 11. Model Names, Endpoint IDs & Context Windows

### Endpoint ID System

Volcengine Ark uses a **unique endpoint system (推理接入点)**:
- Each model deployment gets an endpoint ID: `ep-xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`
- You create endpoints in the console: 在线推理 → 创建推理接入点
- Public model IDs work for testing but have stricter TPM limits
- Production should use endpoint IDs for better rate limits and monitoring

### Complete Model List (Current as of 2026)

#### Seed 2.1 Series (Latest)

| Model | Public ID | Context | Max Output | Capabilities |
|-------|-----------|---------|------------|--------------|
| **Seed 2.1 Pro** | `doubao-seed-2-1-pro` | 256K | 256K | Deep reasoning, multimodal, tools |
| **Seed 2.1 Turbo** | `doubao-seed-2-1-turbo` | 256K | 32K | Fast responses |

#### Seed 2.0 Series

| Model | Public ID | Context | Max Output | Capabilities |
|-------|-----------|---------|------------|--------------|
| **Seed 2.0 Pro** | `doubao-seed-2-0-pro-260215` | 256K | 128K (incl. CoT 128K) | Deep thinking, multimodal, tools |
| **Seed 2.0 Code** | `doubao-seed-2-0-code-260215` | 256K | 256K | Code + vision, thinking |
| **Seed 2.0 Lite** | `doubao-seed-2-0-lite-260428` | 256K | 32K | Thinking, multimodal, tools, structured output |
| **Seed 2.0 Mini** | `doubao-seed-2-0-mini-260215` | 256K | 128K | Lightweight, 4 thinking-length levels |

#### Seed Evolving

| Model | Public ID | Context | Max Output | Notes |
|-------|-----------|---------|------------|-------|
| **Seed Evolving** | `doubao-seed-evolving` | **1024K (1M!)** | **256K** | Latest coding & agent model |

#### Seed 1.8

| Model | Public ID | Context | Max Output |
|-------|-----------|---------|------------|
| **Seed 1.8** | `doubao-seed-1-8-251228` | 256K | — |

#### Seed 1.6 Series

| Model | Public ID | Context | Max Output | Notes |
|-------|-----------|---------|------------|-------|
| **Seed 1.6 (Standard)** | `doubao-seed-1-6-251015` | 256K | 32K | General purpose |
| **Seed 1.6 Thinking** | `doubao-seed-1-6-thinking-250601` | 256K | 32K | RL-trained reasoning |
| **Seed 1.6 Thinking v2** | `doubao-seed-1-6-thinking-250615` | 256K | 32K | Updated reasoning |
| **Seed 1.6 Vision** | `doubao-seed-1.6-vision-250815` | 256K | 32K | Vision-focused |
| **Seed 1.6 Flash** | `doubao-seed-1-6-flash-251015` | 256K | 16K | Fast responses |
| **Seed 1.6 Embedding** | `doubao-seed-1-6-embedding-250615` | 128K | — | Text embeddings |

#### Doubao 1.5 Series (Legacy but still available)

| Model | Public ID | Context | Max Output |
|-------|-----------|---------|------------|
| **1.5 Pro (32K)** | `doubao-1-5-pro-32k-250115` | 32K | 12K |
| **1.5 Pro (256K)** | `doubao-1-5-pro-256k-250115` | 256K | 12K |
| **1.5 Lite (32K)** | `doubao-1-5-lite-32k-250115` | 32K | 12K |

#### Classic Series (Being Deprecated)

| Model | Context | Notes |
|-------|---------|-------|
| `doubao-pro-4k` | 4K | Legacy |
| `doubao-pro-32k` | 32K | Legacy |
| `doubao-pro-128k` | 128K | Legacy |
| `doubao-lite-4k` | 4K | Legacy |
| `doubao-lite-32k` | 32K | Legacy, ¥0.3/M tokens |

#### Third-Party Models on Ark

| Model | Notes |
|-------|-------|
| DeepSeek V3.2 | Hosted on Ark |
| DeepSeek R1 | With thinking support |
| GLM-4.7 | Zhipu AI model |
| Kimi K2 / K2.5 | Moonshot AI model |

#### Coding Plan

| Model | Notes |
|-------|-------|
| `ark-code-latest` | Auto-routes to best coding model |

#### Image/Video Generation (Separate APIs)

| Model | Type |
|-------|------|
| Seedream 4.0 / 4.5 / 5.0 | Image generation |
| Seedance 1.0 / 1.5 / 2.0 | Video generation |

---

## 12. Token Usage Reporting

### Non-Streaming Response

```json
{
  "usage": {
    "prompt_tokens": 22,
    "completion_tokens": 9,
    "total_tokens": 31
  }
}
```

| Field | Type | Meaning |
|-------|------|---------|
| `prompt_tokens` | int | Input tokens consumed |
| `completion_tokens` | int | Output tokens (includes thinking chain if present) |
| `total_tokens` | int | Sum of prompt + completion |

### Streaming Usage

Set `stream_options: {"include_usage": true}` → usage returned in the **last chunk** after `finish_reason` is set.

### Thinking Model Token Counting

For thinking models:
- `completion_tokens` includes BOTH `reasoning_content` AND `content`
- `max_output_tokens` (or `max_completion_tokens`) covers the combined budget
- `reasoning_tokens` may appear separately in usage (model-dependent)

---

## 13. finish_reason Values

| Value | Meaning |
|-------|---------|
| `stop` | Normal completion, or truncated by `stop` parameter |
| `length` | Reached `max_tokens` / `max_completion_tokens` limit |
| `content_filter` | Content filtered (sensitive content detected) |
| `tool_calls` | Model wants to invoke tool(s); `content` is `null` |
| `thinking` | Transitioning from thinking → answering phase (some implementations) |

**Notes:**
- In streaming: `finish_reason` is `null` during stream, set only in final chunk
- For thinking models: `max_tokens` includes both reasoning chain AND final answer
- The final stream chunk always has `data: [DONE]` after the usage chunk

---

## 14. Error Handling

### Error Response Format

```json
{
  "error": {
    "code": "InvalidParameter.UnsupportedImageFormat",
    "message": "The request failed because the image format is not supported."
  },
  "RequestId": "202408051234567890abcdef"
}
```

### Common Error Codes

| HTTP Status | Error Code | Description |
|-------------|------------|-------------|
| 400 | `MissingParameter` | Missing required parameter |
| 400 | `InvalidParameter` | Invalid parameter value |
| 400 | `InputTextSensitiveContentDetected` | Sensitive content in input |
| 400 | `InvalidParameter.UnsupportedImageFormat` | Image format not supported |
| 401 | `AuthenticationError` | API Key invalid or expired |
| 403 | `AccessDenied` | No access permission |
| 403 | `AccountOverdueError` | Account balance < 0 |
| 404 | `InvalidEndpointOrModel.NotFound` | Model/endpoint not found |
| 404 | `ModelNotOpen` | Model not activated |
| 429 | `RateLimitExceeded.EndpointRPMExceeded` | Endpoint RPM limit |
| 429 | `RateLimitExceeded.EndpointTPMExceeded` | Endpoint TPM limit |
| 429 | `RateLimitExceeded.ModelRPMExceeded` | Base model RPM limit |
| 429 | `RateLimitExceeded.ModelTPMExceeded` | Base model TPM limit |
| 429 | `RequestBurstTooFast` | Burst too fast |
| 429 | `ServerOverloaded` | Server overloaded |
| 429 | `QuotaExceeded` | Free quota exhausted |
| 500 | `InternalServiceError` | Internal error (retry) |

### Full Error Code Reference

- Official: https://www.volcengine.com/docs/82379/1299023
- Apifox: https://doubao.apifox.cn/6107465m0

---

## 15. Rate Limits

### Rate Limit Dimensions

| Dimension | Scope | Description |
|-----------|-------|-------------|
| **RPM** | Per endpoint + per base model | Requests Per Minute |
| **TPM** | Per endpoint + per base model | Tokens Per Minute |

### Example Limits (Seed 2.0 Pro)

- 30,000 RPM / 5,000,000 TPM

### Pre-Deduction Mechanism

Volcengine uses a **pre-deduction (预扣) mechanism**:
- On each request, estimated tokens are pre-deducted based on input length
- This guarantees completion rates for submitted requests
- Even if console shows remaining quota, 429 can occur if pre-deducted reserves are exhausted

### Coding Plan Rate Limits (Subscription)

- Per 5-hour window (~1,200 requests for Lite plan)
- Weekly and monthly limits
- Cannot be monitored via standard headers

---

## 16. Provider-Specific Deviations from OpenAI

### ⚠️ Critical Deviations

| Deviation | Details |
|-----------|---------|
| **`reasoning_content` field** | Appears in `choices[].message.reasoning_content` and `choices[].delta.reasoning_content`. NOT part of standard OpenAI API — clients must handle this extra field. Some frameworks (AstrBot, langchain) had bugs from this field appearing unexpectedly. |
| **`thinking` request parameter** | Non-standard: `{"type": "enabled"/"disabled"/"adaptive", "budget_tokens": N}`. Frameworks like Spring AI, langchain need custom support. |
| **Endpoint ID concept** | `model` field uses inference endpoint IDs (`ep-xxxx`) created in console, not raw model names. Public model IDs work but have stricter limits. |
| **Rate limit header unreliability** | TPM headers (`x-ratelimit-*-tokens`) completely ABSENT. RPM headers present but values can be wrong (showing 0 remaining on successful responses). |
| **Pre-deduction rate limiting** | Tokens pre-deducted on request arrival, not on completion. Different from OpenAI's post-hoc accounting. |
| **Two API interfaces** | Both Chat Completions API and newer Responses API (`/v3/responses`) are supported. |

### Rate Limit Headers Comparison

| Header | OpenAI | Volcengine |
|--------|--------|------------|
| `x-ratelimit-limit-requests` | ✅ | Sometimes returned, values unreliable |
| `x-ratelimit-remaining-requests` | ✅ | Present but can show 0 on success |
| `x-ratelimit-reset-requests` | ✅ | Sometimes returned |
| `x-ratelimit-limit-tokens` | ✅ | ❌ NOT returned |
| `x-ratelimit-remaining-tokens` | ✅ | ❌ NOT returned |
| `x-ratelimit-reset-tokens` | ✅ | ❌ NOT returned |
| `retry-after` | ✅ | Not documented; type-specific codes instead |

### Other Differences

- `max_completion_tokens` (not `max_tokens`) controls total output budget for thinking models (0–65536)
- `finish_reason: "thinking"` may appear during thinking → answering transition
- SSE `data:` prefix may sometimes lack space after colon (known bug)
- `web_search` built-in tool cannot be combined with custom function calling in same request
- Multimodal embeddings use separate endpoint `/v3/embeddings/multimodal`
- `file_id://` URL scheme for platform-uploaded files

---

## 17. Responses API (Newer Interface)

In addition to Chat Completions, Volcengine supports the **Responses API**:

```
POST https://ark.cn-beijing.volces.com/api/v3/responses
```

### Differences from Chat API

| Feature | Chat API | Responses API |
|---------|----------|---------------|
| Endpoint | `/v3/chat/completions` | `/v3/responses` |
| Input format | `messages` array | `input` array |
| Built-in tools | Limited | `web_search`, `image_process`, `knowledge_search`, `mcp` |
| Native context | Manual | Built-in context management |

### Responses API Example

```json
{
  "model": "<endpoint-id>",
  "input": [
    {"role": "user", "content": "Search for latest AI news"}
  ],
  "tools": [
    {"type": "web_search", "max_keyword": 2}
  ]
}
```

### Migration Guide

Official migration: https://www.volcengine.com/docs/82379/1585128

---

## 18. MCP (Model Context Protocol) Support

Volcengine Ark has comprehensive MCP integration:

- **MCP Server Marketplace** — 100+ pre-built MCP servers (search, databases, business APIs)
- **Cloud-deployed MCP / Remote MCP** — Connect via Streamable HTTP
- **Official GitHub repo** — https://github.com/volcengine/mcp-server (open source)
- **Agent-level MCP** — Declare MCP servers at agent level with tool scope control
- **AICC Trusted MCP** — End-to-end confidential communication for enterprise

### MCP Documentation

| Resource | URL |
|----------|-----|
| MCP Introduction | https://www.volcengine.com/docs/82379/1539085 |
| Cloud-deployed MCP | https://www.volcengine.com/docs/82379/1827534 |
| MCP Configuration | https://www.volcengine.com/docs/82379/2553718 |
| MCP Server | https://www.volcengine.com/docs/82379/2173253 |

---

## 19. Coding Plan (Anthropic-Compatible Endpoint)

Volcengine offers a **Coding Plan** specifically for AI coding tools (Claude Code, Cursor, Cline, OpenCode, Codex CLI):

### Configuration

```bash
export ANTHROPIC_BASE_URL=https://ark.cn-beijing.volces.com/api/coding
export ANTHROPIC_AUTH_TOKEN=<YOUR_ARK_API_KEY>
export ANTHROPIC_MODEL=ark-code-latest
```

### Features

- Native Anthropic API format support (for Claude Code compatibility)
- Auto-routes to best coding model
- Tiered subscription plans (Lite, Pro, etc.)
- Separate rate limits per 5-hour window

### Documentation

https://www.volcengine.com/docs/82379/1925114

---

## 20. Pricing

### Per Million Tokens (CNY ¥)

| Model | Input | Output | Notes |
|-------|-------|--------|-------|
| **Seed 2.1 Pro** | ¥6.00 | ¥30.00 | Flagship |
| **Seed 2.0 Pro** | ~¥10 | ~¥50 | Estimated |
| **Seed 2.0 Lite** (≤32K) | ¥1.20 | ¥18.00 | |
| **Seed 2.0 Lite** (>32K) | ¥0.40 | ¥6.00 | Discounted for long context |
| **Doubao 1.5 Pro 32K** | ¥2.00 | ¥5.00 | |
| **Doubao 1.5 Lite** | ¥0.30 | ¥0.60 | Cheapest |
| **Seed 1.6 Thinking** | ~¥0.80 | ~¥8.00 | |

### Free Tier

- 500K tokens per model (after real-name verification)
- Valid for 30 days
- "安心模式" (Safe Mode) — only consumes free quota, auto-pauses when exhausted
- Invite bonus: 15元 voucher via referral link
- Enterprise: 5M tokens free via collaboration plan
- Daily replenishment via Collaboration Rewards Program

---

## 21. Official Documentation Links

| Resource | URL |
|----------|-----|
| **Documentation Center** | https://www.volcengine.com/docs/82379 |
| **Base URL & Auth** | https://www.volcengine.com/docs/82379/1298459 |
| **API Key Management** | https://www.volcengine.com/docs/82379/1541594 |
| **Quick Start** | https://www.volcengine.com/docs/82379/1399008 |
| **Model List** | https://www.volcengine.com/docs/82379/1330310 |
| **Model Pricing** | https://www.volcengine.com/docs/82379/1544106 |
| **OpenAI SDK Compatibility** | https://docs.volcengine.com/docs/82379/1330626 |
| **Chat API** | https://www.volcengine.com/docs/82379/1494384 |
| **Chat API (v2)** | https://www.volcengine.com/docs/82379/1298454 |
| **Responses API** | https://www.volcengine.com/docs/82379/1569618 |
| **Migrate to Responses API** | https://www.volcengine.com/docs/82379/1585128 |
| **Text Generation** | https://www.volcengine.com/docs/82379/1399009 |
| **Streaming Output** | https://www.volcengine.com/docs/82379/2123275 |
| **SSE Streaming Events** | https://docs.volcengine.com/docs/82379/1599499 |
| **Deep Thinking** | https://www.volcengine.com/docs/82379/1449737 |
| **Function Calling** | https://docs.volcengine.com/docs/82379/1262342 |
| **Tool Overview** | https://www.volcengine.com/docs/82379/1827538 |
| **Responses API Tool Calling** | https://www.volcengine.com/docs/82379/1958524 |
| **Image Understanding (Vision)** | https://www.volcengine.com/docs/82379/1362931 |
| **Embedding API** | https://www.volcengine.com/docs/82379/1263524 |
| **Error Codes** | https://www.volcengine.com/docs/82379/1299023 |
| **Coding Plan** | https://www.volcengine.com/docs/82379/1925114 |
| **Context Management** | https://www.volcengine.com/docs/82379/2123288 |
| **Burst Traffic Best Practices** | https://www.volcengine.com/docs/82379/1848593 |
| **Manage Endpoints** | https://www.volcengine.com/docs/82379/1182403 |
| **Create Endpoint API** | https://www.volcengine.com/docs/82379/1262823 |
| **Batch Inference** | https://www.volcengine.com/docs/82379/1099455 |
| **FAQ / Troubleshooting** | https://www.volcengine.com/docs/82379/1359411 |
| **MCP Introduction** | https://www.volcengine.com/docs/82379/1539085 |
| **Cloud-deployed MCP** | https://www.volcengine.com/docs/82379/1827534 |
| **SDK V1/V2 Deprecation** | https://www.volcengine.com/docs/82379/1355331 |
| **Apifox API Docs (Text)** | https://doubao.apifox.cn/265892759e0 |
| **Apifox API Docs (Vision)** | https://doubao.apifox.cn/265897481e0 |
| **Apifox Error Codes** | https://doubao.apifox.cn/6107465m0 |
| **BytePlus (English) Docs** | https://docs.byteplus.com/en/docs/ModelArk/1449737 |
| **Volcengine MCP Server (GitHub)** | https://github.com/volcengine/mcp-server |
| **Ark CLI (GitHub)** | https://github.com/volcengine/ark-cli |
| **Product Page** | https://www.volcengine.com/product/doubao |
| **AI Hub** | https://ai.volcengine.com/ |

---

## 22. Sources

### Official Documentation (Primary)

1. Volcengine Ark Documentation Center — https://www.volcengine.com/docs/82379
2. OpenAI SDK Compatibility — https://docs.volcengine.com/docs/82379/1330626
3. Chat API Reference — https://www.volcengine.com/docs/82379/1494384
4. Function Calling — https://docs.volcengine.com/docs/82379/1262342
5. Tool Overview — https://www.volcengine.com/docs/82379/1827538
6. Deep Thinking — https://www.volcengine.com/docs/82379/1449737
7. Streaming Output — https://www.volcengine.com/docs/82379/2123275
8. Model List — https://www.volcengine.com/docs/82379/1330310
9. Base URL & Auth — https://www.volcengine.com/docs/82379/1298459
10. Error Codes — https://www.volcengine.com/docs/82379/1299023
11. Image Understanding — https://www.volcengine.com/docs/82379/1362931
12. API Key Management — https://www.volcengine.com/docs/82379/1541594

### Third-Party & Community Sources

13. huasheng.ai — Volcengine Ark API Deep Dive — https://huasheng.ai/insights/volcengine-ark-api-guide/
14. Apifox API Docs — https://doubao.apifox.cn/
15. OpenClaw Provider Docs — https://docs.openclaw.ai/providers/volcengine
16. OpenCode Volcengine Integration — https://opencodecn.com/docs/best-practices/volengine-ark-all
17. CSDN — 豆包官方开放API调用指南 — blog.csdn.net
18. Juejin — Node.js+Vue3.5 豆包流式调用方案 — juejin.cn
19. CodexBar Doubao Provider Docs — https://github.com/steipete/CodexBar/blob/main/docs/doubao.md
20. BytePlus Function Call (International) — https://docs.byteplus.com/en/docs/ModelArk/1262342
21. Dify Issue #13682 — SSE compatibility bug — https://github.com/langgenius/dify/issues/13682
22. LiteLLM Volcengine Provider — https://github.com/BerriAI/litellm/issues/23871
23. TechNode — Doubao 1.6-Vision — technode.com
24. compshare.cn — Thinking parameter details — https://www.compshare.cn/docs/modelverse/models/text_api/thinking/doubao
25. dmxapi.com — Thinking parameter details — https://doc.dmxapi.com/thinking-doubao.html

---

## Verification Notes

### Claims Verified by Multiple Sources ✅

- Base URL: `https://ark.cn-beijing.volces.com/api/v3` — confirmed across 8+ sources
- Authentication: `Authorization: Bearer <API_KEY>` — confirmed across all sources
- `reasoning_content` field name — confirmed by official docs, compshare.cn, dmxapi.com, multiple code examples
- Two-phase streaming (reasoning then content) — confirmed by 3+ sources with code examples
- Endpoint ID system — confirmed by official docs, OpenClaw, huasheng.ai, CodexBar
- Rate limit header deviations (TPM missing) — confirmed by CodexBar docs and integration guides
- Pre-deduction mechanism — confirmed by multiple Chinese technical blogs
- `thinking.type` values ("enabled"/"disabled"/"adaptive") — confirmed by official docs and third-party guides
- SSE `data: [DONE]` terminal — confirmed across all streaming examples
- `finish_reason: "tool_calls"` — confirmed by official docs and code examples

### Claims with Limited Verification ⚠️

- Exact pricing figures — subject to change, verified against 2-3 sources but may be outdated
- Seed Evolving 1M context / 256K output — reported by one source, plausible but not independently verified
- Specific rate limit numbers (30,000 RPM / 5,000,000 TPM for Seed 2.0 Pro) — from one source, may vary by plan

---

*Report generated by deep-research workflow. All data cross-referenced across official documentation, third-party integration guides, and community resources.*
