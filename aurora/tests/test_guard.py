"""Tests for SoulRuntimeGuard policy enforcement."""

import pytest

from app.guard import GuardViolation, SoulRuntimeGuard, Policy
from app.compliance import ComplianceLevel


@pytest.fixture
def guard():
    return SoulRuntimeGuard()


def test_validate_success(guard):
    result = guard.validate(agent_id="test-agent", task_type="llm_completion")
    assert result is True


def test_missing_agent_id(guard):
    with pytest.raises(GuardViolation, match="agent_id is required"):
        guard.validate(agent_id="", task_type="default")


def test_blocked_agent(guard):
    guard.update_policy(blocked_agents=["bad-agent"])
    with pytest.raises(GuardViolation, match="blocked"):
        guard.validate(agent_id="bad-agent", task_type="default")


def test_disallowed_task_type(guard):
    with pytest.raises(GuardViolation, match="not in the allowed list"):
        guard.validate(agent_id="test", task_type="malicious_task")


def test_payload_too_large(guard):
    guard.update_policy(max_payload_bytes=10)
    with pytest.raises(GuardViolation, match="exceeds maximum"):
        guard.validate(
            agent_id="test",
            task_type="default",
            payload=b"x" * 100,
        )


def test_compliance_event_logged(guard):
    guard.validate(agent_id="test", task_type="default")
    events = guard.compliance.get_events()
    assert len(events) >= 1
    # Should have at least one guard_pass event
    pass_events = [e for e in events if e.event_type == "guard_pass"]
    assert len(pass_events) >= 1


def test_violation_logged(guard):
    with pytest.raises(GuardViolation):
        guard.validate(agent_id="", task_type="default")

    violations = guard.compliance.get_events(level=ComplianceLevel.VIOLATION)
    assert len(violations) >= 1


def test_custom_policy():
    policy = Policy(
        name="strict",
        max_payload_bytes=100,
        allowed_task_types=["safe_task"],
        blocked_agents=["untrusted"],
        require_agent_id=True,
    )
    guard = SoulRuntimeGuard(policy=policy)

    with pytest.raises(GuardViolation):
        guard.validate(agent_id="untrusted", task_type="safe_task")

    result = guard.validate(agent_id="good", task_type="safe_task")
    assert result is True
