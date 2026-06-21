# Helen Programming Agent — Memory

> Agent-level persistent memory. Tracks learnings, preferences, and environment info.

## Learnings

- Division by zero is the most common runtime error
- Users prefer snake_case naming convention
- Quality threshold is typically 7.5
- Helen does not support closures (dynamic scoping, not lexical)
- Anonymous functions as arguments are not supported in Helen

## User Preferences

- Coding style: functional-first
- Test framework: test_suite/test_case API
- Quality requirement: 7-dimension score ≥ 7.5
- Git workflow: commit + push in one step
- Language: Chinese narrative, English code/paths

## Environment

- System: Linux (1.8GB RAM + 8GB swap)
- Python: 3.11.15
- Helen repo: ~/helen/ (master branch)
- Tests run in batches to avoid OOM
- Memory-constrained: prefer asyncio with zero threads

## Known Patterns

- Division by zero → add `assert divisor != 0`
- Empty list access → check `len > 0`
- High complexity → extract sub-functions
- Low security score → add input validation
