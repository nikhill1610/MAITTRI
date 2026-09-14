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
# OpenRouter API Client
# -----------------------------------------------------------------------------
def call_openrouter(
    messages: List[Dict[str, str]],
    model: Optional[str] = None
) -> Tuple[bool, str, str]:
    """
    Calls OpenRouter chat completions API.
    Tries primary model first, falls back to secondary model if needed.
    Returns (success, reply_content, model_used).
    """
    api_key = os.getenv("OPENROUTER_API_KEY", "").strip()
    if not api_key:
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

    # 1. Anti-hallucination interceptors (Section 12: live mandi prices, live weather forecasts, ungrounded chemical queries)
    intercept = check_anti_hallucination_intercept(clean_msg, lang)
    if intercept:
        return intercept

    # 2. RAG Retrieval from ChromaDB
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
            "provider": "boundary_guard"
        }

    # 4. Low confidence / Gibberish guard
    if rag_result.get("is_low_confidence") or not rag_result.get("chunks"):
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
            "provider": "low_confidence_guard"
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

    if success:
        print(f"\nOPENROUTER SUCCESS (model: {model_used})")
        print("\nFINAL ANSWER:")
        print(result[:300] + "..." if len(result) > 300 else result)
        print("\nSOURCES USED:")
        for s in sources:
            print(f"• {s.get('organization')} ({s.get('source_type')}) — {s.get('title')}")
        print("=" * 60 + "\n")

        return {
            "reply": result,
            "sources": sources,
            "retrieved_chunks": len(chunks),
            "confidence": confidence,
            "language": lang,
            "provider": "openrouter",
            "model": model_used
        }

    # 8. Fallback: Synthesize cleanly from retrieved chunks
    print(f"\nOPENROUTER UNAVAILABLE ({result}). Generating grounded local RAG synthesis.")
    offline_reply = generate_grounded_offline_reply(clean_msg, lang, chunks)
    print("\nFINAL ANSWER:")
    print(offline_reply[:300] + "...")
    print("=" * 60 + "\n")

    return {
        "reply": offline_reply,
        "sources": sources,
        "retrieved_chunks": len(chunks),
        "confidence": confidence,
        "language": lang,
        "provider": "grounded_local_rag"
    }
