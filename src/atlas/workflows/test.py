from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from atlas.tools.command import CommandExecutor
from atlas.tools.result import CommandResult

if TYPE_CHECKING:
    from atlas.security.auth import Principal
    from atlas.security.service import SecurityService


@dataclass(slots=True)
class TestResult:
    command: str
    succeeded: bool
    output: str
    duration: float
    return_code: int


class TestWorkflow:
    """
    Execute controlled engineering verification commands.
    """

    def __init__(
        self,
        workspace: str | Path,
        *,
        security: SecurityService | None = None,
        principal: Principal | None = None,
        timeout: float = 600.0,
    ) -> None:
        self.executor = CommandExecutor(
            workspace,
            default_timeout=timeout,
            security=security,
            principal=principal,
        )

    def run(
        self,
        command: str = "pytest -q",
        *,
        cwd: str | Path | None = None,
    ) -> TestResult:
        result = self.executor.run(
            command,
            cwd=cwd,
            timeout=self.executor.default_timeout,
        )

        return TestResult(
            command=result.command,
            succeeded=result.succeeded,
            output=result.output,
            duration=result.duration,
            return_code=result.return_code,
        )

    def verify(
        self,
        command: str = "pytest -q",
        *,
        cwd: str | Path | None = None,
    ) -> CommandResult:
        return self.executor.run(
            command,
            cwd=cwd,
            timeout=self.executor.default_timeout,
        )
