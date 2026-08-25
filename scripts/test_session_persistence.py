from __future__ import annotations

import tempfile
from pathlib import Path

from atlas.core.session import Session
from atlas.memory.history import HistoryStore


print("=" * 60)
print("ATLAS SESSION PERSISTENCE")
print("=" * 60)

with tempfile.TemporaryDirectory() as tmp:
    database = Path(tmp) / "atlas.db"

    # Create session.
    session = Session()
    session.start("Session persistence verification")

    # Persist session history.
    history = HistoryStore(database)

    history.add(
        session_id=session.id,
        role="system",
        content="Session started",
    )

    history.add(
        session_id=session.id,
        role="user",
        content=session.task,
    )

    # Verify persisted data is available from a new store instance.
    restored_history = HistoryStore(database)

    messages = restored_history.list(
        session_id=session.id,
    )

    assert len(messages) == 2
    assert messages[0]["role"] == "system"
    assert messages[1]["role"] == "user"
    assert messages[1]["content"] == session.task

    # Verify session lifecycle remains deterministic.
    session.finish()

    assert session.status == "completed"

    print(f"Session ID       : {session.id}")
    print(f"Session status   : {session.status}")
    print(f"Persisted records: {len(messages)}")
    print("=" * 60)
    print("Session persistence verified.")
    print("=" * 60)
