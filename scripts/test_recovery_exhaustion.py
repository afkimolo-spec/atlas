from __future__ import annotations

from atlas.core.execution import (
    ExecutionState,
    ExecutionStateMachine,
    StageState,
)
from atlas.core.execution_store import ExecutionStore
from atlas.core.recovery import (
    RecoveryAction,
    RecoveryManager,
    RecoveryPolicy,
)
from atlas.planning import TaskPlanner, TaskStage


print("=" * 60)
print("ATLAS RECOVERY LIMIT")
print("=" * 60)

plan = TaskPlanner().plan(
    "Recovery limit verification",
    research=True,
    architecture=False,
    development=False,
    review=False,
    operations=False,
)

execution = ExecutionStateMachine(plan=plan)
execution.start()

stage = TaskStage.RESEARCH

recovery = RecoveryManager(
    policy=RecoveryPolicy(max_attempts=2)
)

execution.start_stage(stage)
execution.fail_stage(stage, "failure one")
execution.fail(reason="failure one")

first = recovery.recover(
    execution,
    stage.value,
    "failure one",
)

assert first.action == RecoveryAction.RETRY
assert execution.state == ExecutionState.RETRYING

execution.resume()

execution.start_stage(stage)
execution.fail_stage(stage, "failure two")
execution.fail(reason="failure two")

second = recovery.recover(
    execution,
    stage.value,
    "failure two",
)

assert second.action == RecoveryAction.FAIL
assert execution.state == ExecutionState.FAILED
assert execution.get_stage(stage).attempts == 2

print("Attempt 1 : retry")
print("Attempt 2 : fail")
print("Final     : failed")
print("=" * 60)
print("Recovery limit verified.")
print("=" * 60)
