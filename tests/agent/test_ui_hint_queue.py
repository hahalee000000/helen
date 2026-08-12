"""Tests for helen/agent/ui/hint_queue.py"""

import threading
import time

from helen.agent.ui.hint_queue import HintQueue, Hint, get_hint_queue


class TestHintDataclass:
    def test_hint_fields(self):
        h = Hint(text="hello", timestamp=1.0, client_id="c1")
        assert h.text == "hello"
        assert h.timestamp == 1.0
        assert h.client_id == "c1"


class TestHintQueue:
    def setup_method(self):
        self.q = HintQueue()

    def test_add_hint_returns_hint(self):
        h = self.q.add_hint("s1", "hello", "c1")
        assert isinstance(h, Hint)
        assert h.text == "hello"
        assert h.client_id == "c1"
        assert h.timestamp > 0

    def test_add_hint_default_client_id(self):
        h = self.q.add_hint("s1", "hello")
        assert h.client_id == ""

    def test_pop_all_hints_empty(self):
        result = self.q.pop_all_hints("s1")
        assert result == []

    def test_pop_all_hints_returns_and_clears(self):
        self.q.add_hint("s1", "a")
        self.q.add_hint("s1", "b")
        hints = self.q.pop_all_hints("s1")
        assert len(hints) == 2
        assert hints[0].text == "a"
        assert hints[1].text == "b"
        # queue should be empty now
        assert self.q.pop_all_hints() == []

    def test_pop_all_returns_copy(self):
        """Mutating returned list should not affect queue."""
        self.q.add_hint("s1", "a")
        hints = self.q.pop_all_hints()
        hints.clear()
        # Re-add and pop should work independently
        self.q.add_hint("s1", "b")
        hints2 = self.q.pop_all_hints()
        assert len(hints2) == 1

    def test_has_pending_false_when_empty(self):
        assert self.q.has_pending() is False

    def test_has_pending_true_after_add(self):
        self.q.add_hint("s1", "hello")
        assert self.q.has_pending() is True

    def test_has_pending_false_after_pop(self):
        self.q.add_hint("s1", "hello")
        self.q.pop_all_hints()
        assert self.q.has_pending() is False

    def test_clear_session(self):
        self.q.add_hint("s1", "a")
        self.q.add_hint("s1", "b")
        self.q.clear_session("s1")
        assert self.q.has_pending() is False

    def test_clear_all(self):
        self.q.add_hint("s1", "a")
        self.q.add_hint("s2", "b")
        self.q.clear_all()
        assert self.q.has_pending() is False

    def test_session_id_ignored_uses_single_queue(self):
        """v1.39.4: session_id is ignored, single queue for all."""
        self.q.add_hint("s1", "from_s1")
        self.q.add_hint("s2", "from_s2")
        hints = self.q.pop_all_hints("s3")
        assert len(hints) == 2

    def test_clear_session_clears_all_regardless_of_id(self):
        self.q.add_hint("s1", "a")
        self.q.clear_session("different_id")
        assert self.q.has_pending() is False


class TestHintQueueSingleton:
    def test_get_hint_queue_returns_same_instance(self):
        q1 = get_hint_queue()
        q2 = get_hint_queue()
        assert q1 is q2

    def test_get_hint_queue_returns_hint_queue_type(self):
        q = get_hint_queue()
        assert isinstance(q, HintQueue)


class TestHintQueueThreadSafety:
    def test_concurrent_add_and_pop(self):
        q = HintQueue()
        results = []
        barrier = threading.Barrier(2)

        def producer():
            barrier.wait()
            for i in range(100):
                q.add_hint("s1", f"hint_{i}")

        def consumer():
            barrier.wait()
            time.sleep(0.01)
            all_hints = []
            for _ in range(50):
                all_hints.extend(q.pop_all_hints())
                time.sleep(0.001)
            results.append(all_hints)

        t1 = threading.Thread(target=producer)
        t2 = threading.Thread(target=consumer)
        t1.start()
        t2.start()
        t1.join(timeout=5)
        t2.join(timeout=5)

        # No exception should have occurred; total hints should be <= 100
        total = len(results[0]) if results else 0
        remaining = len(q.pop_all_hints())
        assert total + remaining == 100
