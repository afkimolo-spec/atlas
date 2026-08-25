from atlas.memory.knowledge import KnowledgeDocument

doc = KnowledgeDocument(
    id="architecture",
    title="Atlas Architecture",
    source="docs/engineering/architecture.md",
    content="Atlas uses multiple local language models.",
    tags=["architecture", "design"],
)

print("=" * 60)
print("KNOWLEDGE DOCUMENT")
print("=" * 60)

print(doc.id)
print(doc.title)
print(doc.source)
print(doc.tags)
print(doc.words)
print(doc.size)

print("=" * 60)
print("Knowledge document verified.")
print("=" * 60)
