from starlette.testclient import TestClient
from sqlalchemy.orm import Session
from app.database import Company, CompanyProfile


def test_create_company_success(client: TestClient):
    payload = {
        "name": "Acme Analytics",
        "website": "https://www.acme-analytics.io/home",
        "industry": "Business Intelligence",
    }
    response = client.post("/api/companies", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Acme Analytics"
    assert data["normalized_domain"] == "acme-analytics.io"
    assert data["industry"] == "Business Intelligence"
    assert data["status"] == "ACTIVE"
    assert "id" in data


def test_create_company_invalid_url(client: TestClient):
    # Invalid protocol
    res1 = client.post("/api/companies", json={"name": "Bad", "website": "ftp://files.example.com"})
    assert res1.status_code == 400
    assert "Unsupported protocol" in res1.json()["error"]["message"]

    # Embedded credentials
    res2 = client.post("/api/companies", json={"name": "Bad", "website": "https://user:pass@example.com"})
    assert res2.status_code == 400
    assert "Embedded credentials" in res2.json()["error"]["message"]

    # Non-standard port
    res3 = client.post("/api/companies", json={"name": "Bad", "website": "https://example.com:8443"})
    assert res3.status_code == 400
    assert "Port 8443 is not permitted" in res3.json()["error"]["message"]

    # Blank company name
    res4 = client.post("/api/companies", json={"name": "   ", "website": "https://example.com"})
    assert res4.status_code == 422


def test_prevent_duplicate_company_domain(client: TestClient):
    # First registration
    client.post("/api/companies", json={"name": "First Corp", "website": "https://first-corp.com"})

    # Duplicate with different subdomain/path
    res_dup = client.post(
        "/api/companies",
        json={"name": "Second Name", "website": "https://www.first-corp.com/about"},
    )
    assert res_dup.status_code == 409
    assert res_dup.json()["error"]["code"] == "DUPLICATE_COMPANY"


def test_get_company_by_id_and_list(client: TestClient):
    res_create = client.post(
        "/api/companies",
        json={"name": "Target Enterprise", "website": "https://target-enterprise.com"},
    )
    assert res_create.status_code == 201
    cid = res_create.json()["id"]

    # Get by ID
    res_get = client.get(f"/api/companies/{cid}")
    assert res_get.status_code == 200
    assert res_get.json()["id"] == cid
    assert res_get.json()["normalized_domain"] == "target-enterprise.com"

    # List all
    res_list = client.get("/api/companies")
    assert res_list.status_code == 200
    assert isinstance(res_list.json(), list)
    assert any(c["id"] == cid for c in res_list.json())


def test_company_profile_persistence_and_update(client: TestClient, db_session: Session):
    res_create = client.post(
        "/api/companies",
        json={"name": "Profile Target", "website": "https://profile-target.com"},
    )
    cid = res_create.json()["id"]

    # Initially profile does not exist
    res_init = client.get(f"/api/companies/{cid}/profile")
    assert res_init.status_code == 404

    # Save initial profile via PUT
    put_data = {
        "industry": "Enterprise Software",
        "business_model": "B2B SaaS subscription",
        "products_services": ["Signal Engine", "Executive Alerts"],
        "target_customers": ["C-Suite", "Venture Capitalists"],
        "customer_problems": ["Information overload", "Missed competitor signals"],
        "revenue_streams": ["Annual contracts"],
        "geographical_markets": ["North America", "Europe"],
        "positioning": "Autonomous executive intelligence platform",
        "growth_related_information": ["Expanding to APAC"],
        "unknown_information": ["Pricing tier specifics"],
    }
    res_put = client.put(f"/api/companies/{cid}/profile", json=put_data)
    assert res_put.status_code == 200
    pdata = res_put.json()
    assert pdata["profile_version"] == 1
    assert pdata["business_model"] == "B2B SaaS subscription"
    assert "Signal Engine" in pdata["products_services"]

    # Update profile (increments version)
    put_data["business_model"] = "Usage-based enterprise subscription"
    res_put2 = client.put(f"/api/companies/{cid}/profile", json=put_data)
    assert res_put2.status_code == 200
    assert res_put2.json()["profile_version"] == 2
    assert res_put2.json()["business_model"] == "Usage-based enterprise subscription"
