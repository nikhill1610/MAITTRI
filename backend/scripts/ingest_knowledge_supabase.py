"""
MAITRI Smart Agriculture AI Platform — Knowledge Ingestion Pipeline for Supabase pgvector
------------------------------------------------------------------------------------------
Ingests Markdown, TXT, PDF, and JSON knowledge assets from backend/knowledge_base/
into Supabase PostgreSQL enterprise tables:
  - public.knowledge_documents (with SHA-256 checksum deduplication)
  - public.knowledge_chunks (with 384-dimensional pgvector embeddings & HNSW indexing)

Preserves rich agronomic metadata:
  - title, source, source_type, source_url, organization, category, crop, region,
    language, section_title, section_type, page_number, version, metadata JSONB

Uses official all-MiniLM-L6-v2 embedding model (dimension: exactly 384).
"""

import os
import re
import sys
import json
import hashlib
import argparse
import logging
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional
from datetime import datetime, timezone
from dotenv import load_dotenv

# Path configuration
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

load_dotenv(BASE_DIR / ".env")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s"
)
logger = logging.getLogger("maitri.ingest_supabase")

KB_DIR = BASE_DIR / "knowledge_base"

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
    ("Eligibility & Scheme Benefits", r"eligibility|benefit|installment|claim|exclusion|आवेदन|पात्रता|लाभ|किस्त|मुआवजा"),
    ("Mountain & Hill Farming", r"mountain|hill|terrace|pahadi|pahaad|पहाड़ी|सीढ़ीनुमा|समोच्च|ऊँचाई|altitude")
]


def classify_section_type(text: str) -> str:
    """Classifies section text into standardized agronomic categories."""
    t_lower = text.lower()
    for category_name, pattern in SECTION_TYPE_PATTERNS:
        if re.search(pattern, t_lower):
            return category_name
    return "General Agronomic Advisory"


def compute_sha256(data: bytes) -> str:
    """Calculates SHA-256 hex digest for document deduplication."""
    return hashlib.sha256(data).hexdigest()


def parse_frontmatter(content: str) -> Tuple[Dict[str, Any], str]:
    """Extracts YAML-style frontmatter headers if present."""
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


def get_embedding_function():
    """Returns official all-MiniLM-L6-v2 embedding model function (384-d)."""
    import chromadb.utils.embedding_functions as ef
    return ef.DefaultEmbeddingFunction()


# -----------------------------------------------------------------------------
# Document Chunking Functions
# -----------------------------------------------------------------------------

def chunk_markdown_document(file_path: Path, raw_bytes: bytes) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    """
    Parses Markdown/TXT documents into structured document metadata and section chunks.
    Preserves symptoms, causes, irrigation, nutrients, and pest/disease blocks.
    """
    raw_text = raw_bytes.decode("utf-8", errors="replace")
    fm, body = parse_frontmatter(raw_text)

    # Document-level attributes
    title = fm.get("title") or file_path.stem.replace("_", " ").title()
    source = fm.get("source") or "Maitri Agronomy Reference Desk"
    source_type = fm.get("source_type") or ("official_verified" if fm.get("verified") else "curated_reference")
    if source_type not in ("official_verified", "curated_reference", "general_reference"):
        source_type = "curated_reference"
    source_url = fm.get("url") or ""
    category = fm.get("category") or file_path.parent.name.replace("_", " ").title()
    crop = fm.get("crop") or "General"
    version = str(fm.get("version") or "2024.1")
    is_verified = bool(fm.get("verified", source_type == "official_verified"))
    keywords_hi = fm.get("keywords_hi") or ""
    organization = fm.get("organization") or fm.get("reference_basis") or "ICAR / Agricultural Universities"
    region = fm.get("region") or ("Himalayan & Hill Regions" if "mountain" in file_path.stem.lower() else "National / All India")
    language = "hi" if re.search(r"[\u0900-\u097F]", raw_text[:500]) else "en"

    rel_file = str(file_path.resolve().relative_to(BASE_DIR.resolve()))

    doc_meta = {
        "title": title[:255],
        "source": source[:255],
        "source_type": source_type,
        "source_url": source_url,
        "document_type": "markdown" if file_path.suffix == ".md" else "txt",
        "language": language,
        "category": category[:80],
        "crop": crop[:80],
        "version": version[:50],
        "file_path": rel_file,
        "checksum": compute_sha256(raw_bytes),
        "is_public": True,
        "is_verified": is_verified,
        "access_level": "public",
        "metadata": {
            "organization": organization,
            "region": region,
            "keywords_hi": keywords_hi,
            "reference_basis": fm.get("reference_basis", "")
        }
    }

    # Split into sections based on headings
    if re.search(r"\n##\s+", body):
        raw_sections = re.split(r"\n(?=##\s+)", body)
    else:
        raw_sections = re.split(r"\n(?=#{1,3}\s+)", body)

    chunks = []
    chunk_idx = 0

    for sec in raw_sections:
        sec = sec.strip()
        if not sec or len(sec) < 40:
            continue
        if sec.startswith("# ") and "\n" not in sec:
            continue

        heading_match = re.match(r"^#{1,3}\s+(.+)", sec)
        heading = heading_match.group(1).strip() if heading_match else f"Section {chunk_idx + 1}"
        sec_type = classify_section_type(heading + "\n" + sec[:300])

        clean_text = re.sub(r"\n{3,}", "\n\n", sec)
        chunk_idx += 1

        anchor_header = (
            f"[Source: {source} ({source_type}) | Category: {category} | Crop: {crop} | "
            f"Topic: {title} - {heading} ({sec_type}) | Keywords: {keywords_hi}]\n"
        )
        full_chunk_text = anchor_header + clean_text
        chunk_id_str = f"{file_path.stem.lower()}_sec_{chunk_idx}"

        chunks.append({
            "chunk_id_str": chunk_id_str[:120],
            "chunk_index": chunk_idx,
            "section_title": heading[:255],
            "section_type": sec_type[:100],
            "page_number": 1,
            "content": full_chunk_text,
            "metadata": {
                "title": title,
                "section": heading,
                "section_type": sec_type,
                "crop": crop,
                "category": category,
                "source": source,
                "source_type": source_type,
                "organization": organization,
                "region": region,
                "language": language
            }
        })

    return doc_meta, chunks


def chunk_pdf_document(file_path: Path, raw_bytes: bytes) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    """Extracts text from PDF page-by-page preserving page numbers and sections."""
    import pypdf
    import io

    reader = pypdf.PdfReader(io.BytesIO(raw_bytes))
    title = file_path.stem.replace("_", " ").title()
    source = "Official Agricultural Publication"
    source_type = "official_verified"
    category = file_path.parent.name.replace("_", " ").title()
    crop = "General"
    rel_file = str(file_path.resolve().relative_to(BASE_DIR.resolve()))

    doc_meta = {
        "title": title[:255],
        "source": source[:255],
        "source_type": source_type,
        "source_url": "",
        "document_type": "pdf",
        "language": "hi",
        "category": category[:80],
        "crop": crop[:80],
        "version": "Official PDF",
        "file_path": rel_file,
        "checksum": compute_sha256(raw_bytes),
        "is_public": True,
        "is_verified": True,
        "access_level": "public",
        "metadata": {
            "organization": "ICAR / State Agricultural Department",
            "page_count": len(reader.pages)
        }
    }

    chunks = []
    chunk_idx = 0

    for page_num, page in enumerate(reader.pages, start=1):
        page_text = (page.extract_text() or "").strip()
        if len(page_text) < 40:
            continue

        sub_sections = re.split(r"\n(?=[A-Z0-9\.\-\s]{4,35}\n)", page_text)
        for s_idx, sec in enumerate(sub_sections):
            sec = sec.strip()
            if len(sec) < 40:
                continue

            chunk_idx += 1
            heading = f"Page {page_num} - Part {s_idx + 1}"
            sec_type = classify_section_type(heading + "\n" + sec)
            chunk_id_str = f"{file_path.stem.lower()}_p{page_num}_s{s_idx + 1}"

            anchor_header = (
                f"[Source: {source} ({source_type}) | Category: {category} | Crop: {crop} | "
                f"Section: {heading} ({sec_type}) | Page: {page_num}]\n"
            )

            chunks.append({
                "chunk_id_str": chunk_id_str[:120],
                "chunk_index": chunk_idx,
                "section_title": heading[:255],
                "section_type": sec_type[:100],
                "page_number": page_num,
                "content": anchor_header + sec,
                "metadata": {
                    "title": title,
                    "section": heading,
                    "section_type": sec_type,
                    "crop": crop,
                    "category": category,
                    "source": source,
                    "source_type": source_type,
                    "page_number": page_num
                }
            })

    return doc_meta, chunks


def chunk_json_document(file_path: Path, raw_bytes: bytes) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    """Chunks JSON structured knowledge tables into discrete records."""
    data = json.loads(raw_bytes.decode("utf-8"))
    items = data if isinstance(data, list) else [data]

    title = file_path.stem.replace("_", " ").title()
    source = "Maitri Agricultural Reference Database"
    source_type = "general_reference"
    category = file_path.parent.name.replace("_", " ").title()
    crop = "General"
    rel_file = str(file_path.resolve().relative_to(BASE_DIR.resolve()))

    doc_meta = {
        "title": title[:255],
        "source": source[:255],
        "source_type": source_type,
        "source_url": "",
        "document_type": "json",
        "language": "hi",
        "category": category[:80],
        "crop": crop[:80],
        "version": "2024.1",
        "file_path": rel_file,
        "checksum": compute_sha256(raw_bytes),
        "is_public": True,
        "is_verified": False,
        "access_level": "public",
        "metadata": {
            "record_count": len(items)
        }
    }

    chunks = []
    for idx, item in enumerate(items):
        item_title = item.get("crop") or item.get("name") or item.get("scheme") or item.get("topic") or file_path.stem
        item_crop = item.get("crop") or ("Rice" if "rice" in str(item).lower() else "General")

        lines = [f"{k.replace('_', ' ').title()}: {v}" for k, v in item.items() if v]
        item_text = "\n".join(lines)
        sec_type = classify_section_type(str(item_title) + "\n" + item_text)
        chunk_id_str = f"{file_path.stem.lower()}_rec_{idx + 1}"

        anchor_header = (
            f"[Source: {source} ({source_type}) | Category: {category} | Crop: {item_crop} | "
            f"Record: {item_title} ({sec_type})]\n"
        )

        chunks.append({
            "chunk_id_str": chunk_id_str[:120],
            "chunk_index": idx + 1,
            "section_title": str(item_title)[:255],
            "section_type": sec_type[:100],
            "page_number": 1,
            "content": anchor_header + item_text,
            "metadata": {
                "title": str(item_title),
                "section": str(item_title),
                "section_type": sec_type,
                "crop": str(item_crop),
                "category": category,
                "source": source,
                "source_type": source_type
            }
        })

    return doc_meta, chunks


# -----------------------------------------------------------------------------
# Core Ingestion Engine
# -----------------------------------------------------------------------------

def run_ingestion(rebuild: bool = False, dry_run: bool = False) -> Dict[str, Any]:
    """
    Executes end-to-end ingestion from backend/knowledge_base/ into Supabase pgvector.
    Reports detailed statistics per Phase 3 specifications.
    """
    import psycopg2
    from psycopg2.extras import RealDictCursor

    db_url = os.getenv("DATABASE_URL", "").strip()
    if not (db_url.startswith("postgresql://") or db_url.startswith("postgres://")):
        raise RuntimeError("DATABASE_URL is not configured for Supabase PostgreSQL. Halting ingestion.")

    stats = {
        "files_discovered": 0,
        "documents_inserted": 0,
        "documents_updated": 0,
        "documents_skipped": 0,
        "chunks_created": 0,
        "embeddings_generated": 0,
        "duplicates_detected": 0,
        "failures": []
    }

    if not KB_DIR.exists():
        logger.error(f"Knowledge base directory does not exist: {KB_DIR}")
        return stats

    # Collect all knowledge files
    file_list = []
    for ext in ("*.md", "*.txt", "*.pdf", "*.json"):
        file_list.extend(sorted(KB_DIR.rglob(ext)))

    stats["files_discovered"] = len(file_list)
    logger.info(f"Discovered {len(file_list)} knowledge files in {KB_DIR}")

    if dry_run:
        logger.info("[DRY RUN] Inspection only. Zero database writes will be executed.")
        return stats

    emb_fn = get_embedding_function()
    conn = psycopg2.connect(dsn=db_url)
    conn.autocommit = False

    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # If rebuild requested, purge existing documents and chunks
            if rebuild:
                logger.warning("Rebuild flag active: Deleting existing knowledge_documents and chunks...")
                cur.execute("DELETE FROM public.knowledge_documents;")
                conn.commit()

            # Load existing documents map {file_path: (id, checksum)}
            cur.execute("SELECT id, file_path, checksum FROM public.knowledge_documents;")
            existing_docs = {r["file_path"]: (r["id"], r["checksum"]) for r in cur.fetchall()}

            for f_idx, file_path in enumerate(file_list, start=1):
                try:
                    with open(file_path, "rb") as f:
                        raw_bytes = f.read()

                    # Chunk document based on extension
                    ext = file_path.suffix.lower()
                    if ext in (".md", ".txt"):
                        doc_meta, chunks = chunk_markdown_document(file_path, raw_bytes)
                    elif ext == ".pdf":
                        doc_meta, chunks = chunk_pdf_document(file_path, raw_bytes)
                    elif ext == ".json":
                        doc_meta, chunks = chunk_json_document(file_path, raw_bytes)
                    else:
                        continue

                    rel_path = doc_meta["file_path"]
                    current_checksum = doc_meta["checksum"]

                    # Deduplication Check
                    doc_id = None
                    if rel_path in existing_docs:
                        existing_id, existing_checksum = existing_docs[rel_path]
                        if existing_checksum == current_checksum and not rebuild:
                            stats["documents_skipped"] += 1
                            stats["duplicates_detected"] += 1
                            continue
                        else:
                            # Content changed: update document & replace chunks
                            doc_id = existing_id
                            cur.execute(
                                """
                                UPDATE public.knowledge_documents SET
                                    title = %(title)s,
                                    source = %(source)s,
                                    source_type = %(source_type)s,
                                    source_url = %(source_url)s,
                                    language = %(language)s,
                                    category = %(category)s,
                                    crop = %(crop)s,
                                    version = %(version)s,
                                    checksum = %(checksum)s,
                                    is_public = %(is_public)s,
                                    is_verified = %(is_verified)s,
                                    access_level = %(access_level)s,
                                    metadata = %(metadata)s,
                                    updated_at = NOW()
                                WHERE id = %(id)s;
                                """,
                                {**doc_meta, "id": doc_id, "metadata": json.dumps(doc_meta["metadata"])}
                            )
                            # Remove old chunks
                            cur.execute("DELETE FROM public.knowledge_chunks WHERE document_id = %s;", (doc_id,))
                            stats["documents_updated"] += 1
                    else:
                        # Insert new document
                        cur.execute(
                            """
                            INSERT INTO public.knowledge_documents (
                                title, source, source_type, source_url, document_type,
                                language, category, crop, version, file_path, checksum,
                                is_public, is_verified, access_level, metadata
                            ) VALUES (
                                %(title)s, %(source)s, %(source_type)s, %(source_url)s, %(document_type)s,
                                %(language)s, %(category)s, %(crop)s, %(version)s, %(file_path)s, %(checksum)s,
                                %(is_public)s, %(is_verified)s, %(access_level)s, %(metadata)s
                            ) RETURNING id;
                            """,
                            {**doc_meta, "metadata": json.dumps(doc_meta["metadata"])}
                        )
                        doc_id = cur.fetchone()["id"]
                        stats["documents_inserted"] += 1
                        existing_docs[rel_path] = (doc_id, current_checksum)

                    if not chunks:
                        continue

                    # Generate 384-dimensional dense vector embeddings
                    chunk_texts = [c["content"] for c in chunks]
                    embeddings = emb_fn(chunk_texts)
                    stats["embeddings_generated"] += len(embeddings)

                    # Insert chunks with pgvector
                    for c_obj, emb in zip(chunks, embeddings):
                        # Ensure exactly 384 dimensions
                        if len(emb) != 384:
                            raise ValueError(f"Unexpected embedding dimension: {len(emb)} (expected 384)")

                        vec_str = "[" + ",".join(f"{v:.8f}" for v in emb) + "]"
                        cur.execute(
                            """
                            INSERT INTO public.knowledge_chunks (
                                document_id, chunk_id_str, content, chunk_index,
                                section_title, section_type, page_number, embedding, metadata
                            ) VALUES (
                                %(document_id)s, %(chunk_id_str)s, %(content)s, %(chunk_index)s,
                                %(section_title)s, %(section_type)s, %(page_number)s, %(embedding)s::extensions.vector, %(metadata)s
                            ) ON CONFLICT (chunk_id_str) DO UPDATE SET
                                content = EXCLUDED.content,
                                section_title = EXCLUDED.section_title,
                                section_type = EXCLUDED.section_type,
                                embedding = EXCLUDED.embedding,
                                metadata = EXCLUDED.metadata;
                            """,
                            {
                                "document_id": doc_id,
                                "chunk_id_str": c_obj["chunk_id_str"],
                                "content": c_obj["content"],
                                "chunk_index": c_obj["chunk_index"],
                                "section_title": c_obj["section_title"],
                                "section_type": c_obj["section_type"],
                                "page_number": c_obj["page_number"],
                                "embedding": vec_str,
                                "metadata": json.dumps(c_obj["metadata"])
                            }
                        )
                        stats["chunks_created"] += 1

                    conn.commit()
                    if f_idx % 5 == 0 or f_idx == len(file_list):
                        logger.info(f"Progress: [{f_idx}/{len(file_list)}] Ingested {file_path.name} | Total chunks: {stats['chunks_created']}")

                except Exception as e:
                    conn.rollback()
                    err_msg = f"Failed processing {file_path.name}: {e}"
                    logger.error(err_msg)
                    stats["failures"].append({"file": file_path.name, "error": str(e)})

    finally:
        conn.close()

    return stats


def inspect_supabase_knowledge_base():
    """Prints status and record counts of Supabase knowledge tables."""
    import psycopg2
    from psycopg2.extras import RealDictCursor

    db_url = os.getenv("DATABASE_URL", "")
    conn = psycopg2.connect(dsn=db_url)
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("SELECT COUNT(*) AS count FROM public.knowledge_documents;")
        doc_count = cur.fetchone()["count"]

        cur.execute("SELECT COUNT(*) AS count FROM public.knowledge_chunks;")
        chunk_count = cur.fetchone()["count"]

        cur.execute(
            """
            SELECT d.crop, COUNT(c.id) AS chunks
            FROM public.knowledge_chunks c
            JOIN public.knowledge_documents d ON c.document_id = d.id
            GROUP BY d.crop
            ORDER BY chunks DESC
            LIMIT 10;
            """
        )
        crop_counts = cur.fetchall()

        cur.execute(
            """
            SELECT d.title, COUNT(c.id) AS chunks
            FROM public.knowledge_chunks c
            JOIN public.knowledge_documents d ON c.document_id = d.id
            WHERE d.file_path ILIKE '%mountain%'
            GROUP BY d.title;
            """
        )
        mountain_chunks = cur.fetchall()

    conn.close()

    print("\n" + "=" * 60)
    print("SUPABASE PGVECTOR KNOWLEDGE BASE STATUS")
    print("=" * 60)
    print(f"Total Knowledge Documents: {doc_count}")
    print(f"Total Knowledge Chunks:    {chunk_count}")
    print("\nTop Crops by Chunk Count:")
    for r in crop_counts:
        print(f"  • {r['crop']}: {r['chunks']} chunks")
    print("\nMountain Farming Assets:")
    for r in mountain_chunks:
        print(f"  • {r['title']}: {r['chunks']} chunks")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ingest agricultural knowledge base into Supabase pgvector")
    parser.add_argument("--rebuild", action="store_true", help="Delete all existing documents/chunks before ingesting")
    parser.add_argument("--inspect", action="store_true", help="Inspect current documents and chunks stored in Supabase")
    parser.add_argument("--dry-run", action="store_true", help="Discover and report files without writing to database")
    args = parser.parse_args()

    if args.inspect:
        inspect_supabase_knowledge_base()
        sys.exit(0)

    print("\nStarting Supabase pgvector Knowledge Ingestion Pipeline...")
    res = run_ingestion(rebuild=args.rebuild, dry_run=args.dry_run)
    print("\n" + "=" * 60)
    print("INGESTION EXECUTION REPORT")
    print("=" * 60)
    print(f"Files Discovered:      {res['files_discovered']}")
    print(f"Documents Inserted:    {res['documents_inserted']}")
    print(f"Documents Updated:     {res['documents_updated']}")
    print(f"Documents Skipped:     {res['documents_skipped']}")
    print(f"Duplicates Detected:   {res['duplicates_detected']}")
    print(f"Chunks Created:        {res['chunks_created']}")
    print(f"Embeddings Generated:  {res['embeddings_generated']}")
    print(f"Failures:              {len(res['failures'])}")
    if res["failures"]:
        for f in res["failures"]:
            print(f"  FAILED: {f['file']} — {f['error']}")
    print("=" * 60 + "\n")
