from __future__ import annotations

import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory

from atlas.agents.architect import ArchitectAgent
from atlas.agents.operator import OperatorAgent
from atlas.agents.researcher import ResearcherAgent
from atlas.agents.reviewer import ReviewerAgent
from atlas.planning import TaskPlanner
from atlas.runtime import AutonomousPlanExecutor, AutonomousRuntime


class StubAgent:
    def __init__(self, role: str) -> None:
        self.role = role

    def run(
        self,
        task: str,
        *,
        session_id: str,
    ) -> str:
        return f"{self.role} stage completed."


class DeterministicDeveloper:
    def __init__(self) -> None:
        self.calls = 0

    def next_action(
        self,
        task: str,
        *,
        session_id: str,
        state: str,
    ) -> dict[str, str]:
        self.calls += 1

        if self.calls == 1:
            return {
                "type": "read_file",
                "path": "calculator.py",
            }

        if self.calls == 2:
            return {
                "type": "write_file",
                "path": "calculator.py",
                "content": (
                    "def add(a, b):\n"
                    "    return a + b\n"
                ),
            }

        if self.calls == 3:
            return {
                "type": "run_command",
                "command": "python -m pytest -q",
            }

        return {
            "type": "finish",
            "summary": "Implementation verified.",
        }


print("=" * 70)
print("ATLAS AUTONOMOUS PLAN KERNEL INTEGRATION")
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
        ["git", "init"],
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
        ["git", "add", "."],
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
        "Fix calculator.add so it performs addition.",
        research=True,
        architecture=True,
        development=True,
        review=True,
        operations=True,
    )

    executor = AutonomousPlanExecutor(
        workspace=root,
        researcher=StubAgent("research"),
        architect=StubAgent("architecture"),
        reviewer=StubAgent("review"),
        operator=StubAgent("operations"),
        autonomous_runtime=runtime,
    )

    result = executor.execute(plan)

    assert result.succeeded
    assert result.execution is not None
    assert result.execution.state.value == "completed"

    expected_stages = [
        "research",
        "architecture",
        "development",
        "review",
        "operations",
    ]

    assert list(
        result.outputs.keys()
    ) == expected_stages

    assert result.development_runtime is not None
    assert (
        result.development_runtime.status
        == "completed"
    )

    assert (
        result.development_runtime.verification_passed
    )

    implementation = (
        root / "calculator.py"
    ).read_text(
        encoding="utf-8"
    )

    assert "return a + b" in implementation

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

    print("Five-stage plan            : PASS")
    print("Dependency execution       : PASS")
    print("Durable execution state    : PASS")
    print("Research stage             : PASS")
    print("Architecture stage         : PASS")
    print("Autonomous development    : PASS")
    print("Independent verification   : PASS")
    print("Review stage               : PASS")
    print("Operations stage           : PASS")
    print("Final repository tests     : PASS")

print("=" * 70)
print("AUTONOMOUS PLAN KERNEL INTEGRATION: VERIFIED")
print("=" * 70)
