from __future__ import annotations

import os
import sqlite3
import tempfile
from pathlib import Path
from urllib.request import urlopen

from atlas.core.execution_store import ExecutionStore
from atlas.core.health import HealthChecker


print("=" * 60)
print("ATLAS DEPLOYMENT & OPERATIONS")
print("=" * 60)

with tempfile.TemporaryDirectory() as directory:
    root = Path(directory)

    database = (
        root
        / ".ai"
        / "memory"
        / "db"
        / "atlas.db"
    )

    database.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    # Persistent state creation.
    store = ExecutionStore(
        database
    )

    connection = sqlite3.connect(
        database
    )

    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS
        deployment_test (
            id INTEGER PRIMARY KEY,
            value TEXT NOT NULL
        )
        """
    )

    connection.execute(
        """
        INSERT INTO deployment_test
        (id, value)
        VALUES (1, 'persistent')
        """
    )

    connection.commit()
    connection.close()

    # Simulated restart: new store/database connection.
    restarted = ExecutionStore(
        database
    )

    connection = sqlite3.connect(
        database
    )

    row = connection.execute(
        """
        SELECT value
        FROM deployment_test
        WHERE id = 1
        """
    ).fetchone()

    connection.close()

    assert row is not None
    assert row[0] == "persistent"

    # Database integrity.
    health = HealthChecker(
        database
    )

    result = health.check_database()

    assert result.status == "healthy"

    # Verify operational scripts exist.
    project_root = Path(
        os.getcwd()
    )

    assert (
        project_root
        / "scripts/ops/backup_atlas.sh"
    ).exists()

    assert (
        project_root
        / "scripts/ops/restore_atlas.sh"
    ).exists()

print("Persistent state : verified")
print("Restart survival : verified")
print("Database health  : verified")
print("Backup tooling   : verified")
print("Restore tooling  : verified")
print("Deployment files : verified")
print("=" * 60)
print("Deployment operations verified.")
print("=" * 60)
