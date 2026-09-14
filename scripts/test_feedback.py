from __future__ import annotations

import time
import tempfile
from pathlib import Path

from atlas.core.feedback import (
    FeedbackStore,
)


print("=" * 60)
print("ATLAS FEEDBACK INFRASTRUCTURE")
print("=" * 60)

with tempfile.TemporaryDirectory() as directory:
    database = Path(directory) / "atlas.db"

    store = FeedbackStore(database)

    execution_id = "feedback-test"

    store.start_execution(
        execution_id,
        stage_count=2,
        metadata={"task": "feedback test"},
    )

    first = store.start_stage(
        execution_id,
        "research",
        attempt=1,
    )

    assert first > 0

    time.sleep(0.005)

    store.complete_stage(
        first,
        metadata={"agent": "researcher"},
    )

    second = store.start_stage(
        execution_id,
        "development",
        attempt=1,
    )

    store.fail_stage(
        second,
        error="simulated failure",
        metadata={"agent": "developer"},
    )

    store.record_retry(
        execution_id
    )

    third = store.start_stage(
        execution_id,
        "development",
        attempt=2,
    )

    store.complete_stage(
        third
    )

    store.complete_execution(
        execution_id,
        completed_stages=2,
    )

    execution = store.execution(
        execution_id
    )

    assert execution is not None
    assert execution["status"] == "completed"
    assert execution["completed_stages"] == 2
    assert execution["retries"] == 1
    assert execution["total_duration_ms"] >= 0

    stages = store.stages(
        execution_id
    )

    assert len(stages) == 3
    assert stages[0]["outcome"] == "completed"
    assert stages[1]["outcome"] == "failed"
    assert stages[2]["outcome"] == "completed"

    development = store.summary(
        stage="development"
    )

    assert development["total"] == 2
    assert development["completed"] == 1
    assert development["failed"] == 1
    assert development["success_rate"] == 0.5

    summary = store.execution_summary()

    assert summary["total"] == 1
    assert summary["completed"] == 1
    assert summary["failed"] == 0
    assert summary["retries"] == 1

    signals = store.optimization_signals()

    assert signals["slowest_stage"] is not None
    assert (
        signals["most_failure_prone_stage"]
        is not None
    )

    # Verify persistence across a new store instance.
    restarted = FeedbackStore(
        database
    )

    restored = restarted.execution(
        execution_id
    )

    assert restored is not None
    assert restored["retries"] == 1

print("Execution metrics : verified")
print("Stage outcomes    : verified")
print("Retry tracking    : verified")
print("Querying          : verified")
print("Restart persistence: verified")
print("Optimization data : verified")
print("=" * 60)
print("Feedback infrastructure verified.")
print("=" * 60)
