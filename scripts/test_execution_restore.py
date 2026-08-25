from __future__ import annotations

from atlas.core.execution import (
    ExecutionState,
    ExecutionStateMachine,
    StageState,
)
from atlas.core.execution_store import ExecutionStore
from atlas.planning import TaskPlanner, TaskStage


print("=" * 60)
print("ATLAS EXECUTION RESTORE")
print("=" * 60)

planner = TaskPlanner()

plan = planner.plan(
    "Test crash recovery",
    research=True,
    architecture=True,
    development=False,
    review=False,
    operations=False,
)

store = ExecutionStore()

execution_id = "test-crash-recovery"

store.delete(execution_id)

execution = ExecutionStateMachine(
    plan=plan,
)

execution.start()

execution.start_stage(
    TaskStage.RESEARCH
)

execution.complete_stage(
    TaskStage.RESEARCH,
    "Research completed before simulated crash.",
)

store.save(
    execution_id,
    execution,
)

print(
    f"Saved state : {execution.state.value}"
)

print(
    f"Saved research : "
    f"{execution.get_stage(TaskStage.RESEARCH).state.value}"
)

restored = store.restore(
    execution_id,
    plan,
)

if restored is None:
    raise AssertionError(
        "Execution restore returned None."
    )

print(
    f"Restored state : "
    f"{restored.state.value}"
)

print(
    f"Restored research : "
    f"{restored.get_stage(TaskStage.RESEARCH).state.value}"
)

print(
    f"Restored architecture : "
    f"{restored.get_stage(TaskStage.ARCHITECTURE).state.value}"
)

if restored.state != ExecutionState.RUNNING:
    raise AssertionError(
        "Execution state was not restored."
    )

if (
    restored.get_stage(TaskStage.RESEARCH).state
    != StageState.COMPLETED
):
    raise AssertionError(
        "Completed research stage was not restored."
    )

if (
    restored.get_stage(TaskStage.ARCHITECTURE).state
    != StageState.PENDING
):
    raise AssertionError(
        "Pending architecture stage was not restored."
    )

if not restored.ready(TaskStage.ARCHITECTURE):
    raise AssertionError(
        "Restored execution did not expose "
        "architecture as the next ready stage."
    )

store.delete(execution_id)

print("=" * 60)
print("Execution restore verified.")
print("=" * 60)
