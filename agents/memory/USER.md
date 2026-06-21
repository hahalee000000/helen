# Helen Programming Agent — User Profile

> User preferences and working style.

## Communication

- Prefers Chinese for narrative/explanations
- English for code, paths, and technical terms
- Wants comprehensive test coverage
- Expects git commit AND push for all changes

## Development Style

- Plan-first, then refine, then execute
- Contract-first + TDD for language development
- Systematic quality improvement cycles
- Prefers grounded answers over hallucinations

## Quality Standards

- 7-dimension quality assessment framework
- Actionable P0/P1/P2 priorities with file locations
- Verification after fixes (tests pass, flake8=0, coverage improved)
- Followed by commit + push

## Technical Constraints

- Memory-constrained environment (1.8GB RAM)
- Tests must run in batches to avoid OOM
- Prefers asyncio with zero threads
- Helen repo uses master branch (not main)
