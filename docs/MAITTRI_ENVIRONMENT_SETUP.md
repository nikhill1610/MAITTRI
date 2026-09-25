# MAITTRI Environment Setup & Security Hygiene Guide

**Document Version**: 1.0.0  
**Status**: APPROVED & ACTIVE  
**Last Audit**: 2026-09-22  
**System**: MAITTRI Environment & Secret Hygiene Specification

---

## 1. Secret Hygiene & Git Isolation

The MAITTRI repository enforces zero-trust credential hygiene:
- **`.gitignore`**: Blocks all `.env`, `.env.*`, `*.pem`, `*.key`, and `secrets/` folders.
- **Client vs Server Boundary**: Frontend (`frontend/`) contains zero server-side secret keys. Only `VITE_API_URL` or public anon keys are used client-side.
- **Sensitive Key Protection**: `SUPABASE_SERVICE_ROLE_KEY`, `OPENROUTER_API_KEY`, `GEMINI_API_KEY`, and `TAVILY_API_KEY` are isolated exclusively in the backend runtime environment.
- **Log Sanitization**: Application logger explicitly masks authorization tokens, passwords, and API credentials.

---

## 2. Environment Variables Specification

| Variable Name | Required / Optional | Scope | Default / Example | Purpose |
| :--- | :--- | :--- | :--- | :--- |
| `ENVIRONMENT` | Required | Backend | `development` / `production` | Controls SQLite dev DB vs Supabase PostgreSQL pooler |
| `SECRET_KEY` | Required | Backend | 32+ char secure hex | JWT token signing & session authentication |
| `DATABASE_URL` | Required | Backend | `sqlite:///./agri.db` (dev) | Relational database connection string |
| `CORS_ORIGINS` | Required | Backend | `http://localhost:5173` | Allowed frontend origins for API access |
| `OPENROUTER_API_KEY`| Optional | Backend | `sk-or-v1-...` | Primary LLM generation provider |
| `OPENROUTER_MODEL` | Optional | Backend | `meta-llama/llama-3.3-70b-instruct:free` | Primary LLM model identifier |
| `GEMINI_API_KEY` | Optional | Backend | `AIza...` | Secondary LLM fallback provider |
| `TAVILY_API_KEY` | Optional | Backend | `tvly-...` | Trusted web search fallback API |
| `WEB_SEARCH_ENABLED`| Optional | Backend | `true` | Enables live web search fallback |

---

## 3. Quickstart Local Setup

### 3.1 Backend Setup (Python 3.12)
```bash
cd backend
python -m venv .venv
# On Windows:
.venv\Scripts\activate
# On Linux/macOS:
source .venv/bin/activate

pip install -r requirements.txt
cp .env.example .env

# Start FastAPI server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 3.2 Frontend Setup (Node.js 18+)
```bash
cd frontend
npm install
npm run dev
# Access local web application at http://localhost:5173
```
