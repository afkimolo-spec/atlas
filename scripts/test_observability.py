from __future__ import annotations

import tempfile
from pathlib import Path

from atlas.core.health import HealthChecker
from atlas.core.telemetry import (
    TelemetryRecorder,
    TelemetryStore,
)


print("=" * 60)
print("ATLAS OBSERVABILITY")
print("=" * 60)

with tempfile.TemporaryDirectory() as directory:
    database = Path(directory) / "atlas.db"

    store = TelemetryStore(database)
    recorder = TelemetryRecorder(store)

    trace_id = "trace-observability"
    execution_id = "execution-observability"

    recorder.start_trace(
        trace_id,
        execution_id,
        metadata={
            "task": "observability verification",
        },
    )

    execution_span = recorder.start_span(
        trace_id,
        execution_id,
        name="workflow.execute",
        kind="execution",
    )

    development_span = recorder.start_span(
        trace_id,
        execution_id,
        name="stage.development",
        kind="stage",
        stage="development",
        agent="developer",
        attributes={
            "attempt": 1,
        },
    )

    recorder.finish_span(
        development_span,
        status="completed",
        attributes={
            "attempt": 1,
        },
    )

    review_span = recorder.start_span(
        trace_id,
        execution_id,
        name="stage.review",
        kind="stage",
        stage="review",
        agent="reviewer",
        attributes={
            "attempt": 1,
        },
    )

    recorder.finish_span(
        review_span,
        status="failed",
        error="simulated review failure",
    )

    recorder.finish_span(
        execution_span,
        status="failed",
        error="simulated review failure",
    )

    recorder.finish_trace(
        trace_id,
        status="failed",
        error="simulated review failure",
    )

    trace = store.trace(trace_id)

    assert trace is not None
    assert trace["execution_id"] == execution_id
    assert trace["status"] == "failed"

    spans = store.spans(trace_id)

    assert len(spans) == 3

    assert spans[0]["kind"] == "execution"
    assert spans[0]["status"] == "failed"

    assert spans[1]["stage"] == "development"
    assert spans[1]["status"] == "completed"

    assert spans[2]["stage"] == "review"
    assert spans[2]["status"] == "failed"

    failures = store.failures(
        execution_id=execution_id
    )

    assert len(failures) == 2

    metrics = store.execution_metrics()

    assert metrics["executions"] == 1
    assert metrics["failed_executions"] == 1
    assert metrics["spans"] == 3
    assert metrics["completed_spans"] == 1
    assert metrics["failed_spans"] == 2

    stage_metrics = store.stage_metrics()

    assert len(stage_metrics) == 2

    development_metrics = next(
        item
        for item in stage_metrics
        if item["stage"] == "development"
    )

    review_metrics = next(
        item
        for item in stage_metrics
        if item["stage"] == "review"
    )

    assert development_metrics["executions"] == 1
    assert development_metrics["completed"] == 1
    assert development_metrics["failed"] == 0

    assert review_metrics["executions"] == 1
    assert review_metrics["completed"] == 0
    assert review_metrics["failed"] == 1

    development_only = store.stage_metrics(
        stage="development"
    )

    assert len(development_only) == 1
    assert development_only[0]["stage"] == "development"

    restarted = TelemetryStore(database)

    restored = restarted.trace(
        trace_id
    )

    assert restored is not None
    assert restored["status"] == "failed"

    restored_spans = restarted.spans(
        trace_id
    )

    assert len(restored_spans) == 3

    health = HealthChecker(
        database
    )

    database_health = health.check_database()

    assert database_health.status == "healthy"

print("Tracing          : verified")
print("Stage spans      : verified")
print("Failure analysis : verified")
print("Metrics          : verified")
print("Stage analytics  : verified")
print("Restart survival : verified")
print("Database health  : verified")
print("=" * 60)
print("Observability verified.")
print("=" * 60)
