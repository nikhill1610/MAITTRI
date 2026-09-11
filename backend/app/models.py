from sqlalchemy import Column, Integer, String, Float, DateTime, Text, ForeignKey, Boolean
from datetime import datetime, timezone
from .database import Base

def utcnow():
    return datetime.now(timezone.utc)

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    language = Column(String(10), default="en")
    created_at = Column(DateTime, default=utcnow)

class Farm(Base):
    __tablename__ = "farms"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String(120), default="My Farm")
    latitude = Column(Float)
    longitude = Column(Float)
    location_name = Column(String(120), nullable=True)
    location_source = Column(String(50), default="manual")  # gps, map_click, search, manual
    area = Column(Float, nullable=False)
    area_unit = Column(String(20), default="acre")
    soil_type = Column(String(80), nullable=False)
    soil_type_source = Column(String(50), default="farmer_selected")  # auto_detected, farmer_selected
    soil_confidence = Column(String(20), default="Medium")  # High, Medium, Low
    irrigation = Column(String(50), default="available")
    previous_crop = Column(String(80))
    previous_crop_month = Column(String(30))
    previous_crop_period = Column(String(80), nullable=True)
    current_crop = Column(String(80))
    cultivation_count = Column(Integer, default=1)
    soil_n = Column(Float)
    soil_p = Column(Float)
    soil_k = Column(Float)
    soil_ph = Column(Float)
    organic_carbon = Column(Float)
    sowing_date = Column(String(40), nullable=True)
    created_at = Column(DateTime, default=utcnow)

class FarmPlan(Base):
    __tablename__ = "farm_plans"
    id = Column(Integer, primary_key=True)
    farm_id = Column(Integer, ForeignKey("farms.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    selected_crop = Column(String(80))
    sowing_date = Column(String(40), nullable=True)
    variety = Column(String(80), nullable=True)
    current_stage = Column(String(80), nullable=True)
    plan_json = Column(Text)
    plan_data_json = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

class FarmPlanTask(Base):
    __tablename__ = "farm_plan_tasks"
    id = Column(Integer, primary_key=True)
    farm_plan_id = Column(Integer, ForeignKey("farm_plans.id", ondelete="CASCADE"), nullable=False)
    task_date = Column(String(40), nullable=False, index=True)
    crop_age_day = Column(Integer, nullable=False)
    growth_stage = Column(String(80), nullable=False)
    category = Column(String(80), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    priority = Column(String(20), default="MEDIUM")
    estimated_duration = Column(String(50), default="30 mins")
    source = Column(String(120), default="ICAR / SAU Guidance")
    status = Column(String(30), default="pending", index=True)
    why_needed = Column(Text, nullable=True)
    action_steps = Column(Text, nullable=True)
    is_top_priority = Column(Boolean, default=False)
    plan_updated_reason = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

class FarmPlanCompletion(Base):
    __tablename__ = "farm_plan_completions"
    id = Column(Integer, primary_key=True)
    task_id = Column(Integer, ForeignKey("farm_plan_tasks.id", ondelete="SET NULL"), nullable=True)
    farm_plan_id = Column(Integer, ForeignKey("farm_plans.id", ondelete="CASCADE"), nullable=False)
    task_title = Column(String(255), nullable=False)
    category = Column(String(80), nullable=True)
    growth_stage = Column(String(80), nullable=True)
    crop_age_day = Column(Integer, nullable=True)
    completion_date = Column(String(40), nullable=False, index=True)
    completed_at = Column(DateTime, default=utcnow)
    farmer_notes = Column(Text, nullable=True)
    sensor_snapshot_json = Column(Text, nullable=True)
    weather_snapshot_json = Column(Text, nullable=True)

class NutrientAnalysisRecord(Base):
    __tablename__ = "nutrient_analyses"
    id = Column(Integer, primary_key=True)
    farm_id = Column(Integer, ForeignKey("farms.id"), nullable=False)
    analysis_json = Column(Text, nullable=False)
    created_at = Column(DateTime, default=utcnow)

class ParaliAnalysisRecord(Base):
    __tablename__ = "parali_analyses"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    farm_id = Column(Integer, ForeignKey("farms.id"), nullable=True)
    crop = Column(String(80), nullable=False)
    residue_type = Column(String(80), nullable=False)
    area = Column(Float, nullable=False)
    area_unit = Column(String(20), default="acre")
    analysis_json = Column(Text, nullable=False)
    created_at = Column(DateTime, default=utcnow)

class Field(Base):
    __tablename__ = "fields"
    id = Column(Integer, primary_key=True)
    farm_id = Column(Integer, ForeignKey("farms.id"), nullable=False)
    name = Column(String(120), default="Main Field")
    area = Column(Float, nullable=True)
    soil_type = Column(String(80), nullable=True)
    created_at = Column(DateTime, default=utcnow)

class Device(Base):
    __tablename__ = "devices"
    id = Column(Integer, primary_key=True)
    farm_id = Column(Integer, ForeignKey("farms.id"), nullable=False)
    field_id = Column(Integer, ForeignKey("fields.id"), nullable=True)
    device_code = Column(String(80), unique=True, index=True)
    device_type = Column(String(80), default="soil_sensor_npk")
    status = Column(String(40), default="active")
    last_seen = Column(DateTime, default=utcnow)
    created_at = Column(DateTime, default=utcnow)

class FarmCropHistory(Base):
    __tablename__ = "farm_crop_histories"
    id = Column(Integer, primary_key=True)
    farm_id = Column(Integer, ForeignKey("farms.id"), nullable=False)
    field_id = Column(Integer, ForeignKey("fields.id"), nullable=True)
    crop = Column(String(80), nullable=False)
    season = Column(String(40), default="rabi")
    year = Column(Integer, nullable=True)
    yield_tonnes = Column(Float, nullable=True)
    previous_crop = Column(String(80), nullable=True)
    fertilizer_used_json = Column(Text, nullable=True)
    pesticide_used_json = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utcnow)

class SoilAnalysis(Base):
    __tablename__ = "soil_analyses"
    id = Column(Integer, primary_key=True)
    farm_id = Column(Integer, ForeignKey("farms.id"), nullable=False)
    field_id = Column(Integer, ForeignKey("fields.id"), nullable=True)
    analysis_type = Column(String(40), default="laboratory")  # laboratory, sensor, farmer_entered
    lab_name = Column(String(120), nullable=True)
    sample_date = Column(DateTime, nullable=True)
    ph = Column(Float, nullable=True)
    ec = Column(Float, nullable=True)
    organic_carbon = Column(Float, nullable=True)
    moisture = Column(Float, nullable=True)
    soil_temperature = Column(Float, nullable=True)
    nitrogen = Column(Float, nullable=True)
    phosphorus = Column(Float, nullable=True)
    potassium = Column(Float, nullable=True)
    sulphur = Column(Float, nullable=True)
    calcium = Column(Float, nullable=True)
    magnesium = Column(Float, nullable=True)
    zinc = Column(Float, nullable=True)
    iron = Column(Float, nullable=True)
    boron = Column(Float, nullable=True)
    manganese = Column(Float, nullable=True)
    copper = Column(Float, nullable=True)
    report_file = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=utcnow)

class NutrientObservation(Base):
    __tablename__ = "nutrient_observations"
    id = Column(Integer, primary_key=True)
    farm_id = Column(Integer, ForeignKey("farms.id"), nullable=False)
    device_id = Column(Integer, ForeignKey("devices.id"), nullable=True)
    source = Column(String(40), default="sensor")  # sensor, lab, farmer
    nitrogen = Column(Float, nullable=True)
    phosphorus = Column(Float, nullable=True)
    potassium = Column(Float, nullable=True)
    ph = Column(Float, nullable=True)
    moisture = Column(Float, nullable=True)
    temperature = Column(Float, nullable=True)
    ec = Column(Float, nullable=True)
    observed_at = Column(DateTime, default=utcnow)

class FertilizerApplication(Base):
    __tablename__ = "fertilizer_applications"
    id = Column(Integer, primary_key=True)
    farm_id = Column(Integer, ForeignKey("farms.id"), nullable=False)
    crop = Column(String(80), nullable=False)
    fertilizer_type = Column(String(80), nullable=False)  # chemical, organic, biofertilizer
    fertilizer_name = Column(String(120), nullable=False)
    application_stage = Column(String(80), nullable=True)
    rate_per_acre = Column(String(80), nullable=True)
    application_method = Column(String(80), nullable=True)
    applied_at = Column(DateTime, default=utcnow)
    notes = Column(Text, nullable=True)

class PesticideApplication(Base):
    __tablename__ = "pesticide_applications"
    id = Column(Integer, primary_key=True)
    farm_id = Column(Integer, ForeignKey("farms.id"), nullable=False)
    crop = Column(String(80), nullable=False)
    target_pest_or_disease = Column(String(120), nullable=False)
    pesticide_name = Column(String(120), nullable=False)
    active_ingredient = Column(String(120), nullable=True)
    dosage = Column(String(80), nullable=True)
    application_method = Column(String(80), nullable=True)
    applied_at = Column(DateTime, default=utcnow)
    notes = Column(Text, nullable=True)

class PestObservation(Base):
    __tablename__ = "pest_observations"
    id = Column(Integer, primary_key=True)
    farm_id = Column(Integer, ForeignKey("farms.id"), nullable=False)
    crop = Column(String(80), nullable=False)
    pest_name = Column(String(120), nullable=True)
    disease_name = Column(String(120), nullable=True)
    symptoms = Column(Text, nullable=True)
    affected_area_pct = Column(Float, nullable=True)
    crop_stage = Column(String(80), nullable=True)
    image_url = Column(String(255), nullable=True)
    severity = Column(String(40), default="low")
    observed_at = Column(DateTime, default=utcnow)

class FertilizerRecommendation(Base):
    __tablename__ = "fertilizer_recommendations"
    id = Column(Integer, primary_key=True)
    farm_id = Column(Integer, ForeignKey("farms.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    crop = Column(String(80), nullable=False)
    previous_crop = Column(String(80), nullable=True)
    stage = Column(String(80), nullable=True)
    soil_type = Column(String(80), nullable=True)
    recommendation_json = Column(Text, nullable=False)
    confidence = Column(String(20), default="Medium")
    explanation_summary = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utcnow)

class PesticideRecommendation(Base):
    __tablename__ = "pesticide_recommendations"
    id = Column(Integer, primary_key=True)
    farm_id = Column(Integer, ForeignKey("farms.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    crop = Column(String(80), nullable=False)
    pest_or_disease = Column(String(120), nullable=True)
    recommendation_json = Column(Text, nullable=False)
    confidence = Column(String(20), default="Medium")
    explanation_summary = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utcnow)

class GovernmentScheme(Base):
    __tablename__ = "government_schemes"
    id = Column(Integer, primary_key=True)
    scheme_name = Column(String(255), nullable=False, index=True)
    scheme_type = Column(String(80), nullable=True)  # subsidy, direct_benefit, credit, insurance, training
    level = Column(String(40), default="central")    # central, state
    state = Column(String(80), nullable=True, index=True)  # None if central, state name if state scheme
    department = Column(String(255), nullable=True)
    category = Column(String(80), nullable=True, index=True)  # Crop Support, Financial Support, Irrigation, etc.
    description = Column(Text, nullable=True)
    eligibility_criteria_json = Column(Text, nullable=True)
    benefits_json = Column(Text, nullable=True)
    crop_applicability = Column(String(255), nullable=True)  # All, or specific crops
    season = Column(String(80), nullable=True)
    farm_size_rule = Column(String(80), nullable=True)
    application_start = Column(String(40), nullable=True)
    application_end = Column(String(40), nullable=True)
    status = Column(String(40), default="Open", index=True)  # Open, Upcoming, Closing Soon, Closed, Not Yet Verified
    official_source = Column(String(255), nullable=True)
    official_url = Column(String(255), nullable=True)
    documents_json = Column(Text, nullable=True)
    last_verified = Column(String(40), nullable=True)
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

class InsurancePlan(Base):
    __tablename__ = "insurance_plans"
    id = Column(Integer, primary_key=True)
    scheme_name = Column(String(255), nullable=False, index=True)
    plan_code = Column(String(80), nullable=True)
    state = Column(String(80), nullable=True, index=True)
    district = Column(String(80), nullable=True)
    crop = Column(String(80), nullable=False, index=True)
    season = Column(String(80), nullable=False, index=True)  # kharif, rabi, zaid, commercial
    coverage_json = Column(Text, nullable=True)
    premium_farmer_pct = Column(Float, nullable=True)
    premium_actuarial_pct = Column(Float, nullable=True)
    eligibility_json = Column(Text, nullable=True)
    application_start = Column(String(40), nullable=True)
    application_end = Column(String(40), nullable=True)
    claim_process_json = Column(Text, nullable=True)
    documents_json = Column(Text, nullable=True)
    official_source = Column(String(255), nullable=True)
    official_url = Column(String(255), nullable=True)
    last_verified = Column(String(40), nullable=True)
    created_at = Column(DateTime, default=utcnow)

class IoTDevice(Base):
    __tablename__ = "iot_devices"
    id = Column(Integer, primary_key=True)
    device_id = Column(String(80), unique=True, index=True, nullable=False)
    controller_type = Column(String(40), default="ESP8266")  # ESP8266, ESP32
    name = Column(String(120), default="Field Telemetry Node")
    farm_id = Column(Integer, ForeignKey("farms.id"), nullable=True)
    is_active = Column(Boolean, default=True)
    last_seen = Column(DateTime, default=utcnow)
    created_at = Column(DateTime, default=utcnow)

class IoTSensorReading(Base):
    __tablename__ = "iot_sensor_readings"
    id = Column(Integer, primary_key=True)
    device_id = Column(String(80), index=True, nullable=False)
    controller_type = Column(String(40), default="ESP8266")
    timestamp = Column(DateTime, default=utcnow, index=True)
    temperature = Column(Float, nullable=True)
    humidity = Column(Float, nullable=True)
    soil_moisture = Column(Float, nullable=True)
    scan_json = Column(Text, nullable=True)  # JSON array of {angle, distance, object_detected, status}
    nearest_distance = Column(Float, nullable=True)
    nearest_angle = Column(Integer, nullable=True)
    water_distance_cm = Column(Float, nullable=True)
    object_status = Column(String(40), nullable=True)  # CLEAR, OBJECT DETECTED, WARNING, VERY CLOSE, NO READING
    created_at = Column(DateTime, default=utcnow)

