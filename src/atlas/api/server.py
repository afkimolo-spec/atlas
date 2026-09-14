from __future__ import annotations

from pathlib import Path
from typing import Any

from atlas.api import routes


UI_ROOT = (
    Path(__file__).resolve().parent.parent / "ui"
)

UI_INDEX = UI_ROOT / "index.html"


from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel


app = FastAPI(
    title="Atlas API",
    version="0.1.0",
    description=(
        "Atlas autonomous engineering control plane."
    ),
)


class AuthRequest(BaseModel):
    username: str
    password: str


class TaskRequest(AuthRequest):
    task: str
    research: bool = False
    architecture: bool = True
    development: bool = True
    review: bool = True
    operations: bool = True


class ResumeRequest(AuthRequest):
    task: str
    execution_id: str
    research: bool = False
    architecture: bool = True
    development: bool = True
    review: bool = True
    operations: bool = True


class ExecutionStatusRequest(AuthRequest):
    execution_id: str


class FeedbackRequest(AuthRequest):
    execution_id: str | None = None
    stage: str | None = None


class TelemetryRequest(AuthRequest):
    trace_id: str


def _call(
    function,
    **kwargs: Any,
):
    try:
        return function(**kwargs)

    except KeyError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc

    except PermissionError as exc:
        raise HTTPException(
            status_code=403,
            detail=str(exc),
        ) from exc

    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc


@app.get("/")
def get_ui():
    if not UI_INDEX.exists():
        raise HTTPException(
            status_code=500,
            detail="Atlas UI is not installed.",
        )

    return FileResponse(
        UI_INDEX,
        media_type="text/html",
    )


@app.get("/health")
def get_health():
    return routes.health_status()


@app.get("/ready")
def get_readiness():
    result = routes.health_status()

    if result["status"] != "healthy":
        raise HTTPException(
            status_code=503,
            detail=result,
        )

    return {
        "status": "ready",
        "checks": result["checks"],
        "checked_at": result["checked_at"],
    }


@app.post("/v1/plan")
def create_plan(request: TaskRequest):
    return _call(
        routes.plan_task,
        username=request.username,
        password=request.password,
        task=request.task,
        research=request.research,
        architecture=request.architecture,
        development=request.development,
        review=request.review,
        operations=request.operations,
    )


@app.post("/v1/executions")
def create_execution(request: TaskRequest):
    return _call(
        routes.execute_task,
        username=request.username,
        password=request.password,
        task=request.task,
        research=request.research,
        architecture=request.architecture,
        development=request.development,
        review=request.review,
        operations=request.operations,
    )


@app.post("/v1/executions/resume")
def resume_execution(request: ResumeRequest):
    return _call(
        routes.resume_execution,
        username=request.username,
        password=request.password,
        task=request.task,
        execution_id=request.execution_id,
        research=request.research,
        architecture=request.architecture,
        development=request.development,
        review=request.review,
        operations=request.operations,
    )


@app.post("/v1/executions/status")
def execution_status(
    request: ExecutionStatusRequest,
):
    return _call(
        routes.execution_status,
        username=request.username,
        password=request.password,
        execution_id=request.execution_id,
    )


@app.post("/v1/feedback")
def get_feedback(
    request: FeedbackRequest,
):
    return _call(
        routes.feedback,
        username=request.username,
        password=request.password,
        execution_id=request.execution_id,
        stage=request.stage,
    )


@app.post("/v1/telemetry")
def get_telemetry(
    request: TelemetryRequest,
):
    return _call(
        routes.telemetry,
        username=request.username,
        password=request.password,
        trace_id=request.trace_id,
    )


def main() -> None:
    import uvicorn

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8080,
        reload=False,
    )


if __name__ == "__main__":
    main()
