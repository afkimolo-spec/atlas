from atlas.core.resource import (
    ResourceConflictError,
    ResourceManager,
    ResourcePriority,
)


manager = ResourceManager()

manager.register("gpu", capacity=2)

first = manager.acquire(
    "gpu",
    "task-a",
    priority=ResourcePriority.NORMAL,
)

second = manager.acquire(
    "gpu",
    "task-b",
    priority=ResourcePriority.HIGH,
)

assert manager.available("gpu") == 0

try:
    manager.acquire("gpu", "task-c")
except ResourceConflictError:
    pass
else:
    raise AssertionError(
        "Expected resource conflict."
    )

manager.release(first)

assert manager.available("gpu") == 1

released = manager.release_owner("task-b")

assert released == 1
assert manager.available("gpu") == 2

print("=" * 60)
print("ATLAS RESOURCE MANAGER")
print("=" * 60)
print("Capacity  : 2")
print("Conflict   : blocked")
print("Released   :", released)
print("Available  :", manager.available("gpu"))
print("=" * 60)
print("Resource manager verified.")
