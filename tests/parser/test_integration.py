"""Integration test: complete Agent program with all Phase 1 features."""

import pytest
from hellen.core.lexer import Scanner
from hellen.core.parser import Parser
from hellen.core.ast import (
    ProgramNode, AgentDeclNode, MainBlockNode,
    TryStmtNode, LlmIfStmtNode, MatchStmtNode,
    FunctionDeclNode, CallNode, AsyncCallStmtNode,
    VarDeclNode, IfStmtNode, ForStmtNode,
)


def _parse(source: str) -> Parser:
    scanner = Scanner(source, file="<test>")
    tokens = scanner.scan_all()
    parser = Parser(tokens, scanner.errors)
    return parser


class TestIntegration:
    def test_full_agent_program(self):
        source = '''
agent SearchAgent(query: str, max_results: int = 10) {
    description "A search agent"
    model "gpt-4"

    prompt "Search for {{query}} with max {{max_results}} results"

    fn format_result(item: str) -> str {
        return "Result: " + item
    }

    main {
        let results = search(query)
        let formatted = []

        for item in results {
            let r = format_result(item)
            formatted.append(r)
        }

        llm if "Should we proceed?" {
            branch true {
                for item in formatted {
                    print(item)
                }
            }
            default {
                print("Aborted")
            }
        }

        try {
            async saveResults(formatted)
        catch Error e {
            print("Error: " + e)
        } finally {
            cleanup()
        }

        match status {
            case "success" {
                print("Done")
            }
            default {
                print("Unknown status")
            }
        }
    }
}
'''
        p = _parse(source)
        prog = p.parse()
        assert isinstance(prog, ProgramNode)
        assert len(prog.statements) == 1
        agent = prog.statements[0]
        assert isinstance(agent, AgentDeclNode)
        assert agent.name == "SearchAgent"

    def test_multiple_declarations(self):
        source = '''
fn helper(x: int) -> int { return x * 2 }

agent Agent1 { prompt "hello" }

agent Agent2(name: str) {
    main {
        let x = helper(5)
        if x > 5 { print(x) }
    }
}
'''
        p = _parse(source)
        prog = p.parse()
        assert len(prog.statements) == 3
