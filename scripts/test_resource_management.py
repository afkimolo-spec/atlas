from __future__ import annotations

import tempfile
import threading
import time
from pathlib import Path

from atlas.core.resource import (
    ResourceConflictError,
    ResourceManager,
    ResourcePriority,
)
from atlas.core.resource_store import ResourceStore


print("=" * 60)
print("ATLAS RESOURCE MANAGEMENT")
print("=" * 60)

with tempfile.TemporaryDirectory() as directory:
    database = Path(directory) / "atlas.db"

    manager = ResourceManager(database)

    manager.register(
        "engineering-model",
        capacity=1,
    )

    # --------------------------------------------------------------
    # Ownership / allocation
    # --------------------------------------------------------------

    first = manager.acquire(
        "engineering-model",
        "execution-a",
        priority=ResourcePriority.HIGH,
    )

    assert manager.available(
        "engineering-model"
    ) == 0

    try:
        manager.acquire(
            "engineering-model",
            "execution-b",
        )
    except ResourceConflictError:
        pass
    else:
        raise AssertionError(
            "Conflicting allocation was not blocked."
        )

    manager.release(first)

    assert manager.available(
        "engineering-model"
    ) == 1

    # --------------------------------------------------------------
    # Priority
    # --------------------------------------------------------------

    high = manager.acquire(
        "engineering-model",
        "high-priority",
        priority=ResourcePriority.HIGH,
    )

    leases = manager.leases(
        resource="engineering-model"
    )

    assert leases[0].owner == "high-priority"
    assert (
        leases[0].priority
        == ResourcePriority.HIGH
    )

    manager.release(high)

    # --------------------------------------------------------------
    # Execution locking
    # --------------------------------------------------------------

    manager.lock_execution(
        "exec-1",
        "worker-a",
    )

    assert (
        manager.execution_lock_owner("exec-1")
        == "worker-a"
    )

    try:
        manager.lock_execution(
            "exec-1",
            "worker-b",
        )
    except ResourceConflictError:
        pass
    else:
        raise AssertionError(
            "Execution lock conflict was not blocked."
        )

    manager.unlock_execution(
        "exec-1",
        "worker-a",
    )

    assert (
        manager.execution_lock_owner("exec-1")
        is None
    )

    # --------------------------------------------------------------
    # Persistent state
    # --------------------------------------------------------------

    manager.lock_execution(
        "exec-persist",
        "worker-a",
    )

    manager.acquire(
        "engineering-model",
        "worker-a",
    )

    restarted = ResourceManager(database)

    assert (
        restarted.execution_lock_owner(
            "exec-persist"
        )
        == "worker-a"
    )

    assert restarted.available(
        "engineering-model"
    ) == 0

    # --------------------------------------------------------------
    # Cross-thread concurrency
    # --------------------------------------------------------------

    manager.unlock_execution(
        "exec-persist",
        "worker-a",
    )

    restarted.release_owner(
        "worker-a"
    )

    successes = []
    failures = []
    barrier = threading.Barrier(3)

    def worker(name: str) -> None:
        local = ResourceManager(database)

        barrier.wait()

        try:
            lease = local.acquire(
                "engineering-model",
                name,
            )

            successes.append(name)

            time.sleep(0.05)

            local.release(lease)

        except ResourceConflictError:
            failures.append(name)

    threads = [
        threading.Thread(
            target=worker,
            args=(f"worker-{index}",),
        )
        for index in range(2)
    ]

    for thread in threads:
        thread.start()

    barrier.wait()

    for thread in threads:
        thread.join()

    assert len(successes) == 1
    assert len(failures) == 1

    # --------------------------------------------------------------
    # Expiration / recovery
    # --------------------------------------------------------------

    expiring = restarted.acquire(
        "engineering-model",
        "expiring",
        ttl_seconds=0.05,
    )

    time.sleep(0.10)

    recovered = restarted.recover_expired()

    assert recovered >= 1

    assert restarted.available(
        "engineering-model"
    ) == 1

    assert expiring.owner == "expiring"

    # --------------------------------------------------------------
    # Store facade
    # --------------------------------------------------------------

    store = ResourceStore(database)

    snapshot = store.snapshot()

    assert "resources" in snapshot
    assert "leases" in snapshot
    assert len(store.resources()) == 1

print("Registry        : verified")
print("Ownership       : verified")
print("Conflict        : blocked")
print("Priority        : verified")
print("Execution lock  : verified")
print("Persistence     : verified")
print("Concurrency     : verified")
print("Expiry recovery : verified")
print("=" * 60)
print("Resource management verified.")
print("=" * 60)
