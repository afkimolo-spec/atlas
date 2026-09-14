from __future__ import annotations

import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

from atlas.core.session import Session
from atlas.workflows.engineering import EngineeringExecutor


@dataclass(frozen=True)
class RealTask:
    name: str
    task: str
    source_files: dict[str, str]
    test_files: dict[str, str]


TASKS = (
    RealTask(
        name="calculator_bugfix",
        task=(
            "Fix the calculator implementation so that add(a, b) "
            "performs mathematical addition. Do not modify any test "
            "files. Investigate the implementation, make the smallest "
            "correct source-code change, run the tests, and finish only "
            "after the verification command succeeds."
        ),
        source_files={
            "src/calculator.py": (
                "def add(a, b):\n"
                "    return a - b\n"
            ),
        },
        test_files={
            "tests/test_calculator.py": (
                "from calculator import add\n\n"
                "\n"
                "def test_add_positive_numbers():\n"
                "    assert add(2, 3) == 5\n"
                "\n"
                "\n"
                "def test_add_negative_numbers():\n"
                "    assert add(-2, -3) == -5\n"
                "\n"
                "\n"
                "def test_add_mixed_numbers():\n"
                "    assert add(-2, 5) == 3\n"
            ),
        },
    ),
    RealTask(
        name="statistics_feature",
        task=(
            "Implement the missing mean(values) function in "
            "src/statistics.py. It must return the arithmetic mean "
            "of a non-empty iterable of numbers and raise ValueError "
            "for an empty iterable. Do not modify test files. "
            "Investigate the existing implementation, make the "
            "necessary source change, run the tests, and finish only "
            "after the verification command succeeds."
        ),
        source_files={
            "src/statistics.py": (
                "def mean(values):\n"
                "    raise NotImplementedError\n"
            ),
        },
        test_files={
            "tests/test_statistics.py": (
                "from statistics import mean\n\n"
                "\n"
                "def test_mean_integers():\n"
                "    assert mean([1, 2, 3, 4, 5]) == 3\n"
                "\n"
                "\n"
                "def test_mean_floats():\n"
                "    assert mean([1.5, 2.5, 3.5]) == 2.5\n"
                "\n"
                "\n"
                "def test_mean_empty():\n"
                "    try:\n"
                "        mean([])\n"
                "    except ValueError:\n"
                "        return\n"
                "    raise AssertionError('mean([]) must raise ValueError')\n"
            ),
        },
    ),
    RealTask(
        name="string_bugfix",
        task=(
            "Fix normalize_name(value) in src/names.py. The function "
            "must strip leading and trailing whitespace, collapse "
            "runs of internal whitespace to a single space, and "
            "preserve the original letter casing. Do not modify test "
            "files. Investigate the implementation, make the smallest "
            "correct source-code change, run the tests, and finish "
            "only after the verification command succeeds."
        ),
        source_files={
            "src/names.py": (
                "def normalize_name(value):\n"
                "    return value\n"
            ),
        },
        test_files={
            "tests/test_names.py": (
                "from names import normalize_name\n\n"
                "\n"
                "def test_trim():\n"
                "    assert normalize_name('  Alice  ') == 'Alice'\n"
                "\n"
                "\n"
                "def test_collapse_internal_whitespace():\n"
                "    assert normalize_name('Alice    Marie') == 'Alice Marie'\n"
                "\n"
                "\n"
                "def test_preserve_case():\n"
                "    assert normalize_name('  aLiCe   MaRiE  ') == 'aLiCe MaRiE'\n"
            ),
        },
    ),
)


def run(
    command: list[str],
    cwd: Path,
    *,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=cwd,
        text=True,
        capture_output=True,
        check=check,
    )


def cleanup_generated_artifacts(root: Path) -> None:
    for path in root.rglob("__pycache__"):
        if path.is_dir():
            shutil.rmtree(path)

    for path in root.rglob("*.pyc"):
        if path.is_file():
            path.unlink()


def write_workspace(
    task: RealTask,
    root: Path,
) -> dict[str, str]:
    snapshots: dict[str, str] = {}

    (root / "src").mkdir(parents=True)
    (root / "tests").mkdir(parents=True)

    for relative, content in task.source_files.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            content,
            encoding="utf-8",
        )

    for relative, content in task.test_files.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            content,
            encoding="utf-8",
        )
        snapshots[relative] = content

    conftest = root / "tests" / "conftest.py"
    conftest.write_text(
        "import sys\n"
        "from pathlib import Path\n\n"
        "sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))\n",
        encoding="utf-8",
    )
    snapshots["tests/conftest.py"] = conftest.read_text(
        encoding="utf-8",
    )

    return snapshots


def initialize_git(root: Path) -> None:
    run(["git", "init"], root)
    run(
        [
            "git",
            "config",
            "user.email",
            "atlas-validation@example.invalid",
        ],
        root,
    )
    run(
        [
            "git",
            "config",
            "user.name",
            "Atlas Validation",
        ],
        root,
    )
    run(["git", "add", "."], root)
    run(
        [
            "git",
            "commit",
            "-m",
            "baseline",
        ],
        root,
    )


def modified_paths(root: Path) -> list[str]:
    cleanup_generated_artifacts(root)

    result = run(
        ["git", "status", "--short"],
        root,
    )

    paths: list[str] = []

    for line in result.stdout.splitlines():
        if not line.strip():
            continue

        path = line[3:].strip()

        if " -> " in path:
            path = path.split(" -> ", 1)[1]

        paths.append(path)

    return paths


def assert_source_only_changes(
    root: Path,
    allowed_source_files: set[str],
) -> list[str]:
    changed = modified_paths(root)

    unauthorized = [
        path
        for path in changed
        if path not in allowed_source_files
    ]

    if unauthorized:
        raise AssertionError(
            "Unauthorized workspace changes detected: "
            f"{unauthorized}"
        )

    source_changes = [
        path
        for path in changed
        if path in allowed_source_files
    ]

    if not source_changes:
        raise AssertionError(
            "No authorized source-file changes detected."
        )

    return source_changes


def main() -> None:
    print("=" * 60)
    print("ATLAS PHASE 8 — OBJECTIVE 3")
    print("AUTONOMOUS ENGINEERING VALIDATION")
    print("=" * 60)

    passed = 0

    for index, task in enumerate(
        TASKS,
        start=1,
    ):
        print()
        print("=" * 60)
        print(
            f"TASK {index}/{len(TASKS)} : "
            f"{task.name}"
        )
        print("=" * 60)

        with tempfile.TemporaryDirectory(
            prefix=f"atlas-objective3-{task.name}-"
        ) as temporary:
            workspace = Path(temporary)

            test_snapshots = write_workspace(
                task,
                workspace,
            )

            initialize_git(workspace)

            initial_tests = run(
                [
                    "python",
                    "-m",
                    "pytest",
                    "-q",
                ],
                workspace,
                check=False,
            )

            cleanup_generated_artifacts(workspace)

            if initial_tests.returncode == 0:
                raise AssertionError(
                    f"{task.name}: baseline tests unexpectedly passed"
                )

            print("Baseline failure      : verified")

            session = Session()
            session.start(task.task)

            executor = EngineeringExecutor(
                workspace=workspace,
                developer=None,
                max_steps=30,
                max_action_failures=3,
                command_timeout=120,
                verification_command="python -m pytest -q",
            )

            result = executor.execute(
                task.task,
                session_id=session.id,
            )

            print(
                "Autonomous execution  :",
                result.succeeded,
            )
            print(
                "Verification          :",
                result.verification_passed,
            )
            print(
                "Steps                 :",
                result.attempts,
            )

            if not result.succeeded:
                raise AssertionError(
                    f"{task.name}: autonomous execution did not succeed"
                )

            if not result.verification_passed:
                raise AssertionError(
                    f"{task.name}: verification was not recorded"
                )

            action_types = [
                action.type
                for action in result.actions
            ]

            if "write_file" not in action_types:
                raise AssertionError(
                    f"{task.name}: no write_file action recorded"
                )

            if "run_command" not in action_types:
                raise AssertionError(
                    f"{task.name}: no run_command action recorded"
                )

            final_tests = run(
                [
                    "python",
                    "-m",
                    "pytest",
                    "-q",
                ],
                workspace,
                check=False,
            )

            if final_tests.returncode != 0:
                print(final_tests.stdout)
                print(final_tests.stderr)
                raise AssertionError(
                    f"{task.name}: final tests failed"
                )

            print("Final tests            : verified")

            cleanup_generated_artifacts(workspace)

            for relative, expected in test_snapshots.items():
                actual = (
                    workspace / relative
                ).read_text(
                    encoding="utf-8",
                )

                if actual != expected:
                    raise AssertionError(
                        f"{task.name}: test file modified: {relative}"
                    )

            print("Test integrity         : verified")

            allowed_source_files = {
                *task.source_files.keys(),
            }

            changed_source_files = assert_source_only_changes(
                workspace,
                allowed_source_files,
            )

            print("Workspace containment  : verified")
            print("Source modification    : verified")
            print(
                "Changed source files   :",
                changed_source_files,
            )

            session.finish()

            passed += 1

            print(
                f"{task.name:<23}: VERIFIED"
            )

    print()
    print("=" * 60)
    print(
        f"REAL TASKS VERIFIED     : "
        f"{passed}/{len(TASKS)}"
    )
    print("PHASE 8 OBJECTIVE 3")
    print("AUTONOMOUS ENGINEERING VALIDATION VERIFIED")
    print("=" * 60)


if __name__ == "__main__":
    main()
