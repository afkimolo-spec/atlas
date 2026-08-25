from atlas.config.loader import MODELS
from atlas.core.client import LlamaClient

client = LlamaClient(
    endpoint=MODELS.engineering.endpoint,
    model=MODELS.engineering.model,
)

print("=" * 60)
print("ENGINEERING MODEL")
print("=" * 60)

models = client.models()

print(models["data"][0]["id"])

print("=" * 60)

reply = client.chat(
    "Reply with exactly: Atlas client operational."
)

print(reply)

print("=" * 60)
