from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC
from datetime import datetime
from uuid import uuid4


@dataclass(slots=True)
class Session:

    id: str = field(default_factory=lambda: str(uuid4()))

    created: datetime = field(
        default_factory=lambda: datetime.now(UTC)
    )

    project: str = "Atlas"

    user: str = "administrator"

    task: str = ""

    status: str = "idle"

    def start(self, task: str) -> None:
        self.task = task
        self.status = "running"

    def finish(self) -> None:
        self.status = "completed"

    def fail(self) -> None:
        self.status = "failed"
