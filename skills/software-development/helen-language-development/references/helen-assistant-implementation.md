# Helen Language Assistant Implementation

Reference implementation of a REPL extension: AI-powered language assistant.

## Helen Program: `helen/agent/helen_assistant.helen`

```helen
agent HelenAssistant(question: str, docs_path: str, source_dir: str) {
    prompt """You are an expert Helen language assistant. You help users:
1. Understand Helen syntax and semantics
2. Write Helen code (agents, functions, LLM integration)
3. Debug Helen programs (syntax errors, semantic errors, runtime errors)

You have access to:
- Helen documentation (tutorial.md)
- Helen source code (parser, interpreter, AST, etc.)

When answering questions about implementation details, internals, or advanced features,
reference the source code. Be concise, practical, and provide code examples when relevant.
Cite specific files and functions from the source code when appropriate."""
    
    functions {
        fn load_documentation() -> str {
            let tutorial = read_file(docs_path)
            return tutorial
        }
        
        fn load_source_code() -> str {
            let parser = read_file(source_dir + "core/parser.py")
            let interpreter = read_file(source_dir + "interpreter/interpreter.py")
            let ast = read_file(source_dir + "core/ast.py")
            let lexer = read_file(source_dir + "core/lexer.py")
            
            let sources = "# Helen Source Code\n\n"
            sources = sources + "## Parser (helen/core/parser.py)\n```\n" + parser + "\n```\n\n"
            sources = sources + "## Interpreter (helen/interpreter/interpreter.py)\n```\n" + interpreter + "\n```\n\n"
            sources = sources + "## AST (helen/core/ast.py)\n```\n" + ast + "\n```\n\n"
            sources = sources + "## Lexer (helen/core/lexer.py)\n```\n" + lexer + "\n```\n"
            
            return sources
        }
        
        fn build_context() -> str {
            let docs = load_documentation()
            let sources = load_source_code()
            
            let context = "# Helen Language Documentation\n\n" + docs + "\n\n---\n\n"
            context = context + sources + "\n---\n\n"
            context = context + "# User Question\n\n" + question
            return context
        }
    }
    
    main {
        let context = build_context()
        let answer = llm act context
        return answer
    }
}

main {
    let question = "How do I define an agent in Helen?"
    let docs_path = "docs/tutorial.md"  // Relative path for development
    let source_dir = "helen/"  // Relative path for development
    let answer = HelenAssistant(question, docs_path, source_dir)
    print(answer)
}
```

## REPL Integration: `helen/cli/repl.py`

```python
def _run_helen_assistant(question: str) -> str:
    from pathlib import Path
    from helen.core.lexer import Scanner
    from helen.core.parser import Parser
    from helen.core.errors import ErrorReporter
    from helen.interpreter.interpreter import Interpreter
    from helen.runtime.http_llm import HttpLLMRuntime
    
    # Module-relative path resolution
    import helen.cli.repl as repl_module
    module_dir = Path(repl_module.__file__).parent.parent  # helen/cli -> helen/
    assistant_path = module_dir / "agent" / "helen_assistant.helen"
    docs_path = module_dir.parent / "docs" / "tutorial.md"
    source_dir = module_dir
    
    # Validate all paths
    if not assistant_path.exists():
        return f"Error: Helen assistant not found at {assistant_path}"
    if not docs_path.exists():
        return f"Error: Documentation not found at {docs_path}"
    if not source_dir.exists():
        return f"Error: Source directory not found at {source_dir}"
    
    source = assistant_path.read_text(encoding="utf-8")
    
    # Parameter injection via string replacement
    modified_source = source.replace(
        'let question = "How do I define an agent in Helen?"',
        f'let question = "{question}"'
    ).replace(
        'let docs_path = "docs/tutorial.md"  // Relative path for development',
        f'let docs_path = "{docs_path}"  // Absolute path from REPL'
    ).replace(
        'let source_dir = "helen/"  // Relative path for development',
        f'let source_dir = "{source_dir}/"  // Absolute path from REPL'
    )
    
    # Parse and execute
    errors = ErrorReporter()
    scanner = Scanner(source=modified_source, file=str(assistant_path))
    tokens = scanner.scan_all()
    parser = Parser(tokens, errors=errors)
    program = parser.parse()
    
    if errors.has_errors:
        return f"Parse error: {errors.format_report()}"
    
    llm_runtime = HttpLLMRuntime()
    interp = Interpreter(errors=errors, llm_runtime=llm_runtime)
    
    try:
        result = interp.interpret(program)
        return result if result else "No response generated."
    except Exception as e:
        return f"Runtime error: {e}"
```

## Key Design Decisions

1. **Three parameters**: `question`, `docs_path`, `source_dir` — separates concerns
2. **Load both docs and source**: Comprehensive coverage for syntax AND implementation questions
3. **Module-relative paths**: Works from any working directory
4. **String replacement injection**: Simple, no AST manipulation needed
5. **Standalone execution**: Helen program can run independently for testing

## Evolution History

- **v1**: Only loaded docs, used relative paths → Failed from different directories
- **v2**: Added absolute path resolution → Fixed CWD issue  
- **v3**: Added source code loading → Can answer implementation questions
- **v4**: Added `source_dir` parameter → Complete knowledge base
