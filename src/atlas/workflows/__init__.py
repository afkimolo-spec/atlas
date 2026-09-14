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
)
from atlas.core.execution_store import ExecutionStore
from atlas.core.recovery import RecoveryManager, RecoveryPolicy
from atlas.core.session import Session
from atlas.planning import TaskPlan, TaskPlanner
from atlas.runtime.plan import (
    AutonomousPlanExecutor,
    AutonomousPlanResult,
)


@dataclass(slots=True)
class WorkflowResult:
    """
    Backward-compatible public workflow result.
    """

    session_id: str
    status: str
    outputs: dict[str, str] = field(
        default_factory=dict
    )
    execution: ExecutionStateMachine | None = None
    runtime: AutonomousPlanResult | None = None

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
    Atlas workflow facade.

    Legacy single-stage methods remain available.

    Plan execution is delegated to AutonomousPlanExecutor, which is
    the durable autonomous execution kernel.
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
                max_attempts=3,
            )
        )

        self.autonomous = AutonomousPlanExecutor(
            researcher=self.researcher,
            architect=self.architect,
            reviewer=self.reviewer,
            operator=self.operator,
            execution_store=self.execution_store,
            recovery=self.recovery,
        )

    # ------------------------------------------------------------------
    # LEGACY SINGLE-STAGE API
    # ------------------------------------------------------------------

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

    def architecture(
        self,
        task: str,
    ) -> str:
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

    def development(
        self,
        task: str,
    ) -> str:
        session = self._new_session(task)

        try:
            runtime = self.autonomous.autonomous_runtime.execute(
                task,
                session_id=session.id,
            )

            if runtime.status != "completed":
                raise RuntimeError(
                    runtime.last_error
                    or (
                        "Autonomous engineering execution "
                        "did not complete."
                    )
                )

            session.finish()

            return (
                self.autonomous._development_summary(
                    runtime
                )
            )

        except Exception:
            session.fail()
            raise

    def research(
        self,
        task: str,
    ) -> str:
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

    def review(
        self,
        task: str,
    ) -> str:
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

    def operations(
        self,
        task: str,
    ) -> str:
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

    # ------------------------------------------------------------------
    # PLAN API
    # ------------------------------------------------------------------

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
        runtime_result = self.autonomous.execute(
            plan,
            execution_id=execution_id,
            resume=execution_id is not None,
        )

        return WorkflowResult(
            session_id=runtime_result.session_id,
            status=runtime_result.status,
            outputs=dict(
                runtime_result.outputs
            ),
            execution=runtime_result.execution,
            runtime=runtime_result,
        )

    def resume_plan(
        self,
        plan: TaskPlan,
        execution_id: str,
    ) -> WorkflowResult:
        runtime_result = self.autonomous.resume(
            plan,
            execution_id,
        )

        return WorkflowResult(
            session_id=runtime_result.session_id,
            status=runtime_result.status,
            outputs=dict(
                runtime_result.outputs
            ),
            execution=runtime_result.execution,
            runtime=runtime_result,
        )


Workflow = AtlasWorkflow
