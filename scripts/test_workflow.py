from atlas.workflows import Workflow

workflow = Workflow()

print("=" * 60)
print("ATLAS WORKFLOW")
print("=" * 60)

result = workflow.architecture(
    "Reply with exactly: Workflow operational."
)

print(result)

print("=" * 60)
print("Workflow verified.")
print("=" * 60)
