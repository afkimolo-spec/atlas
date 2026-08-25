from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

from atlas.core.execution import (
    ExecutionEvent,
    ExecutionState,
    ExecutionStateMachine,
    StageExecution,
    StageState,
)
from atlas.planning import TaskPlan


ROOT = Path("/home/administrator/workspace/atlas")
DATABASE = ROOT / ".ai" / "memory" / "db" / "atlas.db"


class ExecutionStore:
    """
    Persistent storage and reconstruction for Atlas executions.
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
                CREATE TABLE IF NOT EXISTS executions (
                    execution_id TEXT PRIMARY KEY,
                    state TEXT NOT NULL,
                    snapshot TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS
                idx_executions_state
                ON executions(state)
                """
            )

            connection.commit()

    def save(
        self,
        execution_id: str,
        execution: ExecutionStateMachine,
    ) -> None:
        if not execution_id.strip():
            raise ValueError(
                "execution_id cannot be empty"
            )

        snapshot = execution.snapshot()

        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO executions (
                    execution_id,
                    state,
                    snapshot
                )
                VALUES (?, ?, ?)
                ON CONFLICT(execution_id)
                DO UPDATE SET
                    state = excluded.state,
                    snapshot = excluded.snapshot,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (
                    execution_id,
                    execution.state.value,
                    json.dumps(
                        snapshot,
                        ensure_ascii=False,
                    ),
                ),
            )

            connection.commit()

    def load(
        self,
        execution_id: str,
    ) -> dict[str, Any] | None:
        if not execution_id.strip():
            raise ValueError(
                "execution_id cannot be empty"
            )

        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT snapshot
                FROM executions
                WHERE execution_id = ?
                """,
                (execution_id,),
            ).fetchone()

        if row is None:
            return None

        return json.loads(row["snapshot"])

    def restore(
        self,
        execution_id: str,
        plan: TaskPlan,
    ) -> ExecutionStateMachine | None:
        """
        Reconstruct an ExecutionStateMachine from persistent state.
        """

        snapshot = self.load(execution_id)

        if snapshot is None:
            return None

        execution = ExecutionStateMachine(
            plan=plan,
        )

        execution.state = ExecutionState(
            snapshot["state"]
        )

        execution.history.clear()

        for event in snapshot.get("history", []):
            execution.history.append(
                ExecutionEvent(
                    from_state=ExecutionState(
                        event["from"]
                    ),
                    to_state=ExecutionState(
                        event["to"]
                    ),
                    reason=event.get("reason", ""),
                    timestamp=datetime.fromisoformat(
                        event["timestamp"]
                    ),
                )
            )

        for name, data in snapshot.get(
            "stages",
            {},
        ).items():

            if name not in execution.stages:
                execution.stages[name] = StageExecution(
                    name=name
                )

            stage = execution.stages[name]

            stage.state = StageState(
                data["state"]
            )

            stage.attempts = int(
                data.get("attempts", 0)
            )

            started_at = data.get("started_at")
            completed_at = data.get("completed_at")

            stage.started_at = (
                datetime.fromisoformat(started_at)
                if started_at
                else None
            )

            stage.completed_at = (
                datetime.fromisoformat(completed_at)
                if completed_at
                else None
            )

            stage.result = data.get(
                "result",
                "",
            )

            stage.error = data.get(
                "error",
                "",
            )

        return execution

    def state(
        self,
        execution_id: str,
    ) -> ExecutionState | None:
        snapshot = self.load(execution_id)

        if snapshot is None:
            return None

        return ExecutionState(
            snapshot["state"]
        )

    def exists(
        self,
        execution_id: str,
    ) -> bool:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT 1
                FROM executions
                WHERE execution_id = ?
                """,
                (execution_id,),
            ).fetchone()

        return row is not None

    def delete(
        self,
        execution_id: str,
    ) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                DELETE FROM executions
                WHERE execution_id = ?
                """,
                (execution_id,)

            )

            connection.commit()

    def list(
        self,
        *,
        state: ExecutionState | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        if limit <= 0:
            raise ValueError(
                "limit must be greater than zero"
            )

        with self._connect() as connection:

            if state is None:
                rows = connection.execute(
                    """
                    SELECT
                        execution_id,
                        state,
                        snapshot,
                        created_at,
                        updated_at
                    FROM executions
                    ORDER BY updated_at DESC
                    LIMIT ?
                    """,
                    (limit,),
                ).fetchall()

            else:
                rows = connection.execute(
                    """
                    SELECT
                        execution_id,
                        state,
                        snapshot,
                        created_at,
                        updated_at
                    FROM executions
                    WHERE state = ?
                    ORDER BY updated_at DESC
                    LIMIT ?
                    """,
                    (
                        state.value,
                        limit,
                    ),
                ).fetchall()

        return [
            {
                "execution_id": row["execution_id"],
                "state": row["state"],
                "snapshot": json.loads(
                    row["snapshot"]
                ),
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
            }
            for row in rows
        ]
