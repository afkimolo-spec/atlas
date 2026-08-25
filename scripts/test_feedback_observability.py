import tempfile
from pathlib import Path

from atlas.core.events import EventStore
from atlas.core.feedback import (
    FeedbackRecord,
    FeedbackStore,
)
from atlas.core.observability import ExecutionObserver


with tempfile.TemporaryDirectory() as directory:
    database = Path(directory) / "atlas.db"

    events = EventStore(database)
    feedback = FeedbackStore(database)

    observer = ExecutionObserver(
        events=events,
        feedback=feedback,
    )

    execution_id = "execution-test"

    observer.execution_started(execution_id)
    observer.stage_started(
        execution_id,
        "development",
    )

    observer.stage_completed(
        execution_id,
        "development",
        duration_ms=125.5,
        attempts=1,
    )

    observer.recovery(
        execution_id,
        "development",
        action="retry",
        attempt=1,
        reason="transient failure",
    )

    observer.stage_failed(
        execution_id,
        "development",
        duration_ms=80.0,
        attempts=2,
        error="test failure",
    )

    observer.execution_failed(
        execution_id,
        "stage failed",
    )

    records = feedback.list(
        execution_id=execution_id,
    )

    assert len(records) == 2
    assert records[0]["outcome"] == "failed"
    assert records[1]["outcome"] == "completed"

    summary = feedback.summary(
        stage="development",
    )

    assert summary["total"] == 2
    assert summary["completed"] == 1
    assert summary["failed"] == 1

    event_records = events.list(
        execution_id,
    )

    assert len(event_records) == 6
    assert event_records[0]["event_type"] == (
        "execution.started"
    )
    assert event_records[-1]["event_type"] == (
        "execution.failed"
    )

print("=" * 60)
print("ATLAS FEEDBACK + OBSERVABILITY")
print("=" * 60)
print("Feedback records :", len(records))
print("Completed        :", summary["completed"])
print("Failed           :", summary["failed"])
print("Events           :", len(event_records))
print("=" * 60)
print("Feedback and observability verified.")
