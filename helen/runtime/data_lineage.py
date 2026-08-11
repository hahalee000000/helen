"""Data lineage tracking for cross-agent data flow analysis.

v1.40: Tracks how data flows between agents, enabling debugging of
data-related issues in multi-agent systems.

Key Features:
- Track data flow at Channel send/receive points
- Track data flow at agent call boundaries
- Query data origin and consumers
- Store lineage in SQLite sidecar file

Usage:
    from helen.runtime.data_lineage import DataLineageTracker

    tracker = DataLineageTracker(session_dir)
    tracker.record_flow(producer_uuid, consumer_uuid, "channel", metadata)

    # Query data origin
    origins = tracker.get_origin("msg_xyz")

    # Query data consumers
    consumers = tracker.get_consumers("msg_abc")
"""

from __future__ import annotations

import hashlib
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class DataFlow:
    """Represents a data flow between two messages."""

    producer_uuid: str           # UUID of the message that produced the data
    consumer_uuid: str           # UUID of the message that consumed the data
    flow_type: str               # "channel", "agent_call", "prompt"
    timestamp: float             # When the flow occurred
    metadata: dict[str, Any]     # Additional metadata (e.g., channel name, arg name)

    def to_dict(self) -> dict[str, Any]:
        """Convert to JSON-serializable dict."""
        return {
            "producer_uuid": self.producer_uuid,
            "consumer_uuid": self.consumer_uuid,
            "flow_type": self.flow_type,
            "timestamp": self.timestamp,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DataFlow:
        """Reconstruct from dict."""
        return cls(
            producer_uuid=data["producer_uuid"],
            consumer_uuid=data["consumer_uuid"],
            flow_type=data["flow_type"],
            timestamp=data["timestamp"],
            metadata=data.get("metadata", {}),
        )


class DataLineageTracker:
    """Tracks data flow between agents using SQLite sidecar.

    Creates a separate SQLite database (<session_id>_lineage.db) to store
    data flow information. This is independent of the transcript backend
    (JSONL or SQLite).
    """

    def __init__(self, session_dir: Path | str, session_id: str):
        """Initialize data lineage tracker.

        Args:
            session_dir: Directory containing session files
            session_id: Session identifier
        """
        self.session_dir = Path(session_dir) if isinstance(session_dir, str) else session_dir
        self.session_id = session_id
        self.db_path = self.session_dir / f"{session_id}_lineage.db"

        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self._init_schema()

    def _init_schema(self) -> None:
        """Initialize the database schema."""
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS data_lineage (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                producer_uuid TEXT NOT NULL,
                consumer_uuid TEXT NOT NULL,
                flow_type TEXT NOT NULL,
                timestamp REAL NOT NULL,
                metadata TEXT
            )
        """)
        self.conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_producer
            ON data_lineage(producer_uuid)
        """)
        self.conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_consumer
            ON data_lineage(consumer_uuid)
        """)
        self.conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_timestamp
            ON data_lineage(timestamp)
        """)
        self.conn.commit()

    def record_flow(
        self,
        producer_uuid: str,
        consumer_uuid: str,
        flow_type: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Record a data flow event.

        Args:
            producer_uuid: UUID of the message that produced the data
            consumer_uuid: UUID of the message that consumed the data
            flow_type: Type of flow ("channel", "agent_call", "prompt")
            metadata: Additional metadata (e.g., channel name, argument name)
        """
        import time
        import json

        self.conn.execute(
            """
            INSERT INTO data_lineage
            (producer_uuid, consumer_uuid, flow_type, timestamp, metadata)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                producer_uuid,
                consumer_uuid,
                flow_type,
                time.time(),
                json.dumps(metadata or {}),
            ),
        )
        self.conn.commit()

    def get_origin(self, consumer_uuid: str) -> list[DataFlow]:
        """Get the origin(s) of data consumed by a message.

        Args:
            consumer_uuid: UUID of the message that consumed data

        Returns:
            List of DataFlow objects representing data origins
        """
        import json

        cursor = self.conn.execute(
            """
            SELECT producer_uuid, consumer_uuid, flow_type, timestamp, metadata
            FROM data_lineage
            WHERE consumer_uuid = ?
            ORDER BY timestamp ASC
            """,
            (consumer_uuid,),
        )

        flows = []
        for row in cursor:
            flow = DataFlow(
                producer_uuid=row[0],
                consumer_uuid=row[1],
                flow_type=row[2],
                timestamp=row[3],
                metadata=json.loads(row[4]) if row[4] else {},
            )
            flows.append(flow)

        return flows

    def get_consumers(self, producer_uuid: str) -> list[DataFlow]:
        """Get the consumers of data produced by a message.

        Args:
            producer_uuid: UUID of the message that produced data

        Returns:
            List of DataFlow objects representing data consumers
        """
        import json

        cursor = self.conn.execute(
            """
            SELECT producer_uuid, consumer_uuid, flow_type, timestamp, metadata
            FROM data_lineage
            WHERE producer_uuid = ?
            ORDER BY timestamp ASC
            """,
            (producer_uuid,),
        )

        flows = []
        for row in cursor:
            flow = DataFlow(
                producer_uuid=row[0],
                consumer_uuid=row[1],
                flow_type=row[2],
                timestamp=row[3],
                metadata=json.loads(row[4]) if row[4] else {},
            )
            flows.append(flow)

        return flows

    def get_full_lineage(self) -> dict[str, Any]:
        """Get the complete data lineage graph.

        Returns:
            Dict with 'nodes' (message UUIDs) and 'edges' (data flows)
        """
        import json

        cursor = self.conn.execute(
            """
            SELECT producer_uuid, consumer_uuid, flow_type, timestamp, metadata
            FROM data_lineage
            ORDER BY timestamp ASC
            """
        )

        nodes = set()
        edges = []

        for row in cursor:
            producer_uuid = row[0]
            consumer_uuid = row[1]
            flow_type = row[2]
            timestamp = row[3]
            metadata = json.loads(row[4]) if row[4] else {}

            nodes.add(producer_uuid)
            nodes.add(consumer_uuid)

            edges.append({
                "source": producer_uuid,
                "target": consumer_uuid,
                "flow_type": flow_type,
                "timestamp": timestamp,
                "metadata": metadata,
            })

        return {
            "nodes": list(nodes),
            "edges": edges,
        }

    def close(self) -> None:
        """Close the database connection."""
        if self.conn:
            self.conn.close()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
