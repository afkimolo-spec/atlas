from __future__ import annotations

from atlas.agents.base import BaseAgent


class ReviewerAgent(BaseAgent):
    """
    Atlas autonomous review agent.

    Review is part of the execution-critical lifecycle and therefore uses
    the engineering model so autonomous plans are not gated by the slower
    dedicated deep-research backend.

    The reviewer receives the persistent session history, which contains
    research, architecture, and development results.
    """

    MODEL_MAX_TOKENS = 256

    def __init__(self) -> None:
        super().__init__(
            role="reviewer",
            prompt_file="reviewer.md",
            model="engineering",
        )

    def run(
        self,
        task: str,
        *,
        session_id: str,
    ) -> str:
        return super().run(
            task,
            session_id=session_id,
            include_history=True,
            include_knowledge=False,
            persist_history=True,
            temperature=0.0,
            max_tokens=self.MODEL_MAX_TOKENS,
        )
