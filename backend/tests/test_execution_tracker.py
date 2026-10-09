"""
Comprehensive unit and integration tests for CHAI Real-Time Multi-Agent Execution Tracker.
Covers:
- Request started
- Agent started and completed
- Concurrent agent events
- Failed agent (with safe error sanitization)
- Skipped agent
- Synthesizer completion
- Reliability Monitor rejection
- Final answer available
- Unknown request ID (404)
- Client disconnect
- No duplicate execution
"""
import asyncio
import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient

from backend.core.execution_events import (
    ExecutionEvent,
    ExecutionEventManager,
    execution_event_manager,
    sanitize_error_message,
    FINALIZATION_AGENTS,
    AGENT_DISPLAY_NAMES,
)
from backend.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_mock_env(monkeypatch):
    monkeypatch.setenv("CHAI_MOCK_MODE", "true")


@pytest.mark.asyncio
async def test_request_started():
    mgr = ExecutionEventManager()
    req_id = "test-req-started-01"
    selected = ["researcher", "strategist", "synthesizer", "output_validator"]

    evt = await mgr.emit(
        request_id=req_id,
        event="request_started",
        status="running",
        selected_agents=selected,
        domain="business",
    )

    assert evt.request_id == req_id
    assert evt.event == "request_started"
    assert evt.status == "running"
    assert evt.selected_agents == selected
    assert evt.domain == "business"
    assert evt.message == "CHAI is coordinating its agents"

    session = mgr.get_session(req_id)
    assert session is not None
    assert session.selected_agents == selected
    assert len(session.events_history) == 1


@pytest.mark.asyncio
async def test_agent_started_and_completed():
    mgr = ExecutionEventManager()
    req_id = "test-agent-start-complete-02"

    evt_start = await mgr.emit(
        request_id=req_id,
        event="agent_status",
        agent="researcher",
        status="running",
    )
    assert evt_start.status == "running"
    assert evt_start.agent == "researcher"
    assert evt_start.message == "Gathering empirical evidence and domain research"

    evt_done = await mgr.emit(
        request_id=req_id,
        event="agent_status",
        agent="researcher",
        status="completed",
        duration_ms=452.3,
    )
    assert evt_done.status == "completed"
    assert evt_done.duration_ms == 452.3
    assert evt_done.agent == "researcher"
    assert not evt_done.is_finalization

    session = mgr.get_session(req_id)
    assert len(session.events_history) == 2


@pytest.mark.asyncio
async def test_concurrent_agent_events():
    mgr = ExecutionEventManager()
    req_id = "test-concurrent-agents-03"

    agents = ["researcher", "strategist", "engineer", "guardian", "security"]

    async def run_agent(agent_name: str, delay: float):
        await mgr.emit(request_id=req_id, event="agent_status", agent=agent_name, status="running")
        await asyncio.sleep(delay)
        await mgr.emit(
            request_id=req_id,
            event="agent_status",
            agent=agent_name,
            status="completed",
            duration_ms=delay * 1000,
        )

    tasks = [run_agent(a, 0.02 * (i + 1)) for i, a in enumerate(agents)]
    await asyncio.gather(*tasks)

    session = mgr.get_session(req_id)
    assert session is not None
    # Each agent emitted 2 events (running and completed) -> 10 total
    assert len(session.events_history) == 10

    completed_events = [e for e in session.events_history if e.status == "completed"]
    assert len(completed_events) == 5
    completed_agents = {e.agent for e in completed_events}
    assert completed_agents == set(agents)


@pytest.mark.asyncio
async def test_failed_agent_and_sanitization():
    mgr = ExecutionEventManager()
    req_id = "test-failed-agent-04"

    raw_error_with_key = "Connection failed with api_key=AIzaSyD-SECRET123 and Traceback line 42"
    evt_fail = await mgr.emit(
        request_id=req_id,
        event="agent_status",
        agent="engineer",
        status="failed",
        duration_ms=120.0,
        error=raw_error_with_key,
    )

    assert evt_fail.status == "failed"
    assert evt_fail.agent == "engineer"
    # Verify sanitization stripped secret and stack trace
    assert "api_key" not in evt_fail.error.lower()
    assert "secret" not in evt_fail.error.lower()
    assert "traceback" not in evt_fail.error.lower()
    assert "security" in evt_fail.error.lower() or "internal" in evt_fail.error.lower()


@pytest.mark.asyncio
async def test_skipped_agent():
    mgr = ExecutionEventManager()
    req_id = "test-skipped-agent-05"

    evt_skip = await mgr.emit(
        request_id=req_id,
        event="agent_status",
        agent="security",
        status="skipped",
        message="Security Agent skipped for this domain",
    )

    assert evt_skip.status == "skipped"
    assert evt_skip.agent == "security"
    assert "skipped" in evt_skip.message.lower()


@pytest.mark.asyncio
async def test_synthesizer_completion():
    mgr = ExecutionEventManager()
    req_id = "test-synthesizer-06"

    evt = await mgr.emit(
        request_id=req_id,
        event="agent_status",
        agent="synthesizer",
        status="completed",
        duration_ms=310.5,
    )

    assert evt.agent == "synthesizer"
    assert evt.status == "completed"
    assert evt.is_finalization is True
    assert "synthesizer" in FINALIZATION_AGENTS


@pytest.mark.asyncio
async def test_reliability_monitor_rejection():
    mgr = ExecutionEventManager()
    req_id = "test-reliability-reject-07"

    evt = await mgr.emit(
        request_id=req_id,
        event="agent_status",
        agent="reliability_monitor",
        status="failed",
        error="Factual grounding audit rejected output due to unverified claims.",
        duration_ms=180.0,
    )

    assert evt.agent == "reliability_monitor"
    assert evt.status == "failed"
    assert evt.is_finalization is True
    assert "rejected" in evt.error


@pytest.mark.asyncio
async def test_final_answer_available():
    mgr = ExecutionEventManager()
    req_id = "test-final-answer-08"

    evt = await mgr.emit(
        request_id=req_id,
        event="final_answer",
        status="completed",
        final_answer="Comprehensive strategic recommendation.",
    )

    assert evt.event == "final_answer"
    assert evt.status == "completed"
    assert evt.final_answer == "Comprehensive strategic recommendation."

    session = mgr.get_session(req_id)
    assert session.is_terminal is True


def test_unknown_request_id_404():
    """Client requesting events for a nonexistent session receives 404 after wait timeout."""
    # Fast test of non-existent ID
    res = client.get("/api/chat/non-existent-request-id-99999/events")
    assert res.status_code == 404
    assert "not found" in res.json().get("detail", "").lower()

    res_solve = client.get("/api/solve/non-existent-request-id-99999/events")
    assert res_solve.status_code == 404
    assert "not found" in res_solve.json().get("detail", "").lower()


@pytest.mark.asyncio
async def test_client_disconnect_subscriber_cleanup():
    mgr = ExecutionEventManager()
    req_id = "test-disconnect-cleanup-10"

    session = mgr.get_or_create_session(req_id)
    q1 = session.add_subscriber()
    q2 = session.add_subscriber()
    assert len(session.subscribers) == 2

    session.remove_subscriber(q1)
    assert len(session.subscribers) == 1
    assert q2 in session.subscribers


@pytest.mark.asyncio
async def test_no_duplicate_execution_and_replay():
    """Late connecting subscriber gets all past events replayed without triggering re-execution."""
    mgr = ExecutionEventManager()
    req_id = "test-replay-no-dup-11"

    # Emit initial events
    await mgr.emit(req_id, "request_started", selected_agents=["researcher", "synthesizer"])
    await mgr.emit(req_id, "agent_status", agent="researcher", status="running")
    await mgr.emit(req_id, "agent_status", agent="researcher", status="completed", duration_ms=100.0)
    await mgr.emit(req_id, "final_answer", status="completed", final_answer="Done")

    # Connect subscriber AFTER all events have been emitted
    received_events = []
    async for event in mgr.subscribe(req_id, wait_for_init_seconds=0.1):
        received_events.append(event)

    # All 4 events must be replayed exactly once
    assert len(received_events) == 4
    assert received_events[0].event == "request_started"
    assert received_events[1].status == "running"
    assert received_events[2].status == "completed"
    assert received_events[3].event == "final_answer"
    assert received_events[3].final_answer == "Done"
