# Signal Stack AI — System Architecture & Company Intelligence Engine

## 1. Overview
**Signal Stack AI** is an enterprise-grade Company Intelligence and Executive Briefing platform. It continuously crawls external data sources, extracts structured business signals (positioning, business model, product lines, customer problems, markets), verifies claims through verbatim evidence traceability against real web snapshots, and synthesizes high-impact executive profiles via a dual AI provider abstraction (Ollama and Google Gemini).

---

## 2. System Architecture Diagram

```mermaid
flowchart TD
    subgraph Target Data Sources
        DS1[Company Official Website]
        DS2[robots.txt / XML Sitemap]
        DS3[Internal Business Pages]
    end

    subgraph Security & Crawling Layer
        SSRF[SSRF & IP Guard: Reject Private/Loopback/Metadata IPs]
        ROBOTS[Robots.txt Parser & Rate Limiter]
        CRAWLER[Bounded Depth BFS Crawler]
        EXTRACT[Trafilatura & BS4 Content Extractor]
        HASH[SHA-256 Content Deduplicator]
    end

    subgraph Storage Layer (SQLAlchemy 2.0 / SQLite)
        M_COMP[companies]
        M_RUNS[research_runs]
        M_PAGES[research_pages]
        M_PROF[company_profiles]
        M_FACTS[company_facts]
    end

    subgraph AI Intelligence & Evidence Verification
        LLM_MGR[AI Provider Manager: Ollama / Gemini]
        ANALYZER[Company Intelligence Analyzer]
        VERIFY{Verbatim Evidence Check}
        V_FACT[VERIFIED_FACT: Exact Text Match + Page Ref]
        A_FACT[ASSUMPTION: Inference without Verbatim Match]
        U_FACT[UNKNOWN: Explicit Knowledge Gaps]
    end

    subgraph Presentation (React + TypeScript)
        UI_SETUP[Company Registration & Domain Normalizer]
        UI_STATUS[Live Polling Research Telemetry Card]
        UI_PROF[Strategic Profile & Offerings]
        UI_EVID[Evidence & Traceability Panel]
        UI_EDIT[Founder / Analyst Override Form]
    end

    DS1 --> SSRF
    SSRF --> ROBOTS
    ROBOTS --> CRAWLER
    DS2 --> CRAWLER
    CRAWLER --> EXTRACT
    EXTRACT --> HASH
    HASH --> M_PAGES
    CRAWLER --> M_RUNS

    M_PAGES --> ANALYZER
    ANALYZER --> LLM_MGR
    LLM_MGR --> VERIFY
    VERIFY -->|Snippet Found in Extracted Text| V_FACT
    VERIFY -->|Snippet Missing or Unverified| A_FACT
    VERIFY -->|Missing Information| U_FACT
    V_FACT --> M_FACTS
    A_FACT --> M_FACTS
    U_FACT --> M_FACTS
    ANALYZER --> M_PROF

    M_COMP --> UI_SETUP
    M_RUNS --> UI_STATUS
    M_PROF --> UI_PROF
    M_FACTS --> UI_EVID
    UI_EDIT --> M_PROF
```

---

## 3. Database Models Specification

### 3.1 `Company` (`companies`)
- `id`: Integer primary key, autoincrement.
- `name`: Official company name (validated non-empty).
- `website`: Cleaned HTTP/HTTPS URL.
- `normalized_domain`: Normalized domain name (unique, indexed, e.g. `meetuniversity.com`).
- `industry`: Industry or market sector.
- `status`: Lifecycle status (`ACTIVE`, `PENDING`).
- `created_at`, `updated_at`: Timezone-aware UTC timestamps.

### 3.2 `ResearchRun` (`research_runs`)
- `id`: Integer primary key.
- `company_id`: Foreign key referencing `companies.id` (`CASCADE`).
- `status`: Execution state (`PENDING`, `RUNNING`, `COMPLETED`, `COMPLETED_WITH_WARNINGS`, `FAILED`).
- `started_at`, `completed_at`: UTC execution timestamps.
- `pages_discovered`, `pages_fetched`, `pages_failed`: Live telemetry counts.
- `error_message`: Error details if crawl or AI synthesis failed.
- `ai_analysis_status`: Provider state (`PENDING`, `RUNNING`, `COMPLETED`, `FAILED`, `UNAVAILABLE`).

### 3.3 `ResearchPage` (`research_pages`)
- `id`: Integer primary key.
- `company_id`: Foreign key referencing `companies.id` (`CASCADE`).
- `research_run_id`: Foreign key referencing `research_runs.id` (`SET NULL`).
- `url`: Exact crawled URL.
- `canonical_url`: Canonical tag value if present.
- `title`: Page `<title>` or `<h1>` text.
- `extracted_text`: Clean article/body text extracted via Trafilatura.
- `content_hash`: SHA-256 hash of extracted text for snapshot deduplication.
- `http_status`: HTTP status code (200, 404, etc.).
- `first_seen_at`, `last_seen_at`, `crawled_at`: Historical tracking timestamps.

### 3.4 `CompanyProfile` (`company_profiles`)
- `id`: Integer primary key.
- `company_id`: Foreign key referencing `companies.id` (`CASCADE`).
- `research_run_id`: Foreign key referencing `research_runs.id` (`SET NULL`).
- `industry`, `business_model`, `positioning`: Core strategic attributes.
- `products_services`, `target_customers`, `customer_problems`, `revenue_streams`, `geographical_markets`, `growth_related_information`, `unknown_information`: JSON list fields.
- `profile_version`: Incremental version number (allows founder/analyst overrides).
- `updated_at`: Timestamp of latest synthesis or edit.

### 3.5 `CompanyFact` (`company_facts`)
- `id`: Integer primary key.
- `company_id`: Foreign key referencing `companies.id` (`CASCADE`).
- `research_page_id`: Foreign key referencing `research_pages.id` (`SET NULL`).
- `category`: Classification category (e.g. `products_services`, `business_model`).
- `statement`: Factual assertion synthesized by AI.
- `classification`: `VERIFIED_FACT`, `ASSUMPTION`, or `UNKNOWN`.
- `evidence_snippet`: Verbatim quote from extracted webpage text.
- `confidence`: Confidence score (0.0 to 1.0).
- `created_at`: Creation timestamp.

---

## 4. Crawling Security & SSRF Protection
- **IP Address Validation**: Every host is resolved through DNS (`socket.getaddrinfo`) and audited before socket connection. Rejects loopback (`127.0.0.1`), private RFC1918 (`10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`), link-local (`169.254.0.0/16`), and AWS metadata endpoints (`169.254.169.254`).
- **Redirect Hop Inspection**: Redirects are followed manually (`follow_redirects=False`) to validate destination safety on every redirect hop.
- **Domain Scope Enforcement**: Crawling strictly restricted to the registered base domain and legitimate subdomains (`is_internal_link`).
- **Bounded Resource Limits**: Maximum 12 pages, maximum depth 2, 15-second timeouts, 2 MB max response size, 1 request/sec rate limiting.

---

## 5. Evidence Verification Rules
1. **Verbatim Text Match**: For a fact to achieve `VERIFIED_FACT` status, its `evidence_snippet` must exist verbatim (or with normalized whitespace) in the `extracted_text` of the designated `ResearchPage`.
2. **Automated Downgrades**: Any factual assertion whose evidence snippet does not appear in the page text is automatically downgraded to `ASSUMPTION`.
3. **Explicit Knowledge Gaps**: Missing information is maintained under `UNKNOWN` rather than invented.

---

## 6. Implemented APIs

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/health` | System readiness, DB connectivity, AI providers |
| `POST` | `/api/companies` | Register company with domain normalization & SSRF checks |
| `GET` | `/api/companies` | List all registered target companies |
| `GET` | `/api/companies/{id}` | Retrieve company details and latest research run |
| `POST` | `/api/companies/{id}/research` | Trigger background crawling and AI understanding |
| `GET` | `/api/companies/{id}/research` | List research runs for a company |
| `GET` | `/api/companies/{id}/research/{run_id}` | Get telemetry for a specific research run |
| `GET` | `/api/companies/{id}/profile` | Get latest structured company profile |
| `PUT` | `/api/companies/{id}/profile` | Founder / analyst manual profile override |
| `GET` | `/api/companies/{id}/facts` | Get facts with optional `classification` filter |
| `GET` | `/api/companies/{id}/pages` | Get extracted webpage snapshots and content hashes |
