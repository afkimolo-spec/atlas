from atlas.memory.vector import EmbeddingClient

print("=" * 60)
print("EMBEDDING CLIENT")
print("=" * 60)

client = EmbeddingClient()

vector = client.embed("Atlas Engineering Platform")

print(f"Vector Length : {len(vector)}")
print(f"Dimensions    : {client.dimensions()}")

print("=" * 60)
print("Embedding client operational.")
print("=" * 60)
