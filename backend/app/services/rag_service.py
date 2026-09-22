"""
Maitri Krishi Assistant - RAG Retrieval Service
------------------------------------------------
Phase 4 Production Implementation:
1. Unicode-aware multilingual query expansion (Hindi, Hinglish, English)
2. Crop detection & strict cross-crop isolation (Wheat, Rice, Maize, etc.)
3. Category detection & category-aware re-ranking (Schemes, Irrigation, Pests, etc.)
4. Persistent ChromaDB vector search with relevance thresholding
5. Source integrity & metadata tracking (official_verified vs curated_reference vs general_reference)
6. Dynamic source-answer linking (1 to 3 sources actually used, exact count)
7. Out-of-domain & low-confidence safeguards
8. Developer CLI debug command (Section 16)
"""

import os
import re
import sys
import argparse
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv

# Ensure environment is loaded
BASE_DIR = Path(__file__).resolve().parent.parent.parent
load_dotenv(BASE_DIR / ".env")

logger = logging.getLogger("maitri.rag_service")

# Vector Store Configuration
VECTOR_STORE_DIR = BASE_DIR / "vector_store"
COLLECTION_NAME = "maitri_krishi_kb"

_CHROMA_CLIENT = None
_COLLECTION = None


def unicode_word_match(pattern: str, text: str) -> bool:
    """
    Matches terms using Unicode-aware boundary logic rather than ASCII \\b.
    Devanagari vowel signs/matras (e.g. 'ा', 'े', 'ू', 'ं') are non-word characters in ASCII \\b,
    which causes standard \\b to fail on words like 'गेहूं' or falsely match inside 'समाधान'.
    """
    regex = rf"(?<![\u0900-\u097Fa-zA-Z0-9])({pattern})(?![\u0900-\u097Fa-zA-Z0-9])"
    return bool(re.search(regex, text, re.IGNORECASE))


# Multilingual Agricultural Expansions
AGRI_EXPANSIONS = [
    # Crops
    (r"गेहूं|गेहू|gehu|gehun|wheat", "wheat gehu rabi"),
    (r"धान|चावल|\bdhan\b|dhaan|chawal|rice|paddy", "rice paddy dhaan kharif"),
    (r"मक्का|मकई|makka|makai|corn|maize", "maize corn makka kharif"),
    (r"आलू|aaloo|aalu|potato", "potato tuber aalu"),
    (r"टमाटर|tamatar|tomato", "tomato tamatar fruit borer"),
    (r"सरसों|राई|sarson|rai|mustard|rapeseed", "mustard rapeseed sarson rabi"),
    (r"चना|चने|chana|chane|chickpea|gram", "chickpea gram pod borer chana"),

    # Irrigation & Water
    (r"पहली सिंचाई|pehli sinchai|first irrigation", "first irrigation CRI crown root initiation stage 21 days"),
    (r"सिंचाई|पानी|जल|sinchai|paani|pani|water|irrigation|irrigating", "irrigation water moisture scheduling interval alternate wetting drying awd"),
    (r"नमी|moisture|nami", "soil moisture deficit irrigation tensiometer"),
    (r"ड्रिप|drip|फव्वारा|sprinkler", "micro irrigation drip sprinkler subsidy pmksy"),

    # Pests, Insects & Worms
    (r"फॉल आर्मीवर्म|armyworm|faw|लश्करी सुंडी", "fall armyworm spodoptera frugiperda whorl frass shot-holes"),
    (r"कीड़े|कीड़ा|कीट|सुंडी|keede|keeda|keet|pest|pests|insect|insects|worm|caterpillar|larva", "insect pest caterpillar borer larva fall armyworm control"),
    (r"माहू|चेपा|aphid|aphids|chepa", "mustard aphid lipaphis erysimi chepa honey dew"),
    (r"सफेद मक्खी|whitefly", "whitefly tomato leaf curl virus vector bemisia tabaci"),
    (r"तना छेदक|stem borer|dead heart", "rice stem borer scirpophaga incertulas dead heart white earhead"),

    # Diseases & Symptoms
    (r"पीला|पीली|पीले|पीलापन|peela|peeli|peele|peelapan|yellow|yellowing", "yellow leaves chlorosis nitrogen deficiency yellow rust stripe rust puccinia"),
    (r"रतुआ|rust|स्ट्राइप|stripe", "yellow rust stripe rust puccinia striiformis propiconazole tebuconazole"),
    (r"झुलसा|ब्लास्ट|blight|blast", "blast sheath blight late blight early blight tricyclazole copper oxychloride"),
    (r"मुड़|मुड़ना|curl|curling", "leaf curl virus whitefly transmission upward curling"),

    # Fertilizers & Plant Nutrition
    (r"नाइट्रोजन|nitrogen", "nitrogen deficiency chlorosis V-shape yellowing lower leaves urea"),
    (r"यूरिया|urea", "urea nitrogen 46% N top dressing split application nano urea"),
    (r"डीएपी|dap", "di-ammonium phosphate phosphorus basal dose root development"),
    (r"पोटाश|potash|mop", "muriate of potash potassium marginal scorch lodging resistance"),
    (r"जिंक|zinc|खैरा|khaira", "zinc sulphate khaira disease white bud micronutrient"),
    (r"खाद|उर्वरक|khad|fertilizer|fertilizers", "fertilizer nutrient dose urea dap mop npk basal top-dressing"),

    # Soil & Land
    (r"मिट्टी|मृदा|mitti|soil", "soil health card testing fertility organic carbon pH nutrient"),
    (r"धीमी बढ़वार|धीमा विकास|slow growth|growth slow|badhwar", "stunted slow plant growth tillering deficiency"),

    # Government Schemes
    (r"पीएम-किसान|पीएम किसान|pm kisan|pm-kisan|samman nidhi", "pm kisan samman nidhi 6000 installment eligibility portal dbt"),
    (r"फसल बीमा|fasal bima|pmfby|insurance", "pmfby crop insurance premium claim 72 hours loss assessment"),
    (r"केसीसी|kcc|किसान क्रेडिट|kisan credit", "kisan credit card kcc loan 4 percent interest subvention scale of finance"),

    # Parali & Weather
    (r"पराली|परली|parali|stubble|straw", "crop residue parali stubble burning happy seeder super seeder pusa bio-decomposer in-situ"),
    (r"पाला|पाले|frost|pala|शीतलहर|cold wave", "frost protection cold wave winter evening irrigation light smoke"),

    # Mountain & Hill Farming (Phase 4 / Step 5)
    (r"पहाड़ी|पहाड़|पहाड़ों|pahadi|pahari|pahaad|pahado|pahadon|mountain|mountains|hill|hills|hilly|high altitude|terrace farming|सीढ़ीनुमा|समोच्च", "mountain farming hill agriculture terrace farming pahadi khet crops high altitude slope organic mandua ragi jhangora rajma off-season vegetables"),
    (r"फसल उगा|uga skta|kaunsi fasal|कौन सी फसल|crop suitability|what crops can i grow|best crops|suitable crops", "best crops crop suitability cultivation selection farming suitable crops"),

    # Commercial & Phase 5 Crops
    (r"मूंगफली|मूँगफली|mungfali|groundnut|peanut", "groundnut mungfali pegging gypsum pod rot tikka arachis hypogaea"),
    (r"अरहर|तुअर|तूअर|arhar|toor|tur|pigeonpea|red gram", "pigeonpea arhar tur pod borer pod fly phytophthora blight cajanus cajan"),
    (r"मिर्च|मिर्ची|mirch|mirchi|chilli|chili|capsicum|shimla mirch|शिमला मिर्च", "chilli mirch leaf curl murda thrips anthracnose capsicum dieback"),
    (r"कपास|रूई|kapas|cotton", "cotton kapas bt cotton non-bt refuge bollworm pink bollworm whitefly clcud"),
    (r"गन्ना|ईख|ganna|sugarcane", "sugarcane ganna red rot sett treatment early shoot borer ratoon"),
    (r"सोयाबीन|soybean|soya", "soybean soya yellow mosaic girdler beetle rust inoculation"),
    (r"प्याज|प्याज़|pyaz|pyaaz|onion", "onion pyaz thrips purple blotch nursery storage bulb"),
    (r"केला|kela|banana", "banana kela g-9 tissue culture panama wilt sigatoka sucker spacing"),
    (r"मसूर|masoor|lentil|चना|chana|chickpea", "chickpea lentil bundelkhand kabar mar vertisol pulse borer wilt"),

    # Specialized Topics & Agroforestry / Protected Cultivation
    (r"पॉपलर|यूकेलिप्टस|कृषि वानिकी|poplar|eucalyptus|agroforestry|कृषिवानिकी", "agroforestry poplar eucalyptus intercropping bund plantation silviculture"),
    (r"पॉलीहाउस|polyhouse|greenhouse|nvph|shade net|शेडनेट", "protected cultivation polyhouse nvph shade net capsicum bell pepper drip fertigation"),
    (r"सूत्रकृमि|नेमाटोड|nematode|root knot|गांठें|गांठे|ganthen", "root knot nematode meloidogyne galls swelling nematicide carbofuran paecilomyces"),
    (r"हर्मेटिक|pics बैग|pics bag|pics bags|hermetic|अनाज भंडारण|grain storage|anaj bhandaran", "hermetic storage PICS bags grain storage insect pest oxygen deprivation post harvest"),
    (r"सुपर सीडर|super seeder|happy seeder|सीडर|कृषि यंत्र|mechanization|chc|custom hiring", "super seeder happy seeder farm mechanization chc implements custom hiring center tractor residue"),
    (r"बायोस्टिमुलेंट|ह्यूमिक|biostimulant|humic acid|जैविक खाद|biofertilizer", "biofertilizers organic manures biostimulant humic acid fco regulation vermicompost fym azotobacter rhizobium psb"),
    (r"गुल्ली डंडा|गुल्लीडंडा|मंडूसी|gulli danda|phalaris|mandusi|खरपतवार|weed|weeds", "phalaris minor gulli danda mandusi weed management herbicide resistance wheat clodinafop pendimethalin sulfosulfuron")
]

# Crop detection regex patterns
CROP_DETECTION_PATTERNS = {
    "Wheat": r"गेहूं|गेहू|गेहूँ|gehu|gehun|wheat",
    "Rice": r"धान|चावल|\bdhan\b|dhaan|chawal|rice|paddy",
    "Maize": r"मक्का|मकई|makka|makai|corn|maize",
    "Potato": r"आलू|aaloo|aalu|potato",
    "Tomato": r"टमाटर|tamatar|tomato",
    "Mustard": r"सरसों|राई|sarson|rai|mustard|rapeseed",
    "Chickpea": r"चना|चने|chana|chane|chickpea|gram|मसूर|lentil",
    "Sugarcane": r"गन्ना|ईख|ganna|sugarcane",
    "Onion": r"प्याज|pyaj|pyaaz|onion",
    "Soybean": r"सोयाबीन|soybean|soya",
    "Groundnut": r"मूंगफली|mungfali|peanut|groundnut",
    "Pigeonpea": r"अरहर|तुअर|arhar|tuar|pigeonpea",
    "Chilli": r"मिर्च|mirch|mirchi|chilli|chili",
    "Banana": r"केला|kela|banana",
    "Cotton": r"कपास|रूई|kapas|cotton"
}

# Category detection patterns for intelligent re-ranking
CATEGORY_DETECTION_PATTERNS = {
    "Mountain Farming": r"पहाड़ी|पहाड़|pahadi|pahari|pahado|pahadon|pahaad|mountain|hill|hilly|terrace|सीढ़ीनुमा|high altitude",
    "Schemes": r"pm-kisan|pm kisan|पीएम किसान|fasal bima|pmfby|फसल बीमा|kcc|केसीसी|किसान क्रेडिट|योजना|scheme|subvention|subsidy|bima",
    "Irrigation": r"sinchai|सिंचाई|पानी|जल|water|irrigation|peeli sinchai|drip|sprinkler|awd|tubewell|नमी|moisture",
    "Pests": r"keeda|keede|कीड़ा|कीड़े|कीट|सुंडी|pest|pests|insect|insects|worm|caterpillar|larva|armyworm|aphid|whitefly|borer|माहू|चेपा|beetle|भृंग",
    "Diseases": r"yellow rust|stripe rust|रतुआ|blight|blast|झुलसा|पर्ण कुंचन|leaf curl|मुड़|रोग|fungus|disease|rot|curl|sadan|सड़न",
    "Fertilizers": r"urea|यूरिया|dap|डीएपी|mop|पोटाश|zinc|जिंक|khad|खाद|fertilizer|fertilizers|उर्वरक|पोषक तत्व|micronutrient|gypsum|जिप्सम|biostimulant|बायोफर्टिलाइजर",
    "Soil": r"mitti|मिट्टी|मृदा|soil|soil health|health card|card|salin|alkali|ph|दोमट|ऊसर|sodic",
    "Crop Residue": r"parali|पराली|stubble|straw|decomposer|seeder",
    "Weather": r"frost|पाला|cold wave|शीतलहर|heatwave|लू|मौसम|weather|rain|barish|monsoon|मानसून"
}


def get_chroma_collection():
    """Returns singleton instance of ChromaDB collection."""
    global _CHROMA_CLIENT, _COLLECTION
    if _COLLECTION is not None:
        return _COLLECTION

    if not VECTOR_STORE_DIR.exists():
        logger.warning(f"Vector store directory {VECTOR_STORE_DIR} does not exist. Creating it.")
        VECTOR_STORE_DIR.mkdir(parents=True, exist_ok=True)

    try:
        import chromadb
        _CHROMA_CLIENT = chromadb.PersistentClient(path=str(VECTOR_STORE_DIR))
        _COLLECTION = _CHROMA_CLIENT.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"description": "Maitri Krishi Assistant Agriculture Knowledge Base (Phase 4)"}
        )
        return _COLLECTION
    except Exception as e:
        logger.error(f"Failed to initialize ChromaDB collection: {e}")
        return None


def detect_language(text: str) -> str:
    """Detects Hindi (Devanagari), Hinglish, or English."""
    if re.search(r"[\u0900-\u097F]", text):
        return "hi"

    hinglish_tokens = {
        "kya", "kyu", "kyun", "kaise", "karein", "kare", "karna", "hai", "hain",
        "meri", "mera", "mere", "fasal", "paani", "pani", "keeda", "keede",
        "peele", "pila", "patte", "patti", "khad", "mitti", "khet", "daalein",
        "daalna", "rog", "upay", "batao", "bataiye", "hoga", "rahe", "raha",
        "chahiye", "kitna", "kab", "booth", "kharif", "rabi", "dhan", "gehu"
    }
    words = re.findall(r"\b[a-zA-Z]+\b", text.lower())
    if any(w in hinglish_tokens for w in words):
        return "hinglish"

    return "en"


def is_non_agricultural(text: str) -> bool:
    """Identifies queries that are completely outside agricultural scope."""
    q_lower = text.lower().strip()

    # Words that guarantee agricultural relevance
    agri_words = [
        "crop", "farm", "kisan", "soil", "pest", "disease", "fertilizer", "wheat",
        "rice", "paddy", "maize", "potato", "tomato", "mustard", "irrigation", "water",
        "paani", "pani", "gehu", "dhaan", "fasal", "mitti", "keeda", "khad", "urea",
        "dap", "pm-kisan", "pm kisan", "pmfby", "kcc", "parali", "sinchai", "mandi",
        "bhav", "weather", "mausam", "mungfali", "groundnut", "arhar", "tur", "pigeonpea",
        "mirch", "mirchi", "chilli", "capsicum", "kapas", "cotton", "ganna", "sugarcane",
        "soybean", "soya", "pyaz", "onion", "kela", "banana", "masoor", "lentil", "chana",
        "gram", "poplar", "eucalyptus", "polyhouse", "nematode", "pics", "hermetic",
        "storage", "seeder", "biostimulant", "humic", "gypsum", "जिप्सम", "पॉलीहाउस"
    ]
    if any(w in q_lower for w in agri_words):
        return False

    out_of_domain_patterns = [
        r"capital of\b",
        r"\bwho is (the )?(president|prime minister|ceo|actor|singer|king)\b",
        r"\bmovie\b", r"\bsong\b", r"\bcricket\b", r"\bfootball\b", r"\bbitcoin\b",
        r"\bwrite (a )?(code|poem|story|song|essay)\b",
        r"\bpython code\b", r"\bjavascript\b", r"\bfrance\b", r"\bgermany\b"
    ]
    for pat in out_of_domain_patterns:
        if re.search(pat, q_lower):
            return True

    return False


def is_gibberish(text: str) -> bool:
    """Detects random key mashing or empty meaningless strings."""
    clean = text.strip()
    if len(clean) < 3:
        return True

    # High length alphabetical string without normal vowel distribution
    if re.fullmatch(r"[a-zA-Z]+", clean) and len(clean) >= 7:
        vowels = re.findall(r"[aeiouAEIOU]", clean)
        if len(vowels) == 0 or len(vowels) / len(clean) < 0.15:
            return True

    if len(set(clean)) <= 2 and len(clean) > 5:
        return True

    return False


def detect_crop_in_query(query: str) -> Optional[str]:
    """Detects primary crop mentioned in the query."""
    for crop_name, pattern in CROP_DETECTION_PATTERNS.items():
        if unicode_word_match(pattern, query):
            return crop_name
    return None


def detect_category_in_query(query: str) -> Optional[str]:
    """Detects primary agricultural category mentioned in the query."""
    for cat_name, pattern in CATEGORY_DETECTION_PATTERNS.items():
        if unicode_word_match(pattern, query):
            return cat_name
    return None


def preprocess_query(query: str) -> str:
    """Expands query with multilingual agricultural synonyms using Unicode boundary matching."""
    added_terms = []
    for pattern, expansion in AGRI_EXPANSIONS:
        if unicode_word_match(pattern, query):
            added_terms.append(expansion)

    if added_terms:
        return f"{query} " + " ".join(added_terms)
    return query


def clean_chunk_text(raw_text: str) -> str:
    """Strips internal indexing anchor tags to produce natural text for the LLM."""
    clean = re.sub(r"^\[Source:[^\]]+\]\s*", "", raw_text).strip()
    clean = re.sub(r"\n{3,}", "\n\n", clean)
    return clean


import threading

_EMBEDDING_FUNCTION = None
_EMBEDDING_LOCK = threading.Lock()


def get_embedding_function():
    """Process-level thread-safe singleton for all-MiniLM-L6-v2 embedding model."""
    global _EMBEDDING_FUNCTION
    if _EMBEDDING_FUNCTION is None:
        with _EMBEDDING_LOCK:
            if _EMBEDDING_FUNCTION is None:
                try:
                    import chromadb.utils.embedding_functions as ef
                    _EMBEDDING_FUNCTION = ef.DefaultEmbeddingFunction()
                    logger.info("Initialized singleton all-MiniLM-L6-v2 embedding function")
                except Exception as e:
                    logger.error(f"Failed to initialize embedding function: {e}")
                    return None
    return _EMBEDDING_FUNCTION


def compute_query_embedding(query_text: str) -> List[float]:
    """Computes 384-dimensional dense vector embedding using singleton all-MiniLM-L6-v2."""
    emb_fn = get_embedding_function()
    if not emb_fn:
        return []
    try:
        res = emb_fn([query_text])[0]
        return [float(x) for x in res]
    except Exception as e:
        logger.error(f"Failed to generate query embedding: {e}")
        return []


def query_knowledge_base_pgvector(
    expanded_q: str,
    top_k: int = 12,
    crop_filter: Optional[str] = None,
    category_filter: Optional[str] = None,
    match_threshold: float = 0.25,
) -> Optional[List[Dict[str, Any]]]:
    """
    Server-Side PostgreSQL Invocation of private.match_knowledge_chunks(...)
    Uses pooled SQLAlchemy connection first for high performance; falls back to direct psycopg2 if needed.
    """
    database_url = os.getenv("DATABASE_URL", "")
    if not (database_url.startswith("postgresql://") or database_url.startswith("postgres://")):
        return None

    embedding = compute_query_embedding(expanded_q)
    if embedding is None or len(embedding) == 0:
        return None

    vec_str = "[" + ",".join(f"{x:.8f}" for x in embedding) + "]"

    # 1. Attempt pooled execution via SQLAlchemy engine
    try:
        from ..database import engine
        from sqlalchemy import text
        if engine and engine.name == "postgresql":
            with engine.connect() as conn:
                res = conn.execute(
                    text("""
                        SELECT 
                            id, document_id, chunk_id_str, content, section_title, section_type,
                            page_number, title, source, source_type, source_url, category, crop,
                            version, similarity
                        FROM private.match_knowledge_chunks(
                            CAST(:vec_str AS extensions.vector),
                            CAST(:threshold AS pg_catalog.float8),
                            CAST(:top_k AS pg_catalog.int4),
                            CAST(:crop AS pg_catalog.varchar),
                            CAST(:category AS pg_catalog.varchar)
                        );
                    """),
                    {
                        "vec_str": vec_str,
                        "threshold": float(match_threshold),
                        "top_k": int(top_k),
                        "crop": crop_filter,
                        "category": category_filter
                    }
                )
                return [dict(r._mapping) for r in res.fetchall()]
    except Exception as pool_err:
        logger.debug(f"SQLAlchemy pooled pgvector query attempt: {pool_err}. Falling back to direct psycopg2.")

    # 2. Resilient fallback with psycopg2
    import time
    import psycopg2
    from psycopg2.extras import RealDictCursor

    max_retries = 2
    for attempt in range(max_retries):
        conn = None
        try:
            conn = psycopg2.connect(dsn=database_url, connect_timeout=10, sslmode="require")
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT 
                        id, document_id, chunk_id_str, content, section_title, section_type,
                        page_number, title, source, source_type, source_url, category, crop,
                        version, similarity
                    FROM private.match_knowledge_chunks(
                        %s::extensions.vector,
                        %s::pg_catalog.float8,
                        %s::pg_catalog.int4,
                        %s::pg_catalog.varchar,
                        %s::pg_catalog.varchar
                    );
                    """,
                    (vec_str, match_threshold, top_k, crop_filter, category_filter)
                )
                rows = [dict(r) for r in cur.fetchall()]
            conn.close()
            return rows
        except Exception as e:
            if conn:
                try:
                    conn.close()
                except Exception:
                    pass
            if attempt < max_retries - 1:
                logger.warning(f"PostgreSQL pgvector query attempt {attempt+1} failed: {e}. Retrying in 1s...")
                time.sleep(1)
            else:
                logger.error(f"Direct server-side PostgreSQL query to private.match_knowledge_chunks failed: {e}")
                return None


def query_knowledge_base(
    query: str,
    crop_filter: Optional[str] = None,
    top_k: int = 3
) -> Dict[str, Any]:
    """
    Primary RAG retrieval function.
    Returns:
    {
        "chunks": List[Dict[str, Any]],  # Structured chunk objects with text & metadata
        "raw_chunk_texts": List[str],    # Cleaned text passages for prompt synthesis
        "sources": List[Dict[str, Any]], # Compact deduplicated sources for frontend (1 to 3 sources)
        "confidence": float,             # Genuine calculated relevance score
        "is_low_confidence": bool,
        "is_out_of_domain": bool,
        "language": str,
        "detected_crop": Optional[str],
        "detected_category": Optional[str]
    }
    """
    clean_query = (query or "").strip()
    lang = detect_language(clean_query)

    # 1. Out of domain check
    if is_non_agricultural(clean_query):
        return {
            "chunks": [],
            "raw_chunk_texts": [],
            "sources": [],
            "confidence": 0.0,
            "is_low_confidence": False,
            "is_out_of_domain": True,
            "language": lang,
            "detected_crop": None,
            "detected_category": None
        }

    # 2. Gibberish check
    if is_gibberish(clean_query):
        return {
            "chunks": [],
            "raw_chunk_texts": [],
            "sources": [],
            "confidence": 0.1,
            "is_low_confidence": True,
            "is_out_of_domain": False,
            "language": lang,
            "detected_crop": None,
            "detected_category": None
        }

    # 3. Detect crop, category & expand query
    detected_crop = crop_filter or detect_crop_in_query(clean_query)
    detected_category = detect_category_in_query(clean_query)
    expanded_q = preprocess_query(clean_query)

    # 4. Dense vector retrieval
    # Server-Side PostgreSQL Architecture:
    # FastAPI backend -> direct PostgreSQL connection / psycopg2 -> private.match_knowledge_chunks(...) -> pgvector
    docs = []
    metas = []
    distances = []

    database_url = os.getenv("DATABASE_URL", "")
    is_postgres = database_url.startswith(("postgresql://", "postgres://"))

    if is_postgres:
        effective_cat_filter = detected_category if detected_category in ("Schemes", "Irrigation", "Mountain Farming") else None
        pg_rows = query_knowledge_base_pgvector(
            expanded_q=expanded_q,
            top_k=12,
            crop_filter=detected_crop,
            category_filter=effective_cat_filter,
            match_threshold=0.25
        )
        if pg_rows:
            for r in pg_rows:
                docs.append(r.get("content", ""))
                metas.append({
                    "title": r.get("title") or "Agricultural Advisory",
                    "section": r.get("section_title") or "",
                    "section_type": r.get("section_type") or "General Agronomic Advisory",
                    "source": r.get("source") or "Maitri Agronomy Reference Desk",
                    "source_type": r.get("source_type") or "curated_reference",
                    "url": r.get("source_url") or "",
                    "version": r.get("version") or "2024.1",
                    "category": r.get("category") or "General",
                    "crop": r.get("crop") or "General",
                    "page_number": r.get("page_number", 1)
                })
                # Similarity is cosine similarity (0 to 1); distance = 2 * (1 - sim)
                sim = float(r.get("similarity") or 0.0)
                distances.append(2.0 * (1.0 - sim))

    # ChromaDB fallback is permitted ONLY during local development (ENVIRONMENT=development) or non-PostgreSQL DB
    env = os.getenv("ENVIRONMENT", "production").lower()
    if not docs and (env == "development" or not is_postgres):
        collection = get_chroma_collection()
        if collection is not None and collection.count() > 0:
            try:
                candidate_count = min(12, collection.count())
                results = collection.query(
                    query_texts=[expanded_q],
                    n_results=candidate_count
                )
                docs = results.get("documents", [[]])[0]
                metas = results.get("metadatas", [[]])[0]
                distances = results.get("distances", [[]])[0]
            except Exception as e:
                logger.error(f"ChromaDB search failed: {e}")

    if not docs:
        return {
            "chunks": [],
            "raw_chunk_texts": [],
            "sources": [],
            "confidence": 0.0,
            "is_low_confidence": True,
            "is_out_of_domain": False,
            "language": lang,
            "detected_crop": detected_crop,
            "detected_category": detected_category
        }

    # 5. Crop-Aware & Category-Aware Re-Ranking
    scored_candidates = []
    for doc, meta, dist in zip(docs, metas, distances):
        # Base cosine/L2 similarity metric (0.0 to 1.0)
        base_sim = max(0.0, min(1.0, 1.0 - (dist / 2.0)))
        adjusted_score = base_sim

        chunk_crop = str(meta.get("crop", "")).strip()
        chunk_cat = str(meta.get("category", "")).strip()

        # Crop matching
        if detected_crop:
            is_crop_match = (
                detected_crop.lower() in chunk_crop.lower()
                or (detected_crop == "Chilli" and any(k in chunk_crop.lower() for k in ["chilli", "capsicum", "pepper", "mirch", "vegetable"]))
                or (detected_crop == "Chickpea" and any(k in chunk_crop.lower() for k in ["chickpea", "gram", "lentil", "pulse"]))
            )
            if is_crop_match:
                adjusted_score += 0.25
            elif any(g in chunk_crop.lower() for g in ["general", "all", "multi", "soil", "fertilizer", "scheme"]):
                adjusted_score += 0.02
            else:
                # Chunk explicitly belongs to a different single crop (e.g. Rice when query is Wheat)
                adjusted_score -= 0.40

        # Category matching
        if detected_category:
            if detected_category.lower() in chunk_cat.lower():
                adjusted_score += 0.22
            elif detected_category in ("Pests", "Diseases") and chunk_cat.lower() in ("pests", "diseases"):
                adjusted_score += 0.18
            elif detected_category in ("Schemes", "Irrigation", "Mountain Farming") and chunk_cat not in (detected_category, "General"):
                # Penalize irrelevant categories when user asks about specific scheme, irrigation, or mountain farming
                adjusted_score -= 0.28

        # Topic-Specific Boosts for High Precision Retrieval
        meta_title_lower = str(meta.get("title", "")).lower()
        meta_sec_lower = str(meta.get("section", "")).lower()

        # Agroforestry
        if any(term in clean_query.lower() for term in ["पॉपलर", "यूकेलिप्टस", "poplar", "eucalyptus", "agroforestry", "सह-फसली"]):
            if any(term in meta_title_lower for term in ["agroforestry", "poplar", "eucalyptus", "वानिकी"]):
                adjusted_score += 0.35

        # Protected Cultivation / Polyhouse
        if any(term in clean_query.lower() for term in ["polyhouse", "पॉलीहाउस", "shade net", "nvph", "protected cultivation"]):
            if any(term in meta_title_lower for term in ["polyhouse", "protected cultivation", "shade net"]):
                adjusted_score += 0.35

        # Nematodes & Root Knots
        if any(term in clean_query.lower() for term in ["गांठें", "गांठे", "nematode", "root knot", "सूत्रकृमि"]):
            if any(term in meta_title_lower for term in ["nematode", "rodent", "गांठ"]):
                adjusted_score += 0.35

        # Hermetic PICS Grain Storage
        if any(term in clean_query.lower() for term in ["pics", "hermetic", "हर्मेटिक", "grain storage", "अनाज भंडारण"]):
            if any(term in meta_title_lower for term in ["storage", "grain", "भंडारण"]):
                adjusted_score += 0.35

        # Farm Mechanization & Super Seeder
        if any(term in clean_query.lower() for term in ["super seeder", "happy seeder", "सुपर सीडर", "chc", "custom hiring"]):
            if any(term in meta_title_lower for term in ["mechanization", "chc", "implements"]):
                adjusted_score += 0.30

        # Biostimulants & Biofertilizers
        if any(term in clean_query.lower() for term in ["biostimulant", "humic acid", "ह्यूमिक", "बायोस्टिमुलेंट"]):
            if any(term in meta_title_lower for term in ["biofertilizer", "organic manure", "जैविक"]):
                adjusted_score += 0.35

        # Weeds / Phalaris minor
        if any(term in clean_query.lower() for term in ["gulli danda", "mandusi", "phalaris", "गुल्ली", "मंडूसी", "खरपतवार"]):
            if any(term in meta_title_lower for term in ["weed", "phalaris", "खरपतवार", "gulli", "canary"]):
                adjusted_score += 0.35

        # If query asks about leaf curling / whitefly symptoms, boost specific leaf curl chunks (only for relevant crops)
        if any(term in clean_query.lower() for term in ["मुड़", "curl", "मरोड़", "कुंचन"]):
            if detected_crop in ("Tomato", "Cotton", "Chilli", None):
                if any(term in meta_title_lower or term in meta_sec_lower for term in ["leaf curl", "curl", "मरोड़", "कुंचन", "whitefly"]):
                    adjusted_score += 0.25

        # If query asks about what crops to grow and chunk is about Best Crops, give bonus
        if any(w in clean_query.lower() for w in ["kaunsi fasal", "फसल", "crop", "crops", "grow", "उगा"]):
            if any(term in meta_sec_lower for term in ["best crops", "फसलें", "crops"]):
                adjusted_score += 0.12


        cleaned_text = clean_chunk_text(doc)
        scored_candidates.append({
            "text": cleaned_text,
            "title": meta.get("title", "Agricultural Advisory"),
            "section": meta.get("section", ""),
            "section_type": meta.get("section_type", "General Agronomic Advisory"),
            "source": meta.get("source", "Maitri Agronomy Reference Desk"),
            "source_type": meta.get("source_type", "curated_reference"),
            "url": meta.get("url", ""),
            "version": meta.get("version", "2024.1"),
            "category": meta.get("category", "General"),
            "crop": meta.get("crop", "General"),
            "page_number": meta.get("page_number", 1),
            "score": round(max(0.05, min(0.98, adjusted_score)), 2),
            "raw_distance": dist
        })

    # Sort by adjusted score descending
    scored_candidates.sort(key=lambda x: x["score"], reverse=True)

    # 6. Apply relevance threshold (only keep chunks that are genuinely relevant)
    RELEVANCE_THRESHOLD = 0.42
    filtered_chunks = [c for c in scored_candidates if c["score"] >= RELEVANCE_THRESHOLD]

    # If no chunk met threshold, take top candidate if not abysmal, else empty
    if not filtered_chunks and scored_candidates and scored_candidates[0]["score"] >= 0.35:
        filtered_chunks = [scored_candidates[0]]

    selected_chunks = filtered_chunks[:top_k]

    # Best score reflects retrieval confidence
    top_score = selected_chunks[0]["score"] if selected_chunks else 0.0
    is_low_conf = (top_score < RELEVANCE_THRESHOLD)

    # 7. Exact Source-to-Answer Linking (Section 9 & 10)
    # ONLY include sources from chunks that were actually selected
    sources = []
    seen_sources = set()
    for c in selected_chunks:
        src_key = (c["title"], c["source"])
        if src_key not in seen_sources:
            seen_sources.add(src_key)
            sources.append({
                "title": c["title"],
                "organization": c["source"],
                "source_type": c["source_type"],
                "url": c["url"],
                "version": c["version"],
                "section": c["section"],
                "category": c["category"],
                "crop": c["crop"],
                "score": c["score"]
            })
        if len(sources) >= 3:
            break

    # Safe Developer Logging
    logger.info(
        f"[RAG Retrieval] Query: '{clean_query[:50]}' | Crop: {detected_crop} | Cat: {detected_category} | "
        f"Top Score: {top_score:.2f} | Sources: {[s['title'] for s in sources]}"
    )

    return {
        "chunks": selected_chunks,
        "raw_chunk_texts": [c["text"] for c in selected_chunks],
        "sources": sources,
        "confidence": top_score,
        "is_low_confidence": is_low_conf,
        "is_out_of_domain": False,
        "language": lang,
        "detected_crop": detected_crop,
        "detected_category": detected_category
    }


def print_rag_debug_report(query_text: str):
    """
    RAG Debug Report CLI command implementation (Section 16).
    Prints:
    QUERY
    Detected crop
    Detected category
    Retrieved chunks:
    1. Source
    2. Title
    3. Score
    4. Chunk preview
    Final answer
    Sources used
    """
    print("\n" + "=" * 70)
    print("MAITRI RAG DEBUG REPORT (Section 16)")
    print("=" * 70)
    print(f"QUERY: {query_text}")

    rag_res = query_knowledge_base(query_text, top_k=3)
    print(f"Detected crop:     {rag_res.get('detected_crop') or 'None'}")
    print(f"Detected category: {rag_res.get('detected_category') or 'None'}")
    print(f"Language:          {rag_res.get('language')}")
    print(f"Confidence score:  {rag_res.get('confidence'):.2f}")

    print("\nRetrieved chunks:")
    chunks = rag_res.get("chunks", [])
    if not chunks:
        print("  [No chunks retrieved / below relevance threshold]")
    else:
        for idx, c in enumerate(chunks):
            print(f"\n  {idx+1}. Source:  {c.get('source')} ({c.get('source_type')})")
            print(f"     Title:   {c.get('title')} - {c.get('section')} [{c.get('section_type')}]")
            print(f"     Score:   {c.get('score'):.2f}")
            snippet = c.get("text", "").replace("\n", " ")[:200]
            print(f"     Preview: {snippet}...")

    # Now generate the answer through chat_service
    from .chat_service import process_chat_message
    chat_res = process_chat_message(query_text)

    print("\nFinal answer:")
    print(chat_res.get("reply", ""))

    print("\nSources used:")
    sources = chat_res.get("sources", [])
    if not sources:
        print("  [No sources cited]")
    else:
        for s in sources:
            org = s.get("organization") or s.get("source")
            stype = s.get("source_type", "")
            stype_str = f" [{stype}]" if stype else ""
            print(f"  • {org} — {s.get('title')}{stype_str}")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Maitri Krishi Assistant RAG Retrieval & Debug")
    parser.add_argument("--query", type=str, required=True, help="Agricultural question to test")
    args = parser.parse_args()
    print_rag_debug_report(args.query)
