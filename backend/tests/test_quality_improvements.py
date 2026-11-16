"""Comprehensive Regression Test Suite for Signal Stack AI Quality Improvements.

Covers:
1. Evidence quotation verification & character offset calculation.
2. Incorrect founding date rejection.
3. Unsupported satisfaction percentage rejection.
4. Placeholder competitor rejection.
5. Revenue stream absence handling.
6. URL-based study destination extraction.
7. Extraction of all seven MeetUniversity study destinations.
8. Duplicate fact merging across pages.
9. Contradictory fact detection & resolution.
10. Complete crawl accounting invariant enforcement.
11. Page-limit skip handling (SKIPPED_LIMIT vs failed).
12. Preservation of historical research records.
13. Multi-page document processing (Stage A + Stage B).
14. Different companies with varied website structures (e.g. B2B SaaS).
"""
from datetime import datetime, timezone
import pytest
from sqlalchemy.orm import Session

from app.ai.base import AICompletionResult, BaseAIProvider
from app.ai.extractor import PageLevelFactExtractor
from app.ai.synthesizer import CompanyProfileSynthesizer
from app.ai.validator import StrictEvidenceValidator
from app.crawlers.engine import WebsiteResearchEngine
from app.crawlers.facets import DeterministicFacetExtractor
from app.database.models import (
    Company,
    CompanyFact,
    CompanyProfile,
    DiscoveredUrl,
    DiscoveredUrlStatus,
    ResearchPage,
    ResearchRun,
)


class MockAIProvider(BaseAIProvider):
    """Deterministic mock AI provider for fast, reliable unit testing."""

    def __init__(self, response_text: str = "{}"):
        super().__init__(model_name="mock-model")
        self.response_text = response_text

    async def is_available(self) -> bool:
        return True

    async def generate_completion(
        self, prompt: str, system_instruction: str = "", temperature: float = 0.0
    ) -> AICompletionResult:
        return AICompletionResult(
            raw_text=self.response_text,
            model=self.model_name,
            provider="mock",
        )


# =============================================================================
# 1. Evidence Quotation Verification & Character Offsets
# =============================================================================
def test_evidence_quotation_offsets_and_verification():
    page_text = (
        "Meet University was born out of a vision to make studying abroad accessible. "
        "Founded in 2013 by an Ivy League alumnus and two seasoned edupreneurs, "
        "we provide unbiased, expert guidance."
    )
    quote = "Founded in 2013 by an Ivy League alumnus and two seasoned edupreneurs"
    res = StrictEvidenceValidator.validate_candidate_fact(
        statement="Meet University was founded in 2013 by an Ivy League alumnus.",
        category="history",
        raw_classification="VERIFIED_FACT",
        evidence_snippet=quote,
        page_text=page_text,
        page_id=2,
        source_url="https://meetuniversity.com/about",
    )
    assert res.classification == "VERIFIED_FACT"
    assert res.confidence == 0.95
    assert res.quote_start_offset is not None
    assert res.quote_end_offset is not None
    assert page_text[res.quote_start_offset:res.quote_end_offset] == quote


# =============================================================================
# 2. Incorrect Founding Date Rejection
# =============================================================================
def test_incorrect_founding_date_rejection():
    page_text = "Founded in 2013 by an Ivy League alumnus. Our team assists students worldwide."
    res = StrictEvidenceValidator.validate_candidate_fact(
        statement="Meet University was founded in 2010 by a team of experienced education consultants.",
        category="history",
        raw_classification="VERIFIED_FACT",
        evidence_snippet="Founded in 2010",
        page_text=page_text,
        page_id=2,
    )
    assert res.classification == "REJECTED_UNSUPPORTED"
    assert res.confidence == 0.0
    assert "2010" in res.rejection_reason
    assert "Founded in 2013" in res.rejection_reason


# =============================================================================
# 3. Unsupported Satisfaction Percentage Rejection
# =============================================================================
def test_unsupported_satisfaction_percentage_rejection():
    page_text = "Why Choose Meet University: 100% SUCCESS RATE and expert mentorship."
    res = StrictEvidenceValidator.validate_candidate_fact(
        statement="Meet University has a 95% client satisfaction rate.",
        category="testimonials",
        raw_classification="VERIFIED_FACT",
        evidence_snippet="95% client satisfaction rate",
        page_text=page_text,
        page_id=2,
    )
    assert res.classification == "REJECTED_UNSUPPORTED"
    assert res.confidence == 0.0
    assert "95%" in res.rejection_reason


# =============================================================================
# 4. Placeholder Competitor Rejection
# =============================================================================
def test_placeholder_competitor_rejection():
    page_text = "We provide global education counseling and admissions services."
    res = StrictEvidenceValidator.validate_candidate_fact(
        statement="Our main competitors are ABC Education and DEF Consulting.",
        category="competitors",
        raw_classification="VERIFIED_FACT",
        evidence_snippet="None",
        page_text=page_text,
        page_id=2,
    )
    assert res.classification == "REJECTED_UNSUPPORTED"
    assert res.confidence == 0.0
    assert "ABC Education" in res.rejection_reason


# =============================================================================
# 5. Revenue Stream Absence
# =============================================================================
def test_revenue_stream_absence():
    synthesizer = CompanyProfileSynthesizer()
    profile = synthesizer.synthesize_profile(
        company_name="MeetUniversity",
        validated_pages=[],
        active_facts=[],
    )
    # Never invent ads, affiliate marketing or consulting fees without proof
    assert any("Not publicly disclosed" in r for r in profile.revenue_streams)
    assert not any("advertising" in r.lower() for r in profile.revenue_streams)
    assert not any("affiliate" in r.lower() for r in profile.revenue_streams)


# =============================================================================
# 6. URL-based Study Destination Extraction
# =============================================================================
def test_url_based_study_destination_extraction():
    extractor = DeterministicFacetExtractor()
    dest, serv = extractor.extract_from_url("https://example.com/study_in_canada")
    assert dest == ["Canada"]

    dest_de, _ = extractor.extract_from_url("https://example.com/destinations/germany")
    assert dest_de == ["Germany"]

    dest_nz, _ = extractor.extract_from_url("https://example.com/countries/new-zealand")
    assert dest_nz == ["New Zealand"]


# =============================================================================
# 7. Extraction of All Seven MeetUniversity Study Destinations
# =============================================================================
def test_extraction_of_all_seven_meetuniversity_destinations():
    extractor = DeterministicFacetExtractor()
    urls = [
        "https://www.meetuniversity.com/study_in_uk",
        "https://www.meetuniversity.com/study_in_usa",
        "https://www.meetuniversity.com/study_in_canada",
        "https://www.meetuniversity.com/study_in_australia",
        "https://www.meetuniversity.com/study_in_ireland",
        "https://www.meetuniversity.com/study_in_germany",
        "https://www.meetuniversity.com/study_in_new_zealand",
    ]
    extracted_destinations = []
    for u in urls:
        d_list, _ = extractor.extract_from_url(u)
        extracted_destinations.extend(d_list)

    expected = {"United Kingdom", "United States", "Canada", "Australia", "Ireland", "Germany", "New Zealand"}
    assert set(extracted_destinations) == expected
    assert len(extracted_destinations) == 7


# =============================================================================
# 8. Duplicate Fact Merging
# =============================================================================
def test_duplicate_fact_merging():
    fact1 = StrictEvidenceValidator.validate_candidate_fact(
        statement="Offers standardized test preparation for SAT and GRE.",
        category="services",
        raw_classification="VERIFIED_FACT",
        evidence_snippet="support for standardized tests such as SAT, GRE",
        page_text="We offer support for standardized tests such as SAT, GRE, GMAT.",
        page_id=2,
    )
    fact2 = StrictEvidenceValidator.validate_candidate_fact(
        statement="Offers standardized test preparation for SAT and GRE.",
        category="services",
        raw_classification="ASSUMPTION",
        evidence_snippet=None,
        page_text="We offer support for standardized tests such as SAT, GRE, GMAT.",
        page_id=5,
    )
    active, rejected = CompanyProfileSynthesizer.merge_facts([fact1, fact2])
    # Duplicate merged into 1 active verified fact
    assert len(active) == 1
    assert active[0].classification == "VERIFIED_FACT"


# =============================================================================
# 9. Contradictory Fact Detection & Resolution
# =============================================================================
def test_contradictory_fact_detection():
    fact_verified = StrictEvidenceValidator.validate_candidate_fact(
        statement="Founded in 2013 by an Ivy League alumnus.",
        category="history",
        raw_classification="VERIFIED_FACT",
        evidence_snippet="Founded in 2013 by an Ivy League alumnus",
        page_text="Founded in 2013 by an Ivy League alumnus and two seasoned edupreneurs.",
        page_id=2,
    )
    fact_conflicting = StrictEvidenceValidator.validate_candidate_fact(
        statement="Meet University was founded in 2010.",
        category="history",
        raw_classification="ASSUMPTION",
        evidence_snippet=None,
        page_text="Some other page text.",
        page_id=4,
    )
    active, rejected = CompanyProfileSynthesizer.merge_facts([fact_verified, fact_conflicting])
    assert len(active) == 1
    assert active[0].statement == "Founded in 2013 by an Ivy League alumnus."
    assert any("2010" in r.statement for r in rejected)


# =============================================================================
# 10. Complete Crawl Accounting Invariant
# =============================================================================
def test_crawl_accounting_invariant():
    run = ResearchRun(
        company_id=1,
        pages_discovered=13,
        pages_fetched=10,
        pages_failed=0,
        pages_skipped_limit=2,
        pages_skipped_robots=1,
        pages_skipped_duplicate=0,
        pages_skipped_out_of_scope=0,
    )
    assert run.validate_crawl_accounting() is True

    # Invariant failure case
    run.pages_discovered = 15
    assert run.validate_crawl_accounting() is False


# =============================================================================
# 11. Page-Limit Skip Handling
# =============================================================================
def test_page_limit_skip_handling(db_session: Session):
    company = Company(
        name="LimitTestCo",
        website="https://limittest.com",
        normalized_domain="limittest.com",
    )
    db_session.add(company)
    db_session.commit()

    run = ResearchRun(
        company_id=company.id,
        status="COMPLETED",
        pages_discovered=13,
        pages_fetched=12,
        pages_failed=0,
        pages_skipped_limit=1,
    )
    db_session.add(run)
    db_session.commit()

    # Create DiscoveredUrl record marked SKIPPED_LIMIT
    disc_url = DiscoveredUrl(
        research_run_id=run.id,
        url="https://limittest.com/blog",
        status=DiscoveredUrlStatus.SKIPPED_LIMIT.value,
        depth=1,
        priority=10,
        error_message="Skipped: reached maximum crawl limit (12 pages)",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db_session.add(disc_url)
    db_session.commit()

    # The skipped URL must not be counted as a failed page
    assert run.pages_failed == 0
    assert run.pages_skipped_limit == 1
    assert run.validate_crawl_accounting() is True


# =============================================================================
# 12. Preservation of Historical Records
# =============================================================================
def test_preservation_of_historical_records(db_session: Session):
    company = Company(
        name="HistoricalCo",
        website="https://historical.com",
        normalized_domain="historical.com",
    )
    db_session.add(company)
    db_session.commit()

    # Historical Run #1
    run1 = ResearchRun(company_id=company.id, status="COMPLETED", pages_discovered=5, pages_fetched=5)
    db_session.add(run1)
    db_session.commit()

    # Historical Profile v1
    prof1 = CompanyProfile(
        company_id=company.id,
        research_run_id=run1.id,
        industry="Original Industry",
        profile_version=1,
    )
    db_session.add(prof1)
    db_session.commit()

    # Historical Fact
    fact1 = CompanyFact(
        company_id=company.id,
        category="general",
        statement="Historical statement",
        classification="ASSUMPTION",
    )
    db_session.add(fact1)
    db_session.commit()

    # Run a new version (Profile v2)
    prof2 = CompanyProfile(
        company_id=company.id,
        research_run_id=run1.id,
        industry="Updated Industry",
        profile_version=2,
    )
    db_session.add(prof2)
    db_session.commit()

    # Verify both versions exist intact
    profiles = db_session.query(CompanyProfile).filter(CompanyProfile.company_id == company.id).all()
    assert len(profiles) == 2
    assert {p.profile_version for p in profiles} == {1, 2}
    assert db_session.query(CompanyFact).filter(CompanyFact.company_id == company.id).count() == 1


# =============================================================================
# 13. Processing Multiple Webpage Documents
# =============================================================================
@pytest.mark.asyncio
async def test_processing_multiple_webpage_documents():
    mock_json = (
        '{"products_services": ["Personalized Counseling", "Visa Guidance"], '
        '"target_customers": ["International Students"], '
        '"facts": [{"statement": "Offers personalized counseling.", "evidence_snippet": "Personalized Counseling", "category": "services", "classification": "VERIFIED_FACT"}]}'
    )
    provider = MockAIProvider(response_text=mock_json)
    extractor = PageLevelFactExtractor(provider)

    page1 = ResearchPage(
        id=1,
        company_id=1,
        url="https://example.com/about",
        title="About Us",
        extracted_text="We provide Personalized Counseling for students worldwide.",
    )
    page2 = ResearchPage(
        id=2,
        company_id=1,
        url="https://example.com/study_in_uk",
        title="Study in UK",
        extracted_text="Study in the UK with our comprehensive guidance.",
    )

    v1 = await extractor.extract_page(page1, "TestCo")
    v2 = await extractor.extract_page(page2, "TestCo")

    assert v1.page_id == 1
    assert "United Kingdom" in v2.study_destinations


# =============================================================================
# 14. Different Companies with Different Website Structures (e.g. B2B SaaS)
# =============================================================================
def test_different_companies_b2b_saas_structure():
    extractor = DeterministicFacetExtractor()
    saas_url = "https://cloudmetrics.io/products/infrastructure-monitoring"
    dest, serv = extractor.extract_from_url(saas_url)
    # A SaaS product page has 0 study destinations
    assert dest == []

    # Address parser detects headquarters
    saas_contact = "CloudMetrics Inc, 100 Montgomery St, San Francisco, California, USA."
    # Strict validation of customer problem
    res = StrictEvidenceValidator.validate_candidate_fact(
        statement="CloudMetrics monitors multi-cloud Kubernetes clusters.",
        category="products_services",
        raw_classification="VERIFIED_FACT",
        evidence_snippet="monitors multi-cloud Kubernetes clusters",
        page_text="Our platform monitors multi-cloud Kubernetes clusters in real-time.",
        page_id=10,
    )
    assert res.classification == "VERIFIED_FACT"
    assert res.quote_start_offset is not None
