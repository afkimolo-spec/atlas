from __future__ import annotations

import shlex
from pathlib import Path


class EngineeringShellPolicy:
    """
    Additional restrictions for autonomous engineering execution.

    SecurityPolicy remains the authoritative security layer. This
    policy adds engineering-specific restrictions designed to prevent
    an LLM-generated shell command from escaping the disposable
    workspace or invoking clearly destructive mechanisms.
    """

    BLOCKED_EXECUTABLES = frozenset(
        {
            "sudo",
            "su",
            "doas",
            "ssh",
            "scp",
            "sftp",
            "rsync",
            "curl",
            "wget",
            "nc",
            "ncat",
            "telnet",
            "ftp",
            "mount",
            "umount",
            "mkfs",
            "fdisk",
            "parted",
            "shutdown",
            "reboot",
            "halt",
            "poweroff",
            "systemctl",
            "service",
            "dd",
            "chown",
            "chmod",
            "useradd",
            "userdel",
            "groupadd",
            "groupdel",
            "passwd",
            "iptables",
            "nft",
        }
    )

    BLOCKED_SHELL_PATTERNS = (
        "$(",
        "`",
        "eval ",
        "exec ",
        "source ",
        ". /",
        ">/etc/",
        ">>/etc/",
        ">/usr/",
        ">>/usr/",
        ">/boot/",
        ">>/boot/",
        ">/sys/",
        ">>/sys/",
        ">/proc/",
        ">>/proc/",
    )

    BLOCKED_COMMAND_WORDS = frozenset(
        {
            "rm",
            "rmdir",
            "unlink",
            "format",
            "mkfs",
        }
    )

    def __init__(
        self,
        workspace: str | Path,
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

    def validate(self, command: str) -> None:
        if not command.strip():
            raise ValueError(
                "Command cannot be empty."
            )

        normalized = command.strip().lower()

        for pattern in self.BLOCKED_SHELL_PATTERNS:
            if pattern in normalized:
                raise PermissionError(
                    "Autonomous shell construct is blocked: "
                    f"{pattern!r}"
                )

        try:
            tokens = shlex.split(command)
        except ValueError as exc:
            raise ValueError(
                f"Invalid shell syntax: {exc}"
            ) from exc

        if not tokens:
            raise ValueError(
                "Command cannot be empty."
            )

        executable = Path(tokens[0]).name.lower()

        if executable in self.BLOCKED_EXECUTABLES:
            raise PermissionError(
                "Executable is blocked for autonomous engineering: "
                f"{executable}"
            )

        if executable in self.BLOCKED_COMMAND_WORDS:
            raise PermissionError(
                "Destructive executable is blocked for autonomous "
                f"engineering: {executable}"
            )

        for token in tokens:
            self._validate_path_token(token)

    def _validate_path_token(
        self,
        token: str,
    ) -> None:
        if not token:
            return

        candidate = token

        if candidate.startswith(
            ("./", "../", "/")
        ):
            path_text = candidate

            if "=" in path_text and not path_text.startswith("/"):
                path_text = path_text.split(
                    "=",
                    1,
                )[1]

            if path_text.startswith("/"):
                path = Path(path_text).resolve()

                try:
                    path.relative_to(
                        self.workspace
                    )
                except ValueError as exc:
                    raise PermissionError(
                        "Command references a path outside the "
                        f"engineering workspace: {path}"
                    ) from exc

            else:
                path = (
                    self.workspace
                    / path_text
                ).resolve()

                try:
                    path.relative_to(
                        self.workspace
                    )
                except ValueError as exc:
                    raise PermissionError(
                        "Command references a path outside the "
                        f"engineering workspace: {path}"
                    ) from exc
