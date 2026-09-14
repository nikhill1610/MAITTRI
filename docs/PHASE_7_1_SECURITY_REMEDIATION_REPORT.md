# PHASE 7.1 — SECURITY REMEDIATION & HARDENING REPORT
**MAITRI Smart Agriculture AI Platform**  
**Date:** September 14, 2026  
**Status:** REMEDIATED & VERIFIED  

---

## 1. Initial Findings

During the full security and production readiness audit of the MAITRI backend, the following architectural vulnerabilities and risk patterns were identified:

1. **Dual JWT Fallback to Admin Client:** In `backend/app/deps.py`, the token verification routine fell back to `get_supabase_admin_client()` when `SUPABASE_ANON_KEY` was absent. This violated the principle of least privilege by invoking `service_role` credentials for public user token validation.
2. **Missing Farm Ownership on Personal Planner Routes:** Multiple endpoints in `backend/app/routes/farmer_planning.py` accepted `Depends(get_optional_current_user)`. When callers omitted authorization headers (`user is None`), tenant ownership checks were bypassed, allowing unauthorized plan generation and viewing of all farmers' plans.
3. **IDOR on Soil Test and Service Request Bookings:** `POST /api/soil-tests` and `POST /api/service-requests` allowed authenticated farmers to supply any arbitrary `farmer_id` without verifying that the requesting identity owned the target farmer record.
4. **Unauthenticated Farm-Scoped Calculations:** In `backend/app/routes/fertilizer.py` and `backend/app/routes/parali.py`, endpoints accepted `farm_id` but did not require authentication, allowing callers to inspect soil chemical profiles and field parameters without authorization.
5. **Global IoT Reading in Farm Brain:** In `backend/app/routes/farm_brain.py`, the latest sensor telemetry was retrieved globally across all devices without filtering by `farm_id` or owner device IDs.
6. **Hardware Configuration Exposure:** `GET /api/iot/config` returned internal host LAN IP addresses in production, while `POST /api/iot/config` lacked role checks to prevent registered farmers from altering hardware threshold calibrations.
7. **Production Debug & Simulation Endpoints:** Endpoints `/api/chat/debug`, `/api/iot/simulate`, and `/api/iot/lan-info` were not strictly restricted or disabled by default in production.

---

## 2. Severity Classification

| Vulnerability / Risk | Severity | Impact | Status |
|---|---|---|---|
| Service-role client fallback for user token verification | **P0 (Critical)** | Potential credential leak / privilege escalation | **Remediated** |
| Farm planner tenant bypass when unauthenticated | **P0 (Critical)** | Multi-tenant data leakage / IDOR | **Remediated** |
| Soil test booking for arbitrary farmer ID | **P1 (High)** | Impersonation / resource tampering | **Remediated** |
| Service request booking for arbitrary farmer ID | **P1 (High)** | Impersonation / grievance manipulation | **Remediated** |
| Farm-scoped fertilizer/parali analysis unauthenticated | **P1 (High)** | Confidential farm agronomic data leak | **Remediated** |
| Cross-tenant IoT sensor reading in Farm Brain | **P1 (High)** | Inaccurate advisory & data leakage | **Remediated** |
| Hardware configuration & internal LAN IP exposure | **P1 (High)** | Network reconnaissance & unauthorized config | **Remediated** |
| Debug & Simulation endpoints active in production | **P1 (High)** | Internal prompt and chunk metadata leakage | **Remediated** |

---

## 3. Files Affected

* `backend/app/deps.py`
* `backend/app/security.py`
* `backend/app/supabase_client.py`
* `backend/app/routes/farmer_planning.py`
* `backend/app/routes/soil_tests.py`
* `backend/app/routes/service_requests.py`
* `backend/app/routes/fertilizer.py`
* `backend/app/routes/parali.py`
* `backend/app/routes/farm_brain.py`
* `backend/app/routes/iot.py`
* `backend/app/routes/chat.py`
* `backend/.env.example`
* `.env.example`
* `backend/tests/test_production_security_hardening.py` (New)
* `backend/tests/test_embedding_parity.py` (New)

---

## 4. Changes Made

1. **Authentication Strictness (`deps.py`):**
   * Removed fallback to `get_supabase_admin_client()` from `_resolve_user_from_token`.
   * Ensured user verification uses strictly `get_supabase_anon_client()` for Supabase Auth JWTs and `SECRET_KEY` with HS256 for local MAITRI JWTs.
   * Enhanced `auth.users` database lookup to check primary key `id = :sub` (UUID) in addition to email lookup.
2. **Farm Planner Hardening (`farmer_planning.py`):**
   * Replaced `get_optional_current_user` with `get_current_user` across all plan creation, retrieval, listing, milestone updating, and farm diary routes.
   * Enforced strict ownership checks: `farm.user_id == user.id` or elevated role (`AUTHORIZED_OPERATOR`, `ADMIN`).
3. **Soil Tests & Service Requests IDOR Remediation (`soil_tests.py`, `service_requests.py`):**
   * Added server-side validation on `POST /api/soil-tests` and `POST /api/service-requests` verifying that `farmer.user_id == current_user.id` or role is operator/admin.
4. **Fertilizer & Parali Farm-Scoped Protection (`fertilizer.py`, `parali.py`):**
   * Enforced that whenever a `farm_id` is supplied in `analyze`, `recommend`, `history`, or `log` endpoints, the request must be authenticated and the caller must own the farm or possess operator privileges.
5. **IoT Sensor Scope in Farm Brain (`farm_brain.py`):**
   * Filtered `IoTSensorReading` queries by devices specifically registered and assigned to `farm.id`. Returns `None` if no physical hardware is linked.
6. **IoT Hardware Configuration & Debug Protection (`iot.py`, `chat.py`):**
   * Updated `GET /api/iot/config` to omit host LAN IPs in production.
   * Protected `POST /api/iot/config` to forbid normal farmers from modifying operator sensor thresholds.
   * Retained strict 403 Forbidden rejection for `/api/chat/debug`, `/api/iot/simulate`, and `/api/iot/lan-info` in production.

---

## 5. Security Reasoning

* **Least Privilege:** Public users authenticating via tokens must never cause the server to instantiate or query through high-privilege service-role credentials.
* **Fail-Closed Authorization:** Every endpoint that accepts an entity ID (`farm_id`, `farmer_id`, `plan_id`, `req_id`) must require an active user session and verify ownership before retrieving or updating the corresponding database row.
* **Separation of Indicative and Certified Data:** IoT readings are indicative and scoped strictly to owned hardware; certified laboratory soil tests require operator submission and cannot be forged by arbitrary users.

---

## 6. Tests Added

1. `backend/tests/test_production_security_hardening.py` (27 dedicated automated security test cases):
   * Forged JWT rejected (401)
   * Modified JWT rejected (401)
   * Expired JWT rejected (401)
   * Missing sub claim rejected (401)
   * Farmer cross-farm read blocked (403/404)
   * Farmer cross-farm update blocked (403/404)
   * Farmer cross-plan read blocked (403)
   * Farmer cross-document download blocked (403)
   * Farmer cross-soil-test read blocked (403)
   * Farmer soil-test status update blocked (403)
   * Farmer soil-test lab report submission blocked (403)
   * Farmer cross-service-request update blocked (403)
   * Farmer cross-preference modification blocked (403)
   * Farmer SMS broadcast blocked (403)
   * Farmer operator-dashboard access blocked (403)
   * Chat debug endpoint disabled in production (403)
   * IoT simulation & LAN info disabled in production (403)
   * IoT hardware token spoofing rejected (403)
   * IoT telemetry aliases require valid device token (401/403)
   * Service-role key never exposed in API payloads
   * Anon client never falls back to service role
   * Database failure path returns clean 503 without crashing
   * SQLite prohibited in production runtime
   * ChromaDB bypassed in production runtime
   * Supabase pgvector retrieval verified
   * Signed URL cross-farmer generation blocked (403)
   * Database UUID / foreign key schema compatibility verified
2. `backend/tests/test_embedding_parity.py` (3 parity tests):
   * 384-dimensional vector verification
   * Process-level singleton verification
   * Live Supabase pgvector cosine similarity retrieval

---

## 7. Tests Executed

* **Full Baseline Test Suite:** 151 / 151 tests PASS (0 failures, 2 warnings).
* **Execution Time:** ~305 seconds.
* **Target Database:** Supabase PostgreSQL (`aws-0-ap-south-1.pooler.supabase.com:6543/postgres?sslmode=require`).
* **Static Code Audit:** 57 Python files scanned, 0 P0 issues, 0 P1 issues.

---

## 8. Before and After Behavior

| Scenario | Before | After |
|---|---|---|
| Unauthenticated request to `/api/farmer-plans` | Returned all plans or created plan | **HTTP 401 Unauthorized** |
| Farmer booking soil test with another's `farmer_id` | Test booked successfully | **HTTP 403 Forbidden** |
| Farmer booking service request with another's `farmer_id` | Request created successfully | **HTTP 403 Forbidden** |
| Unauthenticated request to `/api/fertilizer/analyze` with `farm_id` | Read target farm's confidential soil data | **HTTP 401 Unauthorized** |
| Production call to `/api/iot/config` | Leaked host LAN IPv4 subnets | **Returns empty array `[]` in production** |
| Farmer altering hardware thresholds | Allowed | **HTTP 403 Forbidden** |

---

## 9. Remaining Operational Considerations

* **OpenRouter Latency:** OpenRouter external LLM API calls represent ~1.5–3.0 seconds of latency depending on upstream network routing. The backend maintains bounded 10-second timeouts and a structured offline RAG fallback.
* **Environment Configuration:** In production, platform environment variables must supply a secure `SECRET_KEY` (≥ 32 characters) and valid `DATABASE_URL`. If `SECRET_KEY` is missing or default in production, startup will fail fast.

---

## 10. Deployment Instructions

1. Configure production environment variables in Render/Docker dashboard:
   ```env
   ENVIRONMENT=production
   PORT=8000
   SECRET_KEY=<generate-32-char-random-key>
   DATABASE_URL=postgresql://postgres.[project-ref]:[password]@aws-0-[region].pooler.supabase.com:6543/postgres?sslmode=require
   SUPABASE_URL=https://[project-ref].supabase.co
   SUPABASE_ANON_KEY=<public-anon-key>
   SUPABASE_SERVICE_ROLE_KEY=<private-service-role-key>
   OPENROUTER_API_KEY=<openrouter-key>
   CORS_ORIGINS=https://your-domain.com
   ```
2. Start container using Uvicorn:
   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --app-dir backend
   ```
3. Verify healthcheck:
   ```bash
   curl -f https://your-domain.com/health
   ```
