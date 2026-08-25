from __future__ import annotations

import tempfile
from pathlib import Path

from atlas.core.execution import (
    ExecutionState,
    ExecutionStateMachine,
    StageState,
)
from atlas.core.execution_store import ExecutionStore


print("=" * 60)
print("ATLAS EXECUTION STORE")
print("=" * 60)

with tempfile.TemporaryDirectory() as directory:

    database = Path(directory) / "atlas.db"

    store = ExecutionStore(database)

    execution = ExecutionStateMachine()

    execution.add_stage("development")

    execution.start()
    execution.start_stage("development")
    execution.complete_stage(
        "development",
        "Development completed.",
    )
    execution.complete()

    execution_id = "test-execution-001"

    store.save(
        execution_id,
        execution,
    )

    assert store.exists(execution_id)

    snapshot = store.load(execution_id)

    assert snapshot is not None
    assert snapshot["state"] == "completed"
    assert (
        snapshot["stages"]["development"]["state"]
        == "completed"
    )

    assert (
        store.state(execution_id)
        == ExecutionState.COMPLETED
    )

    records = store.list()

    assert len(records) == 1
    assert records[0]["execution_id"] == execution_id

    store.delete(execution_id)

    assert not store.exists(execution_id)
    assert store.load(execution_id) is None

print("Saved state : completed")
print("Loaded state: completed")
print("Deleted     : verified")
print("=" * 60)
print("Execution store verified.")
print("=" * 60)
