from __future__ import annotations

import tempfile
from pathlib import Path

from atlas.api import routes
from atlas.core.execution_store import ExecutionStore
from atlas.core.feedback import FeedbackCollector
from atlas.core.telemetry import (
    TelemetryRecorder,
    TelemetryStore,
)
from atlas.security.audit import AuditStore
from atlas.security.auth import (
    Authenticator,
    Role,
)
from atlas.security.policy import SecurityPolicy
from atlas.security.service import SecurityService


class FakeAgent:
    role = "api-test-agent"

    def run(
        self,
        task: str,
        *,
        session_id: str,
    ) -> str:
        return "API operational."


print("=" * 60)
print("ATLAS API")
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
        }
    )

    routes.security = SecurityService(
        authenticator=authenticator,
        policy=SecurityPolicy(),
        audit=audit,
    )

    routes.workflow = routes.Workflow()

    routes.workflow.execution_store = (
        ExecutionStore(database)
    )

    routes.workflow.feedback = (
        FeedbackCollector(database)
    )

    routes.workflow.telemetry = (
        TelemetryRecorder(
            TelemetryStore(database)
        )
    )

    fake = FakeAgent()

    routes.workflow.researcher = fake
    routes.workflow.architect = fake
    routes.workflow.developer = fake
    routes.workflow.reviewer = fake
    routes.workflow.operator = fake

    planned = routes.plan_task(
        "admin",
        "AdminPassword!123",
        "API integration test",
        research=False,
        architecture=True,
        development=False,
        review=False,
        operations=False,
    )

    assert planned["stages"] == [
        "architecture"
    ]

    executed = routes.execute_task(
        "admin",
        "AdminPassword!123",
        "API integration test",
        research=False,
        architecture=True,
        development=False,
        review=False,
        operations=False,
    )

    assert executed["status"] == "completed"
    assert executed["succeeded"]
    assert executed["trace_id"]

    feedback = routes.feedback(
        "admin",
        "AdminPassword!123",
        execution_id=executed["session_id"],
    )

    assert (
        feedback["execution"]["status"]
        == "completed"
    )

    telemetry = routes.telemetry(
        "admin",
        "AdminPassword!123",
        executed["trace_id"],
    )

    assert (
        telemetry["trace"]["status"]
        == "completed"
    )

    denied = False

    try:
        routes.execute_task(
            "admin",
            "wrong-password",
            "must fail authentication",
        )
    except Exception:
        denied = True

    assert denied

print("Authentication : verified")
print("Planning       : verified")
print("Execution      : verified")
print("Feedback       : verified")
print("Telemetry      : verified")
print("Authorization  : verified")
print("=" * 60)
print("API verified.")
print("=" * 60)
