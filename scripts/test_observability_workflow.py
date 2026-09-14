from __future__ import annotations

import tempfile
from pathlib import Path

from atlas.core.execution_store import ExecutionStore
from atlas.core.feedback import FeedbackCollector
from atlas.core.telemetry import TelemetryRecorder, TelemetryStore
from atlas.planning import TaskPlanner
from atlas.workflows import Workflow


class FakeAgent:
    role = "test-agent"

    def run(
        self,
        task: str,
        *,
        session_id: str,
    ) -> str:
        return "Observability workflow operational."


print("=" * 60)
print("ATLAS OBSERVABILITY WORKFLOW")
print("=" * 60)

with tempfile.TemporaryDirectory() as directory:
    database = Path(directory) / "atlas.db"

    workflow = Workflow()

    workflow.execution_store = ExecutionStore(
        database
    )

    workflow.feedback = FeedbackCollector(
        database
    )

    workflow.telemetry = TelemetryRecorder(
        TelemetryStore(database)
    )

    fake = FakeAgent()

    workflow.researcher = fake
    workflow.architect = fake
    workflow.developer = fake
    workflow.reviewer = fake
    workflow.operator = fake

    plan = TaskPlanner().plan(
        "Observability workflow integration",
        research=False,
        architecture=True,
        development=False,
        review=False,
        operations=False,
    )

    result = workflow.execute_plan(
        plan
    )

    assert result.status == "completed"
    assert result.trace_id is not None
    assert result.succeeded

    telemetry = workflow.telemetry.store

    trace = telemetry.trace(
        result.trace_id
    )

    assert trace is not None
    assert trace["execution_id"] == result.session_id
    assert trace["status"] == "completed"

    spans = telemetry.spans(
        result.trace_id
    )

    assert len(spans) == 2
    assert spans[0]["kind"] == "execution"
    assert spans[1]["kind"] == "stage"
    assert spans[1]["stage"] == "architecture"
    assert spans[1]["status"] == "completed"

    metrics = telemetry.execution_metrics()

    assert metrics["executions"] == 1
    assert metrics["completed_executions"] == 1
    assert metrics["failed_executions"] == 0

print("Workflow trace     : verified")
print("Execution span     : verified")
print("Stage span         : verified")
print("Metrics integration: verified")
print("Persistence        : verified")
print("=" * 60)
print("Observability workflow verified.")
print("=" * 60)
