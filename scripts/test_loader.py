from atlas.config.loader import LOGGING
from atlas.config.loader import MODELS
from atlas.config.loader import SECURITY
from atlas.config.loader import WORKSPACE

print("=" * 60)
print("ATLAS CONFIGURATION")
print("=" * 60)

print("Workspace :", WORKSPACE.name)
print("Root      :", WORKSPACE.root)
print("Branch    :", WORKSPACE.git.branch)

print()

print("Engineering:", MODELS.engineering.endpoint)
print("Research   :", MODELS.research.endpoint)
print("Completion :", MODELS.completion.endpoint)
print("Embeddings :", MODELS.embeddings.endpoint)

print()

print("Log Level :", LOGGING.level)
print("Network   :", SECURITY.allow_network)

print("=" * 60)
