from __future__ import annotations

from atlas.agents.base import BaseAgent


class ArchitectAgent(BaseAgent):
    """
    Atlas autonomous architecture agent.

    Autonomous architecture is part of the execution-critical lifecycle,
    so it uses the engineering model for bounded, actionable design work.

    The dedicated research model remains available through explicit
    deep-research workflows rather than being required for every plan.
    """

    MODEL_MAX_TOKENS = 256

    def __init__(self) -> None:
        super().__init__(
            role="architect",
            prompt_file="architect.md",
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
