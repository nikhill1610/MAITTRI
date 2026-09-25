# MAITTRI Demo Recovery Plan & Incident Playbook

**Document Version**: 1.0.0  
**Status**: APPROVED & TESTED  
**Last Verified**: 2026-09-22  
**Purpose**: Emergency recovery procedures for presenters if a failure occurs during a live demonstration.

---

## 1. Quick Triage Table

| Symptom Observed | Root Cause | Immediate Recovery Action | Time to Recover |
| :--- | :--- | :--- | :--- |
| **Chat shows loading spinner indefinitely** | Backend server is not running or crashed | Check Terminal 1; restart uvicorn server | $< 10\text{ seconds}$ |
| **API returns HTTP 429 / Rate Limit** | OpenRouter/Gemini quota temporarily exhausted | **Automatic**: System automatically triggers local grounded RAG fallback (`grounded_local_rag`). No presenter intervention needed. | Immediate ($0\text{ s}$) |
| **Browser shows Network Error** | Frontend calling wrong port or CORS blocked | Refresh page (`Ctrl + F5`); check backend is listening on `8000` | $< 5\text{ seconds}$ |
| **Vector count returns 0 chunks** | ChromaDB directory moved or unindexed | Run fast re-ingestion script: `python backend/scripts/ingest_knowledge.py` | $< 25\text{ seconds}$ |
| **Port 8000 already in use** | Stray uvicorn background process running | Kill old process: `Stop-Process -Id (Get-NetTCPConnection -LocalPort 8000).OwningProcess -Force` | $< 5\text{ seconds}$ |

---

## 2. Offline / No-Internet Mode

MAITTRI is built with a resilient dual architecture:
- **Offline Capable**:
  - Full dense vector retrieval over all 62 documents (559 chunks).
  - All intent routing (fertilizer, soil, irrigation, pesticide refusal, gibberish).
  - Deterministic grounded local RAG synthesis from verified ICAR/CIBRC chunks.
- **Presenter Narrative for Offline Operation**:
  > *"Even in rural areas with zero internet or cloud outage, MAITTRI's local embedded RAG engine retrieves verified ICAR packages from disk without needing continuous cloud connectivity."*

---

## 3. Emergency Fast Restart Command
If an unpredictable state occurs, run this single PowerShell line from the repository root:
```powershell
backend\.venv\Scripts\python.exe -c "import app.main; print('Backend Syntax OK'); import chromadb; c=chromadb.PersistentClient('backend/vector_store'); print('Chunks:', c.get_collection('maitri_krishi_kb').count())"
```
If both print OK, simply restart uvicorn:
```powershell
backend\.venv\Scripts\uvicorn.exe app.main:app --app-dir backend --host 127.0.0.1 --port 8000
```
