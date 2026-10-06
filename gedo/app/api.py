"""FastAPI application for Gedo — Vanguard's API gateway and orchestration layer."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from .commands import VoiceCommandDispatcher, UnknownCommandError
from .orchestrator import AsyncSynchronizedVanguard
from .state import SystemState, JobStatus, get_system_state

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# --- Request / response models ---


class SubmitJobRequest(BaseModel):
    task_type: str = Field(..., description="Type of task to execute")
    payload: dict = Field(default_factory=dict, description="Task payload")


class JobResponse(BaseModel):
    job_id: str
    status: str


class JobDetailResponse(BaseModel):
    id: str
    task_type: str
    status: str
    result: dict | None = None
    error: str | None = None


class VoiceCommandRequest(BaseModel):
    text: str = Field(..., description="Transcribed voice command text")


class VoiceCommandResponse(BaseModel):
    action: str
    message: str = ""
    job_id: str | None = None
    error: str | None = None


class HealthResponse(BaseModel):
    status: str = "ok"
    service: str = "gedo"
    version: str = "1.0.0"


# --- Application state ---


class AppState:
    def __init__(self) -> None:
        self.vanguard: AsyncSynchronizedVanguard | None = None
        self.dispatcher: VoiceCommandDispatcher | None = None


app_state = AppState()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    state = get_system_state()
    app_state.vanguard = AsyncSynchronizedVanguard(state=state)
    app_state.dispatcher = VoiceCommandDispatcher(state=state)
    await app_state.vanguard.hermes.connect()
    logger.info("Gedo started — Vanguard orchestrator initialized")
    yield
    # Shutdown
    if app_state.vanguard:
        await app_state.vanguard.shutdown()
    logger.info("Gedo shutdown complete")


app = FastAPI(
    title="Gedo",
    description="Asynchronous execution pipelines and agent logic for Vanguard",
    version="1.0.0",
    lifespan=lifespan,
)


# --- Endpoints ---


@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse()


@app.post("/jobs", response_model=JobResponse, status_code=201)
async def submit_job(req: SubmitJobRequest) -> JobResponse:
    if not app_state.vanguard:
        raise HTTPException(503, "Vanguard orchestrator not initialized")
    job_id = await app_state.vanguard.submit(req.task_type, req.payload)
    return JobResponse(job_id=job_id, status=JobStatus.PENDING.value)


@app.get("/jobs", response_model=list[JobDetailResponse])
async def list_jobs() -> list[JobDetailResponse]:
    if not app_state.vanguard:
        raise HTTPException(503, "Vanguard orchestrator not initialized")
    jobs = await app_state.vanguard.state.list_jobs()
    return [
        JobDetailResponse(
            id=j.id,
            task_type=j.task_type,
            status=j.status.value,
            result=j.result,
            error=j.error,
        )
        for j in jobs
    ]


@app.get("/jobs/{job_id}", response_model=JobDetailResponse)
async def get_job(job_id: str) -> JobDetailResponse:
    if not app_state.vanguard:
        raise HTTPException(503, "Vanguard orchestrator not initialized")
    job = await app_state.vanguard.state.get_job(job_id)
    if job is None:
        raise HTTPException(404, f"Job {job_id} not found")
    return JobDetailResponse(
        id=job.id,
        task_type=job.task_type,
        status=job.status.value,
        result=job.result,
        error=job.error,
    )


@app.post("/jobs/{job_id}/cancel", response_model=JobResponse)
async def cancel_job(job_id: str) -> JobResponse:
    if not app_state.vanguard:
        raise HTTPException(503, "Vanguard orchestrator not initialized")
    cancelled = await app_state.vanguard.cancel_job(job_id)
    if not cancelled:
        raise HTTPException(409, f"Could not cancel job {job_id}")
    return JobResponse(job_id=job_id, status=JobStatus.CANCELLED.value)


@app.post("/voice", response_model=VoiceCommandResponse)
async def voice_command(req: VoiceCommandRequest) -> VoiceCommandResponse:
    if not app_state.dispatcher:
        raise HTTPException(503, "Voice command dispatcher not initialized")
    try:
        result = await app_state.dispatcher.dispatch(req.text)
    except UnknownCommandError as e:
        return VoiceCommandResponse(action="error", error=str(e))
    return VoiceCommandResponse(
        action=result.get("action", "unknown"),
        message=result.get("message", ""),
        job_id=result.get("job_id"),
        error=result.get("error"),
    )
