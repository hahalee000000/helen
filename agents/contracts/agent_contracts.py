"""Contracts for Helen Programming Agent system.

Defines interfaces for all agents in the system.
Follows contract-first + TDD development approach.
"""

from typing import Protocol, Any


# ── Skill Types ───────────────────────────────────────────────


class SkillMetadata(Protocol):
    """Metadata for a skill (from YAML frontmatter)."""
    
    @property
    def name(self) -> str: ...
    
    @property
    def description(self) -> str: ...
    
    @property
    def category(self) -> str: ...
    
    @property
    def tags(self) -> list[str]: ...
    
    @property
    def triggers(self) -> list[dict[str, str]]: ...
    
    @property
    def confidence(self) -> float: ...
    
    @property
    def occurrences(self) -> int: ...


class SkillContent(Protocol):
    """Full skill content."""
    
    @property
    def metadata(self) -> SkillMetadata: ...
    
    @property
    def body(self) -> str: ...
    
    @property
    def path(self) -> str: ...


# ── Skill Manager Contract ────────────────────────────────────


class SkillManagerContract(Protocol):
    """Contract for skill CRUD operations.
    
    Agent: agents/skill_manager.helen
    Parameters:
        action: str — "create" | "read" | "update" | "delete" | "list"
        name: str — skill name (e.g., "division-by-zero")
        category: str — skill category (e.g., "error-patterns")
        content: str — SKILL.md content (for create/update)
    
    Returns:
        map with keys:
            - status: str — "success" | "error"
            - message: str — human-readable result
            - path: str — skill file path (for create/read/update)
            - skills: list[str] — skill paths (for list)
    """
    
    def create(self, name: str, category: str, content: str) -> dict[str, Any]:
        """Create a new skill.
        
        Preconditions:
            - name is non-empty
            - category is one of: error-patterns, code-quality, testing, architecture
            - content is valid SKILL.md format (YAML frontmatter + Markdown)
        
        Postconditions:
            - File created at agents/skills/{category}/{name}/SKILL.md
            - SKILL_INDEX.md updated
            - Returns status="success" with path
        """
        ...
    
    def read(self, name: str, category: str) -> dict[str, Any]:
        """Read a skill's content.
        
        Preconditions:
            - Skill exists at agents/skills/{category}/{name}/SKILL.md
        
        Postconditions:
            - Returns status="success" with content
            - Returns status="error" if not found
        """
        ...
    
    def update(self, name: str, category: str, content: str) -> dict[str, Any]:
        """Update an existing skill.
        
        Preconditions:
            - Skill exists
            - content is valid SKILL.md format
        
        Postconditions:
            - File updated at agents/skills/{category}/{name}/SKILL.md
            - Returns status="success"
        """
        ...
    
    def delete(self, name: str, category: str) -> dict[str, Any]:
        """Delete a skill.
        
        Preconditions:
            - Skill exists
        
        Postconditions:
            - Directory removed at agents/skills/{category}/{name}/
            - SKILL_INDEX.md updated
            - Returns status="success"
        """
        ...
    
    def list_skills(self) -> dict[str, Any]:
        """List all skills.
        
        Postconditions:
            - Returns status="success" with skills list
            - Each skill has: name, category, path
        """
        ...


# ── Skill Matcher Contract ────────────────────────────────────


class SkillMatcherContract(Protocol):
    """Contract for skill search and matching.
    
    Agent: agents/skill_matcher.helen
    Parameters:
        context: str — error message, code snippet, or question
    
    Returns:
        map with keys:
            - matches: list[dict] — matched skills
            - keywords: list[str] — extracted keywords
            - count: int — number of matches
    """
    
    def match(self, context: str) -> dict[str, Any]:
        """Find matching skills for given context.
        
        Preconditions:
            - context is non-empty string
        
        Postconditions:
            - Extracts keywords from context
            - Searches SKILL_INDEX.md for matches
            - Returns matches sorted by confidence (descending)
            - Each match has: name, category, confidence, path
        """
        ...
    
    def extract_keywords(self, context: str) -> list[str]:
        """Extract searchable keywords from context.
        
        Examples:
            "Division by zero in divide()" → ["division", "zero"]
            "list index out of range" → ["index", "range"]
            "complexity too high" → ["complexity"]
        """
        ...


# ── Skill Learner Contract ────────────────────────────────────


class SkillLearnerContract(Protocol):
    """Contract for learning new skills from successful fixes.
    
    Agent: agents/skill_learner.helen
    Parameters:
        error: map — error information (type, message, location)
        fix: str — the fix that was applied
        confirmed: bool — whether user confirmed the fix worked
    
    Returns:
        map with keys:
            - status: str — "saved" | "skipped" | "error"
            - path: str — where skill was saved (if saved)
            - category: str — determined category
            - name: str — generated skill name
    """
    
    def learn(self, error: dict[str, Any], fix: str, confirmed: bool) -> dict[str, Any]:
        """Learn a new skill from a successful fix.
        
        Preconditions:
            - error has keys: type, message
            - fix is non-empty string
            - confirmed is bool
        
        Postconditions:
            - If confirmed=false: returns status="skipped"
            - If confirmed=true:
                - Generates SKILL.md content (via LLM)
                - Determines category from error type
                - Generates name from error message
                - Saves to agents/skills/{category}/{name}/SKILL.md
                - Updates SKILL_INDEX.md
                - Returns status="saved" with path
        """
        ...
    
    def determine_category(self, error: dict[str, Any]) -> str:
        """Determine skill category from error.
        
        Rules:
            - RuntimeError → "error-patterns"
            - QualityIssue → "code-quality"
            - TestFailure → "testing"
            - Architecture → "architecture"
            - Default → "general"
        """
        ...


# ── Skill Evolver Contract ────────────────────────────────────


class SkillEvolverContract(Protocol):
    """Contract for evolving existing skills.
    
    Agent: agents/skill_evolver.helen
    Parameters:
        skill_path: str — path to existing skill
        new_finding: str — new information discovered while using skill
    
    Returns:
        map with keys:
            - status: str — "evolved" | "error"
            - path: str — updated skill path
            - changes: str — description of changes
    """
    
    def evolve(self, skill_path: str, new_finding: str) -> dict[str, Any]:
        """Evolve an existing skill with new findings.
        
        Preconditions:
            - skill_path points to existing SKILL.md
            - new_finding is non-empty
        
        Postconditions:
            - Appends new finding to "Pitfalls" section
            - Increments occurrences count in frontmatter
            - Returns status="evolved"
        """
        ...


# ── Programming Agent Contract ────────────────────────────────


class ProgrammingAgentContract(Protocol):
    """Contract for the main programming agent orchestrator.
    
    Agent: agents/programming_agent.helen
    Parameters:
        project_dir: str — path to project directory
        user_input: str — user's question or task
    
    Returns:
        map with keys:
            - response: str — agent's response
            - skills_used: list[str] — skills that were matched
            - tests_passed: bool — whether tests pass after fix
            - quality_score: float — quality score after fix
    """
    
    def process(self, project_dir: str, user_input: str) -> dict[str, Any]:
        """Process user input and provide programming assistance.
        
        Workflow:
            1. Load agent memory (agents/memory/MEMORY.md)
            2. Search skills for matching patterns
            3. If skill matched: use skill to guide response
            4. If no skill: use LLM reasoning
            5. If code fix applied: run tests + quality check
            6. If fix successful: offer to save as new skill
            7. Update agent memory
        
        Postconditions:
            - Returns response with relevant information
            - skills_used lists any skills that were applied
            - If code was modified, tests_passed and quality_score reflect new state
        """
        ...
    
    def analyze_code(self, file_path: str) -> dict[str, Any]:
        """Analyze a Helen source file.
        
        Returns:
            - metrics: from analyze_code()
            - security: from check_security()
            - scores: from quality_score()
        """
        ...
    
    def run_tests(self, project_dir: str) -> dict[str, Any]:
        """Run tests for a project.
        
        Returns:
            - total: int
            - passed: int
            - failed: int
            - results: list[dict]
        """
        ...


# ── Skill Index Contract ──────────────────────────────────────


class SkillIndexContract(Protocol):
    """Contract for SKILL_INDEX.md management."""
    
    def rebuild(self) -> str:
        """Rebuild the skill index from all SKILL.md files.
        
        Postconditions:
            - Scans agents/skills/ recursively
            - Extracts metadata from each SKILL.md
            - Generates SKILL_INDEX.md
            - Returns path to index file
        """
        ...
    
    def search(self, keywords: list[str]) -> list[dict[str, Any]]:
        """Search index for matching skills.
        
        Postconditions:
            - Returns list of matching skills
            - Each has: name, category, description, confidence, path
        """
        ...
