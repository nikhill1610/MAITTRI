"""
Maitri Krishi Assistant - Knowledge Base Ingestion Pipeline
------------------------------------------------------------
Ingests structured Markdown, TXT, PDF, and JSON documents from backend/knowledge_base/
into a persistent ChromaDB vector store located at backend/vector_store/.

Phase 4 Enhancements:
- Rigorous source integrity: tracks source_type (official_verified, curated_reference, general_reference).
- Preserves URLs, versions/dates, and page numbers (for PDFs).
- Semantic section-aware chunking preserving:
  Symptoms, Causes, Identification, Prevention, Irrigation, Nutrient management,
  Pest management, Disease management, Harvesting, Safety.
- PDF ingestion support using pypdf.
- Rich chunk metadata and clean multilingual anchor headers.
- CLI commands: --rebuild, --inspect, --query "sample question"
"""

import os
import re
import sys
import json
import argparse
from pathlib import Path
from typing import List, Dict, Any, Tuple

# Add backend directory to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

try:
    import chromadb
    from chromadb.config import Settings
except ImportError:
    print("Error: chromadb is not installed. Run: pip install chromadb")
    sys.exit(1)

KB_DIR = BASE_DIR / "knowledge_base"
VECTOR_STORE_DIR = BASE_DIR / "vector_store"
COLLECTION_NAME = "maitri_krishi_kb"

# Standard Agricultural Section Classifications
SECTION_TYPE_PATTERNS = [
    ("Symptoms & Identification", r"symptom|identification|visual|पहचान|लक्षण|नुकसान|damage|appearance"),
    ("Causes & Etiology", r"cause|etiology|biology|pathogen|कारक|कारण|life cycle"),
    ("Irrigation & Water Management", r"irrigation|water|moisture|awd|drip|sprinkler|सिंचाई|पानी|जल|नमी"),
    ("Nutrient Management & Fertilizers", r"nutrient|fertilizer|urea|dap|mop|zinc|nitrogen|phosphorus|potassium|खाद|उर्वरक|पोषक|खुराक"),
    ("Pest Management", r"pest|insect|borer|armyworm|aphid|whitefly|caterpillar|कीट|कीड़ा|सुंडी|माहू|मक्खी"),
    ("Disease Management", r"disease|rust|blight|blast|fungus|fungal|virus|रोग|रतुआ|झुलसा|ब्लास्ट|फफूंद"),
    ("Prevention & Cultural Practices", r"prevention|cultural|sanitation|trap|ipm|रोकथाम|बचाव|सावधानी|नियंत्रण"),
    ("Harvesting & Yield", r"harvest|yield|storage|maturity|कटाई|पैदावार|उपज"),
    ("Safety & Expert Advisory", r"safety|precaution|expert|kvk|advisory|सावधानी|सलाह|चेतावनी|विशेषज्ञ"),
    ("Eligibility & Scheme Benefits", r"eligibility|benefit|installment|claim|exclusion|आवेदन|पात्रता|लाभ|किस्त|मुआवजा")
]


def classify_section_type(text: str) -> str:
    """Classifies section into standard agricultural agronomy categories."""
    t_lower = text.lower()
    for category_name, pattern in SECTION_TYPE_PATTERNS:
        if re.search(pattern, t_lower):
            return category_name
    return "General Agronomic Advisory"


def parse_frontmatter(content: str) -> Tuple[Dict[str, Any], str]:
    """Extracts YAML frontmatter between --- markers if present."""
    metadata = {}
    body = content
    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            fm_text = parts[1]
            body = parts[2].strip()
            for line in fm_text.strip().splitlines():
                if ":" in line:
                    k, v = line.split(":", 1)
                    k = k.strip().lower()
                    v = v.strip().strip("\"'")
                    if v.lower() == "true":
                        metadata[k] = True
                    elif v.lower() == "false":
                        metadata[k] = False
                    else:
                        metadata[k] = v
    return metadata, body


def chunk_markdown_document(file_path: Path) -> List[Dict[str, Any]]:
    """
    Parses a markdown document into meaningful section-level chunks with rich metadata.
    Preserves symptoms, causes, irrigation, nutrients, and pest/disease management blocks.
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            raw_text = f.read()
    except Exception as e:
        print(f"Failed to read {file_path}: {e}")
        return []

    fm, body = parse_frontmatter(raw_text)
    doc_title = fm.get("title") or file_path.stem.replace("_", " ").title()
    doc_source = fm.get("source") or "Maitri Agronomy Reference Desk"
    doc_source_type = fm.get("source_type") or ("official_verified" if fm.get("verified") else "curated_reference")
    doc_url = fm.get("url") or ""
    doc_version = fm.get("version") or "2024.1"
    doc_category = fm.get("category") or file_path.parent.name.capitalize()
    doc_crop = fm.get("crop") or "General"
    keywords_hi = fm.get("keywords_hi") or ""
    verified = bool(fm.get("verified", doc_source_type == "official_verified"))

    # Split on markdown headings: prefer level 2 (##) to keep subsections intact with parent
    if re.search(r"\n##\s+", body):
        sections = re.split(r"\n(?=##\s+)", body)
    else:
        sections = re.split(r"\n(?=#{1,3}\s+)", body)

    chunks = []
    chunk_idx = 0

    for sec in sections:
        sec = sec.strip()
        if not sec or len(sec) < 50:
            continue
        # Skip isolated title without body
        if sec.startswith("# ") and "\n" not in sec:
            continue

        # Extract section heading
        heading_match = re.match(r"^#{1,3}\s+(.+)", sec)
        heading = heading_match.group(1).strip() if heading_match else f"Section {chunk_idx+1}"

        # Classify the section type
        sec_type = classify_section_type(heading + "\n" + sec[:250])

        # Clean markdown text
        clean_text = re.sub(r"\n{3,}", "\n\n", sec)

        chunk_idx += 1
        # Build multilingual anchor header
        anchor_header = (
            f"[Source: {doc_source} ({doc_source_type}) | Category: {doc_category} | Crop: {doc_crop} | "
            f"Topic: {doc_title} - {heading} ({sec_type}) | Keywords: {keywords_hi}]\n"
        )
        full_chunk_text = anchor_header + clean_text

        chunk_id = f"{file_path.stem}_sec_{chunk_idx}"
        try:
            rel_source_file = str(file_path.resolve().relative_to(BASE_DIR.resolve()))
        except Exception:
            rel_source_file = str(file_path.name)

        chunks.append({
            "id": chunk_id,
            "text": full_chunk_text,
            "metadata": {
                "title": doc_title,
                "section": heading,
                "section_type": sec_type,
                "source": doc_source,
                "source_type": doc_source_type,
                "url": doc_url,
                "version": str(doc_version),
                "category": doc_category,
                "crop": doc_crop,
                "source_file": rel_source_file,
                "page_number": 1,
                "verified": verified
            }
        })

    return chunks


def chunk_pdf_document(file_path: Path) -> List[Dict[str, Any]]:
    """
    Ingests official agricultural PDFs page by page, preserving page numbers,
    titles, and structural chunks.
    """
    try:
        import pypdf
        reader = pypdf.PdfReader(str(file_path))
    except ImportError:
        print(f"pypdf is not installed. Skipping PDF: {file_path}")
        return []
    except Exception as e:
        print(f"Failed to read PDF {file_path}: {e}")
        return []

    doc_title = file_path.stem.replace("_", " ").title()
    doc_source = "Official Agricultural Publication"
    doc_source_type = "official_verified"
    doc_category = file_path.parent.name.capitalize()
    doc_crop = "General"
    chunks = []

    for page_num, page in enumerate(reader.pages, start=1):
        page_text = page.extract_text() or ""
        page_text = page_text.strip()
        if len(page_text) < 50:
            continue

        # Split on paragraph blocks
        sub_sections = re.split(r"\n(?=[A-Z0-9\.\-\s]{4,35}\n)", page_text)
        for s_idx, sec in enumerate(sub_sections):
            sec = sec.strip()
            if len(sec) < 40:
                continue
            heading = f"Page {page_num} - Part {s_idx + 1}"
            sec_type = classify_section_type(heading + "\n" + sec)
            chunk_id = f"{file_path.stem}_p{page_num}_sec{s_idx + 1}"
            anchor_header = (
                f"[Source: {doc_source} ({doc_source_type}) | Category: {doc_category} | Crop: {doc_crop} | "
                f"Section: {heading} ({sec_type}) | Page: {page_num}]\n"
            )
            chunks.append({
                "id": chunk_id,
                "text": anchor_header + sec,
                "metadata": {
                    "title": doc_title,
                    "section": heading,
                    "section_type": sec_type,
                    "source": doc_source,
                    "source_type": doc_source_type,
                    "url": "",
                    "version": "Official PDF",
                    "category": doc_category,
                    "crop": doc_crop,
                    "source_file": str(file_path.resolve().relative_to(BASE_DIR.resolve())),
                    "page_number": page_num,
                    "verified": True
                }
            })

    return chunks


def chunk_json_document(file_path: Path) -> List[Dict[str, Any]]:
    """Chunks JSON knowledge base files into discrete structured records."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"Failed to read JSON {file_path}: {e}")
        return []

    if isinstance(data, dict):
        items = [data]
    elif isinstance(data, list):
        items = data
    else:
        return []

    chunks = []
    category = file_path.parent.name.capitalize()
    source = "Maitri Agricultural Reference Database"
    source_type = "general_reference"

    for idx, item in enumerate(items):
        title = item.get("crop") or item.get("name") or item.get("scheme") or item.get("topic") or file_path.stem
        crop = item.get("crop") or ("Rice" if "rice" in str(item).lower() else "General")
        
        # Serialize dict to readable text
        lines = [f"{k.replace('_', ' ').title()}: {v}" for k, v in item.items() if v]
        item_text = "\n".join(lines)
        sec_type = classify_section_type(str(title) + "\n" + item_text)
        anchor_header = f"[Source: {source} ({source_type}) | Category: {category} | Crop: {crop} | Title: {title} ({sec_type})]\n"
        full_chunk = anchor_header + item_text

        chunks.append({
            "id": f"{file_path.stem}_item_{idx+1}",
            "text": full_chunk,
            "metadata": {
                "title": str(title),
                "section": str(title),
                "section_type": sec_type,
                "source": source,
                "source_type": source_type,
                "url": "",
                "version": "2024.1",
                "category": category,
                "crop": str(crop),
                "source_file": str(file_path.resolve().relative_to(BASE_DIR.resolve())),
                "page_number": 1,
                "verified": False
            }
        })

    return chunks


def collect_all_chunks() -> List[Dict[str, Any]]:
    """Traverses knowledge_base directory and collects all chunks from MD, TXT, PDF, and JSON."""
    if not KB_DIR.exists():
        print(f"Error: Knowledge base directory {KB_DIR} does not exist.")
        return []

    all_chunks = []
    # Markdown files
    for md_file in sorted(KB_DIR.rglob("*.md")):
        all_chunks.extend(chunk_markdown_document(md_file))

    # Plain text files
    for txt_file in sorted(KB_DIR.rglob("*.txt")):
        all_chunks.extend(chunk_markdown_document(txt_file))

    # Official PDF files
    for pdf_file in sorted(KB_DIR.rglob("*.pdf")):
        all_chunks.extend(chunk_pdf_document(pdf_file))

    # JSON database files
    for json_file in sorted(KB_DIR.rglob("*.json")):
        all_chunks.extend(chunk_json_document(json_file))

    return all_chunks


def build_vector_database(rebuild: bool = False):
    """Initializes ChromaDB persistent store and inserts all knowledge chunks."""
    VECTOR_STORE_DIR.mkdir(parents=True, exist_ok=True)

    print(f"Connecting to ChromaDB persistent vector store at: {VECTOR_STORE_DIR}")
    client = chromadb.PersistentClient(path=str(VECTOR_STORE_DIR))

    if rebuild:
        try:
            print(f"Rebuilding: Deleting existing collection '{COLLECTION_NAME}'...")
            client.delete_collection(COLLECTION_NAME)
        except Exception:
            pass

    collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"description": "Maitri Krishi Assistant Agriculture Knowledge Base (Phase 4)"}
    )

    chunks = collect_all_chunks()
    if not chunks:
        print("No documents found to ingest.")
        return collection

    print(f"Collected {len(chunks)} total knowledge chunks from {KB_DIR}")

    ids = [c["id"] for c in chunks]
    docs = [c["text"] for c in chunks]
    metas = [c["metadata"] for c in chunks]

    # Ingest in batches of 50
    batch_size = 50
    for i in range(0, len(ids), batch_size):
        b_ids = ids[i:i+batch_size]
        b_docs = docs[i:i+batch_size]
        b_metas = metas[i:i+batch_size]
        collection.upsert(ids=b_ids, documents=b_docs, metadatas=b_metas)
        print(f"Ingested batch {i // batch_size + 1}/{(len(ids)-1) // batch_size + 1} ({len(b_ids)} chunks)")

    total_count = collection.count()
    print(f"\nSuccessfully stored {total_count} chunks in ChromaDB collection '{COLLECTION_NAME}'!")
    return collection


def inspect_collection():
    """Prints stats and sample chunks from the vector database."""
    if not VECTOR_STORE_DIR.exists():
        print("Vector store does not exist. Run with --rebuild first.")
        return

    client = chromadb.PersistentClient(path=str(VECTOR_STORE_DIR))
    collection = client.get_collection(COLLECTION_NAME)
    count = collection.count()
    print(f"Collection '{COLLECTION_NAME}' contains {count} items.")

    sample = collection.peek(limit=5)
    print("\n--- Sample Document Metadata (Phase 4) ---")
    for idx, (cid, meta) in enumerate(zip(sample.get("ids", []), sample.get("metadatas", []))):
        print(
            f"[{idx+1}] ID: {cid}\n"
            f"    Title: {meta.get('title')}\n"
            f"    Source: {meta.get('source')} ({meta.get('source_type')})\n"
            f"    Crop: {meta.get('crop')} | Category: {meta.get('category')}\n"
            f"    Section: {meta.get('section')} [{meta.get('section_type')}]\n"
            f"    URL: {meta.get('url') or 'N/A'}\n"
        )


def query_collection(query_text: str, top_k: int = 3):
    """Runs a test query on the collection and displays similarity distances."""
    client = chromadb.PersistentClient(path=str(VECTOR_STORE_DIR))
    collection = client.get_collection(COLLECTION_NAME)
    results = collection.query(query_texts=[query_text], n_results=top_k)

    print(f"\nQuery: '{query_text}'")
    print(f"Found {len(results.get('documents', [[]])[0])} results:")
    for idx, (doc, meta, dist) in enumerate(zip(
        results.get("documents", [[]])[0],
        results.get("metadatas", [[]])[0],
        results.get("distances", [[]])[0]
    )):
        sim = max(0.0, 1.0 - (dist / 2.0))
        print(f"\nResult #{idx+1} (Distance: {dist:.4f} | Similarity: {sim:.4f})")
        print(f"  Source: {meta.get('source')} ({meta.get('source_type')})")
        print(f"  Title: {meta.get('title')} | Section: {meta.get('section')} [{meta.get('section_type')}]")
        print(f"  Snippet: {doc[:180]}...")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Maitri Agriculture Knowledge Ingestion Pipeline")
    parser.add_argument("--rebuild", action="store_true", help="Rebuild the vector store from scratch")
    parser.add_argument("--inspect", action="store_true", help="Inspect collection count and sample documents")
    parser.add_argument("--query", type=str, help="Run a test query against the vector store")

    args = parser.parse_args()

    if args.query:
        query_collection(args.query)
    elif args.inspect:
        inspect_collection()
    else:
        build_vector_database(rebuild=args.rebuild or True)
