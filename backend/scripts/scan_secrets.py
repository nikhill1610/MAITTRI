"""
scan_secrets.py
---------------
Scans tracked Git files and repository source trees for potential secrets, credentials,
database dumps, and unprotected keys.
"""

import os
import re
import subprocess
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent.parent

PATTERNS = {
    "openrouter_key": re.compile(r"sk-or-v1-[a-f0-9]{64}"),
    "jwt_secret": re.compile(r"""SECRET_KEY\s*=\s*["'](?!(?:change-this|your-secret|dev-secret))([A-Za-z0-9_\-]{32,})["']"""),
    "supabase_service_role": re.compile(r"""SUPABASE_SERVICE_ROLE_KEY\s*=\s*["'](?!(?:your-supabase|change-this))([A-Za-z0-9_\-\.]{50,})["']"""),
    "postgres_password_uri": re.compile(r"""postgresql://[^:]+:(?!(?:your-password|password|\[password\]|\${))([^@]+)@"""),
    "private_key_header": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
}

EXCLUDED_DIRS = {".git", "venv", ".venv", "node_modules", "dist", "backups", "scratch"}


def scan_repo():
    print(f"Scanning repository at: {ROOT_DIR}")
    
    # 1. Check Git tracked files specifically
    out = subprocess.check_output(["git", "ls-files"], cwd=str(ROOT_DIR), text=True)
    tracked_files = [line.strip() for line in out.splitlines() if line.strip()]
    
    findings = []
    
    for rel_path in tracked_files:
        full_path = ROOT_DIR / rel_path
        if not full_path.is_file():
            continue
        
        # Check forbidden tracked file extensions
        if rel_path.endswith((".sqlite", ".db", ".sqlite3", ".log", ".pem", ".key")):
            findings.append((rel_path, 0, "forbidden_file_extension", f"Tracked file has sensitive extension: {rel_path}"))
            continue
        
        if ".env" in full_path.name and not full_path.name.endswith(".example"):
            findings.append((rel_path, 0, "tracked_env_file", f"Tracked .env file: {rel_path}"))
            continue
            
        if rel_path.endswith("scan_secrets.py"):
            continue
        
        try:
            content = full_path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
            
        for pat_name, pat in PATTERNS.items():
            for line_no, line in enumerate(content.splitlines(), start=1):
                if pat.search(line):
                    findings.append((rel_path, line_no, pat_name, line.strip()[:100]))
                    
    print(f"Tracked files scanned: {len(tracked_files)}")
    print(f"Tracked secret findings: {len(findings)}")
    for f in findings:
        print(f"  [ALERT] {f[0]}:{f[1]} - {f[2]} -> {f[3]}")
        
    return len(findings) == 0


if __name__ == "__main__":
    success = scan_repo()
    exit(0 if success else 1)
