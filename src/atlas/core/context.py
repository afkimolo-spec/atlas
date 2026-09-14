from __future__ import annotations

from pathlib import Path

from atlas.memory.history import HistoryStore
from atlas.memory.index import KnowledgeIndex


ROOT = Path("/home/administrator/workspace/atlas")
DATABASE = ROOT / ".ai" / "memory" / "db" / "atlas.db"


class ContextManager:
    """
    Builds bounded model-ready context from Atlas persistent memory.

    Context may contain:

        1. Relevant semantic engineering knowledge
        2. Optional persistent session history
        3. Current task

    Callers can independently control knowledge retrieval and history.
    This is important for autonomous control loops and first-stage
    execution where semantic retrieval is unnecessary overhead.
    """

    DEFAULT_HISTORY_LIMIT = 20
    DEFAULT_KNOWLEDGE_LIMIT = 5

    DEFAULT_MAX_CONTEXT_CHARS = 12000
    DEFAULT_MAX_KNOWLEDGE_CHARS = 5000
    DEFAULT_MAX_HISTORY_CHARS = 4000
    DEFAULT_MAX_DOCUMENT_CHARS = 1800

    def __init__(
        self,
        history: HistoryStore,
        knowledge: KnowledgeIndex,
        *,
        history_limit: int = DEFAULT_HISTORY_LIMIT,
        knowledge_limit: int = DEFAULT_KNOWLEDGE_LIMIT,
        max_context_chars: int = DEFAULT_MAX_CONTEXT_CHARS,
        max_knowledge_chars: int = DEFAULT_MAX_KNOWLEDGE_CHARS,
        max_history_chars: int = DEFAULT_MAX_HISTORY_CHARS,
        max_document_chars: int = DEFAULT_MAX_DOCUMENT_CHARS,
    ) -> None:
        if history_limit <= 0:
            raise ValueError(
                "history_limit must be greater than zero."
            )

        if knowledge_limit <= 0:
            raise ValueError(
                "knowledge_limit must be greater than zero."
            )

        for name, value in (
            ("max_context_chars", max_context_chars),
            ("max_knowledge_chars", max_knowledge_chars),
            ("max_history_chars", max_history_chars),
            ("max_document_chars", max_document_chars),
        ):
            if value <= 0:
                raise ValueError(
                    f"{name} must be greater than zero."
                )

        self.history = history
        self.knowledge = knowledge

        self.history_limit = history_limit
        self.knowledge_limit = knowledge_limit

        self.max_context_chars = max_context_chars
        self.max_knowledge_chars = max_knowledge_chars
        self.max_history_chars = max_history_chars
        self.max_document_chars = max_document_chars

    @classmethod
    def create(
        cls,
        database: str | Path = DATABASE,
        *,
        history_limit: int = DEFAULT_HISTORY_LIMIT,
        knowledge_limit: int = DEFAULT_KNOWLEDGE_LIMIT,
        max_context_chars: int = DEFAULT_MAX_CONTEXT_CHARS,
        max_knowledge_chars: int = DEFAULT_MAX_KNOWLEDGE_CHARS,
        max_history_chars: int = DEFAULT_MAX_HISTORY_CHARS,
        max_document_chars: int = DEFAULT_MAX_DOCUMENT_CHARS,
    ) -> "ContextManager":
        database = Path(database)

        history = HistoryStore(database)
        knowledge = KnowledgeIndex(database)

        return cls(
            history=history,
            knowledge=knowledge,
            history_limit=history_limit,
            knowledge_limit=knowledge_limit,
            max_context_chars=max_context_chars,
            max_knowledge_chars=max_knowledge_chars,
            max_history_chars=max_history_chars,
            max_document_chars=max_document_chars,
        )

    @staticmethod
    def _tail(
        value: str,
        limit: int,
    ) -> str:
        if len(value) <= limit:
            return value

        return (
            "[...truncated...]\n"
            + value[-limit:]
        )

    @staticmethod
    def _head(
        value: str,
        limit: int,
    ) -> str:
        if len(value) <= limit:
            return value

        return value[:limit] + "\n[...truncated...]"

    def _append_bounded(
        self,
        sections: list[str],
        section: str,
        *,
        remaining: int,
    ) -> int:
        if remaining <= 0:
            return 0

        bounded = self._head(
            section,
            remaining,
        )

        sections.append(bounded)

        return max(
            0,
            remaining - len(bounded),
        )

    def build(
        self,
        *,
        session_id: str,
        task: str,
        knowledge_query: str | None = None,
        include_history: bool = True,
        include_knowledge: bool = True,
    ) -> str:
        """
        Build bounded context for a model request.

        include_history controls persistent session-history retrieval.

        include_knowledge controls semantic engineering-knowledge
        retrieval independently from history.

        No embedding request is performed when include_knowledge=False.
        """

        if not session_id.strip():
            raise ValueError(
                "session_id cannot be empty."
            )

        if not task.strip():
            raise ValueError(
                "task cannot be empty."
            )

        sections: list[str] = []
        remaining = self.max_context_chars

        # ---------------------------------------------------------
        # 1. Semantic engineering knowledge
        # ---------------------------------------------------------
        if include_knowledge and remaining > 0:
            query = (
                knowledge_query
                if knowledge_query is not None
                else task
            )

            if not query.strip():
                raise ValueError(
                    "knowledge_query cannot be empty."
                )

            results = self.knowledge.search(
                query,
                limit=self.knowledge_limit,
            )

            if results and remaining > 0:
                knowledge_parts = [
                    "## Relevant Engineering Knowledge"
                ]

                knowledge_remaining = min(
                    self.max_knowledge_chars,
                    remaining,
                )

                for document, score in results:
                    if knowledge_remaining <= 0:
                        break

                    content = self._head(
                        document.content,
                        self.max_document_chars,
                    )

                    entry = (
                        f"\n### {document.title}\n"
                        f"Source: {document.source}\n"
                        f"Relevance: {float(score):.4f}\n"
                        f"{content}\n"
                    )

                    bounded = self._head(
                        entry,
                        knowledge_remaining,
                    )

                    knowledge_parts.append(bounded)
                    knowledge_remaining -= len(bounded)

                knowledge_section = "\n".join(
                    knowledge_parts
                )

                remaining = self._append_bounded(
                    sections,
                    knowledge_section,
                    remaining=remaining,
                )

        # ---------------------------------------------------------
        # 2. Persistent conversational history
        # ---------------------------------------------------------
        if include_history and remaining > 0:
            history = self.history.list(
                session_id,
                limit=self.history_limit,
            )

            if history:
                history_parts = [
                    "## Session History"
                ]

                history_remaining = min(
                    self.max_history_chars,
                    remaining,
                )

                for message in reversed(history):
                    if history_remaining <= 0:
                        break

                    role = str(
                        message.get(
                            "role",
                            "unknown",
                        )
                    )

                    content = str(
                        message.get(
                            "content",
                            "",
                        )
                    )

                    entry = (
                        f"{role}: "
                        f"{self._tail(content, 1500)}\n"
                    )

                    bounded = self._head(
                        entry,
                        history_remaining,
                    )

                    history_parts.append(bounded)

                    history_remaining -= len(bounded)

                history_section = "\n".join(
                    reversed(history_parts)
                )

                remaining = self._append_bounded(
                    sections,
                    history_section,
                    remaining=remaining,
                )

        # ---------------------------------------------------------
        # 3. Current task
        # ---------------------------------------------------------
        task_section = (
            "\n## Current Task\n"
            + self._head(
                task,
                max(1, remaining),
            )
        )

        self._append_bounded(
            sections,
            task_section,
            remaining=remaining,
        )

        result = "\n".join(sections)

        return self._head(
            result,
            self.max_context_chars,
        )
