from __future__ import annotations

import os
import subprocess
import tempfile
from pathlib import Path

from atlas.agents.developer import DeveloperAgent
from atlas.security.auth import Credentials
from atlas.security.service import SecurityService
from atlas.workflows.engineering import EngineeringExecutor


def run(
    command: str,
    cwd: Path,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=cwd,
        shell=True,
        capture_output=True,
        text=True,
        check=False,
    )


def main() -> None:
    print("=" * 60)
    print("ATLAS PHASE 8 — REAL ENGINEERING EXECUTION")
    print("=" * 60)

    with tempfile.TemporaryDirectory(
        prefix="atlas-phase8-"
    ) as temporary:
        workspace = Path(
            temporary
        )

        result = run(
            "git init",
            workspace,
        )

        if result.returncode != 0:
            raise RuntimeError(
                result.stderr
            )

        (workspace / "calculator.py").write_text(
            "def add(a, b):\n"
            "    return a - b\n",
            encoding="utf-8",
        )

        (workspace / "test_calculator.py").write_text(
            "from calculator import add\n\n"
            "def test_add():\n"
            "    assert add(2, 3) == 5\n",
            encoding="utf-8",
        )

        result = run(
            "git add . && "
            'git -c user.name="Atlas Test" '
            '-c user.email="atlas@example.invalid" '
            'commit -m "baseline"',
            workspace,
        )

        if result.returncode != 0:
            raise RuntimeError(
                result.stderr
            )

        security = SecurityService()

        username = os.environ.get(
            "ATLAS_E2E_USERNAME"
        )
        password = os.environ.get(
            "ATLAS_E2E_PASSWORD"
        )

        if username and password:
            principal = security.authenticate(
                Credentials(
                    username=username,
                    password=password,
                )
            )
        else:
            principal = None

        executor = EngineeringExecutor(
            workspace,
            security=security if principal else None,
            principal=principal,
            developer=DeveloperAgent(),
            max_steps=20,
        )

        result = executor.execute(
            (
                "Fix the defect in calculator.py so that add(a, b) "
                "returns the arithmetic sum. Run the test suite and "
                "do not report completion until the test passes."
            ),
            session_id="phase8-e2e",
        )

        assert result.succeeded
        assert result.verification_passed

        calculator = (
            workspace / "calculator.py"
        ).read_text(
            encoding="utf-8"
        )

        assert (
            "return a + b"
            in calculator
        )

        tests = run(
            "pytest -q",
            workspace,
        )

        if tests.returncode != 0:
            raise RuntimeError(
                tests.stdout
                + "\n"
                + tests.stderr
            )

        print()
        print("Engineering task : verified")
        print("File modification : verified")
        print("Test execution    : verified")
        print("Verification      : verified")
        print(
            "Steps             :",
            result.attempts,
        )
        print()
        print("PHASE 8 ENGINEERING EXECUTION VERIFIED")
        print("=" * 60)


if __name__ == "__main__":
    main()
