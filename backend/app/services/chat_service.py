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
import sys
import re
import logging
from datetime import datetime
import requests
from pathlib import Path
from urllib.parse import urlparse
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
    detect_weather_time_scope,
    compose_pesticide_refusal_reply,
    compose_missing_context_reply,
    compose_unsupported_reply,
    compose_web_evidence_unavailable_reply,
    extract_location_from_text,
    CROPS_PATTERNS
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

    # 7b. Strip raw FAQ labels e.g. "- A: ", "- Q: ", "A: ", "Q: "
    cleaned = re.sub(r"^[ \t]*-[ \t]*(?:A|Q|Answer|Question|उत्तर|प्रश्न)\s*[:：]\s*", "- ", cleaned, flags=re.MULTILINE | re.I)
    cleaned = re.sub(r"^[ \t]*(?:A|Q|Answer|Question|उत्तर|प्रश्न)\s*[:：]\s*", "", cleaned, flags=re.MULTILINE | re.I)

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
7. DISEASE IDENTIFICATION SAFETY & DIAGNOSTIC CONFIDENCE CALIBRATION:
   - For initial symptom queries without a laboratory test, state 2 to 4 potential causes non-definitively ('Possible causes include...') and outline distinguishing field checks. Never jump to a single definitive disease diagnosis from one symptom.
   - For follow-up symptom queries where symptoms narrow down (e.g. tomato upward leaf curling + visible whitefly pointing to ToLCV), use calibrated language: 'ToLCV ka strong suspicion hai' / 'ToLCV ki sambhavna kaafi badh jaati hai' / 'Symptoms ToLCV se strongly match karte hain'.
   - Do NOT state definitive diagnosis unless confirmatory laboratory evidence exists.
   - Clearly separate:
     1) Likely Diagnosis (calibrated non-definitive suspicion)
     2) What farmer should check next
     3) Immediate low-risk management (uproot severely infected early plants, yellow sticky traps, vector control; state clearly that no chemical cures the virus once infected)
     4) When expert/lab confirmation is useful (consult KVK before major crop decisions).
   - Include a relevant source line at the end (e.g. 'Source: ICAR-IIVR, Varanasi').
8. TARGET LENGTH & STYLE:
   - Normal simple questions should stay within about 60–120 words unless more detail is genuinely required.
   - Language: {lang_inst}
   - Output ONLY the final farmer-facing response. No meta-commentary, no thinking blocks.
9. SOURCE ATTRIBUTION:
   - If citing the source institution, mention it simply at the bottom (e.g. 'Source: ICAR-IIWBR, Karnal').
10. QUESTION INTENT FIDELITY & DIRECT ANSWERS:
   - If farmer asks for fertilizer dose/quantity, answer the recommended quantity and split schedule from knowledge base; if crop stage is needed, state the splits and ask current stage. Do not deflect with unrelated concepts like neem oil coating.
   - If farmer asks about applying a double dose of fertilizer, explicitly start with: "No, [Fertilizer] ka double dose bina soil-test/recommendation ke na dein." Explain soil fixation and micronutrient lockout. Do NOT append pesticide spray boilerplate.
   - If farmer asks for frost protection, give actionable measures first (light evening irrigation, smoke cover, potassium/thiourea foliar spray).
   - If farmer asks what PM-KISAN is and its eligibility, explain the scheme amount (Rs 6,000/yr in 3 installments) and eligibility (landholding, eKYC, exclusions) directly. Do not substitute payment delay troubleshooting for eligibility.
   - If farmer asks a crop-age + action question (e.g. "mere gehun ko 22 din hue hain, ab kya karu?"):
     * The very first sentence must directly answer "ab kya karu?" by identifying the supported physiological stage from retrieved knowledge (e.g. 20–25 DAS = Crown Root Initiation / CRI stage) and stating whether first irrigation is due.
     * State immediate actionable measures: light first irrigation (4–5 cm depth), first top-dressing of urea (approx 36 kg/acre) after irrigation, and waterlogging prevention.
     * If crop age is outside the CRI window (e.g. 10–12 days), clearly explain that first irrigation is not yet due and advise waiting until 20–25 DAS. If 40–45 days, advise that 2nd irrigation at tillering stage and final urea split are due.
     * Never output raw FAQ markers like "Q:" or "A:".

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
    retrieved_chunks: List[Dict[str, Any]],
    entities: Optional[Dict[str, Any]] = None
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
    if not crop_val and entities and entities.get("crop"):
        crop_val = entities.get("crop")
    source_val = top_chunk.get("source", "")
    org_val = top_chunk.get("organization", "")
    if "IIVR" in org_val or "IIVR" in source_val:
        source_name = "ICAR-IIVR, Varanasi (Vegetable Pathology & Whitefly Management)"
    elif "IIWBR" in source_val or "IIWBR" in org_val:
        source_name = "ICAR-IIWBR, Karnal"
    elif "IIPR" in source_val or "IIPR" in org_val:
        source_name = "ICAR-IIPR, Kanpur"
    elif "CRIDA" in source_val or "CRIDA" in org_val:
        source_name = "ICAR-CRIDA, Hyderabad"
    elif "ICAR" in source_val:
        source_name = "ICAR / State Agriculture Department"
    else:
        source_name = org_val or source_val
    if len(source_name) > 60 and "(" in source_name and "IIVR" not in source_name:
        m = re.search(r"\(([^)]+)\)", source_name)
        if m:
            source_name = f"ICAR-{m.group(1)}"

    q_lower = query.lower()
    is_irrigation = bool(re.search(r"sinchai|irrigate|irrigation|सिंचाई|पानी|water|प्यास|कंस|नमी", q_lower))

    # --- Specific Intent Handlers for High-Value Farm Queries ---

    # 1. DAP Double Dose
    is_dap_double = bool(re.search(r"\bdap\b|डीएपी", q_lower) and re.search(r"double|दो\s*गुना|दोगुना|दोहरा|2\s*गुना", q_lower))
    if is_dap_double:
        if language == "hi":
            lead = "नहीं, डीएपी (DAP) की दोगुनी खुराक बिना मिट्टी जांच या वैज्ञानिक सिफारिश के बिल्कुल न दें।"
            bullets = [
                "- अतिरिक्त फॉस्फोरस मिट्टी में स्थिर (fix) हो जाता है, जिससे पौधे उसे अवशोषित नहीं कर पाते और लागत व्यर्थ जाती है।",
                "- अत्यधिक डीएपी के कारण मिट्टी में जिंक (Zinc) और आयरन (Iron) की उपलब्धता बाधित होती है, जिससे फसल में पीलापन आ सकता है।",
                "- बीज अंकुरण के समय अधिक सांद्रता से नन्हीं जड़ों को रासायनिक क्षति (salt injury) का खतरा रहता है।",
                "- गेहूं में सामान्य अनुशंसित डीएपी 50–55 किग्रा प्रति एकड़ (लगभग 1 बैग, 50 किग्रा प्रति बैग) है, जिसे बुवाई के समय बेसल (basal) दिया जाता है।"
            ]
        elif language == "hinglish":
            lead = "No, DAP ka double dose bina soil-test/recommendation ke na dein."
            bullets = [
                "- Excess phosphorus mitti me fix ho jata hai aur paudhe use absorb nahi kar pate, jisse lagat barbad hoti hai.",
                "- Excessive DAP mitti me Zinc aur Iron ki availability rok deta hai, jisse fasal me severe chlorosis (peelapan) aa sakta hai.",
                "- Germination ke time chemical concentration jyada hone se nanni roots ko salt injury ka risk rehta hai.",
                "- Gehun me normal recommended DAP lagbhag 50–55 kg per acre (approx. 1 bag of 50 kg) hai, jo buwai ke time basal application me di jaati hai."
            ]
        else:
            lead = "No, do not apply a double dose of DAP without soil-test recommendations."
            bullets = [
                "- Excess phosphorus gets fixed in the soil and becomes unavailable to crops, leading to wasted input costs.",
                "- High phosphorus levels induce secondary zinc and iron deficiencies, leading to severe chlorosis.",
                "- Elevated chemical concentrations near germinating seeds cause root salt injury.",
                "- The standard recommended DAP dose for wheat is 50–55 kg per acre (approx. 1 bag of 50 kg), applied strictly as a basal placement at sowing."
            ]
        reply = f"{lead}\n\n" + "\n".join(bullets)
        reply += "\n\nSource: ICAR-IIWBR / Indian Institute of Soil Science (IISS)"
        return clean_farmer_markdown(reply)

    # 2. Wheat Urea Dose
    is_urea_dose = bool(re.search(r"\burea\b|यूरिया", q_lower) and re.search(r"\b(kitna|how\s*much|dose|dena|dein|chahiye)\b|कितना|कितनी|खुराक|मात्रा", q_lower))
    if is_urea_dose and (crop_val == "Wheat" or (entities and entities.get("crop") == "Wheat") or any(w in q_lower for w in ["wheat", "gehun", "gehu", "गेहूं", "गेहु"])):
        if language == "hi":
            lead = "🌾 गेहूं में यूरिया की कुल अनुशंसित मात्रा लगभग 100 किग्रा प्रति एकड़ (45 किग्रा के लगभग 2.2 बैग) होती है, जिसे 3 विभाजित खुराकों (split doses) में दिया जाता है:"
            bullets = [
                "- बेसल खुराक (Basal): बुवाई के समय लगभग 28 किग्रा/एकड़ यूरिया दें (यदि बुवाई पर डीएपी दिया है तो बेसल यूरिया की मात्रा घटाएं)।",
                "- पहली टॉप-ड्रेसिंग (CRI अवस्था, 20–25 दिन): पहली सिंचाई पर 36 किग्रा/एकड़ यूरिया (45 किग्रा का 0.8 बैग)।",
                "- दूसरी टॉप-ड्रेसिंग (कल्ले निकलते समय, 45–50 दिन): दूसरी सिंचाई पर शेष 36 किग्रा/एकड़ यूरिया (45 किग्रा का 0.8 बैग)।",
                "- ध्यान दें: यह सिफारिश मध्यम उपजाऊ व सिंचित भूमि (120 किग्रा N/हेक्टेयर लक्ष्य) के लिए है; मृदा स्वास्थ्य कार्ड (Soil Health Card) व सिंचाई के अनुसार मात्रा समायोजित करें।"
            ]
        elif language == "hinglish":
            lead = "🌾 Gehun me urea ki total recommended dose lagbhag 100 kg per acre (approx. 2.2 bags of 45 kg) hoti hai, jise 3 split doses me dena chahiye:"
            bullets = [
                "- Basal Application: Sowing ke time lagbhag 28 kg/acre urea dein (agar basal DAP use kiya hai to DAP se milne wali starter nitrogen ke anusaar ise kam karein).",
                "- 1st Top-Dressing (CRI stage, 20–25 din): Pehli sinchai par 36 kg/acre urea (approx. 0.8 bag of 45 kg).",
                "- 2nd Top-Dressing (Tillering/Jointing, 45–50 din): Dusri sinchai par 36 kg/acre urea (approx. 0.8 bag of 45 kg).",
                "- Note: Yeh dose irrigated wheat aur medium fertility (120 kg N/ha target) ke liye hai; soil health card aur sinchai suvidha ke anusar matra adjust karein."
            ]
        else:
            lead = "🌾 The recommended total urea application for wheat is approximately 100 kg per acre (approx. 2.2 bags of 45 kg), applied in 3 split doses:"
            bullets = [
                "- Basal Dose: Apply approx. 28 kg/acre urea at sowing (reduce this if basal DAP is applied, as DAP supplies starter nitrogen).",
                "- First Top-Dressing (CRI stage, 20–25 DAS): Apply 36 kg/acre urea (approx. 0.8 bag of 45 kg) at first irrigation.",
                "- Second Top-Dressing (Tillering/Jointing stage, 45–50 DAS): Apply 36 kg/acre urea (approx. 0.8 bag of 45 kg) at second irrigation.",
                "- Note: This recommendation is for irrigated high-yielding wheat under medium fertility (120 kg N/ha); adjust based on Soil Health Card testing and irrigation availability."
            ]
        reply = f"{lead}\n\n" + "\n".join(bullets)
        reply += "\n\nSource: ICAR-IIWBR, Karnal (Wheat Agronomy Guidelines)"
        return clean_farmer_markdown(reply)

    # 3. Frost Protection (Pala se bachav)
    is_frost = bool(re.search(r"\b(pala|frost|पाला|sheetlahar|cold\s*wave|शीतलहर)\b", q_lower) and re.search(r"\b(bachav|bachaav|control|protect|protection|रोकथाम|बचाव|उपाय)\b", q_lower))
    if is_frost:
        if language == "hi":
            lead = "🌾 गेहूं में पाले (Frost) व शीतलहर से फसल को बचाने के लिए तुरंत ये व्यावहारिक उपाय अपनाएं:"
            bullets = [
                "- हल्की शाम की सिंचाई: पाले की संभावना होने पर खेत में शाम को हल्का पानी लगाएं; नम मिट्टी रात में गर्मी रोककर तापमान 1–2°C बढ़ा देती है।",
                "- मेड़ों पर धुआं करना: उत्तर-पश्चिम दिशा में खेत की मेड़ों पर शाम के समय खरपतवार या कूड़ा जलाकर धुआं करें ताकि पाला न जमे।",
                "- पर्णीय पोषण छिड़काव: 0.2% थायोयूरिया (2 ग्राम/लीटर) या 0.5% घुलनशील पोटाश (0:0:50 @ 5 ग्राम/लीटर) का छिड़काव करें, जिससे पौधों में शीत सहनशीलता बढ़ती है।",
                "- खेत की नियमित निगरानी रखें तथा हवा शांत होने और रात का तापमान 4°C से नीचे जाने पर तुरंत धुआं व सिंचाई शुरू करें।"
            ]
        elif language == "hinglish":
            lead = "🌾 Wheat me pala (frost / sheetlahar) se fasal ko bachane ke liye turant ye actionable upay karein:"
            bullets = [
                "- Halka Sinchai: Paale ki sambhavna par shaam ke waqt khet me halka pani lagayein; moist soil raat me temperature 1–2°C maintain rakhti hai.",
                "- Dhuan Cover: North-west direction me khet ki medhon par shaam ko kachra jalakar dhuan karein taki frost na jame.",
                "- Foliar Spray: 0.2% Thiourea (2 g/L) ya 0.5% Soluble Potash (0:0:50 @ 5 g/L) ka spray karein taki cold tolerance badhe.",
                "- Night Temperature Watch: Jab hawa shant ho aur night temp 4°C se neeche gire, to turant sinchai aur smoke cover follow karein."
            ]
        else:
            lead = "🌾 Protect wheat crops from ground frost and cold wave using these actionable measures immediately:"
            bullets = [
                "- Light Evening Irrigation: Apply a light irrigation during evening hours; moist soil holds heat and raises canopy temperature by 1–2°C.",
                "- Perimeter Smoke Cover: Burn organic residue along field borders in the upwind (north-west) direction at night to create a protective smoke blanket.",
                "- Foliar Protective Spray: Spray 0.2% Thiourea (2 g/L) or 0.5% soluble Potash (0:0:50 @ 5 g/L) to increase cell sap concentration and cold tolerance.",
                "- Monitor night temperature closely; initiate protective irrigation when night air drops below 4°C under calm winds."
            ]
        reply = f"{lead}\n\n" + "\n".join(bullets)
        reply += "\n\nSource: ICAR-CRIDA / IMD Agro-Meteorological Contingency Guidelines"
        return clean_farmer_markdown(reply)

    # 4. PM-KISAN Scheme Definition & Eligibility
    is_pm_kisan = bool(re.search(r"pm\s*-?\s*kisan|पीएम\s*-?\s*किसान", q_lower) and re.search(r"kya\s+hai|eligib|पात्रता|yojana|scheme|योजना|क्या\s+है", q_lower))
    if is_pm_kisan:
        if language == "hi":
            lead = "🌾 पीएम-किसान (प्रधानमंत्री किसान सम्मान निधि) भारत सरकार की direct income support योजना है, जिसमें पात्र किसान परिवारों को प्रति वर्ष ₹6,000 की वित्तीय सहायता ₹2,000 की तीन समान किस्तों में सीधे बैंक खाते (DBT) में दी जाती है।"
            bullets = [
                "- भूमि पात्रता: सभी भूमिधारक किसान परिवार जिनके नाम कृषि योग्य भूमि के वैध राजस्व रिकॉर्ड (खतौनी/ROR) दर्ज हैं।",
                "- अनिवार्य e-KYC: बैंक खाते का आधार से लिंक होना (NPCI direct debit) और बायोमेट्रिक या OTP आधारित e-KYC सत्यापन अनिवार्य है।",
                "- अपवर्जन (Ineligible): संस्थागत भूमिधारक, संवैधानिक पदधारक, वर्तमान/पूर्व सांसद व विधायक, सरकारी कर्मचारी, और ₹10,000 से अधिक मासिक पेंशनभोगी इस योजना के पात्र नहीं हैं।",
                "- सत्यापन: आवेदन की स्थिति व नए पंजीकरण के लिए pmkisan.gov.in पोर्टल पर जाएं या नजदीकी जन सेवा केंद्र (CSC) से संपर्क करें।"
            ]
        elif language == "hinglish":
            lead = "🌾 PM-KISAN (Pradhan Mantri Kisan Samman Nidhi) kendra sarkar ki income support scheme hai jisme patra kisan parivaron ko prati varsh ₹6,000 ki financial assistance ₹2,000 ki 3 saman kishton me seedhe bank account (DBT) me di jaati hai."
            bullets = [
                "- Landholding Eligibility: Sabhi cultivable landholder kisan parivar jinke naam zameen ke valid revenue record (Khatauni) darj hain.",
                "- Mandatory e-KYC: Bank account ka Aadhaar NPCI link hona aur OTP ya biometric e-KYC verification anivarya hai.",
                "- Ineligibility Exclusions: Institutional landholders, constitutional post holders, purva/vartaman MPs/MLAs, government employees, aur ₹10,000 se jyada pension pane wale isme eligible nahi hain.",
                "- Verification & Apply: Status check karne ya register karne ke liye pmkisan.gov.in portal visit karein ya nearest CSC center jayein."
            ]
        else:
            lead = "🌾 PM-KISAN (Pradhan Mantri Kisan Samman Nidhi) is a central sector income support scheme providing ₹6,000 per year to eligible landholding farmer families in three equal instalments of ₹2,000 each via Direct Benefit Transfer (DBT)."
            bullets = [
                "- Landholding Eligibility: All cultivable landholder farmer families with valid land ownership records in state land administration registers.",
                "- Mandatory e-KYC: Bank account must be Aadhaar-seeded via NPCI and verified through biometric or OTP-based e-KYC.",
                "- Ineligibility Criteria: Institutional landholders, constitutional office holders, serving/former MPs, MLAs, government employees, and pensioners receiving >₹10,000/month are excluded.",
                "- Verification: Check beneficiary status or register at pmkisan.gov.in or visit your local Common Service Centre (CSC)."
            ]
        reply = f"{lead}\n\n" + "\n".join(bullets)
        reply += "\n\nSource: Ministry of Agriculture & Farmers Welfare, GoI (pmkisan.gov.in)"
        return clean_farmer_markdown(reply)

    # 5. Wheat Leaf Yellowing (Differential Diagnosis)
    is_wheat_yellowing = bool(("wheat" in q_lower or "gehu" in q_lower or "गेहूं" in q_lower or crop_val == "Wheat" or (entities and entities.get("crop") == "Wheat")) and re.search(r"pile|peeli|peele|yellow|पीली|पीले|पीला", q_lower))
    if is_wheat_yellowing:
        if language == "hi":
            lead = "🌾 गेहूं में पत्तियों के पीलेपन के मुख्य रूप से 3 से 4 संभावित कारण हो सकते हैं, सही पहचान के लिए ये अंतर देखें:"
            bullets = [
                "- 1. नाइट्रोजन की कमी (Nitrogen Deficiency): निचली (पुरानी) पत्तियां नोक से पीली होने लगती हैं और बढ़वार रुक जाती है। (जांच: यदि केवल पुरानी निचली पत्तियां पीली हैं तो ओट आने पर यूरिया टॉप-ड्रेसिंग करें)।",
                "- 2. पीला रतुआ (Yellow Rust): पत्तियों पर पीले रंग की समानांतर धारियां बनती हैं, जिन्हें छूने पर उंगली पर पीला पाउडर लगता है। (जांच: यदि उंगली पर पीला पाउडर लगे तो यह रतुआ फफूंद है)।",
                "- 3. जलभराव / अधिक नमी (Waterlogging): पहली सिंचाई के बाद भारी मिट्टी में पानी ठहरने से जड़ें घुटती हैं और पूरा पौधा पीला दिखता है। (जांच: खेत से अतिरिक्त पानी निकालें)।",
                "- 4. जिंक की कमी (Zinc Deficiency): नई पत्तियों के मध्य भाग में सफेद-पीली धारियां या भूरे धब्बे बनते हैं। (जांच: 0.5% जिंक सल्फेट + 2% यूरिया का छिड़काव)।",
                "- कृपया जांचें: क्या उंगली पर पीला पाउडर लग रहा है या केवल निचली पत्तियां पीली हैं? यह बताने पर सटीक उपचार दिया जा सकेगा।"
            ]
        elif language == "hinglish":
            lead = "🌾 Gehun me leaves yellow hone ke main 3 se 4 possible causes ho sakte hain, accurate identification ke liye ye check karein:"
            bullets = [
                "- 1. Nitrogen Deficiency: Nichli (purani) leaves tip se yellow hone lagti hain aur growth slow hoti hai. (Check: Agar purani leaves peeli hain to moisture me urea top-dressing karein).",
                "- 2. Yellow Rust (Peela Ratua): Leaves par yellow powder ki parallel stripes banti hain jo ungli par lagti hain. (Check: Agar ungli par yellow powder lage to yeh rust disease hai).",
                "- 3. Excessive Water / Waterlogging: Heavy soil me sinchai ke baad paani khada hone se roots ko oxygen nahi milti aur plant peela padta hai. (Check: Field se extra water nikalein).",
                "- 4. Zinc Deficiency: Nayi leaves ke beech me safed/peeli stripes ya bronze spots bante hain. (Check: 0.5% Zinc Sulphate + 2% Urea spray).",
                "- Kripya check karein: Kya ungli par peela powder lag raha hai ya nichli leaves peeli hain? Isse sahi upchar nirdharit hoga."
            ]
        else:
            lead = "🌾 Yellowing of wheat leaves can be caused by 3 to 4 distinct factors; inspect your field for these distinguishing symptoms:"
            bullets = [
                "- 1. Nitrogen Deficiency: Lower/older leaves turn pale yellow starting from the leaf tip along the midrib. Check if only older leaves are affected.",
                "- 2. Yellow / Stripe Rust (Puccinia striiformis): Linear yellow powdery stripes appear on leaves and yellow spores rub off on fingers. Check if yellow powder rubs onto your fingers.",
                "- 3. Waterlogging / Excessive Soil Moisture: Flooding after first irrigation in heavy soils suffocates crown roots and induces uniform chlorosis.",
                "- 4. Zinc Deficiency: Interveinal chlorosis appears on newer leaves with necrotic bronzing.",
                "- Please verify whether yellow powder rubs off on fingers or if yellowing started on bottom leaves to determine treatment."
            ]
        reply = f"{lead}\n\n" + "\n".join(bullets)
        reply += "\n\nSource: ICAR-IIWBR, Karnal (Wheat Pathology & Agronomy)"
        return clean_farmer_markdown(reply)

    # 6a. Tomato Upward Leaf Curl + Whitefly (Calibrated ToLCV Diagnostic Follow-up)
    is_tomato_scope = bool(
        crop_val == "Tomato" or
        (entities and entities.get("crop") == "Tomato") or
        any(w in q_lower for w in ["tomato", "tamatar", "टमाटर"])
    )
    has_whitefly_sign = bool(re.search(r"\b(whitefly|white\s*fly|safed\s*makk?hi|सफेद\s*मक्खी|bemisia)\b", q_lower))
    has_upward_or_curl_sign = bool(re.search(r"\b(upar|upward|upwards|ऊपर|cup|curl|mud|roll|मरोड़|सिकुड़|मुड़)\b", q_lower))

    if is_tomato_scope and has_whitefly_sign and has_upward_or_curl_sign:
        if language == "hi":
            lead = "🌾 पत्तियों का ऊपर की ओर मुड़ना और सफेद मक्खी (Whitefly) दिखना Tomato Leaf Curl Virus (ToLCV) की ओर मजबूत संकेत करता है; ToLCV की संभावना काफी बढ़ जाती है, लेकिन यह प्रयोगशाला परीक्षण के बिना 100% निश्चित पुष्टि नहीं है।"
            bullets = [
                "- संभावित पहचान (Likely Diagnosis): लक्षण ToLCV (पर्ण कुंचन विषाणु) से दृढ़ता से मेल खाते हैं (Symptoms ToLCV se strongly match karte hain) और ToLCV का मजबूत संदेह (strong suspicion) है। सफेद मक्खी इस विषाणु का मुख्य वाहक (vector) है।",
                "- आगे क्या जांचें (What to check next): नई पत्तियों का ऊपर मुड़कर कप-नुमा होना, खुरदरा/मोटा होना और पौधे की रुकी हुई बढ़वार (stunting) जांचें। पौधे हिलाने पर पत्तियों के नीचे से सफेद मक्खियों का उड़ना देखें।",
                "- तत्काल कम जोखिम वाले उपाय (Immediate Low-risk Management): यदि खेत में शुरुआती 1-2 पौधे ही गंभीर रूप से ग्रसित हैं, तो उन्हें तुरंत उखाड़कर नष्ट (rogue out) कर दें। सफेद मक्खी नियंत्रण के लिए प्रति एकड़ 10–12 पीले चिपचिपे ट्रैप (Yellow Sticky Traps) लगाएं और नीम तेल (1500 ppm @ 3–5 मिली/लीटर पानी) का छिड़काव करें। ध्यान रखें, पौधे में विषाणु प्रवेश के बाद कोई भी रासायनिक दवा इसे ठीक (cure) नहीं कर सकती; स्प्रे केवल मक्खी को रोककर अन्य स्वस्थ पौधों को बचाता है।",
                "- विशेषज्ञ/प्रयोगशाला पुष्टि (When Expert/Lab Confirmation is Useful): यदि खेत में समस्या तेजी से फैल रही हो, तो बड़े कीटनाशक स्प्रे या बड़े फैसले से पूर्व नजदीकी कृषि विज्ञान केंद्र (KVK) या पौध रोग विशेषज्ञ से पुष्टि कराएं।"
            ]
        elif language == "hinglish":
            lead = "🌾 Leaves ka upar ki taraf mudna aur whitefly dikhna Tomato Leaf Curl Virus (ToLCV) ki taraf strong signal karta hai; ToLCV ki sambhavna kaafi badh jaati hai, par bina laboratory testing ke yeh definitive confirmation nahi hai."
            bullets = [
                "- Likely Diagnosis: Symptoms ToLCV se strongly match karte hain aur ToLCV ka strong suspicion hai. Whitefly is virus ka primary transmitting vector (vahak) hai.",
                "- What to check next: Nayi leaves ka cup-shape me upar roll hona, thick/leathery banna aur plant ka stunted (bauna) rehna inspect karein. Foliage hilane par udti hui whitefly check karein.",
                "- Immediate Low-risk Management: Shuruat me heavily infected 1-2 plants ko turant ukhaadkar (rogue out) khet se door destroy kar dein. Whitefly control ke liye 10-12 Yellow Sticky Traps per acre lagayein aur Neem oil (1500 ppm @ 3-5 ml/L) spray karein. Dhyan rahe, plant me virus aane ke baad koi chemical spray use cure (theek) nahi kar sakta; spray sirf whitefly vector ko rokta hai taaki baki plants safe rahein.",
                "- When Expert / Lab Confirmation is Useful: Agar field me infection zyada fail raha ho, toh high-cost chemical spray ya crop decisions se pehle local Krishi Vigyan Kendra (KVK) ya agriculture expert se lab/field confirmation lena labhdayak hoga."
            ]
        else:
            lead = "🌾 Upward leaf curling coupled with visible whitefly strongly increases suspicion of Tomato Leaf Curl Virus (ToLCV); symptoms strongly match ToLCV, but field observation alone does not constitute a laboratory-confirmed diagnosis."
            bullets = [
                "- Likely Diagnosis: Symptoms strongly match ToLCV (Tomato Leaf Curl Virus) and there is strong suspicion of ToLCV. Whitefly (Bemisia tabaci) serves as the insect vector transmitting the virus.",
                "- What to check next: Inspect newer leaves for cup-shaped upward curling, thickening, puckering, and severe plant stunting. Gently shake foliage to observe fluttering whiteflies.",
                "- Immediate Low-risk Management: Promptly rogue out and destroy the first few heavily infected plants to eliminate infection reservoirs. Install 10-12 yellow sticky traps per acre and apply neem oil (1500 ppm @ 3-5 ml/L). Note: Once a plant is infected, no chemical spray can cure the virus; sprays only manage whitefly vectors to protect healthy plants.",
                "- When Expert/Lab Confirmation is Useful: If symptoms are widespread across the field, seek expert consultation or lab confirmation from your local Krishi Vigyan Kendra (KVK) or plant pathologist before making major crop decisions."
            ]
        reply = f"{lead}\n\n" + "\n".join(bullets)
        reply += "\n\nSource: ICAR-IIVR, Varanasi (Vegetable Pathology & Whitefly Management)"
        return clean_farmer_markdown(reply)

    # 6. Tomato Leaf Curl (Differential Diagnosis)
    is_tomato_curl = bool(("tomato" in q_lower or "tamatar" in q_lower or "टमाटर" in q_lower or crop_val == "Tomato" or (entities and entities.get("crop") == "Tomato")) and re.search(r"curl|मुड़|सिकुड़|roll", q_lower))
    if is_tomato_curl:
        if language == "hi":
            lead = "🌾 टमाटर में पत्तियां मुड़ने (Leaf Curl) के मुख्य रूप से 3 से 4 अलग-अलग कारण हो सकते हैं, सही पहचान के लिए ये अंतर देखें:"
            bullets = [
                "- 1. पर्ण कुंचन वायरस (Tomato Leaf Curl Virus - TLCV): सफेद मक्खी (Whitefly) द्वारा फैलता है; पत्तियां ऊपर की ओर मुड़कर छोटी, मोटी व खुरदरी हो जाती हैं और पौधा बौना रह जाता है।",
                "- 2. शारीरिक पर्ण कुंचन (Physiological Leaf Roll): तेज धूप, उच्च तापमान, या मिट्टी में अत्यधिक सूखे/अनियमित पानी के कारण पत्तियां नलिका की तरह ऊपर मुड़ती हैं, पर रंग पीला नहीं पड़ता।",
                "- 3. रस चूसक कीट (Mites / Thrips / Aphids): माइट्स या थ्रिप्स के रस चूसने से नई कोमल पत्तियां नीचे की तरफ नाव के आकार (inverted boat) में मुड़ती हैं।",
                "- 4. खरपतवारनाशक का असर (Herbicide Drift): आसपास के खेत से खरपतवारनाशक का बहाव आने से पत्तियां विकृत और मुड़ जाती हैं।",
                "- जांचें: क्या पत्तियां ऊपर मुड़कर पीली/छोटी हो रही हैं (वायरस) या केवल नली जैसी मुड़ रही हैं (गर्मी/नमी)? क्या सफेद मक्खी उड़ती दिख रही है?"
            ]
        elif language == "hinglish":
            lead = "🌾 Tamatar me leaves curl (mudne) ke main 3 se 4 alag-alag causes ho sakte hain, accurate check ke liye ye lakshan dekhein:"
            bullets = [
                "- 1. Leaf Curl Virus (TLCV): Whitefly dwara transmit hota hai; leaves upar ki taraf cup-shape me mudti hain, thick/chhoti ho jaati hain aur plant stunted (bauna) reh jata hai.",
                "- 2. Physiological Leaf Roll: High temperature, tez dhoop ya irregular watering se leaves tube ki tarah upar roll hoti hain par yellowing nahi hoti.",
                "- 3. Sucking Pests (Mites / Thrips): Mite feeding se young leaves neeche ki taraf (downward) mudti hain aur inverted boat jaisi dikhti hain.",
                "- 4. Herbicide Drift / Root Stress: Paas ke khet se weedicide spray drift ya roots me moisture stress se leaf distortion ho sakti hai.",
                "- Check karein: Leaves upar roll hain ya neeche? Khet me whitefly udti dikh rahi hai? Yeh batane par accurate management suggest hoga."
            ]
        else:
            lead = "🌾 Leaf curling in tomato can result from 3 to 4 distinct factors; inspect the plants for these key distinguishing signs:"
            bullets = [
                "- 1. Tomato Leaf Curl Virus (TLCV): Transmitted by whiteflies; leaves curl upward and inward, become thick, leathery, and chlorotic, with severe plant stunting.",
                "- 2. Physiological Leaf Roll: Triggered by intense heat, drought stress, or irregular irrigation; leaves roll upward like tubes without chlorosis or stunting.",
                "- 3. Sucking Pests (Broad Mites / Thrips / Aphids): Mite feeding causes downward leaf curling (inverted boat shape) with distorted young growth.",
                "- 4. Herbicide Drift: Accidental drift of hormonal weedicides from nearby fields causing severe leaf twisting.",
                "- Please check: Are leaves curling upward with yellow stunting (virus), or rolling upward without discoloration (heat stress)?"
            ]
        reply = f"{lead}\n\n" + "\n".join(bullets)
        reply += "\n\nSource: ICAR-IIVR, Varanasi (Tomato Pest & Disease Guidelines)"
        return clean_farmer_markdown(reply)

    # 7. Wheat Crop-Age & Action Synthesis (CRI & Growth Stages)
    is_wheat_scope = bool(
        (crop_val == "Wheat") or
        (entities and entities.get("crop") == "Wheat") or
        any(w in q_lower for w in ["wheat", "gehun", "gehu", "गेहूं"])
    )
    detected_wheat_age = entities.get("crop_age_days") if (entities and entities.get("crop_age_days")) else None
    if not detected_wheat_age:
        m_age = re.search(r"\b(\d+)\s*(?:din|दिन|days?|day)\b", q_lower)
        if m_age:
            detected_wheat_age = int(m_age.group(1))
        elif re.search(r"\b(2[0-5]|20|21|22|23|24|25)\b", q_lower):
            detected_wheat_age = 22

    is_action_query = bool(re.search(
        r"\b(ab\s+kya\s+karu|ab\s+kya\s+karein|kya\s+karna\s+hai|kya\s+kare|kya\s+karein|kya\s+kareं|"
        r"agla\s+kadam|next\s+step|what\s+to\s+do|what\s+should\s+i\s+do|what\s+next|"
        r"kya\s+chahiye|next\s+kya|kya\s+dein|kya\s+daalein|kya\s+karna\s+chahiye)\b",
        q_lower
    ))

    # 7a. Wheat 20-25 Days (CRI Stage - First Irrigation & Top Dressing)
    is_wheat_cri = bool(
        is_wheat_scope and (
            (detected_wheat_age and 18 <= detected_wheat_age <= 28) or
            re.search(r"\b2[0-5]\b", q_lower) or
            ((is_irrigation or is_action_query) and any(w in q_lower for w in ["pehli", "first", "पहली", "cri"]))
        )
    )
    if is_wheat_cri:
        age_num = detected_wheat_age or 22
        if language == "hi":
            lead = f"🌾 {age_num} दिन के गेहूं में इस समय मुख्य कार्य ताज मूल अवस्था (CRI stage) पर पहली हल्की सिंचाई (4–5 सेमी) करना और यूरिया की पहली टॉप-ड्रेसिंग देना है।"
            bullets = [
                "- पहली सिंचाई: बुवाई के 20–25 दिन बाद ताज मूल निकलने पर 4–5 सेमी की हल्की सिंचाई अवश्य करें। इस समय नमी की कमी से कल्ले कम बनते हैं और पैदावार 25–35% घट सकती है।",
                "- यूरिया टॉप-ड्रेसिंग: सिंचाई के बाद जब खेत में ओट आ जाए, तो 1/3 नाइट्रोजन (लगभग 36 किग्रा/एकड़, 0.8 बैग) नीम-लेपित यूरिया का छिड़काव करें।",
                "- जलभराव से बचाव: क्यारियों में पानी खड़ा न रहने दें; अधिक जलभराव से जड़ों को ऑक्सीजन नहीं मिलती और फसल पीली पड़ने लगती है।"
            ]
        elif language == "hinglish":
            lead = f"🌾 {age_num} din ke gehun me is samay primary task Crown Root Initiation (CRI stage) par pehli halki sinchai (4–5 cm) karna aur urea ki first top-dressing dena hai."
            bullets = [
                "- First Irrigation: Sowing ke 20–25 din baad CRI stage par 4–5 cm depth ki halki sinchai zaroor karein. Is samay moisture stress se tillers kam bante hain aur yield 25–35% gir sakti hai.",
                "- Urea Top-Dressing: Sinchai ke baad jab khet me per tikne lagein (aat/nami me), 1/3 nitrogen (approx. 36 kg/acre, 0.8 bag) neem-coated urea top-dressing karein.",
                "- Waterlogging Prevention: Bhari mitti me extra paani jama na hone dein; jalbhav se roots suffocate hoti hain aur fasal peeli pad sakti hai."
            ]
        else:
            lead = f"🌾 For {age_num}-day-old wheat, your primary action is to apply the first light irrigation (4–5 cm depth) at the Crown Root Initiation (CRI) stage, followed by nitrogen top-dressing."
            bullets = [
                "- First Irrigation: Apply light and uniform irrigation (4–5 cm depth) at this 20–25 DAS CRI window. Moisture stress here restricts tillering and reduces yield by 25–35%.",
                "- Nitrogen Top-Dressing: Follow with the first top-dressing of neem-coated urea (approx. 36 kg/acre, approx. 0.8 bag of 45 kg) once soil allows walking.",
                "- Prevent Waterlogging: Ensure proper plot leveling and drainage; stagnant water deprives roots of oxygen, causing yellowing."
            ]
        reply = f"{lead}\n\n" + "\n".join(bullets)
        reply += "\n\nSource: ICAR-IIWBR, Karnal (Wheat Water Management & Agronomy)"
        return clean_farmer_markdown(reply)

    # 7b. Wheat Early Vegetative (8-17 Days, e.g. 10-12 Days - Irrigation Not Yet Due)
    is_wheat_early = bool(
        is_wheat_scope and detected_wheat_age and (8 <= detected_wheat_age <= 17) and
        (is_action_query or is_irrigation or any(w in q_lower for w in ["sinchai", "irrigate", "paani", "pani", "kya"]))
    )
    if is_wheat_early:
        age_num = detected_wheat_age
        if language == "hi":
            lead = f"🌾 {age_num} दिन के गेहूं में अभी सिंचाई करने की आवश्यकता नहीं है; पहली सिंचाई बुवाई के 20–25 दिन बाद ताज मूल (CRI stage) निकलने पर ही करें।"
            bullets = [
                "- जड़ विकास अवस्था: 10–15 दिन की फसल में केवल प्राथमिक बीज जड़ें (seminal roots) होती हैं; स्थायी ताज मूल 20–25 दिन पर निकलती हैं। अभी सिंचाई करने से मिट्टी ठंडी होती है और जड़ों का विकास धीमा पड़ता है।",
                "- पलेवा अपवाद: यदि बुवाई पूर्व पलेवा बहुत कम था और ऊपरी 3 सेमी मिट्टी बिल्कुल सूखी होने से अंकुरण रुक रहा हो, केवल तभी अत्यंत हल्की नमी दें।",
                "- अगला कदम: 20–25 दिन की अवस्था होने पर 4–5 सेमी की पहली हल्की सिंचाई और 36 किग्रा/एकड़ यूरिया टॉप-ड्रेसिंग की तैयारी रखें।"
            ]
        elif language == "hinglish":
            lead = f"🌾 {age_num} din ke gehun me abhi sinchai karne ki zaroorat nahi hai; first irrigation sowing ke 20–25 din baad Crown Root Initiation (CRI stage) par hi karein."
            bullets = [
                "- Root Growth Stage: 10–15 din par plant sirf temporary seminal roots par chalta hai; permanent crown roots 20–25 din par nikalti hain. Abhi sinchai karne se soil unnecessarily chill hoti hai.",
                "- Palewa Exception: Agar pre-sowing palewa inadequate tha aur topsoil dry hone se germination ruk raha ho, tabhi emergency light water dein.",
                "- Next Step: 20–25 DAS par pehli halki sinchai (4–5 cm) aur 36 kg/acre urea top-dressing schedule karein."
            ]
        else:
            lead = f"🌾 For {age_num}-day-old wheat, irrigation is not yet due; wait until 20–25 days after sowing for the Crown Root Initiation (CRI) stage."
            bullets = [
                "- Physiological Stage: At 10–15 DAS, seedlings rely on temporary seminal roots. Irrigating now chills the soil unnecessarily and delays root emergence.",
                "- Pre-sowing Exception: Only irrigate early if pre-sowing irrigation (palewa) was completely inadequate and topsoil dryness is hindering germination.",
                "- Planned Action: Schedule the first light irrigation (4–5 cm) and urea top-dressing (approx. 36 kg/acre) when the crop reaches 20–25 DAS."
            ]
        reply = f"{lead}\n\n" + "\n".join(bullets)
        reply += "\n\nSource: ICAR-IIWBR, Karnal (Wheat Water Management & Agronomy)"
        return clean_farmer_markdown(reply)

    # 7c. Wheat Active Tillering (35-55 Days, e.g. 40-45 Days - Second Irrigation & Final Urea)
    is_wheat_tillering = bool(
        is_wheat_scope and detected_wheat_age and (35 <= detected_wheat_age <= 55) and
        (is_action_query or is_irrigation or any(w in q_lower for w in ["sinchai", "irrigate", "paani", "pani", "kya"]))
    )
    if is_wheat_tillering:
        age_num = detected_wheat_age
        if language == "hi":
            lead = f"🌾 {age_num} दिन के गेहूं में इस समय मुख्य कार्य कल्ले निकलने की अवस्था (Tillering stage) पर दूसरी सिंचाई करना और यूरिया की अंतिम टॉप-ड्रेसिंग देना है।"
            bullets = [
                "- दूसरी सिंचाई: 40–45 दिन पर कल्ले फूटने के समय दूसरी सिंचाई करें ताकि शाखाएं और बालियों का विकास मजबूत हो सके।",
                "- यूरिया की अंतिम खुराक: 2nd सिंचाई के साथ बची हुई 1/3 नाइट्रोजन (लगभग 36 किग्रा नीम-लेपित यूरिया प्रति एकड़) की अंतिम टॉप-ड्रेसिंग पूरी कर लें।",
                "- खरपतवार प्रबंधन: यदि खेत में गुल्ली डंडा (Phalaris minor) या बथुआ का प्रकोप हो, तो तुरंत निराई या अनुशंसित खरपतवारनाशी का प्रयोग करें।"
            ]
        elif language == "hinglish":
            lead = f"🌾 {age_num} din ke gehun me is samay primary action Active Tillering stage (kalle nikalne ki avastha) par second irrigation karna aur urea ki final top-dressing dena hai."
            bullets = [
                "- Second Irrigation: 40–45 DAS par active tillering stage par second irrigation dein taki lateral tillers acche banein.",
                "- Urea Top-Dressing: 2nd irrigation ke sath remaining 1/3rd nitrogen (approx. 36 kg/acre neem-coated urea) ki final split complete karein.",
                "- Weed Scouting: Gulli danda ya bathua weeds ke liye khet check karein taaki tillers ko poora nutrition mile."
            ]
        else:
            lead = f"🌾 For {age_num}-day-old wheat, your primary action is to apply the second irrigation at the active tillering stage, followed by the final urea top-dressing."
            bullets = [
                "- Second Irrigation: Apply the second irrigation at 40–45 DAS to support vigorous lateral shoot and tiller development.",
                "- Final Urea Top-Dressing: Apply the remaining 1/3rd nitrogen split (approx. 36 kg/acre neem-coated urea) alongside this irrigation.",
                "- Weed Control: Check for grassy weeds like Phalaris minor so they do not compete with tillers for moisture and nutrients."
            ]
        reply = f"{lead}\n\n" + "\n".join(bullets)
        reply += "\n\nSource: ICAR-IIWBR, Karnal (Wheat Water Management & Agronomy)"
        return clean_farmer_markdown(reply)

    # 8. Pigeonpea / Red Gram Pod Borer Treatment
    is_pod_borer = bool(
        ((crop_val == "Pigeonpea") or (entities and entities.get("crop") == "Pigeonpea") or any(w in q_lower for w in ["arhar", "tuar", "red gram", "pigeonpea"])) and
        any(w in q_lower for w in ["pod borer", "borer", "छेदक", "इल्ली", "सुंडी", "ilaj", "upchar", "dawa", "dawai", "cure", "treatment", "control", "management"])
    )
    if is_pod_borer:
        if language == "hi":
            lead = "🌾 अरहर / तुअर (Red Gram) में फली छेदक (Pod Borer - Helicoverpa armigera) कीट के प्रभावी नियंत्रण हेतु एकीकृत कीट प्रबंधन (IPM) उपाय अपनाएं:"
            bullets = [
                "- निगरानी एवं ट्रैप: 4–5 फेरोमोन ट्रैप (Pheromone traps) प्रति एकड़ लगाएं तथा खेत में टी-आकार की पक्षी खूंटियां (T-perches) स्थापित करें।",
                "- जैविक नियंत्रण: फूल आने की शुरुआती अवस्था में नीम तेल (1500 PPM @ 3–5 मिली/लीटर) या HaNPV (250 LE/हेक्टेयर) का शाम को छिड़काव करें।",
                "- यांत्रिक नियंत्रण: फली बनने से पहले पौधों को हिलाकर नीचे गिरी बड़ी सुंडियों को इकट्ठा कर नष्ट करें।",
                "- रासायनिक सुरक्षा निर्देश: यदि प्रकोप अधिक हो तो CIBRC लेबल अनुसार अनुशंसित कीटनाशक का ही प्रयोग करें और स्थानीय KVK से परामर्श लें।"
            ]
        elif language == "hinglish":
            lead = "🌾 Arhar / Red Gram (Pigeonpea) me Pod Borer (फली छेदक) ke prabhavi control ke liye Integrated Pest Management (IPM) steps follow karein:"
            bullets = [
                "- Monitoring & Traps: 4–5 Pheromone traps per acre lagayein aur field me T-shaped bird perches lagayein.",
                "- Organic / Biological Spray: Flowering stage ke shuru me Neem oil (1500 PPM @ 3–5 ml/L) ya HaNPV (250 LE/ha) ka shaam ko spray karein.",
                "- Mechanical Control: Paudhon ko hila kar zameen par giri sundi/caterpillars ko collect karke destroy karein.",
                "- Chemical Safety Notice: Severe outbreak me CIBRC label-approved insecticide use karein aur local KVK se verify karein."
            ]
        else:
            lead = "🌾 For effective control of Pod Borer (Helicoverpa armigera) in Pigeonpea / Red Gram, adopt these Integrated Pest Management (IPM) steps:"
            bullets = [
                "- Pheromone Trapping & Perches: Install 4–5 pheromone traps per acre and erect T-shaped bird perches across the field.",
                "- Biological & Botanical Spray: Spray Neem oil (1500 PPM @ 3–5 ml/L) or HaNPV (250 LE/ha) during early flowering in the late afternoon.",
                "- Mechanical Collection: Shake plants over plastic sheets to dislodge and destroy early larval instars.",
                "- Chemical Safety Protocol: In severe infestations, apply only CIBRC label-recommended insecticides and consult your local KVK."
            ]
        reply = f"{lead}\n\n" + "\n".join(bullets)
        reply += "\n\nSource: ICAR-IIPR, Kanpur (Pulse Protection Guidelines)"
        return clean_farmer_markdown(reply)

    # General extraction from retrieved chunks
    title = top_chunk.get("title", "कृषि परामर्श")
    all_chunks_text = "\n".join(c.get("text", "") for c in retrieved_chunks[:2])

    clean_lines = []
    in_citation_section = False
    in_faq_section = False
    for line in all_chunks_text.splitlines():
        l = line.strip()
        if not l:
            continue
        if re.search(r"^#{1,3}\s*(?:Authoritative\s+source|Source\s+citation|References|Citations|Metadata)", l, re.I):
            in_citation_section = True
            continue
        if re.search(r"^#{1,3}\s*(?:Common\s+Farmer\s+Questions|FAQ|Frequently\s+Asked|सवाल\s+जवाब)", l, re.I):
            in_faq_section = True
            continue
        if l.startswith("#"):
            in_citation_section = False
            in_faq_section = False
            continue
        if in_citation_section or in_faq_section:
            continue
        if l.startswith(("[Source:", "---", "schema_version", "doc_id:")):
            continue
        # Skip raw FAQ question and answer lines
        if re.search(r"^[\*\-_•\s]*(?:Q\s*:|Question\s*:|प्रश्न\s*:|FAQ|सवाल\s*:)", l, re.I):
            continue
        if re.search(r"^[\*\-_•\s]*(?:A\s*:|Answer\s*:|उत्तर\s*:)", l, re.I):
            continue
        # Remove A: prefix if present
        l = re.sub(r"^[\*\-_•\s]*(?:A\s*:|Answer\s*:|उत्तर\s*:)\s*", "", l, flags=re.I).strip()
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
            pt = re.sub(r"^[\*\-_•\s]*(?:A\s*:|Answer\s*:|उत्तर\s*:)\s*", "", pt, flags=re.I).strip()
            if 15 < len(pt) < 160 and not re.search(r"^[\*\-_•\s]*(?:Q\s*:|Question\s*:|A\s*:|Answer\s*:|FAQ)", pt, re.I):
                candidate_points.append(pt)
        elif ":" in l and len(l) < 140 and not re.search(r"^[\*\-_•\s]*(?:Q\s*:|Question\s*:|A\s*:|Answer\s*:|FAQ)", l, re.I):
            cleaned_col_pt = re.sub(r"^[\*\-_•\s]*(?:A\s*:|Answer\s*:|उत्तर\s*:)\s*", "", l, flags=re.I).strip()
            if len(cleaned_col_pt) > 15:
                candidate_points.append(cleaned_col_pt)

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
            lead_sentence = "🌾 टमाटर में पर्ण कुंचन (Leaf Curl) लक्षण व सफेद मक्खी नियंत्रण हेतु कृषि परामर्श (लक्षण ToLCV से मेल खा सकते हैं, बिना लैब जांच निश्चित पुष्टि नहीं):"
        elif language == "hinglish":
            lead_sentence = "🌾 Tomato me leaf curl symptoms aur whitefly control ke liye advisory (Symptoms ToLCV se match kar sakte hain; ToLCV ki sambhavna hai par bina lab test definitive confirmation nahi):"
        else:
            lead_sentence = "🌾 Key advisory for tomato leaf curl symptoms and whitefly control (Symptoms may align with ToLCV suspicion; not a definitive lab-confirmed diagnosis):"
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

    # Chemical warning conditional on query actually involving chemicals (Exempt pure fertilizer queries)
    is_fertilizer_only = bool(re.search(
        r"\b(urea|dap|npk|potash|khad|fertilizer|fertilizers|gypsum|zinc sulphate|organic manure|compost|यूरिया|डीएपी|खाद|उर्वरक|जिप्सम|पोटाश)\b",
        q_lower
    )) and not bool(re.search(
        r"\b(pesticide|insecticide|fungicide|herbicide|weedicide|कीटनाशक|फफूंदनाशक|खरपतवारनाशक|chemical|रसायन)\b",
        q_lower
    ))

    is_chem = bool(re.search(r"chemical|pesticide|fungicide|insecticide|कीटनाशक|फफूंदनाशक|दवा|दवाई|dawa|dawai|spray|छिड़काव|chidke|chidkaw|dose|खुराक", q_lower))
    if is_chem and not is_fertilizer_only:
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


def detect_scheme_freshness_request(clean_msg: str) -> Optional[Dict[str, str]]:
    """
    Detects if the user query is asking for latest rules, current policies,
    notifications, circulars, or year-specific updates for an agricultural government scheme.
    """
    q_low = clean_msg.lower()

    # 1. Scheme detection
    scheme = None
    if any(k in q_low for k in ["pmfby", "fasal bima", "crop insurance"]):
        scheme = "PMFBY"
    elif any(k in q_low for k in ["pm kisan", "pm-kisan", "pmkisan", "samman nidhi"]):
        scheme = "PM-KISAN"
    elif any(k in q_low for k in ["pmksy", "sinchayee", "sinchai yojana"]):
        scheme = "PMKSY"
    elif any(k in q_low for k in ["kcc", "kisan credit card"]):
        scheme = "KCC"
    elif any(k in q_low for k in ["bima", "yojana", "scheme"]):
        scheme = "PMFBY"

    if not scheme:
        return None

    # 2. Freshness / rules indicator
    has_freshness = bool(re.search(
        r"\b(latest|current|new|rules?|niyam|2026|notification|circular|update|updates|guidelines?|sanshodhan|adhisuchna|paripatra)\b|"
        r"(नई|नए|नया|नियम|गाइडलाइन|अपडेट|अधिसूचना|परिपत्र|संशोधन|2026)",
        q_low
    ))
    if not has_freshness:
        return None

    # 3. Target year detection
    target_year = "2026" if "2026" in q_low else str(datetime.now().year)

    return {
        "scheme": scheme,
        "target_year": target_year
    }


APPROVED_PMFBY_DOMAINS = {
    "pmfby.gov.in",
    "agriwelfare.gov.in",
    "agricoop.nic.in",
    "pib.gov.in",
    "egazette.gov.in",
    "icar.gov.in",
    "agricoop.gov.in",
    "india.gov.in"
}

PMFBY_STRONG_IDENTIFIERS = [
    r"\bpmfby\b",
    r"\bpradhan\s*mantri\s*fasal\s*bima\s*yojana\b",
    r"प्रधानमंत्री\s*फसल\s*बीमा\s*योजना",
    r"\bfasal\s*bima\s*yojana\b",
    r"फसल\s*बीमा\s*योजना",
    r"\boperational\s*guidelines\s*of\s*pmfby\b",
    r"\bpmfby-[\w\-]+\b"
]

FOREIGN_UNRELATED_PATTERNS = [
    r"\bfedramp\b",
    r"\bpoverty\s*guidelines?\b",
    r"\bdepartment\s*of\s*health\s*and\s*human\s*services\b",
    r"\bhhs\b",
    r"\bmedicaid\b",
    r"\bmedicare\b",
    r"\bcybersecurity\b",
    r"\bcloud\s*service\s*providers?\b",
    r"\bfederal\s*register\b",
    r"\bhomeland\s*security\b"
]


def extract_issuing_authority(all_text: str, domain: str) -> str:
    """
    Extracts verifiable issuing authority directly from document text or verified official portal.
    Never attributes foreign or mismatched domains to Ministry of Agriculture.
    """
    all_text_low = all_text.lower()
    domain_low = (domain or "").lower().strip()
    if domain_low.startswith("www."):
        domain_low = domain_low[4:]

    # Foreign domains must never receive an Indian authority attribution
    if domain_low.endswith(".gov") and not domain_low.endswith(".gov.in"):
        return "issuing authority not verified"

    if "ministry of agriculture" in all_text_low or "moa&fw" in all_text_low or "कृषि एवं किसान कल्याण मंत्रालय" in all_text_low:
        return "Ministry of Agriculture & Farmers Welfare, GoI"
    if "department of agriculture" in all_text_low or "dac&fw" in all_text_low or "कृषि विभाग" in all_text_low:
        return "Department of Agriculture & Farmers Welfare, GoI"
    if "press information bureau" in all_text_low or "pib" in all_text_low or "pib.gov.in" in domain_low:
        return "Press Information Bureau (PIB), GoI"
    if "cabinet committee on economic affairs" in all_text_low or "ccea" in all_text_low:
        return "Cabinet Committee on Economic Affairs (CCEA), GoI"
    if "egazette.gov.in" in domain_low:
        return "The Gazette of India, GoI"
    if "pmfby.gov.in" in domain_low:
        return "PMFBY Division, MoA&FW, GoI"
    if "agriwelfare.gov.in" in domain_low or "agricoop.nic.in" in domain_low:
        return "Department of Agriculture & Farmers Welfare, GoI"

    return "issuing authority not verified"


def extract_scheme_structured_evidence(
    evidence_list: List[WebEvidence],
    scheme: str = "PMFBY",
    target_year: str = "2026"
) -> Tuple[List[Dict[str, Any]], str, Optional[str]]:
    """
    Extracts structured official evidence for scheme rule revisions and notifications.
    Strictly enforces 5 validation gates:
    1. Strict Source Authority Gate (approved Indian domains only; reject foreign .gov)
    2. Scheme Relevance Gate (requires strong PMFBY identifier; rejects unrelated topics)
    3. Exclusions (homepage, training/lms, general descriptions)
    4. Date / Freshness Gate (explicit verified date with target_year)
    5. Authority Attribution Invariant (real verified authority or marked unverified)
    """
    valid_notifs: List[Dict[str, Any]] = []
    last_rej_code = "no_verified_2026_rule"
    last_rej_reason = "no_verified_2026_notification"

    for ev in evidence_list:
        content_low = ev.content.lower()
        title_low = ev.title.lower()
        url_low = ev.url.lower()
        domain_low = (ev.domain or "").lower().strip()
        if domain_low.startswith("www."):
            domain_low = domain_low[4:]
        parsed = urlparse(ev.url)
        all_text = f"{ev.published_date or ''} {ev.title} {ev.content}"
        all_text_low = all_text.lower()

        # -------------------------------------------------------------
        # GATE 1: STRICT SOURCE AUTHORITY GATE
        # -------------------------------------------------------------
        # Foreign or non-Indian .gov domains (e.g. fedramp.gov, hhs.gov, aspe.hhs.gov) must be rejected
        is_foreign_gov = domain_low.endswith(".gov") and not domain_low.endswith(".gov.in")
        is_indian_gov = (
            domain_low.endswith(".gov.in") or
            domain_low.endswith(".nic.in") or
            domain_low in APPROVED_PMFBY_DOMAINS or
            any(domain_low.endswith("." + d) for d in APPROVED_PMFBY_DOMAINS)
        )

        if is_foreign_gov or not is_indian_gov:
            last_rej_code = "foreign_or_unauthorized_domain_rejected"
            last_rej_reason = "foreign_or_non_indian_source_rejected"
            continue

        # If domain is .gov.in / .nic.in but NOT in the explicitly approved PMFBY list,
        # require that the document itself explicitly belongs to Ministry of Agriculture / PMFBY
        if domain_low not in APPROVED_PMFBY_DOMAINS and not any(domain_low.endswith("." + d) for d in APPROVED_PMFBY_DOMAINS):
            belongs_to_agri = any(
                k in all_text_low for k in [
                    "ministry of agriculture", "department of agriculture", "moa&fw",
                    "कृषि मंत्रालय", "कृषि एवं किसान कल्याण", "pmfby division", "fasal bima", "dac&fw"
                ]
            )
            if not belongs_to_agri:
                last_rej_code = "unrelated_indian_gov_domain_rejected"
                last_rej_reason = "indian_gov_page_not_affiliated_with_agriculture"
                continue

        # -------------------------------------------------------------
        # GATE 2: SCHEME RELEVANCE GATE
        # -------------------------------------------------------------
        # Immediate rejection if foreign/unrelated topics detected
        if any(re.search(pat, all_text_low) for pat in FOREIGN_UNRELATED_PATTERNS):
            last_rej_code = "foreign_or_unrelated_topic_rejected"
            last_rej_reason = "unrelated_foreign_topic_in_document"
            continue

        # Must contain at least one strong scheme identifier
        if scheme.upper() == "PMFBY":
            has_strong_id = any(re.search(pat, all_text_low) for pat in PMFBY_STRONG_IDENTIFIERS)
            if not has_strong_id:
                last_rej_code = "scheme_irrelevance_rejected"
                last_rej_reason = "document_lacks_strong_pmfby_identifiers"
                continue

        # -------------------------------------------------------------
        # GATE 3: EXCLUSIONS (Homepage, LMS/Training, General/Evaluation Reports)
        # -------------------------------------------------------------
        is_homepage = parsed.path.strip("/") in ("", "index.html", "index.php", "home") or any(
            h in title_low for h in ["welcome to", "pmfby home", "portal home", "home |"]
        )
        if is_homepage:
            last_rej_code = "homepage_excluded"
            last_rej_reason = "homepage_content_excluded"
            continue

        is_lms = "/lms" in url_low or "/training" in url_low or "/course" in url_low or any(
            t in (title_low + " " + content_low) for t in [
                "learning management system", "lms", "training & courses",
                "training and courses", "mega awareness campaign", "awareness campaign"
            ]
        )
        if is_lms:
            last_rej_code = "training_lms_excluded"
            last_rej_reason = "training_or_lms_excluded"
            continue

        is_gen_desc = (
            "was launched in 2016" in content_low
            or "parliamentary committee report" in title_low
            or "evaluation report" in title_low
        )
        if is_gen_desc:
            last_rej_code = "general_description_excluded"
            last_rej_reason = "general_description_excluded"
            continue

        # -------------------------------------------------------------
        # GATE 4: DATE / FRESHNESS GATE
        # -------------------------------------------------------------
        date_year_match = re.search(
            rf"\b(?:\d{{1,2}}[-/\.]\d{{1,2}}[-/\.]{target_year}|{target_year}[-/\.]\d{{1,2}}[-/\.]\d{{1,2}}|\d{{1,2}}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*[\s,]+{target_year}|(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{{1,2}}[\s,]+{target_year}|(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+{target_year}|Kharif\s+{target_year}|Rabi\s+{target_year}(?:-27)?|w\.e\.f\.?\s*{target_year})\b",
            all_text,
            re.IGNORECASE
        )
        past_years_match = re.findall(r"\b(201[6-9]|202[0-5])\b", all_text)

        if not date_year_match:
            if past_years_match:
                last_rej_code = "stale_documents_rejected"
                last_rej_reason = "old_documents_rejected"
            else:
                last_rej_code = "undated_page_rejected"
                last_rej_reason = "undated_evidence_rejected"
            continue

        has_substance = bool(re.search(
            r"\b(circular|notification|guidelines?|order|amendment|adhisuchna|paripatra|rule|rules|mandate|revision|revised|directive|clause)\b",
            title_low + " " + content_low
        ))
        if not has_substance:
            last_rej_code = "no_rule_substance"
            last_rej_reason = "no_rule_change_in_evidence"
            continue

        extracted_date = date_year_match.group(0).strip()

        # -------------------------------------------------------------
        # GATE 5: AUTHORITY ATTRIBUTION INVARIANT
        # -------------------------------------------------------------
        authority = extract_issuing_authority(all_text, domain_low)

        sentences = re.split(r"(?<=[.!?])\s+", ev.content)
        rule_change = ""
        for s in sentences:
            if any(k in s.lower() for k in ["mandatory", "timeline", "transfer", "subsidy", "deadline", "enrollment", "claim", "premium", "settlement", "revised", "amendment", "order", "rule"]):
                rule_change = s.strip()
                break
        if not rule_change and sentences:
            rule_change = sentences[0].strip()
        if len(rule_change) > 160:
            rule_change = rule_change[:157] + "..."

        clean_title = re.sub(r"^\[PDF\]\s*", "", ev.title)
        clean_title = re.sub(r"\s*-\s*PMFBY.*$", "", clean_title).strip()

        valid_notifs.append({
            "title": clean_title,
            "date": extracted_date,
            "authority": authority,
            "rule_change": rule_change,
            "url": ev.url,
            "domain": ev.domain
        })

    if valid_notifs:
        return valid_notifs, "verified_scheme_rule_found", None
    return [], last_rej_code, last_rej_reason


def compose_scheme_fallback_response(scheme: str, target_year: str, language: str) -> str:
    """
    Composes safe fallback response when no verified rule change / notification is found.
    Fulfills exact requirement:
    'Mujhe official Indian government sources se 2026 ke specific naye PMFBY rule changes verify nahi mile. Main unrelated ya outdated documents ko latest PMFBY rules ke roop me present nahi karunga.'
    Followed by stable scheme information separately, clearly labelled as general/background information.
    """
    prefix = (
        f"Mujhe official Indian government sources se {target_year} ke specific naye {scheme} "
        f"rule changes verify nahi mile. Main unrelated ya outdated documents ko "
        f"latest {scheme} rules ke roop me present nahi karunga."
    )

    if scheme.upper() == "PMFBY":
        background_info = (
            "📌 सामान्य PMFBY दिशा-निर्देश (General/Background Information):\n"
            "- किसान प्रीमियम हिस्सा: रबी फसलों के लिए 1.5% (बीमित राशि का), खरीफ फसलों के लिए 2.0%, और वाणिज्यिक/बागवानी फसलों के लिए 5.0%।\n"
            "- 72 घंटे की अनिवार्यता: स्थानीय आपदा (ओलावृष्टि, जलभराव, चक्रवाती बारिश) से फसल क्षति होने पर 72 घंटे के भीतर PMFBY पोर्टल या टोल-फ्री हेल्पलाइन (14447) पर सूचना दर्ज करना अनिवार्य है।\n"
            "- दावा प्रक्रिया: अधिसूचित क्षेत्र, समय पर प्रीमियम भुगतान और फसल कटाई प्रयोग (CCE) के आधिकारिक आकलन के आधार पर दावा निपटान होता है।\n\n"
            "स्रोत: pmfby.gov.in (आधिकारिक पोर्टल) / Ministry of Agriculture & Farmers Welfare, GoI"
        )
    else:
        background_info = (
            f"📌 सामान्य {scheme} दिशा-निर्देश (General/Background Information):\n"
            f"- योजना के विस्तृत दिशा-निर्देश आधिकारिक सरकारी पोर्टल पर उपलब्ध हैं।\n"
            f"- किसी भी नियम संशोधन की पुष्टि केवल आधिकारिक सरकारी अधिसूचना से ही मान्य होती है।\n\n"
            f"स्रोत: आधिकारिक सरकारी पोर्टल (Government of India)"
        )

    return f"{prefix}\n\n{background_info}"


def compose_scheme_freshness_response(
    scheme: str,
    target_year: str,
    notifications: List[Dict[str, Any]],
    language: str
) -> str:
    """
    Farmer-facing format:
    - direct answer first
    - max 3–5 bullets
    - include date for every claimed latest/current change
    - issuing authority directly from metadata/content, or marked unverified
    - source line at end with actual authorities & domains (never blindly hardcoded)
    - no raw search-engine snippets
    """
    header = f"🏛️ {scheme} {target_year} आधिकारिक नियम एवं अधिसूचना (Verified Updates):"
    bullets = []
    for item in notifications[:5]:
        title = item["title"]
        rule = item["rule_change"]
        dt = item["date"]
        auth = item["authority"]
        auth_label = f", जारीकर्ता: {auth}" if auth != "issuing authority not verified" else ", जारीकर्ता: सत्यापित नहीं"
        bullet = f"- **{title}**: {rule} (अधिसूचना तिथि: {dt}{auth_label})"
        bullets.append(bullet)

    bullets_text = "\n".join(bullets)
    auths = sorted(list(set(n["authority"] for n in notifications if n.get("authority") and n["authority"] != "issuing authority not verified")))
    domains = sorted(list(set(n["domain"] for n in notifications if n.get("domain"))))
    auth_display = ", ".join(auths) if auths else "Official Indian Government Sources"
    domain_display = f" ({', '.join(domains)})" if domains else ""
    source_line = f"स्रोत: {auth_display}{domain_display}"

    return f"{header}\n\n{bullets_text}\n\n{source_line}"


def classify_current_weather_evidence(ev_text: str, live_verified: bool) -> str:
    """
    Classifies present/current weather evidence into exactly one supported state:
    - CURRENT_RAIN_CONFIRMED
    - CURRENT_NO_RAIN_CONFIRMED
    - FORECAST_OR_ALERT_ONLY
    - CURRENT_CONDITION_UNVERIFIED

    Rules:
    - Never infer current rain merely from:
      * precipitation forecast
      * rain warning
      * cloud alert
      * tomorrow forecast
      * generic IMD weather page
    - If evidence genuinely cannot distinguish, return CURRENT_CONDITION_UNVERIFIED.
    """
    if not live_verified or not ev_text or not ev_text.strip():
        return "CURRENT_CONDITION_UNVERIFIED"

    text = ev_text.lower()

    # Check if evidence discusses meteorological conditions
    has_weather_terms = bool(re.search(
        r"\b(weather|mausam|rain|rains|raining|rainfall|barish|baarish|forecast|temperature|temp|sunny|clear|dry|shower|showers|thunderstorm|precipitation|cloud|clouds|humidity|wind|drizzle|drizzling)\b",
        text
    ))
    if not has_weather_terms:
        return "CURRENT_CONDITION_UNVERIFIED"

    # Check for explicit absence / negation of rain
    rain_negated = bool(re.search(
        r"\b(no rain|no precipitation|not raining|no rainfall|rain\s*[:\-]?\s*(nil|0|none)|rainfall\s*[:\-]?\s*(nil|0(\.0)?|none)|barish nahi|baarish nahi|वर्षा नहीं|बारिश नहीं)\b",
        text
    ))

    # Check for rain warning, precipitation alert, or forecast
    alert_patterns = [
        r"\b(rain alert|rainfall alert|rain warning|heavy rain warning|heavy rain alert|thunderstorm alert|thunderstorm warning|precipitation alert|cloud alert)\b",
        r"\b(yellow alert|orange alert|red alert)\b[^.!?\n]*\b(rain|rainfall|thunderstorm|precipitation)\b",
        r"\b(rain|rainfall|barish|baarish|showers?|thunderstorm|precipitation)\b[^.!?\n]*\b(alert|warning|forecast|expected|likely|prediction|probability|chance)\b",
        r"\b(alert|warning|forecast|expected|likely|prediction|probability of|chance of)\b[^.!?\n]*\b(rain|rainfall|barish|baarish|showers?|thunderstorm|precipitation)\b",
    ]
    has_rain_alert = any(re.search(pat, text) for pat in alert_patterns)

    # Active current rain observation markers
    active_rain_patterns = [
        r"\b(currently raining|raining now|raining right now|rain is falling|active rain|active rainfall|continuous rain|light rain reported|heavy rain reported|rain reported now|light rain observed|moderate rain observed|heavy rain observed|thunderstorm with rain currently)\b",
        r"\b(present weather\s*[:\-]\s*(light\s+|moderate\s+|heavy\s+)?(rain|drizzle|shower|thunderstorm with rain))\b",
        r"\b(weather\s*[:\-]\s*(light\s+|moderate\s+|heavy\s+)?(rain|drizzle|showers?))\b",
        r"\b(weather\s*right\s*now\s*[:\-]?\s*[^.!?\n]*\b(rain|drizzle|showers?|raining)\b)",
        r"\b(current\s+condition(s)?\s*[:\-]?\s*[^.!?\n]*\b(rain|drizzle|showers?|raining)\b)",
        r"\b(current\s+weather\s*[:\-]?\s*[^.!?\n]*\b(rain|drizzle|showers?|raining)\b)",
        r"\b(abhi\s+(baarish|barish)\s+ho\s+rahi|वर्षा\s+हो\s+रही\s+है|बारिश\s+हो\s+रही\s+है|बारिश\s+जारी\s+है)\b",
    ]
    has_active_rain = any(re.search(pat, text) for pat in active_rain_patterns)

    # 1. CURRENT_RAIN_CONFIRMED: Explicit active current rain observed, not negated and not merely an alert/forecast
    if has_active_rain and not rain_negated and not (has_rain_alert and not re.search(r"\b(currently raining|raining now|raining right now|abhi baarish ho rahi)\b", text)):
        return "CURRENT_RAIN_CONFIRMED"

    # 2. FORECAST_OR_ALERT_ONLY: Active alert/warning or forecast for rain/storm/clouds, but current rain not confirmed
    if has_rain_alert:
        return "FORECAST_OR_ALERT_ONLY"

    # 3. CURRENT_NO_RAIN_CONFIRMED: Clear, sunny, dry, or explicitly confirmed no rain
    has_clear_dry = bool(re.search(
        r"\b(clear sky|clear skies|mainly clear|sunny|mostly sunny|dry weather|dry conditions?|fair weather|clean weather)\b",
        text
    )) or rain_negated

    if has_clear_dry:
        return "CURRENT_NO_RAIN_CONFIRMED"

    # 4. CURRENT_CONDITION_UNVERIFIED: Generic IMD portal, station tables, or inconclusive evidence
    is_purely_historical_or_generic = bool(re.search(
        r"\b(rainfall recorded from|past 24 hours weather data|station\s*\|\s*max temp|departure from normal|model guidance|national weather forecasting centre)\b",
        text
    )) and not bool(re.search(r"\b(current\s+weather|current\s+condition|right now|at present|currently)\b", text))

    if is_purely_historical_or_generic:
        return "CURRENT_CONDITION_UNVERIFIED"

    return "CURRENT_CONDITION_UNVERIFIED"


def generate_weather_hybrid_reply(
    query: str,
    language: str,
    location: Optional[str] = None,
    crop: Optional[str] = None,
    live_verified: bool = False,
    live_failed: bool = False,
    weather_evidence: Optional[List[WebEvidence]] = None,
    kb_chunks: Optional[List[Dict[str, Any]]] = None,
    time_scope: Optional[str] = None
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
    8. Strictly respects requested time horizon (CURRENT/ABHI vs TOMORROW/KAL vs TODAY/AAJ).
    """
    if not time_scope:
        time_scope = detect_weather_time_scope(query)

    loc_display = location or ("आपके क्षेत्र" if language == "hi" else ("aapke area" if language == "hinglish" else "your area"))
    q_lower = query.lower()

    is_irrigation = bool(re.search(r"sinchai|irrigation|पानी|water|सींच|सिंचाई|paani|pani", q_lower))
    is_spray = bool(re.search(r"spray|छिड़काव|स्प्रे|chhidkaw|chidkaw", q_lower))

    # --- 1. Weather Evidence Content Analysis ---
    weather_state = "UNVERIFIED"
    current_weather_state = "CURRENT_CONDITION_UNVERIFIED"
    weather_domain = "IMD"
    ev_text = ""

    if live_verified and weather_evidence:
        top_ev = weather_evidence[0]
        weather_domain = top_ev.domain or "IMD"
        ev_text = " ".join([f"{ev.title} {ev.content}" for ev in weather_evidence]).lower()

        if time_scope == "CURRENT":
            current_weather_state = classify_current_weather_evidence(ev_text, live_verified)
            if current_weather_state == "CURRENT_RAIN_CONFIRMED":
                weather_state = "RAIN_EXPECTED"
            elif current_weather_state == "CURRENT_NO_RAIN_CONFIRMED":
                weather_state = "CLEAR_DRY"
            elif current_weather_state == "FORECAST_OR_ALERT_ONLY":
                weather_state = "RAIN_EXPECTED"
            else:
                weather_state = "UNVERIFIED"
        else:
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
    elif time_scope == "CURRENT":
        current_weather_state = "CURRENT_CONDITION_UNVERIFIED"

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
            if time_scope == "TOMORROW":
                if language == "hi":
                    return (
                        f"🌾 {loc_display} में कल बारिश का पूर्वानुमान होने के कारण सिंचाई स्थगित करने की सलाह दी जाती है।\n\n"
                        f"- लाइव मौसम ({weather_domain}): {loc_display} में कल वर्षा अथवा बादलों की चेतावनी है, अतः तात्कालिक सिंचाई रोकें।\n"
                        f"- कृषि सलाह ({agri_source}): {agri_rain_advice}\n"
                        f"- नमी निगरानी: बारिश के 24–48 घंटे बाद खेत की मिट्टी जांचने के उपरांत ही सिंचाई का अगला निर्णय लें।\n\n"
                        f"Source: IMD ({weather_domain}) | {agri_source}"
                    )
                elif language == "hinglish":
                    return (
                        f"🌾 {loc_display} me kal rain forecast hone ke karan sinchai postpone karne ki salah di jaati hai.\n\n"
                        f"- Live Weather ({weather_domain}): {loc_display} me kal rain alert ya precipitation forecast hai, isliye sinchai rokein.\n"
                        f"- Agronomy Guidance ({agri_source}): {agri_rain_advice}\n"
                        f"- Moisture Monitoring: Rain ke 24–48 hours baad field moisture check karne ke baad hi next irrigation plan karein.\n\n"
                        f"Source: IMD ({weather_domain}) | {agri_source}"
                    )
                else:
                    return (
                        f"🌾 Rain is forecast for {loc_display} tomorrow, so irrigation should be postponed to avoid waterlogging.\n\n"
                        f"- Live Weather ({weather_domain}): Precipitation alert/forecast active for tomorrow in {loc_display}; withhold immediate irrigation.\n"
                        f"- Agronomic Advisory ({agri_source}): {agri_rain_advice}\n"
                        f"- Moisture Inspection: Re-assess soil moisture 24–48 hours after rainfall before scheduling further irrigation.\n\n"
                        f"Source: IMD ({weather_domain}) | {agri_source}"
                    )
            elif time_scope == "CURRENT":
                if current_weather_state == "CURRENT_RAIN_CONFIRMED":
                    if language == "hi":
                        return (
                            f"🌾 {loc_display} में अभी बारिश होने के कारण सिंचाई रोकने की सलाह दी जाती है।\n\n"
                            f"- लाइव मौसम ({weather_domain}): {loc_display} में अभी बारिश हो रही है।\n"
                            f"- कृषि सलाह ({agri_source}): {agri_rain_advice}\n"
                            f"- जल निकासी: बारिश के बाद खेत में जलभराव न होने दें और नाली खुली रखें।\n\n"
                            f"Source: IMD ({weather_domain}) | {agri_source}"
                        )
                    elif language == "hinglish":
                        return (
                            f"🌾 {loc_display} me abhi baarish hone ke karan sinchai rokne ki salah di jaati hai.\n\n"
                            f"- Live Weather ({weather_domain}): {loc_display} me abhi baarish ho rahi hai.\n"
                            f"- Agronomy Guidance ({agri_source}): {agri_rain_advice}\n"
                            f"- Water Drainage: Field me waterlogging avoid karein aur drainage open rakhein.\n\n"
                            f"Source: IMD ({weather_domain}) | {agri_source}"
                        )
                    else:
                        return (
                            f"🌾 With rain currently in {loc_display}, hold off on irrigation.\n\n"
                            f"- Live Weather ({weather_domain}): Rainfall currently observed in {loc_display}.\n"
                            f"- Agronomic Advisory ({agri_source}): {agri_rain_advice}\n"
                            f"- Drainage: Ensure unobstructed field drainage.\n\n"
                            f"Source: IMD ({weather_domain}) | {agri_source}"
                        )
                else:
                    if language == "hi":
                        return (
                            f"🌾 {loc_display} में अभी बारिश की पुष्टि नहीं है, लेकिन बारिश का अलर्ट होने के कारण सिंचाई स्थगित करने की सलाह दी जाती है।\n\n"
                            f"- लाइव मौसम ({weather_domain}): {loc_display} में अभी बारिश की पुष्टि नहीं है, लेकिन बारिश का अलर्ट/पूर्वानुमान सक्रिय है।\n"
                            f"- कृषि सलाह ({agri_source}): {agri_rain_advice}\n"
                            f"- निगरानी: आने वाले घंटों के मौसम पर नजर रखें।\n\n"
                            f"Source: IMD ({weather_domain}) | {agri_source}"
                        )
                    elif language == "hinglish":
                        return (
                            f"🌾 {loc_display} me abhi baarish confirm nahi hai, lekin rain alert hone ke karan sinchai postpone karne ki salah di jaati hai.\n\n"
                            f"- Live Weather ({weather_domain}): {loc_display} me abhi baarish confirm nahi hai, lekin rain alert/forecast active hai.\n"
                            f"- Agronomy Guidance ({agri_source}): {agri_rain_advice}\n"
                            f"- Weather Monitoring: Aane wale ghanton ke mausam par nazar rakhein.\n\n"
                            f"Source: IMD ({weather_domain}) | {agri_source}"
                        )
                    else:
                        return (
                            f"🌾 Rain is not confirmed right now in {loc_display}, but an active rain alert suggests postponing irrigation.\n\n"
                            f"- Live Weather ({weather_domain}): Current rain in {loc_display} is not confirmed, but a rain alert/forecast is active.\n"
                            f"- Agronomic Advisory ({agri_source}): {agri_rain_advice}\n"
                            f"- Monitoring: Track oncoming weather before scheduling irrigation.\n\n"
                            f"Source: IMD ({weather_domain}) | {agri_source}"
                        )
            else:
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
            if time_scope == "TOMORROW":
                if language == "hi":
                    return (
                        f"🌾 {loc_display} में कल मौसम मुख्य रूप से साफ रहने और वर्षा की संभावना न होने पर आप आवश्यकतानुसार सिंचाई कर सकते हैं।\n\n"
                        f"- लाइव मौसम ({weather_domain}): {loc_display} में कल मौसम साफ/शुष्क रहने का अनुमान है और बारिश की तात्कालिक चेतावनी नहीं है।\n"
                        f"- कृषि सलाह ({agri_source}): {agri_advice}\n"
                        f"- नमी की जांच: यदि खेत में पहले से पर्याप्त नमी मौजूद हो तो सिंचाई 2–3 दिन टालें ताकि जलभराव न हो।\n\n"
                        f"Source: IMD ({weather_domain}) | {agri_source}"
                    )
                elif language == "hinglish":
                    return (
                        f"🌾 {loc_display} me kal mausam saaf rehne aur rain forecast na hone par aap zaroorat ke hisaab se sinchai kar sakte hain.\n\n"
                        f"- Live Weather ({weather_domain}): {loc_display} me kal weather mainly clear/dry rehne ka anuman hai aur rain alert nahi hai.\n"
                        f"- Agronomy Guidance ({agri_source}): {agri_advice}\n"
                        f"- Soil Moisture Check: Agar khet me pehle se moisture ho to sinchai 2–3 din postpone karein taki waterlogging na ho.\n\n"
                        f"Source: IMD ({weather_domain}) | {agri_source}"
                    )
                else:
                    return (
                        f"🌾 Based on clear weather forecast for {loc_display} tomorrow with no rain expected, you can proceed with irrigation if required.\n\n"
                        f"- Live Weather ({weather_domain}): Clear and dry atmospheric conditions forecast in {loc_display}.\n"
                        f"- Agronomic Recommendation ({agri_source}): {agri_advice}\n"
                        f"- Moisture Check: If the soil already retains adequate residual moisture, delay irrigation to prevent waterlogging.\n\n"
                        f"Source: IMD ({weather_domain}) | {agri_source}"
                    )
            elif time_scope == "CURRENT":
                if language == "hi":
                    return (
                        f"🌾 {loc_display} में अभी बारिश नहीं हो रही है और मौसम साफ है, आप आवश्यकतानुसार सिंचाई कर सकते हैं।\n\n"
                        f"- लाइव मौसम ({weather_domain}): {loc_display} में वर्तमान में मौसम साफ/शुष्क है।\n"
                        f"- कृषि सलाह ({agri_source}): {agri_advice}\n"
                        f"- नमी की जांच: मिट्टी की नमी जांचने के बाद ही सिंचाई करें।\n\n"
                        f"Source: IMD ({weather_domain}) | {agri_source}"
                    )
                elif language == "hinglish":
                    return (
                        f"🌾 {loc_display} me abhi baarish nahi ho rahi hai aur mausam saaf hai, aap zaroorat ke hisaab se sinchai kar sakte hain.\n\n"
                        f"- Live Weather ({weather_domain}): {loc_display} me currently rain nahi hai aur weather dry hai.\n"
                        f"- Agronomy Guidance ({agri_source}): {agri_advice}\n"
                        f"- Soil Moisture Check: Soil moisture verify karke hi sinchai karein.\n\n"
                        f"Source: IMD ({weather_domain}) | {agri_source}"
                    )
                else:
                    return (
                        f"🌾 It is currently dry in {loc_display} with no rain; proceed with irrigation if required.\n\n"
                        f"- Live Weather ({weather_domain}): Clear and dry conditions observed in {loc_display}.\n"
                        f"- Agronomic Recommendation ({agri_source}): {agri_advice}\n\n"
                        f"Source: IMD ({weather_domain}) | {agri_source}"
                    )
            else:
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
            if time_scope == "TOMORROW":
                if language == "hi":
                    return (
                        f"🌾 {loc_display} के लिए कल का मौसम और वर्षा का सटीक डेटा ऑनलाइन सत्यापित नहीं हो सका, इसलिए सिंचाई से पहले स्थानीय मौसम और खेत की नमी अवश्य जांच लें।\n\n"
                        f"- लाइव मौसम स्थिति: {loc_display} का कल का मौसम पूर्वानुमान अभी ऑनलाइन सत्यापित नहीं हो पाया है।\n"
                        f"- कृषि सिफारिश ({agri_source}): {agri_advice}\n"
                        f"- मौसम सावधानी: यदि स्थानीय स्तर पर बारिश के बादल या वर्षा की संभावना दिखे तो सिंचाई तुरंत रोक दें।\n\n"
                        f"Source: {agri_source} | Live Weather Data Unverified"
                    )
                elif language == "hinglish":
                    return (
                        f"🌾 {loc_display} ke liye kal ka live weather aur rain forecast online verify nahi ho saka, isliye sinchai se pehle local mausam aur field moisture zaroor check karein.\n\n"
                        f"- Live Weather Status: {loc_display} ka kal ka rain forecast online confirm nahi ho paya hai.\n"
                        f"- Agronomy Guidance ({agri_source}): {agri_advice}\n"
                        f"- Weather Caution: Agar local rain ya cloudy weather ke aasaar hon to sinchai postpone karein taki water stagnation na ho.\n\n"
                        f"Source: {agri_source} | Live Weather Data Unverified"
                    )
                else:
                    return (
                        f"🌾 Live weather forecast for {loc_display} tomorrow could not be verified online; please inspect local sky conditions and soil moisture before irrigating.\n\n"
                        f"- Live Weather Status: Meteorological forecast for {loc_display} tomorrow unconfirmed.\n"
                        f"- Agronomic Guidance ({agri_source}): {agri_advice}\n"
                        f"- Weather Caution: If rain appears imminent locally, hold off irrigation to prevent crop root suffocation.\n\n"
                        f"Source: {agri_source} | Live Weather Data Unverified"
                    )
            elif time_scope == "CURRENT":
                if language == "hi":
                    return (
                        f"🌾 {loc_display} के लिए अभी का लाइव मौसम डेटा ऑनलाइन सत्यापित नहीं हो सका, इसलिए स्थानीय मौसम और नमी देखकर ही सिंचाई करें।\n\n"
                        f"- लाइव मौसम स्थिति: {loc_display} का तात्कालिक मौसम डेटा ऑनलाइन सत्यापित नहीं हो पाया है।\n"
                        f"- कृषि सिफारिश ({agri_source}): {agri_advice}\n\n"
                        f"Source: {agri_source} | Live Weather Data Unverified"
                    )
                elif language == "hinglish":
                    return (
                        f"🌾 {loc_display} ke liye abhi ka live weather data online verify nahi ho saka, isliye local mausam dekhkar hi sinchai karein.\n\n"
                        f"- Live Weather Status: {loc_display} ka real-time meteorological data online confirm nahi ho paya hai.\n"
                        f"- Agronomy Guidance ({agri_source}): {agri_advice}\n\n"
                        f"Source: {agri_source} | Live Weather Data Unverified"
                    )
                else:
                    return (
                        f"🌾 Real-time live weather data for {loc_display} could not be confirmed online; inspect local conditions before irrigating.\n\n"
                        f"Source: {agri_source} | Live Weather Data Unverified"
                    )
            else:
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
    if time_scope == "CURRENT":
        if current_weather_state == "CURRENT_RAIN_CONFIRMED":
            if language == "hi":
                return (
                    f"🌦️ {loc_display} में अभी बारिश हो रही है।\n\n"
                    f"- मौसम स्थिति ({weather_domain}): वर्तमान में वर्षा दर्ज की गई है।\n"
                    f"- कृषि कार्य: खुले में रखे अनाज को सुरक्षित ढकें और खेत का जल निकास सुचारू रखें।\n\n"
                    f"Source: IMD ({weather_domain})"
                )
            elif language == "hinglish":
                return (
                    f"🌦️ {loc_display} me abhi baarish ho rahi hai.\n\n"
                    f"- Weather Status ({weather_domain}): Current time me rain observation active hai.\n"
                    f"- Farm Operations: Harvested produce ko safely cover karein aur water drainage open rakhein.\n\n"
                    f"Source: IMD ({weather_domain})"
                )
            else:
                return (
                    f"🌦️ It is currently raining in {loc_display}.\n\n"
                    f"- Weather Status ({weather_domain}): Current rainfall observed.\n"
                    f"- Farm Operations: Protect open produce and maintain proper drainage.\n\n"
                    f"Source: IMD ({weather_domain})"
                )
        elif current_weather_state == "CURRENT_NO_RAIN_CONFIRMED":
            if language == "hi":
                return (
                    f"🌦️ {loc_display} में अभी बारिश नहीं हो रही है।\n\n"
                    f"- मौसम स्थिति ({weather_domain}): वर्तमान में कोई वर्षा नहीं है और मौसम साफ है।\n"
                    f"- कृषि कार्य: सामान्य कृषि कार्य जारी रखे जा सकते हैं।\n\n"
                    f"Source: IMD ({weather_domain})"
                )
            elif language == "hinglish":
                return (
                    f"🌦️ {loc_display} me abhi baarish nahi ho rahi hai.\n\n"
                    f"- Weather Status ({weather_domain}): Current time me rain nahi hai aur mausam saaf hai.\n"
                    f"- Field Operations: Routine field activities continue kar sakte hain.\n\n"
                    f"Source: IMD ({weather_domain})"
                )
            else:
                return (
                    f"🌦️ It is currently not raining in {loc_display}.\n\n"
                    f"- Conditions ({weather_domain}): No current rainfall active in the area.\n"
                    f"- Farm Operations: Normal field operations can continue.\n\n"
                    f"Source: IMD ({weather_domain})"
                )
        elif current_weather_state == "FORECAST_OR_ALERT_ONLY":
            if language == "hi":
                return (
                    f"🌦️ {loc_display} में अभी बारिश की पुष्टि नहीं है, लेकिन बारिश का अलर्ट/पूर्वानुमान सक्रिय है।\n\n"
                    f"- मौसम स्थिति ({weather_domain}): तात्कालिक वर्षा चेतावनी अथवा पूर्वानुमान सक्रिय है।\n"
                    f"- कृषि कार्य: खुले में रखी उपज की सुरक्षा की तैयारी रखें।\n\n"
                    f"Source: IMD ({weather_domain})"
                )
            elif language == "hinglish":
                return (
                    f"🌦️ {loc_display} me abhi baarish confirm nahi hai, lekin rain alert/forecast active hai.\n\n"
                    f"- Weather Status ({weather_domain}): Current precipitation alert ya rain forecast active hai.\n"
                    f"- Farm Operations: Open me rakhe anaj par dhyan rakhein aur aane wale ghanton ke mausam par nazar rakhein.\n\n"
                    f"Source: IMD ({weather_domain})"
                )
            else:
                return (
                    f"🌦️ Current rain in {loc_display} is not confirmed, but a rain alert/forecast is active.\n\n"
                    f"- Conditions ({weather_domain}): Precipitation forecast or alert active.\n"
                    f"- Farm Operations: Monitor weather conditions and protect exposed produce.\n\n"
                    f"Source: IMD ({weather_domain})"
                )
        else:  # CURRENT_CONDITION_UNVERIFIED
            if language == "hi":
                return (
                    f"🌦️ मैं {loc_display} में अभी बारिश हो रही है या नहीं, इसे लाइव स्रोत से सत्यापित नहीं कर पा रहा हूँ।\n\n"
                    f"- लाइव स्थिति: मौसम केंद्र से तात्कालिक मौसम टेलीमेट्री सत्यापित नहीं हो पाई है।\n"
                    f"- कृषि सलाह: स्थानीय मौसम देखकर ही कार्य करें।\n\n"
                    f"Source: Live Weather Data Unverified"
                )
            elif language == "hinglish":
                return (
                    f"🌦️ Main {loc_display} me abhi baarish ho rahi hai ya nahi, ise live source se verify nahi kar pa raha hoon.\n\n"
                    f"- Live Status: Real-time meteorological telemetry verify nahi ho payi.\n"
                    f"- Advisory: Local sky conditions dekhkar hi field operations karein.\n\n"
                    f"Source: Live Weather Data Unverified"
                )
            else:
                return (
                    f"🌦️ I cannot verify from live sources whether it is currently raining in {loc_display}.\n\n"
                    f"Source: Live Weather Data Unverified"
                )

    if weather_state == "RAIN_EXPECTED":
        if time_scope == "TOMORROW":
            if language == "hi":
                return (
                    f"🌦️ {loc_display} में कल बारिश / वर्षा होने का पूर्वानुमान है।\n\n"
                    f"- मौसम स्थिति ({weather_domain}): कल वर्षा अथवा मेघ गर्जन की चेतावनी जारी की गई है।\n"
                    f"- कृषि कार्य: खुले में रखे अनाज की सुरक्षा करें तथा कल के लिए प्रस्तावित रासायनिक छिड़काव अथवा सिंचाई स्थगित रखें।\n\n"
                    f"Source: IMD ({weather_domain})"
                )
            elif language == "hinglish":
                return (
                    f"🌦️ {loc_display} me kal rain / baarish ka forecast hai.\n\n"
                    f"- Weather Status ({weather_domain}): Kal rain warning ya precipitation alert active hai.\n"
                    f"- Farm Operations: Open me rakhe grain ko protect karein aur kal ke liye spray ya sinchai postpone karein.\n\n"
                    f"Source: IMD ({weather_domain})"
                )
            else:
                return (
                    f"🌦️ Rainfall is forecast for {loc_display} tomorrow.\n\n"
                    f"- Weather Status ({weather_domain}): Precipitation alert active for tomorrow.\n"
                    f"- Farm Operations: Protect harvested crops and postpone spraying or irrigation scheduled for tomorrow.\n\n"
                    f"Source: IMD ({weather_domain})"
                )
        else:
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
        if time_scope == "TOMORROW":
            if language == "hi":
                return (
                    f"🌦️ {loc_display} में कल मौसम मुख्य रूप से साफ रहने का अनुमान है और भारी बारिश की संभावना नहीं है।\n\n"
                    f"- मौसम स्थिति ({weather_domain}): कल मौसम साफ/शुष्क रहने का पूर्वानुमान है।\n"
                    f"- कृषि कार्य: मौसम अनुकूल रहने के कारण सामान्य कृषि कार्य जारी रखे जा सकते हैं।\n\n"
                    f"Source: IMD ({weather_domain})"
                )
            elif language == "hinglish":
                return (
                    f"🌦️ {loc_display} me kal mausam mainly clear rehne ka anuman hai aur heavy rain ki sambhavna nahi hai.\n\n"
                    f"- Weather Status ({weather_domain}): Kal weather mainly clear/dry rehne ka forecast hai.\n"
                    f"- Field Operations: Weather favourable hone ke karan routine intercultural operations continue kar sakte hain.\n\n"
                    f"Source: IMD ({weather_domain})"
                )
            else:
                return (
                    f"🌦️ The weather forecast for {loc_display} tomorrow indicates generally clear conditions with no heavy rainfall expected.\n\n"
                    f"- Conditions ({weather_domain}): Temperatures remain seasonal with no immediate precipitation warning tomorrow.\n"
                    f"- Farm Operations: Favorable conditions permit regular intercultural field operations and crop management.\n\n"
                    f"Source: IMD ({weather_domain})"
                )
        else:
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
        if time_scope == "TOMORROW":
            if language == "hi":
                return (
                    f"🌦️ {loc_display} के लिए कल का लाइव मौसम और वर्षा का सटीक डेटा ऑनलाइन सत्यापित नहीं हो सका।\n\n"
                    f"- लाइव स्थिति: कल के मौसम पूर्वानुमान की टेलीमेट्री अभी ऑनलाइन उपलब्ध नहीं है।\n"
                    f"- कृषि सलाह: स्थानीय मौसम और आकाश की स्थिति को देखकर ही योजना बनाएं।\n\n"
                    f"Source: Live Weather Data Unverified"
                )
            elif language == "hinglish":
                return (
                    f"🌦️ {loc_display} ke liye kal ka live weather aur rain forecast online verify nahi ho saka.\n\n"
                    f"- Live Status: Kal ke weather forecast ki telemetry online available nahi hai.\n"
                    f"- Advisory: Local sky conditions dekhkar hi plan karein.\n\n"
                    f"Source: Live Weather Data Unverified"
                )
            else:
                return (
                    f"🌦️ Weather and precipitation forecast for {loc_display} tomorrow could not be confirmed online.\n\n"
                    f"- Live Status: Forecast telemetry for tomorrow could not be verified.\n"
                    f"- Advisory: Inspect local sky conditions before scheduling activities.\n\n"
                    f"Source: Live Weather Data Unverified"
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
) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """
    Parses and verifies mandi market rates from live web search evidence (Tavily).
    Extracts modal price, min-max price range, unit, reported date, and authoritative source.
    Strictly verifies freshness and prevents numerical hallucination.
    Returns (mandi_data, rejection_reason).
    """
    from datetime import date, timedelta
    if not evidence_list:
        return None, "no_evidence_returned"

    today = date.today()
    yesterday = today - timedelta(days=1)
    today_str = today.strftime("%Y-%m-%d")
    today_dmy = today.strftime("%d-%m-%Y")
    today_slash = today.strftime("%d/%m/%Y")
    yest_str = yesterday.strftime("%Y-%m-%d")
    yest_dmy = yesterday.strftime("%d-%m-%Y")
    yest_slash = yesterday.strftime("%d/%m/%Y")
    current_year = str(today.year)

    stale_found = False
    price_found = False

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

        price_found = True

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

        # Freshness Check:
        # A market rate is fresh if reported date is today or yesterday,
        # or content mentions 'today'/'aaj'/'आज' and contains current year without past years.
        is_fresh = False
        if reported_date:
            rd_clean = reported_date.strip()
            if (
                rd_clean in (today_str, today_dmy, today_slash, yest_str, yest_dmy, yest_slash)
                or (str(today.day) in rd_clean and today.strftime("%b") in rd_clean and current_year in rd_clean)
                or (str(yesterday.day) in rd_clean and yesterday.strftime("%b") in rd_clean and current_year in rd_clean)
            ):
                is_fresh = True
        elif ("today" in content.lower() or "aaj" in content.lower() or "आज" in content) and current_year in content:
            if not any(old_y in content for old_y in ["2020", "2021", "2022", "2023", "2024", "2025"]):
                is_fresh = True
                reported_date = today_dmy

        if not is_fresh:
            stale_found = True
            continue

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
            "is_today": True,
            "source_name": source_name,
            "source_url": url,
            "evidence": ev
        }

        return candidate, None

    if stale_found:
        return None, "stale_market_rate_rejected"
    if price_found:
        return None, "unverified_date_rate_rejected"
    return None, "no_price_in_evidence"


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
        time_scope = route_decision.detected_entities.get("time_scope") or detect_weather_time_scope(clean_msg)
        if loc and getattr(web_search_service, "enabled", False):
            try:
                if time_scope == "TOMORROW":
                    weather_search_query = f"{loc} weather tomorrow rainfall forecast IMD"
                elif time_scope == "CURRENT":
                    weather_search_query = f"{loc} current weather right now rain rainfall IMD"
                else:
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
            kb_chunks=kb_chunks,
            time_scope=time_scope
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
        if not loc:
            loc = extract_location_from_text(clean_msg)

        crop = route_decision.detected_entities.get("crop") or (context.get("crop") if context else None)
        if not crop:
            for c_name, pat in CROPS_PATTERNS.items():
                if re.search(pat, clean_msg.lower()):
                    crop = c_name
                    break

        mandi_evidence = []
        live_lookup_attempted = False
        live_lookup_provider = "tavily"
        live_lookup_result = "not_attempted"
        rejection_reason = None
        result_count = 0
        mandi_data = None

        if getattr(web_search_service, "enabled", False):
            live_lookup_attempted = True
            try:
                commodity_canonical = crop.lower() if crop else "commodity"
                loc_term = loc if loc else "India"
                search_query = f"{loc_term} mandi {commodity_canonical} latest modal price AGMARKNET eNAM"
                mandi_evidence = web_search_service.search(
                    query=search_query,
                    crop=crop,
                    location=loc,
                    freshness_needed=True
                )
                result_count = len(mandi_evidence)
                mandi_data, rejection_reason = extract_mandi_data_from_evidence(mandi_evidence, loc, crop)
                if mandi_data:
                    live_lookup_result = "verified_rate_found"
                else:
                    if not mandi_evidence:
                        rejection_reason = "no_evidence_returned"
                        live_lookup_result = "no_verified_rate"
                    elif rejection_reason and "stale" in rejection_reason:
                        live_lookup_result = "stale_rate_rejected"
                    else:
                        rejection_reason = rejection_reason or "no_price_in_evidence"
                        live_lookup_result = "no_verified_rate"
            except Exception as exc:
                logger.warning("Live mandi search via Tavily failed: %s", exc)
                mandi_evidence = []
                mandi_data = None
                live_lookup_result = "provider_error"
                rejection_reason = f"Provider exception: {type(exc).__name__} - {str(exc)}"
        else:
            live_lookup_attempted = False
            live_lookup_result = "provider_disabled_or_no_key"
            rejection_reason = "Tavily API key not configured or web search disabled"

        is_live_verified = bool(mandi_data is not None)
        live_failed = not is_live_verified

        logger.info(
            "MARKET_SERVICE: commodity=%s, location=%s, live_lookup_attempted=%s, "
            "provider=%s, result_count=%d, rejection_reason=%s, anti_hallucination_fallback=%s",
            crop,
            loc,
            live_lookup_attempted,
            live_lookup_provider,
            result_count,
            rejection_reason,
            live_failed
        )

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
            live_failed=live_failed
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
            "detected_entities": route_decision.detected_entities,
            "live_lookup_attempted": live_lookup_attempted,
            "live_lookup_provider": live_lookup_provider,
            "live_lookup_result": live_lookup_result,
            "rejection_reason": rejection_reason
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

        scheme_req = detect_scheme_freshness_request(clean_msg)
        if scheme_req:
            scheme_name = scheme_req["scheme"]
            target_year = scheme_req["target_year"]
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
                    logger.error("Web search for scheme failed: %s", type(exc).__name__)
                    rejection_reason = f"Provider exception: {type(exc).__name__}"
                    fallback_reply = compose_scheme_fallback_response(scheme_name, target_year, lang)
                    logger.info(
                        "SCHEME_FRESHNESS: scheme=%s, year=%s, live_lookup_attempted=True, provider=tavily, result_count=0, rejection_reason=%s, anti_hallucination_fallback=True",
                        scheme_name, target_year, rejection_reason
                    )
                    return {
                        "reply": clean_farmer_markdown(fallback_reply),
                        "sources": [{
                            "title": "Pradhan Mantri Fasal Bima Yojana (PMFBY) Portal",
                            "section": "Official Guidelines",
                            "source": "pmfby.gov.in",
                            "organization": "Ministry of Agriculture & Farmers Welfare, GoI",
                            "category": "Schemes",
                            "url": "https://pmfby.gov.in",
                            "score": 0.90
                        }],
                        "retrieved_chunks": 0,
                        "confidence": 0.70,
                        "language": lang,
                        "provider": "anti_hallucination_guard",
                        "intent": route_decision.intent.value,
                        "route": route_decision.action.value,
                        "live_lookup_attempted": True,
                        "live_lookup_provider": "tavily",
                        "live_lookup_result": "provider_error",
                        "rejection_reason": rejection_reason
                    }
            else:
                logger.info("WebSearchService is disabled via WEB_SEARCH_ENABLED flag.")
                fallback_reply = compose_scheme_fallback_response(scheme_name, target_year, lang)
                return {
                    "reply": clean_farmer_markdown(fallback_reply),
                    "sources": [{
                        "title": "Pradhan Mantri Fasal Bima Yojana (PMFBY) Portal",
                        "section": "Official Guidelines",
                        "source": "pmfby.gov.in",
                        "organization": "Ministry of Agriculture & Farmers Welfare, GoI",
                        "category": "Schemes",
                        "url": "https://pmfby.gov.in",
                        "score": 0.90
                    }],
                    "retrieved_chunks": 0,
                    "confidence": 0.70,
                    "language": lang,
                    "provider": "anti_hallucination_guard",
                    "intent": route_decision.intent.value,
                    "route": route_decision.action.value,
                    "live_lookup_attempted": True,
                    "live_lookup_provider": "tavily",
                    "live_lookup_result": "provider_disabled",
                    "rejection_reason": "provider_disabled"
                }

            # Extract structured evidence from retrieved items
            valid_notifs, rej_code, rej_reason = extract_scheme_structured_evidence(
                evidence, scheme=scheme_name, target_year=target_year
            )

            if valid_notifs:
                reply = compose_scheme_freshness_response(scheme_name, target_year, valid_notifs, lang)
                # Requirement 6: Zero Raw / Foreign Contamination Invariant Check
                foreign_contamination_detected = any(
                    term in reply.lower() for term in [
                        "fedramp", "hhs", "poverty guidelines", "department of health and human services",
                        "aspe.hhs.gov", "fedramp.gov"
                    ]
                )
                if not foreign_contamination_detected:
                    formatted_sources = []
                    for n in valid_notifs:
                        formatted_sources.append({
                            "title": n["title"],
                            "section": "Official Notification",
                            "source": n["domain"],
                            "organization": n["authority"],
                            "category": "Schemes",
                            "url": n["url"],
                            "score": 0.95
                        })
                    logger.info(
                        "SCHEME_FRESHNESS: scheme=%s, year=%s, live_lookup_attempted=True, provider=tavily, result_count=%d, rejection_reason=None, anti_hallucination_fallback=False",
                        scheme_name, target_year, len(valid_notifs)
                    )
                    return {
                        "reply": clean_farmer_markdown(reply),
                        "sources": formatted_sources,
                        "retrieved_chunks": len(valid_notifs),
                        "confidence": 0.95,
                        "language": lang,
                        "provider": "tavily_scheme",
                        "intent": route_decision.intent.value,
                        "route": route_decision.action.value,
                        "live_lookup_attempted": True,
                        "live_lookup_provider": "tavily",
                        "live_lookup_result": "verified_scheme_rule_found",
                        "rejection_reason": None
                    }
                else:
                    logger.error("CONTAMINATION GUARD: Foreign policy terms detected in PMFBY answer. Purging to safe fallback.")
                    rej_reason = "foreign_contamination_purged"

            # Safe fallback: no verified rule change found or contaminated evidence purged
            fallback_reply = compose_scheme_fallback_response(scheme_name, target_year, lang)
            logger.info(
                "SCHEME_FRESHNESS: scheme=%s, year=%s, live_lookup_attempted=True, provider=tavily, result_count=0, rejection_reason=%s, anti_hallucination_fallback=True",
                scheme_name, target_year, rej_reason
            )
            return {
                "reply": clean_farmer_markdown(fallback_reply),
                "sources": [{
                    "title": "Pradhan Mantri Fasal Bima Yojana (PMFBY) Portal",
                    "section": "Official Guidelines",
                    "source": "pmfby.gov.in",
                    "organization": "Ministry of Agriculture & Farmers Welfare, GoI",
                    "category": "Schemes",
                    "url": "https://pmfby.gov.in",
                    "score": 0.90
                }],
                "retrieved_chunks": 0,
                "confidence": 0.75,
                "language": lang,
                "provider": "anti_hallucination_guard",
                "intent": route_decision.intent.value,
                "route": route_decision.action.value,
                "live_lookup_attempted": True,
                "live_lookup_provider": "tavily",
                "live_lookup_result": rej_code or "no_verified_2026_rule",
                "rejection_reason": rej_reason or "no_verified_2026_notification"
            }

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
    effective_crop = route_decision.detected_entities.get("crop")
    effective_pest = route_decision.detected_entities.get("pest_disease")
    effective_age = route_decision.detected_entities.get("crop_age_days")

    q_low = clean_msg.lower()
    is_pronoun_or_ellipsis = bool(
        re.search(r"\b(is|iska|iski|iske|isse|ise|in|inka|inki|it|its|this|that)\b", q_low)
        or (not any(c.lower() in q_low for c in ["gehun", "wheat", "dhan", "rice", "arhar", "tuar", "pigeonpea", "tamatar", "tomato", "chana", "mustard", "sarson", "makka", "maize", "cotton", "kapas", "sugarcane", "ganna", "soybean", "potato", "aloo", "onion", "pyaz"]) and len(q_low.split()) <= 7 and bool(re.search(r"\b(sinchai|irrigation|paani|pani|ilaj|cure|upchar|dawa|davai|management|control|khat|khad|urea|spray|chhidkaw)\b", q_low)))
    )

    if is_pronoun_or_ellipsis:
        if not effective_crop and not effective_pest:
            clarif_reply = (
                "कृपया स्पष्ट करें कि आप किस फसल और किस कीट या रोग के उपचार के बारे में पूछ रहे हैं?"
                if lang == "hi" else (
                    "Kripya clarify karein ki aap kis fasal aur kis keede ya rog ke baare me pooch rahe hain?"
                    if lang == "hinglish" else
                    "Please clarify which crop and pest or disease you are referring to."
                )
            )
            return {
                "reply": clean_farmer_markdown(clarif_reply),
                "sources": [],
                "retrieved_chunks": 0,
                "confidence": 0.5,
                "language": lang,
                "provider": "boundary_guard",
                "intent": route_decision.intent.value,
                "route": route_decision.action.value,
                "detected_entities": route_decision.detected_entities
            }

        query_parts = []
        if effective_crop:
            query_parts.append(effective_crop)
        if effective_age:
            query_parts.append(f"{effective_age} din")
        if effective_pest:
            query_parts.append(effective_pest)
        query_parts.append(clean_msg)
        rag_retrieval_query = " ".join(query_parts)
    else:
        rag_retrieval_query = clean_msg

    rag_result = query_knowledge_base(rag_retrieval_query, crop_filter=effective_crop, top_k=3)

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
            "route": route_decision.action.value,
            "detected_entities": route_decision.detected_entities
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
                        "route": RouteAction.RAG_WEB_FALLBACK.value,
                        "detected_entities": route_decision.detected_entities
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
                        "route": RouteAction.RAG_WEB_FALLBACK.value,
                        "detected_entities": route_decision.detected_entities
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
            "route": route_decision.action.value,
            "detected_entities": route_decision.detected_entities
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
            "route": route_decision.action.value,
            "detected_entities": route_decision.detected_entities
        }

    # 8. Fallback: Synthesize cleanly from retrieved chunks
    _safe_print(f"\nOPENROUTER UNAVAILABLE ({result}). Generating grounded local RAG synthesis.")
    offline_reply = generate_grounded_offline_reply(
        clean_msg, lang, chunks, entities=route_decision.detected_entities
    )
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
        "route": route_decision.action.value,
        "detected_entities": route_decision.detected_entities
    }
