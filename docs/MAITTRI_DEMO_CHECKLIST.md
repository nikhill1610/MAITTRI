# MAITTRI Live Demo Checklist & Operational Runbook

**Document Version**: 1.0.0  
**Status**: APPROVED & TESTED  
**Last Verified**: 2026-09-22  
**Purpose**: Step-by-step checklist to launch, verify, and operate MAITTRI during live presentations.

---

## 1. Pre-Demo Environment Checklist (5 Minutes Before)

- [ ] **Python Environment**: Ensure Python 3.12 is active with `.venv`.
  ```powershell
  backend\.venv\Scripts\python.exe --version
  ```
- [ ] **Node.js Environment**: Ensure Node.js 18+ is available.
  ```powershell
  node -v
  ```
- [ ] **ChromaDB Vector Store Check**: Confirm 559 chunks exist in `backend/vector_store`.
  ```powershell
  backend\.venv\Scripts\python.exe -c "import chromadb; c = chromadb.PersistentClient('backend/vector_store'); print('Chunks in maitri_krishi_kb:', c.get_collection('maitri_krishi_kb').count())"
  ```
- [ ] **Port Availability**: Ensure ports `8000` (FastAPI) and `5173` (Vite) are unoccupied.

---

## 2. Launch Sequence

### Step 1: Start Backend API Server
Open Terminal 1:
```powershell
cd c:\Users\HP\Desktop\MAITTRI
backend\.venv\Scripts\uvicorn.exe app.main:app --app-dir backend --host 127.0.0.1 --port 8000 --reload
```
*Expected Output*: `Application startup complete. Uvicorn running on http://127.0.0.1:8000`

### Step 2: Smoke Test Backend Health
Open Terminal 2 (or browser):
```powershell
curl http://127.0.0.1:8000/api/chat/status
```
*Expected JSON*: `{"status": "ready", "chunks": 559, "model": "all-MiniLM-L6-v2"}`

### Step 3: Start Frontend Client
In Terminal 2:
```powershell
cd c:\Users\HP\Desktop\MAITTRI\frontend
npm run dev
```
*Expected Output*: `VITE v7.3.6 ready in ~300 ms. Local: http://localhost:5173/`

### Step 4: Open Browser
Open Google Chrome to `http://localhost:5173`.  
Navigate to the **Krishi Assistant** (AI Chat) tab.

---

## 3. Live Smoke Verification (First Test Query)
Type into chat:
> *"gehun me pehli sinchai kab karein?"*

Verify:
- [ ] Response renders cleanly in $< 1.5\text{ seconds}$.
- [ ] CRI (Crown Root Initiation) stage at 20–25 DAS is recommended.
- [ ] ICAR-IIWBR Karnal citation badge appears below the answer.

---

## 4. Graceful Shutdown Procedure
1. In Frontend terminal: Press `Ctrl + C`.
2. In Backend terminal: Press `Ctrl + C`.
3. Terminals return cleanly to prompt.
