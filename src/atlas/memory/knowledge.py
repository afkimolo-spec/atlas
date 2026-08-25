from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(slots=True)
class KnowledgeDocument:
    """
    A single piece of indexed engineering knowledge.
    """

    id: str
    title: str
    content: str

    source: str

    tags: list[str] = field(default_factory=list)

    created: datetime = field(default_factory=datetime.utcnow)

    metadata: dict[str, str] = field(default_factory=dict)

    @property
    def size(self) -> int:
        return len(self.content)

    @property
    def words(self) -> int:
        return len(self.content.split())
