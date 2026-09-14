"""
Maitri Krishi Assistant - Frontmatter Standardization Script
Audits and standardizes metadata across all knowledge base markdown files.
Preserves exact body text and ensures honest source attribution.
"""

import os
import glob
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
KB_DIR = BASE_DIR / "knowledge_base"

OFFICIAL_MAP = {
    "pm_kisan_scheme.md": {
        "source_type": "official_verified",
        "source": "Ministry of Agriculture & Farmers Welfare, Government of India",
        "url": "https://pmkisan.gov.in",
        "version": "Operational Guidelines & Portal Status 2024",
        "verified": True
    },
    "pmfby_crop_insurance.md": {
        "source_type": "official_verified",
        "source": "Ministry of Agriculture & Farmers Welfare, Government of India",
        "url": "https://pmfby.gov.in",
        "version": "Revised Operational Guidelines PMFBY",
        "verified": True
    },
    "kcc_kisan_credit_card.md": {
        "source_type": "official_verified",
        "source": "NABARD & Reserve Bank of India",
        "url": "https://www.nabard.org",
        "version": "Master Circular - Kisan Credit Card",
        "verified": True
    },
    "soil_health_card.md": {
        "source_type": "official_verified",
        "source": "Ministry of Agriculture & Farmers Welfare, Government of India",
        "url": "https://soilhealth.dac.gov.in",
        "version": "Soil Health Card Scheme Guidelines",
        "verified": True
    },
    "micro_irrigation_drip.md": {
        "source_type": "official_verified",
        "source": "Department of Agriculture & Farmers Welfare, PMKSY",
        "url": "https://pmksy.gov.in",
        "version": "PMKSY-PDMC Guidelines",
        "verified": True
    }
}


def standardize_frontmatter():
    count = 0
    for fpath in sorted(KB_DIR.rglob("*.md")):
        with open(fpath, "r", encoding="utf-8") as fp:
            content = fp.read()

        fname = fpath.name
        body = content
        old_fm = {}

        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                fm_text = parts[1]
                body = parts[2].strip()
                for line in fm_text.strip().splitlines():
                    if ":" in line:
                        k, v = line.split(":", 1)
                        old_fm[k.strip().lower()] = v.strip().strip("\"'")

        title = old_fm.get("title", fname.replace(".md", "").replace("_", " ").title())
        category = old_fm.get("category", fpath.parent.name.capitalize())
        crop = old_fm.get("crop", "General")
        keywords_hi = old_fm.get("keywords_hi", "")
        old_source = old_fm.get("source", "")

        if fname in OFFICIAL_MAP:
            info = OFFICIAL_MAP[fname]
            new_fm = {
                "title": title,
                "source_type": "official_verified",
                "source": info["source"],
                "url": info["url"],
                "version": info["version"],
                "category": category,
                "crop": crop,
                "verified": True,
                "keywords_hi": keywords_hi
            }
        else:
            new_fm = {
                "title": title,
                "source_type": "curated_reference",
                "source": "Maitri Agronomy Reference Desk",
                "reference_basis": f"Standard Agricultural Practice ({old_source})" if old_source else "Standard Agronomic Package of Practices",
                "url": "",
                "version": "2024.1",
                "category": category,
                "crop": crop,
                "verified": False,
                "keywords_hi": keywords_hi
            }

        # Build clean YAML frontmatter
        fm_lines = ["---"]
        for k, v in new_fm.items():
            if isinstance(v, bool):
                fm_lines.append(f"{k}: {str(v).lower()}")
            elif isinstance(v, (int, float)):
                fm_lines.append(f"{k}: {v}")
            else:
                escaped_v = str(v).replace('"', '\\"')
                if any(c in escaped_v for c in [':', '{', '}', '[', ']', ',', '&', '*', '#', '?', '|', '-', '<', '>', '=', '!', '%', '@', '\\']):
                    fm_lines.append(f'{k}: "{escaped_v}"')
                else:
                    fm_lines.append(f"{k}: {escaped_v}")
        fm_lines.append("---")

        new_content = "\n".join(fm_lines) + "\n\n" + body + "\n"
        with open(fpath, "w", encoding="utf-8") as fp:
            fp.write(new_content)
        count += 1
        print(f"Updated: {fname} -> source_type: {new_fm['source_type']} | source: {new_fm['source']}")

    print(f"\nSuccessfully standardized frontmatter for {count} documents.")


if __name__ == "__main__":
    standardize_frontmatter()
