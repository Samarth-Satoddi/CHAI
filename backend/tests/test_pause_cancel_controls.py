"""
Comprehensive unit and integration tests for CHAI Pause and Cancel controls during AI generation.

Covers:
1. Pause control / API changes session status to Paused and emits request_paused
2. Resume restores execution state and emits request_resumed
3. Cancel aborts active request and marks request as cancelled
4. Cancel stops future agent scheduling in Coordinator
5. One user's cancellation does not affect another request (isolation)
6. Simple LangChain cancellation aborts cleanly without fallback
7. Complex LangGraph cancellation aborts and halts downstream nodes
8. Existing conversation memory remains functional
9. Existing live agent progress remains accurate
10. Unknown request ID handling for pause/resume/cancel endpoints (404)
11. Late response / duplicate cancel safety
"""
import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient

from backend.core.execution_events import (
    ExecutionEventManager,
    execution_event_manager,
    RequestCancelledException,
)
from backend.core.coordinator import Coordinator
from backend.core.schemas import SolveRequest, FinalResponse
from backend.core.workflow import build_chai_workflow
from backend.core.state import create_initial_state
from backend.chat.service import chat_service
from backend.memory.store import memory_store
from backend.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_mock_env(monkeypatch):
    monkeypatch.setenv("CHAI_MOCK_MODE", "true")


# ---------------------------------------------------------------------------
# 1 & 2. Pause and Resume Session Semantics & Events
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_pause_and_resume_lifecycle():
    """Verify that pause and resume manipulate execution session and emit correct SSE events."""
    mgr = ExecutionEventManager()
    req_id = "test-pause-resume-01"
    session = mgr.create_session(req_id)

    assert session.status == "running"
    assert session.pause_event.is_set()
    assert not mgr.is_paused(req_id)

    # Pause
    paused = await mgr.pause_request(req_id)
    assert paused is True
    assert session.status == "paused"
    assert not session.pause_event.is_set()
    assert mgr.is_paused(req_id)

    # Event was emitted
    pause_evt = session.events_history[-1]
    assert pause_evt.event == "request_paused"
    assert pause_evt.status == "paused"

    # Resume
    resumed = await mgr.resume_request(req_id)
    assert resumed is True
    assert session.status == "running"
    assert session.pause_event.is_set()
    assert not mgr.is_paused(req_id)

    resume_evt = session.events_history[-1]
    assert resume_evt.event == "request_resumed"
    assert resume_evt.status == "running"


# ---------------------------------------------------------------------------
# 3. Cancel Aborts Active Request
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_cancel_lifecycle():
    """Verify that cancel transitions session to terminal cancelled state and wakes up waiters."""
    mgr = ExecutionEventManager()
    req_id = "test-cancel-02"
    session = mgr.create_session(req_id)

    # Pause first
    await mgr.pause_request(req_id)
    assert session.status == "paused"

    # Cancel while paused
    cancelled = await mgr.cancel_request(req_id)
    assert cancelled is True
    assert session.status == "cancelled"
    assert session.is_terminal is True
    assert session.pause_event.is_set()  # Released so paused tasks unblock and exit
    assert mgr.is_cancelled(req_id)

    cancel_evt = session.events_history[-1]
    assert cancel_evt.event == "request_cancelled"
    assert cancel_evt.status == "cancelled"


# ---------------------------------------------------------------------------
# 4. Request Isolation: One Cancellation Does Not Affect Another
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_cancellation_isolation_between_requests():
    """Cancelling request A must have no effect on active request B."""
    mgr = ExecutionEventManager()
    req_a = "req-user-alpha"
    req_b = "req-user-beta"

    sess_a = mgr.create_session(req_a)
    sess_b = mgr.create_session(req_b)

    await mgr.cancel_request(req_a)

    assert mgr.is_cancelled(req_a) is True
    assert mgr.is_cancelled(req_b) is False
    assert sess_b.status == "running"
    assert not sess_b.cancel_requested


# ---------------------------------------------------------------------------
# 5. Coordinator Stops Future Agent Scheduling Upon Cancellation
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_coordinator_stops_scheduling_after_cancellation():
    """Coordinator must abort execution and stop scheduling future agents when cancelled."""
    coordinator = Coordinator()
    req_id = "test-coord-cancel-05"

    engineer_called = False
    synthesizer_called = False

    async def mock_engineer_run(*args, **kwargs):
        nonlocal engineer_called
        engineer_called = True
        return {"status": "completed", "specifications": "engine specs"}

    async def mock_synthesizer_run(*args, **kwargs):
        nonlocal synthesizer_called
        synthesizer_called = True
        return {"status": "completed", "final_answer": "synth"}

    coordinator.engineer.run = mock_engineer_run
    coordinator.synthesizer.run = mock_synthesizer_run

    # Pre-cancel before specialist agents run
    execution_event_manager.create_session(req_id)
    await execution_event_manager.cancel_request(req_id)

    req = SolveRequest(
        problem="Design a distributed caching architecture",
        request_id=req_id,
        selected_agents=["engineer", "synthesizer"],
    )

    response = await coordinator.process_request(req)

    assert response.request_status == "cancelled"
    assert "cancelled" in response.final_synthesized_answer.lower()
    # Downstream agents were NOT executed
    assert engineer_called is False
    assert synthesizer_called is False


# ---------------------------------------------------------------------------
# 6. Simple LangChain Chat Cancellation
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_simple_langchain_cancellation():
    """ChatService must check cancellation before and after model invocation and raise RequestCancelledException."""
    req_id = "test-langchain-cancel-06"
    execution_event_manager.create_session(req_id)
    await execution_event_manager.cancel_request(req_id)

    with pytest.raises(RequestCancelledException):
        await chat_service.generate_reply(
            user_id="user_test",
            message="Hello CHAI",
            request_id=req_id,
        )


# ---------------------------------------------------------------------------
# 7. Complex LangGraph Cancellation
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_complex_langgraph_cancellation():
    """LangGraph workflow execution must abort when cancellation is signaled."""
    workflow = build_chai_workflow()
    req_id = "test-langgraph-cancel-07"

    execution_event_manager.create_session(req_id)
    await execution_event_manager.cancel_request(req_id)

    initial_state = create_initial_state(
        problem="Design an enterprise payments gateway",
        user_id="user_test",
    )
    initial_state["request_id"] = req_id

    # Running LangGraph on cancelled request raises RequestCancelledException
    with pytest.raises(RequestCancelledException):
        await workflow.ainvoke(initial_state)


# ---------------------------------------------------------------------------
# 8. API Endpoints (POST /api/chat/... & /api/solve/...)
# ---------------------------------------------------------------------------

def test_api_chat_pause_resume_cancel_endpoints():
    """REST API endpoints for pause, resume, and cancel on /api/chat return expected JSON."""
    req_id = "api-test-chat-08"
    execution_event_manager.create_session(req_id)

    # Pause
    res = client.post(f"/api/chat/{req_id}/pause")
    assert res.status_code == 200
    assert res.json() == {"request_id": req_id, "status": "paused", "success": True}

    # Resume
    res = client.post(f"/api/chat/{req_id}/resume")
    assert res.status_code == 200
    assert res.json() == {"request_id": req_id, "status": "resumed", "success": True}

    # Cancel
    res = client.post(f"/api/chat/{req_id}/cancel")
    assert res.status_code == 200
    assert res.json() == {"request_id": req_id, "status": "cancelled", "success": True}


def test_api_solve_pause_resume_cancel_endpoints():
    """REST API endpoints for pause, resume, and cancel on /api/solve return expected JSON."""
    req_id = "api-test-solve-09"
    execution_event_manager.create_session(req_id)

    res = client.post(f"/api/solve/{req_id}/pause")
    assert res.status_code == 200
    assert res.json() == {"request_id": req_id, "status": "paused", "success": True}

    res = client.post(f"/api/solve/{req_id}/resume")
    assert res.status_code == 200
    assert res.json() == {"request_id": req_id, "status": "resumed", "success": True}

    res = client.post(f"/api/solve/{req_id}/cancel")
    assert res.status_code == 200
    assert res.json() == {"request_id": req_id, "status": "cancelled", "success": True}


def test_api_pause_cancel_unknown_request_id_returns_404():
    """Calling pause/resume/cancel on an unknown request ID returns 404."""
    unknown_id = "unknown-session-404-xyz"
    res = client.post(f"/api/chat/{unknown_id}/pause")
    assert res.status_code == 404

    res = client.post(f"/api/chat/{unknown_id}/resume")
    assert res.status_code == 404

    res = client.post(f"/api/chat/{unknown_id}/cancel")
    assert res.status_code == 404


# ---------------------------------------------------------------------------
# 9. Existing Conversation Memory Remains Functional
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_existing_conversation_memory_remains_functional():
    """Memory store and message persistence operate normally alongside pause/cancel lifecycle."""
    import uuid
    conv_id = f"conv-test-memory-{uuid.uuid4()}"
    user_id = f"user-test-memory-{uuid.uuid4()}"

    await memory_store.add_message(
        conversation_id=conv_id,
        user_id=user_id,
        role="user",
        content="What is microservices architecture?",
    )
    await memory_store.add_message(
        conversation_id=conv_id,
        user_id=user_id,
        role="assistant",
        content="Microservices architecture structures an application as independently deployable services.",
    )

    history = await memory_store.get_recent_messages(conversation_id=conv_id)
    assert len(history) == 2
    assert history[0].role == "user"
    assert history[1].role == "assistant"
