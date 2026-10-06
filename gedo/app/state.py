"""SystemState — synchronized job state with transitions and persistence."""

from __future__ import annotations

import asyncio
import json
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

import uuid


class JobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


# Valid status transitions
_TRANSITIONS: dict[JobStatus, set[JobStatus]] = {
    JobStatus.PENDING: {JobStatus.RUNNING, JobStatus.CANCELLED},
    JobStatus.RUNNING: {JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED},
    JobStatus.COMPLETED: set(),
    JobStatus.FAILED: set(),
    JobStatus.CANCELLED: set(),
}


@dataclass
class Job:
    id: str
    task_type: str
    payload: dict[str, Any]
    status: JobStatus = JobStatus.PENDING
    result: dict[str, Any] | None = None
    error: str | None = None
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "task_type": self.task_type,
            "payload": self.payload,
            "status": self.status.value,
            "result": self.result,
            "error": self.error,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Job":
        return cls(
            id=data["id"],
            task_type=data["task_type"],
            payload=data["payload"],
            status=JobStatus(data["status"]),
            result=data.get("result"),
            error=data.get("error"),
            created_at=data.get("created_at", time.time()),
            updated_at=data.get("updated_at", time.time()),
        )


class InvalidTransitionError(Exception):
    """Raised when an invalid status transition is attempted."""


class SystemState:
    """Async-synchronized job state manager.

    Maintains in-memory job state with an asyncio lock for concurrent access.
    Optionally persists state to a JSON file.
    """

    def __init__(self, persist_path: Path | None = None) -> None:
        self._jobs: dict[str, Job] = {}
        self._lock = asyncio.Lock()
        self._persist_path = persist_path
        if persist_path and persist_path.exists():
            self._load()

    async def create_job(
        self, task_type: str, payload: dict[str, Any] | None = None
    ) -> Job:
        async with self._lock:
            job = Job(
                id=str(uuid.uuid4()),
                task_type=task_type,
                payload=payload or {},
            )
            self._jobs[job.id] = job
            self._persist()
            return job

    async def transition(
        self,
        job_id: str,
        new_status: JobStatus,
        result: dict[str, Any] | None = None,
        error: str | None = None,
    ) -> Job:
        async with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                raise KeyError(f"Job {job_id} not found")
            if new_status not in _TRANSITIONS.get(job.status, set()):
                raise InvalidTransitionError(
                    f"Cannot transition from {job.status.value} to {new_status.value}"
                )
            job.status = new_status
            if result is not None:
                job.result = result
            if error is not None:
                job.error = error
            job.updated_at = time.time()
            self._persist()
            return job

    async def get_job(self, job_id: str) -> Job | None:
        async with self._lock:
            return self._jobs.get(job_id)

    async def list_jobs(self) -> list[Job]:
        async with self._lock:
            return list(self._jobs.values())

    def _persist(self) -> None:
        if not self._persist_path:
            return
        data = {jid: job.to_dict() for jid, job in self._jobs.items()}
        self._persist_path.write_text(json.dumps(data, indent=2))

    def _load(self) -> None:
        if not self._persist_path or not self._persist_path.exists():
            return
        data = json.loads(self._persist_path.read_text())
        self._jobs = {jid: Job.from_dict(jd) for jid, jd in data.items()}


# Global singleton instance
_system_state: SystemState | None = None


def get_system_state() -> SystemState:
    global _system_state
    if _system_state is None:
        _system_state = SystemState()
    return _system_state
