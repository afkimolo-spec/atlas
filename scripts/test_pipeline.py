from atlas.workflows import Workflow


workflow = Workflow()

result = workflow.pipeline(
    "Reply with exactly: Pipeline operational.",
    research=False,
    architecture=True,
    development=False,
    review=False,
    operations=False,
)

print("=" * 60)
print("ATLAS MULTI-AGENT PIPELINE")
print("=" * 60)

print("Session :", result.session_id)
print("Status  :", result.status)

print("-" * 60)

for stage, output in result.outputs.items():
    print(f"Stage   : {stage}")
    print(f"Result  : {output}")

print("=" * 60)

assert result.session_id
assert result.status == "completed"

assert "architecture" in result.outputs

assert (
    "Pipeline operational."
    in result.outputs["architecture"]
)

print("Multi-agent pipeline verified.")
print("=" * 60)
