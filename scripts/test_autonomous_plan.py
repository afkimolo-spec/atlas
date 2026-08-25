from atlas.planning import TaskStage
from atlas.workflows import Workflow


workflow = Workflow()

plan = workflow.plan(
    "Reply with exactly: Autonomous plan execution operational.",
    research=True,
    architecture=True,
    development=True,
    review=True,
    operations=True,
)

print("=" * 60)
print("ATLAS AUTONOMOUS PLAN EXECUTION")
print("=" * 60)

print("Plan stages:")

for stage in plan.stages:
    print(" -", stage.value)

result = workflow.execute_plan(plan)

print("-" * 60)

print("Session :", result.session_id)
print("Status  :", result.status)
print("State   :", result.execution_state)
print("Success :", result.succeeded)

print("-" * 60)

for stage, output in result.outputs.items():
    print(
        f"Stage   : {stage}"
    )
    print(
        f"Result  : {output}"
    )

print("-" * 60)

assert result.session_id
assert result.status == "completed"
assert result.execution_state == "completed"
assert result.succeeded

assert list(result.outputs) == [
    "research",
    "architecture",
    "development",
    "review",
    "operations",
]

assert all(
    result.execution.get_stage(stage).state.value
    == "completed"
    for stage in result.outputs
)

assert all(
    result.execution.get_stage(stage).attempts == 1
    for stage in result.outputs
)

print("=" * 60)
print("Autonomous plan execution verified.")
print("=" * 60)
