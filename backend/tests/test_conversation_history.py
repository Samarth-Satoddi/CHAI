"""
Comprehensive automated test suite for CHAI Persistent Conversation History and Recent Chats.
Validates requirements 1 through 13:
1. New conversation is saved correctly.
2. User and assistant messages are persisted in order.
3. Conversations survive backend restart / store re-instantiation.
4. Conversation titles are generated correctly from user prompts.
5. History listing is ordered by recent activity.
6. Search returns matching conversations (title and message content).
7. Opening an old conversation restores all saved messages.
8. Continuing an old conversation appends messages to the correct conversation.
9. Starting a new conversation does not overwrite an old one.
10. Two different guest identities cannot access each other's conversations (isolation).
11. Missing or unauthorized conversation IDs return 404 Not Found.
12. Existing long-term memory functionality continues to work.
13. Existing routing, execution controls, and chat workflows are not regressed.
"""
import uuid
import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.memory.store import MemoryStore, memory_store
from backend.db.repositories import ConversationRepository, MessageRepository, generate_conversation_title
from backend.memory.models import MemoryCategory

client = TestClient(app)


# =============================================================================
# 1. New conversation is saved correctly
# =============================================================================
def test_1_new_conversation_saved_correctly():
    conv_id = f"test-hist-1-{uuid.uuid4().hex[:8]}"
    user_id = f"user-hist-1-{uuid.uuid4().hex[:6]}"

    res = client.post(
        "/api/chat",
        json={
            "message": "Hello CHAI, can you give me three growth strategies for B2B SaaS?",
            "conversation_id": conv_id,
            "user_id": user_id,
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["conversation_id"] == conv_id

    # Check history endpoint
    h_res = client.get(
        "/api/history",
        headers={"X-User-ID": user_id},
    )
    assert h_res.status_code == 200
    items = h_res.json()
    assert len(items) >= 1
    found = next((c for c in items if c["id"] == conv_id), None)
    assert found is not None
    assert found["title"] != "New Conversation"
    assert "SaaS" in found["title"] or "growth" in found["title"].lower() or "strategies" in found["title"].lower()


# =============================================================================
# 2. User and assistant messages are persisted in order
# =============================================================================
def test_2_user_and_assistant_messages_persisted_in_order():
    conv_id = f"test-hist-2-{uuid.uuid4().hex[:8]}"
    user_id = f"user-hist-2-{uuid.uuid4().hex[:6]}"
    prompt = "What is the capital of France?"

    res = client.post(
        "/api/chat",
        json={
            "message": prompt,
            "conversation_id": conv_id,
            "user_id": user_id,
        },
    )
    assert res.status_code == 200
    reply = res.json()["message"]

    # Retrieve full conversation
    detail_res = client.get(
        f"/api/history/{conv_id}",
        headers={"X-User-ID": user_id},
    )
    assert detail_res.status_code == 200
    detail = detail_res.json()
    assert detail["id"] == conv_id
    msgs = detail["messages"]
    assert len(msgs) == 2
    assert msgs[0]["role"] == "user"
    assert msgs[0]["content"] == prompt
    assert msgs[1]["role"] == "assistant"
    assert msgs[1]["content"] == reply


# =============================================================================
# 3. Conversations survive backend restart / store recreation
# =============================================================================
@pytest.mark.asyncio
async def test_3_conversations_survive_backend_restart():
    conv_id = f"test-hist-3-{uuid.uuid4().hex[:8]}"
    user_id = f"user-hist-3-{uuid.uuid4().hex[:6]}"

    # Save via active store
    await memory_store.add_message(conv_id, user_id, "user", "Message before restart")
    await memory_store.add_message(conv_id, user_id, "assistant", "Reply before restart")

    # Simulate backend restart with a brand new MemoryStore instance
    fresh_store = MemoryStore()
    conv_data = await fresh_store.get_conversation(user_id=user_id, conversation_id=conv_id)
    assert conv_data is not None
    assert conv_data["id"] == conv_id
    assert len(conv_data["messages"]) == 2
    assert conv_data["messages"][0].content == "Message before restart"
    assert conv_data["messages"][1].content == "Reply before restart"


# =============================================================================
# 4. Conversation titles are generated correctly
# =============================================================================
def test_4_conversation_titles_generated_correctly():
    t1 = generate_conversation_title("Hi CHAI, tell me about microservices architecture")
    assert t1.startswith("Tell me about microservices") or "Microservices" in t1
    assert not t1.lower().startswith("hi chai")

    t2 = generate_conversation_title("hey, how do I configure PostgreSQL connection pooling in FastAPI?")
    assert "PostgreSQL" in t2 or "connection pooling" in t2.lower()

    t3 = generate_conversation_title("A" * 80)
    assert len(t3) <= 50
    assert t3.endswith("...")


# =============================================================================
# 5. History listing is ordered by recent activity
# =============================================================================
def test_5_history_listing_ordered_by_recent_activity():
    user_id = f"user-hist-5-{uuid.uuid4().hex[:6]}"
    c1 = f"c1-{uuid.uuid4().hex[:6]}"
    c2 = f"c2-{uuid.uuid4().hex[:6]}"

    # Create c1
    client.post("/api/chat", json={"message": "First conversation prompt", "conversation_id": c1, "user_id": user_id})
    # Create c2
    client.post("/api/chat", json={"message": "Second conversation prompt", "conversation_id": c2, "user_id": user_id})

    # c2 was created last, should be first
    h1 = client.get("/api/history", headers={"X-User-ID": user_id}).json()
    assert h1[0]["id"] == c2

    # Now update c1 with a new message
    client.post("/api/chat", json={"message": "Follow up in first conversation", "conversation_id": c1, "user_id": user_id})

    # c1 is now the most recently updated
    h2 = client.get("/api/history", headers={"X-User-ID": user_id}).json()
    assert h2[0]["id"] == c1


# =============================================================================
# 6. Search returns matching conversations (title and content)
# =============================================================================
def test_6_search_returns_matching_conversations():
    user_id = f"user-hist-6-{uuid.uuid4().hex[:6]}"
    c_astro = f"astro-{uuid.uuid4().hex[:6]}"
    c_bake = f"bake-{uuid.uuid4().hex[:6]}"

    client.post(
        "/api/chat",
        json={"message": "Explain gravitational waves and astrophysics", "conversation_id": c_astro, "user_id": user_id},
    )
    client.post(
        "/api/chat",
        json={"message": "What is the secret to sourdough bread fermentation?", "conversation_id": c_bake, "user_id": user_id},
    )

    # Search for astrophysics
    res_astro = client.get("/api/history?search=astrophysics", headers={"X-User-ID": user_id}).json()
    assert any(c["id"] == c_astro for c in res_astro)
    assert not any(c["id"] == c_bake for c in res_astro)

    # Search for sourdough
    res_bake = client.get("/api/history?search=sourdough", headers={"X-User-ID": user_id}).json()
    assert any(c["id"] == c_bake for c in res_bake)
    assert not any(c["id"] == c_astro for c in res_bake)


# =============================================================================
# 7. Opening an old conversation restores all saved messages
# =============================================================================
def test_7_opening_old_conversation_restores_all_saved_messages():
    conv_id = f"test-hist-7-{uuid.uuid4().hex[:8]}"
    user_id = f"user-hist-7-{uuid.uuid4().hex[:6]}"

    client.post("/api/chat", json={"message": "Step 1: Planning", "conversation_id": conv_id, "user_id": user_id})
    client.post("/api/chat", json={"message": "Step 2: Execution", "conversation_id": conv_id, "user_id": user_id})

    res = client.get(f"/api/history/{conv_id}", headers={"X-User-ID": user_id})
    assert res.status_code == 200
    data = res.json()
    assert len(data["messages"]) == 4
    assert data["messages"][0]["content"] == "Step 1: Planning"
    assert data["messages"][2]["content"] == "Step 2: Execution"


# =============================================================================
# 8. Continuing an old conversation appends messages to the correct conversation
# =============================================================================
def test_8_continuing_old_conversation_appends_messages():
    conv_id = f"test-hist-8-{uuid.uuid4().hex[:8]}"
    user_id = f"user-hist-8-{uuid.uuid4().hex[:6]}"

    # Turn 1
    client.post("/api/chat", json={"message": "Hello", "conversation_id": conv_id, "user_id": user_id})
    # Turn 2
    client.post("/api/chat", json={"message": "How are you?", "conversation_id": conv_id, "user_id": user_id})
    # Turn 3
    client.post("/api/chat", json={"message": "Tell me a joke", "conversation_id": conv_id, "user_id": user_id})

    res = client.get(f"/api/history/{conv_id}", headers={"X-User-ID": user_id})
    assert res.status_code == 200
    assert len(res.json()["messages"]) == 6


# =============================================================================
# 9. Starting a new conversation does not overwrite an old one
# =============================================================================
def test_9_starting_new_conversation_does_not_overwrite_old():
    user_id = f"user-hist-9-{uuid.uuid4().hex[:6]}"
    c1 = f"c1-{uuid.uuid4().hex[:6]}"
    c2 = f"c2-{uuid.uuid4().hex[:6]}"

    client.post("/api/chat", json={"message": "Topic A discussion", "conversation_id": c1, "user_id": user_id})
    client.post("/api/chat", json={"message": "Topic B discussion", "conversation_id": c2, "user_id": user_id})

    d1 = client.get(f"/api/history/{c1}", headers={"X-User-ID": user_id}).json()
    d2 = client.get(f"/api/history/{c2}", headers={"X-User-ID": user_id}).json()

    assert d1["id"] == c1
    assert d1["messages"][0]["content"] == "Topic A discussion"
    assert d2["id"] == c2
    assert d2["messages"][0]["content"] == "Topic B discussion"


# =============================================================================
# 10. Two different guest identities cannot access each other's conversations
# =============================================================================
def test_10_two_guest_identities_cannot_access_each_other():
    sess_alice = f"guest_session_alice_{uuid.uuid4().hex[:6]}"
    sess_bob = f"guest_session_bob_{uuid.uuid4().hex[:6]}"
    c_alice = f"calice-{uuid.uuid4().hex[:6]}"

    # Alice creates conversation
    client.post(
        "/api/chat",
        json={"message": "Alice secret recipe", "conversation_id": c_alice, "session_id": sess_alice},
    )

    # Bob tries to list conversations
    bob_list = client.get("/api/history", headers={"X-Session-ID": sess_bob}).json()
    assert not any(c["id"] == c_alice for c in bob_list)

    # Bob tries to fetch Alice's conversation directly
    bob_attempt = client.get(f"/api/history/{c_alice}", headers={"X-Session-ID": sess_bob})
    assert bob_attempt.status_code == 404


# =============================================================================
# 11. Missing or unauthorized conversation IDs return 404
# =============================================================================
def test_11_missing_or_unauthorized_conversation_handled_correctly():
    res = client.get(
        f"/api/history/non-existent-conv-{uuid.uuid4().hex}",
        headers={"X-User-ID": "test-user"},
    )
    assert res.status_code == 404
    assert res.json()["detail"] == "Conversation not found"


# =============================================================================
# 12. Existing long-term memory continues to work
# =============================================================================
@pytest.mark.asyncio
async def test_12_existing_long_term_memory_continues_to_work():
    user_id = f"user-mem-work-{uuid.uuid4().hex[:6]}"
    await memory_store.add_memory(user_id, "User works in aerospace robotics", category=MemoryCategory.PROJECT)

    mems = await memory_store.get_user_memories(user_id)
    assert any("aerospace robotics" in m.memory for m in mems)


# =============================================================================
# 13. Existing routing and execution controls not regressed
# =============================================================================
def test_13_existing_routing_and_controls_not_regressed():
    res = client.post(
        "/api/chat",
        json={"message": "Explain binary search in Python.", "category": "SOFTWARE"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["mode"] == "chat"
    assert data["resolved_domain"] == "software"


# =============================================================================
# Test A: Refresh during an active conversation
# =============================================================================
def test_refresh_active_conversation_restores_id_and_messages():
    """
    1. Send multiple turns.
    2. Confirm conversation ID is assigned.
    3. Simulate browser refresh by reading active conversation ID and fetching /api/history/{id}.
    4. Verify the exact conversation ID and ordered messages are restored.
    """
    sess_id = f"guest_sess_refresh_{uuid.uuid4().hex[:6]}"
    p1 = "First turn: What is distributed consensus?"
    p2 = "Second turn: How does Raft differ from Paxos?"

    # Turn 1: create conversation
    r1 = client.post(
        "/api/chat",
        json={"message": p1, "session_id": sess_id},
    )
    assert r1.status_code == 200
    d1 = r1.json()
    conv_id = d1["conversation_id"]
    assert conv_id is not None

    # Turn 2: continue conversation
    r2 = client.post(
        "/api/chat",
        json={"message": p2, "conversation_id": conv_id, "session_id": sess_id},
    )
    assert r2.status_code == 200
    assert r2.json()["conversation_id"] == conv_id

    # Simulated browser refresh: frontend reads chai_active_conversation_id and fetches detail
    simulated_active_id = conv_id
    restore_res = client.get(
        f"/api/history/{simulated_active_id}",
        headers={"X-Session-ID": sess_id},
    )
    assert restore_res.status_code == 200
    restored = restore_res.json()
    assert restored["id"] == conv_id
    msgs = restored["messages"]
    assert len(msgs) == 4  # 2 user messages + 2 assistant messages
    assert msgs[0]["role"] == "user" and msgs[0]["content"] == p1
    assert msgs[1]["role"] == "assistant"
    assert msgs[2]["role"] == "user" and msgs[2]["content"] == p2
    assert msgs[3]["role"] == "assistant"


# =============================================================================
# Test B: Continue after refresh
# =============================================================================
def test_continue_conversation_after_refresh():
    """
    1. Restore an existing conversation.
    2. Send a new message using the restored conversation ID.
    3. Verify the message is appended to the same conversation without creating duplicates.
    """
    sess_id = f"guest_sess_cont_{uuid.uuid4().hex[:6]}"
    # Seed initial turn
    r1 = client.post(
        "/api/chat",
        json={"message": "Define idempotency in REST APIs.", "session_id": sess_id},
    )
    assert r1.status_code == 200
    conv_id = r1.json()["conversation_id"]

    # Refresh restores conv_id
    restored_id = conv_id

    # Turn after refresh
    r2 = client.post(
        "/api/chat",
        json={"message": "Can a POST request be idempotent?", "conversation_id": restored_id, "session_id": sess_id},
    )
    assert r2.status_code == 200
    assert r2.json()["conversation_id"] == conv_id

    # Verify conversation now has 4 messages and only 1 conversation exists for this user
    list_res = client.get("/api/history", headers={"X-Session-ID": sess_id})
    user_convs = list_res.json()
    assert len(user_convs) == 1
    assert user_convs[0]["id"] == conv_id


# =============================================================================
# Test C: New Chat remains new
# =============================================================================
def test_new_chat_clears_active_reference_and_refresh_stays_new():
    """
    1. Existing conversation exists.
    2. User clicks New Chat: chai_active_conversation_id cleared (simulated as None).
    3. Refresh before sending any message: active ID is None.
    4. First message creates a brand new conversation without overwriting older conversation.
    """
    sess_id = f"guest_sess_newchat_{uuid.uuid4().hex[:6]}"
    r1 = client.post(
        "/api/chat",
        json={"message": "First project notes.", "session_id": sess_id},
    )
    conv_1 = r1.json()["conversation_id"]

    # User clicks New Chat -> active conversation cleared
    active_storage_id = None

    # Browser refreshes: active_storage_id is None -> no conversation restored
    assert active_storage_id is None

    # User sends first message in new chat
    r2 = client.post(
        "/api/chat",
        json={"message": "Second project notes.", "session_id": sess_id},
    )
    conv_2 = r2.json()["conversation_id"]
    assert conv_2 != conv_1

    # Both conversations remain intact in history
    list_res = client.get("/api/history", headers={"X-Session-ID": sess_id})
    ids = [c["id"] for c in list_res.json()]
    assert conv_1 in ids
    assert conv_2 in ids


# =============================================================================
# Test D: Open a different saved conversation
# =============================================================================
def test_switching_saved_conversations_updates_active_and_refresh_loads_it():
    """
    1. Create Conversation A and Conversation B.
    2. Switch to Conversation B -> active conversation ID updated to B.
    3. Refresh -> restores Conversation B.
    """
    sess_id = f"guest_sess_switch_{uuid.uuid4().hex[:6]}"
    rA = client.post("/api/chat", json={"message": "Topic Alpha", "session_id": sess_id})
    conv_A = rA.json()["conversation_id"]

    rB = client.post("/api/chat", json={"message": "Topic Beta", "session_id": sess_id})
    conv_B = rB.json()["conversation_id"]

    # User switches to B: active storage is set to conv_B
    active_storage_id = conv_B

    # On refresh:
    restore_res = client.get(f"/api/history/{active_storage_id}", headers={"X-Session-ID": sess_id})
    assert restore_res.status_code == 200
    assert restore_res.json()["id"] == conv_B
    assert "Beta" in restore_res.json()["messages"][0]["content"]


# =============================================================================
# Test E: Missing or inaccessible conversation
# =============================================================================
def test_stale_or_unauthorized_conversation_returns_404():
    """
    Stale IDs and unauthorized IDs must return 404 so the frontend clears
    the active ID and shows a clean new chat rather than hanging in an infinite loop.
    """
    stale_id = f"stale-conv-{uuid.uuid4().hex}"
    res = client.get(f"/api/history/{stale_id}", headers={"X-Session-ID": "random-guest"})
    assert res.status_code == 404


# =============================================================================
# Test F: Guest identity initialization and isolation
# =============================================================================
def test_guest_identity_with_guest_session_placeholder_isolated():
    """
    Verify that when user_id is 'guest_session' (from frontend /guest route),
    isolation is strictly enforced using session_id, preventing Guest 1 and Guest 2
    from seeing or restoring each other's chats.
    """
    sess_1 = f"sess_isolated_1_{uuid.uuid4().hex[:6]}"
    sess_2 = f"sess_isolated_2_{uuid.uuid4().hex[:6]}"

    # Guest 1 sends message with user_id="guest_session" (the default prop in App.tsx)
    r1 = client.post(
        "/api/chat",
        json={"message": "Guest 1 private plans", "user_id": "guest_session", "session_id": sess_1},
    )
    assert r1.status_code == 200
    conv_1 = r1.json()["conversation_id"]

    # Guest 2 attempts to restore Guest 1's conversation with user_id="guest_session" and sess_2
    r_hack = client.get(
        f"/api/history/{conv_1}",
        headers={"X-User-ID": "guest_session", "X-Session-ID": sess_2},
    )
    assert r_hack.status_code == 404

    # Guest 1 restores own conversation successfully
    r_legit = client.get(
        f"/api/history/{conv_1}",
        headers={"X-User-ID": "guest_session", "X-Session-ID": sess_1},
    )
    assert r_legit.status_code == 200
    assert r_legit.json()["id"] == conv_1
