from atlas.agents.base import BaseAgent


class ResearcherAgent(BaseAgent):

    def __init__(self):

        super().__init__(
            role="researcher",
            prompt_file="research.md",
            model="research",
        )
