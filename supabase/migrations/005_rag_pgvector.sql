-- =============================================================================
-- MAITRI Smart Agriculture AI Platform — Database Migration 005
-- Enterprise RAG Knowledge Base & pgvector (384-dimensional)
-- =============================================================================

-- 1. Create Private Internal Schema for Privileged Security Definer Functions
CREATE SCHEMA IF NOT EXISTS private;
REVOKE ALL ON SCHEMA private FROM PUBLIC;
GRANT USAGE ON SCHEMA private TO postgres, service_role;

-- 2. Knowledge Base Parent Documents
CREATE TABLE IF NOT EXISTS public.knowledge_documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title VARCHAR(255) NOT NULL,
    source VARCHAR(255) NOT NULL,
    source_type VARCHAR(50) DEFAULT 'curated_reference' CHECK (source_type IN ('official_verified', 'curated_reference', 'general_reference')),
    source_url TEXT,
    document_type VARCHAR(50) DEFAULT 'markdown',
    language VARCHAR(10) DEFAULT 'hi',
    category VARCHAR(80) DEFAULT 'General',
    crop VARCHAR(80) DEFAULT 'General',
    version VARCHAR(50) DEFAULT '2024.1',
    file_path VARCHAR(255),
    checksum VARCHAR(64) UNIQUE, -- SHA-256 hash to prevent duplicate ingestion
    is_public BOOLEAN DEFAULT true NOT NULL, -- Explicit access control
    is_verified BOOLEAN DEFAULT false NOT NULL,
    access_level VARCHAR(30) DEFAULT 'public' NOT NULL CHECK (access_level IN ('public', 'authenticated', 'restricted')),
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now()),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now())
);

CREATE INDEX IF NOT EXISTS idx_knowledge_docs_crop ON public.knowledge_documents(crop);
CREATE INDEX IF NOT EXISTS idx_knowledge_docs_category ON public.knowledge_documents(category);
CREATE INDEX IF NOT EXISTS idx_knowledge_docs_checksum ON public.knowledge_documents(checksum);
CREATE INDEX IF NOT EXISTS idx_knowledge_docs_access ON public.knowledge_documents(is_public, access_level);

-- 3. Knowledge Chunks with 384-dimensional pgvector Embedding
CREATE TABLE IF NOT EXISTS public.knowledge_chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID REFERENCES public.knowledge_documents(id) ON DELETE CASCADE NOT NULL,
    chunk_id_str VARCHAR(120) UNIQUE NOT NULL, -- e.g. mountain_farming_sec_1
    content TEXT NOT NULL,
    chunk_index INT NOT NULL,
    section_title VARCHAR(255),
    section_type VARCHAR(100),
    page_number INT DEFAULT 1,
    embedding extensions.vector(384) NOT NULL, -- Exact 384 dimensions matching all-MiniLM-L6-v2 in extensions schema
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now())
);

CREATE INDEX IF NOT EXISTS idx_knowledge_chunks_doc_id ON public.knowledge_chunks(document_id);
CREATE INDEX IF NOT EXISTS idx_knowledge_chunks_chunk_str ON public.knowledge_chunks(chunk_id_str);

-- Cosine similarity vector index using HNSW for fast nearest neighbor search
CREATE INDEX IF NOT EXISTS idx_knowledge_chunks_vector_hnsw 
    ON public.knowledge_chunks 
    USING hnsw (embedding extensions.vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

-- 4. Hardened Security Definer Function in Private Schema
-- Pinned search_path = '' and fully qualified objects prevent search-path injection
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
SET search_path = '' -- Critical security hardening: Empty search path
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

-- The privileged SECURITY DEFINER function remains safely encapsulated in the
-- non-exposed 'private' schema and is NOT exposed through the PostgREST Data API.


