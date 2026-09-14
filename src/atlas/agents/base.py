from __future__ import annotations

from pathlib import Path

from atlas.core.client import AtlasClient
from atlas.core.context import ContextManager
from atlas.memory.history import HistoryStore
from atlas.memory.index import KnowledgeIndex
from atlas.paths import ROOT


DATABASE = (
    ROOT
    / ".ai"
    / "memory"
    / "db"
    / "atlas.db"
)


class BaseAgent:
    """
    Base runtime for Atlas agents.

    Normal agent sessions use persistent context and history.

    Autonomous internal control-loop calls can independently disable
    conversational history and semantic knowledge retrieval. This keeps
    model requests bounded and prevents unnecessary embedding work.
    """

    def __init__(
        self,
        role: str,
        prompt_file: str,
        model: str,
    ) -> None:
        self.role = role
        self.model = model

        prompt_root = (
            ROOT
            / "tools"
            / "prompts"
        ).resolve()

        prompt_path = (
            prompt_root
            / prompt_file
        ).resolve()

        if (
            prompt_path != prompt_root
            and prompt_root not in prompt_path.parents
        ):
            raise ValueError(
                "Agent prompt path escapes prompt directory: "
                f"{prompt_file}"
            )

        if not prompt_path.exists():
            raise FileNotFoundError(
                f"Agent prompt not found: {prompt_path}"
            )

        if not prompt_path.is_file():
            raise FileNotFoundError(
                f"Agent prompt is not a file: {prompt_path}"
            )

        self.system_prompt = prompt_path.read_text(
            encoding="utf-8"
        )

        self.client = AtlasClient()

        self.history = HistoryStore(
            DATABASE
        )

        self.knowledge = KnowledgeIndex(
            DATABASE
        )

        self.context = ContextManager(
            history=self.history,
            knowledge=self.knowledge,
        )

    def run(
        self,
        task: str,
        *,
        session_id: str,
        knowledge_query: str | None = None,
        include_history: bool = True,
        include_knowledge: bool = True,
        persist_history: bool = True,
        temperature: float = 0.2,
        max_tokens: int = 512,
    ) -> str:
        """
        Execute an agent task.

        include_history:
            Controls persistent session-history retrieval.

        include_knowledge:
            Controls semantic engineering-knowledge retrieval.

        persist_history:
            Controls persistence of request/response history.

        These controls allow autonomous execution paths to remain
        bounded while preserving full persistent-memory behavior for
        normal agent sessions.
        """

        if not isinstance(task, str) or not task.strip():
            raise ValueError(
                "Agent task cannot be empty."
            )

        if not isinstance(session_id, str) or not session_id.strip():
            raise ValueError(
                "session_id cannot be empty."
            )

        if (
            knowledge_query is not None
            and not knowledge_query.strip()
        ):
            raise ValueError(
                "knowledge_query cannot be empty."
            )

        context = self.context.build(
            session_id=session_id,
            task=task,
            knowledge_query=knowledge_query,
            include_history=include_history,
            include_knowledge=include_knowledge,
        )

        system = (
            f"{self.system_prompt}\n\n"
            f"{context}"
        )

        if persist_history:
            self.history.add(
                session_id=session_id,
                role="user",
                content=task,
            )

        response = self.client.chat(
            self.model,
            task,
            system=system,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        if persist_history:
            self.history.add(
                session_id=session_id,
                role="assistant",
                content=response,
            )

        return response
