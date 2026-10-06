"""RuntimeComplianceLogs — structured compliance event logging."""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class ComplianceLevel(str, Enum):
    INFO = "info"
    WARNING = "warning"
    VIOLATION = "violation"
    BLOCKED = "blocked"


@dataclass
class ComplianceEvent:
    event_id: str
    timestamp: float = field(default_factory=time.time)
    level: ComplianceLevel = ComplianceLevel.INFO
    event_type: str = ""
    agent_id: str = ""
    task_id: str = ""
    message: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["level"] = self.level.value
        return d


class RuntimeComplianceLogs:
    """Collects and emits structured compliance events.

    Events are stored in memory and optionally written to a log sink.
    """

    def __init__(self, log_file: str | None = None) -> None:
        self._events: list[ComplianceEvent] = []
        self._log_file = log_file

    def log(
        self,
        event_type: str,
        level: ComplianceLevel = ComplianceLevel.INFO,
        agent_id: str = "",
        task_id: str = "",
        message: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> ComplianceEvent:
        import uuid

        event = ComplianceEvent(
            event_id=str(uuid.uuid4()),
            level=level,
            event_type=event_type,
            agent_id=agent_id,
            task_id=task_id,
            message=message,
            metadata=metadata or {},
        )
        self._events.append(event)

        log_msg = json.dumps(event.to_dict())
        if level in (ComplianceLevel.VIOLATION, ComplianceLevel.BLOCKED):
            logger.error(log_msg)
        elif level == ComplianceLevel.WARNING:
            logger.warning(log_msg)
        else:
            logger.info(log_msg)

        self._flush()
        return event

    def get_events(
        self,
        level: ComplianceLevel | None = None,
        agent_id: str | None = None,
        task_id: str | None = None,
    ) -> list[ComplianceEvent]:
        result = self._events
        if level:
            result = [e for e in result if e.level == level]
        if agent_id:
            result = [e for e in result if e.agent_id == agent_id]
        if task_id:
            result = [e for e in result if e.task_id == task_id]
        return result

    def _flush(self) -> None:
        if not self._log_file:
            return
        with open(self._log_file, "a") as f:
            for event in self._events[-1:]:  # write only new event
                f.write(json.dumps(event.to_dict()) + "\n")


# Global instance
_compliance: RuntimeComplianceLogs | None = None


def get_compliance_logs() -> RuntimeComplianceLogs:
    global _compliance
    if _compliance is None:
        _compliance = RuntimeComplianceLogs()
    return _compliance
