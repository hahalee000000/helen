# Zhipu AI (智谱AI / GLM / BigModel) OpenAI-Compatible API — Complete Protocol Reference

**Research Date**: 2026-08-05
**Sources**: Official docs (docs.bigmodel.cn, docs.z.ai), community discussions, third-party integrations

---

## 1. Base URL & Endpoint

| Item | Value |
|---|---|
| **OpenAI-compatible base URL** | `https://open.bigmodel.cn/api/paas/v4` |
| **Full chat completions endpoint** | `POST https://open.bigmodel.cn/api/paas/v4/chat/completions` |
| **Async chat completions** | `POST https://open.bigmodel.cn/api/paas/v4/chat/completions` (async variant) |
| **Authentication** | `Authorization: Bearer <API_KEY>` |
| **Content-Type** | `application/json` |
| **Z.AI international base URL** | `https://api.z.ai/...` (newer branding) |
| **OpenAI SDK migration** | Set `base_url="https://open.bigmodel.cn/api/paas/v4"` and use Zhipu API key |

### Compatibility
- **OpenAI protocol**: Fully compatible (drop-in replacement)
- **Anthropic (Claude) protocol**: Also supported
- **Gemini protocol**: Also supported

---

## 2. Chat Completions Request Schema

```json
{
  "model": "glm-5.2",
  "messages": [
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": "Hello"},
    {"role": "assistant", "content": "Hi! How can I help?"},
    {"role": "user", "content": "Tell me a joke"}
  ],
  "stream": false,
  "temperature": 1.0,
  "top_p": 0.9,
  "max_tokens": 4096,
  "stop": null,
  "presence_penalty": 0.0,
  "frequency_penalty": 0.0,
  "tools": [...],
  "tool_choice": "auto",
  "thinking": {"type": "enabled"},
  "reasoning_effort": "max",
  "tool_stream": false,
  "response_format": {"type": "text"},
  "user": "user-123"
}
```

### Request Parameters

| Parameter | Type | Required | Default | Description |
|---|---|---|---|---|
| `model` | string | ✅ | — | Model name (e.g., `glm-5.2`, `glm-4.5`) |
| `messages` | array | ✅ | — | Array of message objects `{role, content}` |
| `stream` | boolean | ❌ | `false` | Enable SSE streaming |
| `temperature` | float | ❌ | model-dependent | Sampling temperature [0.0, 1.0] |
| `top_p` | float | ❌ | 0.9 | Nucleus sampling [0.01, 1.0] |
| `max_tokens` | integer | ❌ | model-dependent | Max output tokens |
| `stop` | array/string | ❌ | `null` | Stop sequences |
| `presence_penalty` | float | ❌ | 0.0 | [-2.0, 2.0] |
| `frequency_penalty` | float | ❌ | 0.0 | [-2.0, 2.0] |
| `tools` | array | ❌ | — | Tool/function definitions |
| `tool_choice` | string | ❌ | `"auto"` | **Only `"auto"` supported** (not `"required"` or `"none"`) |
| `thinking` | object | ❌ | `{"type":"enabled"}` | Thinking/reasoning mode control |
| `reasoning_effort` | string | ❌ | `"max"` | Reasoning depth (GLM-5.2+) |
| `tool_stream` | boolean | ❌ | `false` | Stream tool call arguments incrementally |
| `response_format` | object | ❌ | — | `{"type": "text"}` or `{"type": "json_object"}` |
| `user` | string | ❌ | — | End-user identifier |
| `logprobs` | bool/int | ❌ | `false` | Return token log probabilities |

### Temperature Defaults by Model

| Model Family | Default Temperature |
|---|---|
| GLM-5.2 / GLM-5.1 / GLM-5 / GLM-5-Turbo | 1.0 |
| GLM-4.7 / GLM-4.6 | 1.0 |
| GLM-4.5 / GLM-4.5-Air | 0.6 |
| GLM-4 / GLM-4-Plus | 0.75 |

---

## 3. Response Schema (Non-Streaming)

```json
{
  "id": "chatcmpl-1234567890",
  "request_id": "8313807536837492492",
  "created": 1699999999,
  "model": "glm-5.2",
  "choices": [
    {
      "index": 0,
      "finish_reason": "stop",
      "message": {
        "role": "assistant",
        "content": "Hello! I'm Zhipu Qingyan (ChatGLM)...",
        "reasoning_content": "Let me think about this step by step..."
      }
    }
  ],
  "usage": {
    "prompt_tokens": 31,
    "completion_tokens": 217,
    "total_tokens": 248,
    "prompt_tokens_details": {
      "cached_tokens": 0
    },
    "completion_tokens_details": {
      "reasoning_tokens": 150
    }
  }
}
```

### Response Fields

| Field | Type | Description |
|---|---|---|
| `id` | string | Unique completion ID (e.g., `chatcmpl-xxx`) |
| `request_id` | string | Request tracing ID (for debugging/support) |
| `created` | integer | Unix timestamp |
| `model` | string | Model used |
| `choices` | array | Array of completion choices |
| `choices[].index` | integer | Choice index |
| `choices[].finish_reason` | string | Why generation stopped (see §9) |
| `choices[].message.role` | string | Always `"assistant"` |
| `choices[].message.content` | string | Final response text |
| `choices[].message.reasoning_content` | string? | Thinking/reasoning content (if thinking enabled) |
| `choices[].message.tool_calls` | array? | Tool calls (if model decided to call tools) |
| `usage.prompt_tokens` | integer | Input tokens consumed |
| `usage.completion_tokens` | integer | Output tokens consumed (includes reasoning) |
| `usage.total_tokens` | integer | `prompt_tokens + completion_tokens` |
| `usage.prompt_tokens_details.cached_tokens` | integer | Cached input tokens |
| `usage.completion_tokens_details.reasoning_tokens` | integer | Tokens used for reasoning (included in completion_tokens) |

---

## 4. Streaming Protocol (SSE)

### Transport
- Content-Type: `text/event-stream`
- HTTP chunked transfer encoding
- Long-lived connection

### SSE Format
Each event is a `data:` line followed by a JSON payload, terminated by `\n\n`.

```
data: {"id":"1","created":1677652288,"model":"glm-5.2","choices":[{"index":0,"delta":{"role":"assistant","content":""},"finish_reason":null}]}

data: {"id":"1","created":1677652288,"model":"glm-5.2","choices":[{"index":0,"delta":{"reasoning_content":"Let"},"finish_reason":null}]}

data: {"id":"1","created":1677652288,"model":"glm-5.2","choices":[{"index":0,"delta":{"reasoning_content":" me think"},"finish_reason":null}]}

data: {"id":"1","created":1677652288,"model":"glm-5.2","choices":[{"index":0,"delta":{"content":"The"},"finish_reason":null}]}

data: {"id":"1","created":1677652288,"model":"glm-5.2","choices":[{"index":0,"delta":{"content":" answer"},"finish_reason":null}]}

data: {"id":"1","created":1677652288,"model":"glm-5.2","choices":[{"index":0,"delta":{},"finish_reason":"stop"}],"usage":{"prompt_tokens":15,"completion_tokens":85,"total_tokens":100}}

data: [DONE]
```

### Key Streaming Details

| Aspect | Detail |
|---|---|
| **Delta field** | Uses `delta` (not `message`) in each chunk |
| **Reasoning content streams first** | `reasoning_content` chunks come before `content` chunks |
| **Tool calls stream** | `tool_calls` can stream incrementally when `tool_stream=true` |
| **Usage in final chunk** | `usage` only appears in the last chunk (when `finish_reason != null`) |
| **Termination** | Final event: `data: [DONE]` |
| **Empty delta** | Last content chunk may have empty `{}` delta before `finish_reason` |

### Client Processing Pattern (Python)

```python
for chunk in response.iter_lines():
    if chunk:
        decoded = chunk.decode('utf-8')
        if decoded.startswith('data:'):
            data = decoded[5:].strip()
            if data == '[DONE]':
                break
            chunk_obj = json.loads(data)
            delta = chunk_obj['choices'][0].get('delta', {})
            
            # Process reasoning content (if present)
            reasoning = delta.get('reasoning_content')
            if reasoning:
                handle_reasoning(reasoning)
            
            # Process main content
            content = delta.get('content')
            if content:
                handle_content(content)
            
            # Process tool calls
            tool_calls = delta.get('tool_calls')
            if tool_calls:
                handle_tool_calls(tool_calls)
            
            # Check finish
            finish = chunk_obj['choices'][0].get('finish_reason')
            if finish:
                handle_finish(finish, chunk_obj.get('usage'))
```

---

## 5. Function Calling / Tool Use

### Request Format

```json
{
  "model": "glm-5.2",
  "messages": [...],
  "tools": [
    {
      "type": "function",
      "function": {
        "name": "get_weather",
        "description": "Get current weather for a location",
        "parameters": {
          "type": "object",
          "properties": {
            "location": {
              "type": "string",
              "description": "City name"
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

### Response with Tool Calls

```json
{
  "choices": [
    {
      "index": 0,
      "finish_reason": "tool_calls",
      "message": {
        "role": "assistant",
        "content": null,
        "tool_calls": [
          {
            "id": "call_abc123",
            "type": "function",
            "function": {
              "name": "get_weather",
              "arguments": "{\"location\": \"Beijing\", \"unit\": \"celsius\"}"
            }
          }
        ]
      }
    }
  ]
}
```

### Multi-Turn Tool Conversation

```json
{
  "messages": [
    {"role": "user", "content": "What's the weather in Beijing?"},
    {"role": "assistant", "content": null, "tool_calls": [{"id": "call_1", "type": "function", "function": {"name": "get_weather", "arguments": "{\"location\": \"Beijing\"}"}}]},
    {"role": "tool", "tool_call_id": "call_1", "content": "{\"temperature\": 25, \"condition\": \"sunny\"}"},
    {"role": "assistant", "content": "The weather in Beijing is 25°C and sunny."}
  ]
}
```

### Tool Calling Details

| Aspect | Detail |
|---|---|
| **`tool_choice`** | Only `"auto"` supported (model decides whether to call) |
| **`function.arguments`** | JSON **string** (must be parsed) |
| **Parallel tool calls** | Multiple tool_calls in single response supported |
| **`parallel_tool_calls` param** | Not explicitly documented |
| **Tool streaming** | `tool_stream: true` streams args incrementally (GLM-5/5.1/5.2) |
| **Tool role message** | Follow-up message with `role: "tool"` and `tool_call_id` |

---

## 6. Reasoning / Thinking Content (`reasoning_content`)

### How It Works

GLM models support **Chain-of-Thought reasoning** where the model first thinks through a problem, then provides the final answer.

### Enabling/Disabling Thinking

```json
// Enable thinking (default for most models)
{"thinking": {"type": "enabled"}}

// Disable thinking
{"thinking": {"type": "disabled"}}

// Control reasoning depth (GLM-5.2+)
{"reasoning_effort": "max"}  // Options: max, xhigh, high, medium, low, minimal, none
```

### Response Format

```json
{
  "message": {
    "role": "assistant",
    "reasoning_content": "Let me solve this step by step. First...",
    "content": "The answer is 42."
  }
}
```

### Streaming Order
1. **First**: `reasoning_content` chunks stream (thinking process)
2. **Then**: `content` chunks stream (final answer)
3. **Last**: `finish_reason` + `usage`

### Multi-Turn Handling
- **`reasoning_content` is NOT visible to the model in subsequent turns** (known issue)
- To maintain reasoning chain across turns, some users inject `reasoning_content` back into `content` field
- This is a known limitation documented in GitHub issues

### Model-Specific Behavior

| Model | Thinking Behavior |
|---|---|
| GLM-5.2 | Supports `reasoning_effort` control |
| GLM-5 / GLM-5.1 | Dynamic thinking (auto-decides) |
| GLM-4.7 | **Forced thinking** — always thinks regardless of setting |
| GLM-4.6 | Dynamic thinking |
| GLM-4.5 | Dynamic thinking (hybrid reasoning mode) |
| GLM-4.5-Air | Dynamic thinking |
| GLM-4 and below | No thinking support |

---

## 7. Multimodal Support (Vision)

### Image Input Format (OpenAI-Compatible)

```json
{
  "model": "glm-4v-flash",
  "messages": [
    {
      "role": "user",
      "content": [
        {"type": "text", "text": "What's in this image?"},
        {
          "type": "image_url",
          "image_url": {
            "url": "https://example.com/image.jpg"
          }
        }
      ]
    }
  ]
}
```

### Base64 Image Support

```json
{
  "type": "image_url",
  "image_url": {
    "url": "data:image/jpeg;base64,/9j/4AAQSkZJRg..."
  }
}
```

### Vision Model Names

| Model | Type | Notes |
|---|---|---|
| `glm-4v-flash` | Free | Free vision model |
| `glm-4v` | Paid | Standard vision |
| `glm-4v-plus-0111` | Paid | Enhanced vision/video |
| `glm-4.5v` | Open-source | 106B/12B MoE VLM |
| `glm-4.6v` | Paid | Latest vision model |
| `glm-4.1v-thinking` | Open-source | Reasoning VLM |
| `glm-5v-turbo` | Paid | Native VL coding model |

### Multimodal Constraints
- Only one media type per request (can't mix image + video + file)
- Max media size: 20MB (configurable)
- Max media per request: 10

---

## 8. Token Usage Reporting

```json
{
  "usage": {
    "prompt_tokens": 100,
    "completion_tokens": 250,
    "total_tokens": 350,
    "prompt_tokens_details": {
      "cached_tokens": 0
    },
    "completion_tokens_details": {
      "reasoning_tokens": 150
    }
  }
}
```

### Usage Field Details

| Field | Description |
|---|---|
| `prompt_tokens` | Input tokens consumed |
| `completion_tokens` | Output tokens (includes reasoning tokens) |
| `total_tokens` | `prompt_tokens + completion_tokens` |
| `prompt_tokens_details.cached_tokens` | Cached prompt tokens (context cache hits) |
| `completion_tokens_details.reasoning_tokens` | Tokens spent on reasoning/thinking |

### Important
- `reasoning_tokens` is **included within** `completion_tokens` (not additive)
- Reasoning tokens **are billed** at the same rate as regular output tokens
- Only present when thinking/reasoning mode is active

---

## 9. finish_reason Values

| Value | Description |
|---|---|
| `stop` | Natural end of generation, or stop sequence hit |
| `length` | Hit `max_tokens` limit, output truncated |
| `tool_calls` | Model decided to call tool(s) |
| `sensitive` | Content safety filter triggered |
| `model_context_window_exceeded` | Exceeded model's context window |
| `network_error` | Network/infrastructure error |

---

## 10. Model Names (Complete List)

### GLM-5 Series (2026)
| Model | Context | Notes |
|---|---|---|
| `glm-5.2` | 1M tokens | Latest flagship, 1M context |
| `glm-5.1` | 200K | Autonomous work up to 8 hours |
| `glm-5` | — | DSA architecture, agentic engineering |
| `glm-5-turbo` | — | Fast variant |
| `glm-5v-turbo` | — | Vision-language coding model |

### GLM-4.x Series (2025)
| Model | Context | Notes |
|---|---|---|
| `glm-4.7` | — | 355B/32B MoE, coding-focused, forced thinking |
| `glm-4.7-flash` | — | Free tier |
| `glm-4.6` | 200K | Enhanced coding, reasoning, search |
| `glm-4.6v` | — | Vision variant |
| `glm-4.6v-flash` | — | Free vision |
| `glm-4.5` | 128K | Open-source 355B/32B MoE |
| `glm-4.5-air` | — | Compact 106B/12B MoE |
| `glm-4.5-flash` | 128K | Free (deprecated) |
| `glm-4.5v` | — | Vision-language |
| `glm-4.1v-thinking` | — | Reasoning VLM |

### GLM-4 Series (2024-2025)
| Model | Context | Notes |
|---|---|---|
| `glm-4` | 128K | Original flagship |
| `glm-4-plus` | 128K | Enhanced foundation model |
| `glm-4-air` | 128K | Lightweight variant |
| `glm-4-air-x` | 128K | Accelerated Air |
| `glm-4-long` | 1M | Long context |
| `glm-4-flash` | 128K | Free model |
| `glm-4-flash-250414` | 128K | Updated Flash |
| `glm-4-flash-x` | 128K | Accelerated Flash |
| `glm-4v` | — | Vision |
| `glm-4v-plus-0111` | — | Enhanced vision |
| `glm-4v-flash` | — | Free vision |
| `glm-4-32b-0414` | 128K | Open-source 32B |
| `glm-4-9b-chat` | 8K | Open-source 9B |
| `glm-4v-9b` | — | Open-source vision 9B |

---

## 11. Error Handling

### Error Response Format

```json
{
  "error": {
    "code": "1210",
    "message": "Parameter error: invalid model name"
  }
}
```

### Two-Layer Error Structure
- **Outer layer**: HTTP status code (400, 401, 403, 404, 429, 500)
- **Inner layer**: Business error code in response body

### HTTP Status Codes

| Code | Meaning |
|---|---|
| 200 | Success |
| 400 | Bad Request (invalid parameters) |
| 401 | Unauthorized (invalid API key) |
| 403 | Forbidden |
| 404 | Not Found |
| 429 | Rate Limit Exceeded |
| 500 | Internal Server Error |

### Common Business Error Codes
| Code | Description |
|---|---|
| 1210 | Parameter error |
| 1001 | Invalid API key |
| 1002 | Insufficient balance |
| 1003 | Rate limit exceeded |

### Full error code reference:
- Chinese: https://docs.bigmodel.cn/cn/faq/api-code
- English: https://docs.z.ai/api-reference/api-code

---

## 12. Provider-Specific Extensions & Deviations from OpenAI

| Extension | Description |
|---|---|
| **`thinking` parameter** | Object `{type: "enabled"|"disabled"}` — not in OpenAI spec |
| **`reasoning_effort`** | String enum for reasoning depth — OpenAI has this but differently |
| **`reasoning_content`** | In `message`/`delta` — separate field for thinking content |
| **`tool_stream`** | Boolean to stream tool call args incrementally — Zhipu-specific |
| **`tool_choice: "auto"` only** | No `"required"` or `"none"` options (deviation from OpenAI) |
| **`request_id`** | Additional tracing field in response — not in OpenAI |
| **Usage structure** | Has `prompt_tokens_details` and `completion_tokens_details` (similar to OpenAI's recent additions) |
| **`finish_reason: "sensitive"`** | Content safety filter — Zhipu-specific |
| **Forced thinking models** | GLM-4.7 always thinks regardless of settings |
| **Temperature range** | Limited to [0.0, 1.0] with 2 decimal places (OpenAI uses [0.0, 2.0]) |

---

## 13. System Messages & Multi-Turn

### System Message
```json
{"role": "system", "content": "You are a helpful assistant specialized in math."}
```
- Supported as first message in `messages` array
- Sets model behavior/personality for the conversation

### Multi-Turn Conversation
```json
{
  "messages": [
    {"role": "system", "content": "You are helpful."},
    {"role": "user", "content": "What is 2+2?"},
    {"role": "assistant", "content": "4"},
    {"role": "user", "content": "And 3+3?"}
  ]
}
```

### Multi-Turn with Tool Calls
```json
{
  "messages": [
    {"role": "user", "content": "..."},
    {"role": "assistant", "content": null, "tool_calls": [...]},
    {"role": "tool", "tool_call_id": "call_xxx", "content": "..."},
    {"role": "assistant", "content": "Based on the tool result..."}
  ]
}
```

### Multi-Turn with Reasoning (Important Caveat)
- `reasoning_content` from previous turns is **NOT visible to the model**
- This breaks reasoning chain continuity across turns
- Workaround: Some users inject reasoning into the `content` field manually

---

## 14. Response Format Options

| Format | Description |
|---|---|
| `{"type": "text"}` | Default, free-form text output |
| `{"type": "json_object"}` | JSON mode — model always outputs valid JSON |

---

## 15. Official Documentation Links

| Resource | URL |
|---|---|
| **Platform Home** | https://open.bigmodel.cn/ |
| **OpenAI Compat Guide** | https://docs.bigmodel.cn/cn/guide/develop/openai/introduction |
| **HTTP API Guide** | https://docs.bigmodel.cn/cn/guide/develop/http/introduction |
| **API Introduction** | https://docs.bigmodel.cn/cn/api/introduction |
| **Chat Completions API** | https://docs.bigmodel.cn/api-reference/模型-api/对话补全 |
| **Streaming Guide** | https://docs.bigmodel.cn/cn/guide/capabilities/streaming |
| **Tool Streaming** | https://docs.bigmodel.cn/cn/guide/capabilities/stream-tool |
| **Function Calling** | https://docs.bigmodel.cn/cn/guide/capabilities/function-calling |
| **Thinking Mode** | https://docs.bigmodel.cn/cn/guide/capabilities/thinking-mode |
| **Deep Thinking** | https://docs.bigmodel.cn/cn/guide/capabilities/thinking |
| **Model Overview** | https://docs.bigmodel.cn/cn/guide/start/model-overview |
| **Core Parameters** | https://docs.bigmodel.cn/cn/guide/start/concept-param |
| **Error Codes (CN)** | https://docs.bigmodel.cn/cn/faq/api-code |
| **Error Codes (EN)** | https://docs.z.ai/api-reference/api-code |
| **llms.txt** | https://docs.bigmodel.cn/llms.txt |
| **Z.AI (International)** | https://docs.z.ai/ |
| **Pricing** | https://bigmodel.cn/pricing |

---

## 16. Code Examples

### Python (OpenAI SDK compatible)

```python
from openai import OpenAI

client = OpenAI(
    api_key="your-zhipu-api-key",
    base_url="https://open.bigmodel.cn/api/paas/v4"
)

# Non-streaming
response = client.chat.completions.create(
    model="glm-5.2",
    messages=[{"role": "user", "content": "Hello!"}],
    temperature=0.7,
    max_tokens=2048,
)
print(response.choices[0].message.content)
print(f"Reasoning tokens: {response.usage.completion_tokens_details.reasoning_tokens}")

# Streaming
stream = client.chat.completions.create(
    model="glm-5.2",
    messages=[{"role": "user", "content": "Tell me a story"}],
    stream=True,
)
for chunk in stream:
    delta = chunk.choices[0].delta
    if hasattr(delta, 'reasoning_content') and delta.reasoning_content:
        print(f"[THINKING] {delta.reasoning_content}", end="", flush=True)
    if delta.content:
        print(delta.content, end="", flush=True)

# With tool calling
response = client.chat.completions.create(
    model="glm-5.2",
    messages=[{"role": "user", "content": "What's the weather in Beijing?"}],
    tools=[{
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Get current weather",
            "parameters": {
                "type": "object",
                "properties": {"location": {"type": "string"}},
                "required": ["location"]
            }
        }
    }],
    tool_choice="auto",
)

# Vision (multimodal)
response = client.chat.completions.create(
    model="glm-4v-flash",
    messages=[{
        "role": "user",
        "content": [
            {"type": "text", "text": "What's in this image?"},
            {"type": "image_url", "image_url": {"url": "https://example.com/img.jpg"}}
        ]
    }]
)

# With thinking disabled
response = client.chat.completions.create(
    model="glm-5.2",
    messages=[{"role": "user", "content": "Simple question"}],
    extra_body={"thinking": {"type": "disabled"}}
)
```

### Python (native ZhipuAI SDK)

```python
from zhipuai import ZhipuAI

client = ZhipuAI(api_key="your-api-key")

response = client.chat.completions.create(
    model="glm-5.2",
    messages=[{"role": "user", "content": "Hello!"}],
    stream=True,
    extra_body={"tool_stream": True}  # Enable tool streaming
)
```

### curl

```bash
curl -X POST "https://open.bigmodel.cn/api/paas/v4/chat/completions" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -d '{
    "model": "glm-5.2",
    "messages": [
      {"role": "system", "content": "You are a helpful assistant."},
      {"role": "user", "content": "Hello!"}
    ],
    "stream": false,
    "temperature": 0.7,
    "max_tokens": 2048
  }'
```

---

## 17. Known Issues & Gotchas

| Issue | Detail |
|---|---|
| **reasoning_content invisible across turns** | Model doesn't see previous reasoning_content; reasoning chain breaks in multi-turn |
| **tool_choice limited to "auto"** | Cannot force tool calls or disable them explicitly |
| **GLM-4.7 forced thinking** | Cannot disable thinking on GLM-4.7 |
| **Temperature precision** | Limited to 2 decimal places |
| **vLLM/SGLang tool call bugs** | Third-party engines may produce malformed tool calls for GLM-5 |
| **Streaming JSON truncation** | Rare reports of truncated JSON in SSE chunks for GLM-5.1 |
| **Alibaba Cloud proxying** | When using GLM via Alibaba Cloud, must use `extra_body={"tool_stream": True}` |

---

## 18. Summary Table

| Capability | Supported? | Notes |
|---|---|---|
| OpenAI-compatible API | ✅ | Drop-in replacement |
| Chat completions | ✅ | Full support |
| Streaming (SSE) | ✅ | `stream: true` |
| Function calling | ✅ | `tools` array |
| Tool streaming | ✅ | `tool_stream: true` (Zhipu-specific) |
| Reasoning/thinking | ✅ | `thinking.type`, `reasoning_effort` |
| `reasoning_content` | ✅ | Separate field in message/delta |
| Vision/multimodal | ✅ | `image_url` in content array |
| JSON mode | ✅ | `response_format: {"type": "json_object"}` |
| System messages | ✅ | Standard multi-turn |
| Multi-turn | ✅ | Standard messages array |
| Stop sequences | ✅ | `stop` parameter |
| Token usage | ✅ | `usage` object with reasoning tokens |
| Cached tokens | ✅ | `prompt_tokens_details.cached_tokens` |
| Context window up to 1M | ✅ | GLM-5.2 |
| Error codes | ✅ | HTTP + business error codes |
| Batch processing | ✅ | Async API available |
| Embeddings | ✅ | Separate endpoint |
| TTS | ✅ | GLM-TTS |
| Image generation | ✅ | GLM-Image |
| Real-time (WebSocket) | ✅ | GLM-Realtime |

---

*This document represents the complete protocol specification as of 2026-08-05, compiled from official Zhipu AI documentation, community discussions, and third-party integration code.*
