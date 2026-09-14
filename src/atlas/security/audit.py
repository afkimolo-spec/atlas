from __future__ import annotations
from atlas.paths import ROOT

import os

import json
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


DATABASE = ROOT / ".ai" / "memory" / "db" / "atlas.db"


@dataclass(frozen=True, slots=True)
class AuditEvent:
    actor: str
    action: str
    resource: str
    outcome: str
    detail: str = ""
    metadata: dict[str, Any] | None = None


class AuditStore:
    """
    Append-only security audit log.

    Security decisions are persisted independently from execution
    state and are queryable after restart.
    """

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

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(
            self.database,
            timeout=30.0,
        )

        connection.row_factory = sqlite3.Row

        connection.execute(
            "PRAGMA busy_timeout = 30000"
        )

        connection.execute(
            "PRAGMA journal_mode = WAL"
        )

        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS security_audit (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    actor TEXT NOT NULL,
                    action TEXT NOT NULL,
                    resource TEXT NOT NULL,
                    outcome TEXT NOT NULL,
                    detail TEXT NOT NULL DEFAULT '',
                    metadata TEXT NOT NULL DEFAULT '{}',
                    created_at TEXT NOT NULL
                )
                """
            )

            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS
                idx_security_audit_actor
                ON security_audit(actor, id)
                """
            )

            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS
                idx_security_audit_action
                ON security_audit(action, outcome, id)
                """
            )

            connection.commit()

    def record(
        self,
        event: AuditEvent,
    ) -> int:
        if not event.actor.strip():
            raise ValueError(
                "Audit actor cannot be empty."
            )

        if not event.action.strip():
            raise ValueError(
                "Audit action cannot be empty."
            )

        if not event.resource.strip():
            raise ValueError(
                "Audit resource cannot be empty."
            )

        if not event.outcome.strip():
            raise ValueError(
                "Audit outcome cannot be empty."
            )

        with self._connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO security_audit (
                    actor,
                    action,
                    resource,
                    outcome,
                    detail,
                    metadata,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event.actor,
                    event.action,
                    event.resource,
                    event.outcome,
                    event.detail,
                    json.dumps(
                        event.metadata or {},
                        ensure_ascii=False,
                    ),
                    datetime.now(UTC).isoformat(),
                ),
            )

            connection.commit()

            return int(cursor.lastrowid)

    def list(
        self,
        *,
        actor: str | None = None,
        action: str | None = None,
        outcome: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        if limit <= 0:
            raise ValueError(
                "limit must be greater than zero."
            )

        clauses = []
        parameters: list[Any] = []

        if actor is not None:
            clauses.append("actor = ?")
            parameters.append(actor)

        if action is not None:
            clauses.append("action = ?")
            parameters.append(action)

        if outcome is not None:
            clauses.append("outcome = ?")
            parameters.append(outcome)

        where = ""

        if clauses:
            where = (
                "WHERE " + " AND ".join(clauses)
            )

        parameters.append(limit)

        with self._connect() as connection:
            rows = connection.execute(
                f"""
                SELECT
                    id,
                    actor,
                    action,
                    resource,
                    outcome,
                    detail,
                    metadata,
                    created_at
                FROM security_audit
                {where}
                ORDER BY id DESC
                LIMIT ?
                """,
                parameters,
            ).fetchall()

        results = []

        for row in rows:
            result = dict(row)

            result["metadata"] = json.loads(
                result["metadata"] or "{}"
            )

            results.append(result)

        return results

    def count(
        self,
        *,
        outcome: str | None = None,
    ) -> int:
        if outcome is None:
            query = (
                "SELECT COUNT(*) AS count "
                "FROM security_audit"
            )
            parameters = ()
        else:
            query = (
                "SELECT COUNT(*) AS count "
                "FROM security_audit "
                "WHERE outcome = ?"
            )
            parameters = (outcome,)

        with self._connect() as connection:
            row = connection.execute(
                query,
                parameters,
            ).fetchone()

        return int(row["count"])
