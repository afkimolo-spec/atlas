from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class CommandResult:
    """
    Structured result returned by command execution.
    """

    command: str
    cwd: str

    return_code: int

    stdout: str
    stderr: str

    duration: float

    timed_out: bool = False

    @property
    def succeeded(self) -> bool:
        """
        True when the command completed successfully.
        """

        return (
            not self.timed_out
            and self.return_code == 0
        )

    @property
    def failed(self) -> bool:
        """
        True when command execution failed.
        """

        return not self.succeeded

    @property
    def output(self) -> str:
        """
        Combined stdout/stderr output.
        """

        if self.stdout and self.stderr:
            return (
                f"{self.stdout}\n"
                f"{self.stderr}"
            )

        return self.stdout or self.stderr
