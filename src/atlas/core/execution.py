from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Iterable

from atlas.planning import TaskPlan, TaskStage
from atlas.paths import ROOT
DATABASE = ROOT / ".ai" / "memory" / "db" / "atlas.db"


class InvalidStateTransition(RuntimeError):
    """Raised when an invalid execution state transition is requested."""


class StageDependencyError(RuntimeError):
    """Raised when a stage cannot execute because dependencies are incomplete."""


class ExecutionState(str, Enum):
    CREATED = "created"
    RUNNING = "running"
    PAUSED = "paused"
    RETRYING = "retrying"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class StageState(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass(slots=True)
class ExecutionEvent:
    from_state: ExecutionState
    to_state: ExecutionState
    reason: str = ""
    timestamp: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


@dataclass(slots=True)
class StageExecution:
    name: str
    state: StageState = StageState.PENDING
    attempts: int = 0
    started_at: datetime | None = None
    completed_at: datetime | None = None
    result: str = ""
    error: str = ""

    def start(self) -> None:
        if self.state != StageState.PENDING:
            raise InvalidStateTransition(
                f"Cannot start stage {self.name}: "
                f"current state is {self.state.value}"
            )

        self.state = StageState.RUNNING
        self.attempts += 1
        self.started_at = datetime.now(timezone.utc)
        self.completed_at = None
        self.result = ""
        self.error = ""

    def complete(self, result: str = "") -> None:
        if self.state != StageState.RUNNING:
            raise InvalidStateTransition(
                f"Cannot complete stage {self.name}: "
                f"current state is {self.state.value}"
            )

        self.state = StageState.COMPLETED
        self.completed_at = datetime.now(timezone.utc)
        self.result = result
        self.error = ""

    def fail(self, error: str) -> None:
        if self.state != StageState.RUNNING:
            raise InvalidStateTransition(
                f"Cannot fail stage {self.name}: "
                f"current state is {self.state.value}"
            )

        self.state = StageState.FAILED
        self.completed_at = datetime.now(timezone.utc)
        self.error = error

    def skip(self, reason: str = "") -> None:
        if self.state != StageState.PENDING:
            raise InvalidStateTransition(
                f"Cannot skip stage {self.name}: "
                f"current state is {self.state.value}"
            )

        self.state = StageState.SKIPPED
        self.completed_at = datetime.now(timezone.utc)
        self.error = reason

    def reset_for_retry(self) -> None:
        if self.state != StageState.FAILED:
            raise InvalidStateTransition(
                f"Cannot retry stage {self.name}: "
                f"current state is {self.state.value}"
            )

        self.state = StageState.PENDING
        self.started_at = None
        self.completed_at = None
        self.result = ""
        self.error = ""

    def snapshot(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "state": self.state.value,
            "attempts": self.attempts,
            "started_at": (
                self.started_at.isoformat()
                if self.started_at
                else None
            ),
            "completed_at": (
                self.completed_at.isoformat()
                if self.completed_at
                else None
            ),
            "result": self.result,
            "error": self.error,
        }

    @classmethod
    def from_snapshot(
        cls,
        snapshot: dict[str, Any],
    ) -> StageExecution:
        return cls(
            name=str(snapshot["name"]),
            state=StageState(snapshot["state"]),
            attempts=int(snapshot.get("attempts", 0)),
            started_at=(
                datetime.fromisoformat(snapshot["started_at"])
                if snapshot.get("started_at")
                else None
            ),
            completed_at=(
                datetime.fromisoformat(snapshot["completed_at"])
                if snapshot.get("completed_at")
                else None
            ),
            result=str(snapshot.get("result", "")),
            error=str(snapshot.get("error", "")),
        )


@dataclass(slots=True)
class ExecutionStateMachine:
    """
    Atlas execution state machine.

    Supports:
        - TaskPlan-backed execution
        - Explicit stage lists
        - Retry and recovery
        - Dependency validation
        - Durable SQLite snapshots
        - Restoration from persisted snapshots
    """

    plan: TaskPlan | None = None
    state: ExecutionState = ExecutionState.CREATED
    history: list[ExecutionEvent] = field(default_factory=list)
    stages: dict[str, StageExecution] | list[Any] = field(
        default_factory=dict
    )
    execution_id: str | None = None

    def __post_init__(self) -> None:
        """
        Normalize all supported constructor forms.

        Existing Atlas tests and callers may construct:

            ExecutionStateMachine(
                stages=[TaskStage.DEVELOPMENT]
            )

        or:

            ExecutionStateMachine(
                plan=task_plan
            )

        The internal representation is always a dictionary.
        """

        # Compatibility with positional construction where a stage list
        # was historically supplied as the first argument.
        if self.plan is not None and not isinstance(self.plan, TaskPlan):
            if isinstance(self.plan, (list, tuple, set)):
                supplied_stages = self.plan
                self.plan = None

                if not self.stages:
                    self.stages = {}

                for stage in supplied_stages:
                    self._register_stage(stage)

        # Normalize explicitly supplied stage collections.
        if isinstance(self.stages, (list, tuple, set)):
            supplied_stages = self.stages
            self.stages = {}

            for stage in supplied_stages:
                self._register_stage(stage)

        elif not isinstance(self.stages, dict):
            raise TypeError(
                "Execution stages must be a dictionary or iterable "
                "of TaskStage values."
            )

        # Add stages defined by the task plan.
        if self.plan is not None:
            for step in self.plan.steps:
                self._register_stage(step.stage)

    def _register_stage(
        self,
        stage: str | TaskStage | StageExecution,
    ) -> StageExecution:

        if isinstance(stage, StageExecution):
            name = stage.name
            execution = stage
        else:
            if isinstance(stage, TaskStage):
                name = stage.value
            else:
                name = str(stage).strip()

            if not name:
                raise ValueError(
                    "Stage name cannot be empty."
                )

            execution = StageExecution(name=name)

        existing = self.stages.get(name)

        if existing is not None:
            return existing

        self.stages[name] = execution
        return execution

    @property
    def is_terminal(self) -> bool:
        return self.state in {
            ExecutionState.COMPLETED,
            ExecutionState.FAILED,
            ExecutionState.CANCELLED,
        }

    @property
    def is_running(self) -> bool:
        return self.state == ExecutionState.RUNNING

    @property
    def is_paused(self) -> bool:
        return self.state == ExecutionState.PAUSED

    def _transition(
        self,
        target: ExecutionState,
        *,
        reason: str = "",
    ) -> None:

        allowed: dict[
            ExecutionState,
            set[ExecutionState],
        ] = {
            ExecutionState.CREATED: {
                ExecutionState.RUNNING,
            },
            ExecutionState.RUNNING: {
                ExecutionState.PAUSED,
                ExecutionState.RETRYING,
                ExecutionState.COMPLETED,
                ExecutionState.FAILED,
                ExecutionState.CANCELLED,
            },
            ExecutionState.PAUSED: {
                ExecutionState.RUNNING,
                ExecutionState.CANCELLED,
            },
            ExecutionState.RETRYING: {
                ExecutionState.RUNNING,
                ExecutionState.FAILED,
            },
            ExecutionState.COMPLETED: set(),
            ExecutionState.FAILED: {
                ExecutionState.RETRYING,
            },
            ExecutionState.CANCELLED: set(),
        }

        if target not in allowed[self.state]:
            raise InvalidStateTransition(
                f"Invalid execution transition: "
                f"{self.state.value} -> {target.value}"
            )

        previous = self.state
        self.state = target

        self.history.append(
            ExecutionEvent(
                from_state=previous,
                to_state=target,
                reason=reason,
            )
        )

    def start(self, *, reason: str = "") -> None:
        self._transition(
            ExecutionState.RUNNING,
            reason=reason,
        )

    def pause(self, *, reason: str = "") -> None:
        self._transition(
            ExecutionState.PAUSED,
            reason=reason,
        )

    def resume(self, *, reason: str = "") -> None:
        self._transition(
            ExecutionState.RUNNING,
            reason=reason,
        )

    def retry(self, reason: str = "") -> None:
        if self.state != ExecutionState.FAILED:
            raise InvalidStateTransition(
                "Only failed executions can be retried."
            )

        for stage in self.stages.values():
            if stage.state == StageState.FAILED:
                stage.reset_for_retry()

        self._transition(
            ExecutionState.RETRYING,
            reason=reason or "Execution retry requested",
        )

    def complete(self, *, reason: str = "") -> None:
        if self.plan is not None:
            incomplete = [
                name
                for name, stage in self.stages.items()
                if stage.state not in {
                    StageState.COMPLETED,
                    StageState.SKIPPED,
                }
            ]

            if incomplete:
                raise InvalidStateTransition(
                    "Cannot complete execution; "
                    f"incomplete stages: {', '.join(incomplete)}"
                )

        self._transition(
            ExecutionState.COMPLETED,
            reason=reason,
        )

    def fail(self, reason: str = "") -> None:
        self._transition(
            ExecutionState.FAILED,
            reason=reason,
        )

    def cancel(self, reason: str = "") -> None:
        self._transition(
            ExecutionState.CANCELLED,
            reason=reason,
        )

    def add_stage(
        self,
        name: str | TaskStage,
    ) -> StageExecution:

        if isinstance(name, TaskStage):
            name = name.value

        name = str(name).strip()

        if not name:
            raise ValueError(
                "Stage name cannot be empty."
            )

        if name in self.stages:
            return self.stages[name]

        stage = StageExecution(name=name)
        self.stages[name] = stage

        return stage

    def stage(
        self,
        name: str | TaskStage,
    ) -> StageExecution:

        if isinstance(name, TaskStage):
            name = name.value

        key = str(name)

        try:
            return self.stages[key]

        except KeyError as exc:
            raise KeyError(
                f"Unknown execution stage: {name}"
            ) from exc

    def get_stage(
        self,
        name: str | TaskStage,
    ) -> StageExecution:
        return self.stage(name)

    def _dependencies(
        self,
        name: str | TaskStage,
    ) -> list[TaskStage]:

        if self.plan is None:
            return []

        if isinstance(name, str):
            try:
                stage = TaskStage(name)
            except ValueError:
                return []
        else:
            stage = name

        step = self.plan.get(stage)

        if step is None:
            return []

        return list(step.dependencies)

    def dependencies_satisfied(
        self,
        name: str | TaskStage,
    ) -> bool:

        for dependency in self._dependencies(name):
            dependency_stage = self.stage(dependency)

            if dependency_stage.state != StageState.COMPLETED:
                return False

        return True

    def ready(
        self,
        name: str | TaskStage,
    ) -> bool:

        stage = self.stage(name)

        return (
            self.state == ExecutionState.RUNNING
            and stage.state == StageState.PENDING
            and self.dependencies_satisfied(name)
        )

    def start_stage(
        self,
        name: str | TaskStage,
    ) -> StageExecution:

        if self.state != ExecutionState.RUNNING:
            raise InvalidStateTransition(
                "Cannot start a stage unless "
                "execution is running."
            )

        stage = self.stage(name)

        if stage.state != StageState.PENDING:
            raise InvalidStateTransition(
                f"Cannot start stage {stage.name}: "
                f"current state is {stage.state.value}"
            )

        if not self.dependencies_satisfied(name):
            dependencies = self._dependencies(name)

            blocked = [
                dependency.value
                for dependency in dependencies
                if self.stage(dependency).state
                != StageState.COMPLETED
            ]

            raise StageDependencyError(
                f"Stage '{stage.name}' is blocked by: "
                f"{', '.join(blocked)}"
            )

        stage.start()

        return stage

    def complete_stage(
        self,
        name: str | TaskStage,
        result: str = "",
    ) -> StageExecution:

        stage = self.stage(name)
        stage.complete(result)

        return stage

    def fail_stage(
        self,
        name: str | TaskStage,
        error: str,
    ) -> StageExecution:

        stage = self.stage(name)
        stage.fail(error)

        return stage

    def skip_stage(
        self,
        name: str | TaskStage,
        reason: str = "",
    ) -> StageExecution:

        stage = self.stage(name)
        stage.skip(reason)

        return stage

    def next_ready_stage(self) -> StageExecution | None:
        for name in self.stages:
            if self.ready(name):
                return self.stages[name]

        return None

    def snapshot(self) -> dict[str, Any]:
        return {
            "execution_id": self.execution_id,
            "state": self.state.value,
            "terminal": self.is_terminal,
            "running": self.is_running,
            "paused": self.is_paused,
            "history": [
                {
                    "from": event.from_state.value,
                    "to": event.to_state.value,
                    "timestamp": event.timestamp.isoformat(),
                    "reason": event.reason,
                }
                for event in self.history
            ],
            "stages": {
                name: stage.snapshot()
                for name, stage in self.stages.items()
            },
        }

    def save(
        self,
        execution_id: str | None = None,
        database: str | Path = DATABASE,
    ) -> str:

        if execution_id is not None:
            self.execution_id = execution_id

        if not self.execution_id:
            raise ValueError(
                "execution_id is required before saving."
            )

        database = Path(database)

        database.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        snapshot = self.snapshot()

        with sqlite3.connect(database) as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS executions (
                    execution_id TEXT PRIMARY KEY,
                    state TEXT NOT NULL,
                    snapshot TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )

            connection.execute(
                """
                INSERT INTO executions (
                    execution_id,
                    state,
                    snapshot,
                    updated_at
                )
                VALUES (?, ?, ?, ?)
                ON CONFLICT(execution_id)
                DO UPDATE SET
                    state = excluded.state,
                    snapshot = excluded.snapshot,
                    updated_at = excluded.updated_at
                """,
                (
                    self.execution_id,
                    self.state.value,
                    json.dumps(snapshot),
                    datetime.now(timezone.utc).isoformat(),
                ),
            )

            connection.commit()

        return self.execution_id

    @classmethod
    def load(
        cls,
        execution_id: str,
        database: str | Path = DATABASE,
        plan: TaskPlan | None = None,
    ) -> ExecutionStateMachine:

        database = Path(database)

        if not database.exists():
            raise FileNotFoundError(
                f"Execution database does not exist: {database}"
            )

        with sqlite3.connect(database) as connection:
            connection.row_factory = sqlite3.Row

            try:
                row = connection.execute(
                    """
                    SELECT snapshot
                    FROM executions
                    WHERE execution_id = ?
                    """,
                    (execution_id,),
                ).fetchone()
            except sqlite3.OperationalError as exc:
                raise KeyError(
                    f"Execution not found: {execution_id}"
                ) from exc

        if row is None:
            raise KeyError(
                f"Execution not found: {execution_id}"
            )

        snapshot = json.loads(row["snapshot"])

        machine = cls(
            plan=plan,
            state=ExecutionState(snapshot["state"]),
            execution_id=execution_id,
        )

        machine.stages.clear()

        for name, stage_snapshot in snapshot.get(
            "stages",
            {},
        ).items():
            machine.stages[name] = StageExecution.from_snapshot(
                stage_snapshot
            )

        machine.history = [
            ExecutionEvent(
                from_state=ExecutionState(event["from"]),
                to_state=ExecutionState(event["to"]),
                timestamp=datetime.fromisoformat(
                    event["timestamp"]
                ),
                reason=event.get("reason", ""),
            )
            for event in snapshot.get("history", [])
        ]

        return machine
