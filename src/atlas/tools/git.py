from __future__ import annotations

import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from atlas.tools.command import CommandExecutor
from atlas.tools.result import CommandResult

if TYPE_CHECKING:
    from atlas.security.auth import Principal
    from atlas.security.service import SecurityService


@dataclass(slots=True)
class GitCheckpoint:
    """
    Repository state immediately before autonomous modifications.
    """

    clean_tracked_paths: set[str] = field(
        default_factory=set
    )
    untracked_paths: set[str] = field(
        default_factory=set
    )


@dataclass(slots=True)
class GitManager:
    workspace: Path
    command: CommandExecutor
    security: SecurityService | None = None
    principal: Principal | None = None

    def __init__(
        self,
        workspace: str | Path,
        *,
        default_timeout: float = 300.0,
        security: SecurityService | None = None,
        principal: Principal | None = None,
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

        self.command = CommandExecutor(
            self.workspace,
            default_timeout=default_timeout,
            security=security,
            principal=principal,
        )

        self.security = security
        self.principal = principal

    def _run(
        self,
        command: str,
        *,
        reviewed: bool = False,
        timeout: float | None = None,
    ) -> CommandResult:
        if self.security is not None:
            if self.principal is None:
                raise ValueError(
                    "principal is required for Git authorization"
                )

            self.security.authorize_git(
                self.principal,
                command,
                reviewed=reviewed,
            )

        return self.command.run(
            command,
            timeout=timeout,
            reviewed=reviewed,
        )

    def status(self) -> CommandResult:
        return self._run(
            "git status --porcelain=v1"
        )

    def diff(
        self,
        *,
        cached: bool = False,
    ) -> CommandResult:
        command = (
            "git diff --cached"
            if cached
            else "git diff"
        )

        return self._run(
            command
        )

    def diff_stat(self) -> CommandResult:
        return self._run(
            "git diff --stat"
        )

    @staticmethod
    def _normalize_status_path(
        path: str,
    ) -> str:
        return path.rstrip("/")

    def create_checkpoint(self) -> GitCheckpoint:
        result = self._run(
            "git status --porcelain=v1"
        )

        if not result.succeeded:
            raise RuntimeError(
                "Unable to create Git checkpoint:\n"
                f"{result.output}"
            )

        clean_tracked_paths: set[str] = set()
        untracked_paths: set[str] = set()

        for line in result.stdout.splitlines():
            if len(line) < 3:
                continue

            state = line[:2]
            path = self._normalize_status_path(
                line[3:]
            )

            if not path:
                continue

            if state == "??":
                untracked_paths.add(path)
            else:
                clean_tracked_paths.add(path)

        return GitCheckpoint(
            clean_tracked_paths=clean_tracked_paths,
            untracked_paths=untracked_paths,
        )

    def rollback(
        self,
        checkpoint: GitCheckpoint,
    ) -> list[str]:
        current = self.status()

        if not current.succeeded:
            raise RuntimeError(
                "Unable to inspect Git state before rollback:\n"
                f"{current.output}"
            )

        current_tracked: set[str] = set()
        current_untracked: set[str] = set()

        for line in current.stdout.splitlines():
            if len(line) < 3:
                continue

            state = line[:2]
            path = self._normalize_status_path(
                line[3:]
            )

            if not path:
                continue

            if state == "??":
                current_untracked.add(path)
            else:
                current_tracked.add(path)

        changed_clean_paths = sorted(
            current_tracked
            - checkpoint.clean_tracked_paths
        )

        newly_created_untracked = sorted(
            current_untracked
            - checkpoint.untracked_paths
        )

        restored: list[str] = []

        for path in changed_clean_paths:
            result = self._run(
                f'git restore --staged --worktree -- "{path}"'
            )

            if not result.succeeded:
                raise RuntimeError(
                    f"Git restore failed for {path}:\n"
                    f"{result.output}"
                )

            restored.append(path)

        for path in newly_created_untracked:
            path_obj = (
                self.workspace / path
            ).resolve()

            try:
                path_obj.relative_to(
                    self.workspace
                )
            except ValueError as exc:
                raise PermissionError(
                    "Rollback attempted to remove a path outside "
                    f"the workspace: {path_obj}"
                ) from exc

            if not path_obj.exists():
                continue

            if path_obj.is_symlink():
                path_obj.unlink()
            elif path_obj.is_dir():
                shutil.rmtree(
                    path_obj
                )
            else:
                path_obj.unlink()

            restored.append(path)

        return restored

    def apply_patch(
        self,
        patch_file: str | Path,
    ) -> CommandResult:
        patch_path = Path(
            patch_file
        )

        if not patch_path.is_absolute():
            patch_path = (
                self.workspace / patch_path
            ).resolve()
        else:
            patch_path = patch_path.resolve()

        try:
            patch_path.relative_to(
                self.workspace
            )
        except ValueError as exc:
            raise PermissionError(
                "Patch file must remain inside workspace."
            ) from exc

        check = self._run(
            f'git apply --check "{patch_path}"'
        )

        if not check.succeeded:
            return check

        return self._run(
            f'git apply "{patch_path}"'
        )

    def commit(
        self,
        message: str,
    ) -> CommandResult:
        if not message.strip():
            raise ValueError(
                "Commit message cannot be empty."
            )

        safe_message = (
            message.replace(
                "\\",
                "\\\\",
            )
            .replace(
                '"',
                '\\"',
            )
        )

        return self._run(
            f'git commit -m "{safe_message}"',
            reviewed=True,
        )
