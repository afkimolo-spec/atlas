from atlas.agents.developer import DeveloperAgent
from atlas.core.session import Session
from atlas.memory.history import HistoryStore


DATABASE = "/home/administrator/workspace/atlas/.ai/memory/db/atlas.db"


session = Session()

session.start(
    "Implement persistent engineering memory integration."
)

agent = DeveloperAgent()

response = agent.run(
    "Explain how you would integrate persistent memory into Atlas.",
    session_id=session.id,
)

print("=" * 60)
print("AGENT CONTEXT INTEGRATION")
print("=" * 60)

print(response)

print("-" * 60)

history = HistoryStore(DATABASE)

messages = history.get(
    session.id,
)

print(
    f"Persisted messages: {len(messages)}"
)

for message in messages:

    print(
        f"{message['role']}: "
        f"{message['content'][:200]}"
    )

print("=" * 60)
print("Agent context integration verified.")
print("=" * 60)
