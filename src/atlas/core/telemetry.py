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
class TraceSpan:
    trace_id: str
    execution_id: str
    name: str
    kind: str
    status: str
    started_at: str
    completed_at: str
    duration_ms: float
    stage: str = ""
    agent: str = ""
    error: str = ""
    attributes: dict[str, Any] | None = None


class TelemetryStore:
    """
    Persistent execution telemetry.

    Traces represent executions.
    Spans represent execution-level, stage-level, or recovery
    operations.

    Stage analytics operate only on actual stage spans.
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
                CREATE TABLE IF NOT EXISTS telemetry_traces (
                    trace_id TEXT PRIMARY KEY,
                    execution_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    started_at TEXT NOT NULL,
                    completed_at TEXT,
                    duration_ms REAL NOT NULL DEFAULT 0,
                    error TEXT NOT NULL DEFAULT '',
                    metadata TEXT NOT NULL DEFAULT '{}',
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS telemetry_spans (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    trace_id TEXT NOT NULL,
                    execution_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    kind TEXT NOT NULL,
                    stage TEXT NOT NULL DEFAULT '',
                    agent TEXT NOT NULL DEFAULT '',
                    status TEXT NOT NULL,
                    started_at TEXT NOT NULL,
                    completed_at TEXT NOT NULL,
                    duration_ms REAL NOT NULL DEFAULT 0,
                    error TEXT NOT NULL DEFAULT '',
                    attributes TEXT NOT NULL DEFAULT '{}'
                );

                CREATE INDEX IF NOT EXISTS
                idx_telemetry_trace_execution
                ON telemetry_traces(execution_id);

                CREATE INDEX IF NOT EXISTS
                idx_telemetry_spans_trace
                ON telemetry_spans(trace_id, id);

                CREATE INDEX IF NOT EXISTS
                idx_telemetry_spans_stage
                ON telemetry_spans(stage, status);

                CREATE INDEX IF NOT EXISTS
                idx_telemetry_spans_execution
                ON telemetry_spans(execution_id, id);
                """
            )

            connection.commit()

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

    # ------------------------------------------------------------------
    # TRACE
    # ------------------------------------------------------------------

    def start_trace(
        self,
        trace_id: str,
        execution_id: str,
        *,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        if not trace_id.strip():
            raise ValueError(
                "trace_id cannot be empty."
            )

        if not execution_id.strip():
            raise ValueError(
                "execution_id cannot be empty."
            )

        now = self._now().isoformat()

        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO telemetry_traces (
                    trace_id,
                    execution_id,
                    status,
                    started_at,
                    completed_at,
                    duration_ms,
                    error,
                    metadata,
                    updated_at
                )
                VALUES (
                    ?,
                    ?,
                    'running',
                    ?,
                    NULL,
                    0,
                    '',
                    ?,
                    ?
                )
                ON CONFLICT(trace_id)
                DO UPDATE SET
                    execution_id = excluded.execution_id,
                    status = 'running',
                    started_at = excluded.started_at,
                    completed_at = NULL,
                    duration_ms = 0,
                    error = '',
                    metadata = excluded.metadata,
                    updated_at = excluded.updated_at
                """,
                (
                    trace_id,
                    execution_id,
                    now,
                    self._json(metadata),
                    now,
                ),
            )

            connection.commit()

    def finish_trace(
        self,
        trace_id: str,
        *,
        status: str,
        error: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> None:
        now = self._now()

        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT
                    started_at,
                    metadata
                FROM telemetry_traces
                WHERE trace_id = ?
                """,
                (trace_id,),
            ).fetchone()

            if row is None:
                return

            started = datetime.fromisoformat(
                row["started_at"]
            )

            duration_ms = max(
                0.0,
                (
                    now - started
                ).total_seconds()
                * 1000.0,
            )

            existing = json.loads(
                row["metadata"] or "{}"
            )

            if metadata:
                existing.update(metadata)

            connection.execute(
                """
                UPDATE telemetry_traces
                SET
                    status = ?,
                    completed_at = ?,
                    duration_ms = ?,
                    error = ?,
                    metadata = ?,
                    updated_at = ?
                WHERE trace_id = ?
                """,
                (
                    status,
                    now.isoformat(),
                    duration_ms,
                    error,
                    self._json(existing),
                    now.isoformat(),
                    trace_id,
                ),
            )

            connection.commit()

    # ------------------------------------------------------------------
    # SPANS
    # ------------------------------------------------------------------

    def start_span(
        self,
        trace_id: str,
        execution_id: str,
        *,
        name: str,
        kind: str,
        stage: str = "",
        agent: str = "",
        attributes: dict[str, Any] | None = None,
    ) -> int:
        if not trace_id.strip():
            raise ValueError(
                "trace_id cannot be empty."
            )

        if not execution_id.strip():
            raise ValueError(
                "execution_id cannot be empty."
            )

        if not name.strip():
            raise ValueError(
                "span name cannot be empty."
            )

        if not kind.strip():
            raise ValueError(
                "span kind cannot be empty."
            )

        now = self._now()

        with self._connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO telemetry_spans (
                    trace_id,
                    execution_id,
                    name,
                    kind,
                    stage,
                    agent,
                    status,
                    started_at,
                    completed_at,
                    duration_ms,
                    error,
                    attributes
                )
                VALUES (
                    ?,
                    ?,
                    ?,
                    ?,
                    ?,
                    ?,
                    'running',
                    ?,
                    ?,
                    0,
                    '',
                    ?
                )
                """,
                (
                    trace_id,
                    execution_id,
                    name,
                    kind,
                    stage,
                    agent,
                    now.isoformat(),
                    now.isoformat(),
                    self._json(attributes),
                ),
            )

            connection.commit()

            return int(cursor.lastrowid)

    def finish_span(
        self,
        span_id: int,
        *,
        status: str,
        error: str = "",
        attributes: dict[str, Any] | None = None,
    ) -> None:
        now = self._now()

        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT
                    started_at,
                    attributes
                FROM telemetry_spans
                WHERE id = ?
                """,
                (span_id,),
            ).fetchone()

            if row is None:
                return

            started = datetime.fromisoformat(
                row["started_at"]
            )

            duration_ms = max(
                0.0,
                (
                    now - started
                ).total_seconds()
                * 1000.0,
            )

            existing = json.loads(
                row["attributes"] or "{}"
            )

            if attributes:
                existing.update(attributes)

            connection.execute(
                """
                UPDATE telemetry_spans
                SET
                    status = ?,
                    completed_at = ?,
                    duration_ms = ?,
                    error = ?,
                    attributes = ?
                WHERE id = ?
                """,
                (
                    status,
                    now.isoformat(),
                    duration_ms,
                    error,
                    self._json(existing),
                    span_id,
                ),
            )

            connection.commit()

    # ------------------------------------------------------------------
    # QUERIES
    # ------------------------------------------------------------------

    def trace(
        self,
        trace_id: str,
    ) -> dict[str, Any] | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT *
                FROM telemetry_traces
                WHERE trace_id = ?
                """,
                (trace_id,),
            ).fetchone()

        if row is None:
            return None

        result = dict(row)

        result["metadata"] = json.loads(
            result["metadata"] or "{}"
        )

        return result

    def spans(
        self,
        trace_id: str,
    ) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT *
                FROM telemetry_spans
                WHERE trace_id = ?
                ORDER BY id ASC
                """,
                (trace_id,),
            ).fetchall()

        results = []

        for row in rows:
            item = dict(row)

            item["attributes"] = json.loads(
                item["attributes"] or "{}"
            )

            results.append(item)

        return results

    def failures(
        self,
        *,
        execution_id: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        if limit <= 0:
            raise ValueError(
                "limit must be greater than zero."
            )

        if execution_id is None:
            where = "WHERE status = 'failed'"
            parameters: list[Any] = [limit]

        else:
            where = (
                "WHERE execution_id = ? "
                "AND status = 'failed'"
            )
            parameters = [
                execution_id,
                limit,
            ]

        with self._connect() as connection:
            rows = connection.execute(
                f"""
                SELECT *
                FROM telemetry_spans
                {where}
                ORDER BY id DESC
                LIMIT ?
                """,
                parameters,
            ).fetchall()

        return [dict(row) for row in rows]

    # ------------------------------------------------------------------
    # METRICS
    # ------------------------------------------------------------------

    def execution_metrics(
        self,
    ) -> dict[str, float | int]:
        with self._connect() as connection:
            trace = connection.execute(
                """
                SELECT
                    COUNT(*) AS total,
                    COALESCE(
                        SUM(
                            CASE
                                WHEN status = 'completed'
                                THEN 1 ELSE 0
                            END
                        ),
                        0
                    ) AS completed,
                    COALESCE(
                        SUM(
                            CASE
                                WHEN status = 'failed'
                                THEN 1 ELSE 0
                            END
                        ),
                        0
                    ) AS failed,
                    COALESCE(
                        AVG(duration_ms),
                        0
                    ) AS avg_duration_ms
                FROM telemetry_traces
                """
            ).fetchone()

            spans = connection.execute(
                """
                SELECT
                    COUNT(*) AS total,
                    COALESCE(
                        SUM(
                            CASE
                                WHEN status = 'completed'
                                THEN 1 ELSE 0
                            END
                        ),
                        0
                    ) AS completed,
                    COALESCE(
                        SUM(
                            CASE
                                WHEN status = 'failed'
                                THEN 1 ELSE 0
                            END
                        ),
                        0
                    ) AS failed,
                    COALESCE(
                        AVG(duration_ms),
                        0
                    ) AS avg_duration_ms
                FROM telemetry_spans
                """
            ).fetchone()

        executions = int(
            trace["total"]
        )

        completed = int(
            trace["completed"]
        )

        failed = int(
            trace["failed"]
        )

        return {
            "executions": executions,
            "completed_executions": completed,
            "failed_executions": failed,
            "execution_success_rate": (
                completed / executions
                if executions
                else 0.0
            ),
            "avg_execution_duration_ms": float(
                trace["avg_duration_ms"]
            ),
            "spans": int(spans["total"]),
            "completed_spans": int(
                spans["completed"]
            ),
            "failed_spans": int(
                spans["failed"]
            ),
            "avg_span_duration_ms": float(
                spans["avg_duration_ms"]
            ),
        }

    def stage_metrics(
        self,
        stage: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Return metrics for actual workflow stages only.

        Execution-level and recovery-level spans have no stage
        and are intentionally excluded.
        """

        where = "WHERE stage <> ''"
        parameters: list[Any] = []

        if stage is not None:
            where += " AND stage = ?"
            parameters.append(stage)

        with self._connect() as connection:
            rows = connection.execute(
                f"""
                SELECT
                    stage,
                    COUNT(*) AS executions,
                    COALESCE(
                        SUM(
                            CASE
                                WHEN status = 'completed'
                                THEN 1 ELSE 0
                            END
                        ),
                        0
                    ) AS completed,
                    COALESCE(
                        SUM(
                            CASE
                                WHEN status = 'failed'
                                THEN 1 ELSE 0
                            END
                        ),
                        0
                    ) AS failed,
                    COALESCE(
                        AVG(duration_ms),
                        0
                    ) AS avg_duration_ms,
                    COALESCE(
                        AVG(
                            CAST(
                                json_extract(
                                    attributes,
                                    '$.attempt'
                                )
                                AS REAL
                            )
                        ),
                        0
                    ) AS avg_attempt
                FROM telemetry_spans
                {where}
                GROUP BY stage
                ORDER BY stage
                """,
                parameters,
            ).fetchall()

        return [
            dict(row)
            for row in rows
        ]


class TelemetryRecorder:
    """
    Fault-isolating telemetry facade.

    Observability failures never propagate into engineering
    execution.
    """

    def __init__(
        self,
        store: TelemetryStore | None = None,
    ) -> None:
        self.store = store or TelemetryStore()

    def start_trace(
        self,
        trace_id: str,
        execution_id: str,
        *,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        try:
            self.store.start_trace(
                trace_id,
                execution_id,
                metadata=metadata,
            )
        except Exception:
            pass

    def finish_trace(
        self,
        trace_id: str,
        *,
        status: str,
        error: str = "",
    ) -> None:
        try:
            self.store.finish_trace(
                trace_id,
                status=status,
                error=error,
            )
        except Exception:
            pass

    def start_span(
        self,
        trace_id: str,
        execution_id: str,
        *,
        name: str,
        kind: str,
        stage: str = "",
        agent: str = "",
        attributes: dict[str, Any] | None = None,
    ) -> int | None:
        try:
            return self.store.start_span(
                trace_id,
                execution_id,
                name=name,
                kind=kind,
                stage=stage,
                agent=agent,
                attributes=attributes,
            )
        except Exception:
            return None

    def finish_span(
        self,
        span_id: int | None,
        *,
        status: str,
        error: str = "",
        attributes: dict[str, Any] | None = None,
    ) -> None:
        if span_id is None:
            return

        try:
            self.store.finish_span(
                span_id,
                status=status,
                error=error,
                attributes=attributes,
            )
        except Exception:
            pass
