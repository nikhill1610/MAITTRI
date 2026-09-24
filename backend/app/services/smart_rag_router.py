"""
Smart RAG Pre-Retrieval Intent, Safety & Service Router for MAITTRI Krishi Assistant
------------------------------------------------------------------------------------
Executes BEFORE vector retrieval in the RAG pipeline to:
1. Enforce strict agricultural safety guardrails (pesticide dosing/mixing refusal, prompt injection resistance).
2. Filter gibberish and out-of-domain queries before touching vector stores or LLM endpoints.
3. Route live-data questions to deterministic MAITTRI services (Weather, Market Prices, PMFBY Insurance, Schemes).
4. Detect missing required context (e.g. location for weather, crop/area for dosage) and request clarification.
5. Direct agronomic knowledge questions to RAG knowledge base retrieval.

Performance: Ultra-fast local execution (<2ms) using Unicode-aware regex matching and deterministic rules.
Resilience: 100% functional without external LLMs, OpenRouter, or network calls.
"""

import re
import logging
from enum import Enum
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field, asdict

logger = logging.getLogger("maitri.smart_rag_router")


class Intent(str, Enum):
    GENERAL = "GENERAL"
    CALENDAR = "CALENDAR"
    WEATHER = "WEATHER"
    SOIL = "SOIL"
    FERTILIZER = "FERTILIZER"
    PESTICIDE_REFUSAL = "PESTICIDE_REFUSAL"
    FINANCIAL = "FINANCIAL"
    MARKET = "MARKET"
    UNSUPPORTED = "UNSUPPORTED"


class RouteAction(str, Enum):
    RAG = "RAG"
    WEATHER_SERVICE = "WEATHER_SERVICE"
    CALENDAR_SERVICE = "CALENDAR_SERVICE"
    SOIL_SERVICE = "SOIL_SERVICE"
    FERTILIZER_SERVICE = "FERTILIZER_SERVICE"
    FINANCIAL_SERVICE = "FINANCIAL_SERVICE"
    MARKET_SERVICE = "MARKET_SERVICE"
    SAFE_REFUSAL = "SAFE_REFUSAL"
    ASK_FOR_CONTEXT = "ASK_FOR_CONTEXT"
    WEB_SEARCH = "WEB_SEARCH"
    RAG_WEB_FALLBACK = "RAG_WEB_FALLBACK"


@dataclass
class RouteDecision:
    intent: Intent
    confidence: float
    action: RouteAction
    reason: str
    safety_level: str = "normal"  # normal | warning | critical_refusal | out_of_scope
    required_context: List[str] = field(default_factory=list)
    service: Optional[str] = None  # weather | market | insurance | schemes | calendar | fertilizer | soil | rag
    detected_entities: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "intent": self.intent.value,
            "confidence": round(self.confidence, 2),
            "action": self.action.value,
            "reason": self.reason,
            "safety_level": self.safety_level,
            "required_context": self.required_context,
            "service": self.service,
            "detected_entities": self.detected_entities
        }


def unicode_word_match(pattern: str, text: str) -> bool:
    """Matches terms using Unicode-aware boundary logic rather than ASCII \\b."""
    regex = rf"(?<![\u0900-\u097Fa-zA-Z0-9])({pattern})(?![\u0900-\u097Fa-zA-Z0-9])"
    return bool(re.search(regex, text, re.IGNORECASE))


# -----------------------------------------------------------------------------
# Multilingual Vocabulary & Pattern Definitions
# -----------------------------------------------------------------------------

# Helper for unicode word boundaries
def _ubound(pat: str) -> str:
    return rf"(?<![\u0900-\u097Fa-zA-Z0-9])(?:{pat})(?![\u0900-\u097Fa-zA-Z0-9])"

# Crop Patterns (Unicode boundary enforced; Pigeonpea before Chickpea to prevent 'red gram' clash)
CROPS_PATTERNS = {
    "Pigeonpea": _ubound(r"अरहर|तुअर|तुवर|arhar|tuar|tuvar|pigeonpea|red\s*gram"),
    "Wheat": _ubound(r"गेहूं|गेहू|गेहूँ|gehu|gehun|wheat"),
    "Rice": _ubound(r"धान|चावल|dhaan|chawal|rice|paddy"),
    "Mustard": _ubound(r"सरसों|राई|sarson|rai|mustard|rapeseed"),
    "Maize": _ubound(r"मक्का|मकई|makka|makai|corn|maize"),
    "Potato": _ubound(r"आलू|aaloo|aalu|potato"),
    "Tomato": _ubound(r"टमाटर|tamatar|tomato"),
    "Chickpea": _ubound(r"चना|चने|chana|chane|chickpea|bengal\s*gram|gram"),
    "Cotton": _ubound(r"कपास|cotton|kapas"),
    "Sugarcane": _ubound(r"गन्ना|sugarcane|ganna"),
    "Soybean": _ubound(r"सोयाबीन|soybean|soya"),
    "Onion": _ubound(r"प्याज|pyaj|pyaaz|pyaz|onion"),
    "Groundnut": _ubound(r"मूंगफली|mungfali|peanut|groundnut"),
    "Chilli": _ubound(r"मिर्च|mirch|mirchi|chilli|chili"),
    "Banana": _ubound(r"केला|kela|banana")
}

# Prompt Injection Patterns (Attempts to override MAITTRI rules or ask for dangerous instructions)
PROMPT_INJECTION_PATTERNS = [
    r"ignore\s+(?:all\s+)?(?:previous\s+)?(?:system\s+|maittri\s+)?(instructions|prompts?|rules|constraints|guidelines|safety)",
    r"bypass\s+(?:all\s+)?(?:previous\s+)?(?:system\s+|maittri\s+)?(rules|safety|filters)",
    r"disregard\s+(?:all\s+)?(?:previous\s+)?(instructions|prompts?|rules)",
    r"act as\s+(?:an unfiltered|dan|jailbreak)",
    r"forget\s+(?:all\s+)?(?:previous\s+)?(?:your\s+)?(instructions|rules|persona)",
    r"(you are now|pretend to be)\s+(?:an unfiltered|dan|jailbreak|unrestricted)",
    r"(jailbreak|unfiltered)\s+mode",
    r"नियमों को अनदेखा",
    r"सभी नियम भूल जाओ",
    r"(पिछली|सभी)\s+(हिदायतें|निर्देश|नियम)\s*(भूल जाओ|अनदेखा|हटाओ)"
]

# Chemical / Pesticide Safety Risk Patterns (Triggers PESTICIDE_REFUSAL)
PESTICIDE_SAFETY_PATTERNS = [
    # Dosage queries: exact tank quantity, double dose, ml per litre
    r"(kitna|how much|कितना|कितनी)\s+(pesticide|chemical|dose|dawa|कीटनाशक|दवा|दवाई)",
    r"(pesticide|कीटनाशक|chemical|दवा)\s+ka\s+(double|exact|sahi)?\s*dose",
    r"(double|triple|दो गुना|दोगुना)\s*(?:pesticide|chemical|कीटनाशक|दवा)?\s*(dose|खुराक|मात्रा)",
    r"(\d+\s*(litre|liter|लीटर|ltr))\s*(tank|टंकी)?.*?(pesticide|chemical|dose|दवा|कीटनाशक|मिला|mix|spray)",
    # Lethal / Restricted Use Fumigant residential safety gate
    r"(?:celphos|sulphas|quickphos|aluminium phosphide|सल्फास|सेलफॉस|सल्फॉस)",
    # Chemical mixing queries (both SVO and Hindi SOV word orders)
    r"(?:mix|मिलाना|मिलाऊं|मिलाएं|मिलाकर)\s+.*?(?:two|2|these|दो)?\s*(?:pesticides?|chemicals?|दवाएं|कीटनाशक)",
    r"(?:दो|2|these|दो या दो से अधिक)?\s*(?:कीटनाशक|दवा|दवाएं|chemicals?|pesticides?)\s*.*?(?:मिला|mix)",
    r"can i mix (these )?(two )?pesticides",
    r"how much pesticide should i mix",
    r"which chemical dose should i spray",
    r"chemical combinations? (to spray|for pest)",
    r"(tank|टंकी|पंप)\s+me\s+kitna\s+(ml|gram|ग्राम|लीटर|dose|दवा)",
    r"tank me pesticide ka double dose",
    r"dangerous pesticide mixing",
    r"(banned|प्रतिबंधित)\s+(pesticide|chemical|कीटनाशक)",
    r"off-label",
    r"unknown disease.*?(exact pesticide|chemical)",
    r"अज्ञात बीमारी.*?(दवा|कीटनाशक|स्प्रे)"
]

# Weather / Meteorological Patterns (Requires actual meteorological keywords)
WEATHER_PATTERNS = [
    r"(?:मौसम|weather|forecast|\brain\b|ba+rish|बारिश|वर्षा|बरसात|barsat|barsaat|तापमान|temperature|frost|पाला|cold wave|शीतलहर|heatwave|लू|mausam|monsoon|मानसून|drought|सूखा)",
    r"(?:कल|आज|अभी|tomorrow|today|yesterday|aaj|kal|abhi|current|live|now|right\s*now)\s+.*?(?:मौसम|weather|\brain\b|ba+rish|बारिश|वर्षा|बरसात|barsat|barsaat|forecast|तापमान|temperature|frost|पाला|spray|छिड़काव|mausam|sinchai|irrigation|rainfall|humidity|monsoon)",
    r"(?:kya\s+)?(?:abhi|kal|aaj|today|tomorrow)\s+.*?(?:ba+rish|barish|बारिश|वर्षा|barsat|barsaat|rain|raining|precipitation)\s*(?:ho|hogi|hoga|hai|rhi|rahi|pad)",
    r"(?:can i spray|spray karu|छिड़काव करूं|छिड़काव करूँ|spray karun|should i spray)",
    r"(?:aaj|kal|today|tomorrow|now|abhi)\s*.*?(?:irrigation|sinchai|पानी|सिंचाई)\s*(?:karu|karein|dena|karni|kare|chahiye|should)",
    r"(?:should i irrigate|irrigate today|irrigation today)",
    r"(?:mausam|weather)\s*(?:ke hisaab|ke hisab|ke according|according)",
    r"(?:wind speed|हवा की गति|humidity|नमी का स्तर|rainfall|precipitation|बूंदाबांदी|drizzle)"
]

# Mandi & Financial Patterns
MANDI_PATTERNS = [
    r"mandi\s*(?:bhav|rate|price|rates)",
    r"(मंडी|भाव|रेट|rate|price|bhav).*?(क्या है|कितना है|बताएं|बताओ|आज|today|latest|current|modal)",
    r"(आज|today|latest|current).*?(mandi|भाव|रेट|rate|price|bhav|modal)",
    r"what is today'?s (mandi|market) price",
    r"today'?s price of",
    r"mandi rate",
    r"msp|न्यूनतम समर्थन मूल्य|minimum support price",
    r"procurement|खरीद|खरीदी|उपार्जन",
    r"agmarknet|apmc|enam",
    r"modal\s*price",
    r"bazaar\s*(?:bhav|rate|price)",
    r"market\s*price"
]

INSURANCE_SCHEMES_PATTERNS = [
    r"pmfby|pm-fby|fasal bima|फसल बीमा|crop insurance",
    r"insurance premium|प्रीमियम|बीमा राशि|claim 72 hours|क्लेम",
    r"pm-kisan|pm kisan|पीएम किसान|पीएम-किसान|samman nidhi",
    r"kcc|kisan credit card|किसान क्रेडिट कार्ड",
    r"subsidy|सब्सिडी|अनुदान|yojana|scheme|सरकारी योजना"
]

# Soil Patterns
SOIL_PATTERNS = [
    r"(soil|mitti|मिट्टी|मृदा)\s*(ka|ki|ke|test|testing|health|card|ph|type|नमूना|जांच)",
    r"\bph\b\s*(\d+(\.\d+)?)?",
    r"(salin|alkali|salinity|लवणीय|क्षारीय|दोमट|चिकनी मिट्टी)",
    r"मिट्टी में (जिंक|नाइट्रोजन|पोटाश|फास्फोरस|कार्बन)",
    r"soil health card|मृदा स्वास्थ्य कार्ड",
    r"(micronutrient|सूक्ष्म पोषक तत्व|deficiency in soil)"
]

# Fertilizer Patterns
FERTILIZER_PATTERNS = [
    r"(यूरिया|urea|dap|डीएपी|mop|पोटाश|npk|जिंक सल्फेट|zinc sulphate|nano urea|जिप्सम|gypsum)",
    r"(fertilizer|खाद|उर्वरक|khad|nutrients?)\s*(kab|kitna|kaise|schedule|dose|timing|use|dalna|dena)",
    r"(nitrogen|phosphorus|potassium|phosphatic|biostimulant|humic acid|biofertilizer|बायोफर्टिलाइजर|ह्यूमिक)\s*(deficiency|dose|management|se|\bka\b|\bki\b|\bke\b)?",
    r"leaves are yellow.*?(nitrogen|urea|fertilizer)",
    r"पत्ते पीले.*?(नाइट्रोजन|यूरिया|खाद)"
]

# Calendar / Stage Patterns (Supports Hindi कब, English when, and Hinglish kab)
CALENDAR_PATTERNS = [
    r"(पहली|दूसरी|तीसरी|pehli|dusri|first|second)\s*(?:sinchai|irrigation|सिंचाई)\s*(?:kab|when|कब)",
    r"(?:sinchai|irrigation|सिंचाई)\s*(?:kab|when|कब)",
    r"(?:sowing|बुवाई|बोने)\s*(?:time|timing|window|kab|date|तारीख|समय|कब)",
    r"(?:harvesting|कटाई)\s*(?:time|timing|kab|date|कब)",
    r"\d+\s*(?:days|दिन)\s*(?:after|बाद)\s*(?:sowing|बुवाई)",
    r"(?:cri stage|crown root|tillering|flowering stage|अवस्था|कंस निकलने)"
]

# Freshness & Current Information Patterns (Sections 8 & 20)
FRESHNESS_PATTERNS = [
    r"\b(latest|recent|new|today|current|this year|2026|notification|circular|update|rules?|guidelines?)\b",
    r"\b(abhi|aaj|naya|naye|nayi|nai|taaza|taza|haal hi|sanshodhan|adhisuchna|paripatra)\b",
    r"(नई|नए|नया|आज|ताज़ा|ताजा|वर्तमान|हाल ही|नया नियम|नई गाइडलाइन|ताजा अपडेट|नया अपडेट|अधिसूचना|परिपत्र|संशोधन)"
]


def is_freshness_query(text: str) -> bool:
    """Detects explicit user demand for current, latest, or newly updated information."""
    q_lower = text.lower()
    return any(re.search(pat, q_lower) for pat in FRESHNESS_PATTERNS)


# Non-Agricultural Out-of-Domain Patterns
NON_AGRI_PATTERNS = [
    r"\b(python|java|javascript|c\+\+|golang|rust|html|css|sql query|code|coding|programming|algorithm)\b",
    r"\b(binary search|sorting algorithm|quick sort|merge sort|linked list)\b",
    r"\b(capital of|who is (the )?(president|prime minister|actor|actress|ceo|singer))\b",
    r"\b(movie|cinema|hollywood|bollywood|song|lyrics|cricket score|football match|fifa|ipl)\b",
    r"\b(bitcoin|cryptocurrency|ethereum|stock market trading|forex|wall street)\b",
    r"\b(write a (poem|story|essay|letter to girlfriend))\b",
    r"\b(iphone|samsung galaxy|laptop gaming|playstation)\b"
]


VALID_SHORT_WORDS = {
    # Hinglish & Hindi common grammar/stop words
    "is", "me", "ka", "ki", "ke", "ko", "se", "pe", "to", "na", "ha", "ye", "wo", "ab", "do",
    "ho", "ja", "de", "le", "re", "bhi", "par", "kya", "aur", "tai", "mai", "aap", "hum", "hai",
    # English common prepositions & short words
    "in", "on", "at", "to", "or", "of", "an", "as", "by", "if", "my", "up", "so", "no", "hi", "he", "we", "am"
}


def is_gibberish(text: str) -> bool:
    """Detects random key mashing or empty meaningless strings."""
    clean = text.strip()
    clean_lower = clean.lower()

    # Valid short words in Hindi/Hinglish/English are not gibberish
    if clean_lower in VALID_SHORT_WORDS:
        return False

    if len(clean) < 3:
        return True

    # For multi-word input, do not flag if legitimate words/acronyms exist
    if " " in clean:
        words = clean.split()
        gibberish_words = [w for w in words if is_gibberish(w)]
        return len(gibberish_words) / len(words) >= 0.5

    # Single token checks
    mash_patterns = [
        "asdf", "sdfg", "dfgh", "fghj", "ghjk", "hjkl", "jkl;",
        "qwer", "wert", "erty", "rtyu", "tyui", "yuio", "uiop",
        "zxcv", "xcvb", "cvbn", "vbnm",
        "asdjk", "jkash", "shdj", "kashd", "asdfg", "qwerty"
    ]
    if any(p in clean.lower() for p in mash_patterns):
        return True

    # High length alphabetical string without normal vowel distribution
    if re.fullmatch(r"[a-zA-Z]+", clean) and len(clean) >= 6:
        vowels = re.findall(r"[aeiouAEIOU]", clean)
        if len(vowels) == 0 or len(vowels) / len(clean) < 0.18:
            return True

    # Consonant clusters of 5 or more in a single non-acronym word
    if re.search(r"[bcdfghjklmnpqrstvwxyzBCDFGHJKLMNPQRSTVWXYZ]{5,}", clean) and clean.isupper() is False:
        return True

    # Repeated identical characters (e.g. "aaaaaa", "asdfasdfasdf")
    if len(set(clean)) <= 2 and len(clean) > 4:
        return True

    return False


def is_non_agricultural_query(text: str) -> bool:
    """Identifies queries that are completely outside agricultural scope."""
    q_lower = text.lower().strip()

    # If query contains explicit non-agri markers
    for pat in NON_AGRI_PATTERNS:
        if re.search(pat, q_lower):
            # Verify no overriding agricultural context exists (e.g. "python for farm iot" vs "write java code")
            agri_overrides = ["crop", "khet", "farm", "kisan", "soil", "wheat", "rice", "fasal", "mandi", "disease", "advisory", "pest"]
            if not any(w in q_lower for w in agri_overrides):
                return True

    return False


KNOWN_LOCATIONS = {
    # Uttar Pradesh
    "meerut", "aligarh", "agra", "bareilly", "varanasi", "lucknow", "kanpur", "kanpur nagar",
    "muzaffarnagar", "prayagraj", "allahabad", "gorakhpur", "saharanpur", "bijnor", "moradabad",
    "rampur", "bulandshahr", "mathura", "firozabad", "mainpuri", "etawah", "jhansi", "banda",
    "lalitpur", "jalaun", "hamirpur", "mahoba", "chitrakoot", "ayodhya", "faizabad", "barabanki",
    "sultanpur", "amethi", "rae bareli", "sitapur", "lakhimpur", "lakhimpur kheri", "hardoi",
    "unnao", "badaun", "pilibhit", "shahjahanpur", "deoria", "kushinagar", "azamgarh", "mau",
    "ballia", "jaunpur", "ghazipur", "chandauli", "mirzapur", "sonbhadra", "shamli", "baghpat",
    "hapur", "sambhal", "amroha", "kasganj",
    # Punjab
    "ludhiana", "amritsar", "bathinda", "patiala", "jalandhar", "sangrur", "firozpur", "faridkot",
    "moga", "hoshiarpur", "gurdaspur", "kapurthala", "mansa", "muktsar", "barnala", "rupnagar",
    "mohali", "fazilka", "pathankot", "tarn taran",
    # Haryana
    "karnal", "hisar", "ambala", "sirsa", "rohtak", "kurukshetra", "sonipat", "panipat", "jind",
    "kaithal", "fatehabad", "bhiwani", "rewari", "mahendragarh", "gurugram", "gurgaon", "faridabad",
    "palwal", "mewat", "nuh", "panchkula", "yamunanagar", "charkhi dadri",
    # Madhya Pradesh
    "indore", "ujjain", "bhopal", "sehore", "gwalior", "jabalpur", "hoshangabad", "narmadapuram",
    "dewas", "dhar", "khargone", "khandwa", "ratlam", "mandsaur", "neemuch", "sagar", "vidisha",
    # Rajasthan
    "jaipur", "kota", "sri ganganagar", "ganganagar", "bikaner", "jodhpur", "alwar", "bharatpur",
    "hanumangarh", "sikar", "nagaur",
    # Delhi / NCR & Major Centers
    "delhi", "new delhi", "ncr",
    # States
    "uttar pradesh", "punjab", "haryana", "madhya pradesh", "rajasthan", "bihar", "maharashtra", "gujarat"
}

HINDI_KNOWN_LOCATIONS = {
    "दिल्ली": "Delhi",
    "नई दिल्ली": "New Delhi",
    "मेरठ": "Meerut",
    "लखनऊ": "Lucknow",
    "कानपुर": "Kanpur",
    "करनाल": "Karnal",
    "आगरा": "Agra",
    "वाराणसी": "Varanasi",
    "बरेली": "Bareilly",
    "प्रयागराज": "Prayagraj",
    "इलाहाबाद": "Allahabad",
    "गोरखपुर": "Gorakhpur",
    "सहारनपुर": "Saharanpur",
    "अलीगढ़": "Aligarh",
    "मुरादाबाद": "Moradabad",
    "झांसी": "Jhansi",
    "अयोध्या": "Ayodhya",
    "बाराबंकी": "Barabanki",
    "लुधियाना": "Ludhiana",
    "अमृतसर": "Amritsar",
    "पटियाला": "Patiala",
    "जालंधर": "Jalandhar",
    "बठिंडा": "Bathinda",
    "हिसार": "Hisar",
    "रोहतक": "Rohtak",
    "अंबाला": "Ambala",
    "गुरुग्राम": "Gurugram",
    "गुड़गांव": "Gurgaon",
    "फरीदाबाद": "Faridabad",
    "पानीपत": "Panipat",
    "सोनीपत": "Sonipat",
    "इंदौर": "Indore",
    "उज्जैन": "Ujjain",
    "भोपाल": "Bhopal",
    "ग्वालियर": "Gwalior",
    "जबलपुर": "Jabalpur",
    "जयपुर": "Jaipur",
    "कोटा": "Kota",
    "जोधपुर": "Jodhpur",
    "बीकानेर": "Bikaner",
    "उत्तर प्रदेश": "Uttar Pradesh",
    "पंजाब": "Punjab",
    "हरियाणा": "Haryana",
    "मध्य प्रदेश": "Madhya Pradesh",
    "राजस्थान": "Rajasthan",
    "बिहार": "Bihar",
    "गुजरात": "Gujarat",
    "महाराष्ट्र": "Maharashtra",
}

LOCATION_STOPWORDS = {
    # Time / Temporal
    "aaj", "kal", "parson", "today", "tomorrow", "now", "current", "latest", "recent", "abhi",
    "subah", "shaam", "raat", "morning", "evening", "night",
    # Crops & Farm
    "gehun", "gehu", "wheat", "dhan", "dhaan", "paddy", "rice", "makka", "maize", "corn",
    "sarson", "mustard", "aloo", "aalu", "potato", "tamatar", "tomato", "chawal", "fasal", "crop", "crops",
    "khet", "farm", "field", "mitti", "soil", "pani", "water", "sinchai", "irrigation", "khad", "fertilizer",
    "urea", "dap", "spray", "spraying", "keetnashak", "pesticide", "dawa", "rog", "disease",
    "kisan", "farmer", "krishi", "agriculture", "kheti", "beej", "seed",
    "arhar", "tuar", "chana", "chickpea", "gram", "mungfali", "peanut", "groundnut", "soybean", "soya",
    "kapas", "cotton", "ganna", "sugarcane", "pyaj", "onion", "mirch", "chilli", "kela", "banana", "bajra", "jowar",
    # Stages & Operations
    "cri", "tillering", "flowering", "pod", "milking", "dough", "booting", "sowing", "harvesting", "buwai", "ropai", "katai", "nursery",
    # Nutrients
    "gypsum", "potash", "sulphate", "compost", "manure", "gobarkhad", "zinc", "boron",
    # Weather words
    "mausam", "weather", "barish", "baarish", "rain", "rainfall", "temperature", "taapman", "forecast",
    "frost", "pala", "hawa", "wind", "dhoop", "sun", "cloud", "badal", "alert",
    # Action / Grammar / Helpers
    "karein", "kare", "karna", "karni", "karta", "karega", "hoga", "hogi", "hai", "hain", "tha", "thi",
    "kya", "kyu", "kyun", "kab", "kaise", "kisko", "kahan", "kitna", "kitni", "kitne",
    "batao", "bataiye", "batayein", "bata", "dein", "dena", "chahiye", "hisaab", "hisab", "according",
    "apne", "apna", "apni", "mere", "meri", "mera", "is", "iss", "us", "uss", "yeh", "woh",
    "pehli", "dusri", "teesri", "first", "second", "third", "stage", "din", "day", "days",
    "advisory", "advice", "salah", "check", "kripya", "please", "help",
    # Pests, Diseases, and Management
    "borer", "aphid", "aphids", "thrips", "whitefly", "weevil", "mite", "mites", "nematode", "nematodes",
    "caterpillar", "armyworm", "rust", "blight", "rot", "wilt", "curl", "mosaic", "smut", "mildew",
    "keeda", "keede", "sundi", "illi", "ilaj", "upchar", "upay", "dawai", "prabandhan", "management", "control",
    # Market words
    "mandi", "bazaar", "bazar", "market", "apmc", "rate", "rates", "bhav", "price", "prices", "modal", "dam", "daam",
    # Government schemes, policy, and administrative terms
    "pmfby", "pmkisan", "kisan", "yojana", "scheme", "schemes", "bima", "fasal", "policy", "rules", "rule", "niyam",
    "circular", "guidelines", "guideline", "update", "updates", "amendment", "notification", "adhisuchna", "paripatra",
    "central", "government", "sarkar", "state", "pradhan", "mantri"
}


def _is_valid_location_candidate(cand: str) -> bool:
    """Validates candidate string to ensure it is not a stopword, crop, or growth stage."""
    c_low = cand.lower().strip()
    if c_low in LOCATION_STOPWORDS or len(c_low) < 3:
        return False
    # Ensure it doesn't match any crop pattern
    for pat in CROPS_PATTERNS.values():
        if re.search(pat, c_low):
            return False
    return True


def extract_location_from_text(text: str) -> Optional[str]:
    """Extracts an explicit location mention from a query or chat message."""
    if not text or not text.strip():
        return None
    raw = text.strip()
    q_lower = raw.lower()

    # 1. Check Hindi known locations (longest first)
    for h_loc, en_name in sorted(HINDI_KNOWN_LOCATIONS.items(), key=lambda x: len(x[0]), reverse=True):
        if h_loc in raw:
            return en_name

    # 2. Check English / Transliterated known locations (longest first)
    for loc in sorted(KNOWN_LOCATIONS, key=len, reverse=True):
        if re.search(r"\b" + re.escape(loc) + r"\b", q_lower):
            return loc.upper() if len(loc) <= 3 else loc.title()

    # 3. Prepositional / Postpositional patterns
    # Postpositional grammar: "X mein", "X me", "X ka", "X ke", "X ki", "X jile", "X district"
    post_pat = r"\b([a-zA-Z\u0900-\u097F]{3,25})\s+(?:mein|me|ka|ke|ki|jile|jila|district|में|का|के|की|जिले|ज़िले)\b"
    m = re.search(post_pat, raw, re.IGNORECASE)
    if m:
        cand = m.group(1).strip()
        if _is_valid_location_candidate(cand):
            return cand.title() if cand.isascii() else cand

    # Mandi-specific postposition: "X mandi", "X APMC", "X bazaar"
    mandi_loc_pat = r"\b([a-zA-Z\u0900-\u097F]{3,25})\s+(?:mandi|मंडी|bazaar|बाज़ार|market|apmc)\b"
    m = re.search(mandi_loc_pat, raw, re.IGNORECASE)
    if m:
        cand = m.group(1).strip()
        if _is_valid_location_candidate(cand):
            return cand.title() if cand.isascii() else cand

    prep_pat = r"\b(?:in|at|for|near)\s+([a-zA-Z\u0900-\u097F]{3,25})\b"
    m = re.search(prep_pat, raw, re.IGNORECASE)
    if m:
        cand = m.group(1).strip()
        if _is_valid_location_candidate(cand):
            return cand.title() if cand.isascii() else cand

    weath_pat = r"\b([a-zA-Z\u0900-\u097F]{3,25})\s+(?:weather|forecast|mausam|मौसम)\b"
    m = re.search(weath_pat, raw, re.IGNORECASE)
    if m:
        cand = m.group(1).strip()
        if _is_valid_location_candidate(cand):
            return cand.title() if cand.isascii() else cand

    return None


def detect_weather_time_scope(query: str) -> str:
    """Detects requested temporal horizon for weather: CURRENT, TOMORROW, NEXT_24_HOURS, or TODAY."""
    q = (query or "").lower()
    if re.search(r"\b(kal|tomorrow|कल)\b", q):
        return "TOMORROW"
    if re.search(r"\b(abhi|now|currently|right\s*now|इस\s*समय|अभी)\b", q):
        return "CURRENT"
    if re.search(r"\b(next\s*24|agle\s*24|अगले\s*24)\b", q):
        return "NEXT_24_HOURS"
    if re.search(r"\b(aaj|today|आज)\b", q):
        return "TODAY"
    return "TODAY"


def extract_entities(query: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Lightweight extraction of crops, location, and parameters from query and context.
    Enforces deterministic context precedence:
    1. Explicit entities extracted from CURRENT user message
    2. Previously established conversation entities (history)
    3. Request context / active field context / profile
    4. Ask clarification
    Explicit new topic/crop in current message overrides previous conversation context.
    """
    entities: Dict[str, Any] = {}
    q_lower = query.lower()

    # Tier 1: Current user message extraction
    for crop_name, pat in CROPS_PATTERNS.items():
        if re.search(pat, q_lower):
            entities["crop"] = crop_name
            break

    age_match = re.search(r"\b(\d+)\s*(?:din|दिन|days?|day)\b", q_lower)
    if age_match:
        entities["crop_age_days"] = int(age_match.group(1))

    PEST_DISEASE_PATTERNS = {
        "pod borer": r"\b(pod\s*borer|heliothis|helicoverpa|फली\s*छेदक|चना\s*इल्ली|फली\s*सुंडी)\b",
        "yellow rust": r"\b(yellow\s*rust|stripe\s*rust|peela\s*ratua|पीला\s*रतुआ)\b",
        "leaf curl": r"\b(leaf\s*curl|murda|leaf\s*curl\s*virus|पर्ण\s*कुंचन)\b",
        "whitefly": r"\b(whitefly|white\s*fly|सफेद\s*मक्खी)\b",
        "stem borer": r"\b(stem\s*borer|तना\s*छेदक)\b",
        "aphid": r"\b(aphids?|maahu|माहू|मोयला)\b",
        "fall armyworm": r"\b(fall\s*armyworm|faw|सैनिक\s*कीट)\b",
        "late blight": r"\b(late\s*blight|jhulsa|झुलसा|पछेती\s*झुलसा)\b",
        "early blight": r"\b(early\s*blight|अगेती\s*झुलसा)\b"
    }
    for t_name, t_pat in PEST_DISEASE_PATTERNS.items():
        if re.search(t_pat, q_lower):
            entities["pest_disease"] = t_name
            break

    # Tier 2: Previously established entities in conversation history (single reverse pass)
    if context and context.get("history") and not (entities.get("crop") and entities.get("crop_age_days") and entities.get("pest_disease")):
        history = context.get("history")
        if isinstance(history, list):
            for turn in reversed(history):
                if isinstance(turn, dict):
                    msg_text = (turn.get("content") or turn.get("message") or "").lower()
                    if not entities.get("crop"):
                        for crop_name, pat in CROPS_PATTERNS.items():
                            if re.search(pat, msg_text):
                                entities["crop"] = crop_name
                                break
                    if not entities.get("crop_age_days"):
                        m = re.search(r"\b(\d+)\s*(?:din|दिन|days?|day)\b", msg_text)
                        if m:
                            entities["crop_age_days"] = int(m.group(1))
                    if not entities.get("pest_disease"):
                        for t_name, t_pat in PEST_DISEASE_PATTERNS.items():
                            if re.search(t_pat, msg_text):
                                entities["pest_disease"] = t_name
                                break
                    if entities.get("crop") and entities.get("crop_age_days") and entities.get("pest_disease"):
                        break

    # Tier 3: Request context / active field context fallback for crop
    if not entities.get("crop") and context:
        entities["crop"] = context.get("crop") or context.get("field_crop") or context.get("active_crop")

    # Tier 1: Explicit location extracted from CURRENT user message
    loc = extract_location_from_text(query)

    # Tier 2: Explicit location established in current conversation (history)
    if not loc and context and context.get("history"):
        history = context.get("history")
        if isinstance(history, list):
            for turn in reversed(history):
                if isinstance(turn, dict):
                    role = turn.get("role") or turn.get("sender") or ""
                    if role in ("user", "farmer", ""):
                        msg_text = turn.get("content") or turn.get("message") or ""
                        cand_loc = extract_location_from_text(msg_text)
                        if cand_loc:
                            loc = cand_loc
                            break

    # Tier 3: Request context / active field context
    if not loc and context:
        loc = (
            context.get("location")
            or context.get("field_location")
            or context.get("active_location")
            or context.get("active_field_location")
        )

    # Tier 4: User / farm profile location
    if not loc and context:
        loc = (
            context.get("farm_location")
            or context.get("profile_location")
            or context.get("user_location")
        )

    # Tier 5: None if not available
    if loc:
        entities["location"] = str(loc).strip()

    # Detect pH value if present
    ph_match = re.search(r"\bph\s*(?:is|hai|का मान)?\s*([0-9]+(?:\.[0-9]+)?)", q_lower)
    if ph_match:
        try:
            entities["ph"] = float(ph_match.group(1))
        except ValueError:
            pass

    # Temporal weather horizon detection (CURRENT, TOMORROW, NEXT_24_HOURS, TODAY)
    entities["time_scope"] = detect_weather_time_scope(query)

    return entities



# -----------------------------------------------------------------------------
# Main Routing Classifier
# -----------------------------------------------------------------------------
def classify_query(
    message: str,
    context: Optional[Dict[str, Any]] = None
) -> RouteDecision:
    """
    Evaluates incoming query against strict priority order:
    1. Gibberish Detection
    2. Prompt Injection Neutralization
    3. Pesticide Chemical Safety Refusal
    4. Non-Agricultural Scope Refusal
    5. Weather & Meteorological Routing
    6. Financial (Market Prices, PMFBY, Schemes)
    7. Soil Health & Testing
    8. Fertilizer & Plant Nutrition
    9. Crop Calendar & Stages
    10. General Agriculture (RAG)
    """
    clean_msg = (message or "").strip()
    q_lower = clean_msg.lower()
    entities = extract_entities(clean_msg, context)

    # 1. Gibberish Detection
    if is_gibberish(clean_msg):
        logger.info(f"SMART_RAG route=UNSUPPORTED action=SAFE_REFUSAL confidence=0.99 reason=gibberish")
        return RouteDecision(
            intent=Intent.UNSUPPORTED,
            confidence=0.99,
            action=RouteAction.SAFE_REFUSAL,
            reason="Meaningless or gibberish input detected.",
            safety_level="out_of_scope",
            service=None,
            detected_entities=entities
        )

    # 2. Prompt Injection Resistance (Ensure injection doesn't bypass safety)
    has_injection = any(re.search(p, q_lower) for p in PROMPT_INJECTION_PATTERNS)

    # 3. Pesticide Chemical Safety & Refusal (Top safety priority)
    # Fertilizer dose questions must not trigger pesticide refusal solely because of the word "dose"
    is_pure_fertilizer = bool(re.search(
        r"\b(urea|dap|npk|potash|khad|fertilizer|fertilizers|gypsum|zinc sulphate|organic manure|compost|यूरिया|डीएपी|खाद|उर्वरक|जिप्सम|पोटाश)\b",
        q_lower
    ))
    has_chemical_hazard_term = bool(re.search(
        r"\b(pesticide|insecticide|fungicide|herbicide|chemical|dawa|dawai|celphos|sulphas|quickphos|aluminium phosphide|कीटनाशक|रसायन|खरपतवारनाशक|फफूंदनाशक|सल्फास|सेलफॉस|सल्फॉस)\b",
        q_lower
    ))

    is_pesticide_hazard = any(re.search(p, q_lower) for p in PESTICIDE_SAFETY_PATTERNS)
    if is_pure_fertilizer and not has_chemical_hazard_term:
        is_pesticide_hazard = False

    if is_pesticide_hazard:
        logger.warning(f"SMART_RAG route=PESTICIDE_REFUSAL action=SAFE_REFUSAL confidence=0.98 reason=chemical_safety")
        return RouteDecision(
            intent=Intent.PESTICIDE_REFUSAL,
            confidence=0.98,
            action=RouteAction.SAFE_REFUSAL,
            reason="Query requests exact chemical dosage, mixing ratios, or high-risk pesticide application.",
            safety_level="critical_refusal",
            service=None,
            detected_entities=entities
        )

    # If prompt injection detected without chemical hazard, treat as unsupported
    if has_injection:
        logger.warning(f"SMART_RAG route=UNSUPPORTED action=SAFE_REFUSAL confidence=0.95 reason=prompt_injection")
        return RouteDecision(
            intent=Intent.UNSUPPORTED,
            confidence=0.95,
            action=RouteAction.SAFE_REFUSAL,
            reason="Prompt injection instruction detected attempting to bypass system rules.",
            safety_level="critical_refusal",
            service=None,
            detected_entities=entities
        )

    # 4. Non-Agricultural Out-of-Domain Detection
    if is_non_agricultural_query(clean_msg):
        logger.info(f"SMART_RAG route=UNSUPPORTED action=SAFE_REFUSAL confidence=0.96 reason=non_agricultural")
        return RouteDecision(
            intent=Intent.UNSUPPORTED,
            confidence=0.96,
            action=RouteAction.SAFE_REFUSAL,
            reason="Question is outside agricultural scope and MAITTRI capabilities.",
            safety_level="out_of_scope",
            service=None,
            detected_entities=entities
        )

    # 5. Weather Query Detection
    is_weather = any(re.search(p, q_lower) for p in WEATHER_PATTERNS)
    if is_weather:
        # Check if query is a static agronomic contingency / precaution question rather than live weather telemetry
        is_static_advisory = (
            any(w in q_lower for w in [
                "pala se bachav", "pala se bachaav", "frost protection", "frost injury",
                "पाले से बचाव", "heatwave precaution", "तापमान आवश्यकता", "temperature requirement",
                "delayed monsoon", "contingency plan", "monsoon is delayed", "monsoon delayed",
                "chilling hours", "चिलिंग"
            ])
            and not any(re.search(pat, q_lower) for pat in [r"\baaj\b", r"\btoday\b", r"\bcurrent\b", r"\blive\b", r"\bnow\b", r"\bkal\b", r"\btomorrow\b"])
        )

        if is_static_advisory:
            logger.info(f"SMART_RAG route=WEATHER action=RAG confidence=0.92 reason=static_climate_advisory")
            return RouteDecision(
                intent=Intent.WEATHER,
                confidence=0.92,
                action=RouteAction.RAG,
                reason="Static agro-climatic contingency, frost/heatwave precaution, or temperature threshold advisory.",
                safety_level="normal",
                service="kb",
                detected_entities=entities
            )

        # Check for explicit live weather / forecast intent
        live_weather_markers = [
            r"\bkal\b", r"\bba+rish\b", r"\bbarsat\b", r"\bbarsaat\b", r"वर्षा", r"\bweather\b", r"मौसम", r"\bmausam\b", r"\brain\b",
            r"\bforecast\b", r"\btomorrow\b", r"\btoday\b", r"\baaj\b", r"\ba+bhi\b", r"अभी", r"\bnow\b", r"\bspray\b",
            r"होगी", r"रहेगा", r"sambhavna", r"संभावना", r"rhi\s+hai", r"rahi\s+hai",
            r"current", r"live", r"according", r"hisaab", r"hisab"
        ]
        if any(re.search(pat, q_lower) for pat in live_weather_markers):
            has_location = bool(entities.get("location"))
            if not has_location:
                logger.info(f"SMART_RAG route=WEATHER action=ASK_FOR_CONTEXT confidence=0.93 reason=missing_location")
                return RouteDecision(
                    intent=Intent.WEATHER,
                    confidence=0.93,
                    action=RouteAction.ASK_FOR_CONTEXT,
                    reason="Weather forecast requested without farm location context.",
                    safety_level="normal",
                    required_context=["location"],
                    service="weather",
                    detected_entities=entities
                )
            else:
                logger.info(f"SMART_RAG route=WEATHER action=WEATHER_SERVICE confidence=0.95 reason=live_weather")
                return RouteDecision(
                    intent=Intent.WEATHER,
                    confidence=0.95,
                    action=RouteAction.WEATHER_SERVICE,
                    reason="Live weather forecast / meteorological advisory requested.",
                    safety_level="normal",
                    service="weather",
                    detected_entities=entities
                )

    # 6. Financial & Market Query Detection (Mandi Prices, MSP, PMFBY, Schemes)
    is_mandi = any(re.search(p, q_lower) for p in MANDI_PATTERNS) or bool(
        re.search(r"\b(mandi|bazaar|market|apmc|agmarknet|enam|मंडी|बाज़ार)\b", q_lower) and
        re.search(r"\b(bhav|rate|price|rates|prices|modal|bazaar|daam|dam|भाव|रेट|दाम)\b", q_lower)
    )
    is_insurance_or_scheme = any(re.search(p, q_lower) for p in INSURANCE_SCHEMES_PATTERNS)

    if is_mandi:
        logger.info(f"SMART_RAG route=MARKET action=MARKET_SERVICE confidence=0.95 reason=live_market_price")
        return RouteDecision(
            intent=Intent.MARKET,
            confidence=0.95,
            action=RouteAction.MARKET_SERVICE,
            reason="Live mandi / market price requested.",
            safety_level="normal",
            service="market",
            detected_entities=entities
        )

    if is_insurance_or_scheme:
        # If calculation is explicitly requested, always use deterministic insurance service
        is_calculation = bool(re.search(r"\b(calculate|premium calculate|प्रीमियम निकालो|गणना|calculate karo)\b", q_lower))

        # Check if explicit freshness query regarding policy, scheme updates, or procurement rules
        freshness_demanded = is_freshness_query(clean_msg)
        is_policy_or_procurement_update = bool(re.search(
            r"(procurement|खरीद|update|naya|naye|nai|nayi|नई|नए|नया|new|latest|recent|2026|rule|rules|नियम|गाइडलाइन|guidelines?|taaza|taza|अपडेट)",
            q_lower
        ))

        # Explicit policy/scheme/procurement freshness query -> WEB_SEARCH
        if not is_calculation and freshness_demanded:
            logger.info(f"SMART_RAG route=FINANCIAL action=WEB_SEARCH confidence=0.95 reason=freshness_scheme_policy")
            return RouteDecision(
                intent=Intent.FINANCIAL,
                confidence=0.95,
                action=RouteAction.WEB_SEARCH,
                reason="Latest agricultural scheme announcement, policy update, or procurement rules requested.",
                safety_level="normal",
                service="web_search",
                detected_entities=entities
            )

        service_target = "insurance" if "bima" in q_lower or "pmfby" in q_lower or "insurance" in q_lower else "schemes"
        logger.info(f"SMART_RAG route=FINANCIAL action=FINANCIAL_SERVICE confidence=0.94 target={service_target}")
        return RouteDecision(
            intent=Intent.FINANCIAL,
            confidence=0.94,
            action=RouteAction.FINANCIAL_SERVICE,
            reason=f"Agricultural economic / financial query targeting {service_target} service.",
            safety_level="normal",
            service=service_target,
            detected_entities=entities
        )

    # 7. Soil Health & Nutrient Query Detection
    is_soil = any(re.search(p, q_lower) for p in SOIL_PATTERNS)
    if is_soil:
        logger.info(f"SMART_RAG route=SOIL action=SOIL_SERVICE confidence=0.91")
        return RouteDecision(
            intent=Intent.SOIL,
            confidence=0.91,
            action=RouteAction.SOIL_SERVICE,
            reason="Soil health, pH value interpretation, or soil testing query.",
            safety_level="normal",
            service="soil",
            detected_entities=entities
        )

    # 8. Fertilizer & Plant Nutrition Query Detection
    is_fertilizer = any(re.search(p, q_lower) for p in FERTILIZER_PATTERNS)
    if is_fertilizer:
        logger.info(f"SMART_RAG route=FERTILIZER action=FERTILIZER_SERVICE confidence=0.92")
        return RouteDecision(
            intent=Intent.FERTILIZER,
            confidence=0.92,
            action=RouteAction.FERTILIZER_SERVICE,
            reason="Fertilizer schedule, nutrient deficiency, or application guidance query.",
            safety_level="normal",
            service="fertilizer",
            detected_entities=entities
        )

    # 9. Calendar / Sowing / Irrigation Stage Detection
    is_calendar = any(re.search(p, q_lower) for p in CALENDAR_PATTERNS)
    if is_calendar:
        logger.info(f"SMART_RAG route=CALENDAR action=CALENDAR_SERVICE confidence=0.90")
        return RouteDecision(
            intent=Intent.CALENDAR,
            confidence=0.90,
            action=RouteAction.CALENDAR_SERVICE,
            reason="Crop growth calendar, sowing date, or critical irrigation stage query.",
            safety_level="normal",
            service="calendar",
            detected_entities=entities
        )

    # 10. Explicit Freshness Advisory Query (Section 8 Case A)
    is_advisory_or_disease = bool(re.search(r"(advisory|सलाह|recommendation|सिफारिश|yellow rust|पीला रतुआ|disease|रोग|कीट|pest|outbreak|प्रकोप|alert|अलर्ट)", q_lower))
    if is_freshness_query(clean_msg) and is_advisory_or_disease:
        logger.info(f"SMART_RAG route=GENERAL action=WEB_SEARCH confidence=0.92 reason=freshness_advisory")
        return RouteDecision(
            intent=Intent.GENERAL,
            confidence=0.92,
            action=RouteAction.WEB_SEARCH,
            reason="Recent agricultural pest/disease advisory or official ICAR recommendation requested.",
            safety_level="normal",
            service="web_search",
            detected_entities=entities
        )

    # 10.5 Missing Crop Context for Vague Symptom / Diagnosis Queries (Clarification Gate)
    has_crop = bool(entities.get("crop"))
    is_vague_symptom = bool(re.search(
        r"(patte\s+(?:sukh|sukhe|pile|peele)|पत्ते\s+(?:सूख|पीले)|सड़\s*रहे|सूख\s*रहे|keeda|कीड़ा|बीमारी|रोग|bimari|rog|kharab|dawai\s+batao|dawa\s+chahiye)",
        q_lower
    )) and bool(re.search(
        r"(meri\s+fasal|hamari\s+fasal|fasal\s+me|khet\s+me|फसल\s+में|मेरी\s+फसल|पौधों\s+में|plants)",
        q_lower
    ))
    if is_vague_symptom and not has_crop:
        logger.info(f"SMART_RAG route=GENERAL action=ASK_FOR_CONTEXT confidence=0.90 reason=missing_crop_context")
        return RouteDecision(
            intent=Intent.GENERAL,
            confidence=0.90,
            action=RouteAction.ASK_FOR_CONTEXT,
            reason="Ambiguous crop symptom or disease diagnosis requested without crop identity.",
            safety_level="normal",
            required_context=["crop"],
            service="rag",
            detected_entities=entities
        )

    # 11. General Agricultural Query -> RAG Knowledge Base
    logger.info(f"SMART_RAG route=GENERAL action=RAG confidence=0.88")
    return RouteDecision(
        intent=Intent.GENERAL,
        confidence=0.88,
        action=RouteAction.RAG,
        reason="General agricultural production, pest/disease management, or agronomic practice query.",
        safety_level="normal",
        service="rag",
        detected_entities=entities
    )


# -----------------------------------------------------------------------------
# Response Composers for Deterministic / Safe Action Paths
# -----------------------------------------------------------------------------

def compose_pesticide_refusal_reply(language: str, entities: Dict[str, Any]) -> str:
    """
    Constructs an authoritative, non-hallucinatory IPM advisory complying with
    CIBRC and ICAR safety protocols. Strictly refuses exact chemical/tank dosing.
    """
    crop = entities.get("crop", "")
    crop_str = f" ({crop})" if crop else ""

    if language == "hi":
        return (
            f"⚠️ **सुरक्षा निर्देश एवं एकीकृत कीट प्रबंधन (IPM) परामर्श{crop_str}:**\n\n"
            "मैत्री सहायक सुरक्षा नियमों के तहत किसी भी रासायनिक कीटनाशक की मनमानी या दोगुनी खुराक की सिफारिश नहीं करता। गलत या अत्यधिक खुराक से फसल जलने, मित्र कीटों के नष्ट होने और विषाक्तता का गंभीर खतरा रहता है।\n\n"
            "🌱 **सुरक्षित एवं अनुशंसित उपाय:**\n"
            "1. **लेबल निर्देश:** केवल केंद्रीय कीटनाशक बोर्ड (CIBRC) द्वारा पंजीकृत कीटनाशक के आधिकारिक डिब्बे पर छपे प्रति एकड़ अनुशंसित अनुपात का ही पालन करें।\n"
            "2. **जैविक एवं यांत्रिक नियंत्रण:** फेरोमोन ट्रैप, लाइट ट्रैप और नीम तेल (1500 PPM @ 3-5 मिली/लीटर) का प्राथमिक उपयोग करें।\n"
            "3. **सुरक्षा सावधानी:** छिड़काव के समय मास्क, दस्ताने पहनें और हवा के रुख की विपरीत दिशा में कभी छिड़काव न करें।\n\n"
            "📞 **सत्यापित कृषि खुराक के लिए:** सही उत्पाद व खुराक की पुष्टि के लिए अपने निकटतम **कृषि विज्ञान केंद्र (KVK)** या ब्लॉक कृषि अधिकारी से संपर्क करें।\n\n"
            "🚨 **आपातकालीन चिकित्सा परामर्श (Medical Emergency):** यदि किसी ने गलती से कीटनाशक निगल लिया हो या तीव्र विषाक्तता/गंभीर लक्षण दिखें, तो चैटबॉट पर निर्भर न रहें — तुरंत नजदीकी अस्पताल जाएं या राष्ट्रीय आपात नंबर **112** / **108** पर कॉल करें। विशेषज्ञ विष नियंत्रण मार्गदर्शन के लिए **एम्स राष्ट्रीय विष सूचना केंद्र (AIIMS NPIC New Delhi)** के 24x7 टोल-फ्री नंबर **1800 116 117** पर संपर्क करें।"
        )
    elif language == "hinglish":
        return (
            f"⚠️ **Safety Directive & Integrated Pest Management (IPM){crop_str}:**\n\n"
            "Maitri safety policy ke mutabiq hum kisi chemical pesticide ki arbitrary ya double dosage suggest nahi karte. Overdose ya galat chemical mixing se crop burn hone aur beneficial insects destroy hone ka serious risk hota hai.\n\n"
            "🌱 **Safe Recommended Steps:**\n"
            "1. **Label Instructions:** Hamesha product bottle/box par printed CIBRC approved doses aur safety warnings follow karein.\n"
            "2. **IPM & Biological Control:** Pehle neem oil (1500 PPM @ 3-5 ml/L), pheromone traps, ya sticky traps ka use karein.\n"
            "3. **Safety Gear:** Spray karte samay hamesha mask aur gloves pehnein aur tej hawa me spray na karein.\n\n"
            "📞 **Exact dose confirmation ke liye:** Apne local **Krishi Vigyan Kendra (KVK)** ya Block Agriculture Officer se consult karein.\n\n"
            "🚨 **Medical Emergency Alert:** Agar galti se pesticide nigal liya ho ya acute poisoning/chhati me jalan ke lakshan dikhein, turant nearest hospital jayein ya emergency number **112** / **108** par call karein. Clinical poison guidance ke liye **AIIMS National Poisons Information Centre (NPIC)** ke 24x7 toll-free helpline **1800 116 117** par contact karein."
        )
    else:
        return (
            f"⚠️ **Safety Advisory & Integrated Pest Management (IPM){crop_str}:**\n\n"
            "MAITTRI safety protocols strictly prohibit recommending unverified chemical tank dosages, arbitrary concentrations, or dual chemical mixtures. Overdosing risks severe phytotoxicity, beneficial insect mortality, and pesticide resistance.\n\n"
            "🌱 **Safe Recommended Actions:**\n"
            "1. **Follow Label Instructions:** Strictly adhere to the CIBRC-registered label dosage and pre-harvest interval (PHI) specified on the container.\n"
            "2. **Integrated Control:** Prioritize cultural/mechanical measures, pheromone/yellow sticky traps, and neem-based formulations (1500 PPM @ 3–5 ml/L).\n"
            "3. **Protective Equipment:** Always wear protective eyewear, mask, and gloves; never spray against the wind.\n\n"
            "📞 **For verified field dosage:** Please consult your local **Krishi Vigyan Kendra (KVK)** or District Agricultural Extension Officer.\n\n"
            "🚨 **Medical Emergency Directive:** In case of accidental pesticide ingestion, inhalation, or acute chemical exposure, do NOT treat this as an agricultural chatbot inquiry. Seek immediate emergency medical care at the nearest hospital or dial National Emergency **112** / Ambulance **108**. For specialized clinical poison consultation, contact the **National Poisons Information Centre (NPIC), AIIMS New Delhi** at Toll-Free: **1800 116 117** (24x7, Verified: aiims.edu)."
        )


def compose_missing_context_reply(intent: Intent, required_context: List[str], language: str) -> str:
    """Prompts the farmer politely for required context when it cannot be inferred."""
    if "location" in required_context:
        if language == "hi":
            return (
                "🌦️ **स्थान की जानकारी आवश्यक है:**\n\n"
                "सटीक मौसम पूर्वानुमान और वर्षा सलाह देने के लिए कृपया अपने **जिले या गांव का नाम** बताएं (उदा. 'करनाल, हरियाणा' या 'लखनऊ')।\n"
                "आप मैत्री पोर्टल के 'Weather Advisory' टैब में भी लाइव पूर्वानुमान देख सकते हैं।"
            )
        elif language == "hinglish":
            return (
                "🌦️ **Location details required:**\n\n"
                "Accurate live weather aur rainfall forecast ke liye kripya apna **district ya state** batayein (jaise 'Karnal, Haryana' ya 'Meerut, UP').\n"
                "Aap Maitri platform ke 'Weather Advisory' section me bhi apne area ka forecast check kar sakte hain."
            )
        else:
            return (
                "🌦️ **Location context required:**\n\n"
                "To provide an accurate hyper-local weather forecast and spraying advisory, please specify your **district or state** (e.g. 'Karnal, Haryana' or 'Indore, MP').\n"
                "You can also view the live forecast directly in the 'Weather Advisory' dashboard."
            )

    if language == "hi":
        return (
            "नमस्ते! सटीक परामर्श देने के लिए कृपया अपनी फसल का नाम, विकास अवस्था (दिन) और जिले की जानकारी साझा करें।"
        )
    elif language == "hinglish":
        return (
            "Namaste! Accurate advice ke liye kripya apni crop ka naam, crop stage aur district batayein."
        )
    else:
        return (
            "Hello! To give you a precise advisory, please specify your crop name, crop growth stage, and district."
        )


def compose_unsupported_reply(language: str, is_gibberish_input: bool = False) -> str:
    """Polite refusal for out-of-domain or gibberish input."""
    if is_gibberish_input:
        if language == "hi":
            return (
                "नमस्ते! आपका संदेश स्पष्ट नहीं समझ आया।\n"
                "कृपया खेती, फसल, मिट्टी, मौसम, सिंचाई या सरकारी योजनाओं से जुड़ा कोई स्पष्ट प्रश्न लिखें।"
            )
        elif language == "hinglish":
            return (
                "Namaste! Aapka message samajh nahi aaya.\n"
                "Kripya farming, crop, mitti, mausam ya government schemes se juda clear sawal puchein."
            )
        else:
            return (
                "Hello! We could not understand your message.\n"
                "Please enter a clear farming question regarding crops, soil health, weather, irrigation, pests, or agricultural schemes."
            )

    if language == "hi":
        return (
            "नमस्ते! मैं **मैत्री कृषि सहायक (MAITTRI Krishi Assistant)** हूँ।\n\n"
            "मैं केवल भारतीय कृषि, फसलों, मृदा स्वास्थ्य, कीट-रोग प्रबंधन, सिंचाई, मौसम, मंडी भाव और सरकारी कृषि योजनाओं से जुड़े सवालों में आपकी सहायता कर सकता हूँ।\n"
            "कृपया खेती से संबंधित प्रश्न पूछें।"
        )
    elif language == "hinglish":
        return (
            "Namaste! Main **Maitri Krishi Assistant** hoon.\n\n"
            "Main sirf agriculture, fasal, mitti ki janch, keede-rog, sinchai, mausam, mandi bhav aur government farming schemes se jude sawalo me help kar sakta hoon.\n"
            "Kripya kheti se sambandhit sawal puchein."
        )
    else:
        return (
            "Hello! I am **Maitri Krishi Assistant**, dedicated specifically to Indian agriculture.\n\n"
            "I can assist you with crops, soil health, fertilizer scheduling, pest & disease management, weather advisories, market prices, and government farming schemes.\n"
            "Please ask an agricultural or farming-related question."
        )


def compose_web_evidence_unavailable_reply(language: str) -> str:
    """Honest disclosure when live web search produces insufficient reliable evidence."""
    if language == "hi":
        return (
            "क्षमा करें, इस विषय पर वर्तमान में आधिकारिक अथवा प्रामाणिक वेब स्रोत से पर्याप्त सत्यापित जानकारी नहीं मिल सकी।\n\n"
            "गलत या अपुष्ट जानकारी से बचने के लिए, कृपया सीधे संबंधित सरकारी पोर्टल या अपने निकटतम कृषि विज्ञान केंद्र (KVK) से संपर्क करें।"
        )
    elif language == "hinglish":
        return (
            "Sorry, is topic par currently official ya verified web sources se reliable information nahi mil saki.\n\n"
            "Ungrounded information se bachne ke liye, kripya related government portal ya apne local Krishi Vigyan Kendra (KVK) se confirm karein."
        )
    else:
        return (
            "I couldn't verify sufficiently reliable current information right now.\n\n"
            "To avoid ungrounded guidance, please consult the official agricultural portal or your local Krishi Vigyan Kendra (KVK)."
        )
