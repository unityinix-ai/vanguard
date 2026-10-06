"""VoiceCommandDispatcher — text command parsing and dispatch."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Awaitable, Callable

from .state import SystemState


@dataclass
class ParsedCommand:
    action: str
    target: str | None
    args: list[str]
    raw: str


# Command patterns: action word → regex
_COMMAND_PATTERNS: dict[str, re.Pattern[str]] = {
    "run": re.compile(r"^run\s+(\S+)(?:\s+(.+))?$", re.IGNORECASE),
    "status": re.compile(r"^status\s+(\S+)$", re.IGNORECASE),
    "list": re.compile(r"^list(?:\s+(.+))?$", re.IGNORECASE),
    "cancel": re.compile(r"^cancel\s+(\S+)(?:\s+(.+))?$", re.IGNORECASE),
    "help": re.compile(r"^help$", re.IGNORECASE),
}


class UnknownCommandError(Exception):
    """Raised when a command cannot be parsed."""


class VoiceCommandDispatcher:
    """Parses transcribed text commands and dispatches them to handlers.

    Commands:
        run <task_type> [args...]   — create and dispatch a new job
        status <job_id>             — get job status
        list                         — list all jobs
        cancel <job_id> [reason]     — cancel a job
        help                         — show available commands
    """

    def __init__(self, state: SystemState) -> None:
        self.state = state

    def parse(self, text: str) -> ParsedCommand:
        text = text.strip()
        if not text:
            raise UnknownCommandError("Empty command")

        for action, pattern in _COMMAND_PATTERNS.items():
            match = pattern.match(text)
            if match:
                groups = match.groups()
                target = groups[0] if groups else None
                args_str = groups[1] if len(groups) > 1 and groups[1] else ""
                args = args_str.split() if args_str else []
                return ParsedCommand(
                    action=action,
                    target=target,
                    args=args,
                    raw=text,
                )

        raise UnknownCommandError(f"Unknown command: {text}")

    async def dispatch(self, text: str) -> dict[str, str]:
        """Parse and execute a text command. Returns a response dict."""
        cmd = self.parse(text)

        if cmd.action == "run":
            task_type = cmd.target or "default"
            payload = {"args": cmd.args} if cmd.args else {}
            job = await self.state.create_job(task_type, payload)
            return {
                "action": "run",
                "job_id": job.id,
                "message": f"Created {task_type} job {job.id}",
            }

        elif cmd.action == "status":
            if not cmd.target:
                return {"action": "status", "error": "job_id required"}
            job = await self.state.get_job(cmd.target)
            if job is None:
                return {"action": "status", "error": f"Job {cmd.target} not found"}
            return {"action": "status", "job": job.to_dict()}

        elif cmd.action == "list":
            jobs = await self.state.list_jobs()
            return {
                "action": "list",
                "jobs": [j.to_dict() for j in jobs],
                "count": str(len(jobs)),
            }

        elif cmd.action == "cancel":
            if not cmd.target:
                return {"action": "cancel", "error": "job_id required"}
            reason = " ".join(cmd.args) if cmd.args else "user_requested"
            from .state import JobStatus

            try:
                job = await self.state.transition(
                    cmd.target, JobStatus.CANCELLED, error=reason
                )
                return {"action": "cancel", "job_id": job.id, "message": "cancelled"}
            except (KeyError, Exception) as e:
                return {"action": "cancel", "error": str(e)}

        elif cmd.action == "help":
            return {
                "action": "help",
                "commands": "run, status, list, cancel, help",
            }

        return {"action": cmd.action, "error": "unhandled"}
