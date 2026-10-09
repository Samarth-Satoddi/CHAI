"""
Regression Test Suite for CHAI /api/chat Complex Routing, LangChain Chat Mode,
Core Router Authoritative Precedence, Quota Failure Resilience, and Domain Lenses.
"""
import pytest
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient

from backend.main import app
from backend.core.router import (
    route_request,
    resolve_domain,
    ROUTE_SIMPLE,
    ROUTE_COMPLEX,
)
from backend.core.domain_lenses import normalize_domain
from backend.chat.router import intent_router, IntentRouter
from backend.chat.schemas import IntentResult
from backend.shared.llm_client import llm_client


client = TestClient(app)

SAAS_QUERY = (
    "I want to launch a SaaS product for small businesses. Should I target restaurants, "
    "retail stores, or professional services first? Analyze the market opportunity, "
    "competition, pricing strategy, risks, and recommend the best approach."
)

GENERIC_FALLBACK_SNIPPET = "A useful first pass"


# =============================================================================
# PART 10: CORE ROUTER 9/9 TEST MATRIX
# =============================================================================

@pytest.mark.parametrize(
    "query, expected_route",
    [
        ("What is Python?", ROUTE_SIMPLE),
        ("What is the square root of 64?", ROUTE_SIMPLE),
        ("Which language compiles faster, C or Python?", ROUTE_SIMPLE),
        ("What is ISRO?", ROUTE_SIMPLE),
        ("Explain binary search.", ROUTE_SIMPLE),
        ("Design a secure university learning platform for 50,000 students.", ROUTE_COMPLEX),
        ("Compare C and Python for a production AI system.", ROUTE_COMPLEX),
        ("Build a three-year business strategy.", ROUTE_COMPLEX),
        ("SaaS market opportunity, competition, pricing, risks and recommendation.", ROUTE_COMPLEX),
    ],
)
def test_core_router_decision_matrix(query: str, expected_route: str):
    """
    Verifies authoritative backend/core/router.py correctly routes the 9 canonical test queries.
    """
    decision = route_request(query)
    assert decision.route == expected_route, (
        f"Query '{query}' expected route '{expected_route}', got '{decision.route}' "
        f"(reasoning: {decision.reasoning})"
    )


# =============================================================================
# PART 10: /api/chat MULTI-TURN CONVERSATION TEST
# =============================================================================

def test_api_chat_multi_turn_continuity_and_routing():
    """
    Verifies multi-turn conversational continuity and dynamic routing in /api/chat:
    Turn 1: 'What is Python?' -> chat (LangChain)
    Turn 2: 'What about Java?' -> chat (LangChain + memory)
    Turn 3: 'Now compare them for a production AI application considering performance,
             memory, deployment, ecosystem and maintainability.' -> solve (Coordinator / LangGraph)
    """
    conv_id = "test-conv-multi-turn-routing-101"

    # Turn 1: Simple definition -> CHAT
    res1 = client.post(
        "/api/chat",
        json={"message": "What is Python?", "conversation_id": conv_id},
    )
    assert res1.status_code == 200
    data1 = res1.json()
    assert data1["mode"] == "chat"
    assert data1["message"] and len(data1["message"]) > 10

    # Turn 2: Contextual follow-up -> CHAT
    res2 = client.post(
        "/api/chat",
        json={"message": "What about Java?", "conversation_id": conv_id},
    )
    assert res2.status_code == 200
    data2 = res2.json()
    assert data2["mode"] == "chat"
    assert data2["message"] and len(data2["message"]) > 10

    # Turn 3: Multi-constraint comparison across production criteria -> SOLVE
    turn3_query = (
        "Now compare them for a production AI application considering performance, "
        "memory, deployment, ecosystem and maintainability."
    )
    res3 = client.post(
        "/api/chat",
        json={"message": turn3_query, "conversation_id": conv_id},
    )
    assert res3.status_code == 200
    data3 = res3.json()
    assert data3["mode"] == "solve", (
        f"Expected turn 3 to route to solve, but got mode='{data3.get('mode')}' "
        f"with message: {data3.get('message')[:100]}"
    )
    assert isinstance(data3.get("selected_agents"), list)
    assert len(data3["selected_agents"]) > 0, "Selected agents list must not be empty for complex solve"


# =============================================================================
# PART 10: SAAS REGRESSION TEST
# =============================================================================

def test_saas_query_routes_to_solve_and_executes_pipeline():
    """
    Verifies the exact SaaS production query:
    1. Routed to solve mode (NOT downgraded to chat)
    2. Resolved domain is 'business'
    3. Multi-agent pipeline executes with non-empty selected_agents
    4. Final response is NOT the canned fallback text 'A useful first pass...'
    """
    res = client.post(
        "/api/chat",
        json={
            "message": SAAS_QUERY,
            "category": "AUTO",
            "conversation_id": "test-saas-regression-202",
        },
    )
    assert res.status_code == 200
    data = res.json()

    assert data["mode"] == "solve", (
        f"SaaS query was incorrectly handled as mode='{data.get('mode')}'. "
        f"Expected mode='solve'."
    )
    assert data["resolved_domain"] == "business", (
        f"Expected resolved_domain='business', got '{data.get('resolved_domain')}'"
    )
    assert isinstance(data.get("selected_agents"), list)
    assert len(data["selected_agents"]) > 0, "Selected agents must be populated"

    # Verify coordinator execution statuses and agents
    execution_statuses = data.get("agent_execution_statuses") or []
    executed_agents = [s.get("agent_name") for s in execution_statuses if isinstance(s, dict)]

    # Synthesizer and Reliability Monitor must execute in complex pipeline
    assert "synthesizer" in executed_agents or "synthesizer" in data["selected_agents"]
    assert "reliability_monitor" in executed_agents or "reliability_monitor" in data["selected_agents"]

    final_text = data.get("message") or data.get("final_synthesized_answer") or data.get("final_answer") or ""
    assert GENERIC_FALLBACK_SNIPPET not in final_text, (
        f"Response contained canned fallback string '{GENERIC_FALLBACK_SNIPPET}'!"
    )
    assert len(final_text) > 100, f"Expected substantive analysis, got only {len(final_text)} chars"


# =============================================================================
# PART 10: QUOTA / LLM FAILURE RESILIENCE TEST
# =============================================================================

@pytest.mark.asyncio
async def test_quota_exhaustion_does_not_downgrade_to_chat():
    """
    Mocks the chat router's LLM classification to raise an HTTP 429 / Quota error.
    Verifies that complex queries STILL resolve to 'solve' via backend.core.router.
    """
    router = IntentRouter()

    # Mock llm_client.generate_content to raise 429 quota exhaustion
    with patch.object(
        llm_client,
        "generate_content",
        side_effect=Exception("429 ResourceExhausted: Quota exceeded for quota metric 'GenerateContent'"),
    ):
        result = await router.classify(SAAS_QUERY)
        assert result.intent == "solve", (
            f"Quota exhaustion caused complex query to downgrade to '{result.intent}'! "
            f"Reason: {result.reason}"
        )
        assert result.confidence >= 0.85

        # Also verify other complex queries under 429 error
        arch_query = "Design a secure university learning platform for 50,000 students."
        arch_result = await router.classify(arch_query)
        assert arch_result.intent == "solve"

        tech_query = "Compare C and Python for a production AI system."
        tech_result = await router.classify(tech_query)
        assert tech_result.intent == "solve"


# =============================================================================
# PART 10: FRONTEND ERROR HIDING VERIFICATION
# =============================================================================

def test_backend_error_is_not_hidden():
    """
    Verifies that when /api/chat encounters a bad request (empty message),
    it returns proper HTTP 400 error detail, preventing error hiding.
    """
    res = client.post("/api/chat", json={"message": "   "})
    assert res.status_code == 400
    detail = res.json().get("detail", "")
    assert "Message cannot be empty" in detail


# =============================================================================
# PART 11: DOMAIN REGRESSION TESTS
# =============================================================================

def test_domain_regression_auto_and_explicit():
    """
    Verifies the Domain Lens matrix:
    AUTO + SaaS strategy -> BUSINESS
    AUTO + backend architecture -> SOFTWARE
    AUTO + career decision -> PERSONAL
    BUSINESS explicitly selected + technical SaaS question -> BUSINESS
    SOFTWARE explicitly selected + pricing question -> SOFTWARE
    PERSONAL explicitly selected + technology career question -> PERSONAL
    Explicit category MUST NEVER be overridden by AUTO classification.
    """
    # 1. AUTO + SaaS strategy -> BUSINESS
    dom1, _ = resolve_domain(problem=SAAS_QUERY, category="AUTO")
    assert normalize_domain(dom1) == "business"

    # 2. AUTO + backend architecture -> SOFTWARE
    dom2, _ = resolve_domain(
        problem="Design the backend architecture and database schema with microservices.",
        category="AUTO",
    )
    assert normalize_domain(dom2) == "software"

    # 3. AUTO + career decision -> PERSONAL
    dom3, _ = resolve_domain(
        problem="Should I quit my job given my financial situation and parents want me to?",
        category="AUTO",
    )
    assert normalize_domain(dom3) == "personal"

    # 4. BUSINESS explicitly selected + technical SaaS question -> BUSINESS
    dom4, _ = resolve_domain(
        problem="Design the backend architecture and tech stack for my SaaS startup.",
        category="BUSINESS",
    )
    assert normalize_domain(dom4) == "business", "Explicit BUSINESS must override technical query terms"

    # 5. SOFTWARE explicitly selected + pricing question -> SOFTWARE
    dom5, _ = resolve_domain(
        problem="What pricing strategy and customer acquisition cost should we adopt?",
        category="SOFTWARE",
    )
    assert normalize_domain(dom5) == "software", "Explicit SOFTWARE must override business query terms"

    # 6. PERSONAL explicitly selected + technology career question -> PERSONAL
    dom6, _ = resolve_domain(
        problem="How do I transition into artificial intelligence engineering?",
        category="PERSONAL",
    )
    assert normalize_domain(dom6) == "personal", "Explicit PERSONAL must override technology terms"
