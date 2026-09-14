from __future__ import annotations

import hashlib
import hmac
import secrets
from dataclasses import dataclass
from enum import Enum


class AuthError(RuntimeError):
    """Base authentication/authorization error."""


class AuthenticationError(AuthError):
    """Invalid authentication credentials."""


class AuthorizationError(AuthError):
    """Authenticated principal lacks permission."""


class Role(str, Enum):
    ADMIN = "admin"
    ENGINEER = "engineer"
    REVIEWER = "reviewer"
    OPERATOR = "operator"
    READONLY = "readonly"


@dataclass(frozen=True, slots=True)
class Credentials:
    username: str
    password: str


@dataclass(frozen=True, slots=True)
class Principal:
    username: str
    role: Role

    @property
    def is_privileged(self) -> bool:
        return self.role in {
            Role.ADMIN,
            Role.ENGINEER,
            Role.OPERATOR,
        }


class Authenticator:
    """
    Local credential authenticator.

    Passwords are stored as salted PBKDF2 hashes.
    Plaintext passwords are never persisted.
    """

    ITERATIONS = 310_000
    SALT_BYTES = 32
    KEY_BYTES = 32

    ROLE_PERMISSIONS = {
        Role.ADMIN: {
            "read",
            "plan",
            "execute",
            "recover",
            "write",
            "git",
            "shell",
            "admin",
        },
        Role.ENGINEER: {
            "read",
            "plan",
            "execute",
            "recover",
            "write",
            "git",
            "shell",
        },
        Role.REVIEWER: {
            "read",
            "plan",
            "review",
        },
        Role.OPERATOR: {
            "read",
            "execute",
            "recover",
            "shell",
        },
        Role.READONLY: {
            "read",
        },
    }

    def __init__(
        self,
        credentials: dict[str, tuple[Role, str]] | None = None,
    ) -> None:
        self._credentials: dict[
            str,
            tuple[Role, bytes, bytes, int],
        ] = {}

        if credentials:
            for username, (role, password) in credentials.items():
                self.add_user(
                    username,
                    password,
                    role=role,
                )

    @classmethod
    def hash_password(
        cls,
        password: str,
        *,
        salt: bytes | None = None,
    ) -> tuple[bytes, bytes]:
        if not password:
            raise ValueError(
                "Password cannot be empty."
            )

        salt = salt or secrets.token_bytes(
            cls.SALT_BYTES
        )

        digest = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt,
            cls.ITERATIONS,
            dklen=cls.KEY_BYTES,
        )

        return salt, digest

    def add_user(
        self,
        username: str,
        password: str,
        *,
        role: Role = Role.READONLY,
    ) -> None:
        username = username.strip()

        if not username:
            raise ValueError(
                "Username cannot be empty."
            )

        if username in self._credentials:
            raise ValueError(
                f"User already exists: {username}"
            )

        salt, digest = self.hash_password(
            password
        )

        self._credentials[username] = (
            role,
            salt,
            digest,
            self.ITERATIONS,
        )

    def remove_user(
        self,
        username: str,
    ) -> None:
        try:
            del self._credentials[username]
        except KeyError as exc:
            raise KeyError(
                f"User does not exist: {username}"
            ) from exc

    def authenticate(
        self,
        credentials: Credentials,
    ) -> Principal:
        username = credentials.username.strip()

        record = self._credentials.get(
            username
        )

        if record is None:
            raise AuthenticationError(
                "Invalid credentials."
            )

        role, salt, expected, iterations = record

        actual = hashlib.pbkdf2_hmac(
            "sha256",
            credentials.password.encode("utf-8"),
            salt,
            iterations,
            dklen=self.KEY_BYTES,
        )

        if not hmac.compare_digest(
            actual,
            expected,
        ):
            raise AuthenticationError(
                "Invalid credentials."
            )

        return Principal(
            username=username,
            role=role,
        )

    def authorize(
        self,
        principal: Principal,
        permission: str,
    ) -> None:
        permission = permission.strip().lower()

        if not permission:
            raise ValueError(
                "Permission cannot be empty."
            )

        allowed = self.ROLE_PERMISSIONS.get(
            principal.role,
            set(),
        )

        if permission not in allowed:
            raise AuthorizationError(
                f"Role '{principal.role.value}' is not "
                f"authorized for '{permission}'."
            )

    def require(
        self,
        credentials: Credentials,
        permission: str,
    ) -> Principal:
        principal = self.authenticate(
            credentials
        )

        self.authorize(
            principal,
            permission,
        )

        return principal
