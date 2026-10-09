"""
Deterministic Regression Test Suite for CHAI Conversation Memory and Domain Consistency.
Tests A through J validating:
- Test A: Immediate conversation memory
- Test B: Name resolution from conversation context
- Test C: Multiple follow-ups referencing "it"
- Test D: Message persistence across HTTP requests
- Test E: History persistence surviving memory store recreation
- Test F: Relevance-based memory filtering
- Test G: User and guest session isolation
- Test H: Domain continuity on explicit BUSINESS selection
- Test I: Category switching from BUSINESS to SOFTWARE
- Test J: Deterministic separation of CHAT and SOLVE modes
"""
import uuid
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

from backend.main import app
from backend.memory.store import MemoryStore, memory_store
from backend.memory.retrieval import memory_retriever
from backend.memory.models import MemoryItem, MemoryCategory
from backend.core.router import route_request, ROUTE_SIMPLE, ROUTE_COMPLEX
from backend.core.domain_lenses import canonicalize_domain, CANONICAL_DOMAINS


client = TestClient(app)


# =============================================================================
# TEST A: Immediate conversation memory
# =============================================================================
@pytest.mark.asyncio
async def test_a_immediate_conversation_memory():
    """
    1. User: "I'm Samarth and I'm building an AI startup."
    2. Assistant returns a response.
    3. User: "What am I building?"
    4. Assert the LangChain prompt receives the previous turn and the response identifies an AI startup.
    """
    conv_id = f"test-conv-mem-a-{uuid.uuid4().hex[:8]}"
    user_id = "test-user-a"

    # Turn 1
    r1 = client.post(
        "/api/chat",
        json={
            "message": "I'm Samarth and I'm building an AI startup.",
            "conversation_id": conv_id,
            "user_id": user_id,
            "category": "BUSINESS",
        },
    )
    assert r1.status_code == 200
    d1 = r1.json()
    assert d1["mode"] == "chat"
    assert d1["conversation_id"] == conv_id

    # Verify messages are in store
    history = await memory_store.get_recent_messages(conv_id, user_id=user_id)
    assert len(history) >= 2
    assert history[0].role == "user"
    assert "building an AI startup" in history[0].content
    assert history[1].role == "assistant"

    # Turn 2: Follow-up question
    r2 = client.post(
        "/api/chat",
        json={
            "message": "What am I building?",
            "conversation_id": conv_id,
            "user_id": user_id,
            "category": "BUSINESS",
        },
    )
    assert r2.status_code == 200
    d2 = r2.json()
    assert d2["mode"] == "chat"
    assert d2["conversation_id"] == conv_id
    assert "startup" in d2["message"].lower() or "ai" in d2["message"].lower()


# =============================================================================
# TEST B: Name resolution from conversation context
# =============================================================================
def test_b_name_resolution_from_conversation_context():
    """
    1. User establishes that Samarth is building an AI startup.
    2. User asks "Who is Samarth?"
    3. Assert the answer uses conversation context and does not invent unrelated public identities.
    """
    conv_id = f"test-conv-name-b-{uuid.uuid4().hex[:8]}"

    # Turn 1
    r1 = client.post(
        "/api/chat",
        json={
            "message": "hi iam samarth iam building the ai startup",
            "conversation_id": conv_id,
            "category": "BUSINESS",
        },
    )
    assert r1.status_code == 200

    # Turn 2
    r2 = client.post(
        "/api/chat",
        json={
            "message": "who is samarth",
            "conversation_id": conv_id,
            "category": "BUSINESS",
        },
    )
    assert r2.status_code == 200
    d2 = r2.json()
    assert d2["mode"] == "chat"
    ans = d2["message"].lower()
    # Must identify Samarth as the user / founder building the startup, not external Indian schemes
    assert any(w in ans for w in ("you", "founder", "building", "startup", "user"))
    assert "ministry" not in ans
    assert "textiles" not in ans
    assert "yojana" not in ans


# =============================================================================
# TEST C: Multiple follow-ups referencing pronouns ("it")
# =============================================================================
def test_c_multiple_follow_ups_with_pronouns():
    """
    1. User establishes a project and its purpose.
    2. User asks a follow-up referring to "it".
    3. Assert the earlier context is used and request remains in CHAT mode.
    """
    conv_id = f"test-conv-followup-c-{uuid.uuid4().hex[:8]}"

    r1 = client.post(
        "/api/chat",
        json={
            "message": "Our project is called CHAI, an agentic intelligence platform.",
            "conversation_id": conv_id,
            "category": "SOFTWARE",
        },
    )
    assert r1.status_code == 200

    r2 = client.post(
        "/api/chat",
        json={
            "message": "How does it coordinate different agents?",
            "conversation_id": conv_id,
            "category": "SOFTWARE",
        },
    )
    assert r2.status_code == 200
    d2 = r2.json()
    assert d2["mode"] == "chat"
    assert len(d2["message"]) > 20


# =============================================================================
# TEST D: Persistence across requests using same conversation ID
# =============================================================================
@pytest.mark.asyncio
async def test_d_persistence_across_separate_http_requests():
    """
    Send separate HTTP requests using the same conversation ID.
    Verify that subsequent invocations receive all earlier messages.
    """
    conv_id = f"test-conv-persist-d-{uuid.uuid4().hex[:8]}"
    user_id = "test-user-d"

    client.post(
        "/api/chat",
        json={"message": "First message: I like Python.", "conversation_id": conv_id, "user_id": user_id},
    )
    client.post(
        "/api/chat",
        json={"message": "Second message: I work on backend.", "conversation_id": conv_id, "user_id": user_id},
    )

    history = await memory_store.get_recent_messages(conv_id, user_id=user_id, limit=10)
    assert len(history) == 4
    assert history[0].content == "First message: I like Python."
    assert history[2].content == "Second message: I work on backend."


# =============================================================================
# TEST E: Persistence across restart / store recreation
# =============================================================================
@pytest.mark.asyncio
async def test_e_persistence_across_store_recreation():
    """
    Persist conversation messages, recreate the MemoryStore instance,
    and verify the conversation history can still be retrieved from durable database storage.
    """
    conv_id = f"test-conv-restart-e-{uuid.uuid4().hex[:8]}"
    user_id = "test-user-e"

    await memory_store.add_message(conv_id, user_id, "user", "Durable message 1")
    await memory_store.add_message(conv_id, user_id, "assistant", "Durable reply 1")

    # Recreate a fresh MemoryStore instance (simulating application restart)
    new_store = MemoryStore()
    reloaded_messages = await new_store.get_recent_messages(conv_id, user_id=user_id, limit=10)

    assert len(reloaded_messages) == 2
    assert reloaded_messages[0].content == "Durable message 1"
    assert reloaded_messages[1].content == "Durable reply 1"


# =============================================================================
# TEST F: Memory relevance filtering
# =============================================================================
def test_f_memory_relevance_filtering():
    """
    Verify relevant user memories are retrieved and irrelevant memories are excluded.
    """
    mem_ai = MemoryItem(
        user_id="user_f",
        memory="User is building an AI startup.",
        category=MemoryCategory.PROJECT,
    )
    mem_cooking = MemoryItem(
        user_id="user_f",
        memory="User enjoys baking sourdough bread on weekends.",
        category=MemoryCategory.PREFERENCE,
    )
    mem_violin = MemoryItem(
        user_id="user_f",
        memory="User has played violin for 10 years.",
        category=MemoryCategory.EXPERTISE,
    )

    all_memories = [mem_ai, mem_cooking, mem_violin]

    results = memory_retriever.retrieve(
        query="What is my AI startup progress?",
        memories=all_memories,
        limit=2,
    )

    assert len(results) >= 1
    retrieved_texts = [m.memory for m in results]
    assert "User is building an AI startup." in retrieved_texts
    assert "User enjoys baking sourdough bread on weekends." not in retrieved_texts


# =============================================================================
# TEST G: Authenticated-user and guest-session isolation
# =============================================================================
@pytest.mark.asyncio
async def test_g_user_and_session_isolation():
    """
    Verify that User A or Guest A cannot access User B or Guest B's conversations or memories.
    """
    conv_a = f"conv-user-a-{uuid.uuid4().hex[:8]}"
    conv_b = f"conv-user-b-{uuid.uuid4().hex[:8]}"

    await memory_store.add_message(conv_a, "user_alice", "user", "Secret from Alice")
    await memory_store.add_message(conv_b, "user_bob", "user", "Secret from Bob")

    # Bob attempts to read Alice's conversation
    bob_attempt = await memory_store.get_recent_messages(conv_a, user_id="user_bob")
    assert len(bob_attempt) == 0, "Bob must not be able to read Alice's conversation"

    # Alice reads her own conversation
    alice_read = await memory_store.get_recent_messages(conv_a, user_id="user_alice")
    assert len(alice_read) == 1
    assert alice_read[0].content == "Secret from Alice"

    # Guest session isolation
    guest_mem_1 = await memory_store.add_memory("guest_1", "Guest 1 secret", session_id="sess_1")
    guest_mem_2 = await memory_store.add_memory("guest_2", "Guest 2 secret", session_id="sess_2")

    guest_1_mems = await memory_store.get_user_memories("guest_1", session_id="sess_1")
    guest_2_mems = await memory_store.get_user_memories("guest_2", session_id="sess_2")

    assert any(m.memory == "Guest 1 secret" for m in guest_1_mems)
    assert not any(m.memory == "Guest 2 secret" for m in guest_1_mems)
    assert any(m.memory == "Guest 2 secret" for m in guest_2_mems)
    assert not any(m.memory == "Guest 1 secret" for m in guest_2_mems)


# =============================================================================
# TEST H: Domain continuity on explicit BUSINESS selection
# =============================================================================
def test_h_domain_continuity_explicit_business():
    """
    Select BUSINESS and send a greeting followed by 'Who is Samarth?'.
    Verify BUSINESS remains the resolved domain and never returns 'general'.
    """
    conv_id = f"test-conv-domain-h-{uuid.uuid4().hex[:8]}"

    r1 = client.post(
        "/api/chat",
        json={
            "message": "Hello!",
            "conversation_id": conv_id,
            "category": "BUSINESS",
        },
    )
    assert r1.status_code == 200
    d1 = r1.json()
    assert d1["resolved_domain"] == "business"

    r2 = client.post(
        "/api/chat",
        json={
            "message": "Who is Samarth?",
            "conversation_id": conv_id,
            "category": "BUSINESS",
        },
    )
    assert r2.status_code == 200
    d2 = r2.json()
    assert d2["resolved_domain"] == "business"
    assert d2["resolved_domain"] in CANONICAL_DOMAINS
    assert d2["resolved_domain"] != "general"


# =============================================================================
# TEST I: Category switching from BUSINESS to SOFTWARE
# =============================================================================
def test_i_category_switching():
    """
    Change explicit category from BUSINESS to SOFTWARE and verify the next request uses SOFTWARE.
    """
    conv_id = f"test-conv-cat-switch-i-{uuid.uuid4().hex[:8]}"

    r1 = client.post(
        "/api/chat",
        json={
            "message": "What is unit economics?",
            "conversation_id": conv_id,
            "category": "BUSINESS",
        },
    )
    assert r1.status_code == 200
    d1 = r1.json()
    assert d1["resolved_domain"] == "business"

    # User explicitly changes category to SOFTWARE
    r2 = client.post(
        "/api/chat",
        json={
            "message": "How do I implement connection pooling in SQLAlchemy?",
            "conversation_id": conv_id,
            "category": "SOFTWARE",
        },
    )
    assert r2.status_code == 200
    d2 = r2.json()
    assert d2["resolved_domain"] == "software"


# =============================================================================
# TEST J: CHAT vs SOLVE routing separation
# =============================================================================
def test_j_chat_vs_solve_routing_separation():
    """
    A greeting and contextual follow-up use LangChain CHAT.
    A complex reasoning request uses the existing LangGraph SOLVE pipeline.
    """
    conv_id = f"test-conv-sep-j-{uuid.uuid4().hex[:8]}"

    # Turn 1: Conversational greeting -> CHAT
    r1 = client.post(
        "/api/chat",
        json={"message": "Good morning CHAI!", "conversation_id": conv_id},
    )
    assert r1.status_code == 200
    d1 = r1.json()
    assert d1["mode"] == "chat"

    # Turn 2: Follow-up question -> CHAT
    r2 = client.post(
        "/api/chat",
        json={"message": "What can you help me with today?", "conversation_id": conv_id},
    )
    assert r2.status_code == 200
    d2 = r2.json()
    assert d2["mode"] == "chat"

    # Turn 3: Complex multi-criteria architectural trade-off -> SOLVE
    complex_query = (
        "Design a high-throughput, multi-tenant distributed microservices architecture "
        "supporting 50,000 concurrent students with Redis caching, PostgreSQL partitioning, "
        "and evaluate security and latency trade-offs."
    )
    r3 = client.post(
        "/api/chat",
        json={"message": complex_query, "conversation_id": conv_id},
    )
    assert r3.status_code == 200
    d3 = r3.json()
    assert d3["mode"] == "solve"
    assert d3["resolved_domain"] == "software"
    assert len(d3.get("selected_agents", [])) > 0
