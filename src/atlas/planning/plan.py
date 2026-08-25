from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class TaskStage(str, Enum):
    """
    Supported Atlas execution stages.

    The order represents the normal engineering lifecycle.
    """

    RESEARCH = "research"
    ARCHITECTURE = "architecture"
    DEVELOPMENT = "development"
    REVIEW = "review"
    OPERATIONS = "operations"


@dataclass(slots=True)
class PlanStep:
    """
    One executable step in an Atlas task plan.
    """

    stage: TaskStage
    task: str
    dependencies: list[TaskStage] = field(
        default_factory=list
    )

    def __post_init__(self) -> None:

        if not self.task.strip():
            raise ValueError(
                "Plan step task cannot be empty"
            )

        seen: set[TaskStage] = set()

        for dependency in self.dependencies:

            if dependency == self.stage:
                raise ValueError(
                    f"Plan step '{self.stage.value}' "
                    "cannot depend on itself"
                )

            if dependency in seen:
                raise ValueError(
                    f"Duplicate dependency "
                    f"'{dependency.value}' "
                    f"for stage '{self.stage.value}'"
                )

            seen.add(dependency)


@dataclass(slots=True)
class TaskPlan:
    """
    Immutable conceptual representation of an Atlas task plan.

    The plan contains the original user task and the ordered
    execution steps selected for that task.
    """

    task: str
    steps: list[PlanStep] = field(
        default_factory=list
    )

    def __post_init__(self) -> None:

        if not self.task.strip():
            raise ValueError(
                "Task plan task cannot be empty"
            )

        self.validate()

    @property
    def stages(self) -> list[TaskStage]:
        """
        Return the stages in execution order.
        """

        return [
            step.stage
            for step in self.steps
        ]

    def has_stage(
        self,
        stage: TaskStage,
    ) -> bool:
        """
        Determine whether the plan contains a stage.
        """

        return stage in self.stages

    def get(
        self,
        stage: TaskStage,
    ) -> PlanStep | None:
        """
        Return the step for a stage.
        """

        for step in self.steps:
            if step.stage == stage:
                return step

        return None

    def validate(self) -> None:
        """
        Validate ordering, uniqueness, and dependencies.
        """

        seen: set[TaskStage] = set()

        for step in self.steps:

            if step.stage in seen:
                raise ValueError(
                    f"Duplicate plan stage: "
                    f"{step.stage.value}"
                )

            for dependency in step.dependencies:

                if dependency not in seen:
                    raise ValueError(
                        f"Stage '{step.stage.value}' "
                        f"depends on '{dependency.value}', "
                        "which has not been scheduled yet"
                    )

            seen.add(step.stage)

    def __len__(self) -> int:
        return len(self.steps)
