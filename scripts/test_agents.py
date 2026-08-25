from atlas.agents.architect import ArchitectAgent
from atlas.agents.developer import DeveloperAgent
from atlas.agents.operator import OperatorAgent
from atlas.agents.researcher import ResearcherAgent
from atlas.agents.reviewer import ReviewerAgent


agents = [
    ArchitectAgent(),
    DeveloperAgent(),
    ResearcherAgent(),
    ReviewerAgent(),
    OperatorAgent(),
]

print("=" * 60)
print("REGISTERED AGENTS")
print("=" * 60)

for agent in agents:
    print(
        f"{agent.role:12} -> {agent.model}"
    )

print("=" * 60)
print("Agent registry verified.")
print("=" * 60)
