from atlas.paths import ROOT

import os
from pathlib import Path



from pathlib import Path


from pathlib import Path

from pydantic import BaseModel


CONFIG = ROOT / "configs"


class ModelEndpoint(BaseModel):
    provider: str
    endpoint: str
    model: str
    purpose: str


class Models(BaseModel):
    engineering: ModelEndpoint
    research: ModelEndpoint
    completion: ModelEndpoint
    embeddings: ModelEndpoint


class WorkspaceKnowledge(BaseModel):
    agents: str
    prompts: str
    memory: str
    workflows: str
    rules: str


class WorkspaceDocumentation(BaseModel):
    engineering: str


class WorkspaceSource(BaseModel):
    code: str
    tests: str
    packages: str


class WorkspaceGit(BaseModel):
    branch: str


class WorkspaceAI(BaseModel):
    instructions: str


class Workspace(BaseModel):
    name: str
    root: str
    knowledge: WorkspaceKnowledge
    documentation: WorkspaceDocumentation
    source: WorkspaceSource
    git: WorkspaceGit
    ai: WorkspaceAI


class LoggingFiles(BaseModel):
    engineering: str
    research: str
    completion: str
    atlas: str


class Logging(BaseModel):
    level: str
    files: LoggingFiles


class Security(BaseModel):
    allow_shell: bool
    allow_git: bool
    allow_file_write: bool
    allow_network: bool
    require_review_before_commit: bool
    block_system_paths: list[str]
