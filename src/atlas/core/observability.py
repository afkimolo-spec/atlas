from __future__ import annotations

from atlas.core.events import EventStore
from atlas.core.feedback import FeedbackRecord, FeedbackStore


class ExecutionObserver:
    """
    Central operational observer for execution lifecycle events.

    Keeps observability separate from execution business logic.
    """

    def __init__(
        self,
        events: EventStore | None = None,
        feedback: FeedbackStore | None = None,
    ) -> None:
        self.events = events or EventStore()
        self.feedback = feedback or FeedbackStore()

    def execution_started(
        self,
        execution_id: str,
    ) -> None:
        self.events.record(
            execution_id,
            "execution.started",
        )

    def stage_started(
        self,
        execution_id: str,
        stage: str,
    ) -> None:
        self.events.record(
            execution_id,
            "stage.started",
            stage=stage,
        )

    def stage_completed(
        self,
        execution_id: str,
        stage: str,
        *,
        duration_ms: float,
        attempts: int,
    ) -> None:
        self.events.record(
            execution_id,
            "stage.completed",
            stage=stage,
            payload={
                "duration_ms": duration_ms,
                "attempts": attempts,
            },
        )

        self.feedback.record(
            FeedbackRecord(
                execution_id=execution_id,
                stage=stage,
                outcome="completed",
                duration_ms=duration_ms,
                attempts=attempts,
            )
        )

    def stage_failed(
        self,
        execution_id: str,
        stage: str,
        *,
        duration_ms: float,
        attempts: int,
        error: str,
    ) -> None:
        self.events.record(
            execution_id,
            "stage.failed",
            stage=stage,
            payload={
                "duration_ms": duration_ms,
                "attempts": attempts,
                "error": error,
            },
        )

        self.feedback.record(
            FeedbackRecord(
                execution_id=execution_id,
                stage=stage,
                outcome="failed",
                duration_ms=duration_ms,
                attempts=attempts,
                error=error,
            )
        )

    def recovery(
        self,
        execution_id: str,
        stage: str,
        *,
        action: str,
        attempt: int,
        reason: str,
    ) -> None:
        self.events.record(
            execution_id,
            "recovery.decision",
            stage=stage,
            payload={
                "action": action,
                "attempt": attempt,
                "reason": reason,
            },
        )

    def execution_completed(
        self,
        execution_id: str,
    ) -> None:
        self.events.record(
            execution_id,
            "execution.completed",
        )

    def execution_failed(
        self,
        execution_id: str,
        reason: str,
    ) -> None:
        self.events.record(
            execution_id,
            "execution.failed",
            payload={"reason": reason},
        )
