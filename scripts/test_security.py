from __future__ import annotations

import tempfile
from pathlib import Path

from atlas.security.audit import (
    AuditEvent,
    AuditStore,
)
from atlas.security.auth import (
    AuthenticationError,
    AuthorizationError,
    Authenticator,
    Credentials,
    Role,
)
from atlas.security.policy import (
    SecurityPolicy,
)
from atlas.security.service import SecurityService


print("=" * 60)
print("ATLAS SECURITY")
print("=" * 60)

with tempfile.TemporaryDirectory() as directory:
    database = Path(directory) / "atlas.db"

    audit = AuditStore(database)

    authenticator = Authenticator(
        {
            "admin": (
                Role.ADMIN,
                "AdminPassword!123",
            ),
            "engineer": (
                Role.ENGINEER,
                "EngineerPassword!123",
            ),
            "reviewer": (
                Role.REVIEWER,
                "ReviewerPassword!123",
            ),
            "readonly": (
                Role.READONLY,
                "ReadonlyPassword!123",
            ),
        }
    )

    policy = SecurityPolicy(
        allow_shell=True,
        allow_git=True,
        allow_file_write=True,
        allow_network=False,
        require_review_before_commit=True,
        block_system_paths=[
            "/etc",
            "/usr",
            "/boot",
            "/sys",
            "/proc",
        ],
    )

    service = SecurityService(
        authenticator=authenticator,
        policy=policy,
        audit=audit,
    )

    # Authentication
    engineer = service.authenticate(
        Credentials(
            "engineer",
            "EngineerPassword!123",
        )
    )

    assert engineer.role == Role.ENGINEER

    try:
        service.authenticate(
            Credentials(
                "engineer",
                "wrong-password",
            )
        )
    except AuthenticationError:
        pass
    else:
        raise AssertionError(
            "Invalid authentication was accepted."
        )

    # Authorization
    service.authorize(
        engineer,
        "shell",
    )

    try:
        readonly = service.authenticate(
            Credentials(
                "readonly",
                "ReadonlyPassword!123",
            )
        )

        service.authorize(
            readonly,
            "shell",
        )
    except AuthorizationError:
        pass
    else:
        raise AssertionError(
            "Readonly principal gained shell permission."
        )

    # Workspace/system-path restriction
    workspace_file = (
        Path(directory) / "workspace.txt"
    )
    workspace_file.write_text(
        "security test",
        encoding="utf-8",
    )

    resolved = service.authorize_path(
        engineer,
        workspace_file,
    )

    assert resolved == workspace_file.resolve()

    try:
        service.authorize_path(
            engineer,
            "/etc/passwd",
        )
    except PermissionError:
        pass
    else:
        raise AssertionError(
            "Protected system path was not blocked."
        )

    # Shell policy
    service.authorize_command(
        engineer,
        "python -c \"print('ok')\"",
    )

    try:
        service.authorize_command(
            engineer,
            "curl https://example.com",
        )
    except PermissionError:
        pass
    else:
        raise AssertionError(
            "Network command was accepted."
        )

    # Dangerous command policy
    try:
        service.authorize_command(
            engineer,
            "reboot",
        )
    except PermissionError:
        pass
    else:
        raise AssertionError(
            "Dangerous command was accepted."
        )

    # Git commit review gate
    try:
        service.authorize_git(
            engineer,
            "git commit -m 'test'",
            reviewed=False,
        )
    except PermissionError:
        pass
    else:
        raise AssertionError(
            "Unreviewed commit was accepted."
        )

    service.authorize_git(
        engineer,
        "git commit -m 'test'",
        reviewed=True,
    )

    # Audit persistence
    events = audit.list()

    assert len(events) >= 8

    denied = audit.list(
        outcome="denied"
    )

    assert len(denied) >= 4

    restarted = AuditStore(
        database
    )

    assert restarted.count() == audit.count()

print("Authentication     : verified")
print("RBAC               : verified")
print("System paths       : blocked")
print("Shell policy       : verified")
print("Network policy     : blocked")
print("Dangerous commands : blocked")
print("Git review gate    : verified")
print("Audit persistence  : verified")
print("=" * 60)
print("Security verified.")
print("=" * 60)
