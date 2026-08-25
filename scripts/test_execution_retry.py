from atlas.core.execution import (
    ExecutionState,
    ExecutionStateMachine,
    StageState,
)
from atlas.planning import TaskStage


machine = ExecutionStateMachine(
    stages=[
        TaskStage.DEVELOPMENT,
    ]
)

print("=" * 60)
print("ATLAS EXECUTION RETRY")
print("=" * 60)

machine.start()

assert machine.state == ExecutionState.RUNNING

machine.start_stage(
    TaskStage.DEVELOPMENT
)

assert (
    machine.get_stage(
        TaskStage.DEVELOPMENT
    ).state
    == StageState.RUNNING
)

machine.fail_stage(
    TaskStage.DEVELOPMENT,
    "Compilation failed.",
)

assert (
    machine.get_stage(
        TaskStage.DEVELOPMENT
    ).state
    == StageState.FAILED
)

machine.fail(
    "Development stage failed."
)

print(
    "Failed state  :",
    machine.state.value,
)

assert machine.state == ExecutionState.FAILED

stage = machine.get_stage(
    TaskStage.DEVELOPMENT
)

print(
    "Stage state   :",
    stage.state.value,
)

print(
    "Attempts      :",
    stage.attempts,
)

assert stage.attempts == 1

machine.retry()

print(
    "Retry state   :",
    machine.state.value,
)

assert machine.state == ExecutionState.RETRYING

assert (
    machine.get_stage(
        TaskStage.DEVELOPMENT
    ).state
    == StageState.PENDING
)

machine.start()

assert machine.state == ExecutionState.RUNNING

machine.start_stage(
    TaskStage.DEVELOPMENT
)

assert (
    machine.get_stage(
        TaskStage.DEVELOPMENT
    ).attempts == 2
)

machine.complete_stage(
    TaskStage.DEVELOPMENT,
    "Development succeeded after retry.",
)

machine.complete()

print(
    "Final state   :",
    machine.state.value,
)

assert machine.state == ExecutionState.COMPLETED

print(
    "Attempts      :",
    machine.get_stage(
        TaskStage.DEVELOPMENT
    ).attempts,
)

assert (
    machine.get_stage(
        TaskStage.DEVELOPMENT
    ).attempts == 2
)

print("=" * 60)
print("Execution retry verified.")
print("=" * 60)
