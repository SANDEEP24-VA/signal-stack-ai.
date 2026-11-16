# Signal Stack AI

> AI-Powered Company Intelligence & Executive Briefing Platform

Signal Stack AI provides automated, multi-source external signal tracking, competitive intelligence analysis, and executive briefing synthesis using a modular architecture supporting FastAPI, React, SQLite, and dual AI providers (Google Gemini & Ollama).

---

## 1. Project Structure

```
signal-stack-ai/
├── backend/
│   ├── app/
│   │   ├── api/             # Modular API routes (health, future modules)
│   │   ├── core/            # Error handling and middleware
│   │   ├── database/        # SQLite database session and base models
│   │   ├── ai/              # AI provider abstraction (Gemini, Ollama)
│   │   ├── crawlers/        # HTTPX, Trafilatura, Feedparser crawlers
│   │   ├── scheduler/       # APScheduler async background runner
│   │   ├── config.py        # Pydantic Settings
│   │   └── main.py          # FastAPI application entrypoint
│   └── requirements.txt     # Python backend dependencies
├── frontend/
│   ├── src/
│   │   ├── components/      # Layout (Sidebar, Header), Dashboard widgets
│   │   ├── services/        # Backend API service integration
│   │   ├── types/           # TypeScript definitions
│   │   ├── App.tsx          # Main React component
│   │   └── main.tsx         # Application entry
│   ├── package.json         # React + Vite dependencies
│   ├── tailwind.config.js   # Tailwind CSS configuration
│   └── vite.config.ts       # Vite configuration with API proxy
├── docs/
│   └── ARCHITECTURE.md      # Detailed system architecture document
├── .env.example             # Environment configuration template
├── .gitignore               # Version control ignores
└── README.md                # Windows PowerShell setup and execution guide
```

---

## 2. Prerequisites

- **Python**: 3.11+ (Python 3.12 recommended on Windows)
- **Node.js**: v18+ (Node v20+ recommended)
- **PowerShell**: Windows PowerShell 5.1 or PowerShell Core 7+

---

## 3. Quick Start (Windows PowerShell)

Open PowerShell and navigate into the project directory:

```powershell
cd signal-stack-ai
```

### Step 3.1: Environment Configuration

Copy the template `.env.example` to `.env`:

```powershell
Copy-Item .env.example .env
```

*(Optional)* Open `.env` to configure your `GEMINI_API_KEY` or Ollama endpoint:
```powershell
notepad .env
```

---

### Step 3.2: Backend Setup & Execution

Open a dedicated PowerShell terminal for the backend:

```powershell
# Option A: One-click launch from root workspace
python run.py

# Option B: From signal-stack-ai\backend directory
cd signal-stack-ai\backend

# (If running scripts is restricted in PowerShell, run once in your session):
# Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process

# Activate virtual environment
.\venv\Scripts\Activate.ps1

# Launch backend server
python run.py
# or: uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Backend will be active at:
- **API Base**: `http://127.0.0.1:8000`
- **Health Check**: `http://127.0.0.1:8000/api/health`
- **Interactive Swagger Docs**: `http://127.0.0.1:8000/docs`

---

### Step 3.3: Frontend Setup & Execution

Open a second PowerShell terminal for the frontend:

```powershell
# Option A: One-command launch from workspace root:
npm run dev

# Option B: From signal-stack-ai\frontend directory:
cd signal-stack-ai\frontend
npm run dev
```

Frontend will be active at:
- **Dashboard UI**: `http://localhost:5173`

---

## 4. Health Verification

Verify the backend health check in PowerShell:

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/health" | ConvertTo-Json -Depth 4
```

Expected JSON response:
```json
{
  "status": "healthy",
  "service": "Signal Stack AI",
  "version": "0.1.0",
  "environment": "development",
  "timestamp": "2026-11-16T11:45:00.000000+00:00",
  "database": {
    "connected": true,
    "type": "sqlite"
  },
  "ai_providers": {
    "gemini": {
      "configured": false,
      "model": "gemini-1.5-flash",
      "target": "Google AI"
    },
    "ollama": {
      "configured": true,
      "model": "llama3.2",
      "target": "http://localhost:11434"
    }
  }
}
```

---

## 5. Technology Stack Summary

| Layer | Technologies |
|---|---|
| **Frontend** | React 18, TypeScript, Vite 5, Tailwind CSS, Lucide Icons |
| **Backend API** | Python, FastAPI, Uvicorn, Pydantic v2 |
| **Database** | SQLite, SQLAlchemy 2.0 ORM |
| **AI Providers** | Google Gemini API, Local Ollama Abstraction |
| **Crawling & Extraction** | HTTPX (Async), BeautifulSoup4, Trafilatura, Feedparser |
| **Job Scheduling** | APScheduler (AsyncIOScheduler) |
