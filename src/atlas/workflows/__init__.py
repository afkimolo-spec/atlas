from __future__ import annotations

from dataclasses import dataclass, field

from atlas.agents.architect import ArchitectAgent
from atlas.agents.developer import DeveloperAgent
from atlas.agents.operator import OperatorAgent
from atlas.agents.researcher import ResearcherAgent
from atlas.agents.reviewer import ReviewerAgent
from atlas.core.execution import (
    ExecutionState,
    ExecutionStateMachine,
    StageState,
)
from atlas.core.execution_store import ExecutionStore
from atlas.core.recovery import RecoveryManager, RecoveryPolicy
from atlas.core.execution_store import ExecutionStore
from atlas.core.session import Session
from atlas.planning import TaskPlan, TaskPlanner, TaskStage


@dataclass(slots=True)
class WorkflowResult:
    session_id: str
    status: str
    outputs: dict[str, str] = field(default_factory=dict)
    execution: ExecutionStateMachine | None = None

    @property
    def final(self) -> str:
        if not self.outputs:
            return ""

        return next(
            reversed(self.outputs.values())
        )

    @property
    def execution_state(self) -> str:
        if self.execution is None:
            return self.status

        return self.execution.state.value

    @property
    def succeeded(self) -> bool:
        return (
            self.execution is not None
            and self.execution.state
            == ExecutionState.COMPLETED
        )


class AtlasWorkflow:
    """
    Atlas multi-agent orchestration layer.

    Supports:
        - task planning
        - autonomous execution
        - dependency enforcement
        - execution persistence
        - crash recovery
        - stage result collection
    """

    def __init__(self) -> None:
        self.architect = ArchitectAgent()
        self.developer = DeveloperAgent()
        self.researcher = ResearcherAgent()
        self.reviewer = ReviewerAgent()
        self.operator = OperatorAgent()

        self.planner = TaskPlanner()
        self.execution_store = ExecutionStore()

        self.recovery = RecoveryManager(
            policy=RecoveryPolicy(max_attempts=3)
        )

    def _new_session(
        self,
        task: str,
    ) -> Session:
        session = Session()
        session.start(task)
        return session

    def _execute(
        self,
        agent,
        task: str,
        session: Session,
    ) -> str:
        if session.status != "running":
            raise RuntimeError(
                f"Session {session.id} is not running"
            )

        return agent.run(
            task,
            session_id=session.id,
        )

    def _agent_for_stage(
        self,
        stage: TaskStage,
    ):
        agents = {
            TaskStage.RESEARCH: self.researcher,
            TaskStage.ARCHITECTURE: self.architect,
            TaskStage.DEVELOPMENT: self.developer,
            TaskStage.REVIEW: self.reviewer,
            TaskStage.OPERATIONS: self.operator,
        }

        try:
            return agents[stage]
        except KeyError as exc:
            raise ValueError(
                f"No agent registered for stage: {stage}"
            ) from exc

    def _stage_task(
        self,
        stage: TaskStage,
        task: str,
    ) -> str:
        prompts = {
            TaskStage.RESEARCH: (
                "Research the following engineering task. "
                "Identify relevant technical constraints, "
                "risks, dependencies, and implementation "
                "considerations."
            ),
            TaskStage.ARCHITECTURE: (
                "Design the architecture for the following "
                "engineering task. Use the existing session "
                "history and completed research where available. "
                "Produce a concrete implementation design."
            ),
            TaskStage.DEVELOPMENT: (
                "Implement the engineering task based on "
                "the current session context, including "
                "research and architecture decisions. "
                "Identify concrete code and implementation "
                "changes required."
            ),
            TaskStage.REVIEW: (
                "Review the engineering work produced in "
                "this session. Identify correctness issues, "
                "architectural problems, missing requirements, "
                "regressions, and required corrections."
            ),
            TaskStage.OPERATIONS: (
                "Determine the operational execution plan "
                "for the engineering work in this session. "
                "Include validation, deployment, rollback, "
                "and operational verification requirements "
                "where applicable."
            ),
        }

        return (
            f"{prompts[stage]}\n\n"
            f"TASK:\n{task}"
        )

    def architecture(self, task: str) -> str:
        session = self._new_session(task)

        try:
            result = self._execute(
                self.architect,
                task,
                session,
            )
            session.finish()
            return result
        except Exception:
            session.fail()
            raise

    def development(self, task: str) -> str:
        session = self._new_session(task)

        try:
            result = self._execute(
                self.developer,
                task,
                session,
            )
            session.finish()
            return result
        except Exception:
            session.fail()
            raise

    def research(self, task: str) -> str:
        session = self._new_session(task)

        try:
            result = self._execute(
                self.researcher,
                task,
                session,
            )
            session.finish()
            return result
        except Exception:
            session.fail()
            raise

    def review(self, task: str) -> str:
        session = self._new_session(task)

        try:
            result = self._execute(
                self.reviewer,
                task,
                session,
            )
            session.finish()
            return result
        except Exception:
            session.fail()
            raise

    def operations(self, task: str) -> str:
        session = self._new_session(task)

        try:
            result = self._execute(
                self.operator,
                task,
                session,
            )
            session.finish()
            return result
        except Exception:
            session.fail()
            raise

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
        return self.planner.plan(
            task,
            research=research,
            architecture=architecture,
            development=development,
            review=review,
            operations=operations,
        )

    def execute_plan(
        self,
        plan: TaskPlan,
        *,
        execution_id: str | None = None,
    ) -> WorkflowResult:
        """
        Execute or resume a TaskPlan with durable recovery.

        Guarantees:

        - execution state is persisted
        - stage state is persisted
        - completed outputs survive restoration
        - failed stages are retried automatically
        - retry limits are enforced
        - execution can resume after process termination
        """

        if not plan.task.strip():
            raise ValueError(
                "Task plan cannot contain an empty task."
            )

        session = self._new_session(plan.task)

        if execution_id is None:
            execution = ExecutionStateMachine(
                plan=plan,
            )
            execution_id = session.id

        else:
            execution = self.execution_store.restore(
                execution_id,
                plan,
            )

            if execution is None:
                execution = ExecutionStateMachine(
                    plan=plan,
                )

        result = WorkflowResult(
            session_id=session.id,
            status=execution.state.value,
            execution=execution,
        )

        try:
            # ------------------------------------------------------
            # Restore / initialize execution state.
            # ------------------------------------------------------

            if execution.state == ExecutionState.CREATED:
                execution.start(
                    reason="Autonomous plan execution started"
                )

            elif execution.state == ExecutionState.RETRYING:
                execution.resume(
                    reason="Recovered retry resumed"
                )

            elif execution.state != ExecutionState.RUNNING:
                raise RuntimeError(
                    "Cannot execute/resume execution from state: "
                    f"{execution.state.value}"
                )

            self.execution_store.save(
                execution_id,
                execution,
            )

            # ------------------------------------------------------
            # Restore outputs from completed stages.
            # ------------------------------------------------------

            completed = 0

            for name, stage_execution in execution.stages.items():
                if stage_execution.state in {
                    StageState.COMPLETED,
                    StageState.SKIPPED,
                }:
                    completed += 1

                    if stage_execution.result:
                        result.outputs[name] = (
                            stage_execution.result
                        )

            # ------------------------------------------------------
            # Autonomous dependency-aware execution.
            # ------------------------------------------------------

            while completed < len(plan):

                stage = execution.next_ready_stage()

                if stage is None:
                    incomplete = [
                        name
                        for name, item in execution.stages.items()
                        if item.state not in {
                            StageState.COMPLETED,
                            StageState.SKIPPED,
                        }
                    ]

                    raise RuntimeError(
                        "No executable stage is available. "
                        f"Blocked stages: {', '.join(incomplete)}"
                    )

                stage_name = stage.name
                task_stage = TaskStage(stage_name)
                agent = self._agent_for_stage(task_stage)

                execution.start_stage(task_stage)

                self.execution_store.save(
                    execution_id,
                    execution,
                )

                try:
                    output = self._execute(
                        agent,
                        self._stage_task(
                            task_stage,
                            plan.task,
                        ),
                        session,
                    )

                    execution.complete_stage(
                        task_stage,
                        output,
                    )

                    result.outputs[stage_name] = output
                    completed += 1

                    self.execution_store.save(
                        execution_id,
                        execution,
                    )

                except Exception as exc:
                    # ----------------------------------------------
                    # Stage failure.
                    # ----------------------------------------------

                    stage_execution = execution.get_stage(
                        task_stage
                    )

                    if stage_execution.state == StageState.RUNNING:
                        execution.fail_stage(
                            task_stage,
                            str(exc),
                        )

                    execution.fail(
                        reason=(
                            f"Stage '{stage_name}' failed"
                        )
                    )

                    self.execution_store.save(
                        execution_id,
                        execution,
                    )

                    # ----------------------------------------------
                    # Recovery policy.
                    # ----------------------------------------------

                    decision = self.recovery.recover(
                        execution,
                        stage_name,
                        str(exc),
                    )

                    if not decision.retryable:
                        self.execution_store.save(
                            execution_id,
                            execution,
                        )

                        session.fail()
                        result.status = execution.state.value

                        raise RuntimeError(
                            decision.reason
                        ) from exc

                    # ----------------------------------------------
                    # Retry transition.
                    # ----------------------------------------------

                    self.execution_store.save(
                        execution_id,
                        execution,
                    )

                    execution.resume(
                        reason=decision.reason
                    )

                    self.execution_store.save(
                        execution_id,
                        execution,
                    )

                    # Retry the same stage.
                    continue

            # ------------------------------------------------------
            # All stages completed.
            # ------------------------------------------------------

            execution.complete(
                reason=(
                    "All planned stages completed "
                    "autonomously"
                )
            )

            self.execution_store.save(
                execution_id,
                execution,
            )

            session.finish()
            result.status = execution.state.value

            return result

        except Exception:
            if execution.state in {
                ExecutionState.RUNNING,
                ExecutionState.PAUSED,
            }:
                execution.fail(
                    reason="Autonomous plan execution failed"
                )

                self.execution_store.save(
                    execution_id,
                    execution,
                )

            if session.status == "running":
                session.fail()

            result.status = execution.state.value
            raise

    def resume_plan(
        self,
        plan: TaskPlan,
        execution_id: str,
    ) -> WorkflowResult:
        """
        Resume a persisted autonomous execution.
        """

        if not execution_id.strip():
            raise ValueError(
                "execution_id cannot be empty"
            )

        return self.execute_plan(
            plan,
            execution_id=execution_id,
        )

    def pipeline(
        self,
        task: str,
        *,
        research: bool = False,
        architecture: bool = True,
        development: bool = True,
        review: bool = True,
        operations: bool = True,
    ) -> WorkflowResult:
        plan = self.plan(
            task,
            research=research,
            architecture=architecture,
            development=development,
            review=review,
            operations=operations,
        )

        return self.execute_plan(plan)


Workflow = AtlasWorkflow
