"""
Comprehensive automated tests for CHAI AI-Generated Intelligent Conversation Titles.
Verifies all 9 requirements:
1. A technical question produces a concise, topic-specific title.
2. A personal decision produces a neutral, descriptive title.
3. A long initial prompt does not become an awkward truncated sentence with trailing ellipses.
4. Existing titles are preserved when continuing conversations (no regeneration on subsequent turns).
5. Titles persist after reopening conversations and repository reload.
6. The chat response and Conversation History display the exact same saved title.
7. LLM failures trigger a readable fallback title without breaking chat.
8. Concurrent requests do not create conflicting titles.
9. Existing memory, conversation history, routing, and chat functionality remain intact.
"""
import uuid
import asyncio
from unittest.mock import patch, AsyncMock
import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.chat.title_service import (
    title_service,
    clean_generated_title,
    generate_fallback_title,
)
from backend.db.repositories import ConversationRepository, MessageRepository
from backend.memory.store import memory_store

client = TestClient(app)


@pytest.fixture(autouse=True)
def mock_chat_and_solve_replies(monkeypatch):
    """Ensure fast, deterministic unit test execution without hitting live LLM services."""
    from backend.chat.service import chat_service
    from backend.api.chat_routes import coordinator
    from backend.core.schemas import FinalResponse

    async def mock_reply(*args, **kwargs):
        return "Deterministic reply for testing.", []

    async def mock_solve(*args, **kwargs):
        return FinalResponse(
            request_id="req-test",
            problem="test problem",
            final_answer="Deterministic multi-agent reasoning reply.",
            final_synthesized_answer="Deterministic multi-agent reasoning reply.",
            request_status="completed",
        )

    monkeypatch.setattr(chat_service, "generate_reply", mock_reply)
    monkeypatch.setattr(coordinator, "process_request", mock_solve)


# =============================================================================
# Unit Tests: Cleaning & Fallback Heuristics
# =============================================================================

def test_clean_generated_title_strips_unwanted_artifacts():
    """Verifies stripping markdown code fences, prefixes, quotes, and trailing ellipses."""
    # Prefix 'Title:' and quotes
    assert clean_generated_title('Title: "FastAPI vs. Django"') == "FastAPI vs. Django"
    assert clean_generated_title('Topic: 24-Hour DSA Marathon...') == "24-Hour DSA Marathon"
    assert clean_generated_title("Subject: AI-Powered Job Search Agent.") == "AI-Powered Job Search Agent"

    # Markdown blocks
    assert clean_generated_title("```markdown\nFixing Python Index Errors\n```") == "Fixing Python Index Errors"

    # Trailing ellipsis
    assert clean_generated_title("College vs. Startup Decision…") == "College vs. Startup Decision"
    assert clean_generated_title("College vs. Startup Decision...") == "College vs. Startup Decision"

    # Enclosing smart quotes
    assert clean_generated_title("“AI Resume Analyzer”") == "AI Resume Analyzer"


def test_generate_fallback_title_never_dangling_ellipses():
    """Verifies heuristic fallback titles are clean and never chopped with ellipses."""
    # Tech comparison
    t1 = generate_fallback_title("I'm confused between FastAPI and Django for my project.")
    assert t1 == "FastAPI vs. Django"

    # Personal decision
    t2 = generate_fallback_title("I'm thinking about dropping out of college to focus on my startup.")
    assert "College" in t2 and "Startup" in t2
    assert not t2.endswith("...") and not t2.endswith("…")

    # Error fixing
    t3 = generate_fallback_title("My Python code keeps giving an index out of range error when parsing lists.")
    assert "Fixing" in t3 or "Index Out Of Range Error" in t3
    assert not t3.endswith("...") and not t3.endswith("…")

    # Long prompt
    long_prompt = (
        "I need comprehensive advice on architecting an event-driven microservices backend "
        "using Kafka, Kubernetes, PostgreSQL, and Redis caching for a high-frequency trading application "
        "handling more than 100,000 transactions per second under peak market load conditions."
    )
    t4 = generate_fallback_title(long_prompt)
    assert not t4.endswith("...")
    assert not t4.endswith("…")
    assert len(t4.split()) <= 8


# =============================================================================
# Requirement 1: Technical question produces concise, topic-specific title
# =============================================================================

@pytest.mark.asyncio
async def test_1_technical_question_produces_topic_specific_title():
    conv_id = f"test-title-tech-{uuid.uuid4().hex[:8]}"
    user_id = f"user-title-tech-{uuid.uuid4().hex[:6]}"

    with patch.object(
        title_service,
        "generate_title",
        new=AsyncMock(return_value="FastAPI vs. Django"),
    ):
        res = client.post(
            "/api/chat",
            json={
                "message": "I'm confused between FastAPI and Django for my new project.",
                "conversation_id": conv_id,
                "user_id": user_id,
            },
        )
        assert res.status_code == 200
        data = res.json()
        assert data["title"] == "FastAPI vs. Django"

        # Verify persisted in database
        convo = await ConversationRepository.get_conversation(user_id=user_id, conversation_id=conv_id)
        assert convo is not None
        assert convo.title == "FastAPI vs. Django"


# =============================================================================
# Requirement 2: Personal decision produces a neutral, descriptive title
# =============================================================================

@pytest.mark.asyncio
async def test_2_personal_decision_produces_neutral_descriptive_title():
    conv_id = f"test-title-pers-{uuid.uuid4().hex[:8]}"
    user_id = f"user-title-pers-{uuid.uuid4().hex[:6]}"

    with patch.object(
        title_service,
        "generate_title",
        new=AsyncMock(return_value="College vs. Startup: Making the Decision"),
    ):
        res = client.post(
            "/api/chat",
            json={
                "message": "I'm thinking of dropping out of college to focus on my startup.",
                "conversation_id": conv_id,
                "user_id": user_id,
            },
        )
        assert res.status_code == 200
        data = res.json()
        assert data["title"] == "College vs. Startup: Making the Decision"
        assert not data["title"].endswith("...")
        assert "dropping out of college any..." not in data["title"]


# =============================================================================
# Requirement 3: Long initial prompt does not become an awkward truncated sentence
# =============================================================================

@pytest.mark.asyncio
async def test_3_long_prompt_no_awkward_truncated_sentence():
    conv_id = f"test-title-long-{uuid.uuid4().hex[:8]}"
    user_id = f"user-title-long-{uuid.uuid4().hex[:6]}"

    long_msg = (
        "I'm studying for my DSA exam, but I have only 24 hours left and I need to cover "
        "dynamic programming, graph algorithms, binary search trees, and heap data structures "
        "before tomorrow morning."
    )

    with patch.object(
        title_service,
        "generate_title",
        new=AsyncMock(return_value="24-Hour DSA Marathon"),
    ):
        res = client.post(
            "/api/chat",
            json={
                "message": long_msg,
                "conversation_id": conv_id,
                "user_id": user_id,
            },
        )
        assert res.status_code == 200
        data = res.json()
        assert data["title"] == "24-Hour DSA Marathon"
        assert not data["title"].endswith("...")
        assert not data["title"].endswith("…")


# =============================================================================
# Requirement 4: Existing titles are preserved when continuing conversations
# =============================================================================

@pytest.mark.asyncio
async def test_4_existing_titles_preserved_when_continuing():
    conv_id = f"test-title-preserve-{uuid.uuid4().hex[:8]}"
    user_id = f"user-title-preserve-{uuid.uuid4().hex[:6]}"

    # Turn 1
    with patch.object(
        title_service,
        "generate_title",
        new=AsyncMock(return_value="AI-Powered Job Search Agent"),
    ) as mock_gen:
        res1 = client.post(
            "/api/chat",
            json={
                "message": "I want to build an AI agent that searches for jobs and analyzes resumes.",
                "conversation_id": conv_id,
                "user_id": user_id,
            },
        )
        assert res1.status_code == 200
        assert res1.json()["title"] == "AI-Powered Job Search Agent"
        assert mock_gen.call_count == 1

    # Turn 2: Follow-up message in same conversation
    with patch.object(
        title_service,
        "generate_title",
        new=AsyncMock(return_value="Should Not Be Called"),
    ) as mock_gen_turn2:
        res2 = client.post(
            "/api/chat",
            json={
                "message": "Can we use LangGraph and Playwright for the scraper component?",
                "conversation_id": conv_id,
                "user_id": user_id,
            },
        )
        assert res2.status_code == 200
        # Title MUST be preserved from Turn 1
        assert res2.json()["title"] == "AI-Powered Job Search Agent"
        # Title generator should NOT be invoked again
        assert mock_gen_turn2.call_count == 0

    # Verify database still has original title
    convo = await ConversationRepository.get_conversation(user_id=user_id, conversation_id=conv_id)
    assert convo.title == "AI-Powered Job Search Agent"


# =============================================================================
# Requirement 5: Titles persist after reopening conversations and backend restart
# =============================================================================

@pytest.mark.asyncio
async def test_5_titles_persist_after_reopening_and_db_reload():
    conv_id = f"test-title-persist-{uuid.uuid4().hex[:8]}"
    user_id = f"user-title-persist-{uuid.uuid4().hex[:6]}"

    with patch.object(
        title_service,
        "generate_title",
        new=AsyncMock(return_value="Fixing Python Index Errors"),
    ):
        res = client.post(
            "/api/chat",
            json={
                "message": "My Python code keeps giving an index out of range error.",
                "conversation_id": conv_id,
                "user_id": user_id,
            },
        )
        assert res.status_code == 200

    # Simulate fresh fetch (reopening conversation)
    detail_res = client.get(
        f"/api/history/{conv_id}",
        headers={"X-User-ID": user_id},
    )
    assert detail_res.status_code == 200
    assert detail_res.json()["title"] == "Fixing Python Index Errors"

    # Simulate fresh repo query
    direct_convo = await ConversationRepository.get_conversation_with_messages(
        user_id=user_id,
        conversation_id=conv_id,
    )
    assert direct_convo["title"] == "Fixing Python Index Errors"


# =============================================================================
# Requirement 6: Chat response and Conversation History display the same saved title
# =============================================================================

@pytest.mark.asyncio
async def test_6_response_and_history_display_same_saved_title():
    conv_id = f"test-title-match-{uuid.uuid4().hex[:8]}"
    user_id = f"user-title-match-{uuid.uuid4().hex[:6]}"

    with patch.object(
        title_service,
        "generate_title",
        new=AsyncMock(return_value="Distributed Caching with Redis"),
    ):
        chat_res = client.post(
            "/api/chat",
            json={
                "message": "How do I configure distributed Redis caching across three data centers?",
                "conversation_id": conv_id,
                "user_id": user_id,
            },
        )
        assert chat_res.status_code == 200
        returned_title = chat_res.json()["title"]
        assert returned_title == "Distributed Caching with Redis"

    # Check /api/history list
    hist_list_res = client.get(
        "/api/history",
        headers={"X-User-ID": user_id},
    )
    assert hist_list_res.status_code == 200
    hist_items = hist_list_res.json()
    convo_item = next((c for c in hist_items if c["id"] == conv_id), None)
    assert convo_item is not None
    assert convo_item["title"] == returned_title

    # Check /api/history/{id} detail
    hist_detail_res = client.get(
        f"/api/history/{conv_id}",
        headers={"X-User-ID": user_id},
    )
    assert hist_detail_res.status_code == 200
    assert hist_detail_res.json()["title"] == returned_title


# =============================================================================
# Requirement 7: LLM failure triggers readable fallback without breaking chat
# =============================================================================

@pytest.mark.asyncio
async def test_7_llm_failure_triggers_readable_fallback():
    conv_id = f"test-title-fail-{uuid.uuid4().hex[:8]}"
    user_id = f"user-title-fail-{uuid.uuid4().hex[:6]}"

    # Simulate LLM exception/timeout during title generation
    with patch(
        "backend.shared.llm_client.llm_client.generate_content",
        new=AsyncMock(side_effect=asyncio.TimeoutError("LLM call timed out")),
    ):
        res = client.post(
            "/api/chat",
            json={
                "message": "I'm confused between FastAPI and Django for my project.",
                "conversation_id": conv_id,
                "user_id": user_id,
            },
        )
        # Main chat MUST NOT fail
        assert res.status_code == 200
        data = res.json()
        assert data["conversation_id"] == conv_id
        # Fallback title should be generated cleanly
        assert data["title"] == "FastAPI vs. Django"
        assert not data["title"].endswith("...")


# =============================================================================
# Requirement 8: Concurrent requests do not create conflicting titles
# =============================================================================

@pytest.mark.asyncio
async def test_8_concurrent_requests_distinct_titles():
    conv_id_1 = f"test-title-conc-1-{uuid.uuid4().hex[:8]}"
    conv_id_2 = f"test-title-conc-2-{uuid.uuid4().hex[:8]}"
    user_id = f"user-title-conc-{uuid.uuid4().hex[:6]}"

    async def run_chat(conv_id: str, prompt: str, mock_title: str):
        with patch.object(
            title_service,
            "generate_title",
            new=AsyncMock(return_value=mock_title),
        ):
            return client.post(
                "/api/chat",
                json={
                    "message": prompt,
                    "conversation_id": conv_id,
                    "user_id": user_id,
                },
            )

    loop = asyncio.get_event_loop()
    r1, r2 = await asyncio.gather(
        loop.run_in_executor(None, lambda: client.post(
            "/api/chat",
            json={
                "message": "FastAPI vs Django comparison",
                "conversation_id": conv_id_1,
                "user_id": user_id,
            },
        )),
        loop.run_in_executor(None, lambda: client.post(
            "/api/chat",
            json={
                "message": "Fixing Python Index Errors in loops",
                "conversation_id": conv_id_2,
                "user_id": user_id,
            },
        )),
    )

    assert r1.status_code == 200
    assert r2.status_code == 200
    d1 = r1.json()
    d2 = r2.json()

    assert d1["conversation_id"] == conv_id_1
    assert d2["conversation_id"] == conv_id_2
    assert d1["title"] != d2["title"]
    assert not d1["title"].endswith("...")
    assert not d2["title"].endswith("...")


# =============================================================================
# Requirement 9: Existing memory, routing, and chat remain intact
# =============================================================================

@pytest.mark.asyncio
async def test_9_existing_memory_and_routing_intact():
    conv_id = f"test-title-memory-{uuid.uuid4().hex[:8]}"
    user_id = f"user-title-memory-{uuid.uuid4().hex[:6]}"

    res = client.post(
        "/api/chat",
        json={
            "message": "My name is Samantha and I am the lead architect at Stripe.",
            "conversation_id": conv_id,
            "user_id": user_id,
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert "Samantha" in data["title"] or "Stripe" in data["title"] or "Lead Architect" in data["title"]

    # Verify short-term conversation messages stored with correct metadata
    messages = await MessageRepository.get_conversation_messages(
        conversation_id=conv_id,
        user_id=user_id,
    )
    assert len(messages) >= 2
    user_msg = next((m for m in messages if m.role == "user"), None)
    asst_msg = next((m for m in messages if m.role == "assistant"), None)
    assert user_msg is not None
    assert asst_msg is not None
    assert asst_msg.extra_data.get("resolved_domain") is not None
