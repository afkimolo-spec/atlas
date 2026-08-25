from __future__ import annotations

from atlas.planning.plan import (
    PlanStep,
    TaskPlan,
    TaskStage,
)


class TaskPlanner:
    """
    Deterministic Atlas task planner.

    This first implementation establishes a reliable planning
    contract. Autonomous model-driven planning can be introduced
    later without changing the TaskPlan representation.
    """

    def plan(
        self,
        task: str,
        *,
        research: bool = False,
        architecture: bool = True,
        development: bool = True,
        review: bool = True,
        operations: bool = True,
    ) -> TaskPlan:
        """
        Build an ordered execution plan.

        Default engineering lifecycle:

            architecture
                ↓
            development
                ↓
            review
                ↓
            operations

        Research can be enabled explicitly and becomes the first
        stage.
        """

        if not task.strip():
            raise ValueError(
                "Planning task cannot be empty"
            )

        if not any(
            (
                research,
                architecture,
                development,
                review,
                operations,
            )
        ):
            raise ValueError(
                "At least one planning stage must be enabled"
            )

        steps: list[PlanStep] = []

        if research:
            steps.append(
                PlanStep(
                    stage=TaskStage.RESEARCH,
                    task=(
                        "Research the following engineering task. "
                        "Identify relevant technical constraints, "
                        "risks, dependencies, and implementation "
                        "considerations.\n\n"
                        f"TASK:\n{task}"
                    ),
                )
            )

        if architecture:
            dependencies: list[TaskStage] = []

            if research:
                dependencies.append(
                    TaskStage.RESEARCH
                )

            steps.append(
                PlanStep(
                    stage=TaskStage.ARCHITECTURE,
                    task=(
                        "Design the architecture for the following "
                        "engineering task. Use available research "
                        "and persistent session context where "
                        "applicable. Produce a concrete "
                        "implementation design.\n\n"
                        f"TASK:\n{task}"
                    ),
                    dependencies=dependencies,
                )
            )

        if development:
            dependencies = []

            if architecture:
                dependencies.append(
                    TaskStage.ARCHITECTURE
                )
            elif research:
                dependencies.append(
                    TaskStage.RESEARCH
                )

            steps.append(
                PlanStep(
                    stage=TaskStage.DEVELOPMENT,
                    task=(
                        "Implement the following engineering task "
                        "using the available session context, "
                        "research, and architecture decisions.\n\n"
                        f"TASK:\n{task}"
                    ),
                    dependencies=dependencies,
                )
            )

        if review:
            dependencies = []

            if development:
                dependencies.append(
                    TaskStage.DEVELOPMENT
                )
            elif architecture:
                dependencies.append(
                    TaskStage.ARCHITECTURE
                )
            elif research:
                dependencies.append(
                    TaskStage.RESEARCH
                )

            steps.append(
                PlanStep(
                    stage=TaskStage.REVIEW,
                    task=(
                        "Review the engineering work associated "
                        "with the following task. Identify "
                        "correctness issues, architectural "
                        "problems, missing requirements, "
                        "regressions, and required corrections.\n\n"
                        f"TASK:\n{task}"
                    ),
                    dependencies=dependencies,
                )
            )

        if operations:
            dependencies = []

            if review:
                dependencies.append(
                    TaskStage.REVIEW
                )
            elif development:
                dependencies.append(
                    TaskStage.DEVELOPMENT
                )
            elif architecture:
                dependencies.append(
                    TaskStage.ARCHITECTURE
                )
            elif research:
                dependencies.append(
                    TaskStage.RESEARCH
                )

            steps.append(
                PlanStep(
                    stage=TaskStage.OPERATIONS,
                    task=(
                        "Determine the operational execution plan "
                        "for the following engineering task. "
                        "Include validation, deployment, "
                        "rollback, and operational verification "
                        "requirements where applicable.\n\n"
                        f"TASK:\n{task}"
                    ),
                    dependencies=dependencies,
                )
            )

        return TaskPlan(
            task=task,
            steps=steps,
        )
