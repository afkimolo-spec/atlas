from atlas.planning import TaskStage
from atlas.workflows import Workflow


workflow = Workflow()

plan = workflow.planner.plan(
    "Reply with exactly: Planner workflow operational.",
    research=False,
    architecture=True,
    development=False,
    review=False,
    operations=False,
)

print("=" * 60)
print("PLANNER → WORKFLOW INTEGRATION")
print("=" * 60)

print("Stages :", [
    stage.value
    for stage in plan.stages
])

result = workflow.execute_plan(plan)

print("Session:", result.session_id)
print("Status :", result.status)

print("-" * 60)

for stage, output in result.outputs.items():

    print(
        f"Stage  : {stage}"
    )

    print(
        f"Result : {output}"
    )

print("=" * 60)

assert plan.stages == [
    TaskStage.ARCHITECTURE
]

assert result.session_id

assert result.status == "completed"

assert "architecture" in result.outputs

assert (
    "Planner workflow operational."
    in result.outputs["architecture"]
)

print("Planner/workflow integration verified.")
print("=" * 60)
