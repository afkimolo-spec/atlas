from atlas.planning import (
    TaskPlanner,
    TaskStage,
)


planner = TaskPlanner()

plan = planner.plan(
    "Build Atlas autonomous engineering memory.",
    research=True,
    architecture=True,
    development=True,
    review=True,
    operations=True,
)

print("=" * 60)
print("ATLAS TASK PLANNER")
print("=" * 60)

print("Task   :", plan.task)
print("Steps  :", len(plan))
print("-" * 60)

for number, step in enumerate(
    plan.steps,
    start=1,
):
    dependencies = ", ".join(
        dependency.value
        for dependency in step.dependencies
    )

    print(
        f"{number}. "
        f"{step.stage.value}"
    )

    print(
        f"   Dependencies: "
        f"{dependencies or 'none'}"
    )

print("=" * 60)

assert len(plan) == 5

assert plan.stages == [
    TaskStage.RESEARCH,
    TaskStage.ARCHITECTURE,
    TaskStage.DEVELOPMENT,
    TaskStage.REVIEW,
    TaskStage.OPERATIONS,
]

assert plan.get(
    TaskStage.RESEARCH
) is not None

assert plan.get(
    TaskStage.ARCHITECTURE
).dependencies == [
    TaskStage.RESEARCH
]

assert plan.get(
    TaskStage.DEVELOPMENT
).dependencies == [
    TaskStage.ARCHITECTURE
]

assert plan.get(
    TaskStage.REVIEW
).dependencies == [
    TaskStage.DEVELOPMENT
]

assert plan.get(
    TaskStage.OPERATIONS
).dependencies == [
    TaskStage.REVIEW
]

print("Task planner verified.")
print("=" * 60)
