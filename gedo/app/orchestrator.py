"""AsyncSynchronizedVanguard — orchestrates job execution across Hermes/Aurora."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from .state import SystemState, JobStatus

logger = logging.getLogger(__name__)


class HermesClient:
    """Minimal Hermes gRPC client stub.

    In production this would use a generated gRPC stub from vanguard.proto.
    For the initial implementation it provides an async-compatible interface
    that can be replaced with a real gRPC channel.
    """

    def __init__(self, host: str = "hermes", port: int = 50051) -> None:
        self.host = host
        self.port = port
        self._channel: Any = None

    async def connect(self) -> None:
        logger.info("Connecting to Hermes at %s:%d", self.host, self.port)
        # Real implementation: grpc.aio.insecure_channel(f"{self.host}:{self.port}")

    async def execute(
        self, agent_id: str, task_id: str, task_type: str, payload: bytes
    ) -> dict[str, Any]:
        """Stub execution — returns a mock result."""
        await asyncio.sleep(0.01)  # simulate network latency
        return {
            "task_id": task_id,
            "success": True,
            "output": b'{"response": "mock execution completed"}',
            "error": "",
            "duration_ms": 10,
        }

    async def cancel(self, task_id: str, reason: str = "user_requested") -> bool:
        logger.info("Cancelling task %s: %s", task_id, reason)
        return True

    async def close(self) -> None:
        if self._channel:
            await self._channel.close()


class AsyncSynchronizedVanguard:
    """Top-level orchestrator for the Vanguard system.

    Coordinates job lifecycle:
    1. Creates jobs in SystemState
    2. Dispatches execution to Hermes
    3. Transitions job status based on results
    """

    def __init__(
        self,
        state: SystemState | None = None,
        hermes: HermesClient | None = None,
    ) -> None:
        from .state import get_system_state

        self.state = state or get_system_state()
        self.hermes = hermes or HermesClient()

    async def submit(
        self, task_type: str, payload: dict[str, Any] | None = None
    ) -> str:
        """Submit a job for execution. Returns the job ID."""
        import json

        job = await self.state.create_job(task_type, payload)
        logger.info("Submitted job %s (%s)", job.id, task_type)

        # Transition to running
        await self.state.transition(job.id, JobStatus.RUNNING)

        # Dispatch to Hermes asynchronously
        asyncio.create_task(self._execute(job.id, task_type, payload or {}))

        return job.id

    async def _execute(
        self, job_id: str, task_type: str, payload: dict[str, Any]
    ) -> None:
        """Execute a job and update state based on the result."""
        import json

        try:
            result = await self.hermes.execute(
                agent_id=payload.get("agent_id", "default"),
                task_id=job_id,
                task_type=task_type,
                payload=json.dumps(payload).encode(),
            )

            if result.get("success"):
                output = json.loads(result.get("output", b"{}").decode())
                await self.state.transition(
                    job_id,
                    JobStatus.COMPLETED,
                    result=output,
                )
            else:
                await self.state.transition(
                    job_id,
                    JobStatus.FAILED,
                    error=result.get("error", "unknown"),
                )
        except Exception as e:
            logger.exception("Job %s failed: %s", job_id, e)
            await self.state.transition(job_id, JobStatus.FAILED, error=str(e))

    async def cancel_job(self, job_id: str, reason: str = "user_requested") -> bool:
        """Cancel a running job."""
        cancelled = await self.hermes.cancel(job_id, reason)
        if cancelled:
            try:
                await self.state.transition(job_id, JobStatus.CANCELLED, error=reason)
            except Exception:
                pass  # job may already be in a terminal state
        return cancelled

    async def shutdown(self) -> None:
        """Gracefully shut down the orchestrator."""
        await self.hermes.close()
