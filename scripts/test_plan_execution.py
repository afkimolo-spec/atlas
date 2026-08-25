from atlas.core.execution import (
    ExecutionState,
    ExecutionStateMachine,
    StageDependencyError,
    StageState,
)
from atlas.planning import TaskPlanner, TaskStage


planner = TaskPlanner()

plan = planner.plan(
    "Validate dependency-aware execution.",
    research=True,
    architecture=True,
    development=True,
    review=True,
    operations=True,
)

machine = ExecutionStateMachine(plan=plan)

print("=" * 60)
print("ATLAS PLAN-AWARE EXECUTION")
print("=" * 60)

print("Initial :", machine.state.value)

machine.start()

print("Started :", machine.state.value)

assert machine.state == ExecutionState.RUNNING

# Architecture must be blocked until research completes.
try:
    machine.start_stage(TaskStage.ARCHITECTURE)
except StageDependencyError as exc:
    print("Blocked  :", exc)
else:
    raise AssertionError(
        "Architecture started before research completed."
    )

assert (
    machine.get_stage(TaskStage.ARCHITECTURE).state
    == StageState.PENDING
)

# Research
machine.start_stage(TaskStage.RESEARCH)
machine.complete_stage(
    TaskStage.RESEARCH,
    "Research complete.",
)

assert (
    machine.get_stage(TaskStage.RESEARCH).state
    == StageState.COMPLETED
)

# Architecture
machine.start_stage(TaskStage.ARCHITECTURE)
machine.complete_stage(
    TaskStage.ARCHITECTURE,
    "Architecture complete.",
)

# Development
machine.start_stage(TaskStage.DEVELOPMENT)
machine.complete_stage(
    TaskStage.DEVELOPMENT,
    "Development complete.",
)

# Review
machine.start_stage(TaskStage.REVIEW)
machine.complete_stage(
    TaskStage.REVIEW,
    "Review complete.",
)

# Operations
machine.start_stage(TaskStage.OPERATIONS)
machine.complete_stage(
    TaskStage.OPERATIONS,
    "Operations complete.",
)

machine.complete(
    reason="All plan dependencies satisfied.",
)

print("Final   :", machine.state.value)

assert machine.state == ExecutionState.COMPLETED

print("-" * 60)

for name, stage in machine.stages.items():
    print(
        f"{name:12} | "
        f"{stage.state.value:10} | "
        f"attempts={stage.attempts}"
    )

print("=" * 60)
print("Plan-aware execution verified.")
print("=" * 60)
