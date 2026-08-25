from __future__ import annotations

from pathlib import Path

from atlas.config.loader import load_workspace


class Workspace:

    def __init__(self):

        self.config = load_workspace()

        self.root = Path(self.config.root)

    @property
    def source(self) -> Path:
        return self.root / self.config.source.code

    @property
    def tests(self) -> Path:
        return self.root / self.config.source.tests

    @property
    def packages(self) -> Path:
        return self.root / self.config.source.packages

    @property
    def docs(self) -> Path:
        return self.root / self.config.documentation.engineering

    @property
    def agents(self) -> Path:
        return self.root / self.config.knowledge.agents

    @property
    def prompts(self) -> Path:
        return self.root / self.config.knowledge.prompts

    @property
    def memory(self) -> Path:
        return self.root / self.config.knowledge.memory

    @property
    def workflows(self) -> Path:
        return self.root / self.config.knowledge.workflows

    @property
    def rules(self) -> Path:
        return self.root / self.config.knowledge.rules

    def resolve(self, path: str) -> Path:
        return self.root / path
