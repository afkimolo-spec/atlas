from __future__ import annotations

from pathlib import Path

from atlas.memory.history import HistoryStore
from atlas.memory.index import KnowledgeIndex


ROOT = Path("/home/administrator/workspace/atlas")
DATABASE = ROOT / ".ai" / "memory" / "db" / "atlas.db"


class ContextManager:
    """
    Builds model-ready execution context from Atlas persistent memory.

    Context is composed from three layers:

        1. Semantic engineering knowledge
        2. Persistent session history
        3. Current task

    KnowledgeIndex.search() contract:

        (KnowledgeDocument, float)

    where the float is the cosine-similarity relevance score.
    """

    def __init__(
        self,
        history: HistoryStore,
        knowledge: KnowledgeIndex,
        *,
        history_limit: int = 20,
        knowledge_limit: int = 5,
    ) -> None:

        if history_limit <= 0:
            raise ValueError(
                "history_limit must be greater than zero"
            )

        if knowledge_limit <= 0:
            raise ValueError(
                "knowledge_limit must be greater than zero"
            )

        self.history = history
        self.knowledge = knowledge

        self.history_limit = history_limit
        self.knowledge_limit = knowledge_limit

    @classmethod
    def create(
        cls,
        database: str | Path = DATABASE,
        *,
        history_limit: int = 20,
        knowledge_limit: int = 5,
    ) -> "ContextManager":
        """
        Construct a ContextManager backed by Atlas persistent memory.
        """

        database = Path(database)

        history = HistoryStore(database)

        knowledge = KnowledgeIndex(database)

        return cls(
            history=history,
            knowledge=knowledge,
            history_limit=history_limit,
            knowledge_limit=knowledge_limit,
        )

    def build(
        self,
        *,
        session_id: str,
        task: str,
    ) -> str:
        """
        Build the complete model-ready context.

        The resulting context is deterministic and contains:

            ## Relevant Engineering Knowledge
            ## Session History
            ## Current Task
        """

        if not session_id.strip():
            raise ValueError(
                "session_id cannot be empty"
            )

        if not task.strip():
            raise ValueError(
                "task cannot be empty"
            )

        sections: list[str] = []

        # ========================================================
        # 1. Semantic engineering knowledge
        # ========================================================

        results = self.knowledge.search(
            task,
            limit=self.knowledge_limit,
        )

        if results:
            sections.append(
                "## Relevant Engineering Knowledge"
            )

            for document, score in results:
                sections.append(
                    "\n"
                    f"### {document.title}\n"
                    f"Source: {document.source}\n"
                    f"Relevance: {float(score):.4f}\n"
                    f"{document.content}"
                )

        # ========================================================
        # 2. Persistent session history
        # ========================================================

        history = self.history.list(
            session_id,
            limit=self.history_limit,
        )

        if history:
            sections.append(
                "\n## Session History"
            )

            for message in history:
                role = message["role"]
                content = message["content"]

                sections.append(
                    f"{role}: {content}"
                )

        # ========================================================
        # 3. Current task
        # ========================================================

        sections.append(
            "\n## Current Task\n"
            f"{task}"
        )

        return "\n".join(sections)
