from pathlib import Path
from tempfile import TemporaryDirectory

from atlas.memory.index import KnowledgeIndex
from atlas.memory.knowledge import KnowledgeDocument


print("=" * 60)
print("KNOWLEDGE INDEX")
print("=" * 60)


with TemporaryDirectory() as directory:
    database = Path(directory) / "knowledge.db"

    index = KnowledgeIndex(
        database=database,
    )

    documents = [
        KnowledgeDocument(
            id="atlas-architecture",
            title="Atlas Architecture",
            source="docs/engineering/architecture.md",
            content=(
                "Atlas is a local-first autonomous engineering "
                "platform using specialized AI agents, workflows, "
                "model routing, persistent memory, and semantic "
                "knowledge retrieval."
            ),
            tags=[
                "architecture",
                "atlas",
                "agents",
            ],
        ),
        KnowledgeDocument(
            id="mysql-replication",
            title="MySQL Replication",
            source="docs/engineering/mysql.md",
            content=(
                "MySQL replication uses GTID-based replication "
                "between production and replica database servers."
            ),
            tags=[
                "mysql",
                "database",
                "replication",
            ],
        ),
        KnowledgeDocument(
            id="python-development",
            title="Python Development",
            source="docs/engineering/python.md",
            content=(
                "Atlas Python components use typed interfaces, "
                "Pydantic configuration models, HTTP clients, "
                "and automated tests."
            ),
            tags=[
                "python",
                "development",
            ],
        ),
    ]

    for document in documents:
        index.add(document)

    print(f"Documents : {index.count()}")

    results = index.search(
        "How is Atlas structured?",
        limit=3,
    )

    print("------------------------------------------------------------")
    print("SEARCH RESULTS")
    print("------------------------------------------------------------")

    for document, score in results:
        print(
            f"{score:.4f} | "
            f"{document.id} | "
            f"{document.title}"
        )

    assert index.count() == 3

    assert results

    assert results[0][0].id == "atlas-architecture"

    retrieved = index.get(
        "atlas-architecture"
    )

    assert retrieved is not None
    assert retrieved.title == "Atlas Architecture"

    index.remove(
        "python-development"
    )

    assert index.count() == 2


print("=" * 60)
print("Knowledge index verified.")
print("=" * 60)
