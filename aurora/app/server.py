"""Aurora WebSocket server — multi-modal LLM execution backbone.

Provides a WebSocket interface for real-time execution requests,
with model routing and runtime guard enforcement.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from .compliance import ComplianceLevel, get_compliance_logs
from .guard import GuardViolation, SoulRuntimeGuard
from .routing import create_default_router, ModelRouter

logger = logging.getLogger(__name__)


class AuroraServer:
    """WebSocket-based execution server with routing and guard enforcement."""

    def __init__(
        self,
        router: ModelRouter | None = None,
        guard: SoulRuntimeGuard | None = None,
    ) -> None:
        self.router = router or create_default_router()
        self.guard = guard or SoulRuntimeGuard()
        self.compliance = get_compliance_logs()
        self._clients: set[Any] = set()

    async def handle_connection(self, websocket: Any) -> None:
        """Handle an incoming WebSocket connection."""
        self._clients.add(websocket)
        self.compliance.log(
            event_type="connection_open",
            level=ComplianceLevel.INFO,
            message=f"Client connected, total: {len(self._clients)}",
        )
        try:
            await websocket.accept()
            await websocket.send_text(
                json.dumps(
                    {"type": "welcome", "message": "Connected to Aurora"}
                )
            )

            async for message in websocket.iter_text():
                await self._handle_message(websocket, message)

        except Exception as e:
            logger.exception("Connection error: %s", e)
            self.compliance.log(
                event_type="connection_error",
                level=ComplianceLevel.WARNING,
                message=str(e),
            )
        finally:
            self._clients.discard(websocket)
            self.compliance.log(
                event_type="connection_close",
                level=ComplianceLevel.INFO,
                message=f"Client disconnected, total: {len(self._clients)}",
            )

    async def _handle_message(self, websocket: Any, message: str) -> None:
        """Process an incoming message from a client."""
        try:
            data = json.loads(message)
        except json.JSONDecodeError:
            await websocket.send_text(
                json.dumps({"type": "error", "message": "Invalid JSON"})
            )
            return

        msg_type = data.get("type", "execute")
        agent_id = data.get("agent_id", "")
        task_type = data.get("task_type", "default")
        payload = data.get("payload", "").encode() if isinstance(
            data.get("payload"), str
        ) else json.dumps(data.get("payload", {})).encode()
        metadata = data.get("metadata", {})

        # Validate through the guard
        try:
            self.guard.validate(
                agent_id=agent_id,
                task_type=task_type,
                payload=payload,
                metadata=metadata,
            )
        except GuardViolation as e:
            await websocket.send_text(
                json.dumps(
                    {
                        "type": "error",
                        "message": f"Guard violation: {e}",
                    }
                )
            )
            return

        # Route to provider
        provider = self.router.resolve(task_type)
        if provider is None:
            await websocket.send_text(
                json.dumps(
                    {
                        "type": "error",
                        "message": f"No provider for task type: {task_type}",
                    }
                )
            )
            return

        # Execute (mock for now — real implementation would call the provider)
        result = await self._execute(provider, agent_id, task_type, payload)

        await websocket.send_text(
            json.dumps(
                {
                    "type": "result",
                    "agent_id": agent_id,
                    "task_type": task_type,
                    "provider": provider.name,
                    "result": result,
                }
            )
        )

    async def _execute(
        self,
        provider: Any,
        agent_id: str,
        task_type: str,
        payload: bytes,
    ) -> dict[str, Any]:
        """Execute a task against a provider (mock implementation)."""
        await asyncio.sleep(0.01)  # simulate latency
        return {
            "status": "completed",
            "provider": provider.name,
            "model": provider.model,
            "output": "Mock execution completed",
        }

    def get_status(self) -> dict[str, Any]:
        """Return server status information."""
        return {
            "status": "ok",
            "service": "aurora",
            "version": "1.0.0",
            "clients_connected": len(self._clients),
            "providers": [p.name for p in self.router.list_providers()],
        }


# Factory for FastAPI / uvicorn integration
def create_app() -> Any:
    """Create a FastAPI application wrapping the Aurora server."""
    from fastapi import FastAPI, WebSocket

    server = AuroraServer()

    app = FastAPI(
        title="Aurora",
        description="Multi-modal LLM execution backbone and agent routing",
        version="1.0.0",
    )

    @app.get("/health")
    async def health() -> dict:
        return server.get_status()

    @app.websocket("/ws")
    async def websocket_endpoint(websocket: WebSocket) -> None:
        await server.handle_connection(websocket)

    return app
