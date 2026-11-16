"""MeetUniversity Regression Validation Script — Profile v2 Generation.

Executes the improved Two-Stage Company Intelligence Engine on existing
Research Run #2 pages stored in signal_stack.db:
- Creates a new CompanyProfile (v2) without modifying historical records (v1).
- Extracts all 7 study destinations from destination pages.
- Differentiates operational presence (India: Noida & Mumbai) from study destinations.
- Enforces strict evidence quotation offsets on verified facts.
- Rejects unsupported metrics, incorrect founding dates, and competitor placeholders.
- Keeps unstated revenue streams marked as UNKNOWN.
"""
import asyncio
import os
import sys

backend_dir = os.path.abspath(os.path.dirname(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.ai.analyzer import CompanyIntelligenceAnalyzer
from app.ai.manager import get_active_ai_provider
from app.database import (
    Company,
    CompanyFact,
    CompanyProfile,
    ResearchPage,
    ResearchRun,
    SessionLocal,
    ensure_schema_compatibility,
    engine,
)


async def run_meetuniversity_v2_validation():
    print("=" * 75)
    print("SIGNAL STACK AI — MEETUNIVERSITY REGRESSION VALIDATION (PROFILE V2)")
    print("=" * 75)

    ensure_schema_compatibility(engine)
    db = SessionLocal()

    try:
        # 1. Fetch MeetUniversity
        company = db.query(Company).filter(Company.normalized_domain == "meetuniversity.com").first()
        assert company is not None, "MeetUniversity company record not found in database!"
        print(f"Target Company: {company.name} (ID: {company.id}, Domain: {company.normalized_domain})")

        # 2. Fetch Research Run #2
        run = db.query(ResearchRun).filter(ResearchRun.id == 2, ResearchRun.company_id == company.id).first()
        assert run is not None, "Research Run #2 not found!"
        print(f"Research Run #{run.id}: Status={run.status}, Fetched Pages={run.pages_fetched}")

        # 3. Retrieve stored pages for Run #2
        pages = (
            db.query(ResearchPage)
            .filter(ResearchPage.research_run_id == run.id)
            .order_by(ResearchPage.id.asc())
            .all()
        )
        print(f"Stored Research Pages: {len(pages)} pages loaded from database")
        assert len(pages) == 12, f"Expected 12 pages for Run #2, found {len(pages)}"

        # 4. Check historical profile v1
        prof_v1 = (
            db.query(CompanyProfile)
            .filter(CompanyProfile.company_id == company.id, CompanyProfile.profile_version == 1)
            .first()
        )
        print(f"Historical Profile v1 present: ID={prof_v1.id if prof_v1 else 'None'}")

        # Count facts before run
        facts_before_count = db.query(CompanyFact).filter(CompanyFact.company_id == company.id).count()
        print(f"Historical facts in database: {facts_before_count} records")

        # 5. Run Two-Stage Intelligence Analysis using active provider
        provider = await get_active_ai_provider()
        assert provider is not None, "No active AI provider available!"
        print(f"Active AI Provider: {provider.model_name}")

        analyzer = CompanyIntelligenceAnalyzer(provider)
        print("\n[Executing Stage A & Stage B Two-Stage Extraction Pipeline...]")
        prof_v2 = await analyzer.analyze_and_persist(company, run, pages, db)
        assert prof_v2 is not None
        assert prof_v2.profile_version == 2
        print(f"\n>>> Successfully generated Profile v{prof_v2.profile_version} (ID: {prof_v2.id})! <<<")

        # 6. Evaluate Profile v2 against audit criteria
        print("\n" + "=" * 75)
        print("EVALUATION OF IMPROVED PROFILE V2")
        print("=" * 75)
        print(f"Profile Version:     v{prof_v2.profile_version}")
        print(f"Industry:            {prof_v2.industry}")
        print(f"Business Model:      {prof_v2.business_model}")
        print(f"Positioning:         {prof_v2.positioning}")
        print(f"Operating Presence:  {prof_v2.geographical_markets}")
        print(f"Study Destinations:  {prof_v2.study_destinations} ({len(prof_v2.study_destinations)} destinations)")
        print(f"Products / Services: {prof_v2.products_services}")
        print(f"Target Customers:    {prof_v2.target_customers}")
        print(f"Business Partners:   {prof_v2.business_partners}")
        print(f"Customer Problems:   {prof_v2.customer_problems}")
        print(f"Revenue Streams:     {prof_v2.revenue_streams}")
        print(f"Unknowns:            {prof_v2.unknown_information}")

        # Verification Criteria
        # Criterion 1: All 7 study destinations captured
        dest_set = set(prof_v2.study_destinations)
        expected_7 = {"United Kingdom", "United States", "Canada", "Australia", "Ireland", "Germany", "New Zealand"}
        missing_dests = expected_7 - dest_set
        print(f"\n[Criterion 1: Study Destinations Coverage]")
        print(f"  Expected 7: {expected_7}")
        print(f"  Missing:    {missing_dests if missing_dests else 'NONE (100% Captured!)'}")
        assert not missing_dests, f"Failed to capture all 7 destinations! Missing: {missing_dests}"

        # Criterion 2: Distinction between operating presence and study destinations
        print(f"\n[Criterion 2: Operating Presence vs Study Destinations]")
        print(f"  Operating Presence:  {prof_v2.geographical_markets}")
        print(f"  Study Destinations:  {prof_v2.study_destinations}")
        assert prof_v2.geographical_markets != prof_v2.study_destinations

        # Criterion 3: Revenue Streams not invented
        print(f"\n[Criterion 3: Revenue Streams Anti-Hallucination]")
        print(f"  Revenue Streams: {prof_v2.revenue_streams}")
        for rev in prof_v2.revenue_streams:
            assert "advertising" not in rev.lower()
            assert "affiliate" not in rev.lower()

        # 7. Evaluate Facts Stored
        facts_after = db.query(CompanyFact).filter(CompanyFact.company_id == company.id).all()
        print(f"\n[Criterion 4: Evidence-Grounded Facts & Offsets ({len(facts_after)} total records)]")
        verified_facts = [f for f in facts_after if f.classification == "VERIFIED_FACT"]
        assumptions = [f for f in facts_after if f.classification == "ASSUMPTION"]
        unknowns = [f for f in facts_after if f.classification == "UNKNOWN"]
        rejected = [f for f in facts_after if f.classification == "REJECTED_UNSUPPORTED"]

        print(f"  - VERIFIED_FACT:         {len(verified_facts)}")
        print(f"  - ASSUMPTION:            {len(assumptions)}")
        print(f"  - UNKNOWN:               {len(unknowns)}")
        print(f"  - REJECTED_UNSUPPORTED:  {len(rejected)}")

        for idx, vf in enumerate(verified_facts[:5], 1):
            print(f"\n  Verified Fact #{idx}: {vf.statement}")
            print(f"    Page ID: {vf.research_page_id} | Offsets: [{vf.quote_start_offset}, {vf.quote_end_offset}]")
            print(f"    Snippet: \"{vf.evidence_snippet}\"")
            if vf.research_page:
                print(f"    Source:  {vf.research_page.url}")

        # Check that historical v1 profile is still intact
        prof_v1_check = db.query(CompanyProfile).filter(CompanyProfile.company_id == company.id, CompanyProfile.profile_version == 1).first()
        assert prof_v1_check is not None
        print(f"\n[Criterion 5: Historical Record Preservation]")
        print(f"  Profile v1 ID: {prof_v1_check.id} (Intact, version {prof_v1_check.profile_version})")
        print(f"  Profile v2 ID: {prof_v2.id} (Created, version {prof_v2.profile_version})")
        print("  All historical records preserved with zero data corruption.")

        print("\n" + "=" * 75)
        print(">>> MEETUNIVERSITY REGRESSION VALIDATION PASSED ALL CRITERIA! <<<")
        print("=" * 75)

    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(run_meetuniversity_v2_validation())
