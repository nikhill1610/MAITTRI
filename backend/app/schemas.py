from pydantic import BaseModel, EmailStr, Field, ConfigDict, model_validator
from typing import Optional, List, Dict, Any, Union

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6, max_length=128)
    role: Optional[str] = "FARMER"  # FARMER, AUTHORIZED_OPERATOR
    full_name: Optional[str] = None
    phone_number: Optional[str] = None
    language: str = "en"

class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: Optional[str] = "FARMER"
    user_id: Optional[Union[str, int]] = None
    email: Optional[str] = None
    full_name: Optional[str] = None

class FarmCreate(BaseModel):
    name: str = "My Farm"
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    location_name: Optional[str] = None
    location_source: Optional[str] = "manual"  # gps, map_click, search, manual
    area: float = Field(gt=0)
    area_unit: str = "acre"
    soil_type: str
    soil_type_source: Optional[str] = "farmer_selected"  # auto_detected, farmer_selected
    soil_confidence: Optional[str] = "Medium"  # High, Medium, Low
    irrigation: str = "available"
    previous_crop: Optional[str] = None
    previous_crop_month: Optional[str] = None
    previous_crop_period: Optional[str] = None
    current_crop: Optional[str] = None
    cultivation_count: Optional[int] = 1
    soil_n: Optional[float] = None
    soil_p: Optional[float] = None
    soil_k: Optional[float] = None
    soil_ph: Optional[float] = None
    organic_carbon: Optional[float] = None

class FarmResponse(FarmCreate):
    id: int
    model_config = ConfigDict(from_attributes=True)

class FarmUpdate(BaseModel):
    name: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    location_name: Optional[str] = None
    location_source: Optional[str] = None
    area: Optional[float] = Field(default=None, gt=0)
    area_unit: Optional[str] = None
    soil_type: Optional[str] = None
    soil_type_source: Optional[str] = None
    soil_confidence: Optional[str] = None
    irrigation: Optional[str] = None
    previous_crop: Optional[str] = None
    previous_crop_month: Optional[str] = None
    previous_crop_period: Optional[str] = None
    current_crop: Optional[str] = None
    cultivation_count: Optional[int] = None
    soil_n: Optional[float] = None
    soil_p: Optional[float] = None
    soil_k: Optional[float] = None
    soil_ph: Optional[float] = None
    organic_carbon: Optional[float] = None

class RecommendationRequest(BaseModel):
    farm_id: int
    season: str = "rabi"
    budget: float = 50000
    market_preference: str = "balanced"

class PlanRequest(BaseModel):
    farm_id: int
    crop: str = Field(min_length=1)

class WeatherRequest(BaseModel):
    latitude: float
    longitude: float
    location_name: Optional[str] = None
    forecast_days: int = 7

class SoilEstimateRequest(BaseModel):
    latitude: float = Field(..., ge=-90.0, le=90.0)
    longitude: float = Field(..., ge=-180.0, le=180.0)

class NutrientAnalysisRequest(BaseModel):
    farm_id: Optional[int] = None
    soil_type: Optional[str] = "Loamy soil"
    soil_type_source: Optional[str] = "auto_detected"
    previous_crop: Optional[str] = None
    previous_crop_period: Optional[str] = None
    current_crop: Optional[str] = None
    cultivation_count: Optional[int] = 1
    soil_ph: Optional[float] = None
    soil_n: Optional[float] = None
    soil_p: Optional[float] = None
    soil_k: Optional[float] = None
    organic_carbon: Optional[float] = None

class ParaliAnalyzeRequest(BaseModel):
    crop: str = "rice"
    area: float = Field(..., gt=0)
    area_unit: str = "acre"
    residue_quantity: Optional[float] = None
    residue_quantity_source: Optional[str] = "estimated"
    farmer_goal: Optional[str] = "recommend_best"
    machinery_available: Optional[str] = "not_sure"
    machinery: Optional[List[str]] = []
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    soil_type: Optional[str] = None
    previous_crop: Optional[str] = None
    current_crop: Optional[str] = None
    farm_id: Optional[int] = None

class ParaliActionPlanRequest(BaseModel):
    method_id: str
    crop: Optional[str] = "rice"
    area: Optional[float] = 1.0
    area_unit: Optional[str] = "acre"

class FertilizerAnalyzeRequest(BaseModel):
    farm_id: Optional[int] = None
    current_crop: str = Field(..., min_length=1)
    previous_crop: Optional[str] = None
    previous_crop_harvest_season: Optional[str] = None
    crop_stage: Optional[str] = None
    soil_type: Optional[str] = "Alluvial soil"
    soil_ph: Optional[float] = Field(default=None, ge=3.0, le=11.5)
    soil_moisture: Optional[float] = Field(default=None, ge=0.0, le=100.0)
    soil_temperature: Optional[float] = Field(default=None, ge=-10.0, le=60.0)
    soil_n: Optional[float] = Field(default=None, ge=0.0)
    soil_p: Optional[float] = Field(default=None, ge=0.0)
    soil_k: Optional[float] = Field(default=None, ge=0.0)
    secondary_nutrients: Optional[Dict[str, Optional[float]]] = None
    micronutrients: Optional[Dict[str, Optional[float]]] = None
    data_source: Optional[str] = "farmer_input"  # laboratory, sensor, farmer_input, estimated
    farm_location: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    irrigation: Optional[str] = "available"
    pest_observed: Optional[str] = None
    disease_observed: Optional[str] = None
    pest_symptoms: Optional[str] = None
    affected_area_pct: Optional[float] = Field(default=None, ge=0.0, le=100.0)
    residue_handling: Optional[str] = "removed"  # removed, incorporated, burned

class FertilizerRecommendRequest(FertilizerAnalyzeRequest):
    include_weather: Optional[bool] = True

class PestAnalyzeRequest(BaseModel):
    crop: str = Field(..., min_length=1)
    pest_observed: Optional[str] = None
    disease_observed: Optional[str] = None
    symptoms: Optional[str] = None
    affected_area_pct: Optional[float] = Field(default=None, ge=0.0, le=100.0)
    crop_stage: Optional[str] = None
    image_url: Optional[str] = None

class PestRecommendRequest(PestAnalyzeRequest):
    farm_id: Optional[int] = None

class FertilizerApplicationCreate(BaseModel):
    farm_id: int
    crop: str
    fertilizer_type: str  # chemical, organic, biofertilizer
    fertilizer_name: str
    application_stage: Optional[str] = None
    rate_per_acre: Optional[str] = None
    application_method: Optional[str] = None
    notes: Optional[str] = None

class PesticideApplicationCreate(BaseModel):
    farm_id: int
    crop: str
    target_pest_or_disease: str
    pesticide_name: str
    active_ingredient: Optional[str] = None
    dosage: Optional[str] = None
    application_method: Optional[str] = None
    notes: Optional[str] = None

# ========================================================
# Government Schemes Schemas
# ========================================================

class SchemeEligibilityRequest(BaseModel):
    farm_id: Optional[int] = None
    scheme_id: Optional[int] = None
    state: Optional[str] = None
    district: Optional[str] = None
    crop: Optional[str] = None
    season: Optional[str] = None
    farm_size_acres: Optional[float] = Field(default=None, ge=0.0)
    farmer_category: Optional[str] = "General"  # Small/Marginal, SC/ST, Women, General
    land_ownership: Optional[str] = "Owner"    # Owner, Tenant, Sharecropper
    irrigation_type: Optional[str] = "available"
    equipment_needed: Optional[str] = None
    solar_pump_needed: Optional[bool] = False

class SchemeEligibilityResponse(BaseModel):
    scheme_id: int
    scheme_name: str
    eligibility_status: str  # Eligible, Potentially Eligible, Not Eligible, Insufficient Information, Unknown
    match_percentage: int
    reasons: List[str]
    missing_information: List[str]
    action_steps: List[str]
    official_disclaimer: str

# ========================================================
# Insurance Planning Schemas
# ========================================================

class InsuranceAnalyzeRequest(BaseModel):
    farm_id: Optional[int] = None
    state: Optional[str] = None
    district: Optional[str] = None
    crop: Optional[str] = None
    season: Optional[str] = "rabi"
    farm_area: Optional[float] = Field(default=None, ge=0.0)
    sowing_date: Optional[str] = None
    expected_harvest: Optional[str] = None
    irrigation: Optional[str] = "available"
    farm_type: Optional[str] = "Owner"
    farmer_category: Optional[str] = "Small/Marginal"
    include_weather_risk: Optional[bool] = True

class InsuranceEligibilityRequest(BaseModel):
    insurance_id: Optional[int] = None
    state: Optional[str] = None
    crop: Optional[str] = None
    season: Optional[str] = None
    farm_size: Optional[float] = None


# ========================================================
# IoT & Ultrasonic Radar Hardware Schemas
# ========================================================

class RadarScanPoint(BaseModel):
    angle: int = Field(ge=0, le=180, description="Servo angle in degrees (20° to 160°)")
    distance: Optional[float] = Field(default=None, le=450.0, description="Ultrasonic distance in cm (None or <= 0 indicates no echo / out of range)")
    object_detected: bool = Field(default=False, description="True if an obstacle is within threshold")
    status: str = Field(default="CLEAR", description="CLEAR, OBJECT DETECTED, WARNING, VERY CLOSE, or NO READING")

class NearestObject(BaseModel):
    angle: int
    distance: float
    status: str

class IoTSensorDataCreate(BaseModel):
    device_id: Optional[str] = Field(default=None, max_length=80, examples=["MAITRI_ESP32_01"])
    device: Optional[str] = Field(default=None, max_length=80, examples=["ESP32"])
    controller_type: Optional[str] = Field(default="ESP32", examples=["ESP32"])
    temperature: Optional[float] = Field(default=None, description="DHT22 ambient temperature in °C")
    humidity: Optional[float] = Field(default=None, description="DHT22 ambient humidity in %")
    soil_moisture: Optional[float] = Field(default=None, description="Analog soil moisture percentage 0-100%")
    water_distance_cm: Optional[float] = Field(default=None, description="HC-SR04 ultrasonic distance in cm")
    farm_id: Optional[int] = Field(default=None, description="Optional associated farm ID")
    scan: List[RadarScanPoint] = Field(default_factory=list, description="Array of servo angle and ultrasonic distance pairs")

    @model_validator(mode='before')
    @classmethod
    def normalize_device_and_fields(cls, data: Any) -> Any:
        if isinstance(data, dict):
            # Check for explicitly empty strings
            dev = data.get("device")
            dev_id = data.get("device_id")

            if dev_id is not None and isinstance(dev_id, str) and not dev_id.strip():
                raise ValueError("device_id cannot be an empty string")
            if dev is not None and isinstance(dev, str) and not dev.strip():
                raise ValueError("device cannot be an empty string")

            if dev_id and str(dev_id).strip():
                data["device_id"] = str(dev_id).strip()
            elif dev and str(dev).strip():
                dev_str = str(dev).strip()
                if dev_str.upper() == "ESP32":
                    data["device_id"] = "MAITRI_ESP32_01"
                    data["controller_type"] = "ESP32"
                elif dev_str.upper() == "ESP8266":
                    data["device_id"] = "MAITRI_ESP8266_01"
                    data["controller_type"] = "ESP8266"
                else:
                    data["device_id"] = dev_str
            else:
                data["device_id"] = "MAITRI_ESP32_01"

            if dev and not data.get("controller_type"):
                data["controller_type"] = str(dev).strip()

            # Ensure numeric fields are cast if passed as strings (e.g. "28.5")
            for num_field in ("temperature", "humidity", "soil_moisture", "water_distance_cm"):
                val = data.get(num_field)
                if val is not None and val != "":
                    try:
                        data[num_field] = float(val)
                    except (ValueError, TypeError):
                        data[num_field] = None

            # If water_distance_cm is given and scan is empty, synthesize a 90° center radar point
            wd = data.get("water_distance_cm")
            scan_data = data.get("scan")
            if wd is not None and not scan_data:
                try:
                    wd_float = float(wd)
                    if wd_float > 0.0:
                        data["scan"] = [{
                            "angle": 90,
                            "distance": round(wd_float, 1),
                            "object_detected": wd_float <= 100.0,
                            "status": "CLEAR" if wd_float > 100.0 else ("OBJECT DETECTED" if wd_float > 50.0 else ("WARNING" if wd_float > 20.0 else "VERY CLOSE"))
                        }]
                except Exception:
                    pass

        return data

class IoTLatestResponse(BaseModel):
    device_id: str
    controller_type: str
    status: str  # ONLINE, OFFLINE
    is_online: bool
    temperature: Optional[float] = None
    humidity: Optional[float] = None
    soil_moisture: Optional[float] = None
    water_distance_cm: Optional[float] = None
    scan: List[RadarScanPoint] = Field(default_factory=list)
    nearest_object: Optional[NearestObject] = None
    object_status: str = "CLEAR"
    timestamp: Optional[str] = None
    last_seen: Optional[str] = None
    time_diff_seconds: float = 0.0
    thresholds: Optional[Dict[str, Any]] = None
    lan_ips: Optional[List[Dict[str, Any]]] = None
    recommended_url: Optional[str] = None

class IoTDeviceSummary(BaseModel):
    device_id: str
    controller_type: str
    name: str = "Field Telemetry Node"
    status: str  # ONLINE, OFFLINE
    is_online: bool
    last_seen: str
    time_diff_seconds: float
    latest_temperature: Optional[float] = None
    latest_humidity: Optional[float] = None
    latest_soil_moisture: Optional[float] = None

class IoTThresholdConfig(BaseModel):
    clear_distance: float = Field(default=100.0, gt=0)
    warning_distance: float = Field(default=50.0, gt=0)
    critical_distance: float = Field(default=20.0, gt=0)
    offline_timeout_seconds: int = Field(default=20, ge=5)

# ========================================================
# Farmer Planning & Crop Calendar Schemas
# ========================================================

class FarmerPlanCreateRequest(BaseModel):
    farm_id: int
    crop: str = Field(..., min_length=1)
    sowing_date: Optional[str] = None
    crop_age_days: Optional[int] = Field(default=None, ge=0)
    current_stage: Optional[str] = None
    variety: Optional[str] = None

class FarmerPlanUpdateRequest(BaseModel):
    sowing_date: Optional[str] = None
    variety: Optional[str] = None
    crop: Optional[str] = None

class TaskStatusUpdateRequest(BaseModel):
    status: str = Field(..., pattern="^(pending|completed|skipped)$")
    notes: Optional[str] = None

class FarmerNoteRequest(BaseModel):
    notes: str = Field(..., min_length=1)


# ========================================================
# Multi-Channel MAITTRI Platform Schemas
# ========================================================

class FarmerCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=120)
    mobile_number: str = Field(..., min_length=10, max_length=20)
    alternate_mobile: Optional[str] = None
    state: Optional[str] = "Uttar Pradesh"
    district: Optional[str] = "Varanasi"
    block: Optional[str] = None
    village: Optional[str] = None
    farm_area: float = Field(default=1.0, gt=0)
    area_unit: str = "acre"
    land_ownership: Optional[str] = "owner"
    irrigation: Optional[str] = "tubewell"
    soil_type: Optional[str] = "Alluvial Soil"
    soil_test_available: bool = False
    current_crop: Optional[str] = None
    previous_crop: Optional[str] = None
    planned_crop: Optional[str] = None
    sowing_date: Optional[str] = None
    crop_variety: Optional[str] = None
    preferred_language: str = "hi"
    sms_consent: bool = True
    ivr_consent: bool = True

class FarmerUpdate(BaseModel):
    name: Optional[str] = None
    mobile_number: Optional[str] = None
    alternate_mobile: Optional[str] = None
    state: Optional[str] = None
    district: Optional[str] = None
    block: Optional[str] = None
    village: Optional[str] = None
    farm_area: Optional[float] = None
    area_unit: Optional[str] = None
    land_ownership: Optional[str] = None
    irrigation: Optional[str] = None
    soil_type: Optional[str] = None
    soil_test_available: Optional[bool] = None
    current_crop: Optional[str] = None
    previous_crop: Optional[str] = None
    planned_crop: Optional[str] = None
    sowing_date: Optional[str] = None
    crop_variety: Optional[str] = None
    preferred_language: Optional[str] = None
    sms_consent: Optional[bool] = None
    ivr_consent: Optional[bool] = None

class FarmerResponse(FarmerCreate):
    id: int
    maittri_farmer_id: str
    mobile_number: Optional[str] = None
    user_id: Optional[Union[str, int]] = None
    operator_id: Optional[Union[str, int]] = None
    qr_code_data: Optional[str] = None
    created_at: Optional[Any] = None
    updated_at: Optional[Any] = None
    model_config = ConfigDict(from_attributes=True)



class SoilTestRequestCreate(BaseModel):
    farmer_id: int
    farm_id: Optional[int] = None
    location: Optional[str] = None
    crop: Optional[str] = None
    sample_date: Optional[str] = None
    notes: Optional[str] = None

class SoilTestRequestUpdate(BaseModel):
    status: str = Field(..., pattern="^(REQUESTED|SCHEDULED|SAMPLE_COLLECTED|LAB_PROCESSING|REPORT_AVAILABLE|CANCELLED)$")
    lab_name: Optional[str] = None
    notes: Optional[str] = None

class SoilTestRequestResponse(BaseModel):
    id: int
    request_id: str
    farmer_id: int
    farm_id: Optional[int] = None
    location: Optional[str] = None
    crop: Optional[str] = None
    sample_date: Optional[str] = None
    status: str
    lab_name: Optional[str] = None
    notes: Optional[str] = None
    created_at: Optional[Any] = None
    updated_at: Optional[Any] = None
    model_config = ConfigDict(from_attributes=True)


class SoilTestReportCreate(BaseModel):
    request_id: str
    farmer_id: int
    farm_id: Optional[int] = None
    lab_name: str = Field(..., min_length=2)
    test_date: Optional[str] = None
    nitrogen: Optional[float] = None
    phosphorus: Optional[float] = None
    potassium: Optional[float] = None
    ph: Optional[float] = None
    ec: Optional[float] = None
    organic_carbon: Optional[float] = None
    zinc: Optional[float] = None
    iron: Optional[float] = None
    boron: Optional[float] = None
    sulphur: Optional[float] = None

class SoilTestReportResponse(SoilTestReportCreate):
    id: int
    report_file: Optional[str] = None
    is_certified_lab_test: bool = True
    created_at: Optional[Any] = None
    model_config = ConfigDict(from_attributes=True)


class ServiceRequestCreate(BaseModel):
    farmer_id: int
    farm_id: Optional[int] = None
    service_type: str = Field(..., pattern="^(SOIL_TEST|CROP_ADVISORY|PEST_ADVISORY|FERTILIZER_ADVISORY|DOCUMENT_ASSISTANCE|SCHEME_ASSISTANCE|INSURANCE_ASSISTANCE)$")
    description: str = Field(..., min_length=5)

class ServiceRequestUpdate(BaseModel):
    status: str = Field(..., pattern="^(REQUESTED|IN_PROGRESS|SCHEDULED|COMPLETED|CANCELLED)$")
    resolution_notes: Optional[str] = None

class ServiceRequestResponse(BaseModel):
    id: int
    request_id: str
    farmer_id: int
    farm_id: Optional[int] = None
    operator_id: Optional[Union[str, int]] = None
    service_type: str
    status: str
    description: str
    resolution_notes: Optional[str] = None
    created_at: Optional[Any] = None
    updated_at: Optional[Any] = None
    model_config = ConfigDict(from_attributes=True)



class CommunicationPreferenceUpdate(BaseModel):
    sms_enabled: Optional[bool] = None
    ivr_enabled: Optional[bool] = None
    preferred_language: Optional[str] = None
    weather_alerts: Optional[bool] = None
    crop_alerts: Optional[bool] = None
    market_alerts: Optional[bool] = None
    scheme_alerts: Optional[bool] = None
    insurance_alerts: Optional[bool] = None
    promotional_opt_in: Optional[bool] = None

class CommunicationPreferenceResponse(BaseModel):
    farmer_id: int
    sms_enabled: bool
    ivr_enabled: bool
    preferred_language: str
    weather_alerts: bool
    crop_alerts: bool
    market_alerts: bool
    scheme_alerts: bool
    insurance_alerts: bool
    promotional_opt_in: bool
    model_config = ConfigDict(from_attributes=True)


class SMSBroadcastRequest(BaseModel):
    farmer_ids: Optional[List[int]] = None
    mobile_numbers: Optional[List[str]] = None
    message: str = Field(..., min_length=5, max_length=500)
    category: Optional[str] = "weather_warning"

class SMSLogResponse(BaseModel):
    id: int
    farmer_id: Optional[int] = None
    mobile_number: str
    message_content: str
    provider: str
    status: str
    error_message: Optional[str] = None
    is_demo_mode: bool
    created_at: Optional[Any] = None
    model_config = ConfigDict(from_attributes=True)


class IVRSimulateRequest(BaseModel):
    farmer_id: Optional[int] = None
    phone_number: str = "9876543210"
    digits_pressed: Optional[str] = None
    current_menu: str = "main"
    language: str = "hi"
    diagnostic_step: Optional[int] = 0
    diagnostic_answers: Optional[Dict[str, Any]] = None

class IVRSimulateResponse(BaseModel):
    session_id: str
    current_menu: str
    audio_text_hi: str
    audio_text_en: str
    options: List[Dict[str, str]]
    status: str
    is_demo_mode: bool = True


# -----------------------------------------------------------------------------
# Telemetry & Route Action Schemas (CR-23)
# -----------------------------------------------------------------------------
from enum import Enum

class IntentEnum(str, Enum):
    GENERAL = "GENERAL"
    CALENDAR = "CALENDAR"
    WEATHER = "WEATHER"
    SOIL = "SOIL"
    FERTILIZER = "FERTILIZER"
    PESTICIDE_REFUSAL = "PESTICIDE_REFUSAL"
    FINANCIAL = "FINANCIAL"
    MARKET = "MARKET"
    UNSUPPORTED = "UNSUPPORTED"


class RouteActionEnum(str, Enum):
    RAG = "RAG"
    WEATHER_SERVICE = "WEATHER_SERVICE"
    CALENDAR_SERVICE = "CALENDAR_SERVICE"
    SOIL_SERVICE = "SOIL_SERVICE"
    FERTILIZER_SERVICE = "FERTILIZER_SERVICE"
    FINANCIAL_SERVICE = "FINANCIAL_SERVICE"
    MARKET_SERVICE = "MARKET_SERVICE"
    SAFE_REFUSAL = "SAFE_REFUSAL"
    ASK_FOR_CONTEXT = "ASK_FOR_CONTEXT"
    WEB_SEARCH = "WEB_SEARCH"
    RAG_WEB_FALLBACK = "RAG_WEB_FALLBACK"


class PilotTelemetryEvent(BaseModel):
    event_id: str
    timestamp_utc: str
    session_hash: Optional[str] = None
    sanitized_query_text: Optional[str] = None
    detected_language: str
    crop_detected: Optional[str] = None
    voluntary_geography: Optional[Dict[str, Optional[str]]] = None
    detected_intent: IntentEnum
    route_action: RouteActionEnum
    retrieved_doc_ids: List[str]
    answer_status: str
    generation_provider: Optional[str] = None
    confidence_score: Optional[float] = None




