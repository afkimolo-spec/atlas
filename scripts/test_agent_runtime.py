from atlas.agents.developer import DeveloperAgent
from atlas.core.session import Session


session = Session()

session.start(
    "Verify Atlas agent runtime integration."
)

agent = DeveloperAgent()

result = agent.run(
    "Reply with exactly: Agent runtime operational.",
    session_id=session.id,
)

print("=" * 60)
print("AGENT RUNTIME")
print("=" * 60)

print("Session :", session.id)
print("Agent   :", agent.role)
print("Model   :", agent.model)
print("Result  :", result)

print("=" * 60)

assert "Agent runtime operational." in result

messages = agent.history.list(
    session.id
)

print("Messages:", len(messages))

assert len(messages) == 2

print("=" * 60)
print("Agent runtime verified.")
print("=" * 60)
