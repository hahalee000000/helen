"""Tests for hellen.interpreter.environment."""

import pytest

from hellen.interpreter.environment import Environment
from hellen.interpreter.exceptions import ConstAssignmentError


class TestEnvironmentDefine:
    def test_define_and_lookup(self):
        env = Environment()
        env.define("x", 42)
        assert env.lookup("x") == 42

    def test_define_const(self):
        env = Environment()
        env.define("MAX", 100, is_const=True)
        assert env.lookup("MAX") == 100
        assert env.is_const("MAX") is True

    def test_define_mutable(self):
        env = Environment()
        env.define("x", 1, is_const=False)
        assert env.is_const("x") is False


class TestEnvironmentAssign:
    def test_assign_mutable(self):
        env = Environment()
        env.define("x", 1)
        env.assign("x", 2)
        assert env.lookup("x") == 2

    def test_assign_const_raises(self):
        env = Environment()
        env.define("MAX", 100, is_const=True)
        with pytest.raises(ConstAssignmentError):
            env.assign("MAX", 200)

    def test_assign_undefined_raises(self):
        env = Environment()
        with pytest.raises(NameError, match="Undefined variable"):
            env.assign("x", 1)


class TestEnvironmentScopes:
    def test_lookup_parent_scope(self):
        parent = Environment()
        parent.define("x", 42)
        child = parent.enter_scope()
        assert child.lookup("x") == 42

    def test_child_shadows_parent(self):
        parent = Environment()
        parent.define("x", 1)
        child = parent.enter_scope()
        child.define("x", 2)
        assert child.lookup("x") == 2
        assert parent.lookup("x") == 1

    def test_define_in_child_not_visible_in_parent(self):
        parent = Environment()
        child = parent.enter_scope()
        child.define("y", "hello")
        assert child.lookup("y") == "hello"
        with pytest.raises(NameError):
            parent.lookup("y")

    def test_assign_walks_up_chain(self):
        parent = Environment()
        parent.define("x", 1)
        child = parent.enter_scope()
        child.assign("x", 2)
        # The assignment should update the parent's value
        assert parent.lookup("x") == 2
        assert child.lookup("x") == 2

    def test_assign_const_in_parent_raises_from_child(self):
        parent = Environment()
        parent.define("MAX", 100, is_const=True)
        child = parent.enter_scope()
        with pytest.raises(ConstAssignmentError):
            child.assign("MAX", 200)

    def test_exit_scope(self):
        parent = Environment()
        child = parent.enter_scope()
        assert child.exit_scope() is parent
        assert parent.exit_scope() is None

    def test_contains(self):
        parent = Environment()
        parent.define("x", 1)
        child = parent.enter_scope()
        assert "x" in child
        assert "y" not in child
