from atlas.planning import TaskPlanner, TaskStage
from atlas.workflows import Workflow
from atlas.core.execution import (
    ExecutionState,
    StageState,
)


planner = TaskPlanner()
workflow = Workflow()

task = (
    "Reply with exactly: "
    "Atlas autonomous execution operational."
)

print("=" * 60)
print("ATLAS AUTONOMOUS EXECUTION")
print("=" * 60)

# ------------------------------------------------------------
# PLAN
# ------------------------------------------------------------

plan = planner.plan(
    task,
    research=True,
    architecture=True,
    development=True,
    review=True,
    operations=True,
)

print("Planned stages:", [
    stage.value
    for stage in plan.stages
])

assert plan.stages == [
    TaskStage.RESEARCH,
    TaskStage.ARCHITECTURE,
    TaskStage.DEVELOPMENT,
    TaskStage.REVIEW,
    TaskStage.OPERATIONS,
]

# ------------------------------------------------------------
# EXECUTE PLAN
# ------------------------------------------------------------

result = workflow.execute_plan(plan)

print("Session :", result.session_id)
print("Status  :", result.status)

assert result.session_id
assert result.status == ExecutionState.COMPLETED.value

assert result.execution is not None

assert (
    result.execution.state
    == ExecutionState.COMPLETED
)

# ------------------------------------------------------------
# VERIFY ALL STAGES
# ------------------------------------------------------------

expected_stages = [
    "research",
    "architecture",
    "development",
    "review",
    "operations",
]

print("-" * 60)

for stage_name in expected_stages:

    assert stage_name in result.outputs

    stage = result.execution.get_stage(stage_name)

    print(
        f"{stage_name:<15} "
        f"{stage.state.value:<10} "
        f"attempts={stage.attempts}"
    )

    assert stage.state == StageState.COMPLETED
    assert stage.attempts == 1

# ------------------------------------------------------------
# VERIFY OUTPUTS
# ------------------------------------------------------------

print("-" * 60)

for stage_name, output in result.outputs.items():

    assert output

    print(
        f"{stage_name:<15}: "
        f"{output}"
    )

# ------------------------------------------------------------
# VERIFY FINAL RESULT
# ------------------------------------------------------------

assert result.final

print("-" * 60)
print("Execution state :", result.execution_state)
print("Succeeded       :", result.succeeded)
print("Final           :", result.final)

assert result.execution_state == "completed"
assert result.succeeded is True

print("=" * 60)
print("AUTONOMOUS EXECUTION VERIFIED.")
print("=" * 60)
