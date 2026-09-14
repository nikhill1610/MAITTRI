-- =============================================================================
-- MAITRI — Future Architecture Reference Schema (NOT in Current Migration)
-- Multi-Channel Communications, Lab Soil Testing & Operator Grievance Ticketing
-- =============================================================================

-- 1. Official Laboratory Soil Testing Requests
CREATE TABLE IF NOT EXISTS public.soil_test_requests (
    id BIGSERIAL PRIMARY KEY,
    request_id VARCHAR(30) UNIQUE NOT NULL,
    farmer_id BIGINT REFERENCES public.farmers(id) ON DELETE CASCADE NOT NULL,
    farm_id BIGINT REFERENCES public.farms(id) ON DELETE SET NULL,
    location VARCHAR(120),
    crop VARCHAR(80),
    sample_date VARCHAR(40),
    status VARCHAR(40) DEFAULT 'REQUESTED',
    lab_name VARCHAR(120),
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now()),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now())
);

-- 2. Certified Laboratory Soil Reports
CREATE TABLE IF NOT EXISTS public.soil_test_reports (
    id BIGSERIAL PRIMARY KEY,
    request_id VARCHAR(30) REFERENCES public.soil_test_requests(request_id) ON DELETE CASCADE NOT NULL,
    farmer_id BIGINT REFERENCES public.farmers(id) ON DELETE CASCADE NOT NULL,
    farm_id BIGINT REFERENCES public.farms(id) ON DELETE SET NULL,
    lab_name VARCHAR(120) NOT NULL,
    test_date VARCHAR(40),
    report_file VARCHAR(255),
    nitrogen DOUBLE PRECISION,
    phosphorus DOUBLE PRECISION,
    potassium DOUBLE PRECISION,
    ph DOUBLE PRECISION,
    ec DOUBLE PRECISION,
    organic_carbon DOUBLE PRECISION,
    zinc DOUBLE PRECISION,
    iron DOUBLE PRECISION,
    boron DOUBLE PRECISION,
    sulphur DOUBLE PRECISION,
    is_certified_lab_test BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now())
);

-- 3. General Assistance & Grievance Service Requests
CREATE TABLE IF NOT EXISTS public.service_requests (
    id BIGSERIAL PRIMARY KEY,
    request_id VARCHAR(30) UNIQUE NOT NULL,
    farmer_id BIGINT REFERENCES public.farmers(id) ON DELETE CASCADE NOT NULL,
    farm_id BIGINT REFERENCES public.farms(id) ON DELETE SET NULL,
    operator_id UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    service_type VARCHAR(60) NOT NULL,
    status VARCHAR(40) DEFAULT 'REQUESTED',
    description TEXT NOT NULL,
    resolution_notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now()),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now())
);

-- 4. Document Vault Metadata
CREATE TABLE IF NOT EXISTS public.farmer_documents (
    id BIGSERIAL PRIMARY KEY,
    farmer_id BIGINT REFERENCES public.farmers(id) ON DELETE CASCADE NOT NULL,
    farm_id BIGINT REFERENCES public.farms(id) ON DELETE SET NULL,
    document_name VARCHAR(255) NOT NULL,
    category VARCHAR(80) DEFAULT 'Land Record',
    file_path VARCHAR(255) NOT NULL,
    storage_path VARCHAR(255),
    file_type VARCHAR(40) NOT NULL,
    file_size_bytes BIGINT,
    uploaded_by_user_id UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    uploader_role VARCHAR(50) DEFAULT 'FARMER',
    status VARCHAR(40) DEFAULT 'VERIFIED',
    created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now())
);

-- 5. Multi-Channel Communication Preferences & Logs
CREATE TABLE IF NOT EXISTS public.communication_preferences (
    id BIGSERIAL PRIMARY KEY,
    farmer_id BIGINT REFERENCES public.farmers(id) ON DELETE CASCADE UNIQUE NOT NULL,
    sms_enabled BOOLEAN DEFAULT true,
    ivr_enabled BOOLEAN DEFAULT true,
    preferred_language VARCHAR(10) DEFAULT 'hi',
    weather_alerts BOOLEAN DEFAULT true,
    crop_alerts BOOLEAN DEFAULT true,
    market_alerts BOOLEAN DEFAULT true,
    scheme_alerts BOOLEAN DEFAULT true,
    insurance_alerts BOOLEAN DEFAULT true,
    promotional_opt_in BOOLEAN DEFAULT false,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now())
);

CREATE TABLE IF NOT EXISTS public.sms_logs (
    id BIGSERIAL PRIMARY KEY,
    farmer_id BIGINT REFERENCES public.farmers(id) ON DELETE SET NULL,
    mobile_number VARCHAR(20) NOT NULL,
    message_content TEXT NOT NULL,
    provider VARCHAR(40) DEFAULT 'demo',
    status VARCHAR(40) DEFAULT 'SENT',
    error_message TEXT,
    is_demo_mode BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now())
);

CREATE TABLE IF NOT EXISTS public.ivr_sessions (
    id BIGSERIAL PRIMARY KEY,
    session_id VARCHAR(80) UNIQUE NOT NULL,
    caller_number VARCHAR(20) NOT NULL,
    farmer_id BIGINT REFERENCES public.farmers(id) ON DELETE SET NULL,
    language VARCHAR(10) DEFAULT 'hi',
    current_menu VARCHAR(50) DEFAULT 'main',
    digits_pressed VARCHAR(20),
    transcript_json JSONB,
    is_demo_mode BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now()),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now())
);

CREATE TABLE IF NOT EXISTS public.notifications (
    id BIGSERIAL PRIMARY KEY,
    farmer_id BIGINT REFERENCES public.farmers(id) ON DELETE SET NULL,
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    message TEXT NOT NULL,
    category VARCHAR(60) DEFAULT 'general',
    channel VARCHAR(20) DEFAULT 'WEB',
    priority VARCHAR(20) DEFAULT 'NORMAL',
    read BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now())
);

CREATE TABLE IF NOT EXISTS public.operator_activity_logs (
    id BIGSERIAL PRIMARY KEY,
    operator_id UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
    action_type VARCHAR(80) NOT NULL,
    farmer_id BIGINT REFERENCES public.farmers(id) ON DELETE SET NULL,
    farm_id BIGINT REFERENCES public.farms(id) ON DELETE SET NULL,
    details_json JSONB,
    ip_address VARCHAR(60),
    created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now())
);
