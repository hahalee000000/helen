"""Tests for agent declaration with parameters and config."""

import pytest
from hellen.core.lexer import Scanner
from hellen.core.parser import Parser
from hellen.core.ast import (
    AgentDeclNode, AgentParamNode, ProgramNode, TypeNode, OptionalTypeNode,
)


def _parse(source: str) -> Parser:
    scanner = Scanner(source, file="<test>")
    tokens = scanner.scan_all()
    parser = Parser(tokens, scanner.errors)
    return parser


def _first_agent(parser: Parser) -> AgentDeclNode:
    prog = parser.parse()
    assert isinstance(prog, ProgramNode)
    assert len(prog.statements) >= 1
    return prog.statements[0]


class TestAgentDecl:
    def test_agent_simple(self):
        p = _parse('agent Test { prompt "hello" }')
        agent = _first_agent(p)
        assert isinstance(agent, AgentDeclNode)
        assert agent.name == "Test"

    def test_agent_with_params(self):
        p = _parse('agent Search(query: str) { prompt "search {{query}}" }')
        agent = _first_agent(p)
        assert isinstance(agent, AgentDeclNode)
        assert agent.name == "Search"

    def test_agent_param_with_default(self):
        p = _parse('agent Search(query: str = "default") { }')
        agent = _first_agent(p)
        assert isinstance(agent, AgentDeclNode)

    def test_agent_param_no_type(self):
        p = _parse('agent Test(x = 42) { }')
        agent = _first_agent(p)
        assert isinstance(agent, AgentDeclNode)

    def test_agent_multiple_params(self):
        p = _parse('agent Multi(a: int, b: str, c = true) { }')
        agent = _first_agent(p)
        assert isinstance(agent, AgentDeclNode)

    def test_agent_empty_params(self):
        p = _parse('agent NoParams() { prompt "hi" }')
        agent = _first_agent(p)
        assert isinstance(agent, AgentDeclNode)

    def test_agent_param_optional_type(self):
        p = _parse('agent Test(x: str?) { }')
        agent = _first_agent(p)
        assert isinstance(agent, AgentDeclNode)
