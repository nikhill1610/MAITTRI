-- =============================================================================
-- MAITRI Smart Agriculture AI Platform — Database Migration 007
-- Row Level Security (RLS) Policies & Tenant Isolation (Hardened)
-- =============================================================================

-- Helper function to prevent recursive RLS evaluation on profiles
CREATE OR REPLACE FUNCTION public.is_operator_or_admin()
RETURNS BOOLEAN
LANGUAGE sql
SECURITY DEFINER
SET search_path = ''
AS $$
    SELECT EXISTS (
        SELECT 1 FROM public.profiles
        WHERE id = auth.uid() AND role IN ('AUTHORIZED_OPERATOR', 'ADMIN')
    );
$$;

-- -----------------------------------------------------------------------------
-- 1. Profiles
-- -----------------------------------------------------------------------------
ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "profiles_select_own" ON public.profiles;
CREATE POLICY "profiles_select_own"
ON public.profiles FOR SELECT
TO authenticated
USING (id = auth.uid());

DROP POLICY IF EXISTS "profiles_update_own" ON public.profiles;
CREATE POLICY "profiles_update_own"
ON public.profiles FOR UPDATE
TO authenticated
USING (id = auth.uid())
WITH CHECK (id = auth.uid());

DROP POLICY IF EXISTS "profiles_operator_view" ON public.profiles;
CREATE POLICY "profiles_operator_view"
ON public.profiles FOR SELECT
TO authenticated
USING (public.is_operator_or_admin());

-- -----------------------------------------------------------------------------
-- 2. Farmers
-- -----------------------------------------------------------------------------
ALTER TABLE public.farmers ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "farmers_owner_all" ON public.farmers;
CREATE POLICY "farmers_owner_all"
ON public.farmers FOR ALL
TO authenticated
USING (user_id = auth.uid())
WITH CHECK (user_id = auth.uid());

DROP POLICY IF EXISTS "farmers_operator_manage" ON public.farmers;
CREATE POLICY "farmers_operator_manage"
ON public.farmers FOR ALL
TO authenticated
USING (
    operator_id = auth.uid() OR
    public.is_operator_or_admin()
);

-- -----------------------------------------------------------------------------
-- 3. Farms
-- -----------------------------------------------------------------------------
ALTER TABLE public.farms ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "farms_owner_all" ON public.farms;
CREATE POLICY "farms_owner_all"
ON public.farms FOR ALL
TO authenticated
USING (user_id = auth.uid())
WITH CHECK (user_id = auth.uid());

DROP POLICY IF EXISTS "farms_operator_select" ON public.farms;
CREATE POLICY "farms_operator_select"
ON public.farms FOR SELECT
TO authenticated
USING (
    EXISTS (
        SELECT 1 FROM public.farmers f
        WHERE f.id = farms.farmer_id AND (
            f.operator_id = auth.uid() OR
            public.is_operator_or_admin()
        )
    )
);

-- -----------------------------------------------------------------------------
-- 4. Farm Plans & Tasks
-- -----------------------------------------------------------------------------
ALTER TABLE public.farm_plans ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "farm_plans_owner_all" ON public.farm_plans;
CREATE POLICY "farm_plans_owner_all"
ON public.farm_plans FOR ALL
TO authenticated
USING (
    user_id = auth.uid() OR
    farm_id IN (SELECT id FROM public.farms WHERE user_id = auth.uid())
)
WITH CHECK (
    user_id = auth.uid() OR
    farm_id IN (SELECT id FROM public.farms WHERE user_id = auth.uid())
);

ALTER TABLE public.farm_plan_tasks ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "farm_plan_tasks_owner_all" ON public.farm_plan_tasks;
CREATE POLICY "farm_plan_tasks_owner_all"
ON public.farm_plan_tasks FOR ALL
TO authenticated
USING (
    farm_plan_id IN (
        SELECT fp.id FROM public.farm_plans fp
        WHERE fp.user_id = auth.uid() OR fp.farm_id IN (SELECT id FROM public.farms WHERE user_id = auth.uid())
    )
);

ALTER TABLE public.farm_plan_completions ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "farm_plan_completions_owner_all" ON public.farm_plan_completions;
CREATE POLICY "farm_plan_completions_owner_all"
ON public.farm_plan_completions FOR ALL
TO authenticated
USING (
    farm_plan_id IN (
        SELECT fp.id FROM public.farm_plans fp
        WHERE fp.user_id = auth.uid() OR fp.farm_id IN (SELECT id FROM public.farms WHERE user_id = auth.uid())
    )
);

-- -----------------------------------------------------------------------------
-- 5. Nutrient & Parali Analyses
-- -----------------------------------------------------------------------------
ALTER TABLE public.nutrient_analyses ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "nutrient_analyses_owner_all" ON public.nutrient_analyses;
CREATE POLICY "nutrient_analyses_owner_all"
ON public.nutrient_analyses FOR ALL
TO authenticated
USING (
    user_id = auth.uid() OR
    farm_id IN (SELECT id FROM public.farms WHERE user_id = auth.uid())
);

ALTER TABLE public.parali_analyses ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "parali_analyses_owner_all" ON public.parali_analyses;
CREATE POLICY "parali_analyses_owner_all"
ON public.parali_analyses FOR ALL
TO authenticated
USING (
    user_id = auth.uid() OR
    farm_id IN (SELECT id FROM public.farms WHERE user_id = auth.uid())
);

-- -----------------------------------------------------------------------------
-- 6. Fertilizer Applications & Recommendations
-- -----------------------------------------------------------------------------
ALTER TABLE public.fertilizer_applications ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "fertilizer_applications_owner_all" ON public.fertilizer_applications;
CREATE POLICY "fertilizer_applications_owner_all"
ON public.fertilizer_applications FOR ALL
TO authenticated
USING (farm_id IN (SELECT id FROM public.farms WHERE user_id = auth.uid()));

ALTER TABLE public.fertilizer_recommendations ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "fertilizer_recommendations_owner_all" ON public.fertilizer_recommendations;
CREATE POLICY "fertilizer_recommendations_owner_all"
ON public.fertilizer_recommendations FOR ALL
TO authenticated
USING (
    user_id = auth.uid() OR
    farm_id IN (SELECT id FROM public.farms WHERE user_id = auth.uid())
);

-- -----------------------------------------------------------------------------
-- 7. IoT Devices & Readings (Hardened Foreign-Key Enforced Isolation)
-- -----------------------------------------------------------------------------
ALTER TABLE public.iot_devices ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "iot_devices_owner_all" ON public.iot_devices;
CREATE POLICY "iot_devices_owner_all"
ON public.iot_devices FOR ALL
TO authenticated
USING (
    user_id = auth.uid() OR
    farm_id IN (SELECT id FROM public.farms WHERE user_id = auth.uid())
);

ALTER TABLE public.iot_sensor_readings ENABLE ROW LEVEL SECURITY;

-- Reading access strictly enforced through the parent iot_devices record
DROP POLICY IF EXISTS "iot_readings_owner_select" ON public.iot_sensor_readings;
CREATE POLICY "iot_readings_owner_select"
ON public.iot_sensor_readings FOR SELECT
TO authenticated
USING (
    device_table_id IN (
        SELECT d.id FROM public.iot_devices d
        WHERE d.user_id = auth.uid() OR d.farm_id IN (SELECT f.id FROM public.farms f WHERE f.user_id = auth.uid())
    )
);

-- -----------------------------------------------------------------------------
-- 8. Knowledge Documents & Chunks (RAG Access Control)
-- -----------------------------------------------------------------------------
ALTER TABLE public.knowledge_documents ENABLE ROW LEVEL SECURITY;

-- Public can only read published, verified knowledge documents
DROP POLICY IF EXISTS "knowledge_docs_public_read" ON public.knowledge_documents;
CREATE POLICY "knowledge_docs_public_read"
ON public.knowledge_documents FOR SELECT
TO anon, authenticated
USING (is_public = true AND access_level = 'public');

ALTER TABLE public.knowledge_chunks ENABLE ROW LEVEL SECURITY;

-- Chunks readable only if the parent document is public
DROP POLICY IF EXISTS "knowledge_chunks_public_read" ON public.knowledge_chunks;
CREATE POLICY "knowledge_chunks_public_read"
ON public.knowledge_chunks FOR SELECT
TO anon, authenticated
USING (
    EXISTS (
        SELECT 1 FROM public.knowledge_documents d
        WHERE d.id = knowledge_chunks.document_id AND d.is_public = true AND d.access_level = 'public'
    )
);
