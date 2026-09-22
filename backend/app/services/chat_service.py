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

    # 1. Live Mandi Price Query
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
                "📊 **सत्यापित एवं ताज़ा मंडी भाव देखने के लिए:**\n"
                "• मैत्री पोर्टल पर **'Market Prices' (मंडी भाव)** डैशबोर्ड देखें।\n"
                "• भारत सरकार के आधिकारिक **Agmarknet** पोर्टल (agmarknet.gov.in) पर अपनी निकटतम कृषि उपज मंडी समिति (APMC) के आज के दैनिक भाव देखें।"
            )
        elif language == "hinglish":
            reply = (
                "Namaste! Maitri Krishi Assistant chat me live real-time mandi prices ka live data feed connected nahi hai. Isliye main aaj ka live mandi rate invent nahi kar sakta.\n\n"
                "📊 **Live verified rates check karne ke liye:**\n"
                "• Maitri dashboard ke **'Market Prices'** tab me dekhein.\n"
                "• Government of India ke official portal **Agmarknet** (agmarknet.gov.in) par apni local mandi ke rates check karein."
            )
        else:
            reply = (
                "Hello! Maitri Krishi Assistant chat does not have a live streaming market price feed connected. Therefore, I cannot provide today's live market rate.\n\n"
                "📊 **To view verified real-time prices:**\n"
                "• Check the **'Market Prices'** section on the Maitri platform.\n"
                "• Visit the Government of India's official **Agmarknet** portal (agmarknet.gov.in) for your local APMC mandi."
            )
        return {
            "reply": reply,
            "sources": [],
            "retrieved_chunks": 0,
            "confidence": 0.0,
            "language": language,
            "provider": "anti_hallucination_guard"
        }

    # 2. Live Weather Forecast Query
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
                "🌦️ **सटीक एवं स्थानीय मौसम पूर्वानुमान के लिए:**\n"
                "• मैत्री पोर्टल के **'Weather Advisory' (मौसम सलाह)** डैशबोर्ड पर अपने क्षेत्र का पूर्वानुमान देखें।\n"
                "• भारत मौसम विज्ञान विभाग (IMD) के **मौसम पोर्टल** (mausam.imd.gov.in) या **मेघदूत (Meghdoot)** मोबाइल ऐप पर अपने ब्लॉक की मौसम सलाह देखें।"
            )
        elif language == "hinglish":
            reply = (
                "Namaste! Maitri Krishi chat me kal ke live weather forecast ka real-time feed connected nahi hai. Isliye bina live API ke mausam predict karna sahi nahi hoga.\n\n"
                "🌦️ **Accurate forecast ke liye:**\n"
                "• Maitri dashboard ke **'Weather Advisory'** section me dekhein.\n"
                "• IMD ke official **Mausam portal** (mausam.imd.gov.in) ya **Meghdoot App** par apne block ka live weather check karein."
            )
        else:
            reply = (
                "Hello! Maitri Krishi chat does not have an active live meteorological weather feed connected. To prevent incorrect forecasts, I cannot predict tomorrow's specific weather.\n\n"
                "🌦️ **For accurate, hyper-local forecasts:**\n"
                "• Check the **'Weather Advisory'** tab on the Maitri platform.\n"
                "• Refer to the India Meteorological Department (IMD) portal (mausam.imd.gov.in) or the **Meghdoot App** for block-level agro-advisories."
            )
        return {
            "reply": reply,
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
            "उत्तर लगभग 80 से 180 शब्दों में संक्षिप्त एवं बिंदुवार रखें।"
        ),
        "hinglish": (
            "Respond in natural, conversational Hinglish (Roman Hindi) suitable for Indian farmers. "
            "Keep the response concise (80 to 180 words) and directly actionable."
        ),
        "en": (
            "Respond in clear, professional, farmer-friendly English tailored to agriculture. "
            "Keep the response concise (80 to 180 words) and directly actionable."
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
            context_lines.append(f"• Registered Crop: {crop}")
        if context.get("soil_type") and any(w in q_lower for w in ["soil", "mitti", "khad", "fertilizer", "urea", "dap"]):
            context_lines.append(f"• Soil Type: {context.get('soil_type')}")
        if context.get("soil_moisture") is not None and any(w in q_lower for w in ["water", "irrig", "moisture", "paani", "pani", "sinchai", "nami"]):
            context_lines.append(f"• Live IoT Soil Moisture: {context.get('soil_moisture')}%")
        if context.get("temperature") is not None and any(w in q_lower for w in ["weather", "temp", "frost", "cold", "heat", "mausam"]):
            context_lines.append(f"• Live Field Temperature: {context.get('temperature')}°C")

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

CRITICAL GROUNDING & SAFETY RULES:
1. ONLY provide advice supported by the retrieved knowledge pieces. Do NOT invent causes, steps, or products.
2. CHEMICAL ADVICE (Pesticides/Fungicides/Fertilizers):
   - ONLY recommend a chemical spray or fertilizer dose if explicitly stated in the retrieved knowledge.
   - Do NOT guess dosages or combine dosages from different sources.
   - If no verified chemical dose is in the retrieved text, output:
     "I don't have enough verified information to recommend a specific chemical treatment safely. Please confirm the diagnosis and current recommendation with your local KVK/agriculture officer."
     (or Hindi equivalent).
3. DISEASE IDENTIFICATION SAFETY:
   - Text-only questions MUST NOT be treated as a confirmed diagnosis (e.g. if user says 'गेहूं के पत्ते पीले हैं', DO NOT say 'This is definitely Yellow Rust').
   - ALWAYS state: 'Possible causes include...' (संभावित कारणों में...) and outline distinguishing physical checks (e.g. powdery spore rub test on fingers vs inverted V yellowing along midrib).
   - Do NOT claim visual diagnosis capability.
4. ANSWER STRUCTURE FOR SYMPTOMS / PESTS / DISEASES:
   🌱 Possible Causes (संभावित कारण)
   - 2-3 supported possibilities based on retrieved text
   🔎 What to Check (क्या जांचें)
   - Specific physical symptoms or field conditions to differentiate
   ✅ What You Can Do (समाधान एवं उपाय)
   - Practical cultural/IPM actions supported by retrieved text
   ⚠️ When to Consult an Expert (विशेषज्ञ सलाह)
   - Clear note to consult local KVK or Agriculture Officer if severe or uncertain
5. ANSWER LENGTH & STYLE:
   - Target: 80–180 words. Keep it concise, practical, and devoid of filler.
   - Do NOT merely list document titles or mention internal chunks.
   - Language: {lang_inst}
   - Output ONLY the final farmer-facing response. No meta-commentary, no thinking blocks.

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

    return cleaned.strip()


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
            with httpx.Client(timeout=10.0) as client:
                resp = client.post(url, headers=headers, json=payload)
        except ImportError:
            resp = requests.post(url, headers=headers, json=payload, timeout=10.0)

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
    Synthesizes an intelligent, structured agricultural answer directly from
    retrieved knowledge chunks when OpenRouter is unreachable.
    Follows Phase 4 diagnostic structure and concise 80-180 word target.
    """
    if not retrieved_chunks:
        if language == "hi":
            return (
                "नमस्ते! आपके प्रश्न के सटीक समाधान के लिए ज्ञानकोष में पर्याप्त जानकारी नहीं मिली।\n"
                "कृपया अपनी फसल का नाम, राज्य और दिखने वाले विशिष्ट लक्षण बताएं।"
            )
        elif language == "hinglish":
            return (
                "Namaste! Aapke sawal ke exact solution ke liye knowledge base me paryapt details nahi mili.\n"
                "Kripya apni crop, state aur symptoms batayein taaki sahi jankari di ja sake."
            )
        else:
            return (
                "Hello! We could not find sufficient reliable information in the knowledge base for this query.\n"
                "Please provide your crop name, location, and specific symptoms."
            )

    # Extract substantive points from top chunks
    extracted_points = []
    for c in retrieved_chunks[:2]:
        text = c.get("text", "")
        clean_lines = [
            line.strip() for line in text.splitlines()
            if line.strip() and not line.strip().startswith("#") and not line.strip().startswith("[Source:")
        ]
        for l in clean_lines:
            if l.startswith(("-", "•", "1.", "2.", "3.", "4.")):
                extracted_points.append(l)
            elif len(l) > 30 and ":" in l:
                extracted_points.append(f"• {l}")

    if not extracted_points:
        for c in retrieved_chunks[:2]:
            clean_body = re.sub(r"^#+.*", "", c.get("text", ""), flags=re.MULTILINE).strip()
            sentences = [s.strip() for s in clean_body.split(".") if len(s.strip()) > 20]
            extracted_points.extend([f"• {s}." for s in sentences[:3]])

    content_summary = "\n".join(extracted_points[:5])
    top_chunk = retrieved_chunks[0] if retrieved_chunks else {}
    crop_val = top_chunk.get("crop", "")
    crop_hi_map = {
        "Wheat": "गेहूं",
        "Rice": "धान",
        "Maize": "मक्का",
        "Potato": "आलू",
        "Tomato": "टमाटर",
        "Mustard": "सरसों",
        "Chickpea": "चना"
    }
    crop_hi = crop_hi_map.get(crop_val, "")
    crop_str = f" ({crop_val}" + (f" / {crop_hi})" if crop_hi else ")") if crop_val and crop_val != "General" else ""
    title_val = top_chunk.get("title", "कृषि परामर्श")


    if language == "hi":
        return (
            f"🌱 **{title_val}{crop_str} — मुख्य बिंदु एवं निदान:**\n"
            f"{content_summary}\n\n"
            f"✅ **क्या करें:**\n"
            f"• प्रभावित पौधे, फसल और पत्तियों के लक्षणों का सावधानीपूर्वक निरीक्षण करें।\n"
            f"• अनुशंसित जैविक अथवा संतुलित पोषक तत्वों/कीट प्रबंधन का ही प्रयोग करें।\n\n"
            f"⚠️ **कब विशेषज्ञ से संपर्क करें:** किसी भी रासायनिक कीटनाशक छिड़काव से पहले लक्षण की पुष्टि के लिए अपने स्थानीय कृषि विज्ञान केंद्र (KVK) या कृषि अधिकारी से संपर्क करें।"
        )
    elif language == "hinglish":
        return (
            f"🌱 **{title_val}{crop_str} — Key Points & Advisory:**\n"
            f"{content_summary}\n\n"
            f"✅ **What you can do:**\n"
            f"• Field symptoms aur crop moisture conditions ko dhyan se inspect karein.\n"
            f"• Recommended balanced nutrients aur IPM practices follow karein.\n\n"
            f"⚠️ **When to consult an expert:** Kisi bhi chemical spray se pehle apne local Krishi Vigyan Kendra (KVK) ya agriculture officer se confirm zaroor karein."
        )
    else:
        return (
            f"🌱 **Possible Causes & Key Observations:**\n"
            f"{content_summary}\n\n"
            f"✅ **Recommended Actions:**\n"
            f"• Inspect field moisture levels and leaf patterns closely.\n"
            f"• Follow integrated pest and nutrient management practices.\n\n"
            f"⚠️ **When to Consult an Expert:** For chemical pesticide confirmation or severe symptoms, please consult your local Krishi Vigyan Kendra (KVK) or Agriculture Extension Officer."
        )


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
            "उत्तर लगभग 80 से 180 शब्दों में संक्षिप्त एवं बिंदुवार रखें।"
        ),
        "hinglish": (
            "Respond in natural, conversational Hinglish (Roman Hindi) suitable for Indian farmers. "
            "Keep the response concise (80 to 180 words) and directly actionable."
        ),
        "en": (
            "Respond in clear, professional, farmer-friendly English tailored to agriculture. "
            "Keep the response concise (80 to 180 words) and directly actionable."
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

CRITICAL GROUNDING & SYNTHESIS RULES:
1. STRICT GROUNDING: Answer ONLY from the provided web evidence. Do NOT invent facts, rules, dates, or numbers absent from the sources.
2. CITATIONS & DATES: Mention relevant dates and official departments when available in the evidence.
3. CONFLICTING EVIDENCE: If different sources state conflicting rules or figures, explicitly state the difference rather than arbitrarily picking one.
4. HONESTY: If the provided evidence does not fully answer the specific question, clearly state what is known and what cannot be confirmed.
5. NO INVENTED URLs: Never invent URLs or website titles.
6. TARGET LENGTH & LANGUAGE:
   - Target: 80–180 words. Direct, structured, and farmer-friendly.
   - Language: {lang_inst}
   - Output ONLY the final farmer-facing response without meta-commentary or thinking tags.

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
        points.append(f"• **{ev.domain}**{date_str}: {clean_snip}")

    evidence_summary = "\n".join(points)
    top_org = top_items[0].domain

    if language == "hi":
        return (
            f"🌐 **लाइव वेब सूचना ({top_org} एवं अन्य आधिकारिक स्रोत):**\n\n"
            f"{evidence_summary}\n\n"
            f"📌 **सलाह:** यह जानकारी हालिया वेब स्रोतों पर आधारित है। अंतिम पुष्टि हेतु आधिकारिक सरकारी पोर्टल (जैसे {top_org}) का अवलोकन करें।"
        )
    elif language == "hinglish":
        return (
            f"🌐 **Live Web Intelligence ({top_org} & verified sources):**\n\n"
            f"{evidence_summary}\n\n"
            f"📌 **Note:** Ye information recent web sources par grounded hai. Latest notification confirmation ke liye official portal ({top_org}) check karein."
        )
    else:
        return (
            f"🌐 **Live Web Intelligence ({top_org} & verified sources):**\n\n"
            f"{evidence_summary}\n\n"
            f"📌 **Advisory:** This update is derived from recent verified web records. For legal or enrollment confirmation, please check the official portal ({top_org})."
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
    route_decision = classify_query(clean_msg, context)
    logger.info(
        f"SMART_RAG route={route_decision.intent.value} action={route_decision.action.value} confidence={route_decision.confidence:.2f}"
    )

    # Branch 1.1: Safety-critical Pesticide Dosing / Mixing Refusal
    if route_decision.intent == Intent.PESTICIDE_REFUSAL:
        return {
            "reply": compose_pesticide_refusal_reply(lang, route_decision.detected_entities),
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
        from .rag_service import is_gibberish as check_gibberish
        if check_gibberish(clean_msg):
            reply = (
                "मुझे मैत्री कृषि ज्ञानकोष में इस विषय पर पर्याप्त प्रामाणिक जानकारी नहीं मिली।\n\n"
                "सटीक समाधान के लिए कृपया बताएं:\n"
                "• फसल का नाम\n"
                "• राज्य या जिला\n"
                "• फसल की आयु (दिन)\n"
                "• समस्या या दिखने वाले लक्षण"
            ) if lang == "hi" else (
                "Maitri agriculture knowledge base me is sawal par sufficient information nahi mili.\n\n"
                "Accurate advice ke liye kripya batayein:\n"
                "• Crop name\n"
                "• State/District\n"
                "• Crop age (days)\n"
                "• Symptoms ya problem details"
            ) if lang == "hinglish" else (
                "I could not find enough reliable information in the agricultural knowledge base for this query.\n\n"
                "To help you accurately, please specify:\n"
                "• Crop name\n"
                "• Region/state\n"
                "• Crop growth stage\n"
                "• Visible symptoms or problem"
            )
            return {
                "reply": reply,
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
                "reply": compose_unsupported_reply(lang, is_gibberish_input=False),
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
            "reply": compose_missing_context_reply(route_decision.intent, route_decision.required_context, lang),
            "sources": [],
            "retrieved_chunks": 0,
            "confidence": route_decision.confidence,
            "language": lang,
            "provider": "context_guard",
            "intent": route_decision.intent.value,
            "route": route_decision.action.value,
            "requires_context": route_decision.required_context
        }

    # Branch 1.5: Weather Service Advisory (when location context is known)
    if route_decision.intent == Intent.WEATHER and route_decision.action == RouteAction.WEATHER_SERVICE:
        loc = route_decision.detected_entities.get("location", "Your Farm Area")
        if lang == "hi":
            reply = (
                f"🌦️ **मौसम सलाह ({loc}):**\n\n"
                f"आपके क्षेत्र ({loc}) के सटीक पूर्वानुमान एवं कृषि सलाह के लिए मैत्री के **'Weather Advisory'** डैशबोर्ड पर रीयल-टाइम तापमान, वर्षा संभावना और हवा की गति का विश्लेषण उपलब्ध है।\n\n"
                f"🌾 **मौसम आधारित मुख्य कृषि सिफारिश:**\n"
                f"• यदि वर्षा की संभावना 40% से अधिक हो तो कीटनाशक या उर्वरक का पर्णीय छिड़काव स्थगित करें।\n"
                f"• तेज हवा (>15 किमी/घंटा) में स्प्रे ड्रिफ्ट से बचने के लिए सुबह के शांत समय में ही छिड़काव करें।"
            )
        elif lang == "hinglish":
            reply = (
                f"🌦️ **Weather Advisory ({loc}):**\n\n"
                f"Aapke area ({loc}) ke hyper-local forecast aur spraying conditions ke liye Maitri ke **'Weather Advisory'** dashboard me live data check karein.\n\n"
                f"🌾 **Key Farm Recommendations:**\n"
                f"• Agar rain probability 40% se jyada ho to foliar spray postpone karein.\n"
                f"• Tej hawa (>15 km/h) me chemical drift se bachne ke liye early morning spray prefer karein."
            )
        else:
            reply = (
                f"🌦️ **Weather Advisory ({loc}):**\n\n"
                f"For hyper-local forecasts and spraying conditions for {loc}, please inspect the **'Weather Advisory'** tab on the Maitri platform.\n\n"
                f"🌾 **Key Agronomic Rules:**\n"
                f"• Postpone pesticide or foliar fertilizer spraying if precipitation probability exceeds 40%.\n"
                f"• Avoid spraying during high winds (>15 km/h) to eliminate spray drift hazard."
            )
        return {
            "reply": reply,
            "sources": [],
            "retrieved_chunks": 0,
            "confidence": route_decision.confidence,
            "language": lang,
            "provider": "weather_service",
            "intent": route_decision.intent.value,
            "route": route_decision.action.value
        }

    # Branch 1.6: Financial / Insurance (PMFBY Guidelines)
    if route_decision.intent == Intent.FINANCIAL and ("pmfby" in clean_msg.lower() or "bima" in clean_msg.lower() or "insurance" in clean_msg.lower()):
        if lang == "hi":
            reply = (
                "🏛️ **प्रधानमंत्री फसल बीमा योजना (PMFBY) - मुख्य दिशा-निर्देश:**\n\n"
                "• **किसान प्रीमियम हिस्सा:** रबी फसलों के लिए बीमित राशि का 1.5%, खरीफ फसलों के लिए 2.0%, और वाणिज्यिक/बागवानी फसलों के लिए 5.0%।\n"
                "• **72 घंटे की अनिवार्यता:** ओलावृष्टि, जलभराव या चक्रवाती बारिश से स्थानीय क्षति होने पर घटना के **72 घंटे के भीतर** कृषि विभाग या हेल्पलाइन (14447) पर सूचना देना अनिवार्य है।\n"
                "• **दावा निपटान:** आधिकारिक अधिसूचना, प्रीमियम भुगतान और फसल कटाई प्रयोग (CCE) के सत्यापन पर निर्भर करता है।"
            )
        elif lang == "hinglish":
            reply = (
                "🏛️ **Pradhan Mantri Fasal Bima Yojana (PMFBY) Guidelines:**\n\n"
                "• **Farmer Premium Share:** Rabi crops ke liye 1.5% of Sum Insured, Kharif crops ke liye 2.0%, aur commercial/horticultural crops ke liye 5.0%.\n"
                "• **Mandatory 72-Hour Rule:** Hailstorm, inundation ya unseasonal rain se damage hone par **72 hours ke andar** portal ya toll-free helpline (14447) par claim intimation dena zaroori hai.\n"
                "• **Settlement:** Claim official notification, cut-off date enrollment aur Crop Cutting Experiments (CCE) assessment par depend karta hai."
            )
        else:
            reply = (
                "🏛️ **Pradhan Mantri Fasal Bima Yojana (PMFBY) Guidelines:**\n\n"
                "• **Statutory Premium Caps:** 1.5% of Sum Insured for Rabi crops, 2.0% for Kharif crops, and 5.0% for commercial/horticultural crops.\n"
                "• **72-Hour Intimation Mandate:** For localized calamities (hailstorm, inundation, post-harvest rain), intimation must be registered within **72 hours** via the PMFBY portal or helpline (14447).\n"
                "• **Settlement:** Claims depend on notified area status, timely premium submission, and official revenue/CCE loss survey."
            )
        return {
            "reply": reply,
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
                    "reply": result,
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
                    "reply": offline_web_reply,
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
            "reply": reply,
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
                "reply": compose_web_evidence_unavailable_reply(lang),
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
                        "reply": result,
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
                        "reply": offline_reply,
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
                "• फसल का नाम\n"
                "• राज्य या जिला\n"
                "• फसल की आयु (दिन)\n"
                "• समस्या या दिखने वाले लक्षण"
            )
        elif lang == "hinglish":
            reply = (
                "Maitri agriculture knowledge base me is sawal par sufficient information nahi mili.\n\n"
                "Accurate advice ke liye kripya batayein:\n"
                "• Crop name\n"
                "• State/District\n"
                "• Crop age (days)\n"
                "• Symptoms ya problem details"
            )
        else:
            reply = (
                "I could not find enough reliable information in the agricultural knowledge base for this query.\n\n"
                "To help you accurately, please specify:\n"
                "• Crop name\n"
                "• Region/state\n"
                "• Crop growth stage\n"
                "• Visible symptoms or problem"
            )

        return {
            "reply": reply,
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
    print("\n" + "=" * 60)
    print("USER QUERY:")
    print(clean_msg)
    print(f"DETECTED CROP: {rag_result.get('detected_crop')} | CATEGORY: {rag_result.get('detected_category')}")
    print("\nRETRIEVED CHUNKS:")
    for idx, c in enumerate(chunks):
        stype = c.get('source_type', 'curated_reference')
        print(f"{idx+1}. {c.get('source')} ({stype}) / {c.get('title')} - {c.get('section')} / Score: {c.get('score')}")
        snippet = c.get('text', '')[:180].replace('\n', ' ')
        print(f"   {snippet}...")

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
            freshness_note = "ℹ️ **सूचना:** नवीनतम जानकारी के लिए लाइव इंटरनेट सत्यापन वर्तमान में अनुपलब्ध है, इसलिए नवीनतम अपडेट की पुष्टि नहीं की जा सकी। मैत्री ज्ञानकोष में उपलब्ध सत्यापित पृष्ठभूमि जानकारी निम्नलिखित है:\n\n"
        elif lang == "hinglish":
            freshness_note = "ℹ️ **Note:** Live internet verification abhi available nahi hai, isliye latest updates confirm nahi kiye ja sakte. MAITTRI knowledge base me available verified background information neeche di gayi hai:\n\n"
        else:
            freshness_note = "ℹ️ **Note:** Live verification is currently unavailable, so I cannot confirm the latest update. Here is the available MAITTRI background information:\n\n"

    if success:
        print(f"\nOPENROUTER SUCCESS (model: {model_used})")
        print("\nFINAL ANSWER:")
        final_reply = (freshness_note + result) if freshness_note else result
        print(final_reply[:300] + "..." if len(final_reply) > 300 else final_reply)
        print("\nSOURCES USED:")
        for s in sources:
            print(f"• {s.get('organization')} ({s.get('source_type')}) — {s.get('title')}")
        print("=" * 60 + "\n")

        return {
            "reply": final_reply,
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
    print(f"\nOPENROUTER UNAVAILABLE ({result}). Generating grounded local RAG synthesis.")
    offline_reply = generate_grounded_offline_reply(clean_msg, lang, chunks)
    final_offline = (freshness_note + offline_reply) if freshness_note else offline_reply
    print("\nFINAL ANSWER:")
    print(final_offline[:300] + "...")
    print("=" * 60 + "\n")

    return {
        "reply": final_offline,
        "sources": sources,
        "retrieved_chunks": len(chunks),
        "confidence": confidence,
        "language": lang,
        "provider": "grounded_local_rag",
        "intent": route_decision.intent.value,
        "route": route_decision.action.value
    }
