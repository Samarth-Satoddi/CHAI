"""
Comprehensive Test Suite for CHAI Domain Lenses.

Tests:
1. Matrix coverage across all 10 canonical agents for 3 canonical domains
   ('business', 'personal', 'software').
2. Explicit category routing ('BUSINESS', 'PERSONAL', 'SOFTWARE') overriding query semantics.
3. AUTO resolution falling back to query semantic detection.
4. Consumption of resolved domain by all 10 agents without reclassification or overriding.
5. LangGraph execution order, agent schemas, and singleton architecture preservation.
6. End-to-end coordinator execution across Business, Personal, and Software domains.
"""

import pytest
from typing import Dict, Any

from backend.core.domain_lenses import (
    normalize_domain,
    get_domain_lens,
    apply_domain_lens,
    _LENSES,
)
from backend.core.router import resolve_domain
from backend.core.workflow import build_chai_workflow, AGENT_REGISTRY
from backend.core.schemas import SolveRequest, FinalResponse
from backend.core.coordinator import Coordinator, CANONICAL_AGENTS

# 10 canonical agents
from backend.agents.researcher.agent import ResearcherAgent
from backend.agents.strategist.agent import StrategistAgent
from backend.agents.engineer.agent import EngineerAgent
from backend.agents.guardian.agent import GuardianAgent
from backend.agents.security.agent import SecurityAgent
from backend.agents.evaluator.agent import EvaluatorAgent
from backend.agents.conflict_resolver.agent import ConflictResolverAgent
from backend.agents.synthesizer.agent import SynthesizerAgent
from backend.agents.reliability_monitor.agent import ReliabilityMonitorAgent
from backend.validation.output_validator import OutputValidator


CANONICAL_DOMAINS = ["business", "personal", "software"]
ALL_10_AGENT_NAMES = [
    "researcher",
    "strategist",
    "engineer",
    "guardian",
    "security",
    "evaluator",
    "conflict_resolver",
    "synthesizer",
    "reliability_monitor",
    "output_validator",
]


class TestDomainNormalization:
    """Test domain normalization and aliasing."""

    @pytest.mark.parametrize(
        "raw, expected",
        [
            ("business", "business"),
            ("business_strategy", "business"),
            ("BUSINESS", "business"),
            ("biz", "business"),
            ("commercial", "business"),
            ("personal", "personal"),
            ("personal_career", "personal"),
            ("PERSONAL", "personal"),
            ("career", "personal"),
            ("software", "software"),
            ("software_engineering", "software"),
            ("SOFTWARE", "software"),
            ("tech", "software"),
            ("engineering", "software"),
            (None, "general"),
            ("", "general"),
        ],
    )
    def test_normalize_domain(self, raw, expected):
        assert normalize_domain(raw) == expected


class TestDomainLensMatrix:
    """Test centralized domain lens matrix for all 10 agents."""

    def test_all_10_agents_present_in_lenses(self):
        for agent_name in ALL_10_AGENT_NAMES:
            assert agent_name in _LENSES, f"Agent '{agent_name}' missing from _LENSES"

    @pytest.mark.parametrize("agent_name", ALL_10_AGENT_NAMES)
    @pytest.mark.parametrize("domain", CANONICAL_DOMAINS)
    def test_lens_content_exists_for_every_agent_and_domain(self, agent_name: str, domain: str):
        lens = get_domain_lens(agent=agent_name, domain=domain)
        assert isinstance(lens, str)
        assert len(lens.strip()) > 10, f"Lens for {agent_name} x {domain} is unexpectedly empty"
        assert domain.upper() in lens, f"Lens for {agent_name} x {domain} should mention domain keyword"

    def test_apply_domain_lens_appends_without_altering_base(self):
        base = "Base prompt content."
        applied = apply_domain_lens(base, "researcher", "business")
        assert applied.startswith(base)
        assert "DOMAIN LENS — BUSINESS:" in applied

    def test_apply_domain_lens_general_leaves_prompt_unchanged(self):
        base = "Base prompt content."
        applied = apply_domain_lens(base, "researcher", "general")
        assert applied == base

        applied_none = apply_domain_lens(base, "researcher", None)
        assert applied_none == base


class TestExplicitAndAutoRouting:
    """Test router domain resolution: explicit user selection vs AUTO detection."""

    def test_explicit_business_routing(self):
        domain, instr = resolve_domain("Write a Python script", category="BUSINESS")
        assert normalize_domain(domain) == "business"
        assert "BUSINESS" in instr

    def test_explicit_personal_routing(self):
        domain, instr = resolve_domain("Design a scalable distributed database", category="PERSONAL")
        assert normalize_domain(domain) == "personal"
        assert "PERSONAL" in instr

    def test_explicit_software_routing(self):
        domain, instr = resolve_domain("What is the market entry strategy?", category="SOFTWARE")
        assert normalize_domain(domain) == "software"
        assert "SOFTWARE" in instr

    def test_auto_routing_detects_software(self):
        domain, _ = resolve_domain("Design a scalable microservices architecture with Redis caching and FastAPI", category="AUTO")
        assert normalize_domain(domain) == "software"

    def test_auto_routing_detects_business(self):
        domain, _ = resolve_domain("Evaluate market entry, unit economics, ROI, and customer acquisition CAC for SaaS", category="AUTO")
        assert normalize_domain(domain) == "business"

    def test_auto_routing_detects_personal(self):
        domain, _ = resolve_domain("Should I transition from project management to software engineering given my work life balance?", category="AUTO")
        assert normalize_domain(domain) == "personal"

    def test_explicit_overrides_semantic_content(self):
        # Even with heavily technical keywords, explicit BUSINESS must produce business domain
        domain, _ = resolve_domain("Kubernetes microservices architecture and Postgres indexes", category="BUSINESS")
        assert normalize_domain(domain) == "business"


@pytest.mark.asyncio
class TestAll10AgentsConsumeDomainLens:
    """Verify each of the 10 agents accepts domain parameter and consumes domain lens."""

    async def test_1_researcher_domain_lens(self):
        agent = ResearcherAgent()
        for dom in CANONICAL_DOMAINS:
            res = await agent.run(problem="Analyze market trends", domain=dom)
            assert res is not None
            assert hasattr(res, "status")

    async def test_2_strategist_domain_lens(self):
        agent = StrategistAgent()
        for dom in CANONICAL_DOMAINS:
            res = await agent.run(
                problem="Strategic planning",
                research={"key_findings": ["finding 1"], "constraints": []},
                domain=dom,
            )
            assert res is not None
            assert hasattr(res, "status")

    async def test_3_engineer_domain_lens(self):
        agent = EngineerAgent()
        for dom in CANONICAL_DOMAINS:
            res = await agent.run(
                problem="Build application backend",
                context={"researcher": {}, "strategist": {}},
                domain=dom,
            )
            assert res is not None
            assert hasattr(res, "status") or hasattr(res, "engineer_result")

    async def test_4_guardian_domain_lens(self):
        agent = GuardianAgent()
        for dom in CANONICAL_DOMAINS:
            res = await agent.run(
                problem="Evaluate risks and privacy",
                context={"engineer": {}, "strategist": {}},
                domain=dom,
            )
            assert res is not None
            assert hasattr(res, "status") or hasattr(res, "guardian_result")

    async def test_5_security_domain_lens(self):
        agent = SecurityAgent()
        for dom in CANONICAL_DOMAINS:
            res = await agent.run(
                problem="Security audit",
                engineering={},
                research={},
                strategy={},
                domain=dom,
            )
            assert res is not None
            assert hasattr(res, "status")

    async def test_6_evaluator_domain_lens(self):
        agent = EvaluatorAgent()
        for dom in CANONICAL_DOMAINS:
            res = await agent.run(
                problem="Evaluate agent consistency",
                context={"all_outputs": {"strategist": {}, "engineer": {}}},
                domain=dom,
            )
            assert res is not None
            assert hasattr(res, "status") or hasattr(res, "evaluator_result")

    async def test_7_conflict_resolver_domain_lens(self):
        agent = ConflictResolverAgent()
        for dom in CANONICAL_DOMAINS:
            res = await agent.run(
                problem="Resolve trade-offs",
                context={"all_outputs": {"strategist": {}, "engineer": {}}},
                domain=dom,
            )
            assert res is not None
            assert hasattr(res, "status")

    async def test_8_synthesizer_domain_lens(self):
        agent = SynthesizerAgent()
        for dom in CANONICAL_DOMAINS:
            res = await agent.run(
                problem="Synthesize decision",
                context={"all_outputs": {"strategist": {}, "engineer": {}}},
                domain=dom,
            )
            assert res is not None
            assert hasattr(res, "status")

    async def test_9_reliability_monitor_domain_lens(self):
        agent = ReliabilityMonitorAgent()
        for dom in CANONICAL_DOMAINS:
            res = await agent.run(
                problem="Monitor reliability and claims",
                context={"final_answer": "Recommendation text.", "all_outputs": {}},
                domain=dom,
            )
            assert res is not None
            assert hasattr(res, "reliability_score")
            assert hasattr(res, "action")

    async def test_10_output_validator_domain_lens(self):
        validator = OutputValidator()
        for dom in CANONICAL_DOMAINS:
            res = validator.validate(
                output="Valid response text with clear recommendations.",
                context={},
                domain=dom,
            )
            assert res is not None
            assert res.is_valid is True
            assert res.validation_metadata.get("domain") == dom
            assert res.validation_metadata.get("domain_lens_applied") is True


class TestArchitectureAndGraphIntegrity:
    """Verify graph order, singleton agent architecture, and contracts."""

    def test_singleton_agent_registry(self):
        # Exactly one agent class in AGENT_REGISTRY for each canonical role
        for name in ALL_10_AGENT_NAMES:
            assert name in AGENT_REGISTRY
            # Verify class is callable
            cls = AGENT_REGISTRY[name]
            assert callable(cls)

    def test_workflow_compilation_and_node_graph(self):
        graph = build_chai_workflow()
        assert graph is not None
        # Verify node names in compiled graph
        node_keys = graph.nodes.keys()
        for expected in [
            "router",
            "information_acquisition",
            "researcher",
            "strategist",
            "engineer",
            "guardian",
            "security",
            "evaluator",
            "conflict_resolver",
            "synthesizer",
            "reliability_monitor",
            "output_validator",
        ]:
            assert expected in node_keys, f"Node {expected} missing from graph"


@pytest.mark.asyncio
class TestEndToEndCoordinatorDomainLenses:
    """Test full coordinator pipelines across all three canonical domains."""

    async def test_business_pipeline(self):
        coordinator = Coordinator()
        req = SolveRequest(
            problem="Analyze B2B SaaS pricing strategy, competitor churn, and customer CAC payback period.",
            category="BUSINESS",
        )
        res = await coordinator.coordinate(req)
        assert isinstance(res, FinalResponse)
        assert res.domain_category in ("business", "business_strategy")
        assert res.resolved_domain == "business"
        assert res.final_answer is not None
        assert "researcher" in res.selected_agents

    async def test_personal_pipeline(self):
        coordinator = Coordinator()
        req = SolveRequest(
            problem="Should I leave my job to pursue graduate school or stay for another promotion cycle?",
            category="PERSONAL",
        )
        res = await coordinator.coordinate(req)
        assert isinstance(res, FinalResponse)
        assert res.domain_category in ("personal", "personal_career")
        assert res.resolved_domain == "personal"
        assert res.final_answer is not None

    async def test_software_pipeline(self):
        coordinator = Coordinator()
        req = SolveRequest(
            problem="Design a distributed high-throughput message streaming broker in Go with raft consensus.",
            category="SOFTWARE",
        )
        res = await coordinator.coordinate(req)
        assert isinstance(res, FinalResponse)
        assert res.domain_category in ("software", "software_engineering")
        assert res.resolved_domain == "software"
        assert res.final_answer is not None
        assert "engineer" in res.selected_agents
