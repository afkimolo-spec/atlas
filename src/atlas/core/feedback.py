from __future__ import annotations
from atlas.paths import ROOT

import os

import json
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


DATABASE = ROOT / ".ai" / "memory" / "db" / "atlas.db"


@dataclass(frozen=True, slots=True)
class StageFeedback:
    execution_id: str
    stage: str
    attempt: int
    outcome: str
    duration_ms: float
    error: str = ""
    metadata: dict[str, Any] | None = None


@dataclass(frozen=True, slots=True)
class ExecutionFeedback:
    execution_id: str
    status: str
    total_duration_ms: float
    stage_count: int
    completed_stages: int
    failed_stages: int
    retries: int
    error: str = ""
    metadata: dict[str, Any] | None = None


class FeedbackStore:
    """
    Persistent execution-intelligence store.

    Records:
        - per-stage outcomes
        - attempts
        - duration
        - failures
        - retries
        - execution-level outcomes

    The store is intentionally independent from execution state so
    failures in feedback collection do not alter execution semantics.
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
        connection = sqlite3.connect(
            self.database,
            timeout=30.0,
        )

        connection.row_factory = sqlite3.Row

        connection.execute(
            "PRAGMA busy_timeout = 30000"
        )

        connection.execute(
            "PRAGMA journal_mode = WAL"
        )

        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS execution_feedback (
                    execution_id TEXT PRIMARY KEY,
                    status TEXT NOT NULL,
                    total_duration_ms REAL NOT NULL DEFAULT 0,
                    stage_count INTEGER NOT NULL DEFAULT 0,
                    completed_stages INTEGER NOT NULL DEFAULT 0,
                    failed_stages INTEGER NOT NULL DEFAULT 0,
                    retries INTEGER NOT NULL DEFAULT 0,
                    error TEXT NOT NULL DEFAULT '',
                    metadata TEXT NOT NULL DEFAULT '{}',
                    started_at TEXT NOT NULL,
                    completed_at TEXT,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS stage_feedback (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    execution_id TEXT NOT NULL,
                    stage TEXT NOT NULL,
                    attempt INTEGER NOT NULL,
                    outcome TEXT NOT NULL,
                    duration_ms REAL NOT NULL DEFAULT 0,
                    error TEXT NOT NULL DEFAULT '',
                    metadata TEXT NOT NULL DEFAULT '{}',
                    started_at TEXT NOT NULL,
                    completed_at TEXT,
                    updated_at TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS
                idx_execution_feedback_status
                ON execution_feedback(status);

                CREATE INDEX IF NOT EXISTS
                idx_stage_feedback_execution
                ON stage_feedback(execution_id, id);

                CREATE INDEX IF NOT EXISTS
                idx_stage_feedback_stage
                ON stage_feedback(stage, outcome);

                CREATE INDEX IF NOT EXISTS
                idx_stage_feedback_attempt
                ON stage_feedback(
                    execution_id,
                    stage,
                    attempt
                );
                """
            )

    @staticmethod
    def _now() -> datetime:
        return datetime.now(UTC)

    @staticmethod
    def _json(
        value: dict[str, Any] | None,
    ) -> str:
        return json.dumps(
            value or {},
            ensure_ascii=False,
        )

    @staticmethod
    def _duration_ms(
        started_at: str,
        completed_at: datetime,
    ) -> float:
        started = datetime.fromisoformat(
            started_at
        )

        return max(
            0.0,
            (
                completed_at - started
            ).total_seconds()
            * 1000.0,
        )

    # ------------------------------------------------------------------
    # EXECUTION
    # ------------------------------------------------------------------

    def start_execution(
        self,
        execution_id: str,
        *,
        stage_count: int,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        if not execution_id.strip():
            raise ValueError(
                "execution_id cannot be empty."
            )

        if stage_count < 1:
            raise ValueError(
                "stage_count must be at least 1."
            )

        now = self._now()

        with self._connect() as connection:
            existing = connection.execute(
                """
                SELECT execution_id
                FROM execution_feedback
                WHERE execution_id = ?
                """,
                (execution_id,),
            ).fetchone()

            if existing is None:
                connection.execute(
                    """
                    INSERT INTO execution_feedback (
                        execution_id,
                        status,
                        total_duration_ms,
                        stage_count,
                        completed_stages,
                        failed_stages,
                        retries,
                        error,
                        metadata,
                        started_at,
                        completed_at,
                        updated_at
                    )
                    VALUES (
                        ?,
                        'running',
                        0,
                        ?,
                        0,
                        0,
                        0,
                        '',
                        ?,
                        ?,
                        NULL,
                        ?
                    )
                    """,
                    (
                        execution_id,
                        stage_count,
                        self._json(metadata),
                        now.isoformat(),
                        now.isoformat(),
                    ),
                )
            else:
                connection.execute(
                    """
                    UPDATE execution_feedback
                    SET
                        status = CASE
                            WHEN status IN (
                                'completed',
                                'failed',
                                'cancelled'
                            )
                            THEN status
                            ELSE 'running'
                        END,
                        stage_count = ?,
                        metadata = ?,
                        updated_at = ?
                    WHERE execution_id = ?
                    """,
                    (
                        stage_count,
                        self._json(metadata),
                        now.isoformat(),
                        execution_id,
                    ),
                )

            connection.commit()

    def record_retry(
        self,
        execution_id: str,
    ) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE execution_feedback
                SET
                    retries = retries + 1,
                    updated_at = ?
                WHERE execution_id = ?
                """,
                (
                    self._now().isoformat(),
                    execution_id,
                ),
            )

            connection.commit()

    def complete_execution(
        self,
        execution_id: str,
        *,
        completed_stages: int,
        failed_stages: int = 0,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self._finish_execution(
            execution_id=execution_id,
            status="completed",
            completed_stages=completed_stages,
            failed_stages=failed_stages,
            error="",
            metadata=metadata,
        )

    def fail_execution(
        self,
        execution_id: str,
        *,
        completed_stages: int,
        failed_stages: int,
        error: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self._finish_execution(
            execution_id=execution_id,
            status="failed",
            completed_stages=completed_stages,
            failed_stages=failed_stages,
            error=error,
            metadata=metadata,
        )

    def _finish_execution(
        self,
        *,
        execution_id: str,
        status: str,
        completed_stages: int,
        failed_stages: int,
        error: str,
        metadata: dict[str, Any] | None,
    ) -> None:
        now = self._now()

        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT
                    started_at,
                    retries,
                    metadata
                FROM execution_feedback
                WHERE execution_id = ?
                """,
                (execution_id,),
            ).fetchone()

            if row is None:
                connection.execute(
                    """
                    INSERT INTO execution_feedback (
                        execution_id,
                        status,
                        total_duration_ms,
                        stage_count,
                        completed_stages,
                        failed_stages,
                        retries,
                        error,
                        metadata,
                        started_at,
                        completed_at,
                        updated_at
                    )
                    VALUES (
                        ?,
                        ?,
                        0,
                        0,
                        ?,
                        ?,
                        0,
                        ?,
                        ?,
                        ?,
                        ?,
                        ?
                    )
                    """,
                    (
                        execution_id,
                        status,
                        completed_stages,
                        failed_stages,
                        error,
                        self._json(metadata),
                        now.isoformat(),
                        now.isoformat(),
                        now.isoformat(),
                    ),
                )
            else:
                duration_ms = self._duration_ms(
                    row["started_at"],
                    now,
                )

                existing_metadata = json.loads(
                    row["metadata"] or "{}"
                )

                if metadata:
                    existing_metadata.update(
                        metadata
                    )

                connection.execute(
                    """
                    UPDATE execution_feedback
                    SET
                        status = ?,
                        total_duration_ms = ?,
                        completed_stages = ?,
                        failed_stages = ?,
                        error = ?,
                        metadata = ?,
                        completed_at = ?,
                        updated_at = ?
                    WHERE execution_id = ?
                    """,
                    (
                        status,
                        duration_ms,
                        completed_stages,
                        failed_stages,
                        error,
                        self._json(
                            existing_metadata
                        ),
                        now.isoformat(),
                        now.isoformat(),
                        execution_id,
                    ),
                )

            connection.commit()

    # ------------------------------------------------------------------
    # STAGE
    # ------------------------------------------------------------------

    def start_stage(
        self,
        execution_id: str,
        stage: str,
        *,
        attempt: int,
        metadata: dict[str, Any] | None = None,
    ) -> int:
        if not execution_id.strip():
            raise ValueError(
                "execution_id cannot be empty."
            )

        if not stage.strip():
            raise ValueError(
                "stage cannot be empty."
            )

        if attempt < 1:
            raise ValueError(
                "attempt must be at least 1."
            )

        now = self._now()

        with self._connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO stage_feedback (
                    execution_id,
                    stage,
                    attempt,
                    outcome,
                    duration_ms,
                    error,
                    metadata,
                    started_at,
                    completed_at,
                    updated_at
                )
                VALUES (
                    ?,
                    ?,
                    ?,
                    'running',
                    0,
                    '',
                    ?,
                    ?,
                    NULL,
                    ?
                )
                """,
                (
                    execution_id,
                    stage,
                    attempt,
                    self._json(metadata),
                    now.isoformat(),
                    now.isoformat(),
                ),
            )

            connection.commit()

            return int(cursor.lastrowid)

    def complete_stage(
        self,
        feedback_id: int,
        *,
        metadata: dict[str, Any] | None = None,
    ) -> float:
        return self._finish_stage(
            feedback_id=feedback_id,
            outcome="completed",
            error="",
            metadata=metadata,
        )

    def fail_stage(
        self,
        feedback_id: int,
        *,
        error: str,
        metadata: dict[str, Any] | None = None,
    ) -> float:
        return self._finish_stage(
            feedback_id=feedback_id,
            outcome="failed",
            error=error,
            metadata=metadata,
        )

    def _finish_stage(
        self,
        *,
        feedback_id: int,
        outcome: str,
        error: str,
        metadata: dict[str, Any] | None,
    ) -> float:
        now = self._now()

        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT
                    started_at,
                    outcome,
                    metadata
                FROM stage_feedback
                WHERE id = ?
                """,
                (feedback_id,),
            ).fetchone()

            if row is None:
                raise KeyError(
                    f"Stage feedback not found: {feedback_id}"
                )

            if row["outcome"] != "running":
                raise RuntimeError(
                    f"Stage feedback {feedback_id} is already "
                    f"finalized as '{row['outcome']}'."
                )

            duration_ms = self._duration_ms(
                row["started_at"],
                now,
            )

            existing_metadata = json.loads(
                row["metadata"] or "{}"
            )

            if metadata:
                existing_metadata.update(
                    metadata
                )

            connection.execute(
                """
                UPDATE stage_feedback
                SET
                    outcome = ?,
                    duration_ms = ?,
                    error = ?,
                    metadata = ?,
                    completed_at = ?,
                    updated_at = ?
                WHERE id = ?
                """,
                (
                    outcome,
                    duration_ms,
                    error,
                    self._json(
                        existing_metadata
                    ),
                    now.isoformat(),
                    now.isoformat(),
                    feedback_id,
                ),
            )

            connection.commit()

            return duration_ms

    # ------------------------------------------------------------------
    # QUERIES
    # ------------------------------------------------------------------

    def execution(
        self,
        execution_id: str,
    ) -> dict[str, Any] | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT *
                FROM execution_feedback
                WHERE execution_id = ?
                """,
                (execution_id,),
            ).fetchone()

        if row is None:
            return None

        result = dict(row)

        result["metadata"] = json.loads(
            result["metadata"] or "{}"
        )

        return result

    def stages(
        self,
        execution_id: str,
    ) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT *
                FROM stage_feedback
                WHERE execution_id = ?
                ORDER BY id ASC
                """,
                (execution_id,),
            ).fetchall()

        results = []

        for row in rows:
            item = dict(row)

            item["metadata"] = json.loads(
                item["metadata"] or "{}"
            )

            results.append(item)

        return results

    def summary(
        self,
        *,
        stage: str | None = None,
    ) -> dict[str, float | int]:
        where = ""
        parameters: list[Any] = []

        if stage is not None:
            where = "WHERE stage = ?"
            parameters.append(stage)

        with self._connect() as connection:
            row = connection.execute(
                f"""
                SELECT
                    COUNT(*) AS total,
                    COALESCE(
                        SUM(
                            CASE
                                WHEN outcome = 'completed'
                                THEN 1
                                ELSE 0
                            END
                        ),
                        0
                    ) AS completed,
                    COALESCE(
                        SUM(
                            CASE
                                WHEN outcome = 'failed'
                                THEN 1
                                ELSE 0
                            END
                        ),
                        0
                    ) AS failed,
                    COALESCE(
                        SUM(
                            CASE
                                WHEN outcome = 'running'
                                THEN 1
                                ELSE 0
                            END
                        ),
                        0
                    ) AS running,
                    COALESCE(
                        AVG(duration_ms),
                        0
                    ) AS avg_duration_ms,
                    COALESCE(
                        AVG(attempt),
                        0
                    ) AS avg_attempt
                FROM stage_feedback
                {where}
                """,
                parameters,
            ).fetchone()

        total = int(row["total"])
        completed = int(row["completed"])
        failed = int(row["failed"])

        return {
            "total": total,
            "completed": completed,
            "failed": failed,
            "running": int(row["running"]),
            "avg_duration_ms": float(
                row["avg_duration_ms"]
            ),
            "avg_attempt": float(
                row["avg_attempt"]
            ),
            "success_rate": (
                completed / total
                if total
                else 0.0
            ),
            "failure_rate": (
                failed / total
                if total
                else 0.0
            ),
        }

    def execution_summary(self) -> dict[str, float | int]:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT
                    COUNT(*) AS total,
                    COALESCE(
                        SUM(
                            CASE
                                WHEN status = 'completed'
                                THEN 1
                                ELSE 0
                            END
                        ),
                        0
                    ) AS completed,
                    COALESCE(
                        SUM(
                            CASE
                                WHEN status = 'failed'
                                THEN 1
                                ELSE 0
                            END
                        ),
                        0
                    ) AS failed,
                    COALESCE(
                        SUM(retries),
                        0
                    ) AS retries,
                    COALESCE(
                        AVG(total_duration_ms),
                        0
                    ) AS avg_duration_ms
                FROM execution_feedback
                """
            ).fetchone()

        total = int(row["total"])
        completed = int(row["completed"])
        failed = int(row["failed"])

        return {
            "total": total,
            "completed": completed,
            "failed": failed,
            "retries": int(row["retries"]),
            "avg_duration_ms": float(
                row["avg_duration_ms"]
            ),
            "success_rate": (
                completed / total
                if total
                else 0.0
            ),
            "failure_rate": (
                failed / total
                if total
                else 0.0
            ),
        }

    def optimization_signals(self) -> dict[str, Any]:
        execution = self.execution_summary()

        with self._connect() as connection:
            slowest = connection.execute(
                """
                SELECT
                    stage,
                    AVG(duration_ms) AS avg_duration_ms,
                    AVG(attempt) AS avg_attempt,
                    COUNT(*) AS executions,
                    SUM(
                        CASE
                            WHEN outcome = 'failed'
                            THEN 1
                            ELSE 0
                        END
                    ) AS failures
                FROM stage_feedback
                WHERE outcome IN (
                    'completed',
                    'failed'
                )
                GROUP BY stage
                ORDER BY avg_duration_ms DESC
                LIMIT 1
                """
            ).fetchone()

            most_failure_prone = connection.execute(
                """
                SELECT
                    stage,
                    COUNT(*) AS executions,
                    SUM(
                        CASE
                            WHEN outcome = 'failed'
                            THEN 1
                            ELSE 0
                        END
                    ) AS failures
                FROM stage_feedback
                WHERE outcome IN (
                    'completed',
                    'failed'
                )
                GROUP BY stage
                ORDER BY
                    CAST(failures AS REAL)
                    / NULLIF(executions, 0)
                    DESC
                LIMIT 1
                """
            ).fetchone()

        return {
            "execution": execution,
            "slowest_stage": (
                dict(slowest)
                if slowest is not None
                else None
            ),
            "most_failure_prone_stage": (
                dict(most_failure_prone)
                if most_failure_prone is not None
                else None
            ),
        }


class FeedbackCollector:
    """
    Workflow-facing feedback adapter.

    Feedback failures must never become execution failures.
    """

    def __init__(
        self,
        database: str | Path = DATABASE,
        store: FeedbackStore | None = None,
    ) -> None:
        self.store = store or FeedbackStore(
            database
        )

    def start_execution(
        self,
        execution_id: str,
        *,
        stage_count: int,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        try:
            self.store.start_execution(
                execution_id,
                stage_count=stage_count,
                metadata=metadata,
            )
        except Exception:
            pass

    def retry(
        self,
        execution_id: str,
    ) -> None:
        try:
            self.store.record_retry(
                execution_id
            )
        except Exception:
            pass

    def start_stage(
        self,
        execution_id: str,
        stage: str,
        *,
        attempt: int,
        metadata: dict[str, Any] | None = None,
    ) -> int | None:
        try:
            return self.store.start_stage(
                execution_id,
                stage,
                attempt=attempt,
                metadata=metadata,
            )
        except Exception:
            return None

    def complete_stage(
        self,
        feedback_id: int | None,
        *,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        if feedback_id is None:
            return

        try:
            self.store.complete_stage(
                feedback_id,
                metadata=metadata,
            )
        except Exception:
            pass

    def fail_stage(
        self,
        feedback_id: int | None,
        *,
        error: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        if feedback_id is None:
            return

        try:
            self.store.fail_stage(
                feedback_id,
                error=error,
                metadata=metadata,
            )
        except Exception:
            pass

    def complete_execution(
        self,
        execution_id: str,
        *,
        completed_stages: int,
        failed_stages: int = 0,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        try:
            self.store.complete_execution(
                execution_id,
                completed_stages=completed_stages,
                failed_stages=failed_stages,
                metadata=metadata,
            )
        except Exception:
            pass

    def fail_execution(
        self,
        execution_id: str,
        *,
        completed_stages: int,
        failed_stages: int,
        error: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        try:
            self.store.fail_execution(
                execution_id,
                completed_stages=completed_stages,
                failed_stages=failed_stages,
                error=error,
                metadata=metadata,
            )
        except Exception:
            pass
