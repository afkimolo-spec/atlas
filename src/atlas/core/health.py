from __future__ import annotations
from atlas.paths import ROOT

import os

import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Callable


DATABASE = ROOT / ".ai" / "memory" / "db" / "atlas.db"


@dataclass(frozen=True, slots=True)
class HealthResult:
    name: str
    status: str
    duration_ms: float
    detail: str = ""


class HealthChecker:
    """
    Lightweight runtime health checker.

    Checks only dependencies required for local Atlas operation.
    """

    def __init__(
        self,
        database: str | Path = DATABASE,
    ) -> None:
        self.database = Path(database)

    def check_database(self) -> HealthResult:
        started = datetime.now(UTC)

        try:
            with sqlite3.connect(
                self.database,
                timeout=5.0,
            ) as connection:
                result = connection.execute(
                    "PRAGMA integrity_check"
                ).fetchone()

            detail = (
                str(result[0])
                if result
                else "unknown"
            )

            status = (
                "healthy"
                if detail == "ok"
                else "degraded"
            )

        except Exception as exc:
            detail = str(exc)
            status = "unhealthy"

        duration_ms = max(
            0.0,
            (
                datetime.now(UTC) - started
            ).total_seconds()
            * 1000.0,
        )

        return HealthResult(
            name="database",
            status=status,
            duration_ms=duration_ms,
            detail=detail,
        )

    def check_workspace(self) -> HealthResult:
        started = datetime.now(UTC)

        try:
            exists = ROOT.exists()
            writable = ROOT.is_dir()

            if exists and writable:
                status = "healthy"
                detail = str(ROOT)
            else:
                status = "unhealthy"
                detail = "workspace unavailable"

        except Exception as exc:
            status = "unhealthy"
            detail = str(exc)

        duration_ms = max(
            0.0,
            (
                datetime.now(UTC) - started
            ).total_seconds()
            * 1000.0,
        )

        return HealthResult(
            name="workspace",
            status=status,
            duration_ms=duration_ms,
            detail=detail,
        )

    def check(
        self,
        checks: dict[str, Callable[[], HealthResult]]
        | None = None,
    ) -> dict:
        checks = checks or {
            "database": self.check_database,
            "workspace": self.check_workspace,
        }

        results = []

        for check in checks.values():
            results.append(check())

        statuses = {
            result.status
            for result in results
        }

        if "unhealthy" in statuses:
            overall = "unhealthy"
        elif "degraded" in statuses:
            overall = "degraded"
        else:
            overall = "healthy"

        return {
            "status": overall,
            "checked_at": datetime.now(
                UTC
            ).isoformat(),
            "checks": [
                {
                    "name": result.name,
                    "status": result.status,
                    "duration_ms": result.duration_ms,
                    "detail": result.detail,
                }
                for result in results
            ],
        }
