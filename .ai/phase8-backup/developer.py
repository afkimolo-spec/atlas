from atlas.agents.base import BaseAgent


class DeveloperAgent(BaseAgent):

    def __init__(self):

        super().__init__(
            role="developer",
            prompt_file="system.md",
            model="engineering",
        )
