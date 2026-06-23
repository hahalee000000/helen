"""Tests for Helen language assistant (TDD).

The Helen assistant is a Helen program that:
1. Loads Helen documentation
2. Builds context with the documentation
3. Uses LLM to answer questions about Helen
"""

import pytest
from pathlib import Path
from helen.core.lexer import Scanner
from helen.core.parser import Parser
from helen.core.errors import ErrorReporter
from helen.interpreter.interpreter import Interpreter
from helen.runtime.http_llm import HttpLLMRuntime


def _format_errors(errors: ErrorReporter) -> str:
    """格式化错误报告用于测试断言。"""
    return "\n".join(str(e) for e in errors.errors)


class TestHelenAssistantProgram:
    """Test the Helen assistant Helen program."""

    def test_helen_assistant_program_exists(self):
        """Helen assistant program file exists."""
        assistant_path = Path("helen/agent/helen_assistant.helen")
        assert assistant_path.exists(), "helen/agent/helen_assistant.helen should exist"

    def test_helen_assistant_loads_documentation(self):
        """Helen assistant can load Helen documentation."""
        source = """
agent HelenAssistant(question: str, docs_path: str, source_dir: str) {
    prompt "You are a Helen language assistant."
    
    functions {
        fn load_docs(): str {
            return read_file(docs_path)
        }
    }
    
    main {
        let docs = load_docs()
        return docs
    }
}

main {
    let result = HelenAssistant("test", "docs/tutorial.md", "helen/")
    return result
}
"""
        errors = ErrorReporter()
        scanner = Scanner(source=source, file="<test>")
        tokens = scanner.scan_all()
        parser = Parser(tokens, errors=errors)
        program = parser.parse()
        
        assert not errors.has_errors, f"Parse errors: {_format_errors(errors)}"
        
        llm_runtime = HttpLLMRuntime()
        interp = Interpreter(errors=errors, llm_runtime=llm_runtime)
        result = interp.interpret(program)
        
        # Should load documentation content
        assert result is not None
        assert len(result) > 100, "Should load substantial documentation"
        assert "agent" in result.lower(), "Documentation should mention 'agent'"

    def test_helen_assistant_builds_context(self):
        """Helen assistant builds context with question."""
        source = """
agent HelenAssistant(question: str, docs_path: str, source_dir: str) {
    prompt "You are a Helen language assistant."
    
    functions {
        fn build_context(): str {
            let docs = read_file(docs_path)
            return "Documentation:\\n" + docs + "\\n\\nQuestion: " + question
        }
    }
    
    main {
        let context = build_context()
        return context
    }
}

main {
    let result = HelenAssistant("How to define an agent?", "docs/tutorial.md", "helen/")
    return result
}
"""
        errors = ErrorReporter()
        scanner = Scanner(source=source, file="<test>")
        tokens = scanner.scan_all()
        parser = Parser(tokens, errors=errors)
        program = parser.parse()
        
        assert not errors.has_errors
        
        llm_runtime = HttpLLMRuntime()
        interp = Interpreter(errors=errors, llm_runtime=llm_runtime)
        result = interp.interpret(program)
        
        # Should build context with question
        assert "Question:" in result
        assert "How to define an agent?" in result
        assert "Documentation:" in result

    def test_helen_assistant_answers_question(self):
        """Helen assistant uses LLM to answer questions."""
        source = """
agent HelenAssistant(question: str, docs_path: str, source_dir: str) {
    prompt "You are a Helen language assistant. Answer questions about Helen."
    
    functions {
        fn build_context(): str {
            let docs = read_file(docs_path)
            return "Helen Documentation:\\n" + docs + "\\n\\nUser question: " + question
        }
    }
    
    main {
        let context = build_context()
        let answer = llm act context
        return answer
    }
}

main {
    let result = HelenAssistant("What is an agent?", "docs/tutorial.md", "helen/")
    return result
}
"""
        errors = ErrorReporter()
        scanner = Scanner(source=source, file="<test>")
        tokens = scanner.scan_all()
        parser = Parser(tokens, errors=errors)
        program = parser.parse()
        
        assert not errors.has_errors
        
        llm_runtime = HttpLLMRuntime()
        interp = Interpreter(errors=errors, llm_runtime=llm_runtime)
        result = interp.interpret(program)
        
        # Should get LLM response
        assert result is not None
        assert len(result) > 50, "LLM should provide substantial answer"
        # Response should be relevant to the question
        assert "agent" in result.lower() or "helen" in result.lower()

    def test_helen_assistant_loads_source_code(self):
        """Helen assistant can load source code files."""
        source = """
agent HelenAssistant(question: str, docs_path: str, source_dir: str) {
    prompt "You are a Helen language assistant."
    
    functions {
        fn load_sources(): str {
            let parser = read_file(source_dir + "core/parser.py")
            return "Parser source loaded: " + str(len(parser)) + " chars"
        }
    }
    
    main {
        let result = load_sources()
        return result
    }
}

main {
    let result = HelenAssistant("test", "docs/tutorial.md", "helen/")
    return result
}
"""
        errors = ErrorReporter()
        scanner = Scanner(source=source, file="<test>")
        tokens = scanner.scan_all()
        parser = Parser(tokens, errors=errors)
        program = parser.parse()
        
        assert not errors.has_errors, f"Parse errors: {_format_errors(errors)}"
        
        llm_runtime = HttpLLMRuntime()
        interp = Interpreter(errors=errors, llm_runtime=llm_runtime)
        result = interp.interpret(program)
        
        # Should load source code
        assert result is not None
        assert "Parser source loaded" in result
        assert "chars" in result
