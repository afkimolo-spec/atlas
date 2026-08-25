from pathlib import Path
from tempfile import TemporaryDirectory

from atlas.core.execution import (
    ExecutionState,
    ExecutionStateMachine,
    StageState,
)
from atlas.planning import TaskStage


print("=" * 60)
print("ATLAS EXECUTION PERSISTENCE")
print("=" * 60)

with TemporaryDirectory() as tmp:
    database = Path(tmp) / "atlas.db"

    execution = ExecutionStateMachine(
        stages=[
            TaskStage.DEVELOPMENT,
        ]
    )

    execution.execution_id = "persistence-test"

    execution.start()

    execution.start_stage(
        TaskStage.DEVELOPMENT
    )

    execution.complete_stage(
        TaskStage.DEVELOPMENT,
        "Persistence test completed.",
    )

    execution.complete(
        reason="Persistence test completed",
    )

    execution.save(
        database=database,
    )

    print("Saved state :", execution.state.value)
    print("Saved stage :", execution.get_stage(
        TaskStage.DEVELOPMENT
    ).state.value)

    restored = ExecutionStateMachine.load(
        execution_id="persistence-test",
        database=database,
    )

    print("Loaded state:", restored.state.value)
    print("Loaded stage:", restored.get_stage(
        TaskStage.DEVELOPMENT
    ).state.value)

    assert restored.state == ExecutionState.COMPLETED

    assert (
        restored.get_stage(
            TaskStage.DEVELOPMENT
        ).state
        == StageState.COMPLETED
    )

    assert (
        restored.get_stage(
            TaskStage.DEVELOPMENT
        ).result
        == "Persistence test completed."
    )

    assert restored.execution_id == "persistence-test"

print("=" * 60)
print("Execution persistence verified.")
print("=" * 60)
