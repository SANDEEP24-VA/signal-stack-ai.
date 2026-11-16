"""Comprehensive Regression Test Suite for Task 4: Competitor Discovery & Source Intelligence.

Covers:
 1. Dynamic competitor discovery for a target company.
 2. Industry differentiation: EdTech vs Robotics produces distinct competitor sets.
 3. Candidate provenance and evidence tracking.
 4. Duplicate competitor prevention for identical canonical domains.
 5. Competitor governance lifecycle: approve, reject, archive, edit.
 6. Manual competitor registration with validation.
 7. Multi-category source discovery (CUSTOMERS, COMPETITORS, MARKET, INTERNAL).
 8. Industry-specific source discovery differentiation.
 9. Duplicate source URL prevention.
10. Source governance lifecycle: approve, reject, pause, resume, edit, delete.
11. Manual source creation with category assignment.
12. Category-based source filtering.
13. Strict company-level isolation (preventing cross-company leakage).
14. SSRF & private IP range blocking on candidate domains.
15. Malformed and invalid URL rejection.
16. Source health probe logging and content hashing.
17. Resilient fallback behavior when AI provider is offline.
18. Preservation of immutable facts and founder context.
19. Summary KPI statistics calculation.
20. REST API End-to-End workflow via FastAPI TestClient.
"""
from datetime import datetime, timezone
import json
import pytest
from sqlalchemy.orm import Session
from starlette.testclient import TestClient

from app.ai.base import AICompletionResult, BaseAIProvider
from app.crawlers.url_utils import normalize_domain, normalize_url, validate_ip_security, validate_url_syntax
from app.database.models import (
    Company,
    CompanyFact,
    CompanyProfile,
    Competitor,
    CompetitorRelationshipType,
    CompetitorReviewStatus,
    FounderBusinessContext,
    InformationProvenanceType,
    IntelligenceSource,
    IntelligenceSourceCategory,
    IntelligenceSourceStatus,
    IntelligenceSourceType,
    ResearchPage,
    SourceCrawlLog,
)
from app.discovery import (
    CompetitorDiscoveryEngine,
    CompetitorGovernanceManager,
    SourceDiscoveryEngine,
    SourceGovernanceManager,
)
from app.schemas import CompetitorCreate, IntelligenceSourceCreate


class MockDiscoveryAIProvider(BaseAIProvider):
    """Deterministic mock provider for unit testing competitor & source discovery."""

    def __init__(self):
        super().__init__(model_name="mock-llama")

    async def is_available(self) -> bool:
        return True

    async def generate_completion(
        self, prompt: str, system_instruction: str = "", temperature: float = 0.0
    ) -> AICompletionResult:
        prompt_lower = prompt.lower()

        # Competitor Discovery Mode
        if "discover genuine competitors" in prompt_lower:
            if "meetuniversity" in prompt_lower or "edtech" in prompt_lower:
                return AICompletionResult(
                    raw_text=json.dumps({
                        "candidates": [
                            {
                                "name": "IDP Education",
                                "website": "https://www.idp.com",
                                "industry": "International Student Placement",
                                "relationship_type": "DIRECT",
                                "products_services": ["Study Abroad Counseling", "IELTS"],
                                "target_customers": ["International Students"],
                                "geographic_markets": ["India", "United States", "United Kingdom"],
                                "discovery_rationale": "Direct global competitor in international student placement counseling.",
                                "evidence_snippet": "Global student placement leader.",
                                "confidence": 0.95,
                            },
                            {
                                "name": "Leap Scholar",
                                "website": "https://leapscholar.com",
                                "industry": "Study Abroad EdTech",
                                "relationship_type": "DIRECT",
                                "products_services": ["End-to-End Advisory", "Test Prep"],
                                "target_customers": ["Indian Students"],
                                "geographic_markets": ["India", "Global"],
                                "discovery_rationale": "Direct digital counseling rival in South Asian student recruitment.",
                                "evidence_snippet": "Study abroad platform for Indian students.",
                                "confidence": 0.90,
                            },
                            {
                                "name": "Common Application",
                                "website": "https://www.commonapp.org",
                                "industry": "Direct University Admissions",
                                "relationship_type": "SUBSTITUTE",
                                "products_services": ["Direct College Admissions"],
                                "target_customers": ["High School Seniors"],
                                "geographic_markets": ["United States", "Global"],
                                "discovery_rationale": "Substitute service where students bypass counselors to apply directly.",
                                "evidence_snippet": "Direct university portal.",
                                "confidence": 0.85,
                            },
                        ]
                    }),
                    model=self.model_name,
                    provider="mock",
                )
            elif "nexus robotics" in prompt_lower or "robot" in prompt_lower:
                return AICompletionResult(
                    raw_text=json.dumps({
                        "candidates": [
                            {
                                "name": "Carbon Robotics",
                                "website": "https://carbonrobotics.com",
                                "industry": "Autonomous Agricultural Robotics",
                                "relationship_type": "DIRECT",
                                "products_services": ["LaserWeeder"],
                                "target_customers": ["Commercial Specialty Crop Farmers"],
                                "geographic_markets": ["North America"],
                                "discovery_rationale": "Direct competitor deploying automated computer-vision weeding implements.",
                                "evidence_snippet": "Laser-guided weed eradication machines.",
                                "confidence": 0.92,
                            },
                            {
                                "name": "FarmWise",
                                "website": "https://farmwise.io",
                                "industry": "AI Agricultural Implements",
                                "relationship_type": "DIRECT",
                                "products_services": ["Titan Autonomous Weeder"],
                                "target_customers": ["Vegetable Growers"],
                                "geographic_markets": ["United States"],
                                "discovery_rationale": "Direct competitor in precision automated weeding.",
                                "evidence_snippet": "Smart farming automated implements.",
                                "confidence": 0.88,
                            },
                        ]
                    }),
                    model=self.model_name,
                    provider="mock",
                )

        # Source Discovery Mode
        if "intelligence sources" in prompt_lower:
            if "meetuniversity" in prompt_lower or "edtech" in prompt_lower:
                return AICompletionResult(
                    raw_text=json.dumps({
                        "sources": [
                            {
                                "name": "UK Visas & Immigration Student Guidance",
                                "canonical_url": "https://www.gov.uk/student-visa",
                                "source_type": "REGULATORY",
                                "category": "MARKET",
                                "why_it_matters": "Official policy changes on student visas and work rights.",
                                "intelligence_type": "UK student immigration regulations",
                                "credibility_score": 0.98,
                            },
                            {
                                "name": "US SEVP International Student Data",
                                "canonical_url": "https://www.ice.gov/sevis",
                                "source_type": "REGULATORY",
                                "category": "MARKET",
                                "why_it_matters": "US student visa intake statistics and OPT compliance.",
                                "intelligence_type": "US international student statistics",
                                "credibility_score": 0.98,
                            },
                            {
                                "name": "ICEF Monitor",
                                "canonical_url": "https://monitor.icef.com",
                                "source_type": "INDUSTRY_PORTAL",
                                "category": "MARKET",
                                "why_it_matters": "Global international student mobility analytics.",
                                "intelligence_type": "Student mobility trends",
                                "credibility_score": 0.90,
                            },
                        ]
                    }),
                    model=self.model_name,
                    provider="mock",
                )
            else:
                return AICompletionResult(
                    raw_text=json.dumps({
                        "sources": [
                            {
                                "name": "USDA National Agricultural Statistics Service",
                                "canonical_url": "https://www.nass.usda.gov",
                                "source_type": "REGULATORY",
                                "category": "MARKET",
                                "why_it_matters": "Official farm labor costs and crop acreage data.",
                                "intelligence_type": "Agricultural economic statistics",
                                "credibility_score": 0.98,
                            }
                        ]
                    }),
                    model=self.model_name,
                    provider="mock",
                )

        return AICompletionResult(raw_text="{}", model=self.model_name, provider="mock")


@pytest.fixture
def sample_company(db_session: Session) -> Company:
    company = Company(
        name="MeetUniversity",
        website="https://meetuniversity.com",
        normalized_domain="meetuniversity.com",
        industry="EdTech / Higher Education",
        status="ACTIVE",
    )
    db_session.add(company)
    db_session.flush()

    profile = CompanyProfile(
        company_id=company.id,
        industry="Higher Education & International Student Placement",
        business_model="Counseling Platform",
        products_services=["Personalized Counseling", "Visa Advisory"],
        target_customers=["Prospective Indian Students"],
        customer_problems=["Opaque admission processes"],
        revenue_streams=["Institutional commission"],
        geographical_markets=["India"],
        study_destinations=["United States", "United Kingdom", "Canada"],
        positioning="Empowering study abroad aspirants",
        profile_version=1,
    )
    db_session.add(profile)

    fact = CompanyFact(
        company_id=company.id,
        category="services",
        statement="Offers study abroad counseling for global universities.",
        classification="VERIFIED_FACT",
        evidence_snippet="study abroad counseling for global universities",
        provenance_type=InformationProvenanceType.PUBLIC_VERIFIED_FACT.value,
    )
    db_session.add(fact)

    founder_ctx = FounderBusinessContext(
        company_id=company.id,
        interview_session_id=1,
        context_category="competitors",
        field_name="named_rivals",
        confirmed_value=["IDP Education", "Leap Scholar"],
    )
    db_session.add(founder_ctx)

    db_session.commit()
    return company


@pytest.fixture
def robotics_company(db_session: Session) -> Company:
    company = Company(
        name="Nexus Robotics",
        website="https://nexusrobotics.ai",
        normalized_domain="nexusrobotics.ai",
        industry="Autonomous Agricultural Robotics",
        status="ACTIVE",
    )
    db_session.add(company)
    db_session.flush()

    profile = CompanyProfile(
        company_id=company.id,
        industry="Agricultural Robotics",
        business_model="Robotics-as-a-Service",
        products_services=["Autonomous Weeding Robot"],
        target_customers=["Commercial Specialty Crop Growers"],
        customer_problems=["Labor shortages"],
        revenue_streams=["Hardware leases"],
        geographical_markets=["North America"],
        study_destinations=[],
        positioning="Autonomous precision weeding",
        profile_version=1,
    )
    db_session.add(profile)
    db_session.commit()
    return company


# =============================================================================
# 1. Dynamic Competitor Discovery
# =============================================================================
@pytest.mark.asyncio
async def test_dynamic_competitor_discovery(db_session: Session, sample_company: Company):
    provider = MockDiscoveryAIProvider()
    engine = CompetitorDiscoveryEngine(db=db_session, provider=provider)

    competitors = await engine.discover_competitors(company_id=sample_company.id, verify_domains=False)
    assert len(competitors) >= 3
    names = [c.name for c in competitors]
    assert "IDP Education" in names
    assert "Leap Scholar" in names

    # Status must default to CANDIDATE
    for c in competitors:
        assert c.review_status == CompetitorReviewStatus.CANDIDATE.value
        assert c.company_id == sample_company.id
        assert len(c.canonical_domain) > 3


# =============================================================================
# 2. Industry Differentiation: EdTech vs Robotics
# =============================================================================
@pytest.mark.asyncio
async def test_industry_differentiation_edtech_vs_robotics(
    db_session: Session, sample_company: Company, robotics_company: Company
):
    provider = MockDiscoveryAIProvider()
    engine = CompetitorDiscoveryEngine(db=db_session, provider=provider)

    edtech_competitors = await engine.discover_competitors(company_id=sample_company.id, verify_domains=False)
    robotics_competitors = await engine.discover_competitors(company_id=robotics_company.id, verify_domains=False)

    edtech_domains = {c.canonical_domain for c in edtech_competitors}
    robotics_domains = {c.canonical_domain for c in robotics_competitors}

    # Domains must be completely disjoint
    assert edtech_domains.isdisjoint(robotics_domains)
    assert "carbonrobotics.com" in robotics_domains or "farmwise.io" in robotics_domains
    assert "idp.com" in edtech_domains or "leapscholar.com" in edtech_domains


# =============================================================================
# 3. Candidate Provenance and Evidence Tracking
# =============================================================================
@pytest.mark.asyncio
async def test_competitor_provenance_and_evidence(db_session: Session, sample_company: Company):
    provider = MockDiscoveryAIProvider()
    engine = CompetitorDiscoveryEngine(db=db_session, provider=provider)

    competitors = await engine.discover_competitors(company_id=sample_company.id, verify_domains=False)
    idp = next(c for c in competitors if c.canonical_domain == "idp.com")

    assert idp.discovery_method == "AI_PROFILE_EXTRACTION"
    assert idp.relationship_type == CompetitorRelationshipType.DIRECT.value
    assert len(idp.discovery_rationale) > 10
    assert len(idp.supporting_evidence) > 0


# =============================================================================
# 4. Duplicate Competitor Prevention
# =============================================================================
@pytest.mark.asyncio
async def test_duplicate_competitor_prevention(db_session: Session, sample_company: Company):
    provider = MockDiscoveryAIProvider()
    engine = CompetitorDiscoveryEngine(db=db_session, provider=provider)

    # First run
    run1 = await engine.discover_competitors(company_id=sample_company.id, verify_domains=False)
    initial_count = db_session.query(Competitor).filter(Competitor.company_id == sample_company.id).count()

    # Second run
    run2 = await engine.discover_competitors(company_id=sample_company.id, verify_domains=False)
    second_count = db_session.query(Competitor).filter(Competitor.company_id == sample_company.id).count()

    assert initial_count == second_count


# =============================================================================
# 5. Competitor Governance Lifecycle: Approve, Reject, Archive, Edit
# =============================================================================
def test_competitor_governance_lifecycle(db_session: Session, sample_company: Company):
    comp = Competitor(
        company_id=sample_company.id,
        name="Candidate Rival",
        canonical_domain="candidaterival.com",
        website="https://candidaterival.com",
        relationship_type="DIRECT",
        discovery_rationale="Operates in student admissions.",
        confidence=0.80,
        review_status=CompetitorReviewStatus.CANDIDATE.value,
    )
    db_session.add(comp)
    db_session.commit()

    manager = CompetitorGovernanceManager(db=db_session)

    # Approve
    approved = manager.approve_competitor(comp.id)
    assert approved.review_status == CompetitorReviewStatus.APPROVED.value

    # Reject
    rejected = manager.reject_competitor(comp.id)
    assert rejected.review_status == CompetitorReviewStatus.REJECTED.value

    # Edit
    edited = manager.edit_competitor(
        comp.id,
        name="Updated Rival Name",
        relationship_type="INDIRECT",
        discovery_rationale="Refined rationale based on market data.",
    )
    assert edited.name == "Updated Rival Name"
    assert edited.relationship_type == "INDIRECT"

    # Archive
    archived = manager.archive_competitor(comp.id)
    assert archived.review_status == CompetitorReviewStatus.ARCHIVED.value


# =============================================================================
# 6. Manual Competitor Registration
# =============================================================================
@pytest.mark.asyncio
async def test_manual_competitor_registration(db_session: Session, sample_company: Company):
    provider = MockDiscoveryAIProvider()
    engine = CompetitorDiscoveryEngine(db=db_session, provider=provider)

    comp = await engine.manual_add_competitor(
        company_id=sample_company.id,
        name="Studyportals",
        website="https://www.studyportals.com",
        relationship_type="INDIRECT",
        discovery_rationale="Global university study choice platform.",
    )
    assert comp.id is not None
    assert comp.canonical_domain == "studyportals.com"
    assert comp.review_status == CompetitorReviewStatus.APPROVED.value
    assert comp.discovery_method == "MANUAL_ENTRY"


# =============================================================================
# 7. Multi-Category Source Discovery (CUSTOMERS, COMPETITORS, MARKET, INTERNAL)
# =============================================================================
@pytest.mark.asyncio
async def test_multi_category_source_discovery(db_session: Session, sample_company: Company):
    provider = MockDiscoveryAIProvider()
    source_engine = SourceDiscoveryEngine(db=db_session, provider=provider)

    sources = await source_engine.discover_sources_for_company(company_id=sample_company.id, probe_reachability=False)
    assert len(sources) >= 5

    categories = {s.category for s in sources}
    assert IntelligenceSourceCategory.CUSTOMERS.value in categories
    assert IntelligenceSourceCategory.MARKET.value in categories
    assert IntelligenceSourceCategory.INTERNAL.value in categories

    for s in sources:
        assert s.status == IntelligenceSourceStatus.PENDING_APPROVAL.value
        assert s.credibility_score > 0.50
        assert len(s.why_it_matters) > 5


# =============================================================================
# 8. Industry-Specific Source Discovery Differentiation
# =============================================================================
@pytest.mark.asyncio
async def test_industry_source_differentiation(
    db_session: Session, sample_company: Company, robotics_company: Company
):
    provider = MockDiscoveryAIProvider()
    source_engine = SourceDiscoveryEngine(db=db_session, provider=provider)

    edtech_sources = await source_engine.discover_sources_for_company(sample_company.id, probe_reachability=False)
    robotics_sources = await source_engine.discover_sources_for_company(robotics_company.id, probe_reachability=False)

    edtech_urls = {s.canonical_url for s in edtech_sources}
    robotics_urls = {s.canonical_url for s in robotics_sources}

    # No cross-contamination of company sources
    assert edtech_urls.isdisjoint(robotics_urls)


# =============================================================================
# 9. Duplicate Source URL Prevention
# =============================================================================
@pytest.mark.asyncio
async def test_duplicate_source_url_prevention(db_session: Session, sample_company: Company):
    provider = MockDiscoveryAIProvider()
    source_engine = SourceDiscoveryEngine(db=db_session, provider=provider)

    await source_engine.discover_sources_for_company(sample_company.id, probe_reachability=False)
    count1 = db_session.query(IntelligenceSource).filter(IntelligenceSource.company_id == sample_company.id).count()

    await source_engine.discover_sources_for_company(sample_company.id, probe_reachability=False)
    count2 = db_session.query(IntelligenceSource).filter(IntelligenceSource.company_id == sample_company.id).count()

    assert count1 == count2


# =============================================================================
# 10. Source Governance Lifecycle: Approve, Reject, Pause, Resume, Delete
# =============================================================================
def test_source_governance_lifecycle(db_session: Session, sample_company: Company):
    source = IntelligenceSource(
        company_id=sample_company.id,
        name="ICEF Monitor",
        canonical_url="https://monitor.icef.com",
        domain="icef.com",
        category="MARKET",
        why_it_matters="Monitors global recruitment shifts.",
        intelligence_type="Student mobility trends",
        status=IntelligenceSourceStatus.PENDING_APPROVAL.value,
    )
    db_session.add(source)
    db_session.commit()

    manager = SourceGovernanceManager(db=db_session)

    # Approve
    approved = manager.approve_source(source.id)
    assert approved.status == IntelligenceSourceStatus.APPROVED.value

    # Pause
    paused = manager.pause_source(source.id)
    assert paused.status == IntelligenceSourceStatus.PAUSED.value

    # Resume
    resumed = manager.resume_source(source.id)
    assert resumed.status == IntelligenceSourceStatus.APPROVED.value

    # Edit
    edited = manager.edit_source(
        source.id,
        name="ICEF Monitor Premium Feed",
        category="MARKET",
        crawl_frequency_minutes=720,
    )
    assert edited.name == "ICEF Monitor Premium Feed"
    assert edited.crawl_frequency_minutes == 720

    # Reject
    rejected = manager.reject_source(source.id, reason="Paywalled endpoint")
    assert rejected.status == IntelligenceSourceStatus.REJECTED.value
    assert "Paywalled" in rejected.last_error

    # Delete
    deleted = manager.delete_source(source.id)
    assert deleted is True
    assert db_session.get(IntelligenceSource, source.id) is None


# =============================================================================
# 11. Manual Source Creation
# =============================================================================
@pytest.mark.asyncio
async def test_manual_source_creation(db_session: Session, sample_company: Company):
    provider = MockDiscoveryAIProvider()
    source_engine = SourceDiscoveryEngine(db=db_session, provider=provider)

    source = await source_engine.manual_add_source(
        company_id=sample_company.id,
        name="Ministry of Education India",
        url="https://www.education.gov.in",
        category="MARKET",
        why_it_matters="Regulatory policies and higher education statistics.",
        intelligence_type="Policy announcements",
        credibility_score=0.98,
    )
    assert source.id is not None
    assert source.domain == "education.gov.in"
    assert source.status == IntelligenceSourceStatus.APPROVED.value


# =============================================================================
# 12. Category-Based Source Filtering
# =============================================================================
def test_category_based_source_filtering(db_session: Session, sample_company: Company):
    s1 = IntelligenceSource(
        company_id=sample_company.id,
        name="Review Hub",
        canonical_url="https://reviews.com",
        domain="reviews.com",
        category=IntelligenceSourceCategory.CUSTOMERS.value,
        why_it_matters="Student reviews.",
        intelligence_type="Satisfaction",
    )
    s2 = IntelligenceSource(
        company_id=sample_company.id,
        name="Visa Portal",
        canonical_url="https://visas.gov",
        domain="visas.gov",
        category=IntelligenceSourceCategory.MARKET.value,
        why_it_matters="Visa regulations.",
        intelligence_type="Immigration rules",
    )
    db_session.add_all([s1, s2])
    db_session.commit()

    cust_sources = db_session.query(IntelligenceSource).filter(
        IntelligenceSource.company_id == sample_company.id,
        IntelligenceSource.category == IntelligenceSourceCategory.CUSTOMERS.value,
    ).all()
    assert len(cust_sources) == 1
    assert cust_sources[0].domain == "reviews.com"


# =============================================================================
# 13. Strict Company-Level Isolation
# =============================================================================
def test_strict_company_level_isolation(
    db_session: Session, sample_company: Company, robotics_company: Company
):
    s_edtech = IntelligenceSource(
        company_id=sample_company.id,
        name="EdTech Source",
        canonical_url="https://edtech.com/source",
        domain="edtech.com",
        category="MARKET",
        why_it_matters="Why it matters.",
        intelligence_type="Trends",
    )
    s_robot = IntelligenceSource(
        company_id=robotics_company.id,
        name="Robotics Source",
        canonical_url="https://robotics.com/source",
        domain="robotics.com",
        category="MARKET",
        why_it_matters="Why it matters.",
        intelligence_type="Autonomy",
    )
    db_session.add_all([s_edtech, s_robot])
    db_session.commit()

    edtech_list = db_session.query(IntelligenceSource).filter(
        IntelligenceSource.company_id == sample_company.id
    ).all()
    assert len(edtech_list) == 1
    assert edtech_list[0].name == "EdTech Source"


# =============================================================================
# 14. SSRF & Private IP Range Blocking
# =============================================================================
def test_ssrf_and_private_ip_blocking():
    is_safe, msg = validate_ip_security("localhost")
    assert is_safe is False

    is_safe127, _ = validate_ip_security("127.0.0.1")
    assert is_safe127 is False

    is_safe10, _ = validate_ip_security("10.0.0.5")
    assert is_safe10 is False

    is_safe192, _ = validate_ip_security("192.168.1.1")
    assert is_safe192 is False

    is_safe_public, _ = validate_ip_security("google.com")
    assert is_safe_public is True


# =============================================================================
# 15. Malformed and Invalid URL Rejection
# =============================================================================
def test_malformed_url_rejection():
    is_valid, msg = validate_url_syntax("ftp://invalid-protocol.com")
    assert is_valid is False
    assert "Unsupported protocol" in msg

    is_valid_cred, msg_cred = validate_url_syntax("https://admin:pass@example.com")
    assert is_valid_cred is False
    assert "Embedded credentials" in msg_cred

    is_valid_port, msg_port = validate_url_syntax("https://example.com:8080/test")
    assert is_valid_port is False
    assert "Port 8080 is not permitted" in msg_port


# =============================================================================
# 16. Source Health Probe Logging
# =============================================================================
@pytest.mark.asyncio
async def test_source_health_probe_logging(db_session: Session, sample_company: Company):
    source = IntelligenceSource(
        company_id=sample_company.id,
        name="Example Source",
        canonical_url="https://example.com",
        domain="example.com",
        category="MARKET",
        why_it_matters="General reference.",
        intelligence_type="Reference",
        status=IntelligenceSourceStatus.APPROVED.value,
    )
    db_session.add(source)
    db_session.commit()

    manager = SourceGovernanceManager(db=db_session)
    log = await manager.probe_source_health(source.id)
    assert log.id is not None
    assert log.source_id == source.id
    assert source.last_attempted_crawl is not None


# =============================================================================
# 17. Resilient Fallback When AI Provider is Offline
# =============================================================================
@pytest.mark.asyncio
async def test_offline_ai_resilient_fallback(db_session: Session, sample_company: Company):
    class OfflineAIProvider(BaseAIProvider):
        def __init__(self):
            super().__init__(model_name="offline-model")

        async def is_available(self) -> bool:
            return False

        async def generate_completion(self, *args, **kwargs) -> AICompletionResult:
            raise ConnectionError("Ollama daemon unreachable")

    offline_prov = OfflineAIProvider()
    comp_engine = CompetitorDiscoveryEngine(db=db_session, provider=offline_prov)
    source_engine = SourceDiscoveryEngine(db=db_session, provider=offline_prov)

    # Competitor discovery should fall back gracefully without crashing
    competitors = await comp_engine.discover_competitors(sample_company.id, verify_domains=False)
    assert len(competitors) > 0
    assert any(c.canonical_domain == "idp.com" for c in competitors)

    # Source discovery should fall back gracefully
    sources = await source_engine.discover_sources_for_company(sample_company.id, probe_reachability=False)
    assert len(sources) > 0


# =============================================================================
# 18. Preservation of Immutable Facts and Founder Context
# =============================================================================
@pytest.mark.asyncio
async def test_preservation_of_facts_and_founder_context(db_session: Session, sample_company: Company):
    facts_before = db_session.query(CompanyFact).filter(CompanyFact.company_id == sample_company.id).all()
    ctx_before = db_session.query(FounderBusinessContext).filter(FounderBusinessContext.company_id == sample_company.id).all()

    provider = MockDiscoveryAIProvider()
    comp_engine = CompetitorDiscoveryEngine(db=db_session, provider=provider)
    source_engine = SourceDiscoveryEngine(db=db_session, provider=provider)

    await comp_engine.discover_competitors(sample_company.id, verify_domains=False)
    await source_engine.discover_sources_for_company(sample_company.id, probe_reachability=False)

    facts_after = db_session.query(CompanyFact).filter(CompanyFact.company_id == sample_company.id).all()
    ctx_after = db_session.query(FounderBusinessContext).filter(FounderBusinessContext.company_id == sample_company.id).all()

    assert len(facts_before) == len(facts_after)
    assert len(ctx_before) == len(ctx_after)
    assert facts_after[0].provenance_type == InformationProvenanceType.PUBLIC_VERIFIED_FACT.value


# =============================================================================
# 19. Summary KPI Statistics Calculation
# =============================================================================
def test_summary_kpi_stats_calculation(db_session: Session, sample_company: Company):
    s1 = IntelligenceSource(
        company_id=sample_company.id,
        name="Source 1",
        canonical_url="https://s1.com",
        domain="s1.com",
        category="MARKET",
        why_it_matters="M1",
        intelligence_type="T1",
        status=IntelligenceSourceStatus.APPROVED.value,
    )
    s2 = IntelligenceSource(
        company_id=sample_company.id,
        name="Source 2",
        canonical_url="https://s2.com",
        domain="s2.com",
        category="CUSTOMERS",
        why_it_matters="M2",
        intelligence_type="T2",
        status=IntelligenceSourceStatus.PENDING_APPROVAL.value,
    )
    comp1 = Competitor(
        company_id=sample_company.id,
        name="Rival 1",
        canonical_domain="r1.com",
        website="https://r1.com",
        discovery_rationale="R1",
        review_status=CompetitorReviewStatus.APPROVED.value,
    )
    db_session.add_all([s1, s2, comp1])
    db_session.commit()

    from app.api.sources import get_source_summary_stats
    stats = get_source_summary_stats(sample_company.id, db=db_session)

    assert stats.total_sources == 2
    assert stats.approved == 1
    assert stats.pending == 1
    assert stats.competitors_count == 1
    assert stats.approved_competitors == 1
    assert stats.by_category["MARKET"] == 1
    assert stats.by_category["CUSTOMERS"] == 1


# =============================================================================
# 20. REST API End-to-End Workflow via TestClient
# =============================================================================
def test_competitor_and_sources_api_end_to_end(client: TestClient, sample_company: Company, db_session: Session):
    # 1. Manually add competitor
    comp_resp = client.post(
        f"/api/companies/{sample_company.id}/competitors",
        json={
            "name": "Kupfer Advisory",
            "website": "https://kupfer.com",
            "relationship_type": "DIRECT",
            "discovery_rationale": "Direct university counseling competitor.",
        },
    )
    assert comp_resp.status_code == 201
    comp_data = comp_resp.json()
    comp_id = comp_data["id"]
    assert comp_data["canonical_domain"] == "kupfer.com"

    # 2. Approve competitor
    appr_resp = client.post(f"/api/competitors/{comp_id}/approve")
    assert appr_resp.status_code == 200
    assert appr_resp.json()["review_status"] == "APPROVED"

    # 3. List competitors
    list_comp_resp = client.get(f"/api/companies/{sample_company.id}/competitors")
    assert list_comp_resp.status_code == 200
    assert len(list_comp_resp.json()) >= 1

    # 4. Manually add source
    src_resp = client.post(
        f"/api/companies/{sample_company.id}/sources",
        json={
            "name": "Ministry of Education Portal",
            "canonical_url": "https://www.education.gov.in/news",
            "category": "MARKET",
            "why_it_matters": "Monitors university admission announcements.",
            "intelligence_type": "Admission updates",
        },
    )
    assert src_resp.status_code == 201
    src_data = src_resp.json()
    src_id = src_data["id"]

    # 5. Pause and resume source
    pause_resp = client.post(f"/api/sources/{src_id}/pause")
    assert pause_resp.status_code == 200
    assert pause_resp.json()["status"] == "PAUSED"

    resume_resp = client.post(f"/api/sources/{src_id}/resume")
    assert resume_resp.status_code == 200
    assert resume_resp.json()["status"] == "APPROVED"

    # 6. Get source summary stats
    summary_resp = client.get(f"/api/companies/{sample_company.id}/sources/summary")
    assert summary_resp.status_code == 200
    assert summary_resp.json()["total_sources"] >= 1
    assert summary_resp.json()["approved"] >= 1
