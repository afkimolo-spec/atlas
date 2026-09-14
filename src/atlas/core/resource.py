from __future__ import annotations
from atlas.paths import ROOT

import os

import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import IntEnum
from pathlib import Path
from threading import Lock


DATABASE = ROOT / ".ai" / "memory" / "db" / "atlas.db"


class ResourcePriority(IntEnum):
    LOW = 10
    NORMAL = 50
    HIGH = 75
    CRITICAL = 100


class ResourceError(RuntimeError):
    """Base resource-management error."""


class ResourceNotFoundError(ResourceError):
    """Requested resource does not exist."""


class ResourceConflictError(ResourceError):
    """Requested resource cannot currently be acquired."""


class ResourceOwnershipError(ResourceError):
    """Resource ownership operation is invalid."""


@dataclass(frozen=True, slots=True)
class Resource:
    name: str
    capacity: int
    available: int


@dataclass(frozen=True, slots=True)
class ResourceLease:
    resource: str
    owner: str
    units: int
    priority: ResourcePriority
    acquired_at: datetime
    expires_at: datetime | None = None

    @property
    def expired(self) -> bool:
        if self.expires_at is None:
            return False

        return datetime.now(UTC) >= self.expires_at


class ResourceManager:
    """
    Persistent, cross-process resource manager.

    SQLite transactions provide atomic allocation decisions across
    independent Atlas processes/workers.

    A resource has finite capacity. Each acquisition creates a lease.
    Leases may optionally expire and are reclaimed automatically.

    Resources:
        resource name -> finite capacity

    Leases:
        resource + owner + units + priority + expiration

    Execution locks:
        special exclusive locks associated with execution IDs.
    """

    _schema_lock = Lock()

    def __init__(
        self,
        database: str | Path = DATABASE,
    ) -> None:
        self.database = Path(database)

        self.database.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        self._initialize()

    # ------------------------------------------------------------------
    # DATABASE
    # ------------------------------------------------------------------

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(
            self.database,
            timeout=30.0,
            isolation_level=None,
        )

        connection.row_factory = sqlite3.Row

        connection.execute(
            "PRAGMA busy_timeout = 30000"
        )

        connection.execute(
            "PRAGMA journal_mode = WAL"
        )

        connection.execute(
            "PRAGMA foreign_keys = ON"
        )

        return connection

    def _initialize(self) -> None:
        with self._schema_lock:
            with self._connect() as connection:
                connection.executescript(
                    """
                    CREATE TABLE IF NOT EXISTS resources (
                        name TEXT PRIMARY KEY,
                        capacity INTEGER NOT NULL,
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL,
                        CHECK (capacity > 0)
                    );

                    CREATE TABLE IF NOT EXISTS resource_leases (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        resource TEXT NOT NULL,
                        owner TEXT NOT NULL,
                        units INTEGER NOT NULL,
                        priority INTEGER NOT NULL,
                        acquired_at TEXT NOT NULL,
                        expires_at TEXT,
                        FOREIGN KEY(resource)
                            REFERENCES resources(name)
                            ON DELETE CASCADE,
                        CHECK (units > 0)
                    );

                    CREATE INDEX IF NOT EXISTS
                    idx_resource_leases_resource
                    ON resource_leases(resource);

                    CREATE INDEX IF NOT EXISTS
                    idx_resource_leases_owner
                    ON resource_leases(owner);

                    CREATE INDEX IF NOT EXISTS
                    idx_resource_leases_expiry
                    ON resource_leases(expires_at);

                    CREATE TABLE IF NOT EXISTS execution_locks (
                        execution_id TEXT PRIMARY KEY,
                        owner TEXT NOT NULL,
                        acquired_at TEXT NOT NULL,
                        expires_at TEXT
                    );

                    CREATE INDEX IF NOT EXISTS
                    idx_execution_locks_expiry
                    ON execution_locks(expires_at);
                    """
                )

    # ------------------------------------------------------------------
    # INTERNAL HELPERS
    # ------------------------------------------------------------------

    @staticmethod
    def _now() -> datetime:
        return datetime.now(UTC)

    @staticmethod
    def _parse_datetime(
        value: str,
    ) -> datetime:
        return datetime.fromisoformat(value)

    @staticmethod
    def _validate_name(
        value: str,
        label: str,
    ) -> str:
        value = value.strip()

        if not value:
            raise ValueError(
                f"{label} cannot be empty."
            )

        return value

    def _reclaim_expired(
        self,
        connection: sqlite3.Connection,
    ) -> None:
        now = self._now().isoformat()

        connection.execute(
            """
            DELETE FROM resource_leases
            WHERE expires_at IS NOT NULL
              AND expires_at <= ?
            """,
            (now,),
        )

        connection.execute(
            """
            DELETE FROM execution_locks
            WHERE expires_at IS NOT NULL
              AND expires_at <= ?
            """,
            (now,),
        )

    # ------------------------------------------------------------------
    # RESOURCE REGISTRY
    # ------------------------------------------------------------------

    def register(
        self,
        name: str,
        *,
        capacity: int = 1,
        replace: bool = False,
    ) -> Resource:

        name = self._validate_name(
            name,
            "Resource name",
        )

        if capacity < 1:
            raise ValueError(
                "Resource capacity must be at least 1."
            )

        now = self._now().isoformat()

        with self._connect() as connection:
            connection.execute(
                "BEGIN IMMEDIATE"
            )

            self._reclaim_expired(connection)

            row = connection.execute(
                """
                SELECT capacity
                FROM resources
                WHERE name = ?
                """,
                (name,),
            ).fetchone()

            if row is not None and not replace:
                connection.rollback()

                raise ResourceError(
                    f"Resource already registered: {name}"
                )

            if row is not None:
                active = connection.execute(
                    """
                    SELECT COALESCE(SUM(units), 0) AS allocated
                    FROM resource_leases
                    WHERE resource = ?
                    """,
                    (name,),
                ).fetchone()

                allocated = int(
                    active["allocated"]
                )

                if allocated > capacity:
                    connection.rollback()

                    raise ResourceConflictError(
                        f"Cannot reduce capacity for '{name}' "
                        f"below current allocation "
                        f"({allocated})."
                    )

                connection.execute(
                    """
                    UPDATE resources
                    SET
                        capacity = ?,
                        updated_at = ?
                    WHERE name = ?
                    """,
                    (
                        capacity,
                        now,
                        name,
                    ),
                )

            else:
                connection.execute(
                    """
                    INSERT INTO resources (
                        name,
                        capacity,
                        created_at,
                        updated_at
                    )
                    VALUES (?, ?, ?, ?)
                    """,
                    (
                        name,
                        capacity,
                        now,
                        now,
                    ),
                )

            connection.commit()

            allocated = connection.execute(
                """
                SELECT COALESCE(SUM(units), 0) AS allocated
                FROM resource_leases
                WHERE resource = ?
                """,
                (name,),
            ).fetchone()

        return Resource(
            name=name,
            capacity=capacity,
            available=(
                capacity
                - int(allocated["allocated"])
            ),
        )

    def get(
        self,
        name: str,
    ) -> Resource:

        name = self._validate_name(
            name,
            "Resource name",
        )

        with self._connect() as connection:
            self._reclaim_expired(connection)

            row = connection.execute(
                """
                SELECT
                    r.name,
                    r.capacity,
                    COALESCE(
                        SUM(l.units),
                        0
                    ) AS allocated
                FROM resources r
                LEFT JOIN resource_leases l
                    ON l.resource = r.name
                WHERE r.name = ?
                GROUP BY r.name, r.capacity
                """,
                (name,),
            ).fetchone()

        if row is None:
            raise ResourceNotFoundError(
                f"Unknown resource: {name}"
            )

        allocated = int(
            row["allocated"]
        )

        return Resource(
            name=row["name"],
            capacity=int(row["capacity"]),
            available=(
                int(row["capacity"])
                - allocated
            ),
        )

    def list(
        self,
    ) -> list[Resource]:

        with self._connect() as connection:
            self._reclaim_expired(connection)

            rows = connection.execute(
                """
                SELECT
                    r.name,
                    r.capacity,
                    COALESCE(
                        SUM(l.units),
                        0
                    ) AS allocated
                FROM resources r
                LEFT JOIN resource_leases l
                    ON l.resource = r.name
                GROUP BY r.name, r.capacity
                ORDER BY r.name
                """
            ).fetchall()

        return [
            Resource(
                name=row["name"],
                capacity=int(row["capacity"]),
                available=(
                    int(row["capacity"])
                    - int(row["allocated"])
                ),
            )
            for row in rows
        ]

    # ------------------------------------------------------------------
    # ALLOCATION
    # ------------------------------------------------------------------

    def available(
        self,
        name: str,
    ) -> int:
        return self.get(name).available

    def can_acquire(
        self,
        name: str,
        *,
        units: int = 1,
    ) -> bool:

        if units < 1:
            raise ValueError(
                "units must be at least 1."
            )

        return self.available(name) >= units

    def acquire(
        self,
        name: str,
        owner: str,
        *,
        units: int = 1,
        priority: ResourcePriority = ResourcePriority.NORMAL,
        ttl_seconds: float | None = None,
    ) -> ResourceLease:

        name = self._validate_name(
            name,
            "Resource name",
        )

        owner = self._validate_name(
            owner,
            "Resource owner",
        )

        if units < 1:
            raise ValueError(
                "units must be at least 1."
            )

        if ttl_seconds is not None and ttl_seconds <= 0:
            raise ValueError(
                "ttl_seconds must be greater than zero."
            )

        if not isinstance(priority, ResourcePriority):
            priority = ResourcePriority(
                int(priority)
            )

        now = self._now()

        expires_at = (
            now + timedelta(
                seconds=ttl_seconds
            )
            if ttl_seconds is not None
            else None
        )

        with self._connect() as connection:
            connection.execute(
                "BEGIN IMMEDIATE"
            )

            self._reclaim_expired(connection)

            row = connection.execute(
                """
                SELECT capacity
                FROM resources
                WHERE name = ?
                """,
                (name,),
            ).fetchone()

            if row is None:
                connection.rollback()

                raise ResourceNotFoundError(
                    f"Unknown resource: {name}"
                )

            allocated_row = connection.execute(
                """
                SELECT COALESCE(
                    SUM(units),
                    0
                ) AS allocated
                FROM resource_leases
                WHERE resource = ?
                """,
                (name,),
            ).fetchone()

            allocated = int(
                allocated_row["allocated"]
            )

            capacity = int(
                row["capacity"]
            )

            available = capacity - allocated

            if available < units:
                connection.rollback()

                raise ResourceConflictError(
                    f"Resource '{name}' unavailable for "
                    f"owner '{owner}': requested {units}, "
                    f"available {available}."
                )

            connection.execute(
                """
                INSERT INTO resource_leases (
                    resource,
                    owner,
                    units,
                    priority,
                    acquired_at,
                    expires_at
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    name,
                    owner,
                    units,
                    int(priority),
                    now.isoformat(),
                    (
                        expires_at.isoformat()
                        if expires_at
                        else None
                    ),
                ),
            )

            connection.commit()

        return ResourceLease(
            resource=name,
            owner=owner,
            units=units,
            priority=priority,
            acquired_at=now,
            expires_at=expires_at,
        )

    def release(
        self,
        lease: ResourceLease,
    ) -> None:

        with self._connect() as connection:
            connection.execute(
                "BEGIN IMMEDIATE"
            )

            cursor = connection.execute(
                """
                DELETE FROM resource_leases
                WHERE resource = ?
                  AND owner = ?
                  AND units = ?
                  AND priority = ?
                  AND acquired_at = ?
                """,
                (
                    lease.resource,
                    lease.owner,
                    lease.units,
                    int(lease.priority),
                    lease.acquired_at.isoformat(),
                ),
            )

            if cursor.rowcount != 1:
                connection.rollback()

                raise ResourceOwnershipError(
                    "Resource lease is no longer active "
                    "or is not owned by the caller."
                )

            connection.commit()

    def release_owner(
        self,
        owner: str,
    ) -> int:

        owner = self._validate_name(
            owner,
            "Resource owner",
        )

        with self._connect() as connection:
            connection.execute(
                "BEGIN IMMEDIATE"
            )

            cursor = connection.execute(
                """
                DELETE FROM resource_leases
                WHERE owner = ?
                """,
                (owner,),
            )

            connection.commit()

            return cursor.rowcount

    def leases(
        self,
        *,
        resource: str | None = None,
        owner: str | None = None,
    ) -> list[ResourceLease]:

        clauses = []
        parameters: list[str] = []

        if resource is not None:
            resource = self._validate_name(
                resource,
                "Resource name",
            )

            clauses.append(
                "resource = ?"
            )
            parameters.append(resource)

        if owner is not None:
            owner = self._validate_name(
                owner,
                "Resource owner",
            )

            clauses.append(
                "owner = ?"
            )
            parameters.append(owner)

        where = ""

        if clauses:
            where = (
                "WHERE "
                + " AND ".join(clauses)
            )

        with self._connect() as connection:
            self._reclaim_expired(connection)

            rows = connection.execute(
                f"""
                SELECT
                    resource,
                    owner,
                    units,
                    priority,
                    acquired_at,
                    expires_at
                FROM resource_leases
                {where}
                ORDER BY
                    priority DESC,
                    acquired_at ASC
                """,
                parameters,
            ).fetchall()

        return [
            ResourceLease(
                resource=row["resource"],
                owner=row["owner"],
                units=int(row["units"]),
                priority=ResourcePriority(
                    int(row["priority"])
                ),
                acquired_at=self._parse_datetime(
                    row["acquired_at"]
                ),
                expires_at=(
                    self._parse_datetime(
                        row["expires_at"]
                    )
                    if row["expires_at"]
                    else None
                ),
            )
            for row in rows
        ]

    # ------------------------------------------------------------------
    # EXECUTION LOCKING
    # ------------------------------------------------------------------

    def lock_execution(
        self,
        execution_id: str,
        owner: str,
        *,
        ttl_seconds: float | None = None,
    ) -> None:

        execution_id = self._validate_name(
            execution_id,
            "execution_id",
        )

        owner = self._validate_name(
            owner,
            "lock owner",
        )

        if ttl_seconds is not None and ttl_seconds <= 0:
            raise ValueError(
                "ttl_seconds must be greater than zero."
            )

        now = self._now()

        expires_at = (
            now + timedelta(
                seconds=ttl_seconds
            )
            if ttl_seconds is not None
            else None
        )

        with self._connect() as connection:
            connection.execute(
                "BEGIN IMMEDIATE"
            )

            self._reclaim_expired(connection)

            row = connection.execute(
                """
                SELECT owner
                FROM execution_locks
                WHERE execution_id = ?
                """,
                (execution_id,),
            ).fetchone()

            if row is not None:
                existing_owner = row["owner"]

                if existing_owner != owner:
                    connection.rollback()

                    raise ResourceConflictError(
                        f"Execution '{execution_id}' "
                        f"is locked by '{existing_owner}'."
                    )

                connection.execute(
                    """
                    UPDATE execution_locks
                    SET
                        acquired_at = ?,
                        expires_at = ?
                    WHERE execution_id = ?
                    """,
                    (
                        now.isoformat(),
                        (
                            expires_at.isoformat()
                            if expires_at
                            else None
                        ),
                        execution_id,
                    ),
                )

            else:
                connection.execute(
                    """
                    INSERT INTO execution_locks (
                        execution_id,
                        owner,
                        acquired_at,
                        expires_at
                    )
                    VALUES (?, ?, ?, ?)
                    """,
                    (
                        execution_id,
                        owner,
                        now.isoformat(),
                        (
                            expires_at.isoformat()
                            if expires_at
                            else None
                        ),
                    ),
                )

            connection.commit()

    def unlock_execution(
        self,
        execution_id: str,
        owner: str,
    ) -> None:

        execution_id = self._validate_name(
            execution_id,
            "execution_id",
        )

        owner = self._validate_name(
            owner,
            "lock owner",
        )

        with self._connect() as connection:
            connection.execute(
                "BEGIN IMMEDIATE"
            )

            row = connection.execute(
                """
                SELECT owner
                FROM execution_locks
                WHERE execution_id = ?
                """,
                (execution_id,),
            ).fetchone()

            if row is None:
                connection.rollback()

                return

            if row["owner"] != owner:
                connection.rollback()

                raise ResourceOwnershipError(
                    f"Execution '{execution_id}' is owned "
                    f"by '{row['owner']}', not '{owner}'."
                )

            connection.execute(
                """
                DELETE FROM execution_locks
                WHERE execution_id = ?
                """,
                (execution_id,),
            )

            connection.commit()

    def execution_lock_owner(
        self,
        execution_id: str,
    ) -> str | None:

        execution_id = self._validate_name(
            execution_id,
            "execution_id",
        )

        with self._connect() as connection:
            self._reclaim_expired(connection)

            row = connection.execute(
                """
                SELECT owner
                FROM execution_locks
                WHERE execution_id = ?
                """,
                (execution_id,),
            ).fetchone()

        if row is None:
            return None

        return str(row["owner"])

    def recover_expired(self) -> int:
        with self._connect() as connection:
            connection.execute(
                "BEGIN IMMEDIATE"
            )

            before = (
                connection.execute(
                    """
                    SELECT
                        (
                            SELECT COUNT(*)
                            FROM resource_leases
                            WHERE expires_at IS NOT NULL
                              AND expires_at <= ?
                        )
                        +
                        (
                            SELECT COUNT(*)
                            FROM execution_locks
                            WHERE expires_at IS NOT NULL
                              AND expires_at <= ?
                        ) AS count
                    """,
                    (
                        self._now().isoformat(),
                        self._now().isoformat(),
                    ),
                ).fetchone()["count"]
            )

            self._reclaim_expired(
                connection
            )

            connection.commit()

            return int(before)

    # ------------------------------------------------------------------
    # SNAPSHOT
    # ------------------------------------------------------------------

    def snapshot(self) -> dict:
        resources = self.list()
        leases = self.leases()

        return {
            "resources": [
                {
                    "name": resource.name,
                    "capacity": resource.capacity,
                    "available": resource.available,
                }
                for resource in resources
            ],
            "leases": [
                {
                    "resource": lease.resource,
                    "owner": lease.owner,
                    "units": lease.units,
                    "priority": int(
                        lease.priority
                    ),
                    "acquired_at": lease.acquired_at.isoformat(),
                    "expires_at": (
                        lease.expires_at.isoformat()
                        if lease.expires_at
                        else None
                    ),
                }
                for lease in leases
            ],
        }
