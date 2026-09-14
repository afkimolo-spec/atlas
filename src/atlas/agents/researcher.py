from __future__ import annotations

from atlas.agents.base import BaseAgent


class ResearcherAgent(BaseAgent):
    """
    Atlas research-stage agent.

    Research begins from the supplied task and does not require semantic
    knowledge retrieval or conversational history. The resulting research
    brief is persisted for downstream workflow stages.
    """

    MODEL_MAX_TOKENS = 192

    def __init__(self) -> None:
        super().__init__(
            role="researcher",
            prompt_file="research.md",
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
            knowledge_query=None,
            include_history=False,
            include_knowledge=False,
            persist_history=True,
            temperature=0.0,
            max_tokens=self.MODEL_MAX_TOKENS,
        )
