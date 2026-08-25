from atlas.core.client import AtlasClient

client = AtlasClient()

print("=" * 60)
print("ENGINEERING")
print("=" * 60)

print(
    client.chat(
        "engineering",
        "Reply with exactly: Engineering online."
    )
)

print("=" * 60)
print("RESEARCH")
print("=" * 60)

print(
    client.chat(
        "research",
        "Reply with exactly: Research online."
    )
)

print("=" * 60)
print("COMPLETION")
print("=" * 60)

print(
    client.chat(
        "completion",
        "Reply with exactly: Completion online."
    )
)

print("=" * 60)
print("AtlasClient verified.")
print("=" * 60)
