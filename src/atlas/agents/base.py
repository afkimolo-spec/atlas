from __future__ import annotations

from pathlib import Path

from atlas.core.client import AtlasClient
from atlas.core.context import ContextManager
from atlas.memory.history import HistoryStore
from atlas.memory.index import KnowledgeIndex


ROOT = Path("/home/administrator/workspace/atlas")
DATABASE = ROOT / ".ai" / "memory" / "db" / "atlas.db"


class BaseAgent:
    """
    Base runtime for all Atlas agents.

    Execution pipeline:

        task
          ↓
        persistent context
          ↓
        model
          ↓
        persistent history
    """

    def __init__(
        self,
        role: str,
        prompt_file: str,
        model: str,
    ) -> None:

        self.role = role
        self.model = model

        prompt_path = (
            ROOT
            / "tools"
            / "prompts"
            / prompt_file
        )

        if not prompt_path.exists():
            raise FileNotFoundError(
                f"Agent prompt not found: {prompt_path}"
            )

        self.system_prompt = prompt_path.read_text(
            encoding="utf-8"
        )

        self.client = AtlasClient()

        self.history = HistoryStore(DATABASE)

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
    ) -> str:
        """
        Execute an agent task using persistent context.
        """

        if not task.strip():
            raise ValueError(
                "Agent task cannot be empty"
            )

        if not session_id.strip():
            raise ValueError(
                "session_id cannot be empty"
            )

        context = self.context.build(
            session_id=session_id,
            task=task,
        )

        self.history.add(
            session_id=session_id,
            role="user",
            content=task,
        )

        response = self.client.chat(
            self.model,
            task,
            system=(
                f"{self.system_prompt}\n\n"
                f"{context}"
            ),
        )

        self.history.add(
            session_id=session_id,
            role="assistant",
            content=response,
        )

        return response
