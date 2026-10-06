"""SoulRuntimeGuard — runtime policy enforcement for agent execution.

Validates requests against configurable policies before execution proceeds.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .compliance import ComplianceLevel, get_compliance_logs


@dataclass
class Policy:
    name: str = "default"
    max_payload_bytes: int = 10 * 1024 * 1024  # 10 MB
    allowed_task_types: list[str] = field(
        default_factory=lambda: ["llm_completion", "voice_command", "default"]
    )
    blocked_agents: list[str] = field(default_factory=list)
    require_agent_id: bool = True
    allow_anonymous: bool = False


class GuardViolation(Exception):
    """Raised when a request violates a runtime guard policy."""


class SoulRuntimeGuard:
    """Validates execution requests against configured policies.

    The guard checks:
    - Agent ID presence and blocklist
    - Task type allowlist
    - Payload size limits
    - Authentication requirements
    """

    def __init__(self, policy: Policy | None = None) -> None:
        self.policy = policy or Policy()
        self.compliance = get_compliance_logs()

    def validate(
        self,
        agent_id: str,
        task_type: str,
        payload: bytes = b"",
        metadata: dict[str, Any] | None = None,
    ) -> bool:
        """Validate a request. Returns True if allowed, raises GuardViolation if not."""
        metadata = metadata or {}

        # Check agent ID requirement
        if self.policy.require_agent_id and not agent_id:
            self.compliance.log(
                event_type="guard_violation",
                level=ComplianceLevel.VIOLATION,
                agent_id=agent_id,
                message="Missing required agent_id",
                metadata=metadata,
            )
            raise GuardViolation("agent_id is required")

        # Check blocklist
        if agent_id in self.policy.blocked_agents:
            self.compliance.log(
                event_type="guard_violation",
                level=ComplianceLevel.BLOCKED,
                agent_id=agent_id,
                message=f"Agent {agent_id} is blocked",
                metadata=metadata,
            )
            raise GuardViolation(f"Agent '{agent_id}' is blocked")

        # Check task type
        if task_type not in self.policy.allowed_task_types:
            self.compliance.log(
                event_type="guard_violation",
                level=ComplianceLevel.VIOLATION,
                agent_id=agent_id,
                message=f"Task type '{task_type}' not allowed",
                metadata=metadata,
            )
            raise GuardViolation(
                f"Task type '{task_type}' is not in the allowed list: "
                f"{self.policy.allowed_task_types}"
            )

        # Check payload size
        payload_size = len(payload)
        if payload_size > self.policy.max_payload_bytes:
            self.compliance.log(
                event_type="guard_violation",
                level=ComplianceLevel.VIOLATION,
                agent_id=agent_id,
                message=f"Payload size {payload_size} exceeds limit {self.policy.max_payload_bytes}",
                metadata={**metadata, "payload_size": payload_size},
            )
            raise GuardViolation(
                f"Payload size {payload_size} exceeds maximum {self.policy.max_payload_bytes}"
            )

        # All checks passed
        self.compliance.log(
            event_type="guard_pass",
            level=ComplianceLevel.INFO,
            agent_id=agent_id,
            message=f"Request validated for agent {agent_id}, task_type {task_type}",
            metadata=metadata,
        )
        return True

    def update_policy(self, **kwargs: Any) -> None:
        """Update guard policy fields."""
        if "max_payload_bytes" in kwargs:
            self.policy.max_payload_bytes = kwargs["max_payload_bytes"]
        if "allowed_task_types" in kwargs:
            self.policy.allowed_task_types = kwargs["allowed_task_types"]
        if "blocked_agents" in kwargs:
            self.policy.blocked_agents = kwargs["blocked_agents"]
        if "require_agent_id" in kwargs:
            self.policy.require_agent_id = kwargs["require_agent_id"]
