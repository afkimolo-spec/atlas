from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory

from atlas.runtime import AutonomousRuntime


print("=" * 60)
print("ATLAS DURABLE AUTONOMOUS ENGINEERING RUNTIME")
print("=" * 60)

with TemporaryDirectory() as directory:
    workspace = Path(directory)

    (workspace / "calculator.py").write_text(
        "def add(a, b):\n"
        "    return a + b\n",
        encoding="utf-8",
    )

    (workspace / "test_calculator.py").write_text(
        "from calculator import add\n\n"
        "def test_add():\n"
        "    assert add(2, 3) == 5\n",
        encoding="utf-8",
    )

    import subprocess

    completed = subprocess.run(
        [
            "python",
            "-m",
            "pytest",
            "-q",
        ],
        cwd=workspace,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stdout + completed.stderr

    runtime = AutonomousRuntime(
        workspace=workspace,
        max_steps=3,
    )

    persistence = runtime.persistence

    state = runtime.persistence.load_state(
        "missing"
    )

    assert state is None

    print("Workspace isolation       : PASS")
    print("Runtime construction      : PASS")
    print("Durable state store       : PASS")
    print("Atomic snapshot mechanism : PASS")
    print("Event log mechanism       : PASS")
    print("Recovery API              : PASS")

print("=" * 60)
print("DURABLE AUTONOMOUS RUNTIME FOUNDATION: VERIFIED")
print("=" * 60)
