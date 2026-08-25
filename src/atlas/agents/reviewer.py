from atlas.agents.base import BaseAgent


class ReviewerAgent(BaseAgent):

    def __init__(self):

        super().__init__(
            role="reviewer",
            prompt_file="reviewer.md",
            model="research",
        )
