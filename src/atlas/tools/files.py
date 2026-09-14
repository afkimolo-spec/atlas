from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from atlas.security.auth import Principal
    from atlas.security.service import SecurityService


class FileManager:
    """
    Controlled filesystem interface for autonomous engineering.

    Every path is resolved beneath the configured workspace before
    access. File writes additionally pass through Atlas security policy.
    """

    def __init__(
        self,
        workspace: str | Path,
        *,
        security: SecurityService | None = None,
        principal: Principal | None = None,
        max_file_size: int = 10 * 1024 * 1024,
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

        if (
            security is not None
            and principal is None
        ):
            raise ValueError(
                "principal is required when security "
                "authorization is enabled"
            )

        if max_file_size <= 0:
            raise ValueError(
                "max_file_size must be greater than zero"
            )

        self.security = security
        self.principal = principal
        self.max_file_size = max_file_size

    def resolve_path(
        self,
        path: str | Path,
    ) -> Path:
        candidate = Path(path)

        if candidate.is_absolute():
            resolved = candidate.resolve()
        else:
            resolved = (
                self.workspace / candidate
            ).resolve()

        try:
            resolved.relative_to(
                self.workspace
            )
        except ValueError as exc:
            raise PermissionError(
                "File path must remain inside the engineering "
                f"workspace: {resolved}"
            ) from exc

        if self.security is not None:
            assert self.principal is not None
            return self.security.authorize_path(
                self.principal,
                resolved,
                write=False,
            )

        return resolved

    def _authorize_write(
        self,
        path: Path,
    ) -> Path:
        if self.security is not None:
            assert self.principal is not None
            return self.security.authorize_path(
                self.principal,
                path,
                write=True,
            )

        return path

    def exists(
        self,
        path: str | Path,
    ) -> bool:
        resolved = self.resolve_path(
            path
        )
        return resolved.exists()

    def read_text(
        self,
        path: str | Path,
        *,
        encoding: str = "utf-8",
    ) -> str:
        resolved = self.resolve_path(
            path
        )

        if not resolved.exists():
            raise FileNotFoundError(
                f"File does not exist: {resolved}"
            )

        if not resolved.is_file():
            raise IsADirectoryError(
                f"Path is not a file: {resolved}"
            )

        size = resolved.stat().st_size

        if size > self.max_file_size:
            raise ValueError(
                f"File exceeds maximum permitted size: "
                f"{size} > {self.max_file_size}"
            )

        return resolved.read_text(
            encoding=encoding
        )

    def write_text(
        self,
        path: str | Path,
        content: str,
        *,
        encoding: str = "utf-8",
    ) -> Path:
        if not isinstance(content, str):
            raise TypeError(
                "content must be a string"
            )

        encoded_size = len(
            content.encode(
                encoding,
                errors="strict",
            )
        )

        if encoded_size > self.max_file_size:
            raise ValueError(
                "Content exceeds maximum permitted file size: "
                f"{encoded_size} > {self.max_file_size}"
            )

        resolved = self.resolve_path(
            path
        )

        resolved = self._authorize_write(
            resolved
        )

        resolved.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        fd, temporary = tempfile.mkstemp(
            prefix=f".{resolved.name}.atlas-",
            dir=str(resolved.parent),
            text=True,
        )

        temporary_path = Path(
            temporary
        )

        try:
            with os.fdopen(
                fd,
                "w",
                encoding=encoding,
                newline="",
            ) as handle:
                handle.write(content)
                handle.flush()
                os.fsync(handle.fileno())

            temporary_path.replace(
                resolved
            )

        except Exception:
            try:
                temporary_path.unlink(
                    missing_ok=True
                )
            except OSError:
                pass

            raise

        return resolved

    def delete(
        self,
        path: str | Path,
    ) -> Path:
        resolved = self.resolve_path(
            path
        )

        resolved = self._authorize_write(
            resolved
        )

        if resolved.is_dir():
            raise IsADirectoryError(
                f"Refusing to delete directory: {resolved}"
            )

        if not resolved.exists():
            return resolved

        resolved.unlink()

        return resolved
