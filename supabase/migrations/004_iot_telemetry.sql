-- =============================================================================
-- MAITRI Smart Agriculture AI Platform — Database Migration 004
-- IoT Hardware Controller Telemetry & Ultrasonic Radar Sweeps
-- =============================================================================

-- 1. Registered Edge Controller Nodes (ESP32 / ESP8266)
CREATE TABLE IF NOT EXISTS public.iot_devices (
    id BIGSERIAL PRIMARY KEY,
    device_id VARCHAR(80) UNIQUE NOT NULL, -- e.g. MAITRI_ESP32_01
    user_id UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    farm_id BIGINT REFERENCES public.farms(id) ON DELETE SET NULL,
    name VARCHAR(120) DEFAULT 'Field Telemetry Node',
    controller_type VARCHAR(40) DEFAULT 'ESP32',
    is_active BOOLEAN DEFAULT true,
    last_seen TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now()),
    created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now())
);

CREATE INDEX IF NOT EXISTS idx_iot_devices_device_id ON public.iot_devices(device_id);
CREATE INDEX IF NOT EXISTS idx_iot_devices_user_id ON public.iot_devices(user_id);
CREATE INDEX IF NOT EXISTS idx_iot_devices_farm_id ON public.iot_devices(farm_id);

-- 2. Time-Series Sensor Telemetry Readings
-- Directly linked via Foreign Key to public.iot_devices(id)
CREATE TABLE IF NOT EXISTS public.iot_sensor_readings (
    id BIGSERIAL PRIMARY KEY,
    device_table_id BIGINT REFERENCES public.iot_devices(id) ON DELETE CASCADE,
    device_id VARCHAR(80) NOT NULL,
    controller_type VARCHAR(40) DEFAULT 'ESP32',
    timestamp TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now()),
    temperature DOUBLE PRECISION,
    humidity DOUBLE PRECISION,
    soil_moisture DOUBLE PRECISION,
    water_distance_cm DOUBLE PRECISION,
    scan_json JSONB, -- Array of {angle, distance, object_detected, status}
    nearest_distance DOUBLE PRECISION,
    nearest_angle INT,
    object_status VARCHAR(40), -- CLEAR, OBJECT DETECTED, WARNING, VERY CLOSE, NO READING
    created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now())
);

-- Optimization indexes for time-series queries, device lookup, and dashboard charts
CREATE INDEX IF NOT EXISTS idx_iot_readings_device_table_id ON public.iot_sensor_readings(device_table_id);
CREATE INDEX IF NOT EXISTS idx_iot_readings_device_ts ON public.iot_sensor_readings(device_id, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_iot_readings_ts ON public.iot_sensor_readings(timestamp DESC);
