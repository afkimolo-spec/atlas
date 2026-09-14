from __future__ import annotations

import os
import subprocess
import time
from pathlib import Path

from atlas.tools.result import CommandResult


class CommandExecutor:
    """
    Execute engineering commands inside the Atlas workspace.

    The executor provides:

        - workspace containment
        - configurable timeout
        - stdout capture
        - stderr capture
        - environment inheritance
        - structured execution results

    Commands are executed through the system shell so normal
    engineering commands, pipes, redirects, and shell syntax
    remain available.
    """

    def __init__(
        self,
        workspace: str | Path,
        *,
        default_timeout: float = 300.0,
    ) -> None:

        self.workspace = Path(
            workspace
        ).expanduser().resolve()

        if not self.workspace.exists():
            raise FileNotFoundError(
                f"Workspace does not exist: "
                f"{self.workspace}"
            )

        if not self.workspace.is_dir():
            raise NotADirectoryError(
                f"Workspace is not a directory: "
                f"{self.workspace}"
            )

        if default_timeout <= 0:
            raise ValueError(
                "default_timeout must be greater than zero"
            )

        self.default_timeout = default_timeout

    def resolve_cwd(
        self,
        cwd: str | Path | None = None,
    ) -> Path:
        """
        Resolve and validate the command working directory.

        Relative paths are interpreted relative to the Atlas
        workspace.

        Absolute paths must remain inside the workspace.
        """

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
                "Command working directory must "
                "remain inside the Atlas workspace: "
                f"{path}"
            ) from exc

        if not path.exists():
            raise FileNotFoundError(
                f"Working directory does not exist: "
                f"{path}"
            )

        if not path.is_dir():
            raise NotADirectoryError(
                f"Working directory is not a directory: "
                f"{path}"
            )

        return path

    def run(
        self,
        command: str,
        *,
        cwd: str | Path | None = None,
        timeout: float | None = None,
        env: dict[str, str] | None = None,
    ) -> CommandResult:
        """
        Execute a shell command.

        The command itself is allowed to use normal shell
        syntax. The working directory remains constrained
        to the Atlas workspace.
        """

        if not command.strip():
            raise ValueError(
                "Command cannot be empty"
            )

        working_directory = self.resolve_cwd(cwd)

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
