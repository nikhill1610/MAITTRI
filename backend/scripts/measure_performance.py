import os
import sys
import time

sys.path.insert(0, os.path.abspath("backend"))
sys.stdout.reconfigure(encoding="utf-8")

print("=== STAGE 10 PERFORMANCE SANITY BENCHMARK ===")

# 1. Measure Core App Import Latency
t0 = time.perf_counter()
import app.main
from app.services.rag_service import get_chroma_collection, query_knowledge_base
from app.services.smart_rag_router import classify_query
from app.services.chat_service import process_chat_message
import_time_ms = (time.perf_counter() - t0) * 1000.0
print(f"1. Core Backend Import Time: {import_time_ms:.2f} ms")

# 2. Measure Vector Store Client & Collection Initialization
t0 = time.perf_counter()
col = get_chroma_collection()
count = col.count()
vector_init_ms = (time.perf_counter() - t0) * 1000.0
print(f"2. Vector Store (ChromaDB) Collection Load ({count} chunks): {vector_init_ms:.2f} ms")

# 3. Measure First Query (Cold Retrieval & Embedding Load)
test_q = "gehun me pehli sinchai kab karni chahiye?"
t0 = time.perf_counter()
res1 = process_chat_message(test_q)
first_query_ms = (time.perf_counter() - t0) * 1000.0
print(f"3. First Query End-to-End Latency (Cold): {first_query_ms:.2f} ms")

# 4. Measure Pure Vector Retrieval Latency (Warm Embedder)
t0 = time.perf_counter()
retrieval_res = query_knowledge_base(test_q, top_k=3)
pure_retrieval_ms = (time.perf_counter() - t0) * 1000.0
print(f"4. Pure Vector Retrieval Latency (Warm): {pure_retrieval_ms:.2f} ms")

# 5. Measure Subsequent End-to-End Query (Warm Cache)
test_q2 = "sarson me maahu pest ka ilaj batao"
t0 = time.perf_counter()
res2 = process_chat_message(test_q2)
subsequent_query_ms = (time.perf_counter() - t0) * 1000.0
print(f"5. Subsequent Query End-to-End Latency (Warm): {subsequent_query_ms:.2f} ms")

# 6. Check for Obvious Defects (e.g. Model Re-initialization)
t0 = time.perf_counter()
res3 = process_chat_message("tamatar me patta modak rog")
third_query_ms = (time.perf_counter() - t0) * 1000.0
print(f"6. Third Query End-to-End Latency: {third_query_ms:.2f} ms")

# Persist benchmark numbers
perf_data = {
    "import_time_ms": round(import_time_ms, 2),
    "vector_init_ms": round(vector_init_ms, 2),
    "chunks_in_index": count,
    "first_query_ms": round(first_query_ms, 2),
    "pure_retrieval_ms": round(pure_retrieval_ms, 2),
    "subsequent_query_ms": round(subsequent_query_ms, 2),
    "third_query_ms": round(third_query_ms, 2),
    "evaluation_date": "2026-09-22"
}

with open("backend/knowledge_base/_meta/performance_sanity_metrics.json", "w", encoding="utf-8") as f:
    import json
    json.dump(perf_data, f, indent=2)

print("\nPerformance sanity benchmark completed successfully.")
