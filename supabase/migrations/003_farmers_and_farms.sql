-- =============================================================================
-- MAITRI Smart Agriculture AI Platform — Database Migration 003
-- Farmer Registry, Farms, Land Holdings, Planning & Nutrient Analytics
-- =============================================================================

-- 1. Central Farmer Registry
CREATE TABLE IF NOT EXISTS public.farmers (
    id BIGSERIAL PRIMARY KEY,
    maittri_farmer_id VARCHAR(30) UNIQUE NOT NULL, -- e.g. MT-FARM-123456
    user_id UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    operator_id UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    name VARCHAR(120) NOT NULL,
    mobile_number VARCHAR(20) NOT NULL,
    alternate_mobile VARCHAR(20),
    state VARCHAR(80) DEFAULT 'Uttar Pradesh',
    district VARCHAR(80),
    block VARCHAR(80),
    village VARCHAR(80),
    farm_area DOUBLE PRECISION DEFAULT 1.0,
    area_unit VARCHAR(20) DEFAULT 'acre',
    land_ownership VARCHAR(50) DEFAULT 'owner',
    irrigation VARCHAR(50) DEFAULT 'tubewell',
    soil_type VARCHAR(80) DEFAULT 'Alluvial Soil',
    soil_test_available BOOLEAN DEFAULT false,
    current_crop VARCHAR(80),
    previous_crop VARCHAR(80),
    planned_crop VARCHAR(80),
    sowing_date VARCHAR(40),
    crop_variety VARCHAR(80),
    preferred_language VARCHAR(10) DEFAULT 'hi',
    sms_consent BOOLEAN DEFAULT true,
    ivr_consent BOOLEAN DEFAULT true,
    qr_code_data VARCHAR(120),
    created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now()),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now())
);

CREATE INDEX IF NOT EXISTS idx_farmers_user_id ON public.farmers(user_id);
CREATE INDEX IF NOT EXISTS idx_farmers_operator_id ON public.farmers(operator_id);
CREATE INDEX IF NOT EXISTS idx_farmers_mobile ON public.farmers(mobile_number);
CREATE INDEX IF NOT EXISTS idx_farmers_district ON public.farmers(district);

-- 2. Farms Table
CREATE TABLE IF NOT EXISTS public.farms (
    id BIGSERIAL PRIMARY KEY,
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    farmer_id BIGINT REFERENCES public.farmers(id) ON DELETE SET NULL,
    name VARCHAR(120) DEFAULT 'My Farm',
    latitude DOUBLE PRECISION,
    longitude DOUBLE PRECISION,
    location_name VARCHAR(120),
    location_source VARCHAR(50) DEFAULT 'manual', -- gps, map_click, search, manual
    area DOUBLE PRECISION NOT NULL,
    area_unit VARCHAR(20) DEFAULT 'acre',
    soil_type VARCHAR(80) NOT NULL,
    soil_type_source VARCHAR(50) DEFAULT 'farmer_selected',
    soil_confidence VARCHAR(20) DEFAULT 'Medium',
    irrigation VARCHAR(50) DEFAULT 'available',
    previous_crop VARCHAR(80),
    previous_crop_month VARCHAR(30),
    previous_crop_period VARCHAR(80),
    current_crop VARCHAR(80),
    cultivation_count INT DEFAULT 1,
    soil_n DOUBLE PRECISION,
    soil_p DOUBLE PRECISION,
    soil_k DOUBLE PRECISION,
    soil_ph DOUBLE PRECISION,
    organic_carbon DOUBLE PRECISION,
    sowing_date VARCHAR(40),
    created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now()),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now())
);

CREATE INDEX IF NOT EXISTS idx_farms_user_id ON public.farms(user_id);
CREATE INDEX IF NOT EXISTS idx_farms_farmer_id ON public.farms(farmer_id);
CREATE INDEX IF NOT EXISTS idx_farms_crop ON public.farms(current_crop);

-- 3. Dynamic Farm Growth Plans
CREATE TABLE IF NOT EXISTS public.farm_plans (
    id BIGSERIAL PRIMARY KEY,
    farm_id BIGINT REFERENCES public.farms(id) ON DELETE CASCADE NOT NULL,
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    selected_crop VARCHAR(80),
    sowing_date VARCHAR(40),
    variety VARCHAR(80),
    current_stage VARCHAR(80),
    plan_json JSONB,
    plan_data_json JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now()),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now())
);

CREATE INDEX IF NOT EXISTS idx_farm_plans_farm_id ON public.farm_plans(farm_id);
CREATE INDEX IF NOT EXISTS idx_farm_plans_user_id ON public.farm_plans(user_id);

-- 4. Daily Actionable Agronomy Tasks
CREATE TABLE IF NOT EXISTS public.farm_plan_tasks (
    id BIGSERIAL PRIMARY KEY,
    farm_plan_id BIGINT REFERENCES public.farm_plans(id) ON DELETE CASCADE NOT NULL,
    task_date VARCHAR(40) NOT NULL,
    crop_age_day INT NOT NULL,
    growth_stage VARCHAR(80) NOT NULL,
    category VARCHAR(80) NOT NULL,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    priority VARCHAR(20) DEFAULT 'MEDIUM',
    estimated_duration VARCHAR(50) DEFAULT '30 mins',
    source VARCHAR(120) DEFAULT 'ICAR / SAU Guidance',
    status VARCHAR(30) DEFAULT 'pending',
    why_needed TEXT,
    action_steps TEXT,
    is_top_priority BOOLEAN DEFAULT false,
    plan_updated_reason VARCHAR(255),
    created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now()),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now())
);

CREATE INDEX IF NOT EXISTS idx_plan_tasks_plan_id ON public.farm_plan_tasks(farm_plan_id);
CREATE INDEX IF NOT EXISTS idx_plan_tasks_status ON public.farm_plan_tasks(status);
CREATE INDEX IF NOT EXISTS idx_plan_tasks_date ON public.farm_plan_tasks(task_date);

-- 5. Farm Plan Task Completions
CREATE TABLE IF NOT EXISTS public.farm_plan_completions (
    id BIGSERIAL PRIMARY KEY,
    task_id BIGINT REFERENCES public.farm_plan_tasks(id) ON DELETE SET NULL,
    farm_plan_id BIGINT REFERENCES public.farm_plans(id) ON DELETE CASCADE NOT NULL,
    task_title VARCHAR(255) NOT NULL,
    category VARCHAR(80),
    growth_stage VARCHAR(80),
    crop_age_day INT,
    completion_date VARCHAR(40) NOT NULL,
    completed_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now()),
    farmer_notes TEXT,
    sensor_snapshot_json JSONB,
    weather_snapshot_json JSONB
);

CREATE INDEX IF NOT EXISTS idx_plan_comp_plan_id ON public.farm_plan_completions(farm_plan_id);

-- 6. Nutrient & Parali Records
CREATE TABLE IF NOT EXISTS public.nutrient_analyses (
    id BIGSERIAL PRIMARY KEY,
    farm_id BIGINT REFERENCES public.farms(id) ON DELETE CASCADE NOT NULL,
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    analysis_json JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now())
);

CREATE TABLE IF NOT EXISTS public.parali_analyses (
    id BIGSERIAL PRIMARY KEY,
    user_id UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    farm_id BIGINT REFERENCES public.farms(id) ON DELETE SET NULL,
    crop VARCHAR(80) NOT NULL,
    residue_type VARCHAR(80) NOT NULL,
    area DOUBLE PRECISION NOT NULL,
    area_unit VARCHAR(20) DEFAULT 'acre',
    analysis_json JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now())
);

-- 7. Fertilizer Applications & Recommendations
CREATE TABLE IF NOT EXISTS public.fertilizer_applications (
    id BIGSERIAL PRIMARY KEY,
    farm_id BIGINT REFERENCES public.farms(id) ON DELETE CASCADE NOT NULL,
    crop VARCHAR(80) NOT NULL,
    fertilizer_type VARCHAR(80) NOT NULL,
    fertilizer_name VARCHAR(120) NOT NULL,
    application_stage VARCHAR(80),
    rate_per_acre VARCHAR(80),
    application_method VARCHAR(80),
    applied_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now()),
    notes TEXT
);

CREATE TABLE IF NOT EXISTS public.fertilizer_recommendations (
    id BIGSERIAL PRIMARY KEY,
    farm_id BIGINT REFERENCES public.farms(id) ON DELETE CASCADE NOT NULL,
    user_id UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    crop VARCHAR(80) NOT NULL,
    previous_crop VARCHAR(80),
    stage VARCHAR(80),
    soil_type VARCHAR(80),
    recommendation_json JSONB NOT NULL,
    confidence VARCHAR(20) DEFAULT 'Medium',
    explanation_summary TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now())
);
