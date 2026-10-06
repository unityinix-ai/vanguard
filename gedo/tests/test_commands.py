"""Tests for VoiceCommandDispatcher."""

import pytest

from app.commands import VoiceCommandDispatcher, UnknownCommandError
from app.state import SystemState


@pytest.fixture
def dispatcher():
    state = SystemState()
    return VoiceCommandDispatcher(state=state)


def test_parse_run(dispatcher):
    cmd = dispatcher.parse("run llm_completion --model gpt-4")
    assert cmd.action == "run"
    assert cmd.target == "llm_completion"
    assert "--model" in cmd.args


def test_parse_status(dispatcher):
    cmd = dispatcher.parse("status abc-123")
    assert cmd.action == "status"
    assert cmd.target == "abc-123"


def test_parse_list(dispatcher):
    cmd = dispatcher.parse("list")
    assert cmd.action == "list"


def test_parse_cancel(dispatcher):
    cmd = dispatcher.parse("cancel job-456 timeout")
    assert cmd.action == "cancel"
    assert cmd.target == "job-456"
    assert "timeout" in cmd.args


def test_parse_help(dispatcher):
    cmd = dispatcher.parse("help")
    assert cmd.action == "help"


def test_parse_unknown(dispatcher):
    with pytest.raises(UnknownCommandError):
        dispatcher.parse("foobar baz")


def test_parse_empty(dispatcher):
    with pytest.raises(UnknownCommandError):
        dispatcher.parse("")


async def test_dispatch_run(dispatcher):
    result = await dispatcher.dispatch("run test_task")
    assert result["action"] == "run"
    assert "job_id" in result


async def test_dispatch_status_not_found(dispatcher):
    result = await dispatcher.dispatch("status nonexistent")
    assert result["action"] == "status"
    assert "error" in result


async def test_dispatch_list(dispatcher):
    result = await dispatcher.dispatch("list")
    assert result["action"] == "list"
    assert result["count"] == "0"
