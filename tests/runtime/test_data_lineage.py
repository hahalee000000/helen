"""Tests for data lineage tracking (Phase 5).

Tests the DataLineageTracker class and related functionality.
"""

import pytest
import tempfile
from pathlib import Path
from helen.runtime.data_lineage import DataLineageTracker, DataFlow


class TestDataFlow:
    """Test DataFlow dataclass."""

    def test_data_flow_to_dict(self):
        """Test DataFlow serialization."""
        flow = DataFlow(
            producer_uuid="msg_abc",
            consumer_uuid="msg_xyz",
            flow_type="channel",
            timestamp=1234567890.0,
            metadata={"channel": "main"},
        )
        d = flow.to_dict()
        assert d["producer_uuid"] == "msg_abc"
        assert d["consumer_uuid"] == "msg_xyz"
        assert d["flow_type"] == "channel"
        assert d["metadata"] == {"channel": "main"}

    def test_data_flow_from_dict(self):
        """Test DataFlow deserialization."""
        d = {
            "producer_uuid": "msg_abc",
            "consumer_uuid": "msg_xyz",
            "flow_type": "channel",
            "timestamp": 1234567890.0,
            "metadata": {"channel": "main"},
        }
        flow = DataFlow.from_dict(d)
        assert flow.producer_uuid == "msg_abc"
        assert flow.consumer_uuid == "msg_xyz"
        assert flow.flow_type == "channel"
        assert flow.metadata == {"channel": "main"}


class TestDataLineageTracker:
    """Test DataLineageTracker."""

    def test_create_tracker(self):
        """Test creating a data lineage tracker."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker = DataLineageTracker(tmpdir, "test_session")
            assert tracker.db_path.exists()
            tracker.close()

    def test_record_flow(self):
        """Test recording a data flow."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker = DataLineageTracker(tmpdir, "test_session")

            tracker.record_flow(
                producer_uuid="msg_abc",
                consumer_uuid="msg_xyz",
                flow_type="channel",
                metadata={"channel": "main"},
            )

            # Verify flow was recorded
            flows = tracker.get_origin("msg_xyz")
            assert len(flows) == 1
            assert flows[0].producer_uuid == "msg_abc"
            assert flows[0].flow_type == "channel"

            tracker.close()

    def test_get_origin(self):
        """Test getting data origin."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker = DataLineageTracker(tmpdir, "test_session")

            # Record multiple flows to the same consumer
            tracker.record_flow("msg_a", "msg_x", "channel")
            tracker.record_flow("msg_b", "msg_x", "agent_call")

            flows = tracker.get_origin("msg_x")
            assert len(flows) == 2
            producer_uuids = {f.producer_uuid for f in flows}
            assert producer_uuids == {"msg_a", "msg_b"}

            tracker.close()

    def test_get_consumers(self):
        """Test getting data consumers."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker = DataLineageTracker(tmpdir, "test_session")

            # Record multiple flows from the same producer
            tracker.record_flow("msg_a", "msg_x", "channel")
            tracker.record_flow("msg_a", "msg_y", "prompt")

            flows = tracker.get_consumers("msg_a")
            assert len(flows) == 2
            consumer_uuids = {f.consumer_uuid for f in flows}
            assert consumer_uuids == {"msg_x", "msg_y"}

            tracker.close()

    def test_get_full_lineage(self):
        """Test getting complete lineage graph."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker = DataLineageTracker(tmpdir, "test_session")

            # Record a chain of flows
            tracker.record_flow("msg_a", "msg_b", "channel")
            tracker.record_flow("msg_b", "msg_c", "agent_call")
            tracker.record_flow("msg_c", "msg_d", "prompt")

            lineage = tracker.get_full_lineage()
            assert len(lineage["nodes"]) == 4
            assert len(lineage["edges"]) == 3

            # Verify nodes
            nodes = set(lineage["nodes"])
            assert nodes == {"msg_a", "msg_b", "msg_c", "msg_d"}

            # Verify edges
            edges = lineage["edges"]
            assert len(edges) == 3
            assert edges[0]["source"] == "msg_a"
            assert edges[0]["target"] == "msg_b"

            tracker.close()

    def test_context_manager(self):
        """Test using tracker as context manager."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with DataLineageTracker(tmpdir, "test_session") as tracker:
                tracker.record_flow("msg_a", "msg_b", "channel")

            # Connection should be closed after context manager exits
            # but the database file should still exist
            db_path = Path(tmpdir) / "test_session_lineage.db"
            assert db_path.exists()

    def test_empty_queries(self):
        """Test querying non-existent data."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker = DataLineageTracker(tmpdir, "test_session")

            # Query non-existent message
            flows = tracker.get_origin("nonexistent")
            assert len(flows) == 0

            flows = tracker.get_consumers("nonexistent")
            assert len(flows) == 0

            tracker.close()

    def test_complex_lineage_graph(self):
        """Test complex lineage graph with multiple paths."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker = DataLineageTracker(tmpdir, "test_session")

            # Create a diamond-shaped graph
            # msg_a -> msg_b, msg_c
            # msg_b -> msg_d
            # msg_c -> msg_d
            tracker.record_flow("msg_a", "msg_b", "channel")
            tracker.record_flow("msg_a", "msg_c", "channel")
            tracker.record_flow("msg_b", "msg_d", "agent_call")
            tracker.record_flow("msg_c", "msg_d", "agent_call")

            # msg_d should have two origins
            origins = tracker.get_origin("msg_d")
            assert len(origins) == 2
            origin_uuids = {f.producer_uuid for f in origins}
            assert origin_uuids == {"msg_b", "msg_c"}

            # msg_a should have two consumers
            consumers = tracker.get_consumers("msg_a")
            assert len(consumers) == 2
            consumer_uuids = {f.consumer_uuid for f in consumers}
            assert consumer_uuids == {"msg_b", "msg_c"}

            tracker.close()
