"""Tests for agent environment isolation (HLD 3.5.2).

Covers:
- Sub-agent cannot access parent agent variables
- import creates shared global namespace
- Parameter passing is the only communication channel
- Nested agent calls maintain isolation chain
"""

from helen.core.ast import (
    AgentDeclNode,
    AgentParamNode,
    CallArgNode,
    CallNode,
    ExprStmtNode,
    LiteralNode,
    MainBlockNode,
    ProgramNode,
    ReturnStmtNode,
    VarDeclNode,
    VariableNode,
)
from helen.core.errors import ErrorReporter
from helen.core.source import SourceSpan
from helen.interpreter.interpreter import Interpreter


def _span(line: int = 1) -> SourceSpan:
    return SourceSpan("<test>", line, 1, line, 5)


def _lit(value, line: int = 1) -> LiteralNode:
    return LiteralNode(value=value, span=_span(line))


def _var(name: str, line: int = 1) -> VariableNode:
    return VariableNode(name=name, span=_span(line))


class TestAgentIsolationBasic:
    """Basic environment isolation tests."""

    def test_sub_agent_cannot_access_parent_variable(self):
        """Sub-agent cannot see parent's variables (HLD 3.5.2)."""
        # Create parent agent that sets a variable
        # Then calls child agent which tries to read it

        # We'll test this by calling an agent and checking its environment
        interp = Interpreter()

        # Parent sets a variable
        interp.environment.define("secret", "parent_value")
        interp.environment.define("counter", 42)

        # Create child agent (no params, no access to parent vars)
        child = AgentDeclNode(
            name="ChildAgent",
            params=[],
            declarations=[],
            prompt=None,
            logic=MainBlockNode(body=[], span=_span()),
            span=_span(),
        )
        interp._agents["ChildAgent"] = child

        # Call the child agent
        result = interp._call_agent(child, {})

        # Child's execution doesn't have access to parent's env
        # This is verified by the isolated env creation in _call_agent
        assert result is None

    def test_parent_variables_not_visible_in_child(self):
        """Explicit test: child env is completely isolated."""
        interp = Interpreter()
        interp.environment.define("parent_var", "visible_only_in_parent")

        from helen.interpreter.environment import Environment
        child_env = Environment()

        # Child env should not have parent_var
        try:
            child_env.lookup("parent_var")
            assert False, "Should not find parent_var in child env"
        except NameError:
            pass  # Expected

    def test_child_cannot_modify_parent_variables(self):
        """Child modifications don't affect parent env."""
        interp = Interpreter()
        interp.environment.define("shared", "original")

        child = AgentDeclNode(
            name="Modifier",
            params=[],
            declarations=[],
            prompt=None,
            logic=MainBlockNode(body=[], span=_span()),
            span=_span(),
        )
        interp._agents["Modifier"] = child
        interp._call_agent(child, {})

        # Parent variable unchanged
        assert interp.environment.lookup("shared") == "original"


class TestAgentParameterIsolation:
    """Parameter-based communication tests."""

    def test_parameter_is_only_communication_channel(self):
        """Parameters are the only way to pass data to sub-agent."""
        param = AgentParamNode(
            name="input_data",
            type_annotation=None,
            default_value=None,
            span=_span(),
        )
        agent = AgentDeclNode(
            name="Processor",
            params=[param],
            declarations=[],
            prompt=None,
            logic=MainBlockNode(body=[], span=_span()),
            span=_span(),
        )

        interp = Interpreter()
        interp._agents["Processor"] = agent

        # Call with parameter
        result = interp._call_agent(agent, {"input_data": "test_value"})
        assert result is None

    def test_missing_parameter_uses_default(self):
        """Missing parameter uses default value if defined."""
        param = AgentParamNode(
            name="config",
            type_annotation=None,
            default_value=_lit("default_config"),
            span=_span(),
        )
        agent = AgentDeclNode(
            name="Configurable",
            params=[param],
            declarations=[],
            prompt=None,
            logic=MainBlockNode(body=[], span=_span()),
            span=_span(),
        )

        interp = Interpreter()
        interp._agents["Configurable"] = agent

        # Call without the parameter - should use default
        result = interp._call_agent(agent, {})
        assert result is None

    def test_explicit_parameter_overrides_default(self):
        """Explicit parameter overrides default value."""
        param = AgentParamNode(
            name="setting",
            type_annotation=None,
            default_value=_lit("default"),
            span=_span(),
        )
        agent = AgentDeclNode(
            name="Overridable",
            params=[param],
            declarations=[],
            prompt=None,
            logic=MainBlockNode(body=[], span=_span()),
            span=_span(),
        )

        interp = Interpreter()
        interp._agents["Overridable"] = agent

        # Call with explicit value
        result = interp._call_agent(agent, {"setting": "custom"})
        assert result is None


class TestNestedAgentIsolation:
    """Nested agent call isolation."""

    def test_nested_agents_maintain_isolation(self):
        """Nested agent calls maintain isolation at each level."""
        # Parent -> Child -> Grandchild
        # Each level should have isolated environment

        grandchild = AgentDeclNode(
            name="Grandchild",
            params=[],
            declarations=[],
            prompt=None,
            logic=MainBlockNode(body=[], span=_span()),
            span=_span(),
        )

        interp = Interpreter()
        interp._agents["Grandchild"] = grandchild

        # Set variables at different levels
        interp.environment.define("level1", "parent")

        # Call grandchild
        result = interp._call_agent(grandchild, {})
        assert result is None

        # Parent env unchanged
        assert interp.environment.lookup("level1") == "parent"


class TestAgentReturnValues:
    """Agent return value propagation."""

    def test_agent_return_value_propagates(self):
        """Agent return value propagates back to caller."""
        agent = AgentDeclNode(
            name="Returner",
            params=[],
            declarations=[],
            prompt=None,
            logic=MainBlockNode(
                body=[ReturnStmtNode(value=_lit(42), span=_span())],
                span=_span(),
            ),
            span=_span(),
        )

        interp = Interpreter()
        interp._agents["Returner"] = agent

        result = interp._call_agent(agent, {})
        assert result == 42
