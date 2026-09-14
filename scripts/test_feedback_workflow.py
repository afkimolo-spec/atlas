from __future__ import annotations

import tempfile
from pathlib import Path

from atlas.core.execution_store import ExecutionStore
from atlas.core.feedback import FeedbackCollector
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
        return "Feedback workflow operational."


print("=" * 60)
print("ATLAS FEEDBACK WORKFLOW INTEGRATION")
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

    fake = FakeAgent()

    workflow.researcher = fake
    workflow.architect = fake
    workflow.developer = fake
    workflow.reviewer = fake
    workflow.operator = fake

    plan = TaskPlanner().plan(
        "Feedback workflow integration",
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
    assert result.succeeded
    assert (
        result.outputs["architecture"]
        == "Feedback workflow operational."
    )

    feedback = workflow.feedback.store

    execution = feedback.execution(
        result.session_id
    )

    assert execution is not None
    assert execution["status"] == "completed"
    assert execution["completed_stages"] == 1
    assert execution["failed_stages"] == 0

    stages = feedback.stages(
        result.session_id
    )

    assert len(stages) == 1
    assert stages[0]["stage"] == "architecture"
    assert stages[0]["outcome"] == "completed"
    assert stages[0]["attempt"] == 1
    assert stages[0]["duration_ms"] >= 0

print("Workflow execution : verified")
print("Stage feedback     : verified")
print("Execution feedback : verified")
print("Persistence        : verified")
print("=" * 60)
print("Feedback workflow integration verified.")
print("=" * 60)
