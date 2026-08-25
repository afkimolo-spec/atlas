from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from pathlib import Path


class HistoryStore:
    """
    Persistent conversation history for Atlas sessions.
    """

    def __init__(self, database: str | Path) -> None:
        self.database = Path(database)

        self.database.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database)

        connection.row_factory = sqlite3.Row

        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )

            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS
                idx_messages_session
                ON messages(session_id, id)
                """
            )

            connection.commit()

    def append(
        self,
        session_id: str,
        role: str,
        content: str,
    ) -> int:
        created_at = datetime.now(UTC).isoformat()

        with self._connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO messages (
                    session_id,
                    role,
                    content,
                    created_at
                )
                VALUES (?, ?, ?, ?)
                """,
                (
                    session_id,
                    role,
                    content,
                    created_at,
                ),
            )

            connection.commit()

            return int(cursor.lastrowid)

    def add(
        self,
        session_id: str,
        role: str,
        content: str,
    ) -> int:
        """
        Compatibility alias for append().
        """

        return self.append(
            session_id=session_id,
            role=role,
            content=content,
        )

    def get(
        self,
        session_id: str,
        limit: int = 100,
    ) -> list[dict[str, str]]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT
                    role,
                    content,
                    created_at
                FROM messages
                WHERE session_id = ?
                ORDER BY id ASC
                LIMIT ?
                """,
                (
                    session_id,
                    limit,
                ),
            ).fetchall()

        return [
            {
                "role": row["role"],
                "content": row["content"],
                "created_at": row["created_at"],
            }
            for row in rows
        ]

    def list(
        self,
        session_id: str,
        limit: int = 100,
    ) -> list[dict[str, str]]:
        """
        Compatibility alias for get().
        """

        return self.get(
            session_id=session_id,
            limit=limit,
        )

    def clear(
        self,
        session_id: str,
    ) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                DELETE FROM messages
                WHERE session_id = ?
                """,
                (session_id,),
            )

            connection.commit()

    def count(
        self,
        session_id: str,
    ) -> int:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT COUNT(*) AS count
                FROM messages
                WHERE session_id = ?
                """,
                (session_id,),
            ).fetchone()

        return int(row["count"])
