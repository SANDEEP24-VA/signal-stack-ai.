import asyncio
import json
import os
import sys
import time

backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from starlette.testclient import TestClient
from app.main import app
from app.database import Base, SessionLocal, Company, CompanyProfile, CompanyFact, ResearchPage, ResearchRun, engine
from app.api.research import run_research_pipeline

def run_real_world_demonstration():
    print("=" * 70)
    print("SIGNAL STACK AI — REAL-WORLD MEETUNIVERSITY RESEARCH DEMONSTRATION")
    print("=" * 70)

    # Use the live database signal_stack.db
    Base.metadata.create_all(bind=engine)
    client = TestClient(app)

    # 1. Register MeetUniversity
    print("\n[Step 1] Registering MeetUniversity via POST /api/companies ...")
    payload = {
        "name": "MeetUniversity",
        "website": "https://www.meetuniversity.com",
        "industry": "EdTech / Higher Education",
    }
    # Check if already registered in database; if so, fetch it
    db = SessionLocal()
    existing = db.query(Company).filter(Company.normalized_domain == "meetuniversity.com").first()
    if existing:
        print(f"MeetUniversity is already registered (ID: {existing.id}, Domain: {existing.normalized_domain})")
        company_id = existing.id
    else:
        res = client.post("/api/companies", json=payload)
        print(f"Registration response status: {res.status_code}")
        assert res.status_code in (201, 200), f"Registration failed: {res.text}"
        data = res.json()
        company_id = data["id"]
        print(f"Registered successfully! Company ID: {company_id}, Domain: {data['normalized_domain']}")

    # 2. Create Research Run
    print(f"\n[Step 2] Initiating Real Research Run for Company ID {company_id} ...")
    run = ResearchRun(
        company_id=company_id,
        status="PENDING",
        ai_analysis_status="PENDING",
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    run_id = run.id
    print(f"Created Research Run #{run_id} in status: {run.status}")
    db.close()

    # 3. Execute the Real Research Pipeline (Crawling + Content Extraction + Ollama/Gemini)
    print(f"\n[Step 3] Executing Website Crawl and AI Intelligence Engine (Run #{run_id}) ...")
    start_time = time.time()
    asyncio.run(run_research_pipeline(company_id=company_id, research_run_id=run_id))
    elapsed = time.time() - start_time
    print(f"Research pipeline completed in {elapsed:.1f} seconds.")

    # 4. Check Research Run Status
    res_run = client.get(f"/api/companies/{company_id}/research/{run_id}")
    assert res_run.status_code == 200
    run_data = res_run.json()
    print("\n--- RESEARCH RUN EXECUTION TELEMETRY ---")
    print(f"Status:             {run_data['status']}")
    print(f"Pages Discovered:   {run_data['pages_discovered']}")
    print(f"Pages Extracted:    {run_data['pages_fetched']}")
    print(f"Pages Failed:       {run_data['pages_failed']}")
    print(f"AI Analysis Status: {run_data['ai_analysis_status']}")
    if run_data.get("error_message"):
        print(f"Error / Notice:     {run_data['error_message']}")

    # 5. Retrieve Extracted Pages
    res_pages = client.get(f"/api/companies/{company_id}/pages")
    assert res_pages.status_code == 200
    pages_list = res_pages.json()
    print(f"\n--- EXTRACTED WEBPAGES ({len(pages_list)} pages stored) ---")
    for idx, p in enumerate(pages_list[:8], 1):
        print(f" [{idx}] HTTP {p['http_status']} | Length: {p['text_length']} chars | Title: {p['title']}")
        print(f"     URL: {p['url']}")

    # 6. Retrieve Generated Profile
    res_prof = client.get(f"/api/companies/{company_id}/profile")
    print(f"\n--- PROFILE STATUS (HTTP {res_prof.status_code}) ---")
    if res_prof.status_code == 200:
        prof = res_prof.json()
        print(f"Profile Version:    v{prof['profile_version']}")
        print(f"Industry:           {prof['industry']}")
        print(f"Business Model:     {prof['business_model']}")
        print(f"Positioning:        {prof['positioning']}")
        print(f"Products/Services:  {prof['products_services']}")
        print(f"Target Customers:   {prof['target_customers']}")
        print(f"Customer Problems:  {prof['customer_problems']}")
        print(f"Markets:            {prof['geographical_markets']}")
        print(f"Growth Info:        {prof['growth_related_information']}")
        print(f"Unknowns:           {prof['unknown_information']}")
    else:
        print(f"Profile response: {res_prof.text}")

    # 7. Retrieve Evidence & Facts
    res_facts = client.get(f"/api/companies/{company_id}/facts")
    assert res_facts.status_code == 200
    facts_list = res_facts.json()
    print(f"\n--- EVIDENCE & FACTS SYNTHESIZED ({len(facts_list)} items) ---")
    verified = [f for f in facts_list if f["classification"] == "VERIFIED_FACT"]
    assumptions = [f for f in facts_list if f["classification"] == "ASSUMPTION"]
    unknowns = [f for f in facts_list if f["classification"] == "UNKNOWN"]

    print(f"\n[VERIFIED FACTS ({len(verified)})]")
    for idx, f in enumerate(verified[:6], 1):
        print(f"  ({idx}) {f['statement']}")
        print(f"      Quote: \"{f['evidence_snippet']}\"")
        print(f"      Source: {f['source_url']}")

    print(f"\n[ASSUMPTIONS ({len(assumptions)})]")
    for idx, f in enumerate(assumptions[:4], 1):
        print(f"  ({idx}) {f['statement']}")

    print(f"\n[UNKNOWN INFORMATION ({len(unknowns)})]")
    for idx, f in enumerate(unknowns[:4], 1):
        print(f"  ({idx}) {f['statement']}")

    # 8. Database Persistence & Restart Check
    print("\n--- DATABASE PERSISTENCE VERIFICATION ---")
    db_verify = SessionLocal()
    persisted_company = db_verify.query(Company).filter(Company.id == company_id).first()
    assert persisted_company is not None
    persisted_pages_count = db_verify.query(ResearchPage).filter(ResearchPage.company_id == company_id).count()
    persisted_facts_count = db_verify.query(CompanyFact).filter(CompanyFact.company_id == company_id).count()
    persisted_prof = db_verify.query(CompanyProfile).filter(CompanyProfile.company_id == company_id).first()
    db_verify.close()

    print(f"Company in DB:      {persisted_company.name} ({persisted_company.normalized_domain})")
    print(f"Research Pages DB:  {persisted_pages_count} pages stored")
    print(f"Facts in DB:        {persisted_facts_count} facts stored")
    print(f"Profile in DB:      v{persisted_prof.profile_version if persisted_prof else 'None'}")
    print("\n>>> REAL-WORLD MEETUNIVERSITY DEMONSTRATION COMPLETED SUCCESSFULLY! <<<")

if __name__ == "__main__":
    run_real_world_demonstration()
