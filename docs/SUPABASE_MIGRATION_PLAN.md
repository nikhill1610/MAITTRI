# MAITRI — Complete Supabase Migration Plan (Hardened & Scoped)

## Executive Summary
This document provides the definitive architectural specification for migrating the **MAITRI Smart Agriculture AI Platform** to a lean, secure, and production-ready **Supabase-centered architecture**.

---

## 1. Table Scope Classification

### 1.1 Category A: REQUIRED NOW (Core MAITRI Platform — 14 Tables)
Only tables actively utilized by current working functionality are created during this migration:

1. **`public.profiles`**: Application profiles (`full_name`, `role`, `phone_number`, `preferred_language`, `state`, `district`) linked to `auth.users(id)`.
2. **`public.farmers`**: Central farmer registry (`maittri_farmer_id`, `mobile_number`, landholding, irrigation).
3. **`public.farms`**: Geo-referenced farm plots (`latitude`, `longitude`, `area`, `soil_type`, NPK, `irrigation`).
4. **`public.farm_plans`**: Stage-wise crop calendar schedule (`selected_crop`, `sowing_date`, `variety`, plan JSON).
5. **`public.farm_plan_tasks`**: Daily actionable agronomy tasks (`task_date`, `crop_age_day`, `category`, `title`, `status`, `action_steps`).
6. **`public.farm_plan_completions`**: Completed farm milestones with farmer notes.
7. **`public.nutrient_analyses`**: NPK and organic carbon soil health records.
8. **`public.parali_analyses`**: Crop residue valorization calculations.
9. **`public.fertilizer_applications`**: Historical fertilizer logs.
10. **`public.fertilizer_recommendations`**: Agronomic fertilizer recommendations.
11. **`public.iot_devices`**: Registered ESP32 / ESP8266 edge hardware nodes.
12. **`public.iot_sensor_readings`**: Time-series telemetry with explicit Foreign Key `device_table_id REFERENCES public.iot_devices(id)`.
13. **`public.knowledge_documents`**: RAG knowledge documents with title, source, access control (`is_public`, `access_level`), and SHA-256 checksum.
14. **`public.knowledge_chunks`**: RAG chunks with content, section title, section type, page number, and **`embedding vector(384)`**.

### 1.2 Category B: FUTURE ARCHITECTURE (Moved to Documentation, NOT Created Now)
Documented in `docs/future_architecture/future_services_and_communications.sql`:
- `soil_test_requests` & `soil_test_reports` (Laboratory booking lifecycle)
- `service_requests` (Grievance ticketing system)
- `farmer_documents` (Vault table; files can be stored directly in Supabase Storage `farmer-vault`)
- `communication_preferences`, `sms_logs`, `ivr_sessions` (Demo telephony logs)
- `notifications` & `operator_activity_logs` (Auxiliary demo logs)
- `fields` & `farm_crop_histories` (Redundant sub-field division)
- `pesticide_applications`, `pest_observations`, `pesticide_recommendations`
- `government_schemes` & `insurance_plans` (Curated in-memory via `VERIFIED_SCHEMES` and `NOTIFIED_CROPS_REGISTRY`)

### 1.3 Category C: PERMANENTLY EXCLUDED (Chatbot Messages)
- ❌ **`chat_sessions`**: OMITTED.
- ❌ **`chat_messages`**: OMITTED.
- Active conversations live **strictly in temporary browser state**, bounded to the last 4 turns / 800 tokens, and wiped on Reset/New Chat.

---

## 2. Auth Migration Strategy (Existing 120 Users)

### 2.1 Audit Findings & Verification State Analysis
- **Total Existing Accounts**: 120 users in `backend/agri.db`.
- **Password Hasher**: **Argon2id** (`$argon2id$v=19$m=65536,t=3,p=4$...`).
- **Algorithm Distribution**: 100% (120 of 120) use Argon2id.
- **Verification State Audit Result**:
  - Direct schema inspection of `backend/agri.db` confirms columns: `['id', 'email', 'password_hash', 'language', 'created_at', 'role', 'full_name', 'phone_number']`.
  - The legacy SQLite system had no email-verification field and allowed immediate active sessions. Therefore email_confirm=True is an explicit migration mapping of the legacy authentication behavior, not a preservation of a stored verification flag.
  - In SQLite MAITRI implementation (`backend/app/routes/auth.py`), user registration immediately committed the record and issued an active JWT session.
  - **100% of the 120 existing users (120/120) are fully active, functional accounts** with immediate authentication privileges.

### 2.2 Migration Execution Protocol
- **No Direct SQL Insertion**: Do NOT directly `INSERT INTO auth.users` or manually manipulate `auth.users.encrypted_password`.
- **Supported Supabase Auth Admin Mechanism**: Use the supported Supabase Auth Admin migration mechanism with `password_hash` (`supabase.auth.admin.create_user(email=..., password_hash=..., email_confirm=True, user_metadata=...)`) to preserve the existing Argon2id hashes.
- **Migration Requirements**:
  1. **Preserve User Identity Mapping**: Map existing SQLite user IDs and usernames/emails to Supabase Auth user IDs (UUID) with a durable mapping table/dictionary.
  2. **Auth Verification Mapping**: The legacy SQLite system had no email-verification field and allowed immediate active sessions. Therefore email_confirm=True is an explicit migration mapping of the legacy authentication behavior, not a preservation of a stored verification flag.
  3. **Avoid Duplicate Users**: Query Supabase Auth before creation; skip or update existing accounts idempotently.
  4. **Create Corresponding `public.profiles`**: Ensure each user has a linked row in `public.profiles` with `id = auth.users.id`, `full_name`, `role`, `phone_number`, `preferred_language`, `state`, and `district`.
  5. **Test Login After Migration**: Test authentication against Supabase Auth with test credentials to verify that Argon2id hash verification succeeds end-to-end.
  6. **Zero Password/Hash Leakage**: Never log raw passwords or password hashes in migration logs, terminal output, or debug artifacts.
  7. **No Hypothetical Fallbacks**: Do NOT implement a hypothetical bcrypt-only fallback unless actual migration testing proves it is necessary.
  8. **No Premature Resets**: Do NOT reset passwords unless `password_hash` migration genuinely fails during live execution.

---

## 3. IoT Schema & RLS Strategy (Hardened)

### 3.1 Relational Design
```
auth.users
    │
    ▼
public.farms (id) ──┐
    │                │
    ▼                ▼
public.iot_devices (id, device_id, user_id, farm_id)
    │
    ▼ (device_table_id REFERENCES public.iot_devices(id) ON DELETE CASCADE)
public.iot_sensor_readings
```

### 3.2 Enforceable RLS Policy
```sql
ALTER TABLE public.iot_devices ENABLE ROW LEVEL SECURITY;

CREATE POLICY "iot_devices_owner_all"
ON public.iot_devices FOR ALL
TO authenticated
USING (
    user_id = auth.uid() OR
    farm_id IN (SELECT id FROM public.farms WHERE user_id = auth.uid())
);

ALTER TABLE public.iot_sensor_readings ENABLE ROW LEVEL SECURITY;

CREATE POLICY "iot_readings_owner_select"
ON public.iot_sensor_readings FOR SELECT
TO authenticated
USING (
    device_table_id IN (
        SELECT d.id FROM public.iot_devices d
        WHERE d.user_id = auth.uid() OR d.farm_id IN (SELECT f.id FROM public.farms f WHERE f.user_id = auth.uid())
    )
);
```

---

## 4. RAG pgvector & Security Hardening

### 4.1 Specification
- **Embedding Model**: `all-MiniLM-L6-v2` (SentenceTransformers / ONNX).
- **Dimension**: Exactly **384**.
- **Distance Metric**: Cosine similarity (`vector_cosine_ops`) with HNSW index.
- **Access Control**: `is_public BOOLEAN DEFAULT true`, `access_level VARCHAR(30) DEFAULT 'public'`.

### 4.2 Hardened `match_knowledge_chunks` Function (Private Schema)
```sql
CREATE SCHEMA IF NOT EXISTS private;
REVOKE ALL ON SCHEMA private FROM PUBLIC;
GRANT USAGE ON SCHEMA private TO postgres, service_role;

CREATE OR REPLACE FUNCTION private.match_knowledge_chunks(
    query_embedding extensions.vector(384),
    match_threshold pg_catalog.float8 DEFAULT 0.35,
    match_count pg_catalog.int4 DEFAULT 5,
    filter_crop pg_catalog.varchar DEFAULT NULL,
    filter_category pg_catalog.varchar DEFAULT NULL
)
RETURNS TABLE (
    id UUID,
    document_id UUID,
    chunk_id_str pg_catalog.varchar,
    content pg_catalog.text,
    section_title pg_catalog.varchar,
    section_type pg_catalog.varchar,
    page_number pg_catalog.int4,
    title pg_catalog.varchar,
    source pg_catalog.varchar,
    source_type pg_catalog.varchar,
    source_url pg_catalog.text,
    category pg_catalog.varchar,
    crop pg_catalog.varchar,
    version pg_catalog.varchar,
    similarity pg_catalog.float8
)
LANGUAGE plpgsql
STABLE
SECURITY DEFINER
SET search_path = '' -- Critical security hardening: Empty search path prevents search-path hijacking
AS $$
BEGIN
    RETURN QUERY
    SELECT
        c.id,
        c.document_id,
        c.chunk_id_str,
        c.content,
        c.section_title,
        c.section_type,
        c.page_number,
        d.title,
        d.source,
        d.source_type,
        d.source_url,
        d.category,
        d.crop,
        d.version,
        (1 - (c.embedding OPERATOR(extensions.<=>) query_embedding))::pg_catalog.float8 AS similarity
    FROM public.knowledge_chunks c
    JOIN public.knowledge_documents d ON c.document_id = d.id
    WHERE d.is_public = true -- Explicit access control
      AND d.access_level = 'public'
      AND (1 - (c.embedding OPERATOR(extensions.<=>) query_embedding)) >= match_threshold
      AND (filter_crop IS NULL OR d.crop ILIKE '%' || filter_crop || '%' OR d.crop = 'General')
      AND (filter_category IS NULL OR d.category ILIKE '%' || filter_category || '%' OR d.category = 'General')
    ORDER BY c.embedding OPERATOR(extensions.<=>) query_embedding
    LIMIT match_count;
END;
$$;

-- Restrict privileged function execution in private schema to trusted server roles
REVOKE ALL ON FUNCTION private.match_knowledge_chunks(extensions.vector(384), pg_catalog.float8, pg_catalog.int4, pg_catalog.varchar, pg_catalog.varchar) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION private.match_knowledge_chunks(extensions.vector(384), pg_catalog.float8, pg_catalog.int4, pg_catalog.varchar, pg_catalog.varchar) TO postgres, service_role;
```

### 4.3 Server-Side PostgreSQL Invocation Architecture
```
FastAPI backend
    ↓
direct PostgreSQL connection / psycopg2 (or SQLAlchemy Session)
    ↓
private.match_knowledge_chunks(...)
    ↓
pgvector (in extensions schema)
```
- **Supabase Roles Architecture**:
  - `postgres` = default PostgreSQL administrative role
  - `anon` = unauthenticated Data API role
  - `authenticated` = authenticated Data API role
  - `service_role` = elevated API role that bypasses RLS
- **Actual Backend Connection-Role Distinction**:
  - Direct PostgreSQL connection uses `postgres`
  - Shared pooler connection uses `postgres.<PROJECT-REF>`
  - The exact connection string/username must be taken from the Supabase Dashboard Connect dialog rather than hardcoded from assumptions.
- **RAG SECURITY DEFINER Function & Permissions**:
  - Resides strictly in `private.match_knowledge_chunks(...)`.
  - Pinned `SET search_path = '';` (Empty search path prevents search-path hijacking).
  - Fully qualified types, tables, and operators (`public.knowledge_chunks`, `public.knowledge_documents`, `extensions.vector(384)`, `OPERATOR(extensions.<=>)`).
  - HNSW index uses `extensions.vector_cosine_ops`.
  - No PostgREST Data API exposure.
  - No frontend access; zero service-role keys in frontend.
  - Before execution, verify that the actual database connection used by the FastAPI backend can EXECUTE the private function.
  - Do NOT broaden permissions unnecessarily: execution privileges are granted strictly to `postgres, service_role`.
- **Actual pgvector Extension Schema**: **`extensions`**
  - Supabase installs all PostgreSQL extensions in the dedicated **`extensions`** schema (`CREATE EXTENSION vector WITH SCHEMA extensions;`).
  - Because `SET search_path = ''` is pinned, the type is explicitly schema-qualified as `extensions.vector(384)` and the cosine similarity operator is invoked as `OPERATOR(extensions.<=>)`.

---

## 5. Storage Buckets & Explicit `storage.objects` RLS Policies

### 5.1 Bucket Configurations
- **`farmer-vault`**: Private (`public = false`, 10MB limit). Path: `{auth.uid()}/{filename}`.
- **`knowledge-assets`**: Public read (`public = true`, 20MB limit) for intentionally public ICAR advisories and leaflets.

### 5.2 Explicit `storage.objects` RLS Policies
```sql
ALTER TABLE storage.objects ENABLE ROW LEVEL SECURITY;

-- Farmer can upload only to their own folder in farmer-vault
CREATE POLICY "farmer_vault_insert_own"
ON storage.objects FOR INSERT
TO authenticated
WITH CHECK (
    bucket_id = 'farmer-vault' AND
    (storage.foldername(name))[1] = auth.uid()::text
);

-- Farmer can read only their own documents in farmer-vault
CREATE POLICY "farmer_vault_select_own"
ON storage.objects FOR SELECT
TO authenticated
USING (
    bucket_id = 'farmer-vault' AND
    (storage.foldername(name))[1] = auth.uid()::text
);

-- Farmer can update only their own documents in farmer-vault
CREATE POLICY "farmer_vault_update_own"
ON storage.objects FOR UPDATE
TO authenticated
USING (
    bucket_id = 'farmer-vault' AND
    (storage.foldername(name))[1] = auth.uid()::text
)
WITH CHECK (
    bucket_id = 'farmer-vault' AND
    (storage.foldername(name))[1] = auth.uid()::text
);

-- Farmer can delete only their own documents in farmer-vault
CREATE POLICY "farmer_vault_delete_own"
ON storage.objects FOR DELETE
TO authenticated
USING (
    bucket_id = 'farmer-vault' AND
    (storage.foldername(name))[1] = auth.uid()::text
);

-- Authorized operator/admin access only where explicitly permitted
CREATE POLICY "farmer_vault_operator_admin_select"
ON storage.objects FOR SELECT
TO authenticated
USING (
    bucket_id = 'farmer-vault' AND
    EXISTS (
        SELECT 1 FROM public.profiles
        WHERE id = auth.uid() AND role IN ('AUTHORIZED_OPERATOR', 'ADMIN')
    )
);

-- NO public read access to farmer-vault (strictly zero anon/public policies)

-- Public read for intentionally public knowledge assets
CREATE POLICY "knowledge_assets_public_select"
ON storage.objects FOR SELECT
TO public
USING (bucket_id = 'knowledge-assets');

-- Admin-only management for knowledge assets
CREATE POLICY "knowledge_assets_admin_all"
ON storage.objects FOR ALL
TO authenticated
USING (
    bucket_id = 'knowledge-assets' AND
    EXISTS (
        SELECT 1 FROM public.profiles
        WHERE id = auth.uid() AND role = 'ADMIN'
    )
);
```

---

## 6. Database Resilience & Production Fallback Policy

### 6.1 Authoritative Production Database
- **Supabase PostgreSQL** is the single authoritative persistent production database for MAITRI.
- **Zero Silent Fallback**: Silent fallback from Supabase PostgreSQL to SQLite in production is strictly prohibited.
- **Failure Behavior**:
  - If Supabase PostgreSQL is unreachable, unavailable, or encounters a transaction failure in production:
    1. The backend immediately returns a clear, structured HTTP error (e.g. `503 Service Unavailable` or `500 Internal Database Error`).
    2. Logs the failure safely with sanitized error context (never logging credentials, JWT secrets, passwords, or hashes).
    3. Under NO circumstances does the backend write or mirror production data into SQLite.
- **Local Development Exception**:
  - SQLite compatibility is retained solely as an explicit, opt-in local development mode activated only when running locally with `ENVIRONMENT=development` and `DATABASE_URL=sqlite:///./agri.db`.

---

## 7. Migration Sequence & Rollback

1. **Backup Phase**: Full export and cryptographic snapshot of `backend/agri.db` (6.9 MB) and `backend/vector_store/`.
2. **Schema Phase**: Execute SQL files `001` through `007` in `supabase/migrations/`.
3. **RAG Ingestion Phase**: Embed and store all 107 knowledge chunks into `knowledge_chunks` with `vector(384)` (including `mountain_farming.md`).
4. **Data Migration Phase**: Transfer existing 120 users, 39 farms, 45 plans, and 2,321 readings from SQLite using supported Supabase Auth Admin migration mechanism with `password_hash`.
5. **Verification Phase**: Run full test suite (wheat, rice, maize, mountain farming in Hindi/English/Hinglish).
6. **Deprecation Phase**: ChromaDB is removed ONLY after all Supabase pgvector retrieval tests pass with 100% confidence.
