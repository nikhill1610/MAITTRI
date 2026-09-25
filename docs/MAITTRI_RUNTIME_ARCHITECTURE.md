# MAITTRI Runtime Architecture Specification

**Document Version**: 1.0.0  
**Status**: APPROVED & ACTIVE  
**Last Verified**: 2026-09-22  
**System**: MAITTRI (Maitri Agricultural Intelligence & Trustworthy Technology for Rural India)

---

## 1. End-to-End System Data Flow

The MAITTRI platform implements a zero-trust, multi-tiered AI RAG pipeline designed specifically for rural agricultural advisory in India:

```
[Farmer User / Web Frontend]
       │
       ▼ (HTTP POST /api/chat {message, context, history})
[FastAPI Gateway / Chat Route (backend/app/routes/chat.py)]
       │
       ▼
[Chat Orchestration Service (backend/app/services/chat_service.py)]
       │
       ├────────────────────────────────────────────────────────┐
       ▼                                                        ▼
[Smart RAG Router (smart_rag_router.py)]              [Multi-turn Context Extraction]
 - Language Detection (Hindi, Hinglish, English)      - Carries forward: Crop, Location, Stage
 - Entity Extraction (Crop, Stage, Disease, Pest)     - History tracking (last 5 turns)
 - Intent Classification (10 Agricultural Categories)
 - Prompt Injection & Security Guardrails
 - High-risk Chemical Safety Screening (CIBRC / RUP)
       │
       ▼
[Route Decision: RouteAction]
 ├── SAFE_REFUSAL   ────────> [Response Composer: compose_pesticide_refusal_reply / NPIC AIIMS]
 ├── PROMPT_CONTEXT ────────> [Context Clarification: compose_missing_context_reply]
 ├── LIVE_SERVICE   ────────> [Anti-hallucination Interceptor / Mandi & Weather Routers]
 ├── SEARCH_FALLBACK ───────> [Web Search Service: Trusted Domain Tiering (.gov.in / .edu)]
 └── RAG_RETRIEVE   ────────> [Knowledge Base Vector Retrieval (rag_service.py)]
                                  │
                                  ▼
                              [ChromaDB Vector Store (backend/vector_store)]
                              - Collection: 'maitri_krishi_kb' (559 chunks)
                              - Embeddings: all-MiniLM-L6-v2 (384-dim, cosine)
                              - Metadata filters: Crop, State, Category
                                  │
                                  ▼
                              [Reranker & Provenance Formatter]
                              - Reciprocal rank fusion & crop-boosting
                              - Deduplication & low-confidence thresholding
                                  │
                                  ▼
                              [LLM Generation & Grounding Engine]
                              - Primary: OpenRouter / Free tier
                              - Fallback: Local grounded synthesis
                              - Strict citation enforcement & 7-factor provenance
                                  │
                                  ▼
[Standardized Response Payload {reply, sources, confidence, intent, route}]
       │
       ▼
[Frontend React App (frontend/src/KrishiAssistantPage.jsx)]
 - Markdown rendering & vernacular Devanagari typography
 - Source citation chips & institutional trust badges
 - Emergency poison helpline & KCC callout cards
```

---

## 2. Component Specifications

### 2.1 API & Ingress Layer
- **Endpoint**: `POST /api/chat`
- **Payload Schema**: `ChatMessageRequest`
  - `message`: User input string (1 to 2000 characters).
  - `context`: Optional dictionary containing farm state (`crop`, `location`, `stage`).
  - `history`: Optional array of previous dialogue turns (`role`, `content`).
- **Response Schema**: `ChatMessageResponse`
  - `reply`: Markdown formatted response.
  - `sources`: Array of citation objects with `title`, `source`, `source_type`, `url`, `score`.
  - `retrieved_chunks`: Integer count of context chunks injected.
  - `confidence`: Semantic similarity score (0.0 to 1.0).
  - `intent`: Classified intent category.
  - `route`: Architectural action route.

### 2.2 Smart RAG Router (`smart_rag_router.py`)
- **Intent Taxonomy**:
  1. `PESTICIDE_REFUSAL`: Chemical overdose, tank mixing, or restricted fumigant requests.
  2. `WEATHER`: Weather forecasts, rainfall alerts, heatwave/frost precautions.
  3. `FINANCIAL`: Mandi prices, MSP, PM-KISAN, PMFBY insurance.
  4. `SOIL_HEALTH`: Soil testing, pH, salinity, organic carbon.
  5. `FERTILIZER`: Basal DAP, top-dressing urea, micronutrients (Zn/Fe).
  6. `IRRIGATION`: AWD, drip irrigation, critical crop stages (e.g. CRI in wheat).
  7. `UNSUPPORTED`: Out-of-domain (programming, quantum physics), gibberish, prompt injection.
  8. `GENERAL`: Core agronomic disease, pest, weed, storage, and crop management.
- **Safety Interceptors**:
  - `PESTICIDE_SAFETY_PATTERNS`: Catches tank mixes, 2x/4x doses, and domestic fumigants.
  - Returns `RouteAction.SAFE_REFUSAL` with official AIIMS NPIC `1800 116 117` emergency contact.

### 2.3 Retrieval Layer (`rag_service.py`)
- **Vector Client**: ChromaDB PersistentClient (`backend/vector_store`).
- **Collection Name**: `maitri_krishi_kb` (559 chunks).
- **Embedding Model**: `sentence-transformers/all-MiniLM-L6-v2` (384 dimensions).
- **Metric**: Cosine similarity (`score = 1.0 - distance`).
- **Metadata Filtering**: Dynamically filters on `crop` and `state` when detected with high confidence.
- **Deduplication**: Context chunks with identical normalized text or titles are pruned.

### 2.4 Response Generation & Resilience Layer
- **Prompt Architecture**: Strict system prompts enforcing ICAR/CIBRC compliance, forbidding invented pesticide dosages, and mandating source citation.
- **Resilience Fallback**: If OpenRouter or external LLM APIs fail (HTTP 429, timeout, network error), the system automatically triggers `grounded_local_rag`, synthesizing an advisory directly from top-ranked verified KB chunks.

### 2.5 Presentation Layer (`KrishiAssistantPage.jsx`)
- **Vernacular Rendering**: High-contrast, clean Devanagari Unicode rendering.
- **Institutional Badges**: Tier-A sources display verified badges (e.g., *ICAR-IARI*, *CIBRC*, *Govt of UP*).
- **Safety Callouts**: Dedicated visual cards for critical emergency contacts (AIIMS NPIC `1800 116 117` vs KCC `1800-180-1551`).
