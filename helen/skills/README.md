# Helen Skills

Helen skill system — providing professional knowledge and workflows for AI agents.

## Directory Structure

```
~/helen/skills/                    ← Built-in skills (distributed with the language)
├── README.md                      ← This file
├── LICENSE-THIRD-PARTY.md         ← Third-party license notices
├── software-development/          ← Development methodology skills
│   ├── helen-language-development/   ← Helen language patterns and pitfalls
│   ├── helen-syntax/                 ← Helen syntax reference
│   ├── helen-stdlib/                 ← Standard library usage guide
│   ├── helen-agent-patterns/         ← Agent design patterns
│   ├── helen-testing/                ← Testing framework and TDD workflow
│   ├── helen-quality/                ← 7-dimension quality assessment tool
│   ├── code-quality/                 ← Code quality assessment methodology
│   ├── debugging/                    ← Debugging methodology
│   ├── test-driven-development/      ← TDD RED-GREEN-REFACTOR
│   ├── writing-plans/                ← Implementation plan writing
│   ├── plan/                         ← Plan mode (write-only, no execution)
│   └── subagent-driven-development/  ← Subagent execution workflow
└── devops/                        ← DevOps skills
    ├── hellen-consistency-checker/   ← Design document consistency checking
    └── github/                       ← GitHub workflow (PR, issue, CI/CD)
```

## Skill Search Priority

Helen searches for skills in the following order (higher priority overrides lower):

| Priority | Location | Description |
|----------|----------|-------------|
| 1 (highest) | `<project>/.helen/skills/` | **Project-level** — Skills specific to the current project |
| 2 | `~/.helen/skills/` | **User-level** — User's global skills |
| 3 | `<helen-install>/skills/` | **Built-in** — Distributed with Helen language (this directory) |
| 4 | `~/.hermes/skills/` | **Hermes fallback** — Compatible with Hermes Agent |
| 5 (lowest) | `~/.hermes/hermes-agent/skills/` | **Hermes agent skills** |

### Project-Level Skills

Create a `.helen/skills/` directory in your project root to add project-specific skills:

```
my-project/
├── .helen/
│   └── skills/
│       └── my-api/
│           └── SKILL.md       # Project API documentation
├── main.helen
└── agents/
```

Project-level skills have the highest priority and can override built-in and user skills.

## How Skills Work

Helen uses a **two-tier skill disclosure** mechanism:

1. **Tier 1 — Skill Index**: Lightweight metadata (name + description) injected into the `<available_skills>` section of the system prompt. Helps AI agents decide which skill to load.

2. **Tier 2 — Full Content**: When an agent needs a skill, it calls the `load_skill` tool to read the complete `SKILL.md` content.

## Skill Format

Each skill is a directory containing a `SKILL.md` file with YAML frontmatter:

```markdown
---
name: skill-name
description: "Skill description"
version: 1.0.0
author: Author Name
license: MIT
tags: [tag1, tag2]
---

# Skill Title

Skill content (in Markdown format)...
```

Skills can also include:
- `references/` — Reference documents
- `templates/` — Template files
- `scripts/` — Helper scripts
- `assets/` — Static resources

## Built-in Skills List

| Skill | Category | Description |
|-------|----------|-------------|
| `helen-language-development` | Helen-specific | Helen language patterns, pitfalls, best practices |
| `helen-syntax` | Helen-specific | Helen syntax reference (keywords, types, expressions) |
| `helen-stdlib` | Helen-specific | Usage guide for 193 standard library functions |
| `helen-agent-patterns` | Helen-specific | Agent design patterns (routing, concurrency, error handling) |
| `helen-testing` | Helen-specific | Testing framework and TDD workflow |
| `helen-quality` | Helen-specific | 7-dimension quality assessment tool (CLI + API) |
| `code-quality` | Development | 7-dimension code quality assessment methodology |
| `debugging` | Development | Systematic debugging methodology |
| `test-driven-development` | Development | TDD RED-GREEN-REFACTOR workflow |
| `writing-plans` | Development | Implementation plan writing guide |
| `plan` | Development | Plan mode (write plans only, no execution) |
| `subagent-driven-development` | Development | Subagent-driven development workflow |
| `hellen-consistency-checker` | DevOps | Design document and code consistency checking |
| `github` | DevOps | GitHub workflow (PR, issue, CI/CD) |

## Attribution

Most skills in this directory are derived from [Hermes Agent](https://github.com/NousResearch/hermes-agent) by Nous Research, used under the MIT license. See `LICENSE-THIRD-PARTY.md` for details.

Each skill directory contains an `ATTRIBUTION.md` file with specific attribution information.
