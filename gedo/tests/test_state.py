"""Tests for SystemState job lifecycle and transitions."""

import asyncio
import pytest

from app.state import (
    SystemState,
    Job,
    JobStatus,
    InvalidTransitionError,
)


@pytest.fixture
def state():
    return SystemState()


async def test_create_job(state):
    job = await state.create_job("llm_completion", {"prompt": "hello"})
    assert job.task_type == "llm_completion"
    assert job.status == JobStatus.PENDING
    assert job.payload == {"prompt": "hello"}
    assert job.id is not None


async def test_valid_transition_pending_to_running(state):
    job = await state.create_job("test")
    updated = await state.transition(job.id, JobStatus.RUNNING)
    assert updated.status == JobStatus.RUNNING


async def test_valid_transition_running_to_completed(state):
    job = await state.create_job("test")
    await state.transition(job.id, JobStatus.RUNNING)
    updated = await state.transition(
        job.id, JobStatus.COMPLETED, result={"output": "done"}
    )
    assert updated.status == JobStatus.COMPLETED
    assert updated.result == {"output": "done"}


async def test_invalid_transition_pending_to_completed(state):
    job = await state.create_job("test")
    with pytest.raises(InvalidTransitionError):
        await state.transition(job.id, JobStatus.COMPLETED)


async def test_invalid_transition_from_terminal(state):
    job = await state.create_job("test")
    await state.transition(job.id, JobStatus.RUNNING)
    await state.transition(job.id, JobStatus.COMPLETED)
    with pytest.raises(InvalidTransitionError):
        await state.transition(job.id, JobStatus.FAILED)


async def test_get_job_not_found(state):
    job = await state.get_job("nonexistent")
    assert job is None


async def test_list_jobs(state):
    await state.create_job("type_a")
    await state.create_job("type_b")
    jobs = await state.list_jobs()
    assert len(jobs) == 2


async def test_cancel_from_pending(state):
    job = await state.create_job("test")
    updated = await state.transition(job.id, JobStatus.CANCELLED, error="user")
    assert updated.status == JobStatus.CANCELLED
    assert updated.error == "user"


async def test_persistence(tmp_path):
    persist_path = tmp_path / "state.json"
    s1 = SystemState(persist_path=persist_path)
    job = await s1.create_job("persisted")
    await s1.transition(job.id, JobStatus.RUNNING)

    # New instance loads from file
    s2 = SystemState(persist_path=persist_path)
    loaded = await s2.get_job(job.id)
    assert loaded is not None
    assert loaded.status == JobStatus.RUNNING
