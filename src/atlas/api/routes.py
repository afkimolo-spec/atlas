from __future__ import annotations

from typing import Any

from atlas.core.health import HealthChecker
from atlas.planning import TaskStage
from atlas.security import (
    Credentials,
    SecurityService,
)
from atlas.workflows import Workflow


workflow = Workflow()
security = SecurityService()
health = HealthChecker()


def authenticate(
    username: str,
    password: str,
):
    return security.authenticate(
        Credentials(
            username=username,
            password=password,
        )
    )


def plan_task(
    username: str,
    password: str,
    task: str,
    *,
    research: bool = False,
    architecture: bool = True,
    development: bool = True,
    review: bool = True,
    operations: bool = True,
) -> dict[str, Any]:
    principal = authenticate(
        username,
        password,
    )

    security.authorize(
        principal,
        "plan",
    )

    plan = workflow.plan(
        task,
        research=research,
        architecture=architecture,
        development=development,
        review=review,
        operations=operations,
    )

    return {
        "task": plan.task,
        "stages": [
            stage.value
            for stage in plan.stages
        ],
    }


def execute_task(
    username: str,
    password: str,
    task: str,
    *,
    research: bool = False,
    architecture: bool = True,
    development: bool = True,
    review: bool = True,
    operations: bool = True,
) -> dict[str, Any]:
    principal = authenticate(
        username,
        password,
    )

    security.authorize(
        principal,
        "execute",
    )

    plan = workflow.plan(
        task,
        research=research,
        architecture=architecture,
        development=development,
        review=review,
        operations=operations,
    )

    result = workflow.execute_plan(
        plan
    )

    return {
        "session_id": result.session_id,
        "trace_id": result.trace_id,
        "status": result.status,
        "execution_state": result.execution_state,
        "succeeded": result.succeeded,
        "outputs": result.outputs,
    }


def resume_execution(
    username: str,
    password: str,
    task: str,
    execution_id: str,
    *,
    research: bool = False,
    architecture: bool = True,
    development: bool = True,
    review: bool = True,
    operations: bool = True,
) -> dict[str, Any]:
    principal = authenticate(
        username,
        password,
    )

    security.authorize(
        principal,
        "recover",
    )

    plan = workflow.plan(
        task,
        research=research,
        architecture=architecture,
        development=development,
        review=review,
        operations=operations,
    )

    result = workflow.resume_plan(
        plan,
        execution_id,
    )

    return {
        "session_id": result.session_id,
        "trace_id": result.trace_id,
        "status": result.status,
        "execution_state": result.execution_state,
        "succeeded": result.succeeded,
        "outputs": result.outputs,
    }


def execution_status(
    username: str,
    password: str,
    execution_id: str,
) -> dict[str, Any]:
    principal = authenticate(
        username,
        password,
    )

    security.authorize(
        principal,
        "read",
    )

    execution = (
        workflow.execution_store.restore(
            execution_id,
            _plan_for_status(execution_id),
        )
    )

    if execution is None:
        raise KeyError(
            f"Execution not found: {execution_id}"
        )

    return {
        "execution_id": execution_id,
        "state": execution.state.value,
        "terminal": execution.is_terminal,
        "snapshot": execution.snapshot(),
    }


def _plan_for_status(
    execution_id: str,
):
    record = workflow.execution_store.load(
        execution_id
    )

    if record is None:
        raise KeyError(
            f"Execution not found: {execution_id}"
        )

    stage_names = [
        name
        for name in record.get(
            "stages",
            {},
        )
    ]

    stage_map = {
        TaskStage.RESEARCH,
        TaskStage.ARCHITECTURE,
        TaskStage.DEVELOPMENT,
        TaskStage.REVIEW,
        TaskStage.OPERATIONS,
    }

    selected = [
        TaskStage(name)
        for name in stage_names
        if TaskStage(name) in stage_map
    ]

    flags = {
        TaskStage.RESEARCH: False,
        TaskStage.ARCHITECTURE: False,
        TaskStage.DEVELOPMENT: False,
        TaskStage.REVIEW: False,
        TaskStage.OPERATIONS: False,
    }

    for stage in selected:
        flags[stage] = True

    task = (
        record.get(
            "task",
            "Restored Atlas execution",
        )
    )

    return workflow.plan(
        task,
        research=flags[TaskStage.RESEARCH],
        architecture=flags[TaskStage.ARCHITECTURE],
        development=flags[TaskStage.DEVELOPMENT],
        review=flags[TaskStage.REVIEW],
        operations=flags[TaskStage.OPERATIONS],
    )


def feedback(
    username: str,
    password: str,
    *,
    execution_id: str | None = None,
    stage: str | None = None,
) -> dict[str, Any]:
    principal = authenticate(
        username,
        password,
    )

    security.authorize(
        principal,
        "read",
    )

    store = workflow.feedback.store

    return {
        "execution": (
            store.execution(execution_id)
            if execution_id
            else None
        ),
        "stages": (
            store.stages(execution_id)
            if execution_id
            else []
        ),
        "stage_summary": store.summary(
            stage=stage
        ),
        "execution_summary": (
            store.execution_summary()
        ),
        "optimization_signals": (
            store.optimization_signals()
        ),
    }


def telemetry(
    username: str,
    password: str,
    trace_id: str,
) -> dict[str, Any]:
    principal = authenticate(
        username,
        password,
    )

    security.authorize(
        principal,
        "read",
    )

    store = workflow.telemetry.store

    trace = store.trace(
        trace_id
    )

    if trace is None:
        raise KeyError(
            f"Trace not found: {trace_id}"
        )

    return {
        "trace": trace,
        "spans": store.spans(
            trace_id
        ),
    }


def health_status() -> dict[str, Any]:
    return health.check()
