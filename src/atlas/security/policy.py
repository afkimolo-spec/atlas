from __future__ import annotations

import shlex
from dataclasses import dataclass, field
from pathlib import Path


DEFAULT_SYSTEM_PATHS = (
    "/etc",
    "/usr",
    "/boot",
    "/sys",
    "/proc",
)


@dataclass(slots=True)
class SecurityPolicy:
    """
    Runtime security policy.

    The policy is intentionally explicit. Every privileged capability
    has a separate switch and command/path restrictions are enforced
    before execution.
    """

    allow_shell: bool = True
    allow_git: bool = True
    allow_file_write: bool = True
    allow_network: bool = False
    require_review_before_commit: bool = True

    block_system_paths: list[str] = field(
        default_factory=lambda: list(DEFAULT_SYSTEM_PATHS)
    )

    blocked_commands: list[str] = field(
        default_factory=lambda: [
            "mkfs",
            "fdisk",
            "parted",
            "mount",
            "umount",
            "shutdown",
            "reboot",
            "halt",
            "poweroff",
        ]
    )

    network_commands: list[str] = field(
        default_factory=lambda: [
            "curl",
            "wget",
            "nc",
            "ncat",
            "telnet",
            "ssh",
            "scp",
            "sftp",
            "rsync",
        ]
    )

    commit_commands: list[str] = field(
        default_factory=lambda: [
            "git commit",
        ]
    )

    def __post_init__(self) -> None:
        self.block_system_paths = [
            str(Path(path).expanduser().resolve())
            for path in self.block_system_paths
        ]

        self.blocked_commands = [
            item.strip().lower()
            for item in self.blocked_commands
            if item.strip()
        ]

        self.network_commands = [
            item.strip().lower()
            for item in self.network_commands
            if item.strip()
        ]

        self.commit_commands = [
            item.strip().lower()
            for item in self.commit_commands
            if item.strip()
        ]

    def authorize_shell(self) -> None:
        if not self.allow_shell:
            raise PermissionError(
                "Shell execution is disabled by security policy."
            )

    def authorize_git(self) -> None:
        if not self.allow_git:
            raise PermissionError(
                "Git operations are disabled by security policy."
            )

    def authorize_file_write(self) -> None:
        if not self.allow_file_write:
            raise PermissionError(
                "File writes are disabled by security policy."
            )

    def authorize_network(self) -> None:
        if not self.allow_network:
            raise PermissionError(
                "Network access is disabled by security policy."
            )

    def authorize_path(
        self,
        path: str | Path,
    ) -> Path:
        resolved = Path(path).expanduser().resolve()

        for blocked in self.block_system_paths:
            blocked_path = Path(blocked)

            if (
                resolved == blocked_path
                or blocked_path in resolved.parents
            ):
                raise PermissionError(
                    "Access to protected system path is blocked: "
                    f"{resolved}"
                )

        return resolved

    def authorize_command(
        self,
        command: str,
        *,
        reviewed: bool = False,
    ) -> None:
        if not command.strip():
            raise ValueError(
                "Command cannot be empty."
            )

        self.authorize_shell()

        normalized = " ".join(
            shlex.split(command)
        ).lower()

        tokens = normalized.split()

        if not tokens:
            raise ValueError(
                "Command cannot be empty."
            )

        executable = Path(tokens[0]).name.lower()

        for blocked in self.blocked_commands:
            if executable == blocked:
                raise PermissionError(
                    f"Command is blocked by security policy: {executable}"
                )

        is_network = (
            executable in self.network_commands
        )

        if is_network:
            self.authorize_network()

        is_git = (
            executable == "git"
            or normalized.startswith("git ")
        )

        if is_git:
            self.authorize_git()

        is_commit = any(
            normalized.startswith(prefix)
            for prefix in self.commit_commands
        )

        if (
            is_commit
            and self.require_review_before_commit
            and not reviewed
        ):
            raise PermissionError(
                "Git commit requires explicit review approval."
            )
