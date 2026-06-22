# Helen Programming Agent

> Contract-first programming assistant written in Helen.

## Architecture

```
agents/
├── programming_agent.helen     # Main entry point (imports contracts)
├── contracts/                  # Contract definitions
│   └── contracts.helen         # All function implementations + protocols
├── skills/                     # Skill library
│   ├── SKILL_INDEX.md
│   ├── error-patterns/
│   ├── code-quality/
│   ├── testing/
│   └── architecture/
├── memory/                     # Agent memory
│   ├── MEMORY.md
│   └── USER.md
└── README.md
```

## Design

**Contract-first + TDD**: Protocols define interfaces, implementations satisfy contracts, Python tests verify behavior.

### Protocols

```helen
protocol SkillManagerContract {
    fn skill_create(name, category, content) -> map
    fn skill_read(name, category) -> map
    fn skill_update(name, category, content) -> map
    fn skill_delete(name, category) -> map
    fn skill_list() -> map
}

protocol SkillMatcherContract {
    fn extract_keywords(context) -> list
    fn match_skills(context) -> map
}

protocol SkillLearnerContract {
    fn determine_category(error) -> str
    fn learn_from_fix(error, fix, confirmed) -> map
}

protocol SkillEvolverContract {
    fn evolve_skill(skill_path, new_finding) -> map
}

protocol ProgrammingAgentContract {
    fn process_input(project_dir, user_input) -> map
    fn analyze_file(file_path) -> map
    fn run_project_tests(project_dir) -> map
}
```

### Error Codes

| Code | Meaning |
|------|---------|
| 1 | Validation error |
| 101 | IO error |
| 201 | Not found |
| 202 | Already exists |

## Usage

```bash
# Run the agent
helen agents/programming_agent.helen

# Check syntax
helen check agents/contracts/contracts.helen
helen check agents/programming_agent.helen

# Run tests
python -m pytest tests/agents/test_programming_agent.py -v
```

## Helen Features Used

- **Module imports** (v1.8) — `import "contracts/contracts.helen"`
- **Protocol declarations** (v1.7) — interface contracts
- **Pipe operator** (v1.8) — clean composition
- **regex_test** (v1.8) — boolean regex checks
- **Closures** (v1.7) — function references
- **&& / ||** (v1.7) — logical operators

## Skill Format

```markdown
---
name: skill-name
description: "Skill description"
category: error-patterns
---

# Skill Name

## Trigger
When this skill applies

## Steps
1. Step one
2. Step two

## Pitfalls
- Edge cases
```

## Self-Evolution Loop

```
Solve problem → User confirms → Extract pattern → Save as skill → Reuse next time
```
