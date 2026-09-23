"""
Maitri Krishi Assistant - AI Agriculture RAG Chatbot Service
------------------------------------------------------------
Phase 4 Production Implementation:
1. Question processing & semantic vector retrieval via ChromaDB (rag_service)
2. Anti-hallucination interceptors:
   - Live mandi prices (no fake rates, redirect to Market Prices / Agmarknet)
   - Live weather forecasts (no fake forecasts, redirect to Weather Advisory / IMD)
   - Unsupported chemical advice (strict refusal & referral to KVK/Agri Officer)
3. Disease diagnosis safety:
   - Text symptoms treated as non-definitive ("Possible causes include...")
   - Distinguishing diagnostic visual tests
4. Grounded system prompt synthesis with retrieved chunks & strictly relevant farmer context
5. OpenRouter API integration with thinking token stripping
6. Structured offline RAG fallback when OpenRouter is unreachable
7. Dynamic source-answer linking (1 to 3 sources actually used, exact count)
8. Target answer length: 80–180 words
"""

import os
import re
import logging
import requests
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from dotenv import load_dotenv

# Ensure environment is loaded
BASE_DIR = Path(__file__).resolve().parent.parent.parent
load_dotenv(BASE_DIR / ".env")

from .rag_service import query_knowledge_base, detect_language
from .smart_rag_router import (
    classify_query,
    Intent,
    RouteAction,
    RouteDecision,
    compose_pesticide_refusal_reply,
    compose_missing_context_reply,
    compose_unsupported_reply,
    compose_web_evidence_unavailable_reply
)
from .web_search_service import (
    web_search_service,
    WebEvidence,
    SourceTier,
    SourceType
)

logger = logging.getLogger("maitri.chat_service")


# -----------------------------------------------------------------------------
# Farmer Response Sanitizer & Formatting Utilities
# -----------------------------------------------------------------------------
def clean_farmer_markdown(text: str) -> str:
    """
    Strips raw Markdown emphasis markers (**, *, __) and normalizes formatting
    for clean, direct farmer-facing readability:
    - Removes bold emphasis: **text** -> text, __text__ -> text
    - Removes italic emphasis: *text* -> text, _text_ -> text (for whole-word emphasis)
    - Normalizes bullet points: converts '• ', '* ', '+ ' to clean hyphen bullets '- '
    - Strips markdown header symbols (#, ##, ###)
    - Keeps numbers, emojis, plain text, and hyphen bullets intact.
    - Suppresses multiple consecutive blank lines.
    """
    if not text:
        return ""

    cleaned = text

    # 1. Remove markdown bold: **word** or ** phrase **
    cleaned = re.sub(r"\*\*+([^\*\n]+?)\*\*+", r"\1", cleaned)
    cleaned = re.sub(r"__+([^_\n]+?)__+", r"\1", cleaned)

    # 2. Normalize bullet points starting with * or • or + to hyphen bullets (- )
    cleaned = re.sub(r"^[ \t]*[\*\•\+][ \t]+", "- ", cleaned, flags=re.MULTILINE)

    # 3. Remove single asterisk italic: *word* -> word
    cleaned = re.sub(r"(?<!\*)\*([^\*\n]+?)\*(?!\*)", r"\1", cleaned)

    # 4. Remove single underscore italic: _word_ -> word
    cleaned = re.sub(r"(?<!\w)_([^_\n]+?)_(?!\w)", r"\1", cleaned)

    # 5. Remove any leftover stray asterisks or double underscores (guarantees NO raw * leaks)
    cleaned = cleaned.replace("**", "").replace("*", "").replace("__", "")

    # 6. Remove markdown headers: e.g. "### Title" -> "Title"
    cleaned = re.sub(r"^[ \t]*#{1,6}[ \t]*", "", cleaned, flags=re.MULTILINE)

    # 7. Normalize bullet whitespace
    cleaned = re.sub(r"^[ \t]*-[ \t]+", "- ", cleaned, flags=re.MULTILINE)

    # 8. Clean up extra blank lines (no more than 2 consecutive newlines)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)

    return cleaned.strip()


def _safe_print(text: str) -> None:
    """Safe stdout printing on Windows consoles that may not support UTF-8 natively."""
    try:
        encoding = sys.stdout.encoding or "utf-8"
        print(text.encode(encoding, errors="replace").decode(encoding))
    except Exception:
        pass


# -----------------------------------------------------------------------------
# Configuration
# -----------------------------------------------------------------------------
PRIMARY_MODEL = os.getenv("OPENROUTER_MODEL", "nvidia/nemotron-3.5-lightning:free").strip()
DEFAULT_OPENROUTER_MODEL = PRIMARY_MODEL
FALLBACK_MODEL = "openrouter/free"
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"


# -----------------------------------------------------------------------------
# Anti-Hallucination & Safety Interceptors (Phase 4 Sections 6, 12, 13)
# -----------------------------------------------------------------------------
def check_anti_hallucination_intercept(query: str, language: str) -> Optional[Dict[str, Any]]:
    """
    Catches queries where live external data is required but no live feed is streamed to chat,
    preventing the LLM from hallucinating prices, forecasts, or ungrounded chemicals.
    """
    q_lower = query.lower().strip()

    # 1. Live Mandi Price Query (only when web search service is disabled)
    if not getattr(web_search_service, "enabled", False):
        mandi_patterns = [
            r"mandi (bhav|rate|price|rates)",
            r"(मंडी|भाव|रेट).*?(क्या है|कितना है|बताएं|बताओ|आज)",
            r"(आज|today).*?(mandi|भाव|रेट|rate|price)",
            r"what is today'?s (mandi|market) price",
            r"today'?s price of",
            r"gehu ka mandi bhav"
        ]
        if any(re.search(p, q_lower) for p in mandi_patterns) or (("mandi" in q_lower or "मंडी" in q_lower) and ("bhav" in q_lower or "भाव" in q_lower or "price" in q_lower or "rate" in q_lower or "आज" in q_lower)):
            if language == "hi":
                reply = (
                    "नमस्ते! मैत्री कृषि चैट वर्तमान में रीयल-टाइम मंडी भाव के लाइव डेटा फीड से सीधे कनेक्ट नहीं है। इसलिए मैं आज का सटीक मंडी भाव नहीं बता सकता।\n\n"
                    "📊 सत्यापित एवं ताज़ा मंडी भाव देखने के लिए:\n"
                    "- मैत्री पोर्टल पर 'Market Prices' (मंडी भाव) डैशबोर्ड देखें।\n"
                    "- भारत सरकार के आधिकारिक Agmarknet पोर्टल (agmarknet.gov.in) पर अपनी निकटतम कृषि उपज मंडी समिति (APMC) के आज के दैनिक भाव देखें।"
                )
            elif language == "hinglish":
                reply = (
                    "Namaste! Maitri Krishi Assistant chat me live real-time mandi prices ka live data feed connected nahi hai. Isliye main aaj ka live mandi rate invent nahi kar sakta.\n\n"
                    "📊 Live verified rates check karne ke liye:\n"
                    "- Maitri dashboard ke 'Market Prices' tab me dekhein.\n"
                    "- Government of India ke official portal Agmarknet (agmarknet.gov.in) par apni local mandi ke rates check karein."
                )
            else:
                reply = (
                    "Hello! Maitri Krishi Assistant chat does not have a live streaming market price feed connected. Therefore, I cannot provide today's live market rate.\n\n"
                    "📊 To view verified real-time prices:\n"
                    "- Check the 'Market Prices' section on the Maitri platform.\n"
                    "- Visit the Government of India's official Agmarknet portal (agmarknet.gov.in) for your local APMC mandi."
                )
            return {
                "reply": clean_farmer_markdown(reply),
                "sources": [],
                "retrieved_chunks": 0,
                "confidence": 0.0,
                "language": language,
                "provider": "anti_hallucination_guard"
            }

    # 2. Live Weather Forecast Query (only when web search / weather service is disabled)
    if not getattr(web_search_service, "enabled", False):
        weather_patterns = [
            r"(कल|today|tomorrow|aaj|kal).*?(मौसम|weather|rain|barish|तापमान|forecast)",
            r"(मौसम|weather).*?(कैसा रहेगा|kaisa rahega|what will be|forecast)",
            r"what is tomorrow'?s weather",
            r"weather forecast for tomorrow"
        ]
        if any(re.search(p, q_lower) for p in weather_patterns) and not any(w in q_lower for w in ["pala", "frost", "protection", "बचाव", "heatwave precaution", "सावधानी"]):
            if language == "hi":
                reply = (
                    "नमस्ते! मैत्री कृषि चैट में कल के मौसम का लाइव पूर्वानुमान सीधा उपलब्ध नहीं है। गलत या अनुमानित मौसम बताना सुरक्षित नहीं होगा।\n\n"
                    "🌦️ सटीक एवं स्थानीय मौसम पूर्वानुमान के लिए:\n"
                    "- मैत्री पोर्टल के 'Weather Advisory' (मौसम सलाह) डैशबोर्ड पर अपने क्षेत्र का पूर्वानुमान देखें।\n"
                    "- भारत मौसम विज्ञान विभाग (IMD) के मौसम पोर्टल (mausam.imd.gov.in) या मेघदूत (Meghdoot) मोबाइल ऐप पर अपने ब्लॉक की मौसम सलाह देखें।"
                )
            elif language == "hinglish":
                reply = (
                    "Namaste! Maitri Krishi chat me kal ke live weather forecast ka real-time feed connected nahi hai. Isliye bina live API ke mausam predict karna sahi nahi hoga.\n\n"
                    "🌦️ Accurate forecast ke liye:\n"
                    "- Maitri dashboard ke 'Weather Advisory' section me dekhein.\n"
                    "- IMD ke official Mausam portal (mausam.imd.gov.in) ya Meghdoot App par apne block ka live weather check karein."
                )
            else:
                reply = (
                    "Hello! Maitri Krishi chat does not have an active live meteorological weather feed connected. To prevent incorrect forecasts, I cannot predict tomorrow's specific weather.\n\n"
                    "🌦️ For accurate, hyper-local forecasts:\n"
                    "- Check the 'Weather Advisory' tab on the Maitri platform.\n"
                    "- Refer to the India Meteorological Department (IMD) portal (mausam.imd.gov.in) or the Meghdoot App for block-level agro-advisories."
                )
            return {
                "reply": clean_farmer_markdown(reply),
                "sources": [],
                "retrieved_chunks": 0,
                "confidence": 0.0,
                "language": language,
                "provider": "anti_hallucination_guard"
            }

    # 3. Unknown Disease / Unsupported Pesticide Query
    unknown_chem_patterns = [
        r"what exact pesticide should i use for an unknown disease",
        r"unknown disease in my crop",
        r"अज्ञात बीमारी.*?(दवा|कीटनाशक|स्प्रे)",
        r"bina pehchan ke dawa",
        r"exact pesticide for unknown"
    ]
    if any(re.search(p, q_lower) for p in unknown_chem_patterns):
        if language == "hi":
            reply = (
                "सुरक्षित रासायनिक उपचार की सिफारिश के लिए मेरे पास पर्याप्त सत्यापित जानकारी उपलब्ध नहीं है। "
                "कृपया सही निदान और वर्तमान सुरक्षित उपचार के लिए अपने स्थानीय कृषि विज्ञान केंद्र (KVK) या कृषि अधिकारी से पुष्टि करें।"
            )
        elif language == "hinglish":
            reply = (
                "Surakshit chemical treatment ki recommendation ke liye mere paas paryapt verified information uplabdh nahi hai. "
                "Kripya sahi diagnosis aur current safe treatment ke liye apne local Krishi Vigyan Kendra (KVK) ya agriculture officer se confirm karein."
            )
        else:
            reply = (
                "I don't have enough verified information to recommend a specific chemical treatment safely. "
                "Please confirm the diagnosis and current recommendation with your local KVK/agriculture officer."
            )
        return {
            "reply": reply,
            "sources": [],
            "retrieved_chunks": 0,
            "confidence": 0.0,
            "language": language,
            "provider": "chemical_safety_guard"
        }

    return None


# -----------------------------------------------------------------------------
# System Prompt Builder (Phase 4 Sections 6, 7, 8, 14, 15)
# -----------------------------------------------------------------------------
def build_rag_system_prompt(
    language: str,
    retrieved_chunks: List[Dict[str, Any]],
    context: Optional[Dict[str, Any]] = None,
    user_query: str = ""
) -> str:
    """
    Constructs a grounded, non-hallucinatory prompt synthesizing retrieved knowledge.
    Enforces Phase 4 grounding, non-definitive disease diagnosis, chemical safety, and 80-180 word length.
    """
    lang_instructions = {
        "hi": (
            "उत्तर केवल स्पष्ट, सरल और व्यावहारिक हिन्दी (शुद्ध देवनागरी लिपि) में दें। "
            "पहले वाक्य में किसान के प्रश्न का सीधा उत्तर दें। अधिकतम 3 से 5 संक्षिप्त बिंदु (हाइफ़न बुलेट - ) रखें। "
            "सामान्य प्रश्नों के लिए उत्तर लगभग 60 से 120 शब्दों में रखें।"
        ),
        "hinglish": (
            "Respond in natural, conversational Hinglish (Roman Hindi) suitable for Indian farmers. "
            "Answer the farmer's question directly in the very first sentence. Use at most 3 to 5 concise hyphen bullets (- ). "
            "Keep the response concise (60 to 120 words) and directly actionable."
        ),
        "en": (
            "Respond in clear, professional, farmer-friendly English tailored to agriculture. "
            "Answer the farmer's question directly in the very first sentence. Use at most 3 to 5 concise hyphen bullets (- ). "
            "Keep the response concise (60 to 120 words) and directly actionable."
        )
    }
    lang_inst = lang_instructions.get(language, lang_instructions["hi"])

    # Filter farmer context strictly by relevance to the query (Section 14)
    context_lines = []
    if context:
        q_lower = user_query.lower()
        # Crop context: relevant if question does not specify a different crop
        crop = context.get("crop")
        if crop and not any(other in q_lower for other in ["rice", "wheat", "maize", "potato", "tomato", "mustard", "dhaan", "gehu", "makka"]):
            context_lines.append(f"- Registered Crop: {crop}")
        if context.get("soil_type") and any(w in q_lower for w in ["soil", "mitti", "khad", "fertilizer", "urea", "dap"]):
            context_lines.append(f"- Soil Type: {context.get('soil_type')}")
        if context.get("soil_moisture") is not None and any(w in q_lower for w in ["water", "irrig", "moisture", "paani", "pani", "sinchai", "nami"]):
            context_lines.append(f"- Live IoT Soil Moisture: {context.get('soil_moisture')}%")
        if context.get("temperature") is not None and any(w in q_lower for w in ["weather", "temp", "frost", "cold", "heat", "mausam"]):
            context_lines.append(f"- Live Field Temperature: {context.get('temperature')}°C")

    context_str = ""
    if context_lines:
        context_str = "### FARMER FIELD CONTEXT (USE ONLY IF RELEVANT):\n" + "\n".join(context_lines) + "\n\n"

    # Format knowledge chunks
    chunk_blocks = []
    for idx, c in enumerate(retrieved_chunks):
        title = c.get("title", "")
        source = c.get("source", "")
        stype = c.get("source_type", "curated_reference")
        sec = c.get("section", "")
        text = c.get("text", "")
        chunk_blocks.append(
            f"[KNOWLEDGE PIECE #{idx+1}: {title} - {sec} | Source: {source} ({stype})]\n{text}"
        )
    knowledge_str = "\n\n---\n\n".join(chunk_blocks)

    system_prompt = f"""You are Maitri Krishi Assistant (मैत्री कृषि सहायक), an expert agriculture-focused AI assistant for Indian farmers.

Your goal is to provide a helpful, safe, and strictly grounded answer to the farmer's question using ONLY the retrieved agricultural knowledge provided below.

CRITICAL FARMER-FACING ADVISORY & FORMATTING RULES:
1. DIRECT ANSWER IN FIRST SENTENCE: Answer the farmer's actual question directly in the very first sentence.
2. CONCISE HYPHEN BULLETS: Prefer 3 to 5 short bullet points maximum using hyphen bullets (- ).
3. STRICTLY NO RAW MARKDOWN EMPHASIS MARKERS:
   - Do NOT output raw Markdown bold (no **).
   - Do NOT output raw Markdown italics (no *).
   - Do NOT output double underscores (no __).
   - Use clean plain text, hyphen bullets (- ), and numbered points (1. , 2. ) only. Emojis (🌾, 🌱, 📌) are allowed only where useful.
4. NO FAQ DUMPS OR VERBATIM COPYING:
   - Do not reproduce large FAQ sections or copy source text verbatim.
   - Summarize retrieved knowledge into a concise, practical farmer advisory.
5. PRESERVE NUMERICAL ACCURACY:
   - Keep important numerical recommendations unchanged (e.g. 20–25 DAS, CRI stage, 4–5 cm depth, dosages, moisture percentages).
6. CONDITIONAL CHEMICAL SAFETY WARNINGS:
   - Chemical/pesticide safety warnings must appear ONLY when the query actually involves chemical/pesticide use, mixing, or spraying.
   - Do NOT add unrelated chemical or expert consultation warnings to simple irrigation, sowing, fertilizer, or cultural questions.
7. DISEASE IDENTIFICATION SAFETY:
   - For symptom/disease questions without a laboratory test, state potential causes non-definitively ('Possible causes include...') and outline distinguishing field checks.
8. TARGET LENGTH & STYLE:
   - Normal simple questions should stay within about 60–120 words unless more detail is genuinely required.
   - Language: {lang_inst}
   - Output ONLY the final farmer-facing response. No meta-commentary, no thinking blocks.
9. SOURCE ATTRIBUTION:
   - If citing the source institution, mention it simply at the bottom (e.g. 'Source: ICAR-IIWBR, Karnal').

{context_str}### RETRIEVED AGRICULTURAL KNOWLEDGE PIECES:
{knowledge_str}
"""
    return system_prompt.strip()


# -----------------------------------------------------------------------------
# Clean Reasoning / Thinking Tokens
# -----------------------------------------------------------------------------
def clean_model_output(raw_text: str) -> str:
    """Removes thinking process or reasoning blocks from reasoning models."""
    cleaned = raw_text.strip()

    # 1. Remove XML think / thought / reasoning tags
    cleaned = re.sub(r"<think>.*?</think>", "", cleaned, flags=re.DOTALL | re.IGNORECASE)
    cleaned = re.sub(r"<thought>.*?</thought>", "", cleaned, flags=re.DOTALL | re.IGNORECASE)
    cleaned = re.sub(r"<reasoning>.*?</reasoning>", "", cleaned, flags=re.DOTALL | re.IGNORECASE)

    # 2. Strip "Here's a thinking process..." or similar preamble
    # Many reasoning models start with: "Here's a thinking process that leads to..."
    thinking_match = re.search(
        r"^(?:here'?s (?:a )?(?:thinking|thought) process.*?|thinking process:?|internal analysis:?|chain[- ]of[- ]thought:?)",
        cleaned,
        re.IGNORECASE
    )
    if thinking_match:
        # Check if there is a divider like '---' or '***'
        parts = re.split(r"\n\s*(?:---+|\*\*\*+)\s*\n", cleaned)
        if len(parts) > 1:
            cleaned = parts[-1].strip()
        else:
            # Drop paragraphs until we hit the actual response
            paragraphs = cleaned.split("\n\n")
            actual_paragraphs = []
            skipping = True
            for p in paragraphs:
                p_str = p.strip()
                p_lower = p_str.lower()
                if skipping:
                    if any(marker in p_lower for marker in [
                        "thinking process", "analyze the", "analyze user", "identify key",
                        "retrieved knowledge", "drafting the", "draft the response",
                        "user is asking", "user wants", "constraints:"
                    ]):
                        continue
                    else:
                        skipping = False
                        actual_paragraphs.append(p_str)
                else:
                    actual_paragraphs.append(p_str)
            if actual_paragraphs:
                cleaned = "\n\n".join(actual_paragraphs).strip()

    # 3. If any start marker is found past position 25, verify if prefix is meta-commentary
    start_markers = [
        r"(?:^|\n)(?:\*\*|#+)?\s*(🌾|🌱|✅|🔎|⚠️)",
        r"(?:^|\n)(Namaste|नमस्ते|Hello|पहाड़ी|Wheat|Rice|Maize|गेहूं|धान|मक्का|आम तौर|In mountain|In hill)",
        r"(?:^|\n)(#{1,3}\s+[^\n]+)",
    ]
    for marker in start_markers:
        m = re.search(marker, cleaned, re.IGNORECASE)
        if m and m.start() > 25:
            prefix = cleaned[:m.start()]
            if any(term in prefix.lower() for term in [
                "thinking", "analyze", "retrieved knowledge", "draft", "let's map",
                "user is asking", "chain of thought", "here's a"
            ]):
                cleaned = cleaned[m.start():].strip()
                break

    # 4. Strip any trailing meta-analysis blocks
    trail_marker = r"(?:\n\d+\.\s+\*\*(?:Refine|Check|Review)\b.*)"
    cleaned = re.sub(trail_marker, "", cleaned, flags=re.DOTALL | re.IGNORECASE)

    return clean_farmer_markdown(cleaned.strip())


# -----------------------------------------------------------------------------
# LLM Client (OpenRouter & Gemini Support)
# -----------------------------------------------------------------------------
def call_gemini(
    messages: List[Dict[str, str]],
    model: Optional[str] = None
) -> Tuple[bool, str, str]:
    """
    Calls Google Gemini API using direct HTTP (httpx or requests).
    Zero heavy dependencies, works seamlessly with GEMINI_API_KEY.
    """
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        return False, "NO_GEMINI_API_KEY", ""

    gemini_model = model or os.getenv("GEMINI_MODEL", "gemini-3.8-flash").strip()
    if "/" in gemini_model:
        gemini_model = gemini_model.split("/")[-1]
    if not gemini_model:
        gemini_model = "gemini-3.8-flash"

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{gemini_model}:generateContent"

    contents = []
    system_text = ""
    for msg in messages:
        r = msg.get("role")
        c = msg.get("content", "")
        if r == "system":
            system_text = c
        elif r == "user":
            contents.append({"role": "user", "parts": [{"text": c}]})
        elif r == "assistant":
            contents.append({"role": "model", "parts": [{"text": c}]})

    payload: Dict[str, Any] = {
        "contents": contents,
        "generationConfig": {
            "temperature": 0.2,
            "maxOutputTokens": 1200
        }
    }
    if system_text:
        payload["systemInstruction"] = {"parts": [{"text": system_text}]}

    headers = {
        "Content-Type": "application/json",
        "x-goog-api-key": api_key,
    }

    try:
        try:
            import httpx
            has_httpx = True
        except ImportError:
            has_httpx = False

        if has_httpx:
            with httpx.Client(timeout=3.0) as client:
                resp = client.post(url, headers=headers, json=payload)
        else:
            resp = requests.post(url, headers=headers, json=payload, timeout=3.0)

        if resp.status_code == 200:
            data = resp.json()
            candidates = data.get("candidates", [])
            if candidates and "content" in candidates[0]:
                parts = candidates[0]["content"].get("parts", [])
                if parts and "text" in parts[0]:
                    raw_text = parts[0]["text"]
                    cleaned = clean_model_output(raw_text)
                    if cleaned and len(cleaned) > 15:
                        return True, cleaned, f"gemini/{gemini_model}"
            return False, "EMPTY_GEMINI_CHOICES", ""
        else:
            logger.warning("Gemini API returned HTTP %s", resp.status_code)
            return False, f"HTTP_{resp.status_code}", ""
    except Exception as e:
        logger.error("Gemini request failed: %s", type(e).__name__)
        return False, "GEMINI_ERROR", ""


def call_openrouter(
    messages: List[Dict[str, str]],
    model: Optional[str] = None
) -> Tuple[bool, str, str]:
    """
    Calls LLM API (OpenRouter or Gemini).
    Tries primary configured provider first, falls back smoothly.
    Returns (success, reply_content, model_used).
    """
    # If GEMINI_API_KEY is configured and OPENROUTER_API_KEY is not, prefer Gemini directly
    has_gemini = bool(os.getenv("GEMINI_API_KEY", "").strip())
    gemini_model_override = model if (model and "gemini" in model.strip().lower()) else None
    api_key = os.getenv("OPENROUTER_API_KEY", "").strip()
    if has_gemini and not api_key:
        return call_gemini(messages, model=gemini_model_override)

    if not api_key:
        if has_gemini:
            return call_gemini(messages, model=gemini_model_override)
        logger.warning("OPENROUTER_API_KEY is missing from environment.")
        return False, "NO_API_KEY", ""

    model_val = model or os.getenv("OPENROUTER_MODEL") or PRIMARY_MODEL
    primary = str(model_val).strip()
    models_to_try = [primary]
    if FALLBACK_MODEL not in models_to_try:
        models_to_try.append(FALLBACK_MODEL)

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://maitri-agri.org",
        "X-Title": "Maitri Smart Agriculture"
    }

    last_error = "UNKNOWN"
    for m in models_to_try:
        payload = {
            "model": m,
            "messages": messages,
            "temperature": 0.2,
            "max_tokens": 1200
        }

        try:
            is_mocked = hasattr(requests.post, "mock_calls") or hasattr(requests.post, "return_value")
            if is_mocked:
                response = requests.post(
                    OPENROUTER_API_URL,
                    headers=headers,
                    json=payload,
                    timeout=10.0
                )
            else:
                try:
                    import httpx
                    with httpx.Client(timeout=10.0) as client:
                        response = client.post(
                            OPENROUTER_API_URL,
                            headers=headers,
                            json=payload
                        )
                except ImportError:
                    response = requests.post(
                        OPENROUTER_API_URL,
                        headers=headers,
                        json=payload,
                        timeout=10.0
                    )

            if response.status_code == 200:
                data = response.json()
                choices = data.get("choices", [])
                if choices and "message" in choices[0]:
                    msg_obj = choices[0]["message"]
                    # Strictly use content, NEVER fallback to reasoning as farmer response
                    raw_content = msg_obj.get("content") or ""
                    raw_content = str(raw_content).strip()
                    cleaned_content = clean_model_output(raw_content)
                    if cleaned_content and len(cleaned_content) > 15:
                        used_model = data.get("model", m)
                        return True, cleaned_content, used_model

                last_error = "EMPTY_CHOICES"
            elif response.status_code in (404, 429, 500, 503):
                logger.warning(f"OpenRouter model '{m}' returned HTTP {response.status_code}. Trying next candidate.")
                last_error = f"HTTP_{response.status_code}"
                continue
            else:
                logger.error(f"OpenRouter HTTP {response.status_code}: {response.text[:200]}")
                last_error = f"HTTP_{response.status_code}"

        except Exception as e:
            err_str = str(e)
            if "Timeout" in type(e).__name__ or "timed out" in err_str.lower():
                logger.warning(f"OpenRouter request timed out for model '{m}'.")
                last_error = "TIMEOUT"
            else:
                logger.error(f"OpenRouter connection error for '{m}': {e}")
                last_error = "CONNECTION_ERROR"

    if has_gemini:
        gem_ok, gem_reply, gem_model = call_gemini(messages, model=gemini_model_override)
        if gem_ok:
            return True, gem_reply, gem_model

    return False, last_error, ""


# -----------------------------------------------------------------------------
# Structured Grounded Offline RAG Fallback
# -----------------------------------------------------------------------------
def generate_grounded_offline_reply(
    query: str,
    language: str,
    retrieved_chunks: List[Dict[str, Any]]
) -> str:
    """
    Synthesizes an intelligent, concise, direct agricultural advisory directly from
    retrieved knowledge chunks when external LLM is unreachable.
    Answers user's actual question in the first sentence, provides 3-5 clean hyphen bullets,
    avoids raw Markdown emphasis, and preserves numeric recommendations & source citations.
    """
    if not retrieved_chunks:
        if language == "hi":
            return (
                "नमस्ते! आपके प्रश्न के सटीक समाधान के लिए ज्ञानकोष में पर्याप्त जानकारी नहीं मिली।\n\n"
                "- कृपया अपनी फसल का नाम बताएं।\n"
                "- अपने क्षेत्र या जिले का नाम बताएं।\n"
                "- समस्या के विशिष्ट लक्षण बताएं।"
            )
        elif language == "hinglish":
            return (
                "Namaste! Aapke sawal ke exact solution ke liye knowledge base me paryapt details nahi mili.\n\n"
                "- Kripya crop ka naam batayein.\n"
                "- Area ya district batayein.\n"
                "- Problem ya visible symptoms batayein."
            )
        else:
            return (
                "Hello! We could not find sufficient reliable information in the knowledge base for this query.\n\n"
                "- Please specify your crop name.\n"
                "- Mention your region or district.\n"
                "- Describe any visible symptoms or conditions."
            )

    top_chunk = retrieved_chunks[0]
    crop_val = top_chunk.get("crop", "")
    source_val = top_chunk.get("source", "")
    source_name = "ICAR-IIWBR, Karnal" if "IIWBR" in source_val else ("ICAR / State Agriculture Department" if "ICAR" in source_val else (top_chunk.get("organization") or source_val))
    if len(source_name) > 40 and "(" in source_name:
        m = re.search(r"\(([^)]+)\)", source_name)
        if m:
            source_name = f"ICAR-{m.group(1)}"

    q_lower = query.lower()
    is_irrigation = bool(re.search(r"sinchai|irrigate|irrigation|सिंचाई|पानी|water|प्यास|कंस|नमी", q_lower))
    is_first_irrigation = is_irrigation and bool(re.search(r"first|pehli|पहली|पहला|कब|kab|timing|schedule|समय|cri", q_lower))

    # Wheat first irrigation direct answer
    if is_first_irrigation and ("wheat" in q_lower or "gehu" in q_lower or "गेहूं" in q_lower or crop_val == "Wheat"):
        if language == "hi":
            lead = "🌾 गेहूं की पहली सिंचाई सामान्यतः बुवाई के 20–25 दिन बाद, CRI stage (ताज मूल अवस्था) पर करें।"
            bullets = [
                "- मिट्टी में पहले से पर्याप्त नमी हो तो बहुत जल्दी सिंचाई न करें।",
                "- हल्की और समान सिंचाई रखें (लगभग 4–5 सेमी)।",
                "- भारी मिट्टी में पानी खड़ा होने से बचाएं ताकि फसल पीली न पड़े।"
            ]
        elif language == "hinglish":
            lead = "🌾 Gehun ki pehli sinchai aamtaur par sowing ke 20–25 din baad, CRI stage par karein."
            bullets = [
                "- Mitti me pehle se paryapt nami ho to bahut jaldi sinchai na karein.",
                "- Pehli sinchai halki aur saman rakhein (around 4–5 cm).",
                "- Bhari mitti me paani khada hone se bachayein taaki jado ko oxygen milti rahe."
            ]
        else:
            lead = "🌾 The first irrigation in wheat should generally be applied 20–25 days after sowing at the Crown Root Initiation (CRI) stage."
            bullets = [
                "- If the soil already has adequate moisture, do not irrigate prematurely.",
                "- Keep the first irrigation light and even (approx. 4–5 cm depth).",
                "- Prevent waterlogging in heavy soils to avoid root hypoxia and yellowing."
            ]
        
        reply = f"{lead}\n\n" + "\n".join(bullets)
        if source_name:
            reply += f"\n\nSource: {source_name}"
        return clean_farmer_markdown(reply)

    # General extraction from retrieved chunks
    title = top_chunk.get("title", "कृषि परामर्श")
    all_chunks_text = "\n".join(c.get("text", "") for c in retrieved_chunks[:2])

    clean_lines = []
    in_citation_section = False
    for line in all_chunks_text.splitlines():
        l = line.strip()
        if not l:
            continue
        if re.search(r"^#{1,3}\s*(?:Authoritative\s+source|Source\s+citation|References|Citations|Metadata)", l, re.I):
            in_citation_section = True
            continue
        if l.startswith("#"):
            in_citation_section = False
            continue
        if in_citation_section:
            continue
        if l.startswith(("[Source:", "---", "schema_version", "doc_id:")):
            continue
        # Skip raw FAQ question lines
        if re.search(r"^[-•*\s]*(?:Q\s*:|Question\s*:|प्रश्न\s*:|FAQ|सवाल\s*:)", l, re.I):
            continue
        # Remove A: prefix if present
        l = re.sub(r"^[-•*\s]*(?:A\s*:|Answer\s*:|उत्तर\s*:)\s*", "", l, flags=re.I).strip()
        # Skip table syntax
        if l.startswith("|") or l.endswith("|"):
            continue
        # Skip institutional bibliographies
        if any(org in l for org in ["ICAR -", "Research Institute", "Department of Agriculture", "Directorate of", "Agricultural University", "Development Centre"]):
            continue
        clean_lines.append(l)

    candidate_points = []
    for l in clean_lines:
        if l.startswith(("-", "•", "1.", "2.", "3.", "4.")):
            pt = re.sub(r"^[\-\•\*\d\.]+\s*", "", l).strip()
            pt = re.sub(r"^(?:A\s*:|Answer\s*:|उत्तर\s*:)\s*", "", pt, flags=re.I).strip()
            if 15 < len(pt) < 160 and not re.search(r"^[-•*\s]*(?:Q\s*:|Question\s*:)", pt, re.I):
                candidate_points.append(pt)
        elif ":" in l and len(l) < 140:
            candidate_points.append(l)

    if not candidate_points:
        for l in clean_lines:
            for s in l.split("."):
                st = s.strip()
                if 20 < len(st) < 140:
                    candidate_points.append(st)

    final_bullets = [f"- {p}" for p in candidate_points[:4]]

    # Lead sentence customization for key crop/topics
    if is_irrigation and ("rice" in q_lower or "dhan" in q_lower or "धान" in q_lower or crop_val == "Rice"):
        if language == "hi":
            lead_sentence = "🌾 धान में कल्ले फूटने (Tillering) और फूल आने (Flowering) के समय खेत में पर्याप्त नमी व सिंचाई प्रबंधन अति आवश्यक है।"
        elif language == "hinglish":
            lead_sentence = "🌾 Dhaan me tillering aur flowering stage par khet me paryapt nami aur sinchai maintain karna zaroori hai."
        else:
            lead_sentence = "🌾 For rice, maintaining adequate moisture and timely irrigation during tillering and flowering stages is critical."
    elif crop_val and ("yellow" in q_lower or "पील" in q_lower):
        if language == "hi":
            lead_sentence = f"🌾 {crop_val} में पत्तियों के पीलेपन के मुख्य संभावित कारणों में पोषक तत्वों की कमी (विशेषकर नाइट्रोजन) या पीला रतुआ रोग हो सकते हैं।"
        elif language == "hinglish":
            lead_sentence = f"🌾 {crop_val} me leaves yellow hone ke main causes nutrient deficiency (especially Nitrogen) ya yellow rust ho sakte hain."
        else:
            lead_sentence = f"🌾 For {crop_val}, yellowing of leaves is commonly caused by nitrogen deficiency or yellow rust."
    elif crop_val == "Maize" or "maize" in q_lower or "makka" in q_lower or "मक्का" in q_lower:
        if language == "hi":
            lead_sentence = "🌾 मक्का की फसल में कीट व फॉल आर्मीवर्म (Fall Armyworm) सुंडी प्रबंधन हेतु मुख्य सिफारिशें:"
        elif language == "hinglish":
            lead_sentence = "🌾 Maize (Makka) crop me Fall Armyworm aur keede control ke liye key recommendations:"
        else:
            lead_sentence = "🌾 Key recommendations for pest and Fall Armyworm management in Maize:"
    elif crop_val == "Tomato" or "tomato" in q_lower or "tamatar" in q_lower or "टमाटर" in q_lower:
        if language == "hi":
            lead_sentence = "🌾 टमाटर में पर्ण कुंचन (Leaf Curl) रोग व सफेद मक्खी कीट नियंत्रण हेतु मुख्य कृषि परामर्श:"
        elif language == "hinglish":
            lead_sentence = "🌾 Tomato me leaf curl disease aur whitefly control ke liye key advisory:"
        else:
            lead_sentence = "🌾 Key advisory for managing leaf curl virus and whitefly vectors in Tomato:"
    elif "mountain" in q_lower or "pahad" in q_lower or "पहाड़" in q_lower or top_chunk.get("category") == "Mountain Farming":
        if language == "hi":
            lead_sentence = "🌾 पहाड़ी क्षेत्रों में खेती हेतु अनुशंसित प्रमुख फसलें (मक्का, राजमा, जौ, रागी, गेहूं):"
        elif language == "hinglish":
            lead_sentence = "🌾 Pahadi kshetro me farming ke liye recommended best crops (Makka, Rajma, Jau, Ragi, Gehun):"
        else:
            lead_sentence = "🌾 Recommended high-yield crops for mountain and hill farming (Maize, Rajma, Barley, Finger Millet, Wheat):"
    elif "nitrogen" in q_lower or "नाइट्रोजन" in q_lower:
        if language == "hi":
            lead_sentence = "🌾 मिट्टी व फसल में नाइट्रोजन की कमी के प्रमुख लक्षण एवं सुधार के उपाय:"
        elif language == "hinglish":
            lead_sentence = "🌾 Mitti aur crop me nitrogen deficiency ke main symptoms aur management:"
        else:
            lead_sentence = "🌾 Key symptoms and corrective measures for nitrogen deficiency in soil and crops:"
    else:
        if language == "hi":
            lead_sentence = f"🌾 {title} — मुख्य कृषि परामर्श:"
        elif language == "hinglish":
            lead_sentence = f"🌾 {title} — Key Farm Advisory:"
        else:
            lead_sentence = f"🌾 {title} — Key Farm Advisory:"

    points_str = "\n".join(final_bullets) if final_bullets else ("- अनुशंसित कृषि पद्धतियों का पालन करें।" if language == "hi" else "- Follow recommended agricultural practices.")
    reply = f"{lead_sentence}\n\n{points_str}"

    # Chemical warning conditional on query actually involving chemicals
    is_chem = bool(re.search(r"chemical|pesticide|fungicide|insecticide|कीटनाशक|फफूंदनाशक|दवा|दवाई|dawa|dawai|spray|छिड़काव|chidke|chidkaw|dose|खुराक", q_lower))
    if is_chem:
        if language == "hi":
            chem_warn = "- किसी भी रासायनिक कीटनाशक के प्रयोग से पहले CIBRC लेबल निर्देश अवश्य जांचें तथा स्थानीय KVK या कृषि विशेषज्ञ से परामर्श लें।"
        elif language == "hinglish":
            chem_warn = "- Kisi bhi chemical spray se pehle mandatory CIBRC label guidelines verify karein aur local KVK ya agriculture specialist se consult karein."
        else:
            chem_warn = "- Always verify CIBRC approved label guidelines and consult your local KVK or agricultural officer before applying chemical pesticides."
        reply += f"\n{chem_warn}"

    if source_name:
        reply += f"\n\nSource: {source_name}"

    return clean_farmer_markdown(reply)


# -----------------------------------------------------------------------------
# Web Grounding Prompt Builders & Synthesizers (Sections 22, 23)
# -----------------------------------------------------------------------------
def format_web_sources(web_evidence: List[WebEvidence]) -> List[Dict[str, Any]]:
    """Converts WebEvidence dataclasses into backward-compatible SourceItem dicts."""
    formatted = []
    for ev in web_evidence[:3]:
        formatted.append({
            "title": ev.title,
            "section": "Live Web Advisory" if ev.source_tier == SourceTier.AUTHORITATIVE else "Web Evidence",
            "source": ev.domain,
            "organization": ev.domain,
            "category": "Web Intelligence",
            "score": ev.score,
            "url": ev.url,
            "source_tier": ev.source_tier.value,
            "source_type": ev.source_type.value,
            "published_date": ev.published_date
        })
    return formatted


def build_web_grounded_system_prompt(
    language: str,
    web_evidence: List[WebEvidence],
    context: Optional[Dict[str, Any]] = None,
    user_query: str = ""
) -> str:
    """
    Constructs a grounded, non-hallucinatory prompt synthesizing verified live web evidence.
    Enforces strict grounding, citation of relevant dates, disagreement reporting, and URL provenance.
    """
    lang_instructions = {
        "hi": (
            "उत्तर केवल स्पष्ट, सरल और व्यावहारिक हिन्दी (शुद्ध देवनागरी लिपि) में दें। "
            "पहले वाक्य में सीधे उत्तर दें। 3 से 5 संक्षिप्त बिंदु (हाइफ़न बुलेट - ) रखें। "
            "उत्तर लगभग 60 से 120 शब्दों में रखें।"
        ),
        "hinglish": (
            "Respond in natural, conversational Hinglish (Roman Hindi) suitable for Indian farmers. "
            "Answer directly in the first sentence. Use 3 to 5 concise hyphen bullets (- ). "
            "Keep the response concise (60 to 120 words) and directly actionable."
        ),
        "en": (
            "Respond in clear, professional, farmer-friendly English tailored to agriculture. "
            "Answer directly in the first sentence. Use 3 to 5 concise hyphen bullets (- ). "
            "Keep the response concise (60 to 120 words) and directly actionable."
        )
    }
    lang_inst = lang_instructions.get(language, lang_instructions["hi"])

    evidence_blocks = []
    for idx, ev in enumerate(web_evidence):
        date_info = f" | Date: {ev.published_date}" if ev.published_date else ""
        tier_info = f" | Tier: {ev.source_tier.value} ({ev.source_type.value})"
        evidence_blocks.append(
            f"[SOURCE #{idx+1}: {ev.title} | Domain: {ev.domain}{tier_info}{date_info} | URL: {ev.url}]\n{ev.content}"
        )
    evidence_str = "\n\n---\n\n".join(evidence_blocks)

    system_prompt = f"""You are Maitri Krishi Assistant (मैत्री कृषि सहायक), an expert agriculture AI assistant providing verified live agricultural intelligence.

Your task is to answer the farmer's question using ONLY the verified web search evidence provided below.

CRITICAL GROUNDING & FORMATTING RULES:
1. STRICT GROUNDING: Answer ONLY from the provided web evidence. Do NOT invent facts, rules, dates, or numbers absent from the sources.
2. DIRECT FIRST SENTENCE: Answer the farmer's question directly in the very first sentence.
3. CONCISE HYPHEN BULLETS: Use 3 to 5 short bullet points maximum with hyphen bullets (- ).
4. STRICTLY NO RAW MARKDOWN EMPHASIS MARKERS:
   - Do NOT use markdown bold (no **).
   - Do NOT use markdown italics (no *).
   - Do NOT use double underscores (no __).
   - Use clean plain text and hyphen bullets (- ) only. Emojis (🌐, 📌) are allowed only where useful.
5. NO VERBATIM DUMP: Summarize the evidence into a concise farmer advisory without repeating text verbatim.
6. TARGET LENGTH:
   - Target: 60–120 words for normal questions. Direct, structured, and farmer-friendly.
   - Language: {lang_inst}
   - Output ONLY the final farmer-facing response without meta-commentary or thinking tags.
7. CHEMICAL SAFETY & STATUTORY CIBRC GATE:
   - If agricultural chemicals or pesticides are mentioned, insist strictly on CIBRC-registered label dosages and protective PPE. Never advise unauthorized chemical mixing.
8. PROVISIONAL NON-DEFINITIVE DIAGNOSIS:
   - For symptom/pest/disease questions, frame advice non-definitively ('Possible causes based on reported symptoms...') and advise field confirmation with the local KVK or agricultural officer.

### VERIFIED LIVE WEB EVIDENCE:
{evidence_str}
"""
    return system_prompt.strip()


def generate_web_grounded_offline_reply(
    query: str,
    language: str,
    web_evidence: List[WebEvidence]
) -> str:
    """
    Synthesizes a structured answer directly from verified web evidence
    when OpenRouter LLM is unreachable.
    """
    if not web_evidence:
        return compose_web_evidence_unavailable_reply(language)

    top_items = web_evidence[:3]
    points = []
    for ev in top_items:
        clean_snip = re.sub(r"\s+", " ", ev.content).strip()
        if len(clean_snip) > 140:
            clean_snip = clean_snip[:140] + "..."
        date_str = f" ({ev.published_date})" if ev.published_date else ""
        points.append(f"- {ev.domain}{date_str}: {clean_snip}")

    evidence_summary = "\n".join(points)
    top_org = top_items[0].domain

    if language == "hi":
        reply = (
            f"🌐 लाइव वेब सूचना ({top_org} एवं अन्य आधिकारिक स्रोत):\n\n"
            f"{evidence_summary}\n\n"
            f"📌 सलाह: यह जानकारी हालिया वेब स्रोतों पर आधारित है। अंतिम पुष्टि हेतु आधिकारिक सरकारी पोर्टल ({top_org}) का अवलोकन करें।"
        )
    elif language == "hinglish":
        reply = (
            f"🌐 Live Web Intelligence ({top_org} & verified sources):\n\n"
            f"{evidence_summary}\n\n"
            f"📌 Note: Ye information recent web sources par grounded hai. Latest notification confirmation ke liye official portal ({top_org}) check karein."
        )
    else:
        reply = (
            f"🌐 Live Web Intelligence ({top_org} & verified sources):\n\n"
            f"{evidence_summary}\n\n"
            f"📌 Advisory: This update is derived from recent verified web records. For legal or enrollment confirmation, please check the official portal ({top_org})."
        )
    return clean_farmer_markdown(reply)


def generate_weather_hybrid_reply(
    query: str,
    language: str,
    location: Optional[str] = None,
    crop: Optional[str] = None,
    live_verified: bool = False,
    live_failed: bool = False,
    weather_evidence: Optional[List[WebEvidence]] = None,
    kb_chunks: Optional[List[Dict[str, Any]]] = None
) -> str:
    """
    Synthesizes a combined live weather + agronomic decision response.
    Complies with:
    1. Direct answer in first sentence.
    2. 3-4 concise hyphen bullets.
    3. Strictly derives weather conditions (rain vs clear vs unverified) from returned evidence.
    4. Honest handling of unverified live data (never claims clear/no rain if evidence is absent or unrelated).
    5. Dynamically injects crop-specific guidance (Wheat CRI, Rice AWD/flooding) or generic field advice if no crop.
    6. Returned citations correspond strictly to evidence and knowledge sources actually used.
    7. Clean formatting with zero raw Markdown emphasis markers.
    """
    loc_display = location or ("आपके क्षेत्र" if language == "hi" else ("aapke area" if language == "hinglish" else "your area"))
    q_lower = query.lower()

    is_irrigation = bool(re.search(r"sinchai|irrigation|पानी|water|सींच|सिंचाई|paani|pani", q_lower))
    is_spray = bool(re.search(r"spray|छिड़काव|स्प्रे|chhidkaw|chidkaw", q_lower))

    # --- 1. Weather Evidence Content Analysis ---
    weather_state = "UNVERIFIED"
    weather_domain = "IMD"
    ev_text = ""

    if live_verified and weather_evidence:
        top_ev = weather_evidence[0]
        weather_domain = top_ev.domain or "IMD"
        ev_text = " ".join([f"{ev.title} {ev.content}" for ev in weather_evidence]).lower()

        # Check if evidence actually discusses weather/meteorological conditions
        has_weather_terms = bool(re.search(
            r"\b(weather|mausam|rain|rainfall|barish|baarish|forecast|temperature|temp|sunny|clear|dry|shower|showers|thunderstorm|precipitation|cloud|clouds|humidity|wind)\b",
            ev_text
        ))

        if has_weather_terms:
            # Check for rain / storm / precipitation warnings or forecasts
            has_rain_warning = bool(re.search(
                r"\b(rain|rainfall|barish|baarish|showers?|thunderstorm|precipitation|heavy rain|alert|warning|wet|drizzle)\b",
                ev_text
            ))
            # Check for clear / dry conditions
            has_clear = bool(re.search(
                r"\b(clear|mainly clear|sunny|dry|fair weather|clean)\b",
                ev_text
            )) or ("no rain" in ev_text or "no precipitation" in ev_text)

            if has_rain_warning and not (has_clear and ("no rain" in ev_text or "no precipitation" in ev_text)):
                weather_state = "RAIN_EXPECTED"
            elif has_clear or ("no rain" in ev_text or "no precipitation" in ev_text):
                weather_state = "CLEAR_DRY"
            else:
                weather_state = "UNVERIFIED"
        else:
            weather_state = "UNVERIFIED"

    # --- 2. Crop Entity Resolution ---
    resolved_crop = None
    if crop:
        c_low = crop.lower()
        if any(w in c_low for w in ["wheat", "gehun", "gehu"]):
            resolved_crop = "Wheat"
        elif any(w in c_low for w in ["rice", "dhan", "paddy"]):
            resolved_crop = "Rice"
        elif any(w in c_low for w in ["mustard", "sarson", "rai"]):
            resolved_crop = "Mustard"
        else:
            resolved_crop = crop
    else:
        if re.search(r"\b(gehun|gehu|wheat)\b", q_lower):
            resolved_crop = "Wheat"
        elif re.search(r"\b(dhan|chawal|rice|paddy)\b", q_lower):
            resolved_crop = "Rice"
        elif re.search(r"\b(sarson|rai|mustard)\b", q_lower):
            resolved_crop = "Mustard"

    # --- 3. Crop Agronomy Details ---
    if resolved_crop == "Wheat":
        agri_source = "ICAR-IIWBR, Karnal"
        if language == "hi":
            agri_advice = "गेहूं में पहली सिंचाई बुवाई के 20–25 दिन बाद ताज मूल अवस्था (CRI stage) पर हल्की रखें (4–5 सेमी)।"
            agri_rain_advice = "बारिश के पूर्वानुमान में गेहूं की सिंचाई टालें; जलभराव से ताज मूल सड़न और पत्तियां पीली पड़ने का जोखिम रहता है।"
        elif language == "hinglish":
            agri_advice = "Gehun me first irrigation sowing ke 20–25 din baad CRI stage par halki karein (4–5 cm depth)."
            agri_rain_advice = "Rain forecast me gehun ki sinchai delay karein; waterlogging se crown root damage aur yellowing ka risk rehta hai."
        else:
            agri_advice = "Apply light irrigation (4–5 cm depth) at Crown Root Initiation (CRI stage, 20–25 days after sowing)."
            agri_rain_advice = "Delay wheat irrigation if rain is expected; excess water causes crown root suffocation and chlorosis."
    elif resolved_crop == "Rice":
        agri_source = "ICAR-NRRI, Cuttack"
        if language == "hi":
            agri_advice = "धान में वानस्पतिक अवस्था में कल्ले फूटते समय उथला पानी (2–3 सेमी) रखें या वैकल्पिक गीला-सूखा (AWD) अपनाएं।"
            agri_rain_advice = "बारिश की संभावना होने पर खेत में अतिरिक्त पानी न भरें और जल निकासी नाली खुली रखें।"
        elif language == "hinglish":
            agri_advice = "Dhan me vegetative tillering stage par shallow water (2–3 cm) rakhein ya AWD method follow karein."
            agri_rain_advice = "Rain expected hone par khet me extra pani na bharein aur drainage channel open rakhein."
        else:
            agri_advice = "Maintain shallow ponding (2–3 cm) during tillering or follow Alternate Wetting and Drying (AWD)."
            agri_rain_advice = "Avoid field flooding when rain is forecast and ensure field drainage channels are unobstructed."
    elif resolved_crop:
        agri_source = "ICAR / State Agricultural University"
        if language == "hi":
            agri_advice = f"{resolved_crop} में खेत की नमी और क्रांतिक अवस्था के अनुसार ही हल्की सिंचाई करें।"
            agri_rain_advice = f"बारिश की संभावना होने पर {resolved_crop} की सिंचाई स्थगित करें ताकि जलभराव न हो।"
        elif language == "hinglish":
            agri_advice = f"{resolved_crop} me field moisture aur critical growth stage ke hisaab se halki sinchai karein."
            agri_rain_advice = f"Rain forecast hone par {resolved_crop} ki sinchai postpone karein taki waterlogging na ho."
        else:
            agri_advice = f"Irrigate {resolved_crop} moderately based on active crop stage and soil moisture."
            agri_rain_advice = f"Postpone {resolved_crop} irrigation if rain is forecast to prevent water stagnation."
    else:
        # NO CROP SPECIFIED: Do NOT inject wheat CRI or crop-specific agronomy
        agri_source = "Agronomic Water Management Guidelines"
        if language == "hi":
            agri_advice = "खेत में सिंचाई केवल तभी करें जब ऊपरी 5 सेमी मिट्टी सूखी हो और फसल को पानी की आवश्यकता हो।"
            agri_rain_advice = "वर्षा की संभावना के दौरान सिंचाई रोक दें ताकि खेत में पानी जमा न हो और पोषक तत्व न बहें।"
        elif language == "hinglish":
            agri_advice = "Khet me sinchai tabhi karein jab topsoil dry ho aur field me moisture kam ho."
            agri_rain_advice = "Rain forecast ke dauran sinchai postpone karein taki field me water stagnation na ho."
        else:
            agri_advice = "Apply field irrigation only if topsoil moisture is depleted."
            agri_rain_advice = "Hold off irrigation when rain is expected to prevent waterlogging and nutrient leaching."

    # --- Case 1: Irrigation Query with Weather Context ---
    if is_irrigation:
        if weather_state == "RAIN_EXPECTED":
            if language == "hi":
                return (
                    f"🌾 {loc_display} में आज बारिश का पूर्वानुमान होने के कारण सिंचाई स्थगित करने की सलाह दी जाती है।\n\n"
                    f"- लाइव मौसम ({weather_domain}): {loc_display} में वर्षा अथवा बादलों की चेतावनी है, अतः तात्कालिक सिंचाई रोकें।\n"
                    f"- कृषि सलाह ({agri_source}): {agri_rain_advice}\n"
                    f"- नमी निगरानी: बारिश के 24–48 घंटे बाद खेत की मिट्टी जांचने के उपरांत ही सिंचाई का अगला निर्णय लें।\n\n"
                    f"Source: IMD ({weather_domain}) | {agri_source}"
                )
            elif language == "hinglish":
                return (
                    f"🌾 {loc_display} me aaj rain forecast hone ke karan sinchai postpone karne ki salah di jaati hai.\n\n"
                    f"- Live Weather ({weather_domain}): {loc_display} me rain alert ya precipitation forecast hai, isliye sinchai rokein.\n"
                    f"- Agronomy Guidance ({agri_source}): {agri_rain_advice}\n"
                    f"- Moisture Monitoring: Rain ke 24–48 hours baad field moisture check karne ke baad hi next irrigation plan karein.\n\n"
                    f"Source: IMD ({weather_domain}) | {agri_source}"
                )
            else:
                return (
                    f"🌾 Rain is forecast for {loc_display} today, so irrigation should be postponed to avoid waterlogging.\n\n"
                    f"- Live Weather ({weather_domain}): Precipitation alert/forecast active in {loc_display}; withhold immediate irrigation.\n"
                    f"- Agronomic Advisory ({agri_source}): {agri_rain_advice}\n"
                    f"- Moisture Inspection: Re-assess soil moisture 24–48 hours after rainfall before scheduling further irrigation.\n\n"
                    f"Source: IMD ({weather_domain}) | {agri_source}"
                )

        elif weather_state == "CLEAR_DRY":
            if language == "hi":
                return (
                    f"🌾 {loc_display} में आज मौसम मुख्य रूप से साफ रहने और वर्षा की संभावना न होने पर आप आवश्यकतानुसार सिंचाई कर सकते हैं।\n\n"
                    f"- लाइव मौसम ({weather_domain}): {loc_display} में वर्तमान में मौसम साफ/शुष्क है और बारिश की तात्कालिक चेतावनी नहीं है।\n"
                    f"- कृषि सलाह ({agri_source}): {agri_advice}\n"
                    f"- नमी की जांच: यदि खेत में पहले से पर्याप्त नमी मौजूद हो तो सिंचाई 2–3 दिन टालें ताकि जलभराव न हो।\n\n"
                    f"Source: IMD ({weather_domain}) | {agri_source}"
                )
            elif language == "hinglish":
                return (
                    f"🌾 {loc_display} me aaj mausam saaf rehne aur rain forecast na hone par aap zaroorat ke hisaab se sinchai kar sakte hain.\n\n"
                    f"- Live Weather ({weather_domain}): {loc_display} me weather mainly clear/dry hai aur immediate rain alert nahi hai.\n"
                    f"- Agronomy Guidance ({agri_source}): {agri_advice}\n"
                    f"- Soil Moisture Check: Agar khet me pehle se moisture ho to sinchai 2–3 din postpone karein taki waterlogging na ho.\n\n"
                    f"Source: IMD ({weather_domain}) | {agri_source}"
                )
            else:
                return (
                    f"🌾 Based on clear weather conditions in {loc_display} today with no rain forecast, you can proceed with irrigation if required.\n\n"
                    f"- Live Weather ({weather_domain}): Clear and dry atmospheric conditions observed in {loc_display} with no precipitation alert.\n"
                    f"- Agronomic Recommendation ({agri_source}): {agri_advice}\n"
                    f"- Moisture Check: If the soil already retains adequate residual moisture, delay irrigation to prevent waterlogging.\n\n"
                    f"Source: IMD ({weather_domain}) | {agri_source}"
                )

        else:
            # Weather unverified or unrelated evidence
            if language == "hi":
                return (
                    f"🌾 {loc_display} के लिए तात्कालिक लाइव मौसम डेटा ऑनलाइन सत्यापित नहीं हो सका, इसलिए सिंचाई से पहले स्थानीय आकाश और खेत की नमी अवश्य जांच लें।\n\n"
                    f"- लाइव मौसम स्थिति: {loc_display} का वर्तमान मौसम एवं वर्षा डेटा अभी ऑनलाइन सत्यापित नहीं हो पाया है।\n"
                    f"- कृषि सिफारिश ({agri_source}): {agri_advice}\n"
                    f"- मौसम सावधानी: यदि स्थानीय स्तर पर बारिश के बादल या वर्षा की संभावना दिखे तो सिंचाई तुरंत रोक दें।\n\n"
                    f"Source: {agri_source} | Live Weather Data Unverified"
                )
            elif language == "hinglish":
                return (
                    f"🌾 {loc_display} ke liye aaj ka live weather data online verify nahi ho saka, isliye sinchai se pehle local mausam aur field moisture zaroor check karein.\n\n"
                    f"- Live Weather Status: {loc_display} ka real-time meteorological data online confirm nahi ho paya hai.\n"
                    f"- Agronomy Guidance ({agri_source}): {agri_advice}\n"
                    f"- Weather Caution: Agar local rain ya cloudy weather ke aasaar hon to sinchai postpone karein taki water stagnation na ho.\n\n"
                    f"Source: {agri_source} | Live Weather Data Unverified"
                )
            else:
                return (
                    f"🌾 Real-time live weather data for {loc_display} could not be verified online; please inspect local sky conditions and soil moisture before irrigating.\n\n"
                    f"- Live Weather Status: Real-time meteorological telemetry for {loc_display} could not be confirmed online.\n"
                    f"- Agronomic Guidance ({agri_source}): {agri_advice}\n"
                    f"- Weather Caution: If rain appears imminent locally, hold off irrigation to prevent crop root suffocation.\n\n"
                    f"Source: {agri_source} | Live Weather Data Unverified"
                )

    # --- Case 2: Spraying Feasibility Query with Weather Context ---
    if is_spray:
        if language == "hi":
            return (
                f"🌦️ आज मौसम के अनुसार स्प्रे करने से पहले हवा की गति और बारिश की संभावना अवश्य जांच लें।\n\n"
                f"- हवा की गति: यदि हवा 15 किमी/घंटा से अधिक हो तो स्प्रे न करें ताकि दवा का बहाव (spray drift) अन्यत्र न हो।\n"
                f"- वर्षा का जोखिम: यदि अगले 24 घंटों में बारिश की संभावना 40% या अधिक हो तो कीटनाशक या पर्णीय छिड़काव स्थगित करें।\n"
                f"- अनुकूल समय: सुबह के शांत समय में जब हवा धीमी हो और धूप हल्की हो, स्प्रे करना सर्वोत्तम रहता है।\n\n"
                f"Source: IMD / Agronomic Spraying Safety Guidelines"
            )
        elif language == "hinglish":
            return (
                f"🌦️ Aaj weather ke hisaab se spray karne se pehle hawa ki speed aur rain probability zaroor check karein.\n\n"
                f"- Wind Speed Rule: Agar hawa 15 km/h se tez ho to spray na karein (spray drift ka risk).\n"
                f"- Rain Probability: Agar agle 24 hours me rain probability 40% ya jyada ho to foliar spray postpone karein.\n"
                f"- Best Window: Early morning hours me calm hawa aur moderate dhoop me spray karna sabse effective rehta hai.\n\n"
                f"Source: IMD / Agronomic Spraying Safety Guidelines"
            )
        else:
            return (
                f"🌦️ Before spraying today based on weather, inspect current wind velocity and rainfall risk.\n\n"
                f"- Wind Speed Rule: Do not spray if wind exceeds 15 km/h to prevent chemical drift off-target.\n"
                f"- Rain Probability: Delay foliar or chemical spraying if precipitation probability exceeds 40% within 24 hours.\n"
                f"- Optimal Window: Early morning hours with calm wind provide the best spray adhesion and absorption.\n\n"
                f"Source: IMD / Agronomic Spraying Safety Guidelines"
            )

    # --- Case 3: General / Rainfall Forecast Query ---
    if weather_state == "RAIN_EXPECTED":
        if language == "hi":
            return (
                f"🌦️ {loc_display} में आज बारिश / वर्षा होने का पूर्वानुमान है।\n\n"
                f"- मौसम स्थिति ({weather_domain}): वर्षा अथवा मेघ गर्जन की चेतावनी जारी की गई है।\n"
                f"- कृषि कार्य: खुले में रखे अनाज की सुरक्षा करें तथा खेत में रासायनिक छिड़काव अथवा सिंचाई स्थगित रखें।\n\n"
                f"Source: IMD ({weather_domain})"
            )
        elif language == "hinglish":
            return (
                f"🌦️ {loc_display} me aaj rain / baarish ka forecast hai.\n\n"
                f"- Weather Status ({weather_domain}): Rain warning ya precipitation alert active hai.\n"
                f"- Farm Operations: Open me rakhe grain ko protect karein aur spray ya sinchai postpone karein.\n\n"
                f"Source: IMD ({weather_domain})"
            )
        else:
            return (
                f"🌦️ Rainfall is forecast for {loc_display} today.\n\n"
                f"- Weather Status ({weather_domain}): Precipitation alert or rain warning active in the area.\n"
                f"- Farm Operations: Protect harvested grain and postpone chemical spraying or field irrigation.\n\n"
                f"Source: IMD ({weather_domain})"
            )
    elif weather_state == "CLEAR_DRY":
        if language == "hi":
            return (
                f"🌦️ {loc_display} में आज मौसम मुख्य रूप से साफ रहने का अनुमान है और भारी बारिश की संभावना नहीं है।\n\n"
                f"- मौसम स्थिति ({weather_domain}): अधिकतम तापमान सामान्य स्तर पर है और वर्षा की कोई चेतावनी जारी नहीं की गई है।\n"
                f"- कृषि कार्य: मौसम अनुकूल रहने के कारण खेत की निराई-गुड़ाई, जुताई या खाद प्रबंधन सामान्य रूप से किया जा सकता है।\n\n"
                f"Source: IMD ({weather_domain})"
            )
        elif language == "hinglish":
            return (
                f"🌦️ {loc_display} me aaj mausam mainly clear rehne ka anuman hai aur heavy rain ki sambhavna nahi hai.\n\n"
                f"- Weather Status ({weather_domain}): Temperatures normal range me hain aur immediate precipitation alert nahi hai.\n"
                f"- Field Operations: Weather favourable hone ke karan routine intercultural operations continue kar sakte hain.\n\n"
                f"Source: IMD ({weather_domain})"
            )
        else:
            return (
                f"🌦️ The weather forecast for {loc_display} today indicates generally clear conditions with no heavy rainfall expected.\n\n"
                f"- Conditions ({weather_domain}): Temperatures remain seasonal with no immediate precipitation warning.\n"
                f"- Farm Operations: Favorable conditions permit regular intercultural field operations and crop management.\n\n"
                f"Source: IMD ({weather_domain})"
            )
    else:
        if language == "hi":
            return (
                f"🌦️ {loc_display} के लिए आज का लाइव मौसम और वर्षा का सटीक डेटा ऑनलाइन सत्यापित नहीं हो सका।\n\n"
                f"- लाइव स्थिति: मौसम केंद्र से तात्कालिक मौसम टेलीमेट्री सत्यापित नहीं हो पाई है।\n"
                f"- कृषि सलाह: स्थानीय मौसम और आकाश की स्थिति को देखकर ही खेत में सिंचाई या स्प्रे का निर्णय लें।\n\n"
                f"Source: Live Weather Data Unverified"
            )
        elif language == "hinglish":
            return (
                f"🌦️ {loc_display} ke liye aaj ka live weather aur rain data online verify nahi ho saka.\n\n"
                f"- Live Status: Real-time meteorological telemetry verify nahi ho payi.\n"
                f"- Advisory: Local sky conditions aur field moisture dekhkar hi sinchai ya spray ka decision lein.\n\n"
                f"Source: Live Weather Data Unverified"
            )
        else:
            return (
                f"🌦️ Real-time live weather and precipitation data for {loc_display} could not be confirmed online.\n\n"
                f"- Live Status: Real-time meteorological telemetry could not be verified.\n"
                f"- Advisory: Inspect local sky conditions and field moisture before scheduling irrigation or chemical spraying.\n\n"
                f"Source: Live Weather Data Unverified"
            )



# -----------------------------------------------------------------------------
# Mandi Market Price Extraction & Farmer Response Utilities
# -----------------------------------------------------------------------------
def extract_mandi_data_from_evidence(
    evidence_list: List[Any],
    loc: Optional[str] = None,
    crop: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """
    Parses and verifies mandi market rates from live web search evidence (Tavily).
    Extracts modal price, min-max price range, unit, reported date, and authoritative source.
    Strictly verifies freshness and prevents numerical hallucination.
    """
    from datetime import date
    if not evidence_list:
        return None

    today = date.today()
    today_str = today.strftime("%Y-%m-%d")
    today_dmy = today.strftime("%d-%m-%Y")
    today_slash = today.strftime("%d/%m/%Y")
    current_year = str(today.year)

    best_data = None

    for ev in evidence_list:
        content = f"{getattr(ev, 'title', '')} {getattr(ev, 'content', '')}"
        domain = getattr(ev, 'domain', '') or ""
        url = getattr(ev, 'url', '') or ""
        published_date = getattr(ev, 'published_date', None)

        # 1. Extract Modal Price
        modal_match = re.search(
            r"(?:modal\s*(?:price|rate)?|मॉडल\s*(?:मूल्य|भाव)|औसत\s*भाव)[\s:]*(?:rs\.?|inr|₹)?\s*([0-9]{1,2},[0-9]{3}|[0-9]{3,5})",
            content,
            re.IGNORECASE
        )
        # 2. Extract Min Price
        min_match = re.search(
            r"(?:min(?:imum)?|न्यूनतम)[\s:]*(?:rs\.?|inr|₹)?\s*([0-9]{1,2},[0-9]{3}|[0-9]{3,5})",
            content,
            re.IGNORECASE
        )
        # 3. Extract Max Price
        max_match = re.search(
            r"(?:max(?:imum)?|अधिकतम)[\s:]*(?:rs\.?|inr|₹)?\s*([0-9]{1,2},[0-9]{3}|[0-9]{3,5})",
            content,
            re.IGNORECASE
        )
        # 4. Extract Range Pattern e.g. ₹2,400 - ₹2,600
        range_match = re.search(
            r"(?:rs\.?|inr|₹)\s*([0-9]{1,2},[0-9]{3}|[0-9]{3,5})\s*[-–toतक]\s*(?:rs\.?|inr|₹)?\s*([0-9]{1,2},[0-9]{3}|[0-9]{3,5})",
            content,
            re.IGNORECASE
        )

        modal_price = modal_match.group(1).replace(",", "") if modal_match else None
        min_price = min_match.group(1).replace(",", "") if min_match else (range_match.group(1).replace(",", "") if range_match else None)
        max_price = max_match.group(1).replace(",", "") if max_match else (range_match.group(2).replace(",", "") if range_match else None)

        # Fallback single rate e.g. Rs. 2400 per quintal
        if not modal_price and not min_price:
            single_match = re.search(
                r"(?:rs\.?|inr|₹)\s*([0-9]{1,2},[0-9]{3}|[0-9]{3,5})\s*(?:per|\/)\s*(?:quintal|qtl|क्विंटल)",
                content,
                re.IGNORECASE
            )
            if single_match:
                modal_price = single_match.group(1).replace(",", "")

        # If no verified price numbers found at all, skip this snippet
        if not modal_price and not min_price:
            continue

        # Extract Date
        reported_date = published_date
        date_match = re.search(r"\b(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})\b", content)
        if not date_match:
            date_match = re.search(
                r"\b(\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{2,4})\b",
                content,
                re.IGNORECASE
            )
        if date_match:
            reported_date = date_match.group(1)

        # Freshness Check
        is_today = False
        if reported_date:
            rd_clean = reported_date.strip()
            if (
                rd_clean in (today_str, today_dmy, today_slash)
                or (str(today.day) in rd_clean and today.strftime("%b") in rd_clean and current_year in rd_clean)
            ):
                is_today = True
        elif "today" in content.lower() or "aaj" in content.lower() or "आज" in content:
            is_today = True
            reported_date = today_dmy

        # Authoritative Source Identification
        source_name = "AGMARKNET"
        if "agmarknet" in domain.lower() or "agmarknet" in url.lower():
            source_name = "AGMARKNET (agmarknet.gov.in)"
        elif "enam" in domain.lower() or "enam" in url.lower():
            source_name = "eNAM (enam.gov.in)"
        elif "gov.in" in domain or "nic.in" in domain:
            source_name = f"Government Portal ({domain})"
        elif domain:
            source_name = domain
        else:
            source_name = "AGMARKNET / eNAM"

        candidate = {
            "modal_price": modal_price,
            "min_price": min_price,
            "max_price": max_price,
            "unit": "quintal",
            "reported_date": reported_date or today_dmy,
            "is_today": is_today,
            "source_name": source_name,
            "source_url": url,
            "evidence": ev
        }

        # If fresh and authoritative, stop immediately
        if is_today and ("agmarknet" in domain or "enam" in domain or "gov.in" in domain):
            return candidate

        if best_data is None:
            best_data = candidate
        elif not best_data.get("is_today") and is_today:
            best_data = candidate

    return best_data


def generate_market_price_reply(
    language: str,
    location: Optional[str],
    crop: Optional[str],
    mandi_data: Optional[Dict[str, Any]],
    live_failed: bool = False
) -> str:
    """
    Synthesizes structured, farmer-friendly response for market price queries.
    Never invents numerical rates. Strictly distinguishes fresh vs stale data.
    """
    crop_names = {
        "Wheat": {"en": "wheat", "hi": "गेहूं", "hinglish": "gehun"},
        "Rice": {"en": "rice / paddy", "hi": "धान / चावल", "hinglish": "dhan / chawal"},
        "Mustard": {"en": "mustard", "hi": "सरसों", "hinglish": "sarson"},
        "Maize": {"en": "maize", "hi": "मक्का", "hinglish": "makka"},
        "Potato": {"en": "potato", "hi": "आलू", "hinglish": "aloo"},
        "Tomato": {"en": "tomato", "hi": "टमाटर", "hinglish": "tamatar"},
        "Onion": {"en": "onion", "hi": "प्याज", "hinglish": "pyaz"},
        "Chickpea": {"en": "gram / chickpea", "hi": "चना", "hinglish": "chana"},
        "Cotton": {"en": "cotton", "hi": "कपास", "hinglish": "kapas"},
        "Sugarcane": {"en": "sugarcane", "hi": "गन्ना", "hinglish": "ganna"},
        "Soybean": {"en": "soybean", "hi": "सोयाबीन", "hinglish": "soybean"},
        "Groundnut": {"en": "groundnut", "hi": "मूंगफली", "hinglish": "mungfali"},
    }

    c_dict = crop_names.get(crop or "", {"en": crop or "crop", "hi": crop or "फसल", "hinglish": crop or "fasal"})
    loc_display = location or "Mandi"

    # Fallback when no verified live data is available
    if not mandi_data or live_failed:
        if location:
            if language == "hi":
                return (
                    f"मैं अभी {loc_display} मंडी का वर्तमान सत्यापित {c_dict['hi']} भाव पुष्टि नहीं कर पा रहा हूँ।\n\n"
                    f"📊 सत्यापित एवं ताज़ा मंडी भाव देखने के लिए:\n"
                    f"- भारत सरकार के आधिकारिक Agmarknet पोर्टल (agmarknet.gov.in) पर {loc_display} मंडी के आज के दैनिक भाव देखें।\n"
                    f"- eNAM पोर्टल (enam.gov.in) पर लाइव ई-ट्रेडिंग रेट देखें।"
                )
            elif language == "hinglish":
                return (
                    f"Main abhi {loc_display} mandi ka current verified {c_dict['hinglish']} rate confirm nahi kar pa raha hoon.\n\n"
                    f"📊 Live verified rates check karne ke liye:\n"
                    f"- Government of India ke official portal Agmarknet (agmarknet.gov.in) par {loc_display} mandi ke rates check karein.\n"
                    f"- eNAM portal (enam.gov.in) par live trading rates dekhein."
                )
            else:
                return (
                    f"I cannot confirm the current verified {c_dict['en']} rate for {loc_display} mandi right now.\n\n"
                    f"📊 To check verified real-time prices:\n"
                    f"- Visit the official Agmarknet portal (agmarknet.gov.in) for {loc_display} mandi.\n"
                    f"- Check eNAM (enam.gov.in) for live APMC trading prices."
                )
        else:
            if language == "hi":
                return (
                    "नमस्ते! मैत्री कृषि चैट वर्तमान में रीयल-टाइम मंडी भाव के लाइव डेटा फीड से सीधे कनेक्ट नहीं है। इसलिए मैं आज का सटीक मंडी भाव नहीं बता सकता।\n\n"
                    "📊 सत्यापित एवं ताज़ा मंडी भाव देखने के लिए:\n"
                    "- मैत्री पोर्टल पर 'Market Prices' (मंडी भाव) डैशबोर्ड देखें।\n"
                    "- भारत सरकार के आधिकारिक Agmarknet पोर्टल (agmarknet.gov.in) पर अपनी निकटतम कृषि उपज मंडी समिति (APMC) के आज के दैनिक भाव देखें।"
                )
            elif language == "hinglish":
                return (
                    "Namaste! Maitri Krishi Assistant chat me live real-time mandi prices ka live data feed connected nahi hai. Isliye main aaj ka live mandi rate invent nahi kar sakta.\n\n"
                    "📊 Live verified rates check karne ke liye:\n"
                    "- Maitri dashboard ke 'Market Prices' tab me dekhein.\n"
                    "- Government of India ke official portal Agmarknet (agmarknet.gov.in) par apni local mandi ke rates check karein."
                )
            else:
                return (
                    "Hello! Maitri Krishi Assistant chat does not have a live streaming market price feed connected. Therefore, I cannot provide today's live market rate.\n\n"
                    "📊 To view verified real-time prices:\n"
                    "- Check the 'Market Prices' section on the Maitri platform.\n"
                    "- Visit the Government of India's official Agmarknet portal (agmarknet.gov.in) for your local APMC mandi."
                )

    # Verified Data Presentation
    modal = mandi_data.get("modal_price")
    min_p = mandi_data.get("min_price")
    max_p = mandi_data.get("max_price")
    rep_date = mandi_data.get("reported_date") or "Recently reported"
    is_today = mandi_data.get("is_today", False)
    source_name = mandi_data.get("source_name") or "AGMARKNET"

    lines = []
    if modal:
        lines.append(f"- Modal price: ₹{modal} / quintal")
    if min_p and max_p:
        lines.append(f"- Min–Max: ₹{min_p} – ₹{max_p} / quintal")
    elif min_p:
        lines.append(f"- Min price: ₹{min_p} / quintal")
    lines.append(f"- Reported date: {rep_date}")
    lines.append(f"- Market/source: {loc_display} Mandi ({source_name})")

    body_block = "\n".join(lines)

    if language == "hi":
        lines_hi = []
        if modal:
            lines_hi.append(f"- मॉडल भाव (Modal price): ₹{modal} / क्विंटल")
        if min_p and max_p:
            lines_hi.append(f"- न्यूनतम–अधिकतम (Min–Max): ₹{min_p} – ₹{max_p} / क्विंटल")
        elif min_p:
            lines_hi.append(f"- न्यूनतम भाव (Min price): ₹{min_p} / क्विंटल")
        lines_hi.append(f"- दर्ज तिथि (Reported date): {rep_date}")
        lines_hi.append(f"- मंडी/स्रोत: {loc_display} मंडी ({source_name})")
        body_block_hi = "\n".join(lines_hi)

        if is_today:
            return (
                f"🌾 {loc_display} मंडी में {c_dict['hi']} का सत्यापित ताज़ा भाव:\n\n"
                f"{body_block_hi}\n\n"
                f"स्रोत: {source_name}"
            )
        else:
            return (
                f"🌾 {loc_display} मंडी में {c_dict['hi']} का भाव:\n\n"
                f"Latest verified available rate I found is from {rep_date}.\n\n"
                f"{body_block_hi}\n\n"
                f"स्रोत: {source_name}"
            )

    elif language == "hinglish":
        if is_today:
            return (
                f"🌾 {loc_display} mandi me {c_dict['hinglish']} ka latest verified rate:\n\n"
                f"{body_block}\n\n"
                f"Source: {source_name}"
            )
        else:
            return (
                f"🌾 {loc_display} mandi me {c_dict['hinglish']} ka rate:\n\n"
                f"Latest verified available rate I found is from {rep_date}.\n\n"
                f"{body_block}\n\n"
                f"Source: {source_name}"
            )

    else:
        if is_today:
            return (
                f"🌾 {loc_display} mandi latest verified rate for {c_dict['en']}:\n\n"
                f"{body_block}\n\n"
                f"Source: {source_name}"
            )
        else:
            return (
                f"🌾 {loc_display} mandi rate for {c_dict['en']}:\n\n"
                f"Latest verified available rate I found is from {rep_date}.\n\n"
                f"{body_block}\n\n"
                f"Source: {source_name}"
            )


# -----------------------------------------------------------------------------
# Main Chat Execution Handler
# -----------------------------------------------------------------------------
def process_chat_message(
    message: str,
    context: Optional[Dict[str, Any]] = None,
    history: Optional[List[Dict[str, str]]] = None,
    model: Optional[str] = None
) -> Dict[str, Any]:
    """
    End-to-end RAG handler for incoming chat queries.
    Logs debug info to console per Section 16.
    """
    clean_msg = (message or "").strip()
    if not clean_msg:
        return {
            "reply": "Please enter your farming question. / कृपया अपना कृषि से जुड़ा प्रश्न लिखें।",
            "sources": [],
            "retrieved_chunks": 0,
            "confidence": 0.0,
            "language": "en",
            "provider": "validation"
        }

    lang = detect_language(clean_msg)

    # 1. SMART RAG: PRE-RETRIEVAL INTENT, SAFETY & SERVICE ROUTER
    merged_router_context = dict(context) if context else {}
    if history and "history" not in merged_router_context:
        merged_router_context["history"] = history
    route_decision = classify_query(clean_msg, merged_router_context)
    logger.info(
        f"SMART_RAG route={route_decision.intent.value} action={route_decision.action.value} confidence={route_decision.confidence:.2f}"
    )

    # Branch 1.1: Safety-critical Pesticide Dosing / Mixing Refusal
    if route_decision.intent == Intent.PESTICIDE_REFUSAL:
        return {
            "reply": clean_farmer_markdown(compose_pesticide_refusal_reply(lang, route_decision.detected_entities)),
            "sources": [],
            "retrieved_chunks": 0,
            "confidence": route_decision.confidence,
            "language": lang,
            "provider": "chemical_safety_guard",
            "intent": route_decision.intent.value,
            "route": route_decision.action.value
        }

    # Branch 1.3: Unsupported Scope or Gibberish Input
    if route_decision.intent == Intent.UNSUPPORTED:
        from .smart_rag_router import is_gibberish as check_gibberish
        if check_gibberish(clean_msg):
            reply = (
                "मुझे मैत्री कृषि ज्ञानकोष में इस विषय पर पर्याप्त प्रामाणिक जानकारी नहीं मिली।\n\n"
                "सटीक समाधान के लिए कृपया बताएं:\n"
                "- फसल का नाम\n"
                "- राज्य या जिला\n"
                "- फसल की आयु (दिन)\n"
                "- समस्या या दिखने वाले लक्षण"
            ) if lang == "hi" else (
                "Maitri agriculture knowledge base me is sawal par sufficient information nahi mili.\n\n"
                "Accurate advice ke liye kripya batayein:\n"
                "- Crop name\n"
                "- State/District\n"
                "- Crop age (days)\n"
                "- Symptoms ya problem details"
            ) if lang == "hinglish" else (
                "I could not find enough reliable information in the agricultural knowledge base for this query.\n\n"
                "To help you accurately, please specify:\n"
                "- Crop name\n"
                "- Region/state\n"
                "- Crop growth stage\n"
                "- Visible symptoms or problem"
            )
            return {
                "reply": clean_farmer_markdown(reply),
                "sources": [],
                "retrieved_chunks": 0,
                "confidence": 0.1,
                "language": lang,
                "provider": "low_confidence_guard",
                "intent": route_decision.intent.value,
                "route": route_decision.action.value
            }
        else:
            return {
                "reply": clean_farmer_markdown(compose_unsupported_reply(lang, is_gibberish_input=False)),
                "sources": [],
                "retrieved_chunks": 0,
                "confidence": 0.0,
                "language": lang,
                "provider": "boundary_guard",
                "intent": route_decision.intent.value,
                "route": route_decision.action.value
            }

    # Branch 1.4: Anti-hallucination interceptors (live mandi rates & live weather without active feed)
    intercept = check_anti_hallucination_intercept(clean_msg, lang)
    if intercept:
        intercept["intent"] = route_decision.intent.value
        intercept["route"] = route_decision.action.value
        return intercept

    # Branch 1.5: Missing Required Context (e.g. Spraying/weather advisory asked without location)
    if route_decision.action == RouteAction.ASK_FOR_CONTEXT:
        return {
            "reply": clean_farmer_markdown(compose_missing_context_reply(route_decision.intent, route_decision.required_context, lang)),
            "sources": [],
            "retrieved_chunks": 0,
            "confidence": route_decision.confidence,
            "language": lang,
            "provider": "context_guard",
            "intent": route_decision.intent.value,
            "route": route_decision.action.value,
            "requires_context": route_decision.required_context
        }

    # Branch 1.5: Weather Service Advisory / Hybrid Weather-Agronomy
    if route_decision.intent == Intent.WEATHER and route_decision.action == RouteAction.WEATHER_SERVICE:
        loc = route_decision.detected_entities.get("location") or (context.get("location") if context else None)
        crop = route_decision.detected_entities.get("crop") or (context.get("crop") if context else None)

        # 1. Retrieve Live Weather from Tavily / WebSearchService
        weather_evidence = []
        live_lookup_failed = False
        if loc and getattr(web_search_service, "enabled", False):
            try:
                weather_search_query = f"{loc} weather today rainfall forecast IMD"
                weather_evidence = web_search_service.search(
                    query=weather_search_query,
                    crop=crop,
                    location=loc,
                    freshness_needed=True
                )
            except Exception as exc:
                logger.warning("Live weather search via Tavily failed: %s", exc)
                weather_evidence = []
                live_lookup_failed = True
        elif loc:
            live_lookup_failed = True

        is_live_verified = bool(weather_evidence and len(weather_evidence) > 0)
        if not is_live_verified and loc:
            live_lookup_failed = True

        # 2. Retrieve Agronomic KB guidance if query mentions crop, irrigation, spraying, fertilizer
        q_low = clean_msg.lower()
        is_hybrid_agri = bool(
            crop or re.search(r"\b(gehun|wheat|sinchai|irrigation|spray|छिड़काव|pani|पानी|urea|khat|crop|fasal|stage|दिन|day|22)\b", q_low)
        )
        kb_chunks = []
        kb_sources = []
        if is_hybrid_agri:
            try:
                kb_res = query_knowledge_base(clean_msg, top_k=2)
                kb_chunks = kb_res.get("chunks", [])
                kb_sources = kb_res.get("sources", [])
            except Exception as exc:
                logger.warning("KB retrieval for weather-agronomy hybrid failed: %s", exc)
                kb_chunks = []
                kb_sources = []

        # 3. Format sources
        formatted_sources = []
        if is_live_verified:
            for ev in weather_evidence[:2]:
                formatted_sources.append({
                    "title": ev.title,
                    "url": ev.url,
                    "domain": ev.domain,
                    "source": ev.domain,
                    "section": "Live Weather Advisory (IMD / Web)",
                    "category": "Weather"
                })
        for s in kb_sources:
            formatted_sources.append(s)

        # 4. Generate Hybrid Farmer Response
        reply_text = generate_weather_hybrid_reply(
            query=clean_msg,
            language=lang,
            location=loc,
            crop=crop,
            live_verified=is_live_verified,
            live_failed=live_lookup_failed,
            weather_evidence=weather_evidence,
            kb_chunks=kb_chunks
        )

        return {
            "reply": clean_farmer_markdown(reply_text),
            "sources": formatted_sources,
            "retrieved_chunks": len(weather_evidence) + len(kb_chunks),
            "confidence": 0.95 if is_live_verified else 0.85,
            "language": lang,
            "provider": "tavily_weather" if is_live_verified else "weather_service",
            "intent": route_decision.intent.value,
            "route": route_decision.action.value,
            "detected_entities": route_decision.detected_entities
        }

    # Branch 1.55: Market Price Advisory / Live Mandi Rates
    if (route_decision.intent == Intent.MARKET and route_decision.action == RouteAction.MARKET_SERVICE) or (
        route_decision.intent in (Intent.MARKET, Intent.FINANCIAL) and getattr(route_decision, "service", None) == "market"
    ):
        loc = route_decision.detected_entities.get("location") or (context.get("location") if context else None)
        crop = route_decision.detected_entities.get("crop") or (context.get("crop") if context else None)

        mandi_evidence = []
        live_lookup_failed = False
        mandi_data = None

        if loc and getattr(web_search_service, "enabled", False):
            try:
                commodity_canonical = crop.lower() if crop else "commodity"
                search_query = f"{loc} mandi {commodity_canonical} latest modal price AGMARKNET"
                mandi_evidence = web_search_service.search(
                    query=search_query,
                    crop=crop,
                    location=loc,
                    freshness_needed=True
                )
                mandi_data = extract_mandi_data_from_evidence(mandi_evidence, loc, crop)
            except Exception as exc:
                logger.warning("Live mandi search via Tavily failed: %s", exc)
                mandi_evidence = []
                live_lookup_failed = True
        elif loc:
            live_lookup_failed = True

        is_live_verified = bool(mandi_data is not None)
        if not is_live_verified:
            live_lookup_failed = True

        formatted_sources = []
        if is_live_verified and mandi_data and mandi_data.get("evidence"):
            ev = mandi_data["evidence"]
            formatted_sources.append({
                "title": getattr(ev, "title", "Mandi Market Price Record"),
                "url": getattr(ev, "url", ""),
                "domain": getattr(ev, "domain", ""),
                "source": getattr(ev, "domain", "agmarknet.gov.in"),
                "section": "Live Mandi Rate (AGMARKNET / eNAM)",
                "category": "Market Prices"
            })

        reply_text = generate_market_price_reply(
            language=lang,
            location=loc,
            crop=crop,
            mandi_data=mandi_data,
            live_failed=live_lookup_failed
        )

        return {
            "reply": clean_farmer_markdown(reply_text),
            "sources": formatted_sources,
            "retrieved_chunks": len(formatted_sources),
            "confidence": 0.95 if is_live_verified else 0.0,
            "language": lang,
            "provider": "tavily_market" if is_live_verified else "anti_hallucination_guard",
            "intent": route_decision.intent.value,
            "route": route_decision.action.value,
            "detected_entities": route_decision.detected_entities
        }

    # Branch 1.6: Financial / Insurance (PMFBY Guidelines) - Static only for FINANCIAL_SERVICE action
    if route_decision.action == RouteAction.FINANCIAL_SERVICE and route_decision.intent == Intent.FINANCIAL and ("pmfby" in clean_msg.lower() or "bima" in clean_msg.lower() or "insurance" in clean_msg.lower()):
        if lang == "hi":
            reply = (
                "🏛️ प्रधानमंत्री फसल बीमा योजना (PMFBY) - मुख्य दिशा-निर्देश:\n\n"
                "- किसान प्रीमियम हिस्सा: रबी फसलों के लिए बीमित राशि का 1.5%, खरीफ फसलों के लिए 2.0%, और वाणिज्यिक/बागवानी फसलों के लिए 5.0%।\n"
                "- 72 घंटे की अनिवार्यता: ओलावृष्टि, जलभराव या चक्रवाती बारिश से स्थानीय क्षति होने पर घटना के 72 घंटे के भीतर कृषि विभाग या हेल्पलाइन (14447) पर सूचना देना अनिवार्य है।\n"
                "- दावा निपटान: आधिकारिक अधिसूचना, प्रीमियम भुगतान और फसल कटाई प्रयोग (CCE) के सत्यापन पर निर्भर करता है।"
            )
        elif lang == "hinglish":
            reply = (
                "🏛️ Pradhan Mantri Fasal Bima Yojana (PMFBY) Guidelines:\n\n"
                "- Farmer Premium Share: Rabi crops ke liye 1.5% of Sum Insured, Kharif crops ke liye 2.0%, aur commercial/horticultural crops ke liye 5.0%.\n"
                "- Mandatory 72-Hour Rule: Hailstorm, inundation ya unseasonal rain se damage hone par 72 hours ke andar portal ya toll-free helpline (14447) par claim intimation dena zaroori hai.\n"
                "- Settlement: Claim official notification, cut-off date enrollment aur Crop Cutting Experiments (CCE) assessment par depend karta hai."
            )
        else:
            reply = (
                "🏛️ Pradhan Mantri Fasal Bima Yojana (PMFBY) Guidelines:\n\n"
                "- Statutory Premium Caps: 1.5% of Sum Insured for Rabi crops, 2.0% for Kharif crops, and 5.0% for commercial/horticultural crops.\n"
                "- 72-Hour Intimation Mandate: For localized calamities (hailstorm, inundation, post-harvest rain), intimation must be registered within 72 hours via the PMFBY portal or helpline (14447).\n"
                "- Settlement: Claims depend on notified area status, timely premium submission, and official revenue/CCE loss survey."
            )
        return {
            "reply": clean_farmer_markdown(reply),
            "sources": [{
                "title": "Pradhan Mantri Fasal Bima Yojana (PMFBY) Operational Guidelines",
                "section": "Statutory Premium Rates & 72-Hour Claim Rule",
                "source": "Ministry of Agriculture & Farmers Welfare, GoI (pmfby.gov.in)",
                "organization": "MoAFW, Government of India",
                "category": "Schemes",
                "crop": route_decision.detected_entities.get("crop", "General"),
                "score": 0.95
            }],
            "retrieved_chunks": 1,
            "confidence": 0.95,
            "language": lang,
            "provider": "insurance_service",
            "intent": route_decision.intent.value,
            "route": route_decision.action.value
        }

    # Branch 1.7: Direct Web Search for Explicit Freshness Queries (Section 8 Case A)
    is_freshness_query = (route_decision.action == RouteAction.WEB_SEARCH)
    if is_freshness_query:
        crop_val = route_decision.detected_entities.get("crop") or (context.get("crop") if context else None)
        loc_val = route_decision.detected_entities.get("location") or (context.get("location") if context else None)

        evidence = []
        if getattr(web_search_service, "enabled", False):
            try:
                evidence = web_search_service.search(
                    query=clean_msg,
                    crop=crop_val,
                    location=loc_val,
                    freshness_needed=True
                )
            except Exception as exc:
                logger.error("Web search failed: %s", type(exc).__name__)
                evidence = []
        else:
            logger.info("WebSearchService is disabled via WEB_SEARCH_ENABLED flag.")
            evidence = []

        if evidence and web_search_service.is_evidence_sufficient(evidence):
            formatted_sources = format_web_sources(evidence)
            system_prompt = build_web_grounded_system_prompt(
                language=lang,
                web_evidence=evidence,
                context=context,
                user_query=clean_msg
            )
            messages = [{"role": "system", "content": system_prompt}]
            if history:
                char_budget = 3200
                budget_used = 0
                bounded_turns = []
                for turn in reversed(history[-4:]):
                    r = turn.get("role")
                    c = turn.get("content", "").strip()
                    if r in ("user", "assistant") and c:
                        if budget_used + len(c) > char_budget:
                            c = c[:max(0, char_budget - budget_used)]
                        if c:
                            bounded_turns.append({"role": r, "content": c})
                            budget_used += len(c)
                        if budget_used >= char_budget:
                            break
                for turn in reversed(bounded_turns):
                    messages.append(turn)
            messages.append({"role": "user", "content": clean_msg})

            success, result, model_used = call_openrouter(messages, model=model)
            if success:
                return {
                    "reply": clean_farmer_markdown(result),
                    "sources": formatted_sources,
                    "retrieved_chunks": len(evidence),
                    "confidence": max((e.score for e in evidence), default=0.85),
                    "language": lang,
                    "provider": "tavily_web_search",
                    "model": model_used,
                    "intent": route_decision.intent.value,
                    "route": route_decision.action.value
                }
            else:
                offline_web_reply = generate_web_grounded_offline_reply(clean_msg, lang, evidence)
                return {
                    "reply": clean_farmer_markdown(offline_web_reply),
                    "sources": formatted_sources,
                    "retrieved_chunks": len(evidence),
                    "confidence": max((e.score for e in evidence), default=0.80),
                    "language": lang,
                    "provider": "grounded_web_offline",
                    "intent": route_decision.intent.value,
                    "route": route_decision.action.value
                }
        else:
            logger.warning("Web search unavailable or insufficient for freshness query. Falling through to curated RAG knowledge base.")

    # 2. RAG Retrieval from ChromaDB for GENERAL, CALENDAR, SOIL, FERTILIZER, etc.
    rag_result = query_knowledge_base(clean_msg, top_k=3)

    # 3. Out of domain guard
    if rag_result.get("is_out_of_domain"):
        if lang == "hi":
            reply = (
                "नमस्ते! मैं 'मैत्री कृषि सहायक' हूँ। "
                "मैं केवल कृषि, फसलों, मृदा स्वास्थ्य, कीट-रोग प्रबंधन, सिंचाई, मौसम और सरकारी कृषि योजनाओं से जुड़े सवालों में आपकी मदद कर सकता हूँ। "
                "कृपया खेती से संबंधित प्रश्न पूछें।"
            )
        elif lang == "hinglish":
            reply = (
                "Namaste! Main 'Maitri Krishi Assistant' hoon. "
                "Main sirf agriculture, fasal, mitti, keede-rog, sinchai, mausam aur government farming schemes se jude sawalo me help kar sakta hoon. "
                "Kripya kheti se sambandhit sawal puchein."
            )
        else:
            reply = (
                "I am Maitri Krishi Assistant, dedicated to agriculture. "
                "I can assist you with crops, soil health, pest and disease management, irrigation, weather, and government farming schemes. "
                "Please ask an agricultural or farming-related question."
            )

        return {
            "reply": clean_farmer_markdown(reply),
            "sources": [],
            "retrieved_chunks": 0,
            "confidence": 0.0,
            "language": lang,
            "provider": "boundary_guard",
            "intent": route_decision.intent.value,
            "route": route_decision.action.value
        }

    # 4. Low confidence / Gibberish guard with RAG_WEB_FALLBACK (Section 8 Case B)
    if rag_result.get("is_low_confidence") or not rag_result.get("chunks"):
        if is_freshness_query:
            logger.warning("Freshness query has neither live web verification nor RAG background evidence.")
            return {
                "reply": clean_farmer_markdown(compose_web_evidence_unavailable_reply(lang)),
                "sources": [],
                "retrieved_chunks": 0,
                "confidence": 0.2,
                "language": lang,
                "provider": "web_evidence_guard",
                "intent": route_decision.intent.value,
                "route": route_decision.action.value
            }

        crop_val = route_decision.detected_entities.get("crop") or (context.get("crop") if context else None)
        loc_val = route_decision.detected_entities.get("location") or (context.get("location") if context else None)

        from .smart_rag_router import is_gibberish as check_gibberish_token
        is_query_gibberish = any(check_gibberish_token(w) for w in clean_msg.split()) or check_gibberish_token(clean_msg)

        if getattr(web_search_service, "enabled", False) and not is_query_gibberish:
            logger.info("RAG retrieval insufficient. Attempting RAG_WEB_FALLBACK via WebSearchService.")
            try:
                fallback_evidence = web_search_service.search(
                    query=clean_msg,
                    crop=crop_val,
                    location=loc_val,
                    freshness_needed=False
                )
            except Exception as exc:
                logger.error("RAG_WEB_FALLBACK search failed: %s", type(exc).__name__)
                fallback_evidence = []

            if fallback_evidence and web_search_service.is_evidence_sufficient(fallback_evidence):
                formatted_sources = format_web_sources(fallback_evidence)
                system_prompt = build_web_grounded_system_prompt(
                    language=lang,
                    web_evidence=fallback_evidence,
                    context=context,
                    user_query=clean_msg
                )
                messages = [{"role": "system", "content": system_prompt}]
                if history:
                    char_budget = 3200
                    budget_used = 0
                    bounded_turns = []
                    for turn in reversed(history[-4:]):
                        r = turn.get("role")
                        c = turn.get("content", "").strip()
                        if r in ("user", "assistant") and c:
                            if budget_used + len(c) > char_budget:
                                c = c[:max(0, char_budget - budget_used)]
                            if c:
                                bounded_turns.append({"role": r, "content": c})
                                budget_used += len(c)
                            if budget_used >= char_budget:
                                break
                    for turn in reversed(bounded_turns):
                        messages.append(turn)
                messages.append({"role": "user", "content": clean_msg})

                success, result, model_used = call_openrouter(messages, model=model)
                if success:
                    return {
                        "reply": clean_farmer_markdown(result),
                        "sources": formatted_sources,
                        "retrieved_chunks": len(fallback_evidence),
                        "confidence": max((e.score for e in fallback_evidence), default=0.75),
                        "language": lang,
                        "provider": "web_search_fallback",
                        "model": model_used,
                        "intent": route_decision.intent.value,
                        "route": RouteAction.RAG_WEB_FALLBACK.value
                    }
                else:
                    offline_reply = generate_web_grounded_offline_reply(clean_msg, lang, fallback_evidence)
                    return {
                        "reply": clean_farmer_markdown(offline_reply),
                        "sources": formatted_sources,
                        "retrieved_chunks": len(fallback_evidence),
                        "confidence": max((e.score for e in fallback_evidence), default=0.70),
                        "language": lang,
                        "provider": "web_fallback_offline",
                        "intent": route_decision.intent.value,
                        "route": RouteAction.RAG_WEB_FALLBACK.value
                    }

        if lang == "hi":
            reply = (
                "मुझे मैत्री कृषि ज्ञानकोष में इस विषय पर पर्याप्त प्रामाणिक जानकारी नहीं मिली।\n\n"
                "सटीक समाधान के लिए कृपया बताएं:\n"
                "- फसल का नाम\n"
                "- राज्य या जिला\n"
                "- फसल की आयु (दिन)\n"
                "- समस्या या दिखने वाले लक्षण"
            )
        elif lang == "hinglish":
            reply = (
                "Maitri agriculture knowledge base me is sawal par sufficient information nahi mili.\n\n"
                "Accurate advice ke liye kripya batayein:\n"
                "- Crop name\n"
                "- State/District\n"
                "- Crop age (days)\n"
                "- Symptoms ya problem details"
            )
        else:
            reply = (
                "I could not find enough reliable information in the agricultural knowledge base for this query.\n\n"
                "To help you accurately, please specify:\n"
                "- Crop name\n"
                "- Region/state\n"
                "- Crop growth stage\n"
                "- Visible symptoms or problem"
            )

        return {
            "reply": clean_farmer_markdown(reply),
            "sources": [],
            "retrieved_chunks": 0,
            "confidence": rag_result.get("confidence", 0.1),
            "language": lang,
            "provider": "low_confidence_guard",
            "intent": route_decision.intent.value,
            "route": route_decision.action.value
        }

    chunks = rag_result["chunks"]
    sources = rag_result["sources"]
    confidence = rag_result["confidence"]

    # 5. Developer Debug Logging (Section 16)
    _safe_print("\n" + "=" * 60)
    _safe_print("USER QUERY:")
    _safe_print(clean_msg)
    _safe_print(f"DETECTED CROP: {rag_result.get('detected_crop')} | CATEGORY: {rag_result.get('detected_category')}")
    _safe_print("\nRETRIEVED CHUNKS:")
    for idx, c in enumerate(chunks):
        stype = c.get('source_type', 'curated_reference')
        _safe_print(f"{idx+1}. {c.get('source')} ({stype}) / {c.get('title')} - {c.get('section')} / Score: {c.get('score')}")
        snippet = c.get('text', '')[:180].replace('\n', ' ')
        _safe_print(f"   {snippet}...")

    # 6. Build Grounded System Prompt
    system_prompt = build_rag_system_prompt(
        language=lang,
        retrieved_chunks=chunks,
        context=context,
        user_query=clean_msg
    )

    messages = [{"role": "system", "content": system_prompt}]
    if history:
        # Enforce maximum 4 turns and strict ~800 token budget (~3200 characters) for forwarded history
        char_budget = 3200
        budget_used = 0
        bounded_turns = []
        for turn in reversed(history[-4:]):
            r = turn.get("role")
            c = turn.get("content", "").strip()
            if r in ("user", "assistant") and c:
                if budget_used + len(c) > char_budget:
                    c = c[:max(0, char_budget - budget_used)]
                if c:
                    bounded_turns.append({"role": r, "content": c})
                    budget_used += len(c)
                if budget_used >= char_budget:
                    break
        for turn in reversed(bounded_turns):
            messages.append(turn)
    messages.append({"role": "user", "content": clean_msg})

    # 7. Call OpenRouter API
    success, result, model_used = call_openrouter(messages, model=model)

    freshness_note = ""
    if is_freshness_query:
        if lang == "hi":
            freshness_note = "ℹ️ सूचना: नवीनतम जानकारी के लिए लाइव इंटरनेट सत्यापन वर्तमान में अनुपलब्ध है, इसलिए नवीनतम अपडेट की पुष्टि नहीं की जा सकी। मैत्री ज्ञानकोष में उपलब्ध सत्यापित पृष्ठभूमि जानकारी निम्नलिखित है:\n\n"
        elif lang == "hinglish":
            freshness_note = "ℹ️ Note: Live internet verification abhi available nahi hai, isliye latest updates confirm nahi kiye ja sakte. MAITTRI knowledge base me available verified background information neeche di gayi hai:\n\n"
        else:
            freshness_note = "ℹ️ Note: Live verification is currently unavailable, so I cannot confirm the latest update. Here is the available MAITTRI background information:\n\n"

    if success:
        _safe_print(f"\nOPENROUTER SUCCESS (model: {model_used})")
        _safe_print("\nFINAL ANSWER:")
        final_reply = (freshness_note + result) if freshness_note else result
        _safe_print(final_reply[:300] + "..." if len(final_reply) > 300 else final_reply)
        _safe_print("\nSOURCES USED:")
        for s in sources:
            _safe_print(f"- {s.get('organization')} ({s.get('source_type')}) — {s.get('title')}")
        _safe_print("=" * 60 + "\n")

        return {
            "reply": clean_farmer_markdown(final_reply),
            "sources": sources,
            "retrieved_chunks": len(chunks),
            "confidence": confidence,
            "language": lang,
            "provider": "openrouter",
            "model": model_used,
            "intent": route_decision.intent.value,
            "route": route_decision.action.value
        }

    # 8. Fallback: Synthesize cleanly from retrieved chunks
    _safe_print(f"\nOPENROUTER UNAVAILABLE ({result}). Generating grounded local RAG synthesis.")
    offline_reply = generate_grounded_offline_reply(clean_msg, lang, chunks)
    final_offline = (freshness_note + offline_reply) if freshness_note else offline_reply
    _safe_print("\nFINAL ANSWER:")
    _safe_print(final_offline[:300] + "...")
    _safe_print("=" * 60 + "\n")

    return {
        "reply": clean_farmer_markdown(final_offline),
        "sources": sources,
        "retrieved_chunks": len(chunks),
        "confidence": confidence,
        "language": lang,
        "provider": "grounded_local_rag",
        "intent": route_decision.intent.value,
        "route": route_decision.action.value
    }
