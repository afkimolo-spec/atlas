from atlas.core.workspace import Workspace

workspace = Workspace()

print("=" * 60)
print("ATLAS WORKSPACE")
print("=" * 60)

print("Root      :", workspace.root)
print("Source    :", workspace.source)
print("Tests     :", workspace.tests)
print("Packages  :", workspace.packages)
print("Docs      :", workspace.docs)
print("Agents    :", workspace.agents)
print("Prompts   :", workspace.prompts)
print("Memory    :", workspace.memory)
print("Workflows :", workspace.workflows)
print("Rules     :", workspace.rules)

print("=" * 60)

assert workspace.source.exists()
assert workspace.tests.exists()
assert workspace.packages.exists()
assert workspace.docs.exists()

print("Workspace verified.")

print("=" * 60)
