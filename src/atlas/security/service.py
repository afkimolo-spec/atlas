from __future__ import annotations

from pathlib import Path

from atlas.security.audit import (
    AuditEvent,
    AuditStore,
)
from atlas.security.auth import (
    Authenticator,
    Credentials,
    Principal,
    Role,
)
from atlas.security.policy import SecurityPolicy


class SecurityService:
    """
    Unified security enforcement service.

    Authentication, authorization, policy enforcement and audit
    logging are exposed behind one interface.
    """

    def __init__(
        self,
        *,
        authenticator: Authenticator | None = None,
        policy: SecurityPolicy | None = None,
        audit: AuditStore | None = None,
    ) -> None:
        self.authenticator = (
            authenticator
            or Authenticator()
        )

        self.policy = (
            policy
            or SecurityPolicy()
        )

        self.audit = (
            audit
            or AuditStore()
        )

    def authenticate(
        self,
        credentials: Credentials,
    ) -> Principal:
        try:
            principal = (
                self.authenticator.authenticate(
                    credentials
                )
            )

            self.audit.record(
                AuditEvent(
                    actor=principal.username,
                    action="authenticate",
                    resource="auth",
                    outcome="allowed",
                )
            )

            return principal

        except Exception as exc:
            self.audit.record(
                AuditEvent(
                    actor=credentials.username,
                    action="authenticate",
                    resource="auth",
                    outcome="denied",
                    detail=str(exc),
                )
            )

            raise

    def authorize(
        self,
        principal: Principal,
        permission: str,
    ) -> None:
        try:
            self.authenticator.authorize(
                principal,
                permission,
            )

            self.audit.record(
                AuditEvent(
                    actor=principal.username,
                    action="authorize",
                    resource=permission,
                    outcome="allowed",
                )
            )

        except Exception as exc:
            self.audit.record(
                AuditEvent(
                    actor=principal.username,
                    action="authorize",
                    resource=permission,
                    outcome="denied",
                    detail=str(exc),
                )
            )

            raise

    def authorize_command(
        self,
        principal: Principal,
        command: str,
        *,
        reviewed: bool = False,
    ) -> None:
        self.authorize(
            principal,
            "shell",
        )

        try:
            self.policy.authorize_command(
                command,
                reviewed=reviewed,
            )

            self.audit.record(
                AuditEvent(
                    actor=principal.username,
                    action="command",
                    resource=command[:256],
                    outcome="allowed",
                )
            )

        except Exception as exc:
            self.audit.record(
                AuditEvent(
                    actor=principal.username,
                    action="command",
                    resource=command[:256],
                    outcome="denied",
                    detail=str(exc),
                )
            )

            raise

    def authorize_path(
        self,
        principal: Principal,
        path: str | Path,
        *,
        write: bool = False,
    ) -> Path:
        self.authorize(
            principal,
            "write" if write else "read",
        )

        try:
            resolved = self.policy.authorize_path(
                path
            )

            self.audit.record(
                AuditEvent(
                    actor=principal.username,
                    action=(
                        "file.write"
                        if write
                        else "file.read"
                    ),
                    resource=str(resolved),
                    outcome="allowed",
                )
            )

            return resolved

        except Exception as exc:
            self.audit.record(
                AuditEvent(
                    actor=principal.username,
                    action=(
                        "file.write"
                        if write
                        else "file.read"
                    ),
                    resource=str(path),
                    outcome="denied",
                    detail=str(exc),
                )
            )

            raise

    def authorize_git(
        self,
        principal: Principal,
        command: str,
        *,
        reviewed: bool = False,
    ) -> None:
        self.authorize(
            principal,
            "git",
        )

        try:
            self.policy.authorize_command(
                command,
                reviewed=reviewed,
            )

            self.audit.record(
                AuditEvent(
                    actor=principal.username,
                    action="git",
                    resource=command[:256],
                    outcome="allowed",
                )
            )

        except Exception as exc:
            self.audit.record(
                AuditEvent(
                    actor=principal.username,
                    action="git",
                    resource=command[:256],
                    outcome="denied",
                    detail=str(exc),
                )
            )

            raise
