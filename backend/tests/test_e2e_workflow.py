import json
import pytest
from starlette.testclient import TestClient
from sqlalchemy.orm import Session

from app.ai.analyzer import CompanyIntelligenceAnalyzer
from app.ai.base import AICompletionResult, BaseAIProvider
from app.crawlers.extractor import ContentExtractor
from app.database import Company, CompanyProfile, ResearchPage, ResearchRun


class E2EMockProvider(BaseAIProvider):
    def __init__(self, target_page_id: int):
        super().__init__(model_name="e2e-mock-llm")
        self.target_page_id = target_page_id

    async def is_available(self) -> bool:
        return True

    async def generate_completion(self, prompt: str, system_instruction=None, temperature=0.2):
        data = {
            "company_name": "Nexus Robotics",
            "industry": "Industrial Automation",
            "business_model": "Hardware and Software PaaS",
            "products_services": ["Autonomous Forklifts", "FleetPilot OS"],
            "target_customers": ["Warehouses", "Logistics hubs"],
            "customer_problems": ["Labor shortages in fulfillment centers"],
            "revenue_streams": ["Robot leasing", "Software subscriptions"],
            "geographical_markets": ["North America", "Germany"],
            "positioning": "Pioneering vision-guided warehouse autonomy",
            "growth_related_information": ["Expanding to port logistics"],
            "verified_facts": [
                {
                    "category": "products_services",
                    "statement": "Nexus Robotics builds Autonomous Forklifts powered by FleetPilot OS.",
                    "evidence_snippet": "Nexus Robotics builds Autonomous Forklifts powered by our proprietary FleetPilot OS.",
                    "source_page_id": self.target_page_id,
                }
            ],
            "assumptions": [
                {
                    "category": "business_model",
                    "statement": "Likely pursuing venture funding to accelerate international deployment.",
                }
            ],
            "unknown_information": [
                "Full bill-of-materials and hardware supplier list not publicly available.",
            ],
        }
        return AICompletionResult(
            raw_text=json.dumps(data),
            model="e2e-mock-llm",
            provider="mock",
        )


@pytest.mark.asyncio
async def test_end_to_end_company_intelligence_workflow(client: TestClient, db_session: Session):
    # 1. Register Company via API
    reg_res = client.post(
        "/api/companies",
        json={
            "name": "Nexus Robotics",
            "website": "https://www.nexusrobotics.ai",
            "industry": "Robotics",
        },
    )
    assert reg_res.status_code == 201
    company_data = reg_res.json()
    cid = company_data["id"]
    assert company_data["normalized_domain"] == "nexusrobotics.ai"

    # 2. Simulate Research Run and Page Crawling
    run = ResearchRun(
        company_id=cid,
        status="RUNNING",
        pages_discovered=2,
        pages_fetched=2,
        pages_failed=0,
    )
    db_session.add(run)
    db_session.flush()

    raw_html = """
    <html>
      <head><title>Nexus Robotics - Industrial Autonomy</title></head>
      <body>
        <h1>Warehouse Automation</h1>
        <p>Nexus Robotics builds Autonomous Forklifts powered by our proprietary FleetPilot OS.</p>
        <p>Our solutions eliminate labor bottlenecks in high-volume fulfillment centers.</p>
      </body>
    </html>
    """
    title, text, canonical, content_hash = ContentExtractor.extract(raw_html, "https://nexusrobotics.ai")

    page = ResearchPage(
        company_id=cid,
        research_run_id=run.id,
        url="https://nexusrobotics.ai",
        title=title,
        extracted_text=text,
        content_hash=content_hash,
        http_status=200,
    )
    db_session.add(page)
    db_session.flush()

    # 3. Execute AI Analysis & Verification
    provider = E2EMockProvider(target_page_id=page.id)
    analyzer = CompanyIntelligenceAnalyzer(provider)
    profile = await analyzer.analyze_and_persist(
        company=db_session.get(Company, cid),
        research_run=run,
        pages=[page],
        db=db_session,
    )
    assert profile is not None
    assert profile.profile_version == 1

    # 4. Verify Company Profile Retrieval API
    prof_res = client.get(f"/api/companies/{cid}/profile")
    assert prof_res.status_code == 200
    prof_json = prof_res.json()
    assert prof_json["business_model"] == "Hardware and Software PaaS"
    assert "Autonomous Forklifts" in prof_json["products_services"]
    assert "FleetPilot OS" in prof_json["products_services"]

    # 5. Verify Facts API and Evidence Traceability
    facts_res = client.get(f"/api/companies/{cid}/facts")
    assert facts_res.status_code == 200
    facts_list = facts_res.json()
    assert len(facts_list) >= 3

    verified = [f for f in facts_list if f["classification"] == "VERIFIED_FACT"]
    assert len(verified) == 1
    assert verified[0]["source_url"] == "https://nexusrobotics.ai"
    assert "Autonomous Forklifts" in verified[0]["statement"]
    assert verified[0]["evidence_snippet"] == "Nexus Robotics builds Autonomous Forklifts powered by our proprietary FleetPilot OS."

    # Filter by classification query param
    verified_only = client.get(f"/api/companies/{cid}/facts?classification=VERIFIED_FACT")
    assert verified_only.status_code == 200
    assert all(f["classification"] == "VERIFIED_FACT" for f in verified_only.json())

    # 6. Verify Crawled Pages API
    pages_res = client.get(f"/api/companies/{cid}/pages")
    assert pages_res.status_code == 200
    pages_json = pages_res.json()
    assert len(pages_json) == 1
    assert pages_json[0]["url"] == "https://nexusrobotics.ai"
    assert pages_json[0]["title"] == "Nexus Robotics - Industrial Autonomy"
