from atlas.agents.base import BaseAgent


class OperatorAgent(BaseAgent):

    def __init__(self):

        super().__init__(
            role="operator",
            prompt_file="operator.md",
            model="engineering",
        )
