-- =============================================================================
-- MAITRI Smart Agriculture AI Platform — Database Migration 001
-- Extensions: Vector (pgvector) and UUID Generator
-- =============================================================================

-- Ensure extensions schema exists (standard Supabase extension schema)
CREATE SCHEMA IF NOT EXISTS extensions;

-- Enable pgvector extension explicitly in extensions schema
CREATE EXTENSION IF NOT EXISTS vector WITH SCHEMA extensions;

-- Enable uuid-ossp for cryptographic UUID generation in extensions schema
CREATE EXTENSION IF NOT EXISTS "uuid-ossp" WITH SCHEMA extensions;

-- Enable pgcrypto for auxiliary hashing and random UUIDs in extensions schema
CREATE EXTENSION IF NOT EXISTS pgcrypto WITH SCHEMA extensions;

