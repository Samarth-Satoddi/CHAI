"""
CHAI Reasoning Quality Regression Test Suite.

Verifies fixes for the three core quality failures:
1. PERSONAL Decision-Making: Job offer relocation vs family/WLB dilemma returns
   useful preliminary guidance, multi-factor trade-offs, conditional recommendation,
   and focused follow-up questions without refusing or demanding the user perform the analysis.
2. BUSINESS Strategy: SaaS market targeting separates verified facts from hypotheses,
   avoids fabricating LTV/churn/POS/payment assumptions, provides conditional recommendations,
   and suggests practical customer-discovery experiments.
3. SOFTWARE Architecture: Multi-user auth architecture correctly separates AuthN from AuthZ,
   distinguishes JWT signature verification from decryption, addresses CSRF and XSS realities
   of HttpOnly cookies, details refresh token rotation & reuse detection, PostgreSQL RLS,
   and separates MVP requirements from optional Redis infrastructure.
4. COORDINATOR & RELIABILITY GATE: Missing information preserves preliminary guidance;
   decision dilemmas proceed with limitations; 3 canonical domains + AUTO resolution preserved;
   CHAT vs SOLVE separation maintained.
"""

import pytest
import re
from unittest.mock import patch, AsyncMock

from backend.agents.synthesizer.agent import SynthesizerAgent
from backend.agents.reliability_monitor.agent import ReliabilityMonitorAgent
from backend.agents.reliability_monitor.schemas import ReliabilityAction, ReliabilityLevel
from backend.validation.output_validator import OutputValidator
from backend.core.domain_lenses import normalize_domain, get_domain_lens, _LENSES
from backend.core.router import resolve_domain, route_request, ROUTE_SIMPLE, ROUTE_COMPLEX
from backend.core.coordinator import Coordinator, CANONICAL_AGENTS
from backend.core.schemas import SolveRequest, FinalResponse
from backend.core.workflow import build_chai_workflow, AGENT_REGISTRY


PERSONAL_JOB_OFFER_QUERY = (
    "I have two job offers. One pays more but requires relocation, while the other pays less "
    "but gives me better work-life balance and keeps me close to my family. How should I decide?"
)

BUSINESS_SAAS_TARGET_QUERY = (
    "I want to launch a SaaS product for small businesses. Should I target restaurants, "
    "retail stores, or professional services first? Analyze the market opportunity, "
    "competition, pricing strategy, risks, and recommend the best approach."
)

SOFTWARE_AUTH_ARCH_QUERY = (
    "I am building a multi-user SaaS application. Design a secure authentication and authorization "
    "architecture using a React frontend, FastAPI backend, and PostgreSQL database. "
    "Include APIs, data flow, security controls, and deployment considerations."
)


# =============================================================================
# PART 1: PERSONAL DECISION-MAKING REGRESSION TESTS
# =============================================================================

class TestPersonalDecisionReasoning:
    """Tests for the PERSONAL job-offer decision dilemma."""

    def test_personal_job_offer_synthesizer_output(self):
        """
        Synthesizer must deliver substantive preliminary guidance for the job offer query:
        1. Restates the decision and known facts.
        2. Compares compensation, relocation costs, career growth, WLB, family, long-term consequences.
        3. Explains when each job offer might be preferable.
        4. Identifies unknown factors without inventing personal circumstances.
        5. Provides a conditional recommendation and decision framework.
        6. Asks focused follow-up questions.
        7. Does not refuse or ask user to provide the strategic evaluation.
        """
        synthesizer = SynthesizerAgent()
        result = synthesizer._make_mock_output(
            problem=PERSONAL_JOB_OFFER_QUERY,
            context={"domain": "personal", "all_outputs": {}},
        )
        assert result is not None
        assert result.status.value == "completed"
        ans = result.final_answer

        # 1. Must NOT refuse or demand user provide evaluation
        assert "Additional information is required before a completed answer can be provided" not in ans
        assert "Please provide the details above to proceed" not in ans

        # 2. Restate decision & known facts neutrally
        assert "Offer A" in ans and "Offer B" in ans
        assert "relocation" in ans.lower()
        assert "family" in ans.lower()
        assert "work-life balance" in ans.lower() or "wlb" in ans.lower()

        # 3. Comprehensive multi-factor comparison
        assert "Compensation" in ans or "compensation" in ans
        assert "Relocation" in ans or "relocation" in ans
        assert "Career Growth" in ans or "growth" in ans.lower()
        assert "Work-Life Balance" in ans or "well-being" in ans.lower()
        assert "Family" in ans or "family" in ans.lower()
        assert "Consequences" in ans or "3–5 Year" in ans or "Long-Term" in ans

        # 4. Explains when each offer is preferable
        assert "Offer A is preferable" in ans or "Offer A might be preferable" in ans
        assert "Offer B is preferable" in ans or "Offer B might be preferable" in ans

        # 5. Identifies unknown factors without fabricating them
        assert "Unknown Factors" in ans or "Clarifying" in ans
        # Ensure it doesn't fabricate a specific dollar salary number for user
        assert "$120,000" not in ans and "$150,000" not in ans

        # 6. Provides conditional recommendation & decision framework
        assert "Decision Framework" in ans or "Net Purchasing Power" in ans or "Framework" in ans

        # 7. Focused follow-up questions
        assert "?" in ans
        assert "salary difference" in ans.lower() or "compensation difference" in ans.lower() or "cost of living" in ans.lower()

        # 8. Metadata verification
        assert len(result.key_decisions) > 0
        assert any("decision framework" in d.decision.lower() for d in result.key_decisions)
        assert len(result.missing_information) > 0

    def test_personal_job_offer_output_validator(self):
        """Validator should accept valid preliminary guidance and reject bare refusal."""
        validator = OutputValidator()
        synthesizer = SynthesizerAgent()
        result = synthesizer._make_mock_output(
            problem=PERSONAL_JOB_OFFER_QUERY,
            context={"domain": "personal", "all_outputs": {}},
        )

        val_result = validator.validate(result.final_answer, domain="personal")
        assert val_result.is_valid is True
        assert val_result.validation_metadata.get("domain") == "personal"

        # Bare refusal must fail validation for personal domain
        bare_refusal = (
            "Additional information is required before a completed answer can be provided.\n"
            "Please provide further details regarding your salary."
        )
        val_bad = validator.validate(bare_refusal, domain="personal")
        assert val_bad.is_valid is False
        assert any("Unhelpful refusal" in err for err in val_bad.errors)


# =============================================================================
# PART 2: BUSINESS REASONING & EVIDENCE QUALITY REGRESSION TESTS
# =============================================================================

class TestBusinessReasoningAndEvidenceQuality:
    """Tests for business reasoning, evidence distinction, and hypothesis calibration."""

    def test_business_saas_synthesizer_output(self):
        """
        Synthesizer must deliver rigorous commercial guidance for SaaS SMB targeting:
        1. Compares restaurants, retail stores, and professional services on explicit criteria.
        2. Explicitly separates verified facts/benchmarks from hypotheses/assumptions.
        3. Does not fabricate ungrounded churn rates, LTV, or unprompted POS/payment dependencies.
        4. Provides a provisional recommendation conditional on product capabilities.
        5. Explains what product characteristics could alter the recommendation.
        6. Suggests practical customer-discovery experiments with measurable decision criteria.
        """
        synthesizer = SynthesizerAgent()
        result = synthesizer._make_mock_output(
            problem=BUSINESS_SAAS_TARGET_QUERY,
            context={"domain": "business", "all_outputs": {}},
        )
        assert result is not None
        assert result.status.value == "completed"
        ans = result.final_answer

        # 1. Compares all three segments
        assert "Restaurants" in ans or "restaurants" in ans
        assert "Retail" in ans or "retail" in ans
        assert "Professional Services" in ans or "professional services" in ans

        # 2. Uses explicit evaluation criteria
        assert "Willingness to Pay" in ans or "Margin" in ans
        assert "Sales Velocity" in ans or "Decision-Making" in ans
        assert "Onboarding" in ans or "Friction" in ans

        # 3. Explicitly distinguishes verified facts from hypotheses
        assert "Verified" in ans or "Empirical" in ans
        assert "Hypotheses" in ans or "working hypotheses" in ans.lower()

        # 4. Qualifies churn and POS/payment assumptions
        assert "POS" in ans
        # Must treat POS integration as conditional, not mandatory
        assert "conditional" in ans.lower() or "scope" in ans.lower() or "not necessarily" in ans.lower() or "depends" in ans.lower()

        # 5. Provisional recommendation is conditional
        assert "Provisional Recommendation" in ans or "Recommendation" in ans
        assert "Product Characteristics That Change" in ans or "change" in ans.lower()

        # 6. Practical customer-discovery experiments with measurable criteria
        assert "Customer-Discovery Experiments" in ans or "Discovery" in ans
        assert "interview" in ans.lower()
        assert "Decision Gate" in ans or "pre-commitments" in ans.lower()

    def test_business_output_validator_flags_unhedged_churn_claims(self):
        """Validator should add a warning if an output claims guaranteed zero churn."""
        validator = OutputValidator()
        bad_text = "Targeting professional services yields guaranteed 0% churn and unlimited profits."
        val_res = validator.validate(bad_text, domain="business")
        assert any("churn" in w.lower() for w in val_res.warnings)


# =============================================================================
# PART 3: SOFTWARE ENGINEERING & SECURITY ACCURACY REGRESSION TESTS
# =============================================================================

class TestSoftwareEngineeringAndSecurityAccuracy:
    """Tests for software architecture and security accuracy."""

    def test_software_saas_auth_synthesizer_output(self):
        """
        Synthesizer must deliver accurate software & security architecture:
        1. Separates authentication (who you are) from authorization (what you can do).
        2. Distinguishes signed JWTs (JWS) from encrypted tokens (JWE).
        3. Never describes JWT signature verification as decryption.
        4. Validates signature, issuer, audience, and expiration.
        5. Explains HttpOnly cookie security AND its XSS limitations (ambient request execution).
        6. Addresses CSRF protection (custom headers, Double Submit, SameSite).
        7. Details refresh token rotation, revocation, and reuse detection (family-based).
        8. Covers multi-tenant data isolation and PostgreSQL Row-Level Security (RLS).
        9. Distinguishes MVP (PostgreSQL session table) from optional Redis infrastructure.
        """
        synthesizer = SynthesizerAgent()
        result = synthesizer._make_mock_output(
            problem=SOFTWARE_AUTH_ARCH_QUERY,
            context={"domain": "software", "all_outputs": {}},
        )
        assert result is not None
        assert result.status.value == "completed"
        ans = result.final_answer

        # 1. Authentication vs Authorization
        assert "Authentication" in ans and "Authorization" in ans
        assert "Argon2id" in ans or "bcrypt" in ans

        # 2. JWT signature verification != decryption
        assert "Signature Verification is NOT Decryption" in ans or "not decrypt" in ans.lower()
        assert "signed JWT" in ans or "JWS" in ans
        # Ensure the inaccurate phrase "decrypting the JWT" is NOT present
        assert not re.search(r"\bdecrypting the jwt\b", ans, re.IGNORECASE)

        # 3. Claims validation
        assert "iss" in ans or "issuer" in ans.lower()
        assert "exp" in ans or "expiration" in ans.lower()
        assert "aud" in ans or "audience" in ans.lower()

        # 4. Cookie security attributes, CSRF, and XSS boundaries
        assert "HttpOnly" in ans
        assert "CSRF" in ans
        assert "XSS" in ans
        # Must explain ambient request execution limitation of HttpOnly cookies
        assert "ambient" in ans.lower() or "automatically attach" in ans.lower() or "document.cookie" in ans

        # 5. Refresh token rotation & reuse detection
        assert "Refresh Token" in ans or "refresh_tokens" in ans
        assert "Rotation" in ans or "rotate" in ans.lower()
        assert "Reuse Detection" in ans or "family" in ans.lower()

        # 6. Multi-tenant isolation & PostgreSQL RLS
        assert "Row-Level Security" in ans or "RLS" in ans or "tenant_id" in ans

        # 7. MVP vs Production hardening (Redis optional)
        assert "MVP" in ans
        assert "Redis" in ans
        # Redis should be explained as optional / hardening, not required day-one
        assert "optional" in ans.lower() or "not needed" in ans.lower() or "justified" in ans.lower()

    def test_software_output_validator_detects_decryption_claim(self):
        """Validator flags calling JWT signature verification decryption as a technical inaccuracy."""
        validator = OutputValidator()
        inaccurate_text = (
            "The backend validates the user by decrypting the JWT token signature using the secret key."
        )
        val_res = validator.validate(inaccurate_text, domain="software")
        assert any("decryption" in w.lower() for w in val_res.warnings)


# =============================================================================
# PART 4: COORDINATOR & RELIABILITY GATE REGRESSION TESTS
# =============================================================================

@pytest.mark.asyncio
class TestCoordinatorAndReliabilityGate:
    """Tests for coordinator missing-information handling and domain resolution."""

    async def test_coordinator_preserves_final_answer_on_request_more_information(self):
        """
        When ReliabilityAction is REQUEST_MORE_INFORMATION, Coordinator must NOT wipe out
        final_answer; it must deliver the provisional guidance followed by clarifying questions.
        """
        coordinator = Coordinator()

        # Mock reliability monitor to return REQUEST_MORE_INFORMATION with missing items
        mock_rm = ReliabilityMonitorAgent()
        mock_res = mock_rm._make_mock_output(
            problem=PERSONAL_JOB_OFFER_QUERY,
            context={
                "domain": "personal",
                "final_answer": "## Provisional Guidance\nCompare Offer A and B based on net income delta.",
                "all_outputs": {
                    "conflict_resolver": {
                        "missing_information": [
                            "Exact net salary delta between Offer A and B",
                            "Relocation package details",
                        ]
                    }
                },
            },
        )
        # Force action to REQUEST_MORE_INFORMATION with explicit missing items
        mock_res.action = ReliabilityAction.REQUEST_MORE_INFORMATION
        mock_res.missing_information = [
            "Exact net salary delta between Offer A and B",
            "Relocation package details",
        ]

        # Synthesize a substantive answer
        synthesizer = SynthesizerAgent()
        mock_synth = synthesizer._make_mock_output(
            problem=PERSONAL_JOB_OFFER_QUERY,
            context={"domain": "personal", "all_outputs": {}},
        )
        substantive_answer = (
            "## 1. Decision Restatement\nEvaluating Offer A and B.\n\n"
            "## 2. Multi-Factor Trade-offs\nCompensation vs family proximity."
        )
        mock_synth.final_answer = substantive_answer

        with patch.object(coordinator.synthesizer, "synthesize", AsyncMock(return_value=mock_synth)), \
             patch.object(coordinator.synthesizer, "run", AsyncMock(return_value=mock_synth)), \
             patch.object(coordinator.reliability_monitor, "run", AsyncMock(return_value=mock_res)):
            req = SolveRequest(
                problem=PERSONAL_JOB_OFFER_QUERY,
                category="PERSONAL",
                selected_agents=["synthesizer", "reliability_monitor"],
            )
            res = await coordinator.coordinate(req)
            assert isinstance(res, FinalResponse)
            # Must contain the substantive preliminary guidance
            assert "Decision Restatement" in res.final_answer
            assert "Multi-Factor Trade-offs" in res.final_answer
            # Must append the clarifying details rather than replacing the text
            assert "Clarifying Details for a Tailored Recommendation" in res.final_answer
            assert "Exact net salary delta" in res.final_answer

    async def test_reliability_monitor_proceeds_with_limitations_for_decision_queries(self):
        """
        In personal decision dilemmas with ordinary missing variables (salary delta, relocation costs),
        ReliabilityMonitorAgent must return PROCEED_WITH_LIMITATIONS, not block with REQUEST_MORE_INFORMATION.
        """
        rm = ReliabilityMonitorAgent()
        res = rm._make_mock_output(
            problem=PERSONAL_JOB_OFFER_QUERY,
            context={
                "domain": "personal",
                "final_answer": "Substantive evaluation of Job Offer A vs Job Offer B.",
                "all_outputs": {
                    "conflict_resolver": {
                        "missing_information": [
                            "Exact compensation difference",
                            "Relocation costs",
                        ]
                    }
                },
            },
        )
        assert res.action == ReliabilityAction.PROCEED_WITH_LIMITATIONS
        assert "jurisdiction" not in str(res.missing_information).lower()


# =============================================================================
# PART 5: DOMAIN ROUTING, PRECEDENCE & ARCHITECTURE INTEGRITY
# =============================================================================

class TestArchitectureAndRoutingIntegrity:
    """Verifies architectural invariants across domain lenses and routing."""

    def test_canonical_domain_resolution_matrix(self):
        """Tests that AUTO and explicit categories map to the 3 canonical domains."""
        # AUTO
        d_biz, _ = resolve_domain(problem=BUSINESS_SAAS_TARGET_QUERY, category="AUTO")
        assert normalize_domain(d_biz) == "business"

        d_pers, _ = resolve_domain(problem=PERSONAL_JOB_OFFER_QUERY, category="AUTO")
        assert normalize_domain(d_pers) == "personal"

        d_soft, _ = resolve_domain(problem=SOFTWARE_AUTH_ARCH_QUERY, category="AUTO")
        assert normalize_domain(d_soft) == "software"

        # Explicit overrides
        d_override, _ = resolve_domain(problem=SOFTWARE_AUTH_ARCH_QUERY, category="BUSINESS")
        assert normalize_domain(d_override) == "business"

        d_override_p, _ = resolve_domain(problem=BUSINESS_SAAS_TARGET_QUERY, category="PERSONAL")
        assert normalize_domain(d_override_p) == "personal"

    def test_core_router_chat_vs_solve_separation(self):
        """Verifies simple queries use chat and complex reasoning queries use solve."""
        simple_res = route_request("What is Python?")
        assert simple_res.route == ROUTE_SIMPLE

        complex_job = route_request(PERSONAL_JOB_OFFER_QUERY)
        assert complex_job.route == ROUTE_COMPLEX

        complex_saas = route_request(BUSINESS_SAAS_TARGET_QUERY)
        assert complex_saas.route == ROUTE_COMPLEX

        complex_auth = route_request(SOFTWARE_AUTH_ARCH_QUERY)
        assert complex_auth.route == ROUTE_COMPLEX

    def test_architecture_singleton_registry(self):
        """Verifies exactly one class per canonical role and no duplicate graphs."""
        for agent_name in [
            "researcher", "strategist", "engineer", "guardian", "security",
            "evaluator", "conflict_resolver", "synthesizer", "reliability_monitor",
            "output_validator",
        ]:
            assert agent_name in AGENT_REGISTRY
            assert callable(AGENT_REGISTRY[agent_name])
            # Exactly 3 resolved domains in lenses
            assert "business" in _LENSES[agent_name]
            assert "personal" in _LENSES[agent_name]
            assert "software" in _LENSES[agent_name]

        workflow = build_chai_workflow()
        assert workflow is not None
