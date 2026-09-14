from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path

from atlas.agents.developer import DeveloperAgent
from atlas.core.execution_store import ExecutionStore
from atlas.core.feedback import FeedbackCollector
from atlas.core.recovery import RecoveryManager, RecoveryPolicy
from atlas.core.telemetry import TelemetryRecorder, TelemetryStore
from atlas.workflows.engineering import EngineeringExecutor


class FailureInjectingDeveloper(DeveloperAgent):
    """
    Production-compatible DeveloperAgent test double.

    The first call intentionally executes the defective test suite.
    Every subsequent call uses the real DeveloperAgent implementation.
    """

    def __init__(self) -> None:
        super().__init__()
        self.calls = 0

    def next_action(
        self,
        task: str,
        *,
        session_id: str,
        state: str,
    ) -> dict:
        self.calls += 1

        if self.calls == 1:
            return {
                "type": "run_command",
                "command": "python -m pytest -q",
            }

        return super().next_action(
            task,
            session_id=session_id,
            state=state,
        )


def run(
    command: str,
    cwd: Path,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=cwd,
        shell=True,
        text=True,
        capture_output=True,
        check=False,
    )


def main() -> None:
    root = Path(
        tempfile.mkdtemp(
            prefix="atlas-phase8-failure-recovery-"
        )
    )

    try:
        workspace = root / "workspace"
        workspace.mkdir(parents=True)

        calculator = workspace / "calculator.py"
        tests = workspace / "test_calculator.py"

        calculator.write_text(
            "def add(a, b):\n"
            "    return a - b\n",
            encoding="utf-8",
        )

        tests.write_text(
            "from calculator import add\n\n"
            "def test_add():\n"
            "    assert add(2, 3) == 5\n",
            encoding="utf-8",
        )

        result = run(
            "git init",
            workspace,
        )
        assert result.returncode == 0, result.stderr

        result = run(
            'git config user.email "atlas@test.local"',
            workspace,
        )
        assert result.returncode == 0, result.stderr

        result = run(
            'git config user.name "Atlas Test"',
            workspace,
        )
        assert result.returncode == 0, result.stderr

        result = run(
            "git add .",
            workspace,
        )
        assert result.returncode == 0, result.stderr

        result = run(
            'git commit -m "initial defective workspace"',
            workspace,
        )
        assert result.returncode == 0, result.stderr

        database = root / "atlas.db"

        execution_store = ExecutionStore(
            database
        )

        recovery = RecoveryManager(
            policy=RecoveryPolicy(
                max_attempts=3
            )
        )

        feedback = FeedbackCollector(
            database
        )

        telemetry = TelemetryRecorder(
            TelemetryStore(database)
        )

        developer = FailureInjectingDeveloper()

        executor = EngineeringExecutor(
            workspace,
            developer=developer,
            execution_store=execution_store,
            recovery=recovery,
            feedback=feedback,
            telemetry=telemetry,
            max_steps=20,
            max_action_failures=1,
            command_timeout=30,
            verification_command="python -m pytest -q",
        )

        task = (
            "Fix calculator.py so add(a, b) returns "
            "the arithmetic sum. Run the test suite."
        )

        result = executor.execute(
            task,
            session_id="phase8-failure-recovery",
        )

        execution_id = result.execution_id

        assert execution_id is not None
        assert result.succeeded
        assert result.verification_passed
        assert result.attempts >= 2

        plan = executor._task_plan(task)

        restored = execution_store.restore(
            execution_id,
            plan,
        )

        assert restored is not None
        assert restored.state.value == "completed"

        development = restored.get_stage(
            "development"
        )

        assert development.state.value == "completed"
        assert development.attempts >= 2

        execution_feedback = feedback.store.execution(
            execution_id
        )

        assert execution_feedback is not None
        assert execution_feedback["status"] == "completed"
        assert execution_feedback["retries"] >= 1

        stage_feedback = feedback.store.stages(
            execution_id
        )

        assert any(
            item["outcome"] == "failed"
            for item in stage_feedback
        )

        assert any(
            item["outcome"] == "completed"
            for item in stage_feedback
        )

        trace = telemetry.store.trace(
            result.trace_id
        )

        assert trace is not None
        assert trace["status"] == "completed"

        spans = telemetry.store.spans(
            result.trace_id
        )

        assert any(
            span["kind"] == "recovery"
            for span in spans
        )

        assert any(
            span["status"] == "failed"
            for span in spans
        )

        final_test = run(
            "python -m pytest -q",
            workspace,
        )

        assert final_test.returncode == 0, (
            final_test.stdout
            + final_test.stderr
        )

        final_source = calculator.read_text(
            encoding="utf-8"
        ).strip()

        assert final_source == (
            "def add(a, b):\n"
            "    return a + b"
        )

        print("Developer contract        : verified")
        print("Failure/retry              : verified")
        print("Execution persistence      : verified")
        print("Execution restoration      : verified")
        print("Feedback persistence       : verified")
        print("Failure telemetry          : verified")
        print("Recovery telemetry         : verified")
        print("Final verification         : verified")
        print(f"Attempts                   : {result.attempts}")
        print("PHASE 8 FAILURE RECOVERY VERIFIED")

    finally:
        shutil.rmtree(
            root,
            ignore_errors=True,
        )


if __name__ == "__main__":
    main()
