from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

from atlas.core.execution import (
    ExecutionState,
    ExecutionStateMachine,
    StageState,
)


class RecoveryAction(str, Enum):
    RETRY = "retry"
    FAIL = "fail"
    CANCEL = "cancel"


@dataclass(slots=True)
class RecoveryDecision:
    stage: str
    action: RecoveryAction
    reason: str
    attempt: int
    max_attempts: int

    @property
    def retryable(self) -> bool:
        return self.action == RecoveryAction.RETRY

    def snapshot(self) -> dict[str, Any]:
        return {
            "stage": self.stage,
            "action": self.action.value,
            "reason": self.reason,
            "attempt": self.attempt,
            "max_attempts": self.max_attempts,
            "retryable": self.retryable,
        }


@dataclass(slots=True)
class RecoveryPolicy:
    max_attempts: int = 3

    def __post_init__(self) -> None:
        if self.max_attempts < 1:
            raise ValueError(
                "max_attempts must be at least 1"
            )

    def decide(
        self,
        *,
        stage: str,
        attempt: int,
        error: str,
    ) -> RecoveryDecision:

        if not stage.strip():
            raise ValueError(
                "Recovery stage cannot be empty"
            )

        if attempt < 1:
            raise ValueError(
                "Recovery attempt must be at least 1"
            )

        if attempt < self.max_attempts:
            return RecoveryDecision(
                stage=stage,
                action=RecoveryAction.RETRY,
                reason=(
                    f"Stage '{stage}' failed on attempt "
                    f"{attempt}/{self.max_attempts}: "
                    f"{error}. Retrying."
                ),
                attempt=attempt,
                max_attempts=self.max_attempts,
            )

        return RecoveryDecision(
            stage=stage,
            action=RecoveryAction.FAIL,
            reason=(
                f"Stage '{stage}' failed on attempt "
                f"{attempt}/{self.max_attempts}: "
                f"{error}. Retry limit reached."
            ),
            attempt=attempt,
            max_attempts=self.max_attempts,
        )


@dataclass(slots=True)
class RecoveryManager:
    """
    Coordinates recovery decisions and persistence of recovery state.
    """

    policy: RecoveryPolicy = field(
        default_factory=RecoveryPolicy
    )

    persistence_path: Path | None = None

    def _persist(
        self,
        execution: ExecutionStateMachine,
        decision: RecoveryDecision | None = None,
    ) -> None:

        if self.persistence_path is None:
            return

        path = Path(self.persistence_path)

        path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        payload = {
            "execution": execution.snapshot(),
            "recovery": (
                decision.snapshot()
                if decision is not None
                else None
            ),
        }

        temporary = path.with_suffix(
            path.suffix + ".tmp"
        )

        temporary.write_text(
            json.dumps(
                payload,
                indent=2,
                sort_keys=True,
            ),
            encoding="utf-8",
        )

        temporary.replace(path)

    def recover(
        self,
        execution: ExecutionStateMachine,
        stage: str,
        error: str,
    ) -> RecoveryDecision:

        if execution.state != ExecutionState.FAILED:
            raise RuntimeError(
                "Recovery requires a failed execution."
            )

        stage_execution = execution.get_stage(stage)

        if stage_execution.state != StageState.FAILED:
            raise RuntimeError(
                f"Stage '{stage}' is not failed."
            )

        decision = self.policy.decide(
            stage=stage,
            attempt=stage_execution.attempts,
            error=error,
        )

        if decision.action == RecoveryAction.RETRY:
            execution.retry(
                reason=decision.reason
            )

        self._persist(
            execution,
            decision,
        )

        return decision

    def can_retry(
        self,
        execution: ExecutionStateMachine,
        stage: str,
    ) -> bool:

        stage_execution = execution.get_stage(stage)

        return (
            stage_execution.state == StageState.FAILED
            and stage_execution.attempts
            < self.policy.max_attempts
        )

    def save(
        self,
        execution: ExecutionStateMachine,
    ) -> None:
        """
        Persist the current execution state.
        """

        self._persist(execution)

    def load(
        self,
    ) -> dict[str, Any]:
        """
        Load persisted recovery state.
        """

        if self.persistence_path is None:
            raise RuntimeError(
                "Recovery persistence path is not configured."
            )

        path = Path(self.persistence_path)

        if not path.exists():
            raise FileNotFoundError(
                f"Recovery state not found: {path}"
            )

        return json.loads(
            path.read_text(
                encoding="utf-8"
            )
        )