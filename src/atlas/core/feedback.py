from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path


ROOT = Path("/home/administrator/workspace/atlas")
DATABASE = ROOT / ".ai" / "memory" / "db" / "atlas.db"


@dataclass(slots=True)
class FeedbackRecord:
    execution_id: str
    stage: str
    outcome: str
    duration_ms: float
    attempts: int
    error: str = ""
    metadata: str = ""


class FeedbackStore:
    """
    Persistent execution feedback used for operational analysis
    and future execution-policy optimization.
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
                CREATE TABLE IF NOT EXISTS execution_feedback (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    execution_id TEXT NOT NULL,
                    stage TEXT NOT NULL,
                    outcome TEXT NOT NULL,
                    duration_ms REAL NOT NULL,
                    attempts INTEGER NOT NULL,
                    error TEXT NOT NULL DEFAULT '',
                    metadata TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL
                )
                """
            )

            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS
                idx_feedback_execution
                ON execution_feedback(execution_id, id)
                """
            )

            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS
                idx_feedback_stage
                ON execution_feedback(stage, outcome)
                """
            )

            connection.commit()

    def record(
        self,
        feedback: FeedbackRecord,
    ) -> int:
        if not feedback.execution_id.strip():
            raise ValueError("execution_id cannot be empty.")

        if not feedback.stage.strip():
            raise ValueError("stage cannot be empty.")

        if feedback.duration_ms < 0:
            raise ValueError(
                "duration_ms cannot be negative."
            )

        if feedback.attempts < 1:
            raise ValueError(
                "attempts must be at least 1."
            )

        with self._connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO execution_feedback (
                    execution_id,
                    stage,
                    outcome,
                    duration_ms,
                    attempts,
                    error,
                    metadata,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    feedback.execution_id,
                    feedback.stage,
                    feedback.outcome,
                    feedback.duration_ms,
                    feedback.attempts,
                    feedback.error,
                    feedback.metadata,
                    datetime.now(UTC).isoformat(),
                ),
            )

            connection.commit()

            return int(cursor.lastrowid)

    def list(
        self,
        *,
        execution_id: str | None = None,
        stage: str | None = None,
        limit: int = 100,
    ) -> list[dict]:
        if limit <= 0:
            raise ValueError("limit must be greater than zero.")

        clauses = []
        params: list[object] = []

        if execution_id is not None:
            clauses.append("execution_id = ?")
            params.append(execution_id)

        if stage is not None:
            clauses.append("stage = ?")
            params.append(stage)

        where = ""

        if clauses:
            where = "WHERE " + " AND ".join(clauses)

        params.append(limit)

        with self._connect() as connection:
            rows = connection.execute(
                f"""
                SELECT
                    id,
                    execution_id,
                    stage,
                    outcome,
                    duration_ms,
                    attempts,
                    error,
                    metadata,
                    created_at
                FROM execution_feedback
                {where}
                ORDER BY id DESC
                LIMIT ?
                """,
                params,
            ).fetchall()

        return [dict(row) for row in rows]

    def summary(
        self,
        *,
        stage: str | None = None,
    ) -> dict:
        clauses = []
        params: list[object] = []

        if stage is not None:
            clauses.append("stage = ?")
            params.append(stage)

        where = ""

        if clauses:
            where = "WHERE " + " AND ".join(clauses)

        with self._connect() as connection:
            row = connection.execute(
                f"""
                SELECT
                    COUNT(*) AS total,
                    COALESCE(SUM(
                        CASE WHEN outcome = 'completed'
                        THEN 1 ELSE 0 END
                    ), 0) AS completed,
                    COALESCE(SUM(
                        CASE WHEN outcome = 'failed'
                        THEN 1 ELSE 0 END
                    ), 0) AS failed,
                    COALESCE(AVG(duration_ms), 0) AS avg_duration_ms
                FROM execution_feedback
                {where}
                """,
                params,
            ).fetchone()

        return {
            "total": int(row["total"]),
            "completed": int(row["completed"]),
            "failed": int(row["failed"]),
            "avg_duration_ms": float(
                row["avg_duration_ms"]
            ),
        }
