"""
production_security_audit.py
-----------------------------
Automated static security compliance scanner for MAITRI backend.
Scans all routes, services, and models for security vulnerabilities:
- Unverified JWT claims (get_unverified_claims, verify=False)
- Weak / hardcoded secrets
- Service role fallback from anon client
- Unsafe eval/exec usage
- Raw SQL string formatting/interpolation
"""

import os
import re
import json
from pathlib import Path

BACKEND_APP_DIR = Path(__file__).resolve().parent.parent / "app"

PATTERNS = {
    "unverified_jwt_claims": re.compile(r"get_unverified_claims|verify\s*=\s*False|verify_signature\s*=\s*False"),
    "hardcoded_secrets": re.compile(r"""SECRET_KEY\s*=\s*["'][^"']{1,20}["']"""),
    "anon_to_service_role_fallback": re.compile(r"get_supabase_anon_client\(\)\s*or\s*get_supabase_admin_client\(\)"),
    "unsafe_eval_exec": re.compile(r"\b(eval|exec)\s*\("),
    "sql_string_interpolation": re.compile(r"""execute\s*\(\s*f["'].*SELECT|execute\s*\(\s*["'].*%s.*["']\s*%\s*"""),
}


def scan_codebase():
    results = {
        "scanned_directory": str(BACKEND_APP_DIR),
        "files_scanned": 0,
        "findings": [],
        "summary": {
            "p0_count": 0,
            "p1_count": 0,
            "p2_count": 0
        }
    }

    for py_file in BACKEND_APP_DIR.rglob("*.py"):
        if "__pycache__" in str(py_file):
            continue
        results["files_scanned"] += 1
        rel_path = py_file.relative_to(BACKEND_APP_DIR.parent).as_posix()
        try:
            content = py_file.read_text(encoding="utf-8")
        except Exception:
            continue

        for pattern_name, regex in PATTERNS.items():
            for line_no, line in enumerate(content.splitlines(), start=1):
                if regex.search(line):
                    stripped = line.strip()
                    if stripped.startswith("#") or "test" in rel_path.lower():
                        continue
                    severity = "P0" if "jwt" in pattern_name or "secret" in pattern_name else "P1"
                    if severity == "P0":
                        results["summary"]["p0_count"] += 1
                    else:
                        results["summary"]["p1_count"] += 1

                    results["findings"].append({
                        "file": rel_path,
                        "line": line_no,
                        "pattern": pattern_name,
                        "code": stripped[:120],
                        "severity": severity
                    })

    print(f"Scanned {results['files_scanned']} backend files.")
    print(f"P0 issues: {results['summary']['p0_count']}")
    print(f"P1 issues: {results['summary']['p1_count']}")
    return results


if __name__ == "__main__":
    scan_codebase()
