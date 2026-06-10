"""Extract and test all helen code blocks from the tutorial."""
import re
import sys
import os
from pathlib import Path

# Add project root to path
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
print(f"Project root: {ROOT}")
print(f"Python: {sys.executable}")

from helen.core.errors import ErrorReporter, ErrorCode
from helen.core.lexer import Scanner
from helen.core.parser import Parser
from helen.semantic.analyzer import SemanticAnalyzer
from helen.interpreter.interpreter import Interpreter
from helen.runtime.llm_runtime import MockLLMRuntime

TUTORIAL_DIR = Path("/home/admin/wiki/helen/tutorial")


def extract_helen_blocks(text: str) -> list[tuple[str, str]]:
    """Extract helen code blocks from markdown."""
    blocks = []
    pattern = re.compile(r"```(\w+)?\n(.*?)```", re.DOTALL)
    for match in pattern.finditer(text):
        lang = match.group(1)
        code = match.group(2).strip()
        if lang != "helen":
            continue
            
        has_fail = "❌" in code or "Error:" in code
        lines = []
        for line in code.split("\n"):
            line = line.strip()
            if line.startswith("Error:") or line.startswith("// ❌") or line.startswith("// ✅"):
                continue
            if "// ❌" in line:
                line = line.split("// ❌")[0].strip()
            if "// ✅" in line:
                line = line.split("// ✅")[0].strip()
            if line:
                lines.append(line)
                
        source = "\n".join(lines)
        if source:
            blocks.append((source, "fail" if has_fail else "ok"))
            
    return blocks


def run_source(source: str, filename: str = "<test>") -> tuple[bool, str]:
    """Run a helen source string with safety checks."""
    # Skip features not fully implemented or requiring external runtime
    if "while (true)" in source or "while (1)" in source:
        return False, "Skipped (infinite loop)"
    # While loops without break are dangerous in tutorial tests
    if "while (" in source and "break" not in source:
        return False, "Skipped (while without break)"
        
    if "async " in source or "await " in source:
        return False, "Skipped (async)"
    if "llm " in source:
        return False, "Skipped (LLM)"
    if "import " in source:
        return False, "Skipped (import - requires file fixtures)"
    # try/catch blocks reference undeclared agents/functions as examples
    if "try {" in source:
        return False, "Skipped (try/catch - uses undeclared examples)"
        
    errors = ErrorReporter()
    llm_runtime = MockLLMRuntime()
    interp = Interpreter(errors=errors, llm_runtime=llm_runtime)
    analyzer = SemanticAnalyzer(errors, base_dir=".")

    try:
        scanner = Scanner(source=source, file=filename)
        tokens = scanner.scan_all()
    except Exception as e:
        return False, str(e)

    try:
        parser = Parser(tokens, errors=errors)
        program = parser.parse()
    except Exception as e:
        return False, str(e)

    if errors.has_errors:
        return False, "Syntax error"

    try:
        analyzer.analyze(program)
    except Exception as e:
        return False, str(e)

    if errors.has_errors:
        return False, "Semantic error"

    try:
        interp.interpret(program)
    except Exception as e:
        return False, f"RuntimeError: {e}"

    if errors.has_errors:
        return False, "Runtime error"

    return True, "OK"


def main():
    print("Starting tutorial tests...")
    total = 0
    passed = 0
    failed = 0
    skipped = 0
    
    for md_file in sorted(TUTORIAL_DIR.glob("*.md")):
        print(f"\n{'='*60}", flush=True)
        print(f"Testing: {md_file.name}", flush=True)
        print(f"{'='*60}", flush=True)
        
        content = md_file.read_text()
        blocks = extract_helen_blocks(content)
        print(f"  Found {len(blocks)} blocks", flush=True)
        
        for i, (source, expected) in enumerate(blocks, 1):
            total += 1
            print(f"  Running block {i}...", flush=True)
            ok, msg = run_source(source, f"{md_file.name}:{i}")
            print(f"  Done block {i}: {msg[:50]}", flush=True)
            
            if msg.startswith("Skipped"):
                skipped += 1
                status = "SKIP"
            elif (ok and expected == "ok") or (not ok and expected == "fail"):
                passed += 1
                status = "PASS"
            else:
                failed += 1
                status = "FAIL"
                
            print(f"  [{status}] Block {i} (expected: {expected})")
            if status == "FAIL":
                print(f"    Source (first 60 chars): {source[:60]}...")
                print(f"    Error: {msg}")
                
    print(f"\n{'='*60}")
    print(f"SUMMARY: {passed} passed, {failed} failed, {skipped} skipped (Total: {total})")
    print(f"{'='*60}")
    
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
