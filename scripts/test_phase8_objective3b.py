from __future__ import annotations

import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from atlas.core.session import Session
from atlas.workflows.engineering import EngineeringExecutor


@dataclass(frozen=True)
class RealTask:
    name: str
    task: str
    source_files: dict[str, str]
    test_files: dict[str, str]
    required_source_changes: set[str]
    minimum_writes: int = 1
    minimum_reads: int = 1
    minimum_commands: int = 1
    require_failed_intermediate_verification: bool = False


TASKS = (
    RealTask(
        name="multi_file_service_fix",
        task=(
            "Repair the service implementation and its item "
            "normalization helper. The repository intentionally "
            "contains defects in both source modules. "
            "normalize_item(item) must return a dictionary with "
            "a numeric float value under the 'price' key. "
            "calculate_total(items) must normalize every item, "
            "sum the normalized prices exactly once, and return "
            "a numeric total. Investigate both modules and their "
            "interaction before editing. Do not modify any test "
            "files. Make the smallest correct source changes, "
            "run the tests, diagnose failures, and continue until "
            "the complete verification command succeeds. Both "
            "source modules must be corrected."
        ),
        source_files={
            "src/items.py": (
                "def normalize_item(item):\n"
                "    return {\n"
                "        'price': str(item['price']).strip()\n"
                "    }\n"
            ),
            "src/service.py": (
                "from items import normalize_item\n\n"
                "\n"
                "def calculate_total(items):\n"
                "    total = 0.0\n"
                "    for item in items:\n"
                "        normalized = normalize_item(item)\n"
                "        total += float(normalized['price']) * 2\n"
                "    return total\n"
            ),
        },
        test_files={
            "tests/test_service.py": (
                "from items import normalize_item\n"
                "from service import calculate_total\n\n"
                "\n"
                "def test_normalize_item_contract():\n"
                "    normalized = normalize_item({'price': ' 10.50 '})\n"
                "    assert normalized == {'price': 10.5}\n"
                "    assert isinstance(normalized['price'], float)\n"
                "\n"
                "\n"
                "def test_total_multiple_items():\n"
                "    assert calculate_total([\n"
                "        {'price': '10.50'},\n"
                "        {'price': '2.25'},\n"
                "        {'price': 7},\n"
                "    ]) == 19.75\n"
                "\n"
                "\n"
                "def test_total_empty():\n"
                "    assert calculate_total([]) == 0.0\n"
            ),
        },
        required_source_changes={
            "src/items.py",
            "src/service.py",
        },
        minimum_writes=2,
        minimum_reads=2,
        minimum_commands=1,
    ),
    RealTask(
        name="cross_module_feature",
        task=(
            "Implement the missing user greeting feature. "
            "format_user_name(name) in src/users.py must strip "
            "surrounding whitespace, collapse repeated internal "
            "whitespace to a single space, and preserve letter "
            "casing. greet_user(name) in src/greeting.py must use "
            "format_user_name and return exactly "
            "'Hello, <normalized name>!'. Investigate the existing "
            "module relationship before editing. Do not modify "
            "the existing tests. Make the necessary source "
            "changes, run the tests, diagnose failures, and "
            "finish only after verification succeeds. The "
            "correct solution requires changes to both source "
            "modules."
        ),
        source_files={
            "src/users.py": (
                "def format_user_name(name):\n"
                "    raise NotImplementedError\n"
            ),
            "src/greeting.py": (
                "from users import format_user_name\n\n"
                "\n"
                "def greet_user(name):\n"
                "    return f'Hello, {name}!'\n"
            ),
        },
        test_files={
            "tests/test_greeting.py": (
                "from users import format_user_name\n"
                "from greeting import greet_user\n\n"
                "\n"
                "def test_name_formatter_contract():\n"
                "    assert format_user_name('  Alice    Marie  ') == 'Alice Marie'\n"
                "    assert format_user_name('  aLiCe   MaRiE  ') == 'aLiCe MaRiE'\n"
                "\n"
                "\n"
                "def test_normalized_greeting():\n"
                "    assert greet_user('  Alice    Marie  ') == 'Hello, Alice Marie!'\n"
                "\n"
                "\n"
                "def test_case_is_preserved():\n"
                "    assert greet_user('  aLiCe  ') == 'Hello, aLiCe!'\n"
            ),
        },
        required_source_changes={
            "src/users.py",
            "src/greeting.py",
        },
        minimum_writes=2,
        minimum_reads=2,
        minimum_commands=1,
    ),
    RealTask(
        name="iterative_debugging",
        task=(
            "Fix the order-processing implementation so that "
            "process_orders(orders) returns the total value of "
            "valid orders. Each order must be normalized by "
            "normalize_order(order), invalid orders must be "
            "skipped, and the returned total must be numeric. "
            "There are multiple related defects in the "
            "implementation. Do not modify the existing tests. "
            "Investigate the implementation, run the tests, use "
            "the failure output to diagnose the remaining defect, "
            "make all required source changes, and rerun "
            "verification until every test passes. The first "
            "source change may not be sufficient."
        ),
        source_files={
            "src/orders.py": (
                "def normalize_order(order):\n"
                "    if not isinstance(order, dict):\n"
                "        return None\n"
                "    if 'amount' not in order:\n"
                "        return None\n"
                "    try:\n"
                "        return {'amount': float(order['amount'])}\n"
                "    except (TypeError, ValueError):\n"
                "        return None\n"
            ),
            "src/processor.py": (
                "from orders import normalize_order\n\n"
                "\n"
                "def process_orders(orders):\n"
                "    total = ''\n"
                "    for order in orders:\n"
                "        normalized = normalize_order(order)\n"
                "        if normalized:\n"
                "            total += str(normalized['amount'])\n"
                "    return total\n"
            ),
        },
        test_files={
            "tests/test_processor.py": (
                "from processor import process_orders\n\n"
                "\n"
                "def test_valid_orders_are_summed():\n"
                "    assert process_orders([\n"
                "        {'amount': 10},\n"
                "        {'amount': '2.5'},\n"
                "        {'amount': 7.5},\n"
                "    ]) == 20.0\n"
                "\n"
                "\n"
                "def test_invalid_orders_are_skipped():\n"
                "    assert process_orders([\n"
                "        {'amount': 10},\n"
                "        {},\n"
                "        {'amount': 'bad'},\n"
                "        None,\n"
                "    ]) == 10.0\n"
            ),
        },
        required_source_changes={
            "src/processor.py",
        },
        minimum_writes=1,
        minimum_reads=1,
        minimum_commands=1,
        require_failed_intermediate_verification=True,
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
        path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )
        path.write_text(
            content,
            encoding="utf-8",
        )

    for relative, content in task.test_files.items():
        path = root / relative
        path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )
        path.write_text(
            content,
            encoding="utf-8",
        )
        snapshots[relative] = content

    conftest = root / "tests" / "conftest.py"

    conftest.write_text(
        "import sys\n"
        "from pathlib import Path\n\n"
        "sys.path.insert(\n"
        "    0,\n"
        "    str(Path(__file__).resolve().parents[1] / 'src'),\n"
        ")\n",
        encoding="utf-8",
    )

    snapshots["tests/conftest.py"] = conftest.read_text(
        encoding="utf-8",
    )

    return snapshots


def initialize_git(root: Path) -> None:
    run(
        ["git", "init"],
        root,
    )

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

    run(
        ["git", "add", "."],
        root,
    )

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


def assert_workspace_changes(
    root: Path,
    allowed_source_files: set[str],
    required_source_files: set[str],
) -> list[str]:
    changed = modified_paths(root)

    unauthorized = [
        path
        for path in changed
        if path not in allowed_source_files
    ]

    if unauthorized:
        raise AssertionError(
            "Unauthorized workspace changes: "
            f"{unauthorized}"
        )

    missing = [
        path
        for path in required_source_files
        if path not in changed
    ]

    if missing:
        raise AssertionError(
            "Required source files were not changed: "
            f"{missing}"
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


def count_successful_actions(
    result: Any,
    action_type: str,
) -> int:
    return sum(
        1
        for action in result.actions
        if (
            action.type == action_type
            and action.succeeded
        )
    )


def count_failed_actions(
    result: Any,
    action_type: str,
) -> int:
    return sum(
        1
        for action in result.actions
        if (
            action.type == action_type
            and not action.succeeded
        )
    )


def main() -> None:
    print("=" * 60)
    print("ATLAS PHASE 8 — OBJECTIVE 3B")
    print("BROADER AUTONOMOUS ENGINEERING VALIDATION")
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
            prefix=(
                "atlas-objective3b-"
                f"{task.name}-"
            ),
        ) as temporary:
            workspace = Path(temporary)

            test_snapshots = write_workspace(
                task,
                workspace,
            )

            initialize_git(workspace)

            baseline = run(
                [
                    "python",
                    "-m",
                    "pytest",
                    "-q",
                ],
                workspace,
                check=False,
            )

            cleanup_generated_artifacts(
                workspace,
            )

            if baseline.returncode == 0:
                raise AssertionError(
                    f"{task.name}: baseline tests "
                    "unexpectedly passed"
                )

            print(
                "Baseline failure           : verified"
            )

            session = Session()
            session.start(task.task)

            executor = EngineeringExecutor(
                workspace=workspace,
                developer=None,
                max_steps=40,
                max_action_failures=3,
                command_timeout=120,
                verification_command=(
                    "python -m pytest -q"
                ),
            )

            result = executor.execute(
                task.task,
                session_id=session.id,
            )

            successful_reads = count_successful_actions(
                result,
                "read_file",
            )

            successful_writes = count_successful_actions(
                result,
                "write_file",
            )

            successful_commands = count_successful_actions(
                result,
                "run_command",
            )

            failed_commands = count_failed_actions(
                result,
                "run_command",
            )

            action_types = [
                action.type
                for action in result.actions
            ]

            print(
                "Autonomous execution      :",
                result.succeeded,
            )
            print(
                "Verification              :",
                result.verification_passed,
            )
            print(
                "Executor steps            :",
                result.attempts,
            )
            print(
                "Action history            :",
                action_types,
            )
            print(
                "Successful reads          :",
                successful_reads,
            )
            print(
                "Successful writes         :",
                successful_writes,
            )
            print(
                "Successful commands       :",
                successful_commands,
            )
            print(
                "Failed commands           :",
                failed_commands,
            )

            if not result.succeeded:
                raise AssertionError(
                    f"{task.name}: autonomous "
                    "execution failed"
                )

            if not result.verification_passed:
                raise AssertionError(
                    f"{task.name}: verification "
                    "was not recorded"
                )

            if successful_reads < task.minimum_reads:
                raise AssertionError(
                    f"{task.name}: expected at least "
                    f"{task.minimum_reads} successful "
                    f"read_file actions, got "
                    f"{successful_reads}"
                )

            if successful_writes < task.minimum_writes:
                raise AssertionError(
                    f"{task.name}: expected at least "
                    f"{task.minimum_writes} successful "
                    f"write_file actions, got "
                    f"{successful_writes}"
                )

            if successful_commands < task.minimum_commands:
                raise AssertionError(
                    f"{task.name}: expected at least "
                    f"{task.minimum_commands} successful "
                    f"run_command actions, got "
                    f"{successful_commands}"
                )

            if task.require_failed_intermediate_verification:
                if failed_commands == 0:
                    raise AssertionError(
                        f"{task.name}: expected at least "
                        "one failed intermediate command"
                    )

                print(
                    "Intermediate failure      : verified"
                )

            final = run(
                [
                    "python",
                    "-m",
                    "pytest",
                    "-q",
                ],
                workspace,
                check=False,
            )

            cleanup_generated_artifacts(
                workspace,
            )

            if final.returncode != 0:
                print()
                print(
                    "===== FINAL STDOUT ====="
                )
                print(final.stdout)
                print()
                print(
                    "===== FINAL STDERR ====="
                )
                print(final.stderr)

                raise AssertionError(
                    f"{task.name}: final verification "
                    "failed"
                )

            print(
                "Final verification        : verified"
            )

            for relative, expected in test_snapshots.items():
                actual = (
                    workspace / relative
                ).read_text(
                    encoding="utf-8",
                )

                if actual != expected:
                    raise AssertionError(
                        f"{task.name}: test modified: "
                        f"{relative}"
                    )

            print(
                "Test integrity             : verified"
            )

            changed_source_files = (
                assert_workspace_changes(
                    workspace,
                    set(task.source_files),
                    task.required_source_changes,
                )
            )

            print(
                "Workspace containment      : verified"
            )
            print(
                "Required source changes    : verified"
            )
            print(
                "Changed source files       :",
                changed_source_files,
            )

            session.finish()

            passed += 1

            print(
                f"{task.name:<27}: VERIFIED"
            )

    print()
    print("=" * 60)
    print(
        f"REAL COMPLEX TASKS VERIFIED : "
        f"{passed}/{len(TASKS)}"
    )
    print(
        "PHASE 8 OBJECTIVE 3B"
    )
    print(
        "BROADER AUTONOMOUS ENGINEERING "
        "VALIDATION VERIFIED"
    )
    print("=" * 60)


if __name__ == "__main__":
    main()
