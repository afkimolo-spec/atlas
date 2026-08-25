from atlas.core import (
    ExecutionState,
    RecoveryAction,
    RecoveryManager,
    RecoveryPolicy,
    StageState,
)
from atlas.core.execution import ExecutionStateMachine
from atlas.planning import TaskStage


print("=" * 60)
print("ATLAS RECOVERY MANAGER")
print("=" * 60)

execution = ExecutionStateMachine(
    stages=[
        TaskStage.DEVELOPMENT,
    ]
)

execution.start()

execution.start_stage(
    TaskStage.DEVELOPMENT
)

execution.fail_stage(
    TaskStage.DEVELOPMENT,
    "Compilation failed.",
)

execution.fail(
    "Development stage failed."
)

assert execution.state == ExecutionState.FAILED

manager = RecoveryManager(
    RecoveryPolicy(max_attempts=2)
)

decision = manager.recover(
    execution,
    TaskStage.DEVELOPMENT,
    "Compilation failed.",
)

print("Action  :", decision.action.value)
print("Attempt :", decision.attempt)
print("Reason  :", decision.reason)

assert decision.action == RecoveryAction.RETRY
assert execution.state == ExecutionState.RETRYING

execution.start()

execution.start_stage(
    TaskStage.DEVELOPMENT
)

execution.fail_stage(
    TaskStage.DEVELOPMENT,
    "Compilation failed again.",
)

execution.fail(
    "Development stage failed again."
)

decision = manager.recover(
    execution,
    TaskStage.DEVELOPMENT,
    "Compilation failed again.",
)

print("Action  :", decision.action.value)
print("Attempt :", decision.attempt)
print("Reason  :", decision.reason)

assert decision.action == RecoveryAction.FAIL
assert execution.state == ExecutionState.FAILED

assert not manager.can_retry(
    execution,
    TaskStage.DEVELOPMENT,
)

print("-" * 60)
print(
    "Final state :",
    execution.state.value,
)
print(
    "Attempts    :",
    execution.get_stage(
        TaskStage.DEVELOPMENT
    ).attempts,
)

assert execution.get_stage(
    TaskStage.DEVELOPMENT
).state == StageState.FAILED

assert execution.get_stage(
    TaskStage.DEVELOPMENT
).attempts == 2

print("=" * 60)
print("Recovery manager verified.")
print("=" * 60)
