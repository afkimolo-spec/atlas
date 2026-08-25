from atlas.core.execution import (
    ExecutionState,
    ExecutionStateMachine,
    InvalidStateTransition,
)


print("=" * 60)
print("ATLAS EXECUTION STATE MACHINE")
print("=" * 60)


machine = ExecutionStateMachine()

print("Initial :", machine.state.value)

assert machine.state == ExecutionState.CREATED
assert not machine.is_terminal


machine.start(
    reason="Execution started."
)

print("Started :", machine.state.value)

assert machine.state == ExecutionState.RUNNING
assert machine.is_running


machine.pause(
    reason="Execution paused for validation."
)

print("Paused  :", machine.state.value)

assert machine.state == ExecutionState.PAUSED
assert machine.is_paused


machine.resume(
    reason="Execution resumed."
)

print("Resumed :", machine.state.value)

assert machine.state == ExecutionState.RUNNING


machine.complete(
    reason="Execution completed successfully."
)

print("Final   :", machine.state.value)

assert machine.state == ExecutionState.COMPLETED
assert machine.is_terminal


print("-" * 60)
print("TRANSITIONS")

for event in machine.history:
    print(
        f"{event.from_state.value}"
        f" -> "
        f"{event.to_state.value}"
        f" | "
        f"{event.reason}"
    )


print("-" * 60)
print("INVALID TRANSITION TEST")

try:
    machine.start()

except InvalidStateTransition as exc:
    print("Blocked :", exc)

else:
    raise AssertionError(
        "Terminal execution accepted an invalid transition."
    )


print("-" * 60)
print("SNAPSHOT")

snapshot = machine.snapshot()

print("State    :", snapshot["state"])
print("Terminal :", snapshot["terminal"])
print(
    "History  :",
    len(snapshot["history"]),
)

assert snapshot["state"] == "completed"
assert snapshot["terminal"] is True
assert len(snapshot["history"]) == 4


print("=" * 60)
print("Execution state machine verified.")
print("=" * 60)
