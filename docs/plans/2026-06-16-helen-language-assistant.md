# Helen Language Assistant Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Build an AI-powered Helen language assistant integrated into the REPL, capable of answering questions about Helen, writing Helen code, and debugging Helen programs.

**Architecture:** 
- Create a `HelenAssistant` Agent with a comprehensive prompt containing Helen documentation and source code context
- Add REPL command `:ask <question>` to invoke the assistant
- Use existing `HttpLLMRuntime` for LLM calls
- Implement knowledge base loader to inject Helen docs/source into assistant context

**Tech Stack:** Python 3.11, Helen Agent system, HttpLLMRuntime, existing REPL infrastructure

---

## Phase 1: Knowledge Base Infrastructure

### Task 1.1: Create Knowledge Base Loader Contract

**Objective:** Define the interface for loading Helen documentation and source code

**Files:**
- Create: `helen/assistant/knowledge.py`
- Test: `tests/assistant/test_knowledge.py`

**Step 1: Write failing test**

```python
# tests/assistant/test_knowledge.py
import pytest
from helen.assistant.knowledge import KnowledgeBase

def test_knowledge_base_loads_tutorial():
    """KnowledgeBase loads Helen tutorial documentation."""
    kb = KnowledgeBase(docs_dir="docs/")
    content = kb.get_tutorial_content()
    assert "agent" in content.lower()
    assert "llm act" in content.lower()

def test_knowledge_base_loads_source_code():
    """KnowledgeBase loads Helen source code structure."""
    kb = KnowledgeBase(source_dir="helen/")
    structure = kb.get_source_structure()
    assert "parser.py" in structure
    assert "interpreter.py" in structure

def test_knowledge_base_generates_context():
    """KnowledgeBase generates LLM context from docs and source."""
    kb = KnowledgeBase(docs_dir="docs/", source_dir="helen/")
    context = kb.generate_context()
    assert len(context) > 1000  # Substantial context
    assert "Helen" in context
```

**Step 2: Run test to verify failure**

```bash
pytest tests/assistant/test_knowledge.py -v
```

Expected: FAIL — "ModuleNotFoundError: No module named 'helen.assistant'"

**Step 3: Write minimal implementation**

```python
# helen/assistant/__init__.py
"""Helen language assistant package."""

# helen/assistant/knowledge.py
"""Knowledge base for Helen language assistant."""

from pathlib import Path
from typing import Optional


class KnowledgeBase:
    """Loads and manages Helen documentation and source code context.
    
    Args:
        docs_dir: Path to Helen documentation directory.
        source_dir: Path to Helen source code directory.
    """
    
    def __init__(self, docs_dir: str = "docs/", source_dir: str = "helen/"):
        self.docs_dir = Path(docs_dir)
        self.source_dir = Path(source_dir)
    
    def get_tutorial_content(self) -> str:
        """Load Helen tutorial documentation."""
        tutorial_path = self.docs_dir / "tutorial.md"
        if tutorial_path.exists():
            return tutorial_path.read_text(encoding="utf-8")
        return ""
    
    def get_source_structure(self) -> str:
        """Get Helen source code structure."""
        files = []
        for py_file in self.source_dir.rglob("*.py"):
            files.append(str(py_file.relative_to(self.source_dir)))
        return "\n".join(sorted(files))
    
    def generate_context(self) -> str:
        """Generate comprehensive context for LLM."""
        tutorial = self.get_tutorial_content()
        structure = self.get_source_structure()
        
        context = f"""# Helen Language Documentation

{tutorial}

# Helen Source Code Structure

{structure}
"""
        return context
```

**Step 4: Run test to verify pass**

```bash
pytest tests/assistant/test_knowledge.py -v
```

Expected: 3 passed

**Step 5: Commit**

```bash
git add helen/assistant/ tests/assistant/
git commit -m "feat: add knowledge base infrastructure for Helen assistant"
```

---

### Task 1.2: Implement Source Code Snippet Extraction

**Objective:** Extract relevant source code snippets for context

**Files:**
- Modify: `helen/assistant/knowledge.py`
- Test: `tests/assistant/test_knowledge.py`

**Step 1: Write failing test**

```python
def test_knowledge_base_extracts_parser_snippets():
    """KnowledgeBase extracts key parser code snippets."""
    kb = KnowledgeBase(source_dir="helen/")
    snippets = kb.get_key_source_snippets()
    assert "class Parser" in snippets
    assert "def parse" in snippets

def test_knowledge_base_extracts_interpreter_snippets():
    """KnowledgeBase extracts key interpreter code snippets."""
    kb = KnowledgeBase(source_dir="helen/")
    snippets = kb.get_key_source_snippets()
    assert "class Interpreter" in snippets
    assert "def visit_" in snippets
```

**Step 2: Run test to verify failure**

```bash
pytest tests/assistant/test_knowledge.py::test_knowledge_base_extracts_parser_snippets -v
```

Expected: FAIL — "AttributeError: 'KnowledgeBase' object has no attribute 'get_key_source_snippets'"

**Step 3: Write minimal implementation**

```python
# Add to helen/assistant/knowledge.py

def get_key_source_snippets(self) -> str:
    """Extract key source code snippets (parser, interpreter, AST)."""
    snippets = []
    
    # Parser class definition
    parser_path = self.source_dir / "core" / "parser.py"
    if parser_path.exists():
        content = parser_path.read_text(encoding="utf-8")
        # Extract class Parser and first 50 lines
        lines = content.split("\n")
        for i, line in enumerate(lines):
            if "class Parser" in line:
                snippets.append("\n".join(lines[i:i+50]))
                break
    
    # Interpreter class definition
    interp_path = self.source_dir / "interpreter" / "interpreter.py"
    if interp_path.exists():
        content = interp_path.read_text(encoding="utf-8")
        lines = content.split("\n")
        for i, line in enumerate(lines):
            if "class Interpreter" in line:
                snippets.append("\n".join(lines[i:i+50]))
                break
    
    return "\n\n".join(snippets)
```

**Step 4: Run test to verify pass**

```bash
pytest tests/assistant/test_knowledge.py -v
```

Expected: 5 passed

**Step 5: Commit**

```bash
git add helen/assistant/knowledge.py tests/assistant/test_knowledge.py
git commit -m "feat: add source code snippet extraction to knowledge base"
```

---

## Phase 2: Helen Assistant Agent

### Task 2.1: Create Helen Assistant Agent Contract

**Objective:** Define the HelenAssistant agent that uses knowledge base

**Files:**
- Create: `helen/assistant/agent.py`
- Test: `tests/assistant/test_agent.py`

**Step 1: Write failing test**

```python
# tests/assistant/test_agent.py
import pytest
from helen.assistant.agent import HelenAssistant
from helen.runtime.http_llm import HttpLLMRuntime

def test_helen_assistant_initializes_with_knowledge():
    """HelenAssistant loads knowledge base on initialization."""
    runtime = HttpLLMRuntime()
    assistant = HelenAssistant(runtime=runtime)
    assert assistant.knowledge is not None
    assert len(assistant.system_prompt) > 500

def test_helen_assistant_system_prompt_contains_helen_docs():
    """HelenAssistant system prompt includes Helen documentation."""
    runtime = HttpLLMRuntime()
    assistant = HelenAssistant(runtime=runtime)
    assert "Helen" in assistant.system_prompt
    assert "agent" in assistant.system_prompt.lower()
```

**Step 2: Run test to verify failure**

```bash
pytest tests/assistant/test_agent.py -v
```

Expected: FAIL — "ModuleNotFoundError: No module named 'helen.assistant.agent'"

**Step 3: Write minimal implementation**

```python
# helen/assistant/agent.py
"""Helen language assistant agent."""

from helen.assistant.knowledge import KnowledgeBase
from helen.runtime.llm_runtime import LLMRuntime


class HelenAssistant:
    """AI-powered Helen language assistant.
    
    Uses LLM to answer questions about Helen, write code, and debug.
    
    Args:
        runtime: LLM runtime for making calls.
        docs_dir: Path to Helen documentation.
        source_dir: Path to Helen source code.
    """
    
    def __init__(
        self,
        runtime: LLMRuntime,
        docs_dir: str = "docs/",
        source_dir: str = "helen/"
    ):
        self.runtime = runtime
        self.knowledge = KnowledgeBase(docs_dir=docs_dir, source_dir=source_dir)
        self.system_prompt = self._build_system_prompt()
    
    def _build_system_prompt(self) -> str:
        """Build comprehensive system prompt with Helen knowledge."""
        context = self.knowledge.generate_context()
        snippets = self.knowledge.get_key_source_snippets()
        
        prompt = f"""You are an expert Helen language assistant. You help users:
1. Answer questions about Helen syntax, semantics, and features
2. Write Helen code (agents, functions, LLM integration)
3. Debug Helen programs (syntax errors, semantic errors, runtime errors)

# Helen Language Documentation

{context}

# Key Source Code Snippets

{snippets}

When answering:
- Be concise and practical
- Provide code examples when relevant
- Reference specific parts of the documentation
- Explain errors clearly with fix suggestions
"""
        return prompt
    
    def ask(self, question: str) -> str:
        """Ask the assistant a question.
        
        Args:
            question: User's question about Helen.
        
        Returns:
            Assistant's response.
        """
        # Use LLM runtime to generate response
        response = self.runtime.act(
            description=f"{self.system_prompt}\n\nUser question: {question}",
            target="HelenAssistant",
            args={}
        )
        return response if response else "I couldn't generate a response."
```

**Step 4: Run test to verify pass**

```bash
pytest tests/assistant/test_agent.py -v
```

Expected: 2 passed

**Step 5: Commit**

```bash
git add helen/assistant/agent.py tests/assistant/test_agent.py
git commit -m "feat: add HelenAssistant agent with knowledge integration"
```

---

### Task 2.2: Implement Question Answering

**Objective:** Implement the `ask` method to answer Helen questions

**Files:**
- Modify: `helen/assistant/agent.py`
- Test: `tests/assistant/test_agent.py`

**Step 1: Write failing test**

```python
def test_helen_assistant_answers_syntax_question():
    """HelenAssistant answers questions about Helen syntax."""
    runtime = HttpLLMRuntime()
    assistant = HelenAssistant(runtime=runtime)
    response = assistant.ask("How do I define an agent in Helen?")
    assert "agent" in response.lower()
    assert len(response) > 50

def test_helen_assistant_answers_llm_question():
    """HelenAssistant answers questions about LLM integration."""
    runtime = HttpLLMRuntime()
    assistant = HelenAssistant(runtime=runtime)
    response = assistant.ask("What is llm act?")
    assert "llm" in response.lower()
```

**Step 2: Run test to verify failure**

```bash
pytest tests/assistant/test_agent.py::test_helen_assistant_answers_syntax_question -v
```

Expected: FAIL — "assert 'agent' in response.lower()" (because `act` returns empty)

**Step 3: Write minimal implementation**

```python
# Update ask method in helen/assistant/agent.py

def ask(self, question: str) -> str:
    """Ask the assistant a question.
    
    Args:
        question: User's question about Helen.
    
    Returns:
        Assistant's response.
    """
    # Construct full prompt with system context and user question
    full_prompt = f"{self.system_prompt}\n\nUser question: {question}"
    
    # Use LLM runtime's act method directly
    response = self.runtime.act(full_prompt)
    
    if not response or len(response.strip()) < 10:
        return "I couldn't generate a meaningful response. Please try rephrasing your question."
    
    return response.strip()
```

**Step 4: Run test to verify pass**

```bash
pytest tests/assistant/test_agent.py -v
```

Expected: 4 passed

**Step 5: Commit**

```bash
git add helen/assistant/agent.py tests/assistant/test_agent.py
git commit -m "feat: implement question answering in HelenAssistant"
```

---

## Phase 3: REPL Integration

### Task 3.1: Add :ask Command to REPL

**Objective:** Integrate HelenAssistant into REPL with `:ask` command

**Files:**
- Modify: `helen/cli/repl.py`
- Test: `tests/cli/test_repl_assistant.py`

**Step 1: Write failing test**

```python
# tests/cli/test_repl_assistant.py
import pytest
from unittest.mock import Mock, patch
from helen.cli.repl import _handle_repl_command
from helen.interpreter.interpreter import Interpreter
from helen.semantic.analyzer import SemanticAnalyzer
from helen.core.errors import ErrorReporter

def test_repl_ask_command_invokes_assistant():
    """:ask command invokes HelenAssistant."""
    errors = ErrorReporter()
    interp = Interpreter(errors=errors)
    analyzer = SemanticAnalyzer(errors)
    
    with patch('helen.cli.repl.HelenAssistant') as MockAssistant:
        mock_instance = Mock()
        mock_instance.ask.return_value = "Helen agents are defined with 'agent' keyword."
        MockAssistant.return_value = mock_instance
        
        result = _handle_repl_command(":ask How do I define an agent?", interp, analyzer)
        
        assert result is True  # Command was handled
        mock_instance.ask.assert_called_once_with("How do I define an agent?")

def test_repl_ask_command_prints_response():
    """:ask command prints assistant response."""
    errors = ErrorReporter()
    interp = Interpreter(errors=errors)
    analyzer = SemanticAnalyzer(errors)
    
    with patch('helen.cli.repl.HelenAssistant') as MockAssistant:
        mock_instance = Mock()
        mock_instance.ask.return_value = "Test response"
        MockAssistant.return_value = mock_instance
        
        with patch('builtins.print') as mock_print:
            _handle_repl_command(":ask test question", interp, analyzer)
            mock_print.assert_called()
```

**Step 2: Run test to verify failure**

```bash
pytest tests/cli/test_repl_assistant.py -v
```

Expected: FAIL — "NameError: name 'HelenAssistant' is not defined"

**Step 3: Write minimal implementation**

```python
# Add to helen/cli/repl.py imports
from helen.assistant.agent import HelenAssistant

# Add to _handle_repl_command function

if cmd == ":ask":
    if not arg:
        print("Usage: :ask <question>")
        return True
    
    # Create assistant and ask question
    assistant = HelenAssistant(runtime=interp.llm_runtime)
    response = assistant.ask(arg)
    print(f"\n{response}\n")
    return True

# Update :help command to include :ask
if cmd == ":help":
    print("REPL commands:")
    print("  :help             Show this help message")
    print("  :reset            Clear all definitions (functions, agents)")
    print("  :list             List all defined functions and agents")
    print("  :undefine <name>  Remove a function or agent definition")
    print("  :ask <question>   Ask the Helen language assistant")
    print("  exit              Exit the REPL")
    return True
```

**Step 4: Run test to verify pass**

```bash
pytest tests/cli/test_repl_assistant.py -v
```

Expected: 2 passed

**Step 5: Commit**

```bash
git add helen/cli/repl.py tests/cli/test_repl_assistant.py
git commit -m "feat: add :ask command to REPL for Helen assistant"
```

---

### Task 3.2: Add :assistant Command (Alternative Syntax)

**Objective:** Provide `:assistant` as alternative to `:ask`

**Files:**
- Modify: `helen/cli/repl.py`
- Test: `tests/cli/test_repl_assistant.py`

**Step 1: Write failing test**

```python
def test_repl_assistant_command_alias():
    """:assistant command is alias for :ask."""
    errors = ErrorReporter()
    interp = Interpreter(errors=errors)
    analyzer = SemanticAnalyzer(errors)
    
    with patch('helen.cli.repl.HelenAssistant') as MockAssistant:
        mock_instance = Mock()
        mock_instance.ask.return_value = "Response"
        MockAssistant.return_value = mock_instance
        
        result = _handle_repl_command(":assistant test", interp, analyzer)
        
        assert result is True
        mock_instance.ask.assert_called_once_with("test")
```

**Step 2: Run test to verify failure**

```bash
pytest tests/cli/test_repl_assistant.py::test_repl_assistant_command_alias -v
```

Expected: FAIL — "Unknown command: :assistant"

**Step 3: Write minimal implementation**

```python
# Add to _handle_repl_command function

if cmd in (":ask", ":assistant"):
    if not arg:
        print(f"Usage: {cmd} <question>")
        return True
    
    assistant = HelenAssistant(runtime=interp.llm_runtime)
    response = assistant.ask(arg)
    print(f"\n{response}\n")
    return True

# Update :help
if cmd == ":help":
    print("REPL commands:")
    print("  :help             Show this help message")
    print("  :reset            Clear all definitions (functions, agents)")
    print("  :list             List all defined functions and agents")
    print("  :undefine <name>  Remove a function or agent definition")
    print("  :ask <question>   Ask the Helen language assistant")
    print("  :assistant <q>    Alias for :ask")
    print("  exit              Exit the REPL")
    return True
```

**Step 4: Run test to verify pass**

```bash
pytest tests/cli/test_repl_assistant.py -v
```

Expected: 3 passed

**Step 5: Commit**

```bash
git add helen/cli/repl.py tests/cli/test_repl_assistant.py
git commit -m "feat: add :assistant command as alias for :ask"
```

---

## Phase 4: Documentation and Examples

### Task 4.1: Update Tutorial with Assistant Examples

**Objective:** Document the Helen assistant feature in tutorial

**Files:**
- Modify: `docs/tutorial.md`
- Modify: `~/wiki/helen/tutorial/09-repl.md` (if exists) or create new

**Step 1: Add assistant section to tutorial**

```markdown
## 11. Helen Language Assistant

Helen REPL includes a built-in AI assistant that can help you:
- Answer questions about Helen syntax and features
- Write Helen code (agents, functions, LLM integration)
- Debug Helen programs

### Using the Assistant

In the REPL, use the `:ask` or `:assistant` command:

```
>>> :ask How do I define an agent in Helen?

Helen agents are defined using the `agent` keyword:

```helen
agent Translator {
    prompt "You are a translator."
    main {
        llm act
    }
}
```

>>> :ask What is llm act?

`llm act` is an expression that calls the LLM with the agent's prompt template...
```

**Step 2: Commit**

```bash
git add docs/tutorial.md
git commit -m "docs: add Helen assistant section to tutorial"
```

---

## Phase 5: Testing and Polish

### Task 5.1: Integration Test

**Objective:** End-to-end test of assistant in REPL

**Files:**
- Create: `tests/integration/test_repl_assistant_integration.py`

**Step 1: Write integration test**

```python
# tests/integration/test_repl_assistant_integration.py
import pytest
from unittest.mock import patch, MagicMock
from helen.cli.repl import repl_command

def test_repl_assistant_integration():
    """Full integration test of :ask command in REPL."""
    with patch('builtins.input') as mock_input:
        with patch('helen.cli.repl.HelenAssistant') as MockAssistant:
            # Simulate user input
            mock_input.side_effect = [
                ":ask How do I define a function?",
                "exit"
            ]
            
            # Mock assistant response
            mock_instance = MagicMock()
            mock_instance.ask.return_value = "Functions are defined with 'fn' keyword."
            MockAssistant.return_value = mock_instance
            
            # Run REPL
            with patch('builtins.print'):
                result = repl_command()
            
            assert result == 0
            mock_instance.ask.assert_called()
```

**Step 2: Run integration test**

```bash
pytest tests/integration/test_repl_assistant_integration.py -v
```

Expected: 1 passed

**Step 3: Commit**

```bash
git add tests/integration/test_repl_assistant_integration.py
git commit -m "test: add integration test for REPL assistant"
```

---

## Summary

This plan implements a Helen language assistant with:

1. **Knowledge Base** - Loads Helen docs and source code
2. **HelenAssistant Agent** - Uses LLM to answer questions
3. **REPL Integration** - `:ask` and `:assistant` commands
4. **Documentation** - Tutorial updates with examples
5. **Testing** - Unit tests + integration tests

**Total Tasks:** 11 tasks across 5 phases
**Estimated Time:** 2-3 hours with TDD
**Test Coverage:** 10+ tests covering all functionality

Ready to execute using subagent-driven-development!
