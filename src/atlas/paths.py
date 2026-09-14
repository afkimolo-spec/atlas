from __future__ import annotations

from pathlib import Path


ROOT = Path("/home/administrator/workspace/atlas").resolve()

CONFIG_ROOT = ROOT / "configs"
TOOLS_ROOT = ROOT / "tools"
SRC_ROOT = ROOT / "src"
TESTS_ROOT = ROOT / "tests"
DOCS_ROOT = ROOT / "docs"

AI_ROOT = ROOT / ".ai"
AI_MEMORY_ROOT = AI_ROOT / "memory"
AI_MEMORY_DB = AI_MEMORY_ROOT / "db"

DATABASE = AI_MEMORY_DB / "atlas.db"

RUNTIME_ROOT = AI_ROOT / "runtime"
RUNTIME_STATE_ROOT = RUNTIME_ROOT / "executions"
RUNTIME_EVENT_ROOT = RUNTIME_ROOT / "events"

__all__ = [
    "ROOT",
    "CONFIG_ROOT",
    "TOOLS_ROOT",
    "SRC_ROOT",
    "TESTS_ROOT",
    "DOCS_ROOT",
    "AI_ROOT",
    "AI_MEMORY_ROOT",
    "AI_MEMORY_DB",
    "DATABASE",
    "RUNTIME_ROOT",
    "RUNTIME_STATE_ROOT",
    "RUNTIME_EVENT_ROOT",
]
