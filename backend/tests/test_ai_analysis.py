import json
import pytest
from sqlalchemy.orm import Session
from app.ai.analyzer import CompanyIntelligenceAnalyzer
from app.ai.base import AICompletionResult, BaseAIProvider
from app.database import Company, CompanyFact, CompanyProfile, ResearchPage, ResearchRun


class MockAIProvider(BaseAIProvider):
    def __init__(self, response_text: str, is_avail: bool = True):
        super().__init__(model_name="mock-ai")
        self.response_text = response_text
        self._avail = is_avail

    async def is_available(self) -> bool:
        return self._avail

    async def generate_completion(self, prompt: str, system_instruction=None, temperature=0.2):
        if not self._avail:
            raise ConnectionError("Mock AI provider unreachable")
        return AICompletionResult(
            raw_text=self.response_text,
            model="mock-ai",
            provider="mock",
        )


@pytest.mark.asyncio
async def test_evidence_snippet_verification_and_downgrade(db_session: Session):
    company = Company(
        name="Veritas Signals",
        website="https://veritas-signals.com",
        normalized_domain="veritas-signals.com",
        status="ACTIVE",
    )
    db_session.add(company)
    db_session.flush()

    run = ResearchRun(company_id=company.id, status="RUNNING")
    db_session.add(run)
    db_session.flush()

    real_page_text = (
        "Veritas Signals provides enterprise automated market intelligence. "
        "Our flagship product SignalLens extracts executive competitive insights."
    )
    page = ResearchPage(
        company_id=company.id,
        research_run_id=run.id,
        url="https://veritas-signals.com/product",
        title="SignalLens Product",
        extracted_text=real_page_text,
        content_hash=ResearchPage.compute_hash(real_page_text),
        http_status=200,
    )
    db_session.add(page)
    db_session.flush()

    # Mock response containing:
    # 1. Fact 1 with VERBATIM snippet found in text -> Should be VERIFIED_FACT
    # 2. Fact 2 with hallucinated snippet NOT found in text -> Should be downgraded to ASSUMPTION
    ai_json = {
        "company_name": "Veritas Signals",
        "industry": "Market Intelligence",
        "business_model": "SaaS",
        "products_services": ["SignalLens"],
        "target_customers": ["Enterprise executives"],
        "customer_problems": ["Competitive blindness"],
        "revenue_streams": ["Software subscriptions"],
        "geographical_markets": ["Global"],
        "positioning": "Automated market intelligence",
        "growth_related_information": ["Expanding customer base"],
        "verified_facts": [
            {
                "category": "products_services",
                "statement": "The flagship product is SignalLens.",
                "evidence_snippet": "Our flagship product SignalLens extracts executive competitive insights.",
                "source_page_id": page.id,
            },
            {
                "category": "funding",
                "statement": "Veritas raised $50M in Series B led by Sequoia.",
                "evidence_snippet": "Veritas closed a 50 million series B financing round led by Sequoia Capital.",
                "source_page_id": page.id,
            },
        ],
        "assumptions": [
            {
                "category": "strategy",
                "statement": "The company likely targets Fortune 500 sales teams.",
            }
        ],
        "unknown_information": [
            "Exact headcount and founders are not disclosed on public pages.",
        ],
    }

    provider = MockAIProvider(response_text=json.dumps(ai_json))
    analyzer = CompanyIntelligenceAnalyzer(provider)

    profile = await analyzer.analyze_and_persist(company, run, [page], db_session)
    assert profile is not None
    assert profile.profile_version == 1
    assert run.ai_analysis_status == "COMPLETED"

    # Query saved facts
    facts = db_session.query(CompanyFact).filter(CompanyFact.company_id == company.id).all()
    assert len(facts) >= 3

    # Check verified fact
    v_facts = [f for f in facts if f.classification == "VERIFIED_FACT"]
    assert len(v_facts) == 1
    assert "SignalLens" in v_facts[0].statement
    assert v_facts[0].research_page_id == page.id
    assert v_facts[0].evidence_snippet == "Our flagship product SignalLens extracts executive competitive insights."

    # Check that hallucinated $50M funding fact was classified as unsupported / assumption
    downgraded = [f for f in facts if "Series B" in f.statement and f.classification in ("ASSUMPTION", "REJECTED_UNSUPPORTED")]
    assert len(downgraded) == 1

    # Check unknown information
    unknowns = [f for f in facts if f.classification == "UNKNOWN"]
    assert len(unknowns) == 1
    assert "headcount" in unknowns[0].statement


@pytest.mark.asyncio
async def test_invalid_json_handling(db_session: Session):
    company = Company(name="Bad JSON Co", website="https://bad-json.com", normalized_domain="bad-json.com")
    db_session.add(company)
    db_session.flush()

    run = ResearchRun(company_id=company.id, status="RUNNING")
    db_session.add(run)
    db_session.flush()

    page = ResearchPage(
        company_id=company.id,
        research_run_id=run.id,
        url="https://bad-json.com/home",
        extracted_text="Some text",
    )
    db_session.add(page)
    db_session.flush()

    # Provider returns non-JSON text
    provider = MockAIProvider(response_text="I am an AI and I cannot generate JSON right now.")
    analyzer = CompanyIntelligenceAnalyzer(provider)

    profile = await analyzer.analyze_and_persist(company, run, [page], db_session)
    assert profile is None
    assert run.ai_analysis_status == "FAILED"
    assert "invalid json" in run.error_message.lower()
