from __future__ import annotations

from atlas.core.execution import (
    ExecutionState,
    ExecutionStateMachine,
    StageState,
)
from atlas.core.recovery import (
    RecoveryAction,
    RecoveryManager,
    RecoveryPolicy,
)
from atlas.core.execution_store import ExecutionStore
from atlas.planning import TaskPlanner, TaskStage


print("=" * 60)
print("ATLAS AUTONOMOUS RECOVERY")
print("=" * 60)

planner = TaskPlanner()

plan = planner.plan(
    "Test autonomous recovery",
    research=True,
    architecture=False,
    development=False,
    review=False,
    operations=False,
)

execution = ExecutionStateMachine(plan=plan)
execution.start()

stage = TaskStage.RESEARCH

execution.start_stage(stage)
execution.fail_stage(
    stage,
    "Simulated research failure",
)
execution.fail(
    reason="Simulated autonomous stage failure",
)

store = ExecutionStore()
execution_id = "test-autonomous-recovery"
store.delete(execution_id)
store.save(execution_id, execution)

recovery = RecoveryManager(
    policy=RecoveryPolicy(max_attempts=2)
)

decision = recovery.recover(
    execution,
    stage.value,
    "Simulated research failure",
)

assert decision.action == RecoveryAction.RETRY
assert execution.state == ExecutionState.RETRYING
assert execution.get_stage(stage).state == StageState.PENDING

store.save(execution_id, execution)

restored = store.restore(
    execution_id,
    plan,
)

assert restored is not None
assert restored.state == ExecutionState.RETRYING
assert restored.get_stage(stage).state == StageState.PENDING

restored._transition(
    ExecutionState.RUNNING,
    reason="Recovery retry resumed",
)

restored.start_stage(stage)
restored.complete_stage(
    stage,
    "Research recovered successfully.",
)
restored.complete(
    reason="Recovered autonomous execution completed",
)

store.save(execution_id, restored)

final = store.restore(
    execution_id,
    plan,
)

assert final is not None
assert final.state == ExecutionState.COMPLETED
assert final.get_stage(stage).state == StageState.COMPLETED
assert final.get_stage(stage).attempts == 2

store.delete(execution_id)

print("Initial state : failed")
print("Recovery      : retry")
print("Retry state   : retrying")
print("Restored      : retrying")
print("Final state   : completed")
print("Attempts      : 2")
print("=" * 60)
print("Autonomous recovery verified.")
print("=" * 60)
