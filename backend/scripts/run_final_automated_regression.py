import os
import sys
import time
import json
import subprocess
import glob
import re

sys.path.insert(0, os.path.abspath("backend"))
sys.stdout.reconfigure(encoding="utf-8")

print("=== STAGE 14 FINAL AUTOMATED REGRESSION RUN ===")
t_start = time.time()

report = {
    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
    "status": "RUNNING",
    "checks": {}
}

# 1. Pytest Suite Execution
print("\n--- 1. Running Pytest Suite ---")
test_files = [
    "backend/tests/test_rag_trustworthy.py",
    "backend/tests/test_chat_rag.py",
    "backend/tests/test_smart_rag_router.py",
    "backend/tests/test_web_search_fallback.py",
    "backend/tests/test_coderabbit_security_web_fixes.py",
    "backend/tests/test_manual_batch1_fixes.py",
    "backend/tests/test_scheme_source_contamination.py"
]
p_start = time.time()
res_pytest = subprocess.run([sys.executable, "-m", "pytest"] + test_files + ["-q"], capture_output=True, text=True, encoding="utf-8", errors="replace")
p_runtime = time.time() - p_start
pytest_output = (res_pytest.stdout or "") + "\n" + (res_pytest.stderr or "")
print(pytest_output.strip().split("\n")[-1])

passed_match = re.search(r"(\d+) passed", pytest_output)
failed_match = re.search(r"(\d+) failed", pytest_output)
passed_count = int(passed_match.group(1)) if passed_match else 0
failed_count = int(failed_match.group(1)) if failed_match else 0

report["checks"]["pytest_regression"] = {
    "total_collected": passed_count + failed_count,
    "passed": passed_count,
    "failed": failed_count,
    "runtime_seconds": round(p_runtime, 2),
    "exit_code": res_pytest.returncode,
    "status": "PASSED" if res_pytest.returncode == 0 and failed_count == 0 else "FAILED"
}

# 2. Vector Store & Knowledge Base Counts
print("\n--- 2. Checking KB & Vector Store Counts ---")
import chromadb
client = chromadb.PersistentClient(path="backend/vector_store")
col = client.get_collection("maitri_krishi_kb")
chunk_count = col.count()

kb_dir = "backend/knowledge_base"
md_files = [f for f in glob.glob(f"{kb_dir}/**/*.md", recursive=True) if "_meta" not in f]
json_regs = [f for f in glob.glob(f"{kb_dir}/**/*.json", recursive=True) if "_meta" not in f]

doc_ids = set()
for f in md_files:
    with open(f, "r", encoding="utf-8") as fp:
        m = re.search(r'doc_id:\s*["\']?([^"\n\r\']+)["\']?', fp.read())
        if m:
            doc_ids.add(m.group(1).strip())

report["checks"]["corpus_integrity"] = {
    "markdown_docs_count": len(md_files),
    "json_registries_count": len(json_regs),
    "unique_doc_ids_count": len(doc_ids),
    "chromadb_chunks_count": chunk_count,
    "status": "PASSED" if len(md_files) == 62 and len(json_regs) == 6 and len(doc_ids) == 62 and chunk_count == 559 else "FAILED"
}
print(f"MD: {len(md_files)}/62 | JSON: {len(json_regs)}/6 | Doc IDs: {len(doc_ids)}/62 | Chunks: {chunk_count}/559")

# 3. Frontend Build Status
print("\n--- 3. Checking Frontend Build Artifacts ---")
dist_index = os.path.exists("frontend/dist/index.html")
report["checks"]["frontend_build"] = {
    "dist_index_html_exists": dist_index,
    "status": "PASSED" if dist_index else "FAILED"
}
print(f"Frontend dist/index.html exists: {dist_index}")

# 4. Multi-turn and Resilience Scripts Verification
print("\n--- 4. Multi-Turn & Resilience Verification ---")
res_mt = subprocess.run([sys.executable, "backend/scripts/verify_stage6_multiturn.py"], capture_output=True, text=True, encoding="utf-8")
report["checks"]["multiturn_context"] = {
    "status": "PASSED" if res_mt.returncode == 0 else "FAILED",
    "exit_code": res_mt.returncode
}

res_res = subprocess.run([sys.executable, "backend/scripts/verify_stage8_resilience.py"], capture_output=True, text=True, encoding="utf-8")
report["checks"]["security_resilience"] = {
    "status": "PASSED" if res_res.returncode == 0 else "FAILED",
    "exit_code": res_res.returncode
}
print(f"Multi-turn: {report['checks']['multiturn_context']['status']} | Resilience: {report['checks']['security_resilience']['status']}")

# Overall
total_duration = time.time() - t_start
all_passed = all(c.get("status") == "PASSED" for c in report["checks"].values())
report["status"] = "ALL_CHECKS_PASSED" if all_passed else "FAILED"
report["total_runtime_seconds"] = round(total_duration, 2)

out_file = "backend/knowledge_base/_meta/final_automated_regression_result.json"
with open(out_file, "w", encoding="utf-8") as f:
    json.dump(report, f, indent=2)

print(f"\nFINAL AUTOMATED REGRESSION: {report['status']} in {total_duration:.2f}s")
assert all_passed, "Some checks failed in final automated regression"
