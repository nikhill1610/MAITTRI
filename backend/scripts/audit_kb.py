import os
import json
import re
from pathlib import Path

KB_DIR = Path(__file__).resolve().parent.parent / "knowledge_base"

inventory = []

def parse_frontmatter(content):
    fm = {}
    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            for line in parts[1].strip().splitlines():
                if ":" in line:
                    k, v = line.split(":", 1)
                    fm[k.strip().lower()] = v.strip()
    return fm

def run_audit():
    for f in sorted(KB_DIR.rglob("*")):
        if f.is_file():
            rel_path = str(f.relative_to(KB_DIR))
            ext = f.suffix.lower()
            if ext == ".md":
                with open(f, "r", encoding="utf-8") as fp:
                    text = fp.read()
                fm = parse_frontmatter(text)
                inventory.append({
                    "file": rel_path,
                    "type": "markdown",
                    "title": fm.get("title", f.stem.replace("_", " ").title()),
                    "source": fm.get("source", "Curated Reference"),
                    "crop": fm.get("crop", "General"),
                    "category": fm.get("category", f.parent.name.capitalize()),
                    "url": fm.get("url", ""),
                    "verified": fm.get("verified", "false"),
                    "doc_type": "official_verified" if "pmkisan" in text or "pmfby" in text or "soilhealth" in text else "curated_reference"
                })
            elif ext == ".json":
                with open(f, "r", encoding="utf-8") as fp:
                    try:
                        data = json.load(fp)
                        count = len(data) if isinstance(data, list) else 1
                    except Exception:
                        count = 0
                inventory.append({
                    "file": rel_path,
                    "type": "json",
                    "title": f"{f.stem.replace('_', ' ').title()} Database ({count} records)",
                    "source": "Pre-packaged Dataset",
                    "crop": "General",
                    "category": f.parent.name.capitalize(),
                    "url": "",
                    "verified": "true",
                    "doc_type": "official_verified"
                })

    print(f"Total knowledge base files audited: {len(inventory)}")
    return inventory

if __name__ == "__main__":
    run_audit()
