-- =============================================================================
-- MAITRI Smart Agriculture AI Platform — Database Migration 006
-- Supabase Storage Buckets and Access Control Policies
-- =============================================================================

-- 1. Create Storage Buckets
INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
VALUES 
    ('farmer-vault', 'farmer-vault', false, 10485760, ARRAY['application/pdf', 'image/jpeg', 'image/png', 'image/webp']),
    ('knowledge-assets', 'knowledge-assets', true, 20971520, ARRAY['application/pdf', 'image/jpeg', 'image/png', 'text/markdown', 'text/plain'])
ON CONFLICT (id) DO UPDATE SET
    public = EXCLUDED.public,
    file_size_limit = EXCLUDED.file_size_limit,
    allowed_mime_types = EXCLUDED.allowed_mime_types;

-- 2. Note: Row Level Security on storage.objects is enabled by default by Supabase (owned by supabase_storage_admin)

-- -----------------------------------------------------------------------------
-- 3. Storage Policies for 'farmer-vault' (Private Vault)
-- -----------------------------------------------------------------------------
-- Strict Isolation: NO public read access (zero policies granted to anon or public).

-- Farmer can upload only to their own directory
DROP POLICY IF EXISTS "farmer_vault_insert_own" ON storage.objects;
CREATE POLICY "farmer_vault_insert_own"
ON storage.objects FOR INSERT
TO authenticated
WITH CHECK (
    bucket_id = 'farmer-vault' AND
    (storage.foldername(name))[1] = auth.uid()::text
);

-- Farmer can read only their own documents
DROP POLICY IF EXISTS "farmer_vault_select_own" ON storage.objects;
CREATE POLICY "farmer_vault_select_own"
ON storage.objects FOR SELECT
TO authenticated
USING (
    bucket_id = 'farmer-vault' AND
    (storage.foldername(name))[1] = auth.uid()::text
);

-- Farmer can update only their own documents
DROP POLICY IF EXISTS "farmer_vault_update_own" ON storage.objects;
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

-- Farmer can delete only their own documents
DROP POLICY IF EXISTS "farmer_vault_delete_own" ON storage.objects;
CREATE POLICY "farmer_vault_delete_own"
ON storage.objects FOR DELETE
TO authenticated
USING (
    bucket_id = 'farmer-vault' AND
    (storage.foldername(name))[1] = auth.uid()::text
);

-- Authorized operators and admins can inspect farmer vault files
DROP POLICY IF EXISTS "farmer_vault_operator_admin_select" ON storage.objects;
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

-- -----------------------------------------------------------------------------
-- 4. Storage Policies for 'knowledge-assets' (Intentionally Public Leaflets/Advisories)
-- -----------------------------------------------------------------------------

-- Public can read verified knowledge assets
DROP POLICY IF EXISTS "knowledge_assets_public_select" ON storage.objects;
CREATE POLICY "knowledge_assets_public_select"
ON storage.objects FOR SELECT
TO public
USING (bucket_id = 'knowledge-assets');

-- Admins can manage knowledge assets
DROP POLICY IF EXISTS "knowledge_assets_admin_all" ON storage.objects;
CREATE POLICY "knowledge_assets_admin_all"
ON storage.objects FOR ALL
TO authenticated
USING (
    bucket_id = 'knowledge-assets' AND
    EXISTS (
        SELECT 1 FROM public.profiles
        WHERE id = auth.uid() AND role = 'ADMIN'
    )
)
WITH CHECK (
    bucket_id = 'knowledge-assets' AND
    EXISTS (
        SELECT 1 FROM public.profiles
        WHERE id = auth.uid() AND role = 'ADMIN'
    )
);
