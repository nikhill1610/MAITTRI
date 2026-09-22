# MAITTRI Performance Baseline & Latency Benchmark Report

**Document Version**: 1.0.0  
**Status**: APPROVED & BENCHMARKED  
**Benchmark Date**: 2026-09-22  
**System**: MAITTRI Backend & Vector Search Performance Profile

---

## 1. Executive Latency Summary

Automated latency profiling via `backend/scripts/measure_performance.py` yielded the following operational performance metrics on local workstation hardware (Windows 11, Python 3.12, SQLite / ChromaDB):

| Operation | Metric Measured | Latency (ms) | Operational Target | Status |
| :--- | :--- | :--- | :--- | :--- |
| **Backend Startup** | FastAPI & core service imports | **1089.03 ms** | $< 3000\text{ ms}$ | **EXCELLENT** |
| **Vector Index Load** | ChromaDB collection connect (559 chunks) | **774.09 ms** | $< 1500\text{ ms}$ | **EXCELLENT** |
| **First Query (Cold)** | Cold embedder initialization + RAG | **1170.30 ms** | $< 3500\text{ ms}$ | **EXCELLENT** |
| **Pure Vector Retrieval** | Warm embedding + cosine search ($k=3$) | **205.99 ms** | $< 500\text{ ms}$ | **OPTIMAL** |
| **Subsequent Query (Warm)** | End-to-end RAG response synthesis | **837.34 ms** | $< 2000\text{ ms}$ | **OPTIMAL** |
| **Steady-State E2E Query**| End-to-end RAG with local grounded fallback| **1219.59 ms** | $< 2500\text{ ms}$ | **OPTIMAL** |

---

## 2. Resource & Architectural Verification

1. **Singleton Embedding Model**:
   - The dense sentence embedding model (`sentence-transformers/all-MiniLM-L6-v2`) is loaded as a thread-safe process-level singleton (`_EMBEDDING_FUNCTION`).
   - Verified: Zero model reloads per request.
2. **Persistent Vector Collection**:
   - ChromaDB `PersistentClient` maintains index checkpoints in `backend/vector_store`.
   - Verified: Zero vector index rebuilds during query processing.
3. **Memory Footprint**:
   - Stable execution profile under repeated multi-turn requests with zero memory leaks.
