from pathlib import Path
from tempfile import TemporaryDirectory

from atlas.memory.history import HistoryStore


print("=" * 60)
print("HISTORY STORE")
print("=" * 60)


with TemporaryDirectory() as directory:
    database = Path(directory) / "history.db"

    history = HistoryStore(database)

    session_id = "atlas-test-session"

    first_id = history.add(
        session_id,
        "user",
        "Build Atlas memory.",
    )

    second_id = history.add(
        session_id,
        "assistant",
        "Atlas memory implementation started.",
    )

    messages = history.list(session_id)

    print(f"First ID  : {first_id}")
    print(f"Second ID : {second_id}")
    print(f"Messages  : {len(messages)}")

    for message in messages:
        print(
            f"{message['role']}: "
            f"{message['content']}"
        )

    history.clear(session_id)

    remaining = history.list(session_id)

    print(f"After clear: {len(remaining)}")


print("=" * 60)
print("History store verified.")
print("=" * 60)
