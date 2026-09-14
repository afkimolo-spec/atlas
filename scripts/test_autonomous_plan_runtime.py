from __future__ import annotations

import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

from atlas.planning import TaskPlanner
from atlas.runtime import (
    AutonomousPlanExecutor,
    AutonomousRuntime,
)


class DeterministicDeveloper:
    """
    Deterministic developer used only for runtime integration tests.
    """

    def __init__(self) -> None:
        self.calls = 0

    def next_action(
        self,
        task: str,
        *,
        session_id: str,
        state: str,
    ) -> dict[str, Any]:
        self.calls += 1

        actions = [
            {
                "type": "read_file",
                "path": "calculator.py",
            },
            {
                "type": "write_file",
                "path": "calculator.py",
                "content": (
                    "def add(a, b):\n"
                    "    return a + b\n"
                ),
            },
            {
                "type": "run_command",
                "command": "python -m pytest -q",
            },
            {
                "type": "finish",
                "summary": "Tests passed and implementation verified.",
            },
        ]

        return actions[self.calls - 1]


print("=" * 70)
print("ATLAS DURABLE AUTONOMOUS PLAN RUNTIME")
print("=" * 70)

with TemporaryDirectory() as directory:
    root = Path(directory)

    (root / "calculator.py").write_text(
        "def add(a, b):\n"
        "    return a - b\n",
        encoding="utf-8",
    )

    (root / "test_calculator.py").write_text(
        "from calculator import add\n\n"
        "def test_add():\n"
        "    assert add(2, 3) == 5\n",
        encoding="utf-8",
    )

    subprocess.run(
        [
            "git",
            "init",
        ],
        cwd=root,
        capture_output=True,
        text=True,
        check=True,
    )

    subprocess.run(
        [
            "git",
            "config",
            "user.email",
            "atlas@test.local",
        ],
        cwd=root,
        capture_output=True,
        text=True,
        check=True,
    )

    subprocess.run(
        [
            "git",
            "config",
            "user.name",
            "Atlas Test",
        ],
        cwd=root,
        capture_output=True,
        text=True,
        check=True,
    )

    subprocess.run(
        [
            "git",
            "add",
            ".",
        ],
        cwd=root,
        capture_output=True,
        text=True,
        check=True,
    )

    subprocess.run(
        [
            "git",
            "commit",
            "-m",
            "baseline",
        ],
        cwd=root,
        capture_output=True,
        text=True,
        check=True,
    )

    baseline = subprocess.run(
        [
            "python",
            "-m",
            "pytest",
            "-q",
        ],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )

    assert baseline.returncode != 0

    developer = DeterministicDeveloper()

    runtime = AutonomousRuntime(
        workspace=root,
        developer=developer,
        max_steps=8,
    )

    planner = TaskPlanner()

    plan = planner.plan(
        "Fix calculator.add so addition works correctly.",
        research=False,
        architecture=False,
        development=True,
        review=False,
        operations=False,
    )

    executor = AutonomousPlanExecutor(
        workspace=root,
        autonomous_runtime=runtime,
    )

    result = executor.execute(plan)

    assert result.succeeded
    assert result.execution is not None
    assert result.execution.state.value == "completed"
    assert result.autonomous_runtime is not None
    assert result.autonomous_runtime.status == "completed"
    assert result.autonomous_runtime.verification_passed
    assert developer.calls == 4

    implementation = (
        root / "calculator.py"
    ).read_text(
        encoding="utf-8"
    )

    assert (
        "return a + b"
        in implementation
    )

    final = subprocess.run(
        [
            "python",
            "-m",
            "pytest",
            "-q",
        ],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )

    assert final.returncode == 0, (
        final.stdout
        + "\n"
        + final.stderr
    )

    print("Plan construction       : PASS")
    print("Execution state machine : PASS")
    print("Autonomous action loop  : PASS")
    print("File read               : PASS")
    print("File write              : PASS")
    print("Test execution          : PASS")
    print("Independent verification: PASS")
    print("Finish gate             : PASS")
    print("Final pytest            : PASS")

print("=" * 70)
print("DURABLE AUTONOMOUS PLAN RUNTIME: VERIFIED")
print("=" * 70)
