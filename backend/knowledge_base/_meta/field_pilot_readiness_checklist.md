# MAITTRI — Operational Field Pilot Readiness Checklist

**Phase**: Pre-Deployment Operational Preparation (Stage 11)  
**Corpus Baseline**: `MAITTRI-KB-v1.0.0-RELEASE-FREEZE`  
**Governing Standard**: `backend/knowledge_base/_meta/pilot_metrics_and_governance.md`  
**Status**: ACTIVE CHECKLIST (Mandatory for Field Deployment)  

---

## 1. Pilot Participant Consent & Onboarding

- [ ] **Vernacular Informed Consent**: Obtain explicit oral or written consent in Hindi / regional dialect before onboarding farmer participants.
- [ ] **Advisory Scope Disclosure**: Inform participants that MAITTRI provides agronomic guidance and decision support based on ICAR / State Agriculture Department packages, but does not replace on-ground physical inspection by a certified agricultural extension officer.
- [ ] **Right to Withdraw**: Ensure participants understand they may withdraw from the pilot at any point without prejudice to their access to regular KVK services.

---

## 2. Privacy-Safe Telemetry & Logging

- [ ] **Zero PII Storage**: Ensure farmer phone numbers, Aadhaar numbers, and bank account numbers are scrubbed by `pilot_telemetry_schema.json` prior to ingestion into analytics logs.
- [ ] **Location Granularity Limitation**: Log geographic location strictly at district/block level (e.g. `district: "Barabanki", state: "Uttar Pradesh"`), never GPS coordinate points of specific farm plots.
- [ ] **Audit Trail**: Maintain hashed session identifiers (`session_id_hash`) with daily rotation to prevent user re-identification.

---

## 3. Evaluator Instructions & Field Protocols

- [ ] **Dual Evaluation Team**: Pair every field facilitator with a trained agricultural graduate (B.Sc. Ag / M.Sc. Ag) or KVK Subject Matter Specialist (SMS).
- [ ] **Objective Facilitation**: Facilitators must allow farmers to type or voice their natural, unscripted queries in their own dialect without prompting formal technical terminology.
- [ ] **Visual Symptom Verification**: When a farmer queries a disease symptom, the facilitator must cross-check the physical leaf/stem with reference photographs from the verified ICAR manuals.

---

## 4. Farmer Feedback Capture (CSAT & Likert Scale)

- [ ] **Structured Post-Interaction Rating**: Prompt farmer for a 1-to-5 star rating immediately following query resolution.
- [ ] **Qualitative Feedback Fields**:
  - *Did the answer understand your local crop variety?* (Yes / Partially / No)
  - *Was the recommendation feasible in your village market?* (Yes / No)
  - *Did the advisory prevent unnecessary chemical spraying?* (Yes / Not Applicable)
- [ ] **Grievance / Dissent Logging**: Dedicated audio memo option for farmers to register dissatisfaction or confusion.

---

## 5. Query Sampling & Quality Assurance

- [ ] **Stratified Sampling Quota**:
  - Small & Marginal Farmers ($<2\text{ hectares}$): Minimum 60% of total pilot query volume.
  - Commercial / Horticulture Farmers: 20%.
  - Allied Enterprise Farmers (Dairy, Poultry, Fisheries, Honey): 20%.
- [ ] **Linguistic Diversity**: Minimum 40% Hindi Devanagari, 40% Hinglish voice/text transcripts, 20% standard dialect inputs.
- [ ] **Daily Random Sample**: Daily random pull of 10% of all queries for dual blind review by the Agronomy Quality Desk.

---

## 6. Failure Escalation & Incident Triage

- [ ] **Classification Matrix**:
  - **SEV-1 (CRITICAL)**: Chemical dosage recommendation, hazardous pesticide encouragement, or toxic ingestion risk.
  - **SEV-2 (HIGH)**: Recommending a variety banned in the state or missing an active quarantine pest outbreak.
  - **SEV-3 (MEDIUM)**: Crop stage mismatch (e.g. recommending basal fertilizer at grain filling).
  - **SEV-4 (LOW)**: Minor typographical error or formatting layout defect.
- [ ] **Escalation Protocol**: SEV-1 incidents trigger an automated SMS alert to the Lead Agronomist within 15 minutes and automatically suspend the affected crop topic.

---

## 7. Critical Safety & Poisoning Incident Protocol

- [ ] **Immediate Medical Emergency Action (Do NOT treat via Chatbot)**:
  - In the event of accidental pesticide ingestion, inhalation, dermal splash, or acute toxic symptoms:
    - **Immediate Physical Action**: Transport victim immediately to the nearest Primary Health Centre (PHC), Community Health Centre (CHC), or District Hospital. Do not wait for symptoms to worsen.
    - **National Emergency Services**: Dial **112** (All-India Emergency Response Support System) or **108** / **102** (Ambulance).
- [ ] **Authoritative Poison Information Center**:
  - **Organization**: National Poisons Information Centre (NPIC), Department of Pharmacology, All India Institute of Medical Sciences (AIIMS), New Delhi.
  - **Official Verification Source**: `https://aiims.edu` & Ministry of Health and Family Welfare (MoHFW).
  - **Verification Date**: 2026-09-22.
  - **Toll-Free Emergency Number**: **1800 116 117** (Operational 24x7, 365 days).
  - **Direct Landlines**: `011-2658 9391`, `011-2659 3677`.
  - **Purpose**: Clinical toxicological guidance for healthcare personnel, first responders, and poisoning emergencies.
- [ ] **Agricultural Advisory (Non-Medical)**:
  - **Kisan Call Centre (KCC)**: **1800-180-1551** (Toll-free under Department of Agriculture & Farmers Welfare, 6:00 AM – 10:00 PM).
  - **Strict Clarification**: KCC is exclusively for agricultural agronomic advisory, crop management, and government schemes. It is **NOT** a medical emergency or poisons hotline.
- [ ] **Quarantine Sandbox**: Any document generating an unverified chemical dosage must be instantly disabled from the Chroma vector collection via metadata soft-delete.

---

## 8. Agronomist Review & Peer Review Sign-Off

- [ ] **Weekly Agronomy Board**: Convene weekly review between MAITTRI engineering leads and ICAR/KVK agronomists to review unresolved queue items.
- [ ] **Differential Diagnosis Sign-Off**: Mandatory physical sign-off on all "Murda Complex", "Yellowing", and "Wilting" clinical decisions before promoting advice to primary prompt.
- [ ] **Input Availability Validation**: Agronomists must verify that recommended bio-control agents (e.g., *Trichoderma*, *Pseudomonas fluorescens*, PICS bags) are physically in stock at district Agro-junctions or IFFCO centers.

---

## 9. Change-Control & Governance Workflow

- [ ] **Zero Unilateral Changes**: No developer or model engineer may edit knowledge base files without an approved `PILOT_CHANGELOG.md` entry.
- [ ] **Approved Change Types Only**: Changes restricted strictly to `CRITICAL_SAFETY`, `FACTUAL_CORRECTION`, `EVALUATION_FIX`, or `PILOT_REQUIREMENT`.
- [ ] **Regression Prerequisite**: Any modification must re-run the 55-item test suite (`pytest tests/`) and achieve 100% passage before redeployment.

---

## 10. Release Rollback Procedure

- [ ] **Versioned Checkpoints**: The current frozen baseline `MAITTRI-KB-v1.0.0-RELEASE-FREEZE` (Git commit `0d8bb25845741eddbe4993cb486a268d4ea476a5`) serves as the permanent golden restore point.
- [ ] **Rollback Execution**:
  ```bash
  git checkout 0d8bb25845741eddbe4993cb486a268d4ea476a5 -- backend/knowledge_base/
  python backend/scripts/ingest_knowledge.py --reindex
  pytest backend/tests/test_rag_trustworthy.py backend/tests/test_chat_rag.py backend/tests/test_smart_rag_router.py backend/tests/test_web_search_fallback.py
  ```
- [ ] **Mean Time to Recovery (MTTR)**: Rollback procedure must be capable of full restoration in $< 5\text{ minutes}$ in staging environments.
