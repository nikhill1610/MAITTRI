from sqlalchemy import Column, Integer, String, Float, DateTime, Text, ForeignKey, Boolean
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.types import CHAR, TypeDecorator
from datetime import datetime, timezone
from .database import Base

def utcnow():
    return datetime.now(timezone.utc)

class GUID(TypeDecorator):
    """Platform-independent GUID type.
    Uses PostgreSQL's UUID type (as string), otherwise uses CHAR(36).
    """
    impl = CHAR
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(PG_UUID(as_uuid=False))
        return dialect.type_descriptor(CHAR(36))

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        val_str = str(value)
        try:
            import uuid as _u
            return str(_u.UUID(val_str))
        except (ValueError, AttributeError):
            import uuid as _u
            return str(_u.uuid5(_u.NAMESPACE_OID, val_str))

    def process_result_value(self, value, dialect):
        return str(value) if value is not None else None

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(50), default="FARMER", index=True)  # FARMER, AUTHORIZED_OPERATOR
    full_name = Column(String(120), nullable=True)
    phone_number = Column(String(20), nullable=True, index=True)
    language = Column(String(10), default="en")
    created_at = Column(DateTime, default=utcnow)

class Profile(Base):
    __tablename__ = "profiles"
    id = Column(GUID, primary_key=True)
    role = Column(String(50), default="FARMER", index=True)
    full_name = Column(String(120), nullable=True)
    phone_number = Column(String(20), nullable=True)
    preferred_language = Column(String(10), default="hi")
    state = Column(String(80), nullable=True)
    district = Column(String(80), nullable=True)
    avatar_url = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

    @property
    def language(self):
        return self.preferred_language

    @property
    def email(self):
        return getattr(self, "_email", None)

    @email.setter
    def email(self, value):
        self._email = value

class Farm(Base):
    __tablename__ = "farms"
    id = Column(Integer, primary_key=True)
    user_id = Column(GUID, nullable=False, index=True)
    farmer_id = Column(Integer, nullable=True, index=True)
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
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

    @property
    def size_acres(self):
        return self.area

    @size_acres.setter
    def size_acres(self, value):
        self.area = value

    @property
    def crop(self):
        return self.current_crop

    @crop.setter
    def crop(self, value):
        self.current_crop = value

    def __init__(self, **kwargs):
        if "size_acres" in kwargs and "area" not in kwargs:
            kwargs["area"] = kwargs.pop("size_acres")
        if "crop" in kwargs and "current_crop" not in kwargs:
            kwargs["current_crop"] = kwargs.pop("crop")
        super().__init__(**kwargs)

class FarmPlan(Base):
    __tablename__ = "farm_plans"
    id = Column(Integer, primary_key=True)
    farm_id = Column(Integer, ForeignKey("farms.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(GUID, nullable=True, index=True)
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
    farm_id = Column(Integer, ForeignKey("farms.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(GUID, nullable=True, index=True)
    analysis_json = Column(Text, nullable=False)
    created_at = Column(DateTime, default=utcnow)

class ParaliAnalysisRecord(Base):
    __tablename__ = "parali_analyses"
    id = Column(Integer, primary_key=True)
    user_id = Column(GUID, nullable=True, index=True)
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
    farm_id = Column(Integer, ForeignKey("farms.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(GUID, nullable=True, index=True)
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
    farm_id = Column(Integer, ForeignKey("farms.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(GUID, nullable=True, index=True)
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
    user_id = Column(GUID, nullable=True, index=True)
    farm_id = Column(Integer, ForeignKey("farms.id"), nullable=True)
    name = Column(String(120), default="Field Telemetry Node")
    controller_type = Column(String(40), default="ESP8266")  # ESP8266, ESP32
    device_token_hash = Column(String(64), nullable=True, index=True)
    is_active = Column(Boolean, default=True)
    last_seen = Column(DateTime, default=utcnow)
    created_at = Column(DateTime, default=utcnow)

class IoTSensorReading(Base):
    __tablename__ = "iot_sensor_readings"
    id = Column(Integer, primary_key=True)
    device_table_id = Column(Integer, ForeignKey("iot_devices.id", ondelete="CASCADE"), nullable=True, index=True)
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

# =============================================================================
# Multi-Channel MAITTRI Platform Models
# =============================================================================

class Farmer(Base):
    """
    Central Farmer entity representing a registered farmer.
    Supports self-registration (linked to user_id) or assisted registration
    conducted by an Authorized Seva Operator (operator_id).
    """
    __tablename__ = "farmers"
    id = Column(Integer, primary_key=True)
    maittri_farmer_id = Column(String(30), unique=True, index=True, nullable=False)  # MT-FARM-XXXXXX
    user_id = Column(GUID, nullable=True, index=True)
    operator_id = Column(GUID, nullable=True, index=True)
    name = Column(String(120), nullable=False)
    mobile_number = Column(String(20), nullable=False, index=True)
    alternate_mobile = Column(String(20), nullable=True)
    state = Column(String(80), nullable=True, default="Uttar Pradesh")
    district = Column(String(80), nullable=True, index=True)
    block = Column(String(80), nullable=True)
    village = Column(String(80), nullable=True)
    farm_area = Column(Float, default=1.0)
    area_unit = Column(String(20), default="acre")
    land_ownership = Column(String(50), default="owner")  # owner, tenant, sharecropper
    irrigation = Column(String(50), default="tubewell")  # canal, tubewell, rainfed, drip, none
    soil_type = Column(String(80), default="Alluvial Soil")
    soil_test_available = Column(Boolean, default=False)
    current_crop = Column(String(80), nullable=True)
    previous_crop = Column(String(80), nullable=True)
    planned_crop = Column(String(80), nullable=True)
    sowing_date = Column(String(40), nullable=True)
    crop_variety = Column(String(80), nullable=True)
    preferred_language = Column(String(10), default="hi")  # hi, en
    sms_consent = Column(Boolean, default=True)
    ivr_consent = Column(Boolean, default=True)
    qr_code_data = Column(String(120), nullable=True)
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

    @property
    def full_name(self):
        return self.name

    @full_name.setter
    def full_name(self, value):
        self.name = value

    def __init__(self, **kwargs):
        if "full_name" in kwargs and "name" not in kwargs:
            kwargs["name"] = kwargs.pop("full_name")
        if "mobile_number" not in kwargs:
            import random
            kwargs["mobile_number"] = f"98765{random.randint(10000, 99999)}"
        super().__init__(**kwargs)


class FarmerDocument(Base):
    """
    Document Vault for verified land records, certified soil reports, and subsidy docs.
    """
    __tablename__ = "farmer_documents"
    id = Column(Integer, primary_key=True)
    farmer_id = Column(Integer, ForeignKey("farmers.id"), nullable=False, index=True)
    farm_id = Column(Integer, ForeignKey("farms.id"), nullable=True)
    document_name = Column(String(255), nullable=False)
    category = Column(String(80), default="Land Record")  # Land Record, Soil Test Report, Crop Record, Insurance, Scheme Application, Other
    file_path = Column(String(255), nullable=False)
    storage_path = Column(String(255), nullable=True)
    file_url = Column(Text, nullable=True)
    file_type = Column(String(40), nullable=False)
    file_size_bytes = Column(Integer, nullable=True)
    uploaded_by_user_id = Column(GUID, nullable=True, index=True)
    uploader_role = Column(String(50), default="FARMER")
    status = Column(String(40), default="VERIFIED")  # VERIFIED, PENDING_REVIEW, ARCHIVED
    created_at = Column(DateTime, default=utcnow)


class SoilTestRequest(Base):
    """
    Lifecycle tracking for official laboratory soil testing bookings.
    """
    __tablename__ = "soil_test_requests"
    id = Column(Integer, primary_key=True)
    request_id = Column(String(30), unique=True, index=True, nullable=False)  # MT-STR-XXXXXX
    farmer_id = Column(Integer, ForeignKey("farmers.id"), nullable=False, index=True)
    farm_id = Column(Integer, ForeignKey("farms.id"), nullable=True)
    location = Column(String(120), nullable=True)
    crop = Column(String(80), nullable=True)
    sample_date = Column(String(40), nullable=True)
    status = Column(String(40), default="REQUESTED", index=True)  # REQUESTED, SCHEDULED, SAMPLE_COLLECTED, LAB_PROCESSING, REPORT_AVAILABLE, CANCELLED
    lab_name = Column(String(120), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)


class SoilTestReport(Base):
    """
    Certified laboratory soil analysis report.
    Explicitly marked certified (distinct from indicative IoT sensor readings).
    """
    __tablename__ = "soil_test_reports"
    id = Column(Integer, primary_key=True)
    request_id = Column(String(30), ForeignKey("soil_test_requests.request_id"), nullable=False, index=True)
    farmer_id = Column(Integer, ForeignKey("farmers.id"), nullable=False, index=True)
    farm_id = Column(Integer, ForeignKey("farms.id"), nullable=True)
    lab_name = Column(String(120), nullable=False)
    test_date = Column(String(40), nullable=True)
    report_file = Column(String(255), nullable=True)
    nitrogen = Column(Float, nullable=True)
    phosphorus = Column(Float, nullable=True)
    potassium = Column(Float, nullable=True)
    ph = Column(Float, nullable=True)
    ec = Column(Float, nullable=True)
    organic_carbon = Column(Float, nullable=True)
    zinc = Column(Float, nullable=True)
    iron = Column(Float, nullable=True)
    boron = Column(Float, nullable=True)
    sulphur = Column(Float, nullable=True)
    is_certified_lab_test = Column(Boolean, default=True)
    created_at = Column(DateTime, default=utcnow)


class ServiceRequest(Base):
    """
    General assistance/grievance service request tracked by Seva Operators and Farmers.
    """
    __tablename__ = "service_requests"
    id = Column(Integer, primary_key=True)
    request_id = Column(String(30), unique=True, index=True, nullable=False)  # MT-REQ-XXXXXX
    farmer_id = Column(Integer, ForeignKey("farmers.id"), nullable=False, index=True)
    farm_id = Column(Integer, ForeignKey("farms.id"), nullable=True)
    operator_id = Column(GUID, nullable=True, index=True)
    service_type = Column(String(60), nullable=False, index=True)  # SOIL_TEST, CROP_ADVISORY, PEST_ADVISORY, FERTILIZER_ADVISORY, DOCUMENT_ASSISTANCE, SCHEME_ASSISTANCE, INSURANCE_ASSISTANCE
    status = Column(String(40), default="REQUESTED", index=True)  # REQUESTED, IN_PROGRESS, SCHEDULED, COMPLETED, CANCELLED
    description = Column(Text, nullable=False)
    resolution_notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)


class CommunicationPreference(Base):
    """
    Farmer preferences for SMS and IVR voice broadcasts.
    """
    __tablename__ = "communication_preferences"
    id = Column(Integer, primary_key=True)
    farmer_id = Column(Integer, ForeignKey("farmers.id"), unique=True, nullable=False, index=True)
    sms_enabled = Column(Boolean, default=True)
    ivr_enabled = Column(Boolean, default=True)
    preferred_language = Column(String(10), default="hi")
    weather_alerts = Column(Boolean, default=True)
    crop_alerts = Column(Boolean, default=True)
    market_alerts = Column(Boolean, default=True)
    scheme_alerts = Column(Boolean, default=True)
    insurance_alerts = Column(Boolean, default=True)
    promotional_opt_in = Column(Boolean, default=False)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)


class SMSLog(Base):
    """
    Audit log of outbound SMS messages dispatched or simulated.
    """
    __tablename__ = "sms_logs"
    id = Column(Integer, primary_key=True)
    farmer_id = Column(Integer, ForeignKey("farmers.id"), nullable=True, index=True)
    mobile_number = Column(String(20), nullable=False)
    message_content = Column(Text, nullable=False)
    provider = Column(String(40), default="demo")  # demo, twilio, msg91
    status = Column(String(40), default="SENT")  # SENT, FAILED, SIMULATED_DEMO
    error_message = Column(Text, nullable=True)
    is_demo_mode = Column(Boolean, default=True)
    created_at = Column(DateTime, default=utcnow)


class IVRSession(Base):
    """
    Session logs for incoming or simulated IVR keypad interactions.
    """
    __tablename__ = "ivr_sessions"
    id = Column(Integer, primary_key=True)
    session_id = Column(String(80), unique=True, index=True, nullable=False)
    caller_number = Column(String(20), nullable=False, index=True)
    farmer_id = Column(Integer, ForeignKey("farmers.id"), nullable=True, index=True)
    language = Column(String(10), default="hi")
    current_menu = Column(String(50), default="main")
    digits_pressed = Column(String(20), nullable=True)
    transcript_json = Column(Text, nullable=True)
    is_demo_mode = Column(Boolean, default=True)
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)


class Notification(Base):
    """
    Multi-channel system notification.
    """
    __tablename__ = "notifications"
    id = Column(Integer, primary_key=True)
    farmer_id = Column(Integer, ForeignKey("farmers.id"), nullable=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    category = Column(String(60), default="general")  # weather, crop, fertilizer, pest, market, scheme, soil_test, service
    channel = Column(String(20), default="WEB")  # WEB, SMS, IVR
    priority = Column(String(20), default="NORMAL")  # HIGH, MEDIUM, NORMAL
    read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=utcnow)


class OperatorActivityLog(Base):
    """
    Audit trail for authorized operator actions.
    """
    __tablename__ = "operator_activity_logs"
    id = Column(Integer, primary_key=True)
    operator_id = Column(GUID, nullable=True, index=True)
    action_type = Column(String(80), nullable=False, index=True)
    farmer_id = Column(Integer, ForeignKey("farmers.id"), nullable=True, index=True)
    farm_id = Column(Integer, ForeignKey("farms.id"), nullable=True)
    details_json = Column(Text, nullable=True)
    ip_address = Column(String(60), nullable=True)
    created_at = Column(DateTime, default=utcnow)


