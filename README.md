# Signal Stack AI

### AI-Powered Company Intelligence & Executive Briefing Platform

**Signal Stack AI** is an evidence-grounded company intelligence platform designed to help businesses understand their competitive environment, discover relevant market developments, identify strategic opportunities and make better decisions.

It combines automated website research, AI-powered company profiling, adaptive founder interviews, competitor discovery and intelligence source management into a modular platform.

The system uses a dual-provider AI architecture supporting **Google Gemini and local Ollama**, with FastAPI, React, TypeScript and SQLite powering the application.

---

## 1. Key Features

### 1.1 Automated Company Research

- Register companies using their name and official website.
- Crawl publicly accessible website pages.
- Discover pages through sitemaps and internal links.
- Extract meaningful website content using Trafilatura and BeautifulSoup.
- Respect robots.txt, crawling restrictions and website boundaries.
- Store research runs, extracted pages and historical information.

### 1.2 Evidence-Grounded Company Intelligence

- Extract company-level facts from collected website content.
- Use a two-stage extraction and synthesis architecture.
- Generate structured, versioned company profiles.
- Attach supporting evidence to extracted claims.
- Validate evidence using exact text excerpts and character offsets.
- Distinguish verified facts, assumptions, unknown information and unsupported claims.
- Preserve historical profile versions.

### 1.3 Adaptive AI Founder Interview Engine

The platform conducts an executive-level interview to understand business information that cannot be reliably obtained through public website research.

Capabilities include:

- Generates exactly 10 company-specific core questions.
- Adapts questions to the company's industry, products, customers and research blindspots.
- Presents one question at a time.
- Generates contextual follow-up questions.
- Supports skipping, editing, pausing and resuming interviews.
- Tracks interview progress.
- Extracts founder-confirmed business context.
- Maintains separation between public evidence and founder-provided information.
- Supports confidential responses and their exclusion from public profile extraction.
- Updates company profiles through versioned changes.

### 1.4 Competitor Discovery

- Identifies potential competitors using company business context.
- Supports direct competitors, indirect competitors and substitutes.
- Evaluates product, customer and geographic overlap.
- Maintains supporting evidence and discovery rationale.
- Supports competitor review and governance workflows.
- Avoids relying on hardcoded competitor lists.

### 1.5 Intelligence Source Discovery and Management

Organizes intelligence around four Signal Stack categories:

| Category | Intelligence focus |
|---|---|
| Customers | Customer needs, behaviour, reviews and market feedback |
| Competitors | Competitor products, announcements, pricing and strategic developments |
| Market | Industry trends, regulations, research and market developments |
| Internal | Founder-confirmed information and authorized internal business intelligence |

The source management architecture supports source discovery, categorization, evidence tracking and source governance.

### 1.6 AI Provider Abstraction

The application supports multiple AI providers through a common provider architecture.

- Google Gemini for cloud-based AI reasoning.
- Ollama for locally hosted language models.
- Configurable provider selection.
- Structured AI outputs and validation.
- Fallback handling for provider failures.

### 1.7 Persistent Data Storage

The platform uses SQLAlchemy ORM and SQLite to persist company information, research records, profiles, interview data and intelligence-related records.

### 1.8 Background Scheduling Foundation

An APScheduler-based scheduling module is included to support automated intelligence workflows and recurring background jobs.

---

## 2. System Architecture

```text
                    SIGNAL STACK AI
                           |
             +-------------+-------------+
             |                           |
         FRONTEND                    BACKEND
             |                           |
      React + TypeScript              FastAPI
             |                           |
      Dashboard & Views          Modular API Routes
             |                           |
             +-------------+-------------+
                           |
                    APPLICATION SERVICES
                           |
       +-------------------+-------------------+
       |                   |                   |
  Company Research   Founder Interview   Discovery Engine
       |                   |                   |
  Web Crawlers       Question Generator  Competitor Discovery
  Content Extraction Follow-up Engine    Source Discovery
  Evidence Validator Context Extractor   Source Governance
       |                   |                   |
       +-------------------+-------------------+
                           |
                       AI LAYER
                           |
                +----------+----------+
                |                     |
            Google Gemini           Ollama
                |                     |
                +----------+----------+
                           |
                     DATA LAYER
                           |
                    SQLAlchemy ORM
                           |
                        SQLite
```

---

## 3. Project Structure

```text
signal-stack-ai/
│
├── backend/
│   ├── app/
│   │   ├── ai/
│   │   │   ├── analyzer.py
│   │   │   ├── base.py
│   │   │   ├── extractor.py
│   │   │   ├── gemini.py
│   │   │   ├── manager.py
│   │   │   ├── ollama.py
│   │   │   ├── synthesizer.py
│   │   │   └── validator.py
│   │   │
│   │   ├── api/
│   │   │   ├── companies.py
│   │   │   ├── competitors.py
│   │   │   ├── health.py
│   │   │   ├── interviews.py
│   │   │   ├── profiles.py
│   │   │   ├── research.py
│   │   │   ├── sources.py
│   │   │   └── router.py
│   │   │
│   │   ├── core/
│   │   │   └── errors.py
│   │   │
│   │   ├── crawlers/
│   │   │   ├── base.py
│   │   │   ├── engine.py
│   │   │   ├── extractor.py
│   │   │   ├── facets.py
│   │   │   ├── robots.py
│   │   │   ├── sitemap.py
│   │   │   └── url_utils.py
│   │   │
│   │   ├── database/
│   │   │   ├── base.py
│   │   │   ├── migration.py
│   │   │   ├── models.py
│   │   │   └── session.py
│   │   │
│   │   ├── discovery/
│   │   │   ├── competitors.py
│   │   │   ├── governance.py
│   │   │   └── sources.py
│   │   │
│   │   ├── interview/
│   │   │   ├── context_extractor.py
│   │   │   ├── followup.py
│   │   │   ├── generator.py
│   │   │   └── state_machine.py
│   │   │
│   │   ├── scheduler/
│   │   │   └── manager.py
│   │   │
│   │   ├── schemas/
│   │   ├── config.py
│   │   └── main.py
│   │
│   ├── tests/
│   ├── requirements.txt
│   └── run.py
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── companies/
│   │   │   ├── dashboard/
│   │   │   ├── interview/
│   │   │   ├── layout/
│   │   │   └── sources/
│   │   │
│   │   ├── services/
│   │   ├── types/
│   │   ├── App.tsx
│   │   ├── index.css
│   │   └── main.tsx
│   │
│   ├── package.json
│   ├── tailwind.config.js
│   └── vite.config.ts
│
├── docs/
│   └── ARCHITECTURE.md
│
├── .env.example
├── .gitignore
├── package.json
└── README.md
```

---

## 4. Technology Stack

| Layer | Technologies |
|---|---|
| Frontend | React, TypeScript, Vite, Tailwind CSS |
| Backend | Python, FastAPI, Uvicorn |
| Database | SQLite, SQLAlchemy 2.0 ORM |
| Data Validation | Pydantic v2 |
| Cloud AI | Google Gemini |
| Local AI | Ollama, Llama 3.2 |
| Web Crawling | HTTPX, BeautifulSoup4 |
| Content Extraction | Trafilatura |
| URL Discovery | Sitemaps, robots.txt, internal links |
| Background Jobs | APScheduler |
| Testing | Pytest |
| Version Control | Git, GitHub |

---

## 5. Prerequisites

Install the following before running the application:

- **Python:** 3.11 or above (Python 3.12 recommended).
- **Node.js:** 20 or above.
- **npm:** Included with Node.js.
- **Git:** For version control.
- **Ollama:** Required when using the local AI provider.
- **Google Gemini API key:** Optional when using Gemini.

---

## 6. Installation and Setup

### Step 6.1: Clone the Repository

```powershell
git clone <YOUR_GITHUB_REPOSITORY_URL>
cd signal-stack-ai
```

### Step 6.2: Configure Environment Variables

Create a local environment file from the provided template:

```powershell
Copy-Item .env.example .env
```

Open the environment file:

```powershell
notepad .env
```

Example configuration:

```env
PROJECT_NAME="Signal Stack AI"
ENVIRONMENT="development"
DEBUG=True

HOST="127.0.0.1"
PORT=8000

DATABASE_URL="sqlite:///./signal_stack.db"

# Gemini configuration
GEMINI_API_KEY=""
GEMINI_MODEL="gemini-1.5-flash"

# Ollama configuration
OLLAMA_BASE_URL="http://localhost:11434"
OLLAMA_MODEL="llama3.2"

# Choose the active provider
DEFAULT_AI_PROVIDER="ollama"

VITE_API_BASE_URL="http://127.0.0.1:8000/api"
```

For Gemini, add your own API key and configure:

```env
DEFAULT_AI_PROVIDER="gemini"
```

Never commit your actual `.env` file or API credentials.

### Step 6.3: Backend Installation

From the project root:

```powershell
py -3.12 -m venv backend\venv
```

Activate the environment:

```powershell
.\backend\venv\Scripts\Activate.ps1
```

If PowerShell blocks script execution, use:

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process
```

Install the backend dependencies:

```powershell
python -m pip install --upgrade pip
pip install -r backend\requirements.txt
```

### Step 6.4: Start the Backend

From the project root, with the virtual environment activated:

```powershell
python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000 --reload
```

The backend will be available at:

- **API Base:** http://127.0.0.1:8000
- **Health Check:** http://127.0.0.1:8000/api/health
- **Swagger Documentation:** http://127.0.0.1:8000/docs

### Step 6.5: Configure the Local AI Provider

For Ollama, install Ollama and download the required model:

```powershell
ollama pull llama3.2
```

Verify the model:

```powershell
ollama list
```

Ensure the Ollama service is running and accessible at:

```text
http://localhost:11434
```

### Step 6.6: Frontend Installation

Open a second terminal:

```powershell
cd frontend
npm install
```

Start the development server:

```powershell
npm run dev
```

The frontend will be available at:

http://localhost:5173

---

## 7. Health Verification

Verify backend connectivity using PowerShell:

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/health" |
    ConvertTo-Json -Depth 5
```

The health endpoint reports application and database connectivity, together with configured AI provider information.

Open the interactive API documentation:

http://127.0.0.1:8000/docs

---

## 8. Database Architecture

Signal Stack AI uses SQLite as its development database and SQLAlchemy as its ORM.

The database contains persistent records for:

| Model | Responsibility |
|---|---|
| Company | Registered companies |
| ResearchRun | Company research execution history |
| ResearchPage | Extracted website pages |
| CompanyProfile | Versioned company intelligence profiles |
| CompanyFact | Evidence-backed public company facts |
| DiscoveredUrl | Discovered website URLs |
| InterviewSession | Founder interview sessions |
| InterviewQuestion | Core and follow-up questions |
| InterviewAnswer | Founder responses |
| FounderBusinessContext | Founder-confirmed business information |
| Competitor records | Discovered competitor information |
| Source records | Intelligence source information |

The database is created and accessed by the backend according to the configured `DATABASE_URL`.

Local database files are excluded from GitHub to prevent accidental publication of private or environment-specific information.

---

## 9. Testing

Run the backend test suite from the project root with the virtual environment activated:

```powershell
python -m pytest backend/tests -v
```

The tests cover application health, database operations, crawling, AI analysis, company research, founder interviews and competitor/source discovery.

Additional demonstration and validation scripts are available in the backend test directory.

---

## 10. Responsible Intelligence Collection

Signal Stack AI is designed around evidence quality, source provenance and responsible public-web collection.

The system follows these principles:

- Respect robots.txt and applicable website restrictions.
- Avoid bypassing authentication, paywalls or access controls.
- Apply URL validation and SSRF protections.
- Avoid unnecessary repeated downloads.
- Preserve evidence supporting extracted claims.
- Separate public information from founder-provided information.
- Treat AI-generated discoveries as candidates until appropriately validated.
- Avoid presenting unsupported assumptions as verified facts.

---

## 11. Development Roadmap

The platform is being developed incrementally toward a complete executive intelligence workflow.

| Milestone | Objective |
|---|---|
| Task 1 | Company registration and automated website research |
| Task 2 | Evidence validation and versioned company profiling |
| Task 3 | Adaptive AI founder interview engine |
| Task 4 | Dynamic competitor discovery and source management |
| Task 5 | Continuous intelligence collection and change detection |
| Task 6 | Signal classification, business-impact analysis and ranking |
| Task 7 | Monday Morning executive intelligence briefing |
| Task 8 | Internal intelligence, action tracking and automation |
| Task 9 | Cross-industry validation, deployment and final demonstration |

The ultimate objective is to transform raw external information into evidence-backed business signals and actionable executive intelligence.

---

## 12. Project Vision

Signal Stack AI aims to move beyond conventional news aggregation.

Instead of simply collecting articles, it is designed to understand a company's business model, identify relevant developments, evaluate the supporting evidence, determine the potential business impact and communicate what leadership should pay attention to.

**From information collection to evidence-grounded strategic intelligence.**

---

## 13. License

Add an appropriate open-source license before publishing the project as an open-source repository.

---

**Developed as an AI-powered company intelligence and executive briefing platform.**