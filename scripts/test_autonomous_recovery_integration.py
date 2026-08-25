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
print("ATLAS DURABLE AUTONOMOUS RECOVERY")
print("=" * 60)

planner = TaskPlanner()

plan = planner.plan(
    "Durable autonomous recovery integration",
    research=True,
    architecture=True,
    development=False,
    review=False,
    operations=False,
)

store = ExecutionStore()
execution_id = "test-durable-autonomous-recovery"
store.delete(execution_id)

execution = ExecutionStateMachine(plan=plan)
execution.start()

research = execution.start_stage(
    TaskStage.RESEARCH
)

assert research.attempts == 1

execution.fail_stage(
    TaskStage.RESEARCH,
    "Simulated transient failure",
)

execution.fail(
    reason="Research failed"
)

store.save(
    execution_id,
    execution,
)

recovery = RecoveryManager(
    policy=RecoveryPolicy(max_attempts=3)
)

decision = recovery.recover(
    execution,
    TaskStage.RESEARCH.value,
    "Simulated transient failure",
)

assert decision.action == RecoveryAction.RETRY
assert execution.state == ExecutionState.RETRYING

store.save(
    execution_id,
    execution,
)

restored = store.restore(
    execution_id,
    plan,
)

assert restored is not None
assert restored.state == ExecutionState.RETRYING
assert (
    restored.get_stage(TaskStage.RESEARCH).state
    == StageState.PENDING
)
assert (
    restored.get_stage(TaskStage.RESEARCH).attempts
    == 1
)

restored.resume(
    reason="Resume persisted retry"
)

restored.start_stage(
    TaskStage.RESEARCH
)

assert (
    restored.get_stage(TaskStage.RESEARCH).attempts
    == 2
)

restored.complete_stage(
    TaskStage.RESEARCH,
    "Recovered research result",
)

store.save(
    execution_id,
    restored,
)

restored = store.restore(
    execution_id,
    plan,
)

assert restored is not None
assert restored.state == ExecutionState.RUNNING
assert (
    restored.get_stage(TaskStage.RESEARCH).state
    == StageState.COMPLETED
)
assert (
    restored.get_stage(TaskStage.RESEARCH).attempts
    == 2
)
assert (
    restored.get_stage(TaskStage.RESEARCH).result
    == "Recovered research result"
)
assert restored.ready(TaskStage.ARCHITECTURE)

restored.start_stage(
    TaskStage.ARCHITECTURE
)

restored.complete_stage(
    TaskStage.ARCHITECTURE,
    "Architecture after recovery",
)

restored.complete(
    reason="Recovered execution completed"
)

store.save(
    execution_id,
    restored,
)

final = store.restore(
    execution_id,
    plan,
)

assert final is not None
assert final.state == ExecutionState.COMPLETED
assert (
    final.get_stage(TaskStage.RESEARCH).attempts
    == 2
)
assert (
    final.get_stage(TaskStage.ARCHITECTURE).state
    == StageState.COMPLETED
)

store.delete(execution_id)

print("Initial failure : failed")
print("Recovery action : retry")
print("Retry transition: retrying -> running")
print("Research attempt: 2")
print("Architecture    : completed")
print("Final state     : completed")
print("=" * 60)
print("Durable autonomous recovery verified.")
print("=" * 60)
