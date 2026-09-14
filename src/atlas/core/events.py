from __future__ import annotations
from atlas.paths import ROOT

import os

import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path


DATABASE = ROOT / ".ai" / "memory" / "db" / "atlas.db"


class EventStore:
    """
    Persistent operational event stream for Atlas.
    """

    def __init__(
        self,
        database: str | Path = DATABASE,
    ) -> None:
        self.database = Path(database)
        self.database.parent.mkdir(
            parents=True,
            exist_ok=True,
        )
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS execution_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    execution_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    stage TEXT NOT NULL DEFAULT '',
                    payload TEXT NOT NULL DEFAULT '{}',
                    created_at TEXT NOT NULL
                )
                """
            )

            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS
                idx_events_execution
                ON execution_events(execution_id, id)
                """
            )

            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS
                idx_events_type
                ON execution_events(event_type, id)
                """
            )

            connection.commit()

    def record(
        self,
        execution_id: str,
        event_type: str,
        *,
        stage: str = "",
        payload: dict | None = None,
    ) -> int:
        if not execution_id.strip():
            raise ValueError("execution_id cannot be empty.")

        if not event_type.strip():
            raise ValueError("event_type cannot be empty.")

        with self._connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO execution_events (
                    execution_id,
                    event_type,
                    stage,
                    payload,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    execution_id,
                    event_type,
                    stage,
                    json.dumps(
                        payload or {},
                        ensure_ascii=False,
                    ),
                    datetime.now(UTC).isoformat(),
                ),
            )

            connection.commit()

            return int(cursor.lastrowid)

    def list(
        self,
        execution_id: str,
        *,
        limit: int = 100,
    ) -> list[dict]:
        if not execution_id.strip():
            raise ValueError("execution_id cannot be empty.")

        if limit <= 0:
            raise ValueError("limit must be greater than zero.")

        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT
                    id,
                    execution_id,
                    event_type,
                    stage,
                    payload,
                    created_at
                FROM execution_events
                WHERE execution_id = ?
                ORDER BY id ASC
                LIMIT ?
                """,
                (
                    execution_id,
                    limit,
                ),
            ).fetchall()

        return [
            {
                "id": row["id"],
                "execution_id": row["execution_id"],
                "event_type": row["event_type"],
                "stage": row["stage"],
                "payload": json.loads(row["payload"]),
                "created_at": row["created_at"],
            }
            for row in rows
        ]
