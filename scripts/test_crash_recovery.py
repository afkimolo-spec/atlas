from pathlib import Path
from tempfile import TemporaryDirectory

from atlas.core.execution import (
    ExecutionState,
    ExecutionStateMachine,
    StageState,
)
from atlas.planning import TaskStage


print("=" * 60)
print("ATLAS CRASH / RESTART RECOVERY")
print("=" * 60)

with TemporaryDirectory() as tmp:
    database = Path(tmp) / "atlas.db"

    execution = ExecutionStateMachine(
        stages=[
            TaskStage.DEVELOPMENT,
        ]
    )

    execution.execution_id = "crash-recovery-test"

    execution.start()

    execution.start_stage(
        TaskStage.DEVELOPMENT
    )

    execution.save(
        database=database,
    )

    print("Before crash:")
    print("State   :", execution.state.value)
    print("Stage   :", execution.get_stage(
        TaskStage.DEVELOPMENT
    ).state.value)
    print("Attempt :", execution.get_stage(
        TaskStage.DEVELOPMENT
    ).attempts)

    restored = ExecutionStateMachine.load(
        execution_id="crash-recovery-test",
        database=database,
    )

    print("-" * 60)
    print("After restart:")
    print("State   :", restored.state.value)
    print("Stage   :", restored.get_stage(
        TaskStage.DEVELOPMENT
    ).state.value)
    print("Attempt :", restored.get_stage(
        TaskStage.DEVELOPMENT
    ).attempts)

    assert restored.state == ExecutionState.RUNNING

    assert (
        restored.get_stage(
            TaskStage.DEVELOPMENT
        ).state
        == StageState.RUNNING
    )

    assert (
        restored.get_stage(
            TaskStage.DEVELOPMENT
        ).attempts
        == 1
    )

    restored.fail_stage(
        TaskStage.DEVELOPMENT,
        "Recovered execution failed during restart test.",
    )

    restored.fail(
        reason="Crash recovery test failure",
    )

    assert restored.state == ExecutionState.FAILED

    restored.retry()

    assert restored.state == ExecutionState.RETRYING

    restored.start()

    restored.start_stage(
        TaskStage.DEVELOPMENT
    )

    restored.complete_stage(
        TaskStage.DEVELOPMENT,
        "Recovered successfully after restart.",
    )

    restored.complete(
        reason="Crash recovery completed",
    )

    restored.save(
        database=database,
    )

    final = ExecutionStateMachine.load(
        execution_id="crash-recovery-test",
        database=database,
    )

    print("-" * 60)
    print("After recovery:")
    print("State   :", final.state.value)
    print("Stage   :", final.get_stage(
        TaskStage.DEVELOPMENT
    ).state.value)
    print("Attempts:", final.get_stage(
        TaskStage.DEVELOPMENT
    ).attempts)

    assert final.state == ExecutionState.COMPLETED

    assert (
        final.get_stage(
            TaskStage.DEVELOPMENT
        ).state
        == StageState.COMPLETED
    )

    assert (
        final.get_stage(
            TaskStage.DEVELOPMENT
        ).attempts
        == 2
    )

print("=" * 60)
print("Crash/restart recovery verified.")
print("=" * 60)
