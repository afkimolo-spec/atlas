from __future__ import annotations

import os
import subprocess
import time
from pathlib import Path
from typing import TYPE_CHECKING

from atlas.tools.result import CommandResult
from atlas.tools.shell import EngineeringShellPolicy

if TYPE_CHECKING:
    from atlas.security.auth import Principal
    from atlas.security.service import SecurityService


class CommandExecutor:
    """
    Execute engineering commands inside a constrained workspace.

    The executor provides:

        - workspace containment
        - configurable timeout
        - stdout/stderr capture
        - environment inheritance
        - structured execution results
        - optional Atlas security authorization
        - additional autonomous-engineering shell restrictions
    """

    def __init__(
        self,
        workspace: str | Path,
        *,
        default_timeout: float = 300.0,
        security: SecurityService | None = None,
        principal: Principal | None = None,
        engineering_policy: EngineeringShellPolicy | None = None,
    ) -> None:
        self.workspace = (
            Path(workspace)
            .expanduser()
            .resolve()
        )

        if not self.workspace.exists():
            raise FileNotFoundError(
                f"Workspace does not exist: {self.workspace}"
            )

        if not self.workspace.is_dir():
            raise NotADirectoryError(
                f"Workspace is not a directory: {self.workspace}"
            )

        if default_timeout <= 0:
            raise ValueError(
                "default_timeout must be greater than zero"
            )

        if (
            security is not None
            and principal is None
        ):
            raise ValueError(
                "principal is required when security "
                "authorization is enabled"
            )

        self.default_timeout = default_timeout
        self.security = security
        self.principal = principal
        self.engineering_policy = (
            engineering_policy
            or EngineeringShellPolicy(
                self.workspace
            )
        )

    def resolve_cwd(
        self,
        cwd: str | Path | None = None,
    ) -> Path:
        if cwd is None:
            path = self.workspace

        else:
            candidate = Path(cwd)

            if candidate.is_absolute():
                path = candidate.resolve()
            else:
                path = (
                    self.workspace / candidate
                ).resolve()

        try:
            path.relative_to(
                self.workspace
            )
        except ValueError as exc:
            raise PermissionError(
                "Command working directory must remain "
                f"inside the Atlas workspace: {path}"
            ) from exc

        if not path.exists():
            raise FileNotFoundError(
                f"Working directory does not exist: {path}"
            )

        if not path.is_dir():
            raise NotADirectoryError(
                f"Working directory is not a directory: {path}"
            )

        return path

    def run(
        self,
        command: str,
        *,
        cwd: str | Path | None = None,
        timeout: float | None = None,
        env: dict[str, str] | None = None,
        reviewed: bool = False,
    ) -> CommandResult:
        if not command.strip():
            raise ValueError(
                "Command cannot be empty"
            )

        self.engineering_policy.validate(
            command
        )

        working_directory = self.resolve_cwd(
            cwd
        )

        if self.security is not None:
            assert self.principal is not None

            self.security.authorize_command(
                self.principal,
                command,
                reviewed=reviewed,
            )

        execution_timeout = (
            self.default_timeout
            if timeout is None
            else timeout
        )

        if execution_timeout <= 0:
            raise ValueError(
                "timeout must be greater than zero"
            )

        process_environment = os.environ.copy()

        if env:
            process_environment.update(env)

        started = time.monotonic()
        timed_out = False

        try:
            process = subprocess.run(
                command,
                shell=True,
                cwd=working_directory,
                env=process_environment,
                capture_output=True,
                text=True,
                timeout=execution_timeout,
                check=False,
            )

            return_code = process.returncode
            stdout = process.stdout
            stderr = process.stderr

        except subprocess.TimeoutExpired as exc:
            timed_out = True

            stdout = (
                exc.stdout
                if isinstance(exc.stdout, str)
                else (
                    exc.stdout.decode(
                        errors="replace"
                    )
                    if exc.stdout
                    else ""
                )
            )

            stderr = (
                exc.stderr
                if isinstance(exc.stderr, str)
                else (
                    exc.stderr.decode(
                        errors="replace"
                    )
                    if exc.stderr
                    else ""
                )
            )

            return_code = -1

        duration = (
            time.monotonic() - started
        )

        return CommandResult(
            command=command,
            cwd=str(working_directory),
            return_code=return_code,
            stdout=stdout,
            stderr=stderr,
            duration=duration,
            timed_out=timed_out,
        )
