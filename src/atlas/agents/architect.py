from atlas.agents.base import BaseAgent


class ArchitectAgent(BaseAgent):

    def __init__(self):

        super().__init__(
            role="architect",
            prompt_file="architect.md",
            model="research",
        )
