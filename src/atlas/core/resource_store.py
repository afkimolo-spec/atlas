from __future__ import annotations

from pathlib import Path

from atlas.core.resource import (
    DATABASE,
    ResourceManager,
)


class ResourceStore:
    """
    Persistent resource-state facade.

    Kept separate from execution persistence so resource ownership
    remains independently recoverable.
    """

    def __init__(
        self,
        database: str | Path = DATABASE,
    ) -> None:
        self.manager = ResourceManager(database)

    def snapshot(self) -> dict:
        return self.manager.snapshot()

    def resources(self):
        return self.manager.list()

    def leases(
        self,
        *,
        resource: str | None = None,
        owner: str | None = None,
    ):
        return self.manager.leases(
            resource=resource,
            owner=owner,
        )

    def recover(self) -> int:
        return self.manager.recover_expired()
