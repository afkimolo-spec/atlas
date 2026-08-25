from atlas.models.router import ModelRouter


router = ModelRouter()

print("=" * 60)
print("MODEL ROUTER")
print("=" * 60)

print(router.engineering.endpoint)
print(router.research.endpoint)
print(router.completion.endpoint)
print(router.embeddings.endpoint)

print("=" * 60)

assert router.get("engineering").endpoint == "http://localhost:8002/v1"
assert router.get("research").endpoint == "http://localhost:8003/v1"
assert router.get("completion").endpoint == "http://localhost:8001/v1"
assert router.get("embeddings").endpoint == "http://localhost:8000/v1"

print("Router operational.")
print("=" * 60)
