from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from atlas.agents.developer import DeveloperAgent
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
from atlas.core.telemetry import TelemetryRecorder
from atlas.planning import (
    PlanStep,
    TaskPlan,
    TaskStage,
)
from atlas.tools.command import CommandExecutor
from atlas.tools.files import FileManager
from atlas.tools.git import GitCheckpoint, GitManager
from atlas.workflows.build import BuildWorkflow
from atlas.workflows.test import TestWorkflow

if TYPE_CHECKING:
    from atlas.security.auth import Principal
    from atlas.security.service import SecurityService


@dataclass(slots=True)
class EngineeringAction:
    type: str
    detail: str
    succeeded: bool
    output: str = ""


@dataclass(slots=True)
class EngineeringResult:
    task: str
    succeeded: bool
    summary: str
    actions: list[EngineeringAction] = field(
        default_factory=list
    )
    verification_passed: bool = False
    rolled_back: bool = False
    attempts: int = 0
    execution_id: str | None = None
    trace_id: str | None = None


class EngineeringExecutor:
    """
    Autonomous engineering execution with durable execution state,
    recovery, feedback, telemetry, and workspace rollback.

    One engineering task is represented as one DEVELOPMENT execution
    stage. Action-level failures belong to the current stage attempt.
    Recovery advances the stage attempt through the existing Atlas
    execution/recovery infrastructure.
    """

    DEFAULT_VERIFICATION_COMMAND = "python -m pytest -q"

    def __init__(
        self,
        workspace: str | Path,
        *,
        security: SecurityService | None = None,
        principal: Principal | None = None,
        developer: DeveloperAgent | None = None,
        execution_store: ExecutionStore | None = None,
        recovery: RecoveryManager | None = None,
        feedback: FeedbackCollector | None = None,
        telemetry: TelemetryRecorder | None = None,
        max_steps: int = 30,
        max_action_failures: int = 3,
        command_timeout: float = 600.0,
        verification_command: str = DEFAULT_VERIFICATION_COMMAND,
    ) -> None:
        self.workspace = (
            Path(workspace)
            .expanduser()
            .resolve()
        )

        if not self.workspace.exists():
            raise FileNotFoundError(
                f"Engineering workspace does not exist: "
                f"{self.workspace}"
            )

        if not self.workspace.is_dir():
            raise NotADirectoryError(
                f"Engineering workspace is not a directory: "
                f"{self.workspace}"
            )

        if max_steps <= 0:
            raise ValueError(
                "max_steps must be greater than zero"
            )

        if max_action_failures <= 0:
            raise ValueError(
                "max_action_failures must be greater than zero"
            )

        if not verification_command.strip():
            raise ValueError(
                "verification_command cannot be empty"
            )

        self.security = security
        self.principal = principal
        self.developer = (
            developer
            or DeveloperAgent()
        )

        self.execution_store = (
            execution_store
            or ExecutionStore()
        )

        self.recovery = (
            recovery
            or RecoveryManager(
                policy=RecoveryPolicy(
                    max_attempts=3
                )
            )
        )

        self.feedback = (
            feedback
            or FeedbackCollector()
        )

        self.telemetry = (
            telemetry
            or TelemetryRecorder()
        )

        self.max_steps = max_steps
        self.max_action_failures = (
            max_action_failures
        )

        self.verification_command = (
            verification_command.strip()
        )

        self.files = FileManager(
            self.workspace,
            security=security,
            principal=principal,
        )

        self.command = CommandExecutor(
            self.workspace,
            default_timeout=command_timeout,
            security=security,
            principal=principal,
        )

        self.git = GitManager(
            self.workspace,
            default_timeout=command_timeout,
            security=security,
            principal=principal,
        )

        self.build = BuildWorkflow(
            self.workspace,
            security=security,
            principal=principal,
            timeout=command_timeout,
        )

        self.test = TestWorkflow(
            self.workspace,
            security=security,
            principal=principal,
            timeout=command_timeout,
        )

    def _task_plan(
        self,
        task: str,
    ) -> TaskPlan:
        return TaskPlan(
            task=task,
            steps=[
                PlanStep(
                    stage=TaskStage.DEVELOPMENT,
                    task=task,
                )
            ],
        )

    def execute(
        self,
        task: str,
        *,
        session_id: str,
        execution_id: str | None = None,
        trace_id: str | None = None,
    ) -> EngineeringResult:
        if not task.strip():
            raise ValueError(
                "Engineering task cannot be empty."
            )

        if not session_id.strip():
            raise ValueError(
                "session_id cannot be empty."
            )

        plan = self._task_plan(task)

        restored = (
            execution_id is not None
        )

        if execution_id is None:
            execution_id = (
                f"eng-{uuid.uuid4()}"
            )

            execution = ExecutionStateMachine(
                plan=plan
            )

            execution.execution_id = (
                execution_id
            )

            execution.start(
                reason="Engineering execution started"
            )

        else:
            execution = (
                self.execution_store.restore(
                    execution_id,
                    plan,
                )
            )

            if execution is None:
                raise KeyError(
                    f"Engineering execution not found: "
                    f"{execution_id}"
                )

            if execution.execution_id is None:
                execution.execution_id = (
                    execution_id
                )

            if execution.state == (
                ExecutionState.RETRYING
            ):
                execution.resume(
                    reason="Resume persisted engineering retry"
                )

            elif execution.state != (
                ExecutionState.RUNNING
            ):
                raise RuntimeError(
                    "Cannot resume engineering execution from state: "
                    f"{execution.state.value}"
                )

        trace_id = (
            trace_id
            or f"trace-{uuid.uuid4()}"
        )

        result = EngineeringResult(
            task=task,
            succeeded=False,
            summary="",
            execution_id=execution_id,
            trace_id=trace_id,
        )

        checkpoint: GitCheckpoint | None = None

        try:
            checkpoint = (
                self.git.create_checkpoint()
            )
        except Exception:
            checkpoint = None

        self.execution_store.save(
            execution_id,
            execution,
        )

        self.telemetry.start_trace(
            trace_id,
            execution_id,
            metadata={
                "task": task,
                "engineering": True,
                "resumed": restored,
            },
        )

        execution_span = self.telemetry.start_span(
            trace_id,
            execution_id,
            name="engineering.execute",
            kind="execution",
            agent=getattr(
                self.developer,
                "role",
                "developer",
            ),
            attributes={
                "engineering": True,
                "resumed": restored,
            },
        )

        self.feedback.start_execution(
            execution_id,
            stage_count=1,
            metadata={
                "task": task,
                "engineering": True,
                "resumed": restored,
            },
        )

        stage_failures = 0

        try:
            while True:
                stage = execution.get_stage(
                    TaskStage.DEVELOPMENT
                )

                result.attempts = (
                    stage.attempts
                )

                if stage.state == StageState.COMPLETED:
                    result.verification_passed = True
                    result.succeeded = True
                    result.summary = (
                        stage.result
                        or "Engineering execution completed."
                    )

                    break

                execution_stage = (
                    execution.start_stage(
                        TaskStage.DEVELOPMENT
                    )
                )

                result.attempts = (
                    execution_stage.attempts
                )

                self.execution_store.save(
                    execution_id,
                    execution,
                )

                feedback_id = (
                    self.feedback.start_stage(
                        execution_id,
                        TaskStage.DEVELOPMENT.value,
                        attempt=execution_stage.attempts,
                        metadata={
                            "agent": getattr(
                                self.developer,
                                "role",
                                "developer",
                            ),
                        },
                    )
                )

                stage_span = self.telemetry.start_span(
                    trace_id,
                    execution_id,
                    name="engineering.development",
                    kind="stage",
                    stage=TaskStage.DEVELOPMENT.value,
                    agent=getattr(
                        self.developer,
                        "role",
                        "developer",
                    ),
                    attributes={
                        "attempt": (
                            execution_stage.attempts
                        ),
                    },
                )

                state_lines = [
                    f"workspace={self.workspace}",
                    f"execution_id={execution_id}",
                    f"attempt={execution_stage.attempts}",
                    "verification_passed=false",
                    f"verification_command="
                    f"{self.verification_command}",
                ]

                consecutive_failures = 0
                verification_passed = False
                stage_complete = False
                last_error = ""

                for step_number in range(
                    1,
                    self.max_steps + 1,
                ):
                    try:
                        force_verification = (
                            not verification_passed
                            and any(
                                action.type == "finish"
                                and not action.succeeded
                                for action in result.actions
                            )
                        )

                        if force_verification:
                            action = {
                                "type": "run_command",
                                "command": (
                                    self.verification_command
                                ),
                            }
                        else:
                            action = (
                                self.developer.next_action(
                                    task,
                                    session_id=session_id,
                                    state="\n".join(
                                        state_lines
                                    ),
                                )
                            )

                        action_type = action["type"]

                        if action_type == "finish":
                            if not verification_passed:
                                raise RuntimeError(
                                    "Finish rejected: successful "
                                    "verification has not been recorded."
                                )

                            stage_complete = True

                            outcome = EngineeringAction(
                                type="finish",
                                detail=action["summary"],
                                succeeded=True,
                                output=action["summary"],
                            )

                            result.actions.append(
                                outcome
                            )

                            break

                        if action_type == "read_file":
                            outcome = self._read_file(
                                action
                            )

                        elif action_type == "write_file":
                            outcome = self._write_file(
                                action
                            )

                        elif action_type == "run_command":
                            outcome = self._run_command(
                                action
                            )

                        elif action_type == "git_diff":
                            outcome = self._git_diff()

                        else:
                            raise RuntimeError(
                                f"Unsupported developer action: "
                                f"{action_type!r}"
                            )

                        result.actions.append(
                            outcome
                        )

                        state_lines.extend(
                            [
                                f"step={step_number}",
                                f"action={outcome.type}",
                                f"action_succeeded="
                                f"{outcome.succeeded}",
                                f"action_detail="
                                f"{outcome.detail}",
                                f"action_output="
                                f"{outcome.output[-6000:]}",
                            ]
                        )

                        if not outcome.succeeded:
                            raise RuntimeError(
                                f"Engineering action failed: "
                                f"{outcome.detail}\n"
                                f"{outcome.output}"
                            )

                        if (
                            action_type
                            == "run_command"
                            and self._is_verification_command(
                                action["command"]
                            )
                        ):
                            verification_passed = True
                            result.verification_passed = True

                            state_lines.append(
                                "verification_passed=true"
                            )

                        consecutive_failures = 0

                    except Exception as exc:
                        last_error = (
                            f"{type(exc).__name__}: {exc}"
                        )

                        consecutive_failures += 1

                        result.actions.append(
                            EngineeringAction(
                                type="error",
                                detail=f"step {step_number}",
                                succeeded=False,
                                output=last_error,
                            )
                        )

                        state_lines.extend(
                            [
                                f"step={step_number}",
                                "action=error",
                                f"error={last_error}",
                            ]
                        )

                        if (
                            consecutive_failures
                            >= self.max_action_failures
                        ):
                            break

                if stage_complete:
                    execution.complete_stage(
                        TaskStage.DEVELOPMENT,
                        result.summary
                        or "Engineering work verified.",
                    )

                    self.feedback.complete_stage(
                        feedback_id,
                        metadata={
                            "verification_passed": True,
                            "attempt": (
                                execution_stage.attempts
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
                            "verification_passed": True,
                        },
                    )

                    self.execution_store.save(
                        execution_id,
                        execution,
                    )

                    continue

                execution_stage = (
                    execution.get_stage(
                        TaskStage.DEVELOPMENT
                    )
                )

                if execution_stage.state == (
                    StageState.RUNNING
                ):
                    execution.fail_stage(
                        TaskStage.DEVELOPMENT,
                        last_error
                        or "Engineering stage failed.",
                    )

                execution.fail(
                    reason="Engineering development stage failed"
                )

                self.feedback.fail_stage(
                    feedback_id,
                    error=(
                        last_error
                        or "Engineering stage failed."
                    ),
                    metadata={
                        "attempt": (
                            execution_stage.attempts
                        ),
                    },
                )

                self.telemetry.finish_span(
                    stage_span,
                    status="failed",
                    error=(
                        last_error
                        or "Engineering stage failed."
                    ),
                    attributes={
                        "attempt": (
                            execution_stage.attempts
                        ),
                    },
                )

                self.execution_store.save(
                    execution_id,
                    execution,
                )

                decision = self.recovery.recover(
                    execution,
                    TaskStage.DEVELOPMENT.value,
                    last_error
                    or "Engineering stage failed.",
                )

                if not decision.retryable:
                    result.summary = decision.reason

                    self.feedback.fail_execution(
                        execution_id,
                        completed_stages=0,
                        failed_stages=1,
                        error=decision.reason,
                    )

                    raise RuntimeError(
                        decision.reason
                    )

                stage_failures += 1

                self.feedback.retry(
                    execution_id
                )

                recovery_span = (
                    self.telemetry.start_span(
                        trace_id,
                        execution_id,
                        name="engineering.recovery",
                        kind="recovery",
                        stage=TaskStage.DEVELOPMENT.value,
                        attributes={
                            "attempt": decision.attempt,
                            "action": decision.action.value,
                        },
                    )
                )

                self.telemetry.finish_span(
                    recovery_span,
                    status="completed",
                    attributes={
                        "attempt": decision.attempt,
                        "action": decision.action.value,
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

            execution.complete(
                reason="Engineering task verified successfully"
            )

            self.execution_store.save(
                execution_id,
                execution,
            )

            self.feedback.complete_execution(
                execution_id,
                completed_stages=1,
                failed_stages=0,
                metadata={
                    "attempts": result.attempts,
                    "retries": stage_failures,
                },
            )

            self.telemetry.finish_span(
                execution_span,
                status="completed",
                attributes={
                    "attempts": result.attempts,
                    "retries": stage_failures,
                },
            )

            self.telemetry.finish_trace(
                trace_id,
                status="completed",
            )

            result.succeeded = True
            result.verification_passed = True
            result.summary = (
                result.summary
                or "Engineering execution completed successfully."
            )

            return result

        except Exception as exc:
            if execution.state in {
                ExecutionState.RUNNING,
                ExecutionState.PAUSED,
            }:
                execution.fail(
                    reason="Engineering execution failed"
                )

            self.execution_store.save(
                execution_id,
                execution,
            )

            self.feedback.fail_execution(
                execution_id,
                completed_stages=0,
                failed_stages=1,
                error=str(exc),
            )

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

            result.summary = str(exc)

            if checkpoint is not None:
                try:
                    self.git.rollback(
                        checkpoint
                    )
                    result.rolled_back = True
                except Exception as rollback_exc:
                    result.summary += (
                        f"\nRollback failed: {rollback_exc}"
                    )

            raise

    def _is_verification_command(
        self,
        command: str,
    ) -> bool:
        normalized = (
            command.strip()
            .lower()
        )

        configured = (
            self.verification_command
            .strip()
            .lower()
        )

        return (
            normalized == configured
            or normalized.startswith(
                f"{configured} "
            )
        )

    def _read_file(
        self,
        action: dict,
    ) -> EngineeringAction:
        path = action["path"]

        content = self.files.read_text(
            path
        )

        return EngineeringAction(
            type="read_file",
            detail=path,
            succeeded=True,
            output=content[-12000:],
        )

    def _write_file(
        self,
        action: dict,
    ) -> EngineeringAction:
        path = action["path"]

        written = self.files.write_text(
            path,
            action["content"],
        )

        return EngineeringAction(
            type="write_file",
            detail=str(
                written.relative_to(
                    self.workspace
                )
            ),
            succeeded=True,
            output="File written successfully.",
        )

    def _run_command(
        self,
        action: dict,
    ) -> EngineeringAction:
        command = action["command"]

        result = self.command.run(
            command
        )

        return EngineeringAction(
            type="run_command",
            detail=command,
            succeeded=result.succeeded,
            output=result.output[-12000:],
        )

    def _git_diff(
        self,
    ) -> EngineeringAction:
        result = self.git.diff()

        return EngineeringAction(
            type="git_diff",
            detail="git diff",
            succeeded=result.succeeded,
            output=result.output[-12000:],
        )
