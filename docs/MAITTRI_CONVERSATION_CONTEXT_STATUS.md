# MAITTRI Multi-Turn Conversation Context Status

**Document Version**: 1.0.0  
**Status**: VERIFIED (5/5 Automated Multi-turn Integration Tests Passed)  
**Verification Date**: 2026-09-22  
**System**: MAITTRI Conversational Memory & Context Tracking

---

## 1. Context Architecture

The MAITTRI backend maintains state across conversational turns using the `ChatMessageRequest.history` and `ChatMessageRequest.context` payloads:

```
[Turn 1: "gehun me pehli sinchai kab karein?"]
   │
   ▼
[Extracted Context: {crop: "Wheat", stage: "CRI", location: "Uttar Pradesh"}]
   │
   ▼
[Turn 2: "aur urea kitna daalna hai?"] (Context-deprived query)
   │
   ▼
[Merged Memory: {crop: "Wheat", intent: "FERTILIZER"}]
   │
   ▼
[Retrieval Target: Wheat Fertilizer / Urea Top-dressing Guide]
```

---

## 2. Automated Test Coverage & Verification Results

All 5 core multi-turn dialogue patterns were tested via `backend/scripts/verify_stage6_multiturn.py`:

| Test Case | Interaction Pattern | Turn 1 Prompt | Turn 2 Prompt | Expected Context Behavior | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Case 1** | Crop Context Carry-over | *"gehun me pehli sinchai kab karein?"* | *"aur urea kitna daalna hai?"* | Carries over `crop: Wheat` to fertilizer inquiry | **PASSED** |
| **Case 2** | Location Carry-over | *"Barabanki me mausam kaisa hai?"* | *"kal barish hogi?"* | Carries over `location: Barabanki` to weather service | **PASSED** |
| **Case 3** | Clarification -> Follow-up | *"patte pile pad rahe hain"* (Ambiguous) | *"tamatar ki fasal hai"* | Resolves ambiguous chlorosis to `crop: Tomato` | **PASSED** |
| **Case 4** | Topic / Crop Switching | *"sarson me maahu laga hai"* | *"ab aalu me jhulsa rog ke baare me batao"* | Replaces stale `Mustard` context with new `Potato` context | **PASSED** |
| **Case 5** | Vernacular Hindi Follow-up | *"धान में सिंचाई का सही समय क्या है?"* | *"और खाद कब देनी चाहिए?"* | Carries over `धान (Rice)` context in Hindi dialogue | **PASSED** |

---

## 3. Resilience & Stale Context Expiry

1. **Explicit Override Priority**: When the farmer introduces a new crop in Turn 2 (e.g. *"ab aalu me..."*), the router immediately clears preceding crop entities (`Mustard`), preventing context cross-contamination.
2. **History Window**: Default history processing retains the last 5 dialogue turns to optimize prompt token budgets while preserving conversational coherence.
3. **Local Grounded Synthesis**: Multi-turn dialogue functions robustly even when external LLM APIs experience rate limits (HTTP 429), synthesizing grounded responses from retrieved context.
