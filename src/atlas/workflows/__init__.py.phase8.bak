from __future__ import annotations

from dataclasses import dataclass, field
from uuid import uuid4

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
from atlas.core.feedback import FeedbackCollector
from atlas.core.recovery import (
    RecoveryManager,
    RecoveryPolicy,
)
from atlas.core.session import Session
from atlas.core.telemetry import TelemetryRecorder
from atlas.planning import (
    TaskPlan,
    TaskPlanner,
    TaskStage,
)


@dataclass(slots=True)
class WorkflowResult:
    session_id: str
    status: str
    outputs: dict[str, str] = field(
        default_factory=dict
    )
    execution: ExecutionStateMachine | None = None
    trace_id: str | None = None

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
    Atlas autonomous workflow engine.

    Integrates:
        planning
        dependency-aware execution
        persistence
        recovery
        feedback
        tracing
        observability
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
            policy=RecoveryPolicy(
                max_attempts=3
            )
        )

        self.feedback = FeedbackCollector()
        self.telemetry = TelemetryRecorder()

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
        if not plan.task.strip():
            raise ValueError(
                "Task plan cannot contain an empty task."
            )

        session = self._new_session(
            plan.task
        )

        restored = execution_id is not None

        if execution_id is None:
            execution = ExecutionStateMachine(
                plan=plan
            )
            execution_id = session.id
        else:
            execution = self.execution_store.restore(
                execution_id,
                plan,
            )

            if execution is None:
                raise KeyError(
                    f"Execution not found: {execution_id}"
                )

        execution.execution_id = execution_id

        trace_id = (
            f"trace-{uuid4()}"
        )

        result = WorkflowResult(
            session_id=session.id,
            status=execution.state.value,
            execution=execution,
            trace_id=trace_id,
        )

        self.telemetry.start_trace(
            trace_id,
            execution_id,
            metadata={
                "task": plan.task,
                "resumed": restored,
                "stages": [
                    stage.value
                    for stage in plan.stages
                ],
            },
        )

        self.feedback.start_execution(
            execution_id,
            stage_count=len(plan),
            metadata={
                "task": plan.task,
                "resumed": restored,
            },
        )

        execution_span = self.telemetry.start_span(
            trace_id,
            execution_id,
            name="workflow.execute",
            kind="execution",
            attributes={
                "resumed": restored,
                "stage_count": len(plan),
            },
        )

        try:
            if execution.state == ExecutionState.CREATED:
                execution.start(
                    reason=(
                        "Autonomous plan execution started"
                    )
                )

            elif execution.state == ExecutionState.RETRYING:
                execution.resume(
                    reason=(
                        "Persisted retry execution resumed"
                    )
                )

            elif execution.state != ExecutionState.RUNNING:
                raise RuntimeError(
                    "Cannot execute/resume execution "
                    f"from state: {execution.state.value}"
                )

            self.execution_store.save(
                execution_id,
                execution,
            )

            completed = sum(
                1
                for item in execution.stages.values()
                if item.state in {
                    StageState.COMPLETED,
                    StageState.SKIPPED,
                }
            )

            for name, item in execution.stages.items():
                if (
                    item.state
                    in {
                        StageState.COMPLETED,
                        StageState.SKIPPED,
                    }
                    and item.result
                ):
                    result.outputs[name] = (
                        item.result
                    )

            while completed < len(plan):
                stage = execution.next_ready_stage()

                if stage is None:
                    incomplete = [
                        name
                        for name, item
                        in execution.stages.items()
                        if item.state not in {
                            StageState.COMPLETED,
                            StageState.SKIPPED,
                        }
                    ]

                    raise RuntimeError(
                        "No executable stage is available. "
                        f"Blocked stages: "
                        f"{', '.join(incomplete)}"
                    )

                stage_name = stage.name
                task_stage = TaskStage(
                    stage_name
                )
                agent = self._agent_for_stage(
                    task_stage
                )

                execution_stage = (
                    execution.start_stage(
                        task_stage
                    )
                )

                feedback_id = (
                    self.feedback.start_stage(
                        execution_id,
                        stage_name,
                        attempt=execution_stage.attempts,
                        metadata={
                            "agent": getattr(
                                agent,
                                "role",
                                agent.__class__.__name__,
                            ),
                        },
                    )
                )

                stage_span = self.telemetry.start_span(
                    trace_id,
                    execution_id,
                    name=f"stage.{stage_name}",
                    kind="stage",
                    stage=stage_name,
                    agent=getattr(
                        agent,
                        "role",
                        agent.__class__.__name__,
                    ),
                    attributes={
                        "attempt": execution_stage.attempts,
                    },
                )

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

                    self.feedback.complete_stage(
                        feedback_id,
                        metadata={
                            "agent": getattr(
                                agent,
                                "role",
                                agent.__class__.__name__,
                            ),
                        },
                    )

                    self.telemetry.finish_span(
                        stage_span,
                        status="completed",
                        attributes={
                            "attempt": (
                                execution_stage.attempts
                            ),
                        },
                    )

                    result.outputs[
                        stage_name
                    ] = output

                    completed += 1

                    self.execution_store.save(
                        execution_id,
                        execution,
                    )

                except Exception as exc:
                    error = str(exc)

                    self.feedback.fail_stage(
                        feedback_id,
                        error=error,
                        metadata={
                            "agent": getattr(
                                agent,
                                "role",
                                agent.__class__.__name__,
                            ),
                        },
                    )

                    self.telemetry.finish_span(
                        stage_span,
                        status="failed",
                        error=error,
                        attributes={
                            "attempt": (
                                execution_stage.attempts
                            ),
                        },
                    )

                    if (
                        execution.get_stage(
                            task_stage
                        ).state
                        == StageState.RUNNING
                    ):
                        execution.fail_stage(
                            task_stage,
                            error,
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

                    decision = self.recovery.recover(
                        execution,
                        stage_name,
                        error,
                    )

                    if decision.retryable:
                        self.feedback.retry(
                            execution_id
                        )

                        self.telemetry.start_span(
                            trace_id,
                            execution_id,
                            name="recovery.retry",
                            kind="recovery",
                            stage=stage_name,
                            attributes={
                                "attempt": (
                                    execution_stage.attempts
                                ),
                                "reason": decision.reason,
                            },
                        )

                        execution.resume(
                            reason=decision.reason
                        )

                        self.execution_store.save(
                            execution_id,
                            execution,
                        )

                        continue

                    self.feedback.fail_execution(
                        execution_id,
                        completed_stages=completed,
                        failed_stages=1,
                        error=decision.reason,
                    )

                    session.fail()
                    result.status = (
                        execution.state.value
                    )

                    raise RuntimeError(
                        decision.reason
                    ) from exc

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

            self.feedback.complete_execution(
                execution_id,
                completed_stages=completed,
                failed_stages=0,
            )

            self.telemetry.finish_span(
                execution_span,
                status="completed",
            )

            self.telemetry.finish_trace(
                trace_id,
                status="completed",
            )

            session.finish()

            result.status = execution.state.value

            return result

        except Exception as exc:
            self.telemetry.finish_span(
                execution_span,
                status="failed",
                error=str(exc),
            )

            self.telemetry.finish_trace(
                trace_id,
                status="failed",
                error=str(exc),
            )

            if execution.state in {
                ExecutionState.RUNNING,
                ExecutionState.PAUSED,
            }:
                execution.fail(
                    reason=(
                        "Autonomous plan execution failed"
                    )
                )

                self.execution_store.save(
                    execution_id,
                    execution,
                )

            self.feedback.fail_execution(
                execution_id,
                completed_stages=(
                    sum(
                        1
                        for item
                        in execution.stages.values()
                        if item.state
                        == StageState.COMPLETED
                    )
                ),
                failed_stages=(
                    max(
                        1,
                        sum(
                            1
                            for item
                            in execution.stages.values()
                            if item.state
                            == StageState.FAILED
                        ),
                    )
                ),
                error=str(exc),
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
