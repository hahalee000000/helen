# Helen Language — Threat Model

**Repository**: `/home/rxx/helen/` (Helen v1.39.6 — AI-native DSL for Agent development)
**Date**: 2025-08-07
**Scope**: Repository-wide architectural threat modeling (STRIDE methodology)
**Methodology**: Trust-boundary analysis → data-flow mapping → actor/capability modeling → STRIDE prioritization

---

## 1. System Overview

Helen is a **prompt-first programming language** for AI agents. It combines a deterministic
language runtime (lexer → parser → AST → semantic analyzer → interpreter) with first-class
LLM primitives (`llm act`, `llm if`) and a rich stdlib (333 built-in functions). Programs
written in Helen can invoke LLMs, call shell commands, read/write files, make HTTP requests,
import arbitrary Python modules, and spawn concurrent agents.

### 1.1 Architectural Layers

```
┌─────────────────────────────────────────────────────────────────┐
│  Layer 3: Toolchain                                             │
│  CLI (run/check/repl/test/quality/doc/lsp/agent)                │
│  REPL  ·  LSP (JSON-RPC/stdio)  ·  Web UI (FastAPI+WebSockets)  │
├─────────────────────────────────────────────────────────────────┤
│  Layer 2: Runtime                                               │
│  LLMRuntime → HttpLLMRuntime (OpenAI-compatible)                │
│  Tools (shell_exec, read/write/patch_file, web_search/fetch,    │
│         calculate, load_skill, find/search_files) + MCP         │
│  TranscriptStore (SQLite/JSONL)  ·  SessionManager              │
│  Channel (spawn/mailbox_select)  ·  SharedStore                 │
├─────────────────────────────────────────────────────────────────┤
│  Layer 1: Helen Core                                            │
│  Lexer → Parser → AST → SemanticAnalyzer → Interpreter          │
│  (mixins: llm, pattern, exception, import, streaming)           │
├─────────────────────────────────────────────────────────────────┤
│  Cross-cutting                                                  │
│  Python FFI (eval/exec)  ·  Python Bridge (import hook)         │
│  Stdlib (333 fns: system, network, file, crypto, data, ...)     │
│  Config (~/.helen/config.yaml — plaintext API keys)             │
└─────────────────────────────────────────────────────────────────┘
```

---

## 2. Trust Boundaries

| ID  | Boundary | From → To | Criticality |
|-----|----------|-----------|-------------|
| TB1 | **Program ↔ OS** | Helen program (incl. LLM-directed tool calls) ↔ host operating system | **CRITICAL** |
| TB2 | **LLM ↔ Runtime** | Untrusted LLM output (tool-call decisions, generated text) ↔ interpreter | **CRITICAL** |
| TB3 | **User ↔ CLI/REPL** | Interactive user input ↔ parser/interpreter | HIGH |
| TB4 | **Imported code ↔ Host** | `import`ed `.helen`/`.py`/`.yaml`/`.json` files ↔ runtime | HIGH |
| TB5 | **Helen ↔ Network** | HTTP client / web_search / web_fetch ↔ external internet | HIGH |
| TB6 | **Helen ↔ Python** | FFI `eval`/`exec` and `importlib.import_module` ↔ Python ecosystem | **CRITICAL** |
| TB7 | **Web UI ↔ Client** | FastAPI/WebSocket server ↔ browser or API client | HIGH |
| TB8 | **Config store ↔ Process** | `~/.helen/config.yaml` (API keys) ↔ any Helen process | MEDIUM |
| TB9 | **Transcript store ↔ FS** | SQLite/JSONL session files ↔ filesystem | MEDIUM |
| TB10 | **Agent ↔ Agent** | Parent agent ↔ spawned child agent (shared store / channel) | MEDIUM |

---

## 3. Attack Surfaces & Entry Points

### 3.1 LLM-Directed Tool Execution (TB2 — CRITICAL)

The LLM can invoke any registered tool via `tool_calls` in its response. The runtime
dispatches these calls **without human-in-the-loop confirmation** by default.

**Entry points**:
- `helen/runtime/tools.py::dispatch_tool()` — global tool registry
- `helen/interpreter/llm_mixin.py` — `llm act` tool-call loop

**Tools exposed to the LLM** (all run with full user privileges):
| Tool | Risk |
|------|------|
| `shell_exec` / `shell_exec_full` | Arbitrary command execution, default `shell=True` with `/bin/bash` |
| `read_file` | Arbitrary file read (no path restriction) |
| `write_file` | Arbitrary file write (creates parent dirs) |
| `patch_file` | Arbitrary file modification |
| `web_search` | SSRF / information disclosure via Bing scraping |
| `web_fetch` | SSRF — fetches any URL, returns text |
| `calculate` | Sandboxed (AST whitelist) — low risk |
| `find_files` / `search_files` | Filesystem enumeration |
| `load_skill` / `list_skill_references` | Reads SKILL.md from disk |
| MCP tools | External MCP server commands |

**Threat**: A compromised, jailbroken, or hallucinating LLM can exfiltrate data,
modify code, install backdoors, or pivot to other systems — all under the identity
of the user running Helen.

### 3.2 Python FFI — `eval` / `exec` (TB6 — CRITICAL)

`helen/ffi/python_runtime.py` exposes:
```python
def eval_expression(self, expression: str) -> Any:
    result = eval(expression, self._context)

def exec_statement(self, statement: str) -> None:
    exec(statement, self._context)
```
Any Helen program that uses `import_python` can reach these. The `_context` dict
accumulates every imported module, so `exec("__import__('os').system('rm -rf /')")`
is reachable if the LLM or user drives it.

### 3.3 Shell Execution (TB1 — CRITICAL)

`helen/runtime/tools.py::_shell_exec`:
- Default `shell=True`, executable `/bin/bash` on Unix
- 120-second timeout, 8 KB output truncation
- No command allowlist, no sandboxing, no seccomp/landlock
- Helen stdlib also exposes `exec()` and `shell_exec()` as first-class builtins

### 3.4 File I/O Without Path Restrictions (TB1)

`read_file`, `write_file`, `patch_file`, `http_download`, and stdlib `file_*`
functions accept arbitrary paths. `write_file` creates parent directories
(`Path(path).parent.mkdir(parents=True, exist_ok=True)`), enabling writes to
`/etc/`, `~/.ssh/`, cron dirs, etc.

**Contrast**: `ImportResolver._is_safe_path()` enforces base-directory containment
for `import` statements, but this protection does **not** apply to tool-driven I/O.

### 3.5 Network / SSRF (TB5)

- `_web_fetch(url)` — no scheme/host allowlist; `file://`, `http://169.254.169.254/`
  (cloud metadata), and internal hosts are reachable.
- `_http_request` in `stdlib/network.py` — same issue.
- `_http_download` — writes arbitrary URL content to arbitrary path (combines with 3.4
  for arbitrary file overwrite from the network).
- `_web_search` — Bing HTML scraping; response is regex-stripped but could still carry
  injected content that the LLM then trusts.

### 3.6 Configuration & Secrets (TB8)

- `~/.helen/config.yaml` stores `api_key` in **plaintext YAML**.
- `save_config()` writes it back with mode inherited from umask (no explicit `0600`).
- Env vars `HELEN_API_KEY`, `HELEN_BASE_URL`, `HELEN_MODEL` are read; any child
  process inherits them.
- `env_list()` stdlib function dumps the entire environment to the LLM.

### 3.7 Import Resolver (TB4)

`helen/runtime/import_resolver.py`:
- Allows absolute paths (bypasses base-dir check).
- Parses and executes `.helen` files recursively; transitively imports Python modules.
- Loads `.yaml` via `yaml.safe_load` (safe) and `.json` — OK.
- Circular-import detection present, but a malicious `.helen` file can still execute
  arbitrary code via `import_python` or `shell_exec` at import time.

### 3.8 Python Bridge Import Hook (TB6)

`helen/python_bridge/import_hook.py` installs a `MetaPathFinder` so that
`import some_module.helen` from Python transparently creates a Helen `Interpreter`.
Session ID is read from:
1. `set_session_id()` override
2. `HELEN_SESSION_ID` env var
3. `.helen/current_session_id` memento file (JSON or plain text)

The memento file is writable by any process the user runs; a local attacker can
hijack sessions by pre-creating this file.

### 3.9 Web UI / FastAPI Server (TB7)

`helen/agent/chat_tui_web.py` and the `helen/agent/webui/` frontend:
- FastAPI + WebSockets, launched via `helen agent`.
- Reads memento file at startup; trusts its contents.
- Default bind address not visible in launcher — needs verification (if `0.0.0.0`,
  this is a remote-code-execution surface on the LAN).
- No authentication layer visible in the launcher code.

### 3.10 LSP Server (TB3 — LOW)

JSON-RPC over stdio. Trusts the editor. Risk limited to malicious `.helen` files
opened in the editor triggering parser/semantic-analyzer bugs.

### 3.11 Transcript / Session Storage (TB9)

SQLite/JSONL files under `~/.helen/sessions/` or `<project>/.helen/sessions/`.
Contain full conversation history including API keys echoed in prompts, tool
outputs (which may contain secrets), and user data. No encryption at rest.

### 3.12 Agent Scope Isolation (TB10)

Helen provides `@open`, `@strict`, `@sandbox` isolation levels. `@sandbox` forces
`tools=[]`, but standard agents have full tool access. `shared store` is
thread-safe (RLock) but any agent with a reference can mutate it. `spawn`
deep-copies the environment — but modules (FFI) are singletons and shared.

---

## 4. Threat Actors & Capabilities

| Actor | Position | Capabilities | Primary targets |
|-------|----------|--------------|-----------------|
| **A1. Compromised/Jailbroken LLM** | Inside TB2 | Returns crafted `tool_calls`; injects instructions via generated text | TB1, TB5, TB6 — full host takeover via tool dispatch |
| **A2. Malicious `.helen` package** | Supply chain | Distributed via skills, imports, or shared programs | TB4, TB1, TB6 — arbitrary code at import time |
| **A3. Malicious MCP server** | External tool provider | Returns crafted tool schemas / responses | TB2 → TB1 (indirect LLM manipulation) |
| **A4. Network attacker** | On-path or SSRF target | Injects responses to `web_fetch`/`web_search`; redirects | TB5 → TB2 → TB1 |
| **A5. Local untrusted user** | Same host, different account | Reads `~/.helen/config.yaml`, memento files, transcripts | TB8, TB9 |
| **A6. Malicious web-ui client** | Browser on LAN | Calls FastAPI endpoints if no auth | TB7 → TB1 |
| **A7. Prompt injector (end user)** | Via agent input | Injects instructions through `{{var}}` templates or chat input | TB2 → TB1 |

---

## 5. STRIDE Threat Catalog (Prioritized)

### CRITICAL

| ID | Category | Threat | Affected | Mitigation status |
|----|----------|--------|----------|-------------------|
| T-01 | **Elevation of Privilege** | LLM-directed `shell_exec` runs arbitrary OS commands as the user, no confirmation | TB1, TB2 | **Unmitigated.** `tools` whitelist exists per-agent but default is full set. No human-in-the-loop. |
| T-02 | **Elevation of Privilege** | Python FFI `eval`/`exec` reachable from Helen code and from LLM-driven tool calls | TB6 | **Unmitigated.** No sandboxing of `_context`. |
| T-03 | **Information Disclosure** | `read_file` + `env_list` + `web_fetch` let a compromised LLM exfiltrate any file, env var, or internal HTTP service to the network | TB1, TB5, TB8 | **Unmitigated.** No egress filtering. |
| T-04 | **Tampering** | `write_file` / `patch_file` with no path restriction — LLM can overwrite `~/.ssh/authorized_keys`, crontabs, `~/.helen/config.yaml`, or any project file | TB1 | **Unmitigated.** |

### HIGH

| ID | Category | Threat | Affected | Mitigation status |
|----|----------|--------|----------|-------------------|
| T-05 | **SSRF** | `web_fetch` / `http_get` / `http_download` accept `file://`, `http://169.254.169.254/`, and RFC-1918 targets | TB5 | **Unmitigated.** No scheme/host allowlist. |
| T-06 | **Supply-chain tampering** | `import "path"` accepts absolute paths; a malicious skill or imported file runs code at load time | TB4 | **Partial.** `_is_safe_path` bounds relative imports but absolute paths bypass. |
| T-07 | **Spoofing / Session hijack** | `.helen/current_session_id` memento file is writable by any local process; attacker can force a Helen process to resume an attacker-chosen transcript | TB9 | **Unmitigated.** No integrity check. |
| T-08 | **Information Disclosure** | API key stored in plaintext `~/.helen/config.yaml` with no explicit mode; inherited by child processes via env | TB8 | **Partial.** Env override supported, but file perms not enforced. |
| T-09 | **Denial of Service** | `shell_exec` default timeout 120s, `web_fetch` 15s, no global resource budget; a misbehaving LLM can fork-bomb or exhaust network | TB1, TB5 | **Partial.** Per-call timeouts exist, no aggregate budget. |
| T-10 | **Elevation of Privilege (Web UI)** | FastAPI server launched by `helen agent` — bind address and authentication need verification; if bound to `0.0.0.0` without auth, any LAN host can drive the agent | TB7 | **Unknown — needs verification.** |

### MEDIUM

| ID | Category | Threat | Affected | Mitigation status |
|----|----------|--------|----------|-------------------|
| T-11 | **Information Disclosure** | Transcript SQLite/JSONL files contain full prompts (including secrets) in plaintext on disk | TB9 | **Unmitigated.** No encryption at rest. |
| T-12 | **Tampering** | MCP tool registry is lazy-initialized; a malicious MCP server can return arbitrary tool schemas that the LLM then invokes | TB2, TB3 | **Partial.** MCP is opt-in per agent. |
| T-13 | **Spoofing** | `web_search` parses Bing HTML with regex; a poisoned search result page can inject content the LLM treats as ground truth | TB5 → TB2 | **Unmitigated.** |
| T-14 | **Information Disclosure** | `env_list()` returns the full process environment to the LLM, including any secrets not in `config.yaml` | TB8 → TB2 | **Unmitigated.** |
| T-15 | **Tampering** | `shared store` is mutable by any agent holding a reference; no capability-based restriction between peers | TB10 | **By design**, but risky for multi-tenant agents. |
| T-16 | **Denial of Service** | `calculate` uses AST whitelist — low risk, but `ast.walk` over untrusted input has historically had edge cases | TB3 | **Mitigated** (whitelist). |
| T-17 | **Spoofing** | `{{var}}` prompt templates interpolate user/agent input directly; prompt-injection via variable values can redirect LLM behavior | TB2 | **Unmitigated** (inherent to prompt-first design). |

### LOW

| ID | Category | Threat | Affected | Mitigation status |
|----|----------|--------|----------|-------------------|
| T-18 | **Denial of Service** | LSP parser bugs on malformed input | TB3 | **Partial.** Parser is pure Python; crashes are contained. |
| T-19 | **Information Disclosure** | Error messages may leak file paths, env vars, or stack traces to the LLM | TB2 | **Partial.** Errors are JSON-serialized and returned to LLM. |
| T-20 | **Tampering** | `helen.png` (4.5 MB) and other non-code assets in repo — not a runtime risk but a supply-chain surface if build process trusts them | — | **Low priority.** |

---

## 6. Data-Flow Summary (Hot Paths)

```
[User input / .helen source]
        │
        ▼
   ┌──────────┐     ┌──────────────────┐
   │  Parser  │────▶│ SemanticAnalyzer │
   └──────────┘     └──────────────────┘
        │                    │
        ▼                    ▼
   ┌─────────────────────────────────┐
   │         Interpreter             │
   │  ┌───────────┐  ┌────────────┐  │
   │  │ llm_mixin │  │ import_mix │  │
   │  └─────┬─────┘  └─────┬──────┘  │
   └────────┼───────────────┼─────────┘
            │               │
            ▼               ▼
   ┌────────────────┐  ┌──────────────┐
   │  HttpLLMRuntime│  │ImportResolver│──▶ FS (.helen/.py/.yaml/.json)
   │  (tool_calls)  │  └──────────────┘
   └────────┬───────┘
            │ dispatch_tool()
            ▼
   ┌────────────────────────────────────────┐
   │ Tool handlers (full user privileges):  │
   │  shell_exec · read/write/patch_file ·  │
   │  web_search · web_fetch · calculate ·  │
   │  find_files · search_files · MCP       │
   └────────────────────────────────────────┘
            │
            ▼
   [OS / Filesystem / Network / Python runtime]
```

---

## 7. Security Assumptions & Constraints

### Currently assumed (implicitly)
1. **The user trusts the Helen program they run.** True for local dev; false for
   shared skills, downloaded agents, or LLM-directed tool calls.
2. **The LLM is well-behaved.** This is the single largest assumption — the entire
   tool-dispatch path assumes the LLM will not issue destructive `tool_calls`.
3. **The host OS is single-tenant.** `~/.helen/config.yaml` and transcript files
   have no ACL/encryption; they assume no malicious local users.
4. **Network is not adversarial.** `web_fetch` follows redirects and accepts any
   scheme the underlying `urllib` accepts.
5. **Python ecosystem is trusted.** FFI imports any module the Python env can see.

### Constraints
- Helen is a **development-time tool** by default — most users run it on their own
  workstation against their own code. This limits blast radius compared to a
  multi-tenant service, but the `helen agent` Web UI and Python Bridge expand the
  deployment model into long-running service territory.
- The language is **prompt-first by design**: the LLM is *meant* to drive actions.
  Security controls must therefore be **opt-out-safe** (deny-by-default tool lists,
  path allowlists, confirmation prompts) rather than relying on user discipline.

---

## 8. Prioritized Recommendations

### P0 — Address immediately (before running untrusted Helen code)
1. **Tool allowlists deny-by-default.** New agents should start with `tools=[]`;
   require explicit opt-in per tool class (`shell`, `fs`, `net`, `ffi`).
2. **Human-in-the-loop for destructive tools.** `shell_exec`, `write_file`,
   `patch_file`, FFI `exec` should prompt for confirmation outside `@sandbox` mode,
   or require an explicit `@unsafe agent` annotation.
3. **Path allowlists for file I/O.** Restrict `read_file`/`write_file`/`patch_file`
   to the project directory + explicit allow-list, mirroring `ImportResolver._is_safe_path`.
4. **SSRF guardrails.** Block `file://`, `169.254.0.0/16`, `127.0.0.0/8`,
   `10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16` in `web_fetch` / `http_*`
   unless explicitly allowed.

### P1 — Address in next release
5. **Config file permissions.** `save_config()` should `chmod 0600` `config.yaml`;
   consider keyring/`secret-storage` integration instead of plaintext YAML.
6. **Transcript encryption at rest.** At minimum, mode `0600` on session dirs;
   ideally AES-GCM with a per-user key.
7. **Memento integrity.** HMAC-sign `.helen/current_session_id` or move it under
   `~/.helen/` with `0600`.
8. **Web UI auth + bind.** Verify `helen agent` binds to `127.0.0.1` only; add a
   token/localhost-only auth layer.
9. **Python FFI sandbox.** Run `eval`/`exec` in a `RestrictedPython`-style
   environment or a subprocess with dropped privileges.

### P2 — Strategic
10. **Capability-based tool model.** Replace the global `_tools` registry with
    per-agent capability tokens; MCP servers should be authenticated.
11. **Prompt-injection defenses for `{{var}}`**. Quote/escape interpolated values,
    or route them through a separate "data" channel the LLM is instructed not to
    obey as commands.
12. **Audit log for tool dispatch.** Every `dispatch_tool` call should be recorded
    with caller agent ID, arguments, and result — independent of the transcript —
    so post-incident review is possible even if the LLM is compromised.
13. **Egress allowlist.** Provide a config-level `allowed_hosts` for `web_fetch`
    and `http_*`.
14. **Supply-chain signing.** Sign distributed skills and built-in `.helen` files;
    verify on load.

---

## 9. Scope Exclusions

This model covers the repository as shipped. It does **not** cover:
- Threats introduced by user-written Helen programs (out of language-design scope,
  though the language *does* mediate them — see P0 recommendations).
- Upstream LLM provider security (OpenAI, Anthropic, etc.).
- Third-party MCP server behavior beyond the trust boundary at TB2.
- Frontend (`helen/agent/webui/frontend/`) — not inspected; assumed to be a
  standard React/Vite app whose security depends on the FastAPI backend.

---

## 10. Summary Heat Map

```
                  ┌─────────────────────────────────────────┐
                  │           IMPACT                        │
                  │  Low     Medium    High    Critical     │
        ┌─────────┼─────────────────────────────────────────┤
        │ High    │         │ T-09  │ T-05,T-06,T-10 │     │
        │         │         │       │ T-07,T-08      │     │
  L     │─────────┼─────────┼───────┼────────────────┤     │
  I     │ Medium  │ T-16    │ T-11  │ T-13           │ T-01│
  K     │         │         │ T-15  │ T-14           │ T-02│
  E     │         │         │       │                │ T-03│
  L     │─────────┼─────────┼───────┼────────────────┤ T-04│
  I     │ Low     │ T-18    │ T-12  │ T-17           │     │
  H     │         │ T-19    │ T-20  │                │     │
  O     │         │         │       │                │     │
  O     └─────────┴─────────┴───────┴────────────────┴─────┘
```

**Top 4 risks (all CRITICAL likelihood × CRITICAL impact):** T-01, T-02, T-03, T-04 —
all stem from the same root cause: **the LLM has unrestricted, unconfirmed root-level
access to the host via the tool-dispatch path.** Mitigating this single architectural
property resolves ~40% of the identified threat catalog.

---

*End of threat model.*
