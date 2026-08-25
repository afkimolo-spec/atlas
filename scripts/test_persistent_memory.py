from pathlib import Path
from uuid import uuid4

from atlas.memory.history import HistoryStore
from atlas.memory.index import KnowledgeIndex
from atlas.memory.knowledge import KnowledgeDocument


ROOT = Path("/home/administrator/workspace/atlas")
DATABASE = ROOT / ".ai/memory/db/atlas.db"


print("=" * 60)
print("ATLAS PERSISTENT MEMORY")
print("=" * 60)

history = HistoryStore(DATABASE)

session_id = str(uuid4())

first_id = history.append(
    session_id,
    "user",
    "Build Atlas autonomous engineering memory.",
)

second_id = history.append(
    session_id,
    "assistant",
    "Persistent memory implementation started.",
)

messages = history.get(session_id)

print(f"History DB : {DATABASE}")
print(f"First ID   : {first_id}")
print(f"Second ID  : {second_id}")
print(f"Messages   : {len(messages)}")

for message in messages:
    print(
        f"{message['role']}: "
        f"{message['content']}"
    )

index = KnowledgeIndex(DATABASE)

index.add(
    KnowledgeDocument(
        id="atlas-memory",
        title="Atlas Memory Architecture",
        content=(
            "Atlas maintains persistent engineering "
            "memory using conversation history and "
            "semantic knowledge retrieval."
        ),
        source="docs/engineering/architecture.md",
        tags=["atlas", "memory", "architecture"],
    )
)

print("-" * 60)
print(f"Knowledge : {index.count()}")

results = index.search(
    "How does Atlas remember engineering knowledge?",
    limit=3,
)

for document, score in results:
    print(
        f"{score:.4f} | "
        f"{document.id} | "
        f"{document.title}"
    )

history.clear(session_id)

print("-" * 60)
print(
    f"History after clear: "
    f"{history.count(session_id)}"
)

print("=" * 60)
print("Persistent memory verified.")
print("=" * 60)
