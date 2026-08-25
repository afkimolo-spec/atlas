import tempfile
from pathlib import Path

from atlas.core.events import EventStore
from atlas.core.feedback import FeedbackStore


with tempfile.TemporaryDirectory() as directory:
    database = Path(directory) / "atlas.db"

    events = EventStore(database)
    feedback = FeedbackStore(database)

    events.record(
        "exec-1",
        "resource.acquired",
        stage="development",
        payload={
            "resource": "gpu",
            "owner": "development",
        },
    )

    feedback.record(
        __import__(
            "atlas.core.feedback",
            fromlist=["FeedbackRecord"],
        ).FeedbackRecord(
            execution_id="exec-1",
            stage="development",
            outcome="completed",
            duration_ms=100.0,
            attempts=1,
        )
    )

    restored_events = events.list("exec-1")
    restored_feedback = feedback.list(
        execution_id="exec-1",
    )

    assert len(restored_events) == 1
    assert len(restored_feedback) == 1
    assert restored_events[0]["payload"]["resource"] == "gpu"

print("=" * 60)
print("ATLAS OPERATIONAL PERSISTENCE")
print("=" * 60)
print("Events   :", len(restored_events))
print("Feedback :", len(restored_feedback))
print("=" * 60)
print("Operational persistence verified.")
