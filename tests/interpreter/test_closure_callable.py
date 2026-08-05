"""
Test closure __call__ functionality (v1.32).

Closures are now Python callable via weakref-bound interpreter,
allowing them to be used as callbacks in Python contexts (hooks, etc.)
"""
import pytest
from helen.interpreter.closure import Closure
from helen.core.ast import LambdaNode
from helen.interpreter.environment import Environment


class MockInterpreter:
    """Mock interpreter for testing closure binding."""
    def __init__(self):
        self.call_count = 0
        self.last_args = None

    def _call_closure(self, closure, args):
        self.call_count += 1
        self.last_args = args
        # Simulate simple return value
        if len(args) == 1:
            return args[0] * 2
        return sum(args)


def test_closure_bind_method():
    """Closure.bind() should enable calling."""
    # Create unbound closure
    node = LambdaNode(params=[], body=None, return_type=None, span=None)
    env = Environment()
    closure = Closure(node, env)

    # Should not be callable before binding
    with pytest.raises(RuntimeError, match="not bound"):
        closure()

    # Bind to mock interpreter
    interp = MockInterpreter()
    closure.bind(interp)

    # Should be callable after binding
    result = closure(5)
    assert result == 10
    assert interp.call_count == 1
    assert interp.last_args == [5]


def test_closure_unbound_error():
    """Unbound closure should raise clear error."""
    node = LambdaNode(params=[], body=None, return_type=None, span=None)
    env = Environment()
    closure = Closure(node, env)

    with pytest.raises(RuntimeError, match="not bound"):
        closure()


def test_closure_is_python_callable():
    """Closure should be recognized as Python callable after binding."""
    node = LambdaNode(params=[], body=None, return_type=None, span=None)
    env = Environment()
    closure = Closure(node, env)

    # Unbound closure is not callable (no __call__ success path)
    interp = MockInterpreter()
    closure.bind(interp)

    # Should be callable
    assert callable(closure)


def test_closure_weakref_no_circular_reference():
    """Closure should use weakref to avoid circular references."""
    node = LambdaNode(params=[], body=None, return_type=None, span=None)
    env = Environment()
    closure = Closure(node, env)

    # Bind to interpreter
    interp = MockInterpreter()
    closure.bind(interp)

    assert closure._interpreter_ref is not None

    # Weakref should not prevent garbage collection
    import weakref
    assert isinstance(closure._interpreter_ref, weakref.ref)

    # Should be able to dereference
    assert closure._interpreter_ref() is interp


def test_closure_repr():
    """Closure repr should show bound state."""
    node = LambdaNode(params=[], body=None, return_type=None, span=None)
    env = Environment()
    closure = Closure(node, env)

    # Unbound repr
    assert "unbound" in repr(closure)
    assert "0 params" in repr(closure)

    # Bind and check again
    interp = MockInterpreter()
    closure.bind(interp)
    assert "bound" in repr(closure)


def test_closure_multiple_calls():
    """Closure should be callable multiple times."""
    node = LambdaNode(params=[], body=None, return_type=None, span=None)
    env = Environment()
    closure = Closure(node, env)

    interp = MockInterpreter()
    closure.bind(interp)

    # Call multiple times
    closure(1)
    closure(2)
    closure(3)

    assert interp.call_count == 3


def test_closure_multiple_args():
    """Closure should handle multiple arguments."""
    node = LambdaNode(params=[], body=None, return_type=None, span=None)
    env = Environment()
    closure = Closure(node, env)

    interp = MockInterpreter()
    closure.bind(interp)

    # Call with multiple args
    result = closure(1, 2, 3)
    assert result == 6  # sum of args
    assert interp.last_args == [1, 2, 3]
