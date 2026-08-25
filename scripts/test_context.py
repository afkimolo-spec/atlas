from atlas.core.context import ContextManager


context = ContextManager.create()

session_id = "context-test-session"

context.history.clear(session_id)

context.history.add(
    session_id=session_id,
    role="user",
    content="Build Atlas persistent engineering memory.",
)

context.history.add(
    session_id=session_id,
    role="assistant",
    content="Persistent memory is operational.",
)

result = context.build(
    session_id=session_id,
    task="How should Atlas use persistent engineering memory?",
)

print("=" * 60)
print("ATLAS CONTEXT")
print("=" * 60)

print(result)

print("=" * 60)

assert "## Current Task" in result

assert (
    "How should Atlas use persistent engineering memory?"
    in result
)

assert "## Session History" in result

assert "Build Atlas persistent engineering memory." in result

assert "Persistent memory is operational." in result

print("Context manager verified.")
print("=" * 60)
