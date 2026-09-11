"""
farmer_planning_service.py
MAITTRI Agricultural Decision Support System
Tagline: "किसान का साथी, समृद्धि की शुरुआत"

Dynamic Personal Farm Planner & Stage-Based Farm Brain Engine.
Consumes authoritative Crop Calendar, Weather Forecast, IoT Soil Telemetry,
Soil & Nutrient Intelligence, Fertilizer Recommendations, Pest Observations,
Market Prices, Government Schemes, Insurance Planning, and Parali Management.

Generates:
1. Today's Farm Goal ("आज क्या करना है?") with Top 3 Actions & "Why MAITTRI recommends this"
2. Dynamic 7-Day Farm Plan (This Week's Plan)
3. Complete Crop Lifecycle Timeline with real calculated dates
4. Weekly Milestones across the entire crop season
5. Real-time dynamic updates ("Plan Updated") when weather/sensor changes
6. Digital Farm Diary tracking farmer observations and completion history
"""

import json
from datetime import date, datetime, timedelta, timezone
from typing import Dict, Any, List, Optional, Tuple

from sqlalchemy.orm import Session
from sqlalchemy import desc

from ..models import (
    Farm,
    FarmPlan,
    FarmPlanTask,
    FarmPlanCompletion,
    IoTSensorReading,
    PestObservation,
    FertilizerRecommendation
)
from .crop_calendar_service import (
    get_crop_calendar,
    get_crop_stage_for_day,
    calculate_calendar_dates,
    normalize_crop_key
)
from ..routes.weather import fetch_weather_data
from ..market_price_service import get_latest_market_price
from .government_scheme_service import get_upcoming_schemes
from .iot_service import get_latest_telemetry


def parse_date_safely(date_str: str) -> Optional[date]:
    """Parses date string in ISO (YYYY-MM-DD) or Indian (DD/MM/YYYY) format."""
    if not date_str or not isinstance(date_str, str):
        return None
    clean = date_str.strip()
    if not clean:
        return None

    # Try ISO YYYY-MM-DD
    try:
        return datetime.strptime(clean, "%Y-%m-%d").date()
    except ValueError:
        pass

    # Try Indian DD/MM/YYYY
    try:
        return datetime.strptime(clean, "%d/%m/%Y").date()
    except ValueError:
        pass

    # Try DD-MM-YYYY
    try:
        return datetime.strptime(clean, "%d-%m-%Y").date()
    except ValueError:
        pass

    return None


def calculate_sowing_date_from_age(crop_age_days: int, ref_date: Optional[date] = None) -> date:
    """Estimates sowing date from farmer-provided crop age in days."""
    today = ref_date or date.today()
    age = max(0, int(crop_age_days))
    return today - timedelta(days=age)


def calculate_sowing_date_from_stage(crop_name: str, stage_id_or_name: str, ref_date: Optional[date] = None) -> date:
    """Estimates sowing date from farmer-selected growth stage."""
    today = ref_date or date.today()
    calendar = get_crop_calendar(crop_name)
    if not calendar or not calendar.get("stages"):
        return today - timedelta(days=20)

    clean_stage = stage_id_or_name.strip().lower()
    matched_stage = None
    for s in calendar["stages"]:
        if s["stage_id"].lower() == clean_stage or clean_stage in s["name"].lower() or clean_stage in s["hindi_name"].lower():
            matched_stage = s
            break

    if not matched_stage:
        matched_stage = calendar["stages"][0]

    median_day = (matched_stage["start_day"] + matched_stage["end_day"]) // 2
    return today - timedelta(days=median_day)


_WEATHER_CACHE: Dict[str, Tuple[datetime, Dict[str, Any]]] = {}

def get_farm_weather_context(farm: Optional[Farm]) -> Dict[str, Any]:
    """Fetches live meteorological data for farm coordinates with caching and graceful fallback."""
    if not farm or farm.latitude is None or farm.longitude is None:
        return {
            "available": False,
            "status": "unavailable",
            "message": "Weather data unavailable (location coordinates not configured).",
            "rain_forecast_next_48h": False,
            "precipitation_sum_48h": 0.0,
            "high_wind": False,
            "high_temp": False,
            "condition": "Clear",
            "temp": 26.0
        }

    cache_key = f"{round(farm.latitude, 3)}_{round(farm.longitude, 3)}"
    now = datetime.now(timezone.utc)
    if cache_key in _WEATHER_CACHE:
        cached_time, cached_data = _WEATHER_CACHE[cache_key]
        if (now - cached_time).total_seconds() < 300:  # 5 minutes TTL
            return cached_data

    try:
        data = fetch_weather_data(farm.latitude, farm.longitude, location_name=farm.location_name, forecast_days=7)

        current = data.get("current", {})
        daily = data.get("daily_forecast", [])

        # Check next 48 hours rain
        precip_sum_48h = 0.0
        rain_prob_max = 0
        if daily:
            for day_item in daily[:2]:
                precip_sum_48h += float(day_item.get("precipitation_sum") or 0.0)
                rain_prob_max = max(rain_prob_max, int(day_item.get("precipitation_probability") or 0))

        rain_expected = precip_sum_48h >= 2.0 or rain_prob_max >= 50
        curr_wind = float(current.get("wind_speed_10m") or 0.0)
        curr_temp = float(current.get("temperature_2m") or 25.0)

        result = {
            "available": True,
            "status": "success",
            "message": "Live meteorological data active.",
            "current_temp": curr_temp,
            "current_condition": current.get("condition", "Partly Cloudy"),
            "current_wind_speed": curr_wind,
            "rain_forecast_next_48h": rain_expected,
            "precipitation_sum_48h": round(precip_sum_48h, 1),
            "rain_probability_max_48h": rain_prob_max,
            "high_wind": curr_wind > 18.0,
            "high_temp": curr_temp > 36.0,
            "daily_forecast": daily
        }
        _WEATHER_CACHE[cache_key] = (now, result)
        return result
    except Exception as e:
        return {
            "available": False,
            "status": "error",
            "message": f"Weather API currently unavailable: {str(e)}",
            "rain_forecast_next_48h": False,
            "precipitation_sum_48h": 0.0,
            "high_wind": False,
            "high_temp": False
        }


def get_farm_iot_context(db: Session, farm: Optional[Farm]) -> Dict[str, Any]:
    """Fetches IoT telemetry and soil moisture sensor reading with graceful fallback."""
    try:
        telemetry = get_latest_telemetry(db)
        if not telemetry:
            return {
                "available": False,
                "status": "no_device",
                "message": "Sensor data unavailable. Please use manual soil observation or soil test."
            }

        is_online = telemetry.get("is_online", False)
        soil_moisture = telemetry.get("soil_moisture")
        temp = telemetry.get("temperature")
        device_id = telemetry.get("device_id", "MAITRI_ESP32_01")

        if soil_moisture is not None:
            moisture_val = float(soil_moisture)
            status_desc = "Optimal" if 35.0 <= moisture_val <= 65.0 else ("Low / Dry" if moisture_val < 35.0 else "High / Saturated")
            return {
                "available": True,
                "is_online": is_online,
                "device_id": device_id,
                "soil_moisture": moisture_val,
                "temperature": temp,
                "moisture_status": status_desc,
                "is_dry": moisture_val < 32.0,
                "is_saturated": moisture_val > 68.0,
                "message": f"Sensor Soil Moisture: {moisture_val}% ({status_desc})"
            }

        return {
            "available": False,
            "status": "no_reading",
            "message": "Sensor data unavailable. Please use manual soil observation or soil test."
        }
    except Exception:
        return {
            "available": False,
            "status": "error",
            "message": "Sensor data unavailable. Please use manual soil observation or soil test."
        }


def generate_task_list_for_stage(
    crop_name: str,
    stage: Dict[str, Any],
    crop_age_day: int,
    target_date: date,
    farm: Optional[Farm],
    weather_ctx: Dict[str, Any],
    iot_ctx: Dict[str, Any],
    pest_observation: Optional[PestObservation] = None
) -> List[Dict[str, Any]]:
    """
    Synthesizes intelligent, stage-relevant tasks for a specific date and crop age.
    Modifies tasks dynamically based on weather conditions and soil sensor readings.
    """
    tasks = []
    stage_name = stage["name"]
    critical_irrigation = stage.get("critical_irrigation", False)
    irrigation_note = stage.get("irrigation_note", "")
    crop_norm = normalize_crop_key(crop_name)

    # 1. Irrigation Task (Evidence-based)
    rain_expected = weather_ctx.get("rain_forecast_next_48h", False)
    precip_sum = weather_ctx.get("precipitation_sum_48h", 0.0)
    rain_prob = weather_ctx.get("rain_probability_max_48h", 0)
    soil_dry = iot_ctx.get("is_dry", False)
    soil_saturated = iot_ctx.get("is_saturated", False)
    moisture_val = iot_ctx.get("soil_moisture")

    if stage["stage_id"] in ["maturity", "harvest", "maturity_harvest", "boll_bursting_picking"]:
        # Do not irrigate near harvest
        tasks.append({
            "category": "💧 Irrigation",
            "title": "Hold Irrigation (Pre-Harvest Drydown)",
            "description": "Keep field dry to allow uniform grain/pod ripening and firm footing for harvesting equipment.",
            "priority": "LOW",
            "estimated_duration": "15 mins",
            "why_needed": "Irrigating at maturity causes delayed drying, grain lodging, and mold infection.",
            "action_steps": "Ensure all irrigation valves/channels are closed.",
            "source": "ICAR Package of Practices",
            "plan_updated_reason": None
        })
    elif rain_expected:
        tasks.append({
            "category": "💧 Irrigation",
            "title": "Postpone Irrigation & Check Drainage",
            "description": f"Forecast indicates {precip_sum}mm rainfall ({rain_prob}% probability) over the next 48 hours. Postpone irrigation.",
            "priority": "HIGH",
            "estimated_duration": "30 mins",
            "why_needed": "Rainfall will provide natural soil moisture. Irrigating now risks waterlogging and root aeration stress.",
            "action_steps": "Hold irrigation pumps. Clear drainage furrows and field outlets to prevent water stagnation.",
            "source": "MAITTRI Weather Forecast Advisory",
            "plan_updated_reason": "MAITTRI updated this task because rainfall is forecast."
        })
    elif iot_ctx.get("available") and soil_dry:
        tasks.append({
            "category": "💧 Irrigation",
            "title": f"Critical Irrigation Check (Soil Moisture: {moisture_val}%)",
            "description": f"IoT telemetry indicates soil moisture is low ({moisture_val}%). Critical crop growth demands moisture check.",
            "priority": "HIGH",
            "estimated_duration": "45 mins",
            "why_needed": f"Current stage ({stage_name}) requires adequate root-zone moisture to maintain transpiration and nutrient uptake.",
            "action_steps": f"Inspect field soil directly. Apply scheduled irrigation (check furrow/drip lines). {irrigation_note}",
            "source": "MAITTRI IoT Soil Moisture Trigger",
            "plan_updated_reason": "MAITTRI elevated this priority because IoT sensor detected low soil moisture."
        })
    elif iot_ctx.get("available") and soil_saturated:
        tasks.append({
            "category": "💧 Irrigation",
            "title": f"Soil Moisture Adequate ({moisture_val}%) — Skip Irrigation",
            "description": f"Sensor confirms adequate soil moisture ({moisture_val}%). No additional watering required today.",
            "priority": "LOW",
            "estimated_duration": "15 mins",
            "why_needed": "Excess irrigation wastes water and promotes fungal root rots.",
            "action_steps": "Do not irrigate today. Re-evaluate moisture status in 2 days.",
            "source": "MAITTRI IoT Soil Moisture Monitor",
            "plan_updated_reason": None
        })
    elif critical_irrigation:
        tasks.append({
            "category": "💧 Irrigation",
            "title": f"Monitor Soil Moisture ({stage_name})",
            "description": f"{stage_name} is a critical moisture window. {irrigation_note}",
            "priority": "HIGH",
            "estimated_duration": "30 mins",
            "why_needed": "Moisture stress during this sensitive physiological milestone causes irreversible yield reduction.",
            "action_steps": "Check soil moisture by hand (feel-and-appearance method) or sensor. Irrigate if soil ball crumbles easily.",
            "source": "ICAR Critical Growth Stage Standard",
            "plan_updated_reason": None
        })
    else:
        tasks.append({
            "category": "💧 Irrigation",
            "title": "Routine Soil Moisture Inspection",
            "description": "Inspect root zone moisture. Sensor data unavailable. Please use manual soil observation.",
            "priority": "LOW",
            "estimated_duration": "20 mins",
            "why_needed": "Maintains optimum plant hydration without water excess.",
            "action_steps": "Observe soil in 2-3 spots across the plot.",
            "source": "Agronomic Routine Practice",
            "plan_updated_reason": None
        })

    # 2. Fertilizer / Nutrient Management Task
    fert_guidance = stage.get("fertilizer_guidance", "")
    if fert_guidance and "No application" not in fert_guidance and "None" not in fert_guidance:
        tasks.append({
            "category": "🧪 Fertilizer",
            "title": f"Nutrient Timing ({stage_name})",
            "description": fert_guidance,
            "priority": "HIGH" if stage.get("start_day", 0) <= crop_age_day <= stage.get("start_day", 0) + 7 else "MEDIUM",
            "estimated_duration": "45 mins",
            "why_needed": "Supplying nutrients synchronously with maximum crop uptake efficiency maximizes fertilizer recovery and yield.",
            "action_steps": "Review dosage on MAITTRI Fertilizer Recommendation module. Exact quantity should be based on soil test and official/local agricultural recommendation.",
            "source": "ICAR / State Agricultural University Fertilizer Schedule",
            "plan_updated_reason": None
        })

    # 3. Pest & Disease Scouting Task
    pest_guidance = stage.get("pest_disease_scouting", "")
    if pest_observation:
        tasks.append({
            "category": "🐛 Pest & Disease",
            "title": f"Follow-up on Existing Pest/Disease Observation",
            "description": f"Active observation logged: {pest_observation.pest_name or pest_observation.disease_name or 'Crop Symptoms'}. Severity: {pest_observation.severity}.",
            "priority": "HIGH",
            "estimated_duration": "30 mins",
            "why_needed": "Unmonitored pest or pathogen populations can rapidly cross economic injury levels (EIL).",
            "action_steps": "Inspect affected plot area. Compare symptoms on MAITTRI Pest Management module. Avoid spraying broad-spectrum chemicals blindly.",
            "source": "MAITTRI Farm Health Record",
            "plan_updated_reason": "Follow-up required from logged farm pest observation."
        })
    elif pest_guidance:
        high_wind = weather_ctx.get("high_wind", False)
        wind_note = " (Note: High wind speed observed — avoid chemical spraying until wind subsides below 15 km/h to prevent spray drift)" if high_wind else ""
        tasks.append({
            "category": "🐛 Pest & Disease",
            "title": f"Scout Field for {stage_name} Pests",
            "description": f"{pest_guidance}{wind_note}",
            "priority": "MEDIUM",
            "estimated_duration": "30 mins",
            "why_needed": "Early detection in the initial incubation period enables cultural or biological control before major crop damage.",
            "action_steps": "Walk diagonally across the field (W-pattern). Inspect lower leaf undersides and stems on at least 20 random plants.",
            "source": "Directorate of Plant Protection & Quarantine (DPPQS) Surveillance Guide",
            "plan_updated_reason": "Spray caution updated due to wind forecast." if high_wind else None
        })

    # 4. Weeding / Intercultural Operations
    weed_guidance = stage.get("weeding_guidance", "")
    if weed_guidance and "None" not in weed_guidance:
        tasks.append({
            "category": "🌿 Weeding",
            "title": f"Intercultural Operations & Weed Check",
            "description": weed_guidance,
            "priority": "MEDIUM",
            "estimated_duration": "45 mins",
            "why_needed": "Weeds compete for critical sunlight, water, and soil nutrients during the critical crop-weed competition period.",
            "action_steps": "Execute manual hoeing, mechanical weeding, or target roguing as recommended.",
            "source": "ICAR Weed Management Guide",
            "plan_updated_reason": None
        })

    # 5. Crop Growth & Stand Monitoring
    actions = stage.get("actions", [])
    if actions:
        tasks.append({
            "category": "🌱 Crop Growth",
            "title": f"Crop Growth & Stand Inspection",
            "description": actions[0],
            "priority": "MEDIUM",
            "estimated_duration": "30 mins",
            "why_needed": f"Confirms healthy transition into the {stage_name} phase and verifies plant population density.",
            "action_steps": " ".join(actions[:2]),
            "source": "Agronomic Package of Practices",
            "plan_updated_reason": None
        })

    # 6. Weather-Related Precaution (Dynamic)
    if weather_ctx.get("available"):
        condition = weather_ctx.get("current_condition", "Clear")
        high_temp = weather_ctx.get("high_temp", False)
        if high_temp:
            tasks.append({
                "category": "🌦️ Weather",
                "title": "High Temperature Precaution",
                "description": "Day temperatures exceeding 36°C. Monitor crop for midday wilting or accelerated moisture loss.",
                "priority": "MEDIUM",
                "estimated_duration": "20 mins",
                "why_needed": "Heat spikes cause high vapor pressure deficit (VPD) and pollen desiccation during flowering.",
                "action_steps": "Maintain light moisture in root zone to buffer soil temperatures.",
                "source": "MAITTRI Agrometeorological Advisory",
                "plan_updated_reason": "MAITTRI added this advisory due to forecast high temperatures."
            })

    # 7. Harvest & Mandi Market Planning (If in late stages)
    total_dur = stage.get("end_day", 120)
    if crop_age_day >= (total_dur - 18) or stage["stage_id"] in ["maturity", "harvest", "maturity_harvest"]:
        tasks.append({
            "category": "💰 Market",
            "title": "Mandi Market Price Check & Harvest Logistics",
            "description": f"Crop is approaching harvest ({crop_age_day} DAS). Track market trends and prepare clean storage/transport.",
            "priority": "HIGH",
            "estimated_duration": "30 mins",
            "why_needed": "Comparing regional mandis ensures you sell at favorable rates and prevents distress selling at harvest glut.",
            "action_steps": "Check live mandi arrivals and MSP comparisons on MAITTRI Market Price page. Arrange tarpaulins and clean gunny bags.",
            "source": "AGMARKNET / e-NAM Mandi Price Intelligence",
            "plan_updated_reason": None
        })

    # 8. Parali / Residue Management (If Rice or Wheat near harvest)
    if crop_norm in ["rice", "wheat"] and (crop_age_day >= (total_dur - 15) or stage["stage_id"] in ["harvest", "maturity_harvest"]):
        tasks.append({
            "category": "♻️ Residue / Parali",
            "title": "Crop Residue Management Planning",
            "description": f"Plan non-burning residue management for {crop_name} straw (Happy Seeder, Super SMS, or Bio-decomposer).",
            "priority": "HIGH",
            "estimated_duration": "30 mins",
            "why_needed": "Burning residue destroys beneficial soil microbiota, causes severe air pollution, and leads to statutory penalties.",
            "action_steps": "Book Custom Hiring Center machinery early or prepare bio-decomposer spray. See MAITTRI Parali Management module.",
            "source": "Central Pollution Control Board (CPCB) & CRM Guidelines",
            "plan_updated_reason": None
        })

    # 9. Government Schemes & Insurance Deadlines
    if crop_age_day <= 30:
        tasks.append({
            "category": "🛡️ Insurance",
            "title": "PMFBY Crop Insurance Enrollment Check",
            "description": "Verify enrollment cut-off dates for Pradhan Mantri Fasal Bima Yojana for this season.",
            "priority": "MEDIUM",
            "estimated_duration": "20 mins",
            "why_needed": "Provides comprehensive financial protection against yield losses from natural drought, flood, or pests.",
            "action_steps": "Check notified crops and premium limits on MAITTRI Insurance Planning page.",
            "source": "PMFBY Official Guidelines",
            "plan_updated_reason": None
        })

    return tasks


def generate_full_farm_plan_data(
    crop_name: str,
    sowing_date: date,
    farm: Optional[Farm],
    db: Session,
    reference_date: Optional[date] = None,
    variety: Optional[str] = None
) -> Dict[str, Any]:
    """
    Core planning engine that computes:
    - Today's date, crop age, current growth stage
    - Top 3 priorities with "Why MAITTRI recommends this"
    - Complete 7-day plan (Today + next 6 days)
    - Full crop lifecycle visual timeline
    - Weekly milestones for the entire season
    - Digital diary history
    """
    ref_date = reference_date or date.today()
    crop_age_days = max(0, (ref_date - sowing_date).days)
    calendar = get_crop_calendar(crop_name)

    if not calendar:
        # Graceful fallback if crop calendar is missing
        return {
            "crop": crop_name,
            "sowing_date": sowing_date.isoformat(),
            "crop_age_days": crop_age_days,
            "current_stage": {
                "stage_id": "generic",
                "name": "General Cultivation",
                "hindi_name": "सामान्य कृषि विकास",
                "description": "Crop calendar data is currently unavailable for this crop."
            },
            "today_goals": {
                "date": ref_date.isoformat(),
                "top_priorities": [],
                "why_maittri_recommends": "Crop calendar data is currently unavailable. We cannot generate an accurate stage-based plan."
            },
            "week_plan": [],
            "timeline": [],
            "weekly_milestones": []
        }

    # Contexts
    weather_ctx = get_farm_weather_context(farm)
    iot_ctx = get_farm_iot_context(db, farm)

    # Check for existing pest observation on this farm
    pest_obs = None
    if farm:
        pest_obs = db.query(PestObservation).filter(
            PestObservation.farm_id == farm.id
        ).order_by(desc(PestObservation.observed_at)).first()

    current_stage = get_crop_stage_for_day(crop_name, crop_age_days)
    timeline_stages = calculate_calendar_dates(crop_name, sowing_date)

    # Mark active stage in timeline
    for st in timeline_stages:
        st["is_current"] = (st["start_day"] <= crop_age_days <= st["end_day"])

    # Generate Today's Tasks
    today_tasks_raw = generate_task_list_for_stage(
        crop_name=crop_name,
        stage=current_stage,
        crop_age_day=crop_age_days,
        target_date=ref_date,
        farm=farm,
        weather_ctx=weather_ctx,
        iot_ctx=iot_ctx,
        pest_observation=pest_obs
    )

    # Sort Today's Tasks by Priority (HIGH first, then MEDIUM, then LOW)
    priority_weights = {"HIGH": 3, "MEDIUM": 2, "LOW": 1}
    sorted_today = sorted(today_tasks_raw, key=lambda x: priority_weights.get(x["priority"], 0), reverse=True)

    # Pick Top 3 Important Tasks
    top_3 = sorted_today[:3]
    other_tasks = sorted_today[3:]

    # Construct "Why MAITTRI recommends this"
    why_text_reasons = []
    why_text_reasons.append(f"फसल की आयु {crop_age_days} दिन है और यह '{current_stage.get('hindi_name')}' अवस्था में है।")
    if weather_ctx.get("rain_forecast_next_48h"):
        why_text_reasons.append(f"आगामी 48 घंटों में {weather_ctx.get('precipitation_sum_48h')}mm वर्षा का पूर्वानुमान है, इसलिए जल प्रबंधन को सर्वोच्च प्राथमिकता दी गई है।")
    elif iot_ctx.get("available") and iot_ctx.get("is_dry"):
        why_text_reasons.append(f"खेत में लगे सेंसर के अनुसार मृदा नमी कम ({iot_ctx.get('soil_moisture')}%) है, इसलिए सिंचाई की तत्काल जांच जरूरी है।")
    elif current_stage.get("critical_irrigation"):
        why_text_reasons.append(f"यह अवस्था फसल की वृद्धि के लिए अत्यंत संवेदनशील (Critical Stage) है।")

    why_recommendation_hi = " ".join(why_text_reasons)
    why_recommendation_en = (
        f"Crop age is {crop_age_days} days in '{current_stage.get('name')}' stage. "
        + ("Rainfall is forecast in the next 48 hours, dynamically modifying water management. " if weather_ctx.get("rain_forecast_next_48h") else "")
        + (f"IoT sensor detected low soil moisture ({iot_ctx.get('soil_moisture')}%), triggering irrigation priority. " if iot_ctx.get("available") and iot_ctx.get("is_dry") else "")
        + ("This is an agronomically critical growth milestone requiring close monitoring." if current_stage.get("critical_irrigation") else "")
    )

    # Build 7-Day Plan (This Week's Plan)
    week_plan = []
    days_of_week_en = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    days_of_week_hi = ["सोमवार", "मंगलवार", "बुधवार", "गुरुवार", "शुक्रवार", "शनिवार", "रविवार"]

    for day_offset in range(7):
        curr_d = ref_date + timedelta(days=day_offset)
        curr_age = crop_age_days + day_offset
        curr_stage_day = get_crop_stage_for_day(crop_name, curr_age)

        # Weather consideration for this day
        day_weather = "Normal"
        if weather_ctx.get("daily_forecast") and day_offset < len(weather_ctx["daily_forecast"]):
            fc = weather_ctx["daily_forecast"][day_offset]
            day_weather = f"{fc.get('condition', 'Normal')} · Rain: {fc.get('precipitation_probability', 0)}%"

        day_tasks = generate_task_list_for_stage(
            crop_name=crop_name,
            stage=curr_stage_day,
            crop_age_day=curr_age,
            target_date=curr_d,
            farm=farm,
            weather_ctx=weather_ctx,
            iot_ctx=iot_ctx,
            pest_observation=pest_obs
        )

        # Assign unique temporary IDs for UI
        for idx, t in enumerate(day_tasks):
            t["id"] = f"task_{curr_d.isoformat()}_{idx}"
            t["task_date"] = curr_d.isoformat()
            t["task_date_display"] = curr_d.strftime("%d/%m/%Y")
            t["status"] = "pending"

        main_goal = curr_stage_day.get("actions", ["General crop maintenance"])[0] if curr_stage_day.get("actions") else "General crop maintenance"

        week_plan.append({
            "date": curr_d.isoformat(),
            "date_display": curr_d.strftime("%d/%m/%Y"),
            "day_name_en": days_of_week_en[curr_d.weekday()],
            "day_name_hi": days_of_week_hi[curr_d.weekday()],
            "crop_age_day": curr_age,
            "growth_stage_en": curr_stage_day.get("name"),
            "growth_stage_hi": curr_stage_day.get("hindi_name"),
            "main_goal": main_goal,
            "tasks": day_tasks[:4], # Keep 3-4 distinct tasks per day
            "priority": "HIGH" if any(t["priority"] == "HIGH" for t in day_tasks) else "MEDIUM",
            "weather_consideration": day_weather,
            "status": "Pending"
        })

    # Build Weekly Lifecycle Milestones (Week 1, Week 2... Harvest)
    total_days = calendar.get("typical_duration_days", 120)
    weekly_milestones = []
    total_weeks = (total_days + 6) // 7

    for w in range(1, total_weeks + 1):
        w_start_day = (w - 1) * 7 + 1
        w_end_day = min(w * 7, total_days)
        mid_day = (w_start_day + w_end_day) // 2
        w_stage = get_crop_stage_for_day(crop_name, mid_day)

        w_start_date = sowing_date + timedelta(days=w_start_day)
        w_end_date = sowing_date + timedelta(days=w_end_day)

        is_current_week = (w_start_day <= crop_age_days <= w_end_day)
        is_past = crop_age_days > w_end_day

        weekly_milestones.append({
            "week_number": w,
            "title": f"Week {w}: {w_stage.get('name')}",
            "title_hi": f"सप्ताह {w}: {w_stage.get('hindi_name')}",
            "days_range": f"Day {w_start_day}–{w_end_day}",
            "date_range": f"{w_start_date.strftime('%d/%m/%Y')} – {w_end_date.strftime('%d/%m/%Y')}",
            "growth_stage": w_stage.get("name"),
            "growth_stage_hi": w_stage.get("hindi_name"),
            "is_current": is_current_week,
            "is_past": is_past,
            "key_focus": w_stage.get("description"),
            "key_actions": w_stage.get("actions", [])
        })

    # Upcoming Government Schemes & Insurance relevant to farm
    schemes = get_upcoming_schemes(state=farm.location_name if farm else None)[:3]

    # Mandi price snapshot if near harvest
    mandi_snapshot = None
    if crop_age_days >= total_days - 20:
        try:
            mandi_snapshot = get_latest_market_price(crop=crop_name, state=farm.location_name if farm else None)
        except Exception:
            mandi_snapshot = None

    return {
        "crop": crop_name,
        "hindi_name": calendar.get("hindi_name", crop_name),
        "scientific_name": calendar.get("scientific_name", ""),
        "variety": variety or "Standard Certified Variety",
        "sowing_date": sowing_date.isoformat(),
        "sowing_date_display": sowing_date.strftime("%d/%m/%Y"),
        "reference_date": ref_date.isoformat(),
        "reference_date_display": ref_date.strftime("%d/%m/%Y"),
        "crop_age_days": crop_age_days,
        "typical_duration_days": total_days,
        "days_to_harvest": max(0, total_days - crop_age_days),
        "current_stage": {
            "stage_id": current_stage.get("stage_id"),
            "name": current_stage.get("name"),
            "hindi_name": current_stage.get("hindi_name"),
            "description": current_stage.get("description"),
            "hindi_description": current_stage.get("hindi_description"),
            "critical_irrigation": current_stage.get("critical_irrigation", False)
        },
        "today_goals": {
            "date": ref_date.isoformat(),
            "date_display": ref_date.strftime("%d/%m/%Y"),
            "priority": "HIGH" if any(t["priority"] == "HIGH" for t in top_3) else "MEDIUM",
            "top_3_priorities": top_3,
            "other_tasks": other_tasks,
            "why_maittri_recommends_hi": why_recommendation_hi,
            "why_maittri_recommends_en": why_recommendation_en
        },
        "week_plan": week_plan,
        "timeline": timeline_stages,
        "weekly_milestones": weekly_milestones,
        "weather_context": weather_ctx,
        "iot_context": iot_ctx,
        "mandi_snapshot": mandi_snapshot,
        "schemes_snapshot": schemes,
        "official_sources": calendar.get("official_sources", [])
    }


def create_or_update_persisted_plan(
    db: Session,
    user_id: Optional[int],
    farm_id: int,
    crop_name: str,
    sowing_date: date,
    variety: Optional[str] = None
) -> Tuple[FarmPlan, Dict[str, Any]]:
    """
    Saves or regenerates a personalized farm plan in the database.
    Populates FarmPlanTask rows for today's active tasks while preserving
    existing completion records.
    """
    farm = db.query(Farm).filter(Farm.id == farm_id).first()
    plan_data = generate_full_farm_plan_data(
        crop_name=crop_name,
        sowing_date=sowing_date,
        farm=farm,
        db=db,
        variety=variety
    )

    # Check if a plan already exists for this farm
    existing_plan = db.query(FarmPlan).filter(
        FarmPlan.farm_id == farm_id,
        FarmPlan.selected_crop == crop_name
    ).order_by(desc(FarmPlan.id)).first()

    if existing_plan:
        existing_plan.sowing_date = sowing_date.isoformat()
        existing_plan.variety = variety
        existing_plan.current_stage = plan_data["current_stage"]["name"]
        existing_plan.plan_data_json = json.dumps(plan_data)
        existing_plan.updated_at = datetime.now(timezone.utc)
        plan_record = existing_plan
    else:
        plan_record = FarmPlan(
            farm_id=farm_id,
            user_id=user_id,
            selected_crop=crop_name,
            sowing_date=sowing_date.isoformat(),
            variety=variety,
            current_stage=plan_data["current_stage"]["name"],
            plan_json=json.dumps(plan_data.get("timeline", [])),
            plan_data_json=json.dumps(plan_data)
        )
        db.add(plan_record)

    db.commit()
    db.refresh(plan_record)

    # Persist / sync FarmPlanTask rows for today's goals
    today_str = plan_data["reference_date"]
    top_3 = plan_data["today_goals"]["top_3_priorities"]
    other = plan_data["today_goals"]["other_tasks"]

    # Delete previous non-completed tasks for this plan on today to avoid duplicates
    db.query(FarmPlanTask).filter(
        FarmPlanTask.farm_plan_id == plan_record.id,
        FarmPlanTask.task_date == today_str,
        FarmPlanTask.status == "pending"
    ).delete()

    created_tasks = []
    for idx, t in enumerate(top_3 + other):
        task_row = FarmPlanTask(
            farm_plan_id=plan_record.id,
            task_date=today_str,
            crop_age_day=plan_data["crop_age_days"],
            growth_stage=plan_data["current_stage"]["name"],
            category=t.get("category", "🌱 Crop Growth"),
            title=t.get("title", "Farm Task"),
            description=t.get("description", ""),
            priority=t.get("priority", "MEDIUM"),
            estimated_duration=t.get("estimated_duration", "30 mins"),
            source=t.get("source", "ICAR Guidance"),
            status="pending",
            why_needed=t.get("why_needed", ""),
            action_steps=t.get("action_steps", ""),
            is_top_priority=(idx < 3),
            plan_updated_reason=t.get("plan_updated_reason")
        )
        db.add(task_row)
        created_tasks.append(task_row)

    # Also update farm.current_crop and farm.sowing_date if farm exists
    if farm:
        farm.current_crop = crop_name
        farm.sowing_date = sowing_date.isoformat()

    db.commit()

    # Re-read tasks to supply real DB task IDs to the plan response
    db_tasks = db.query(FarmPlanTask).filter(
        FarmPlanTask.farm_plan_id == plan_record.id,
        FarmPlanTask.task_date == today_str
    ).all()

    task_map = {t.title: t for t in db_tasks}
    for t in plan_data["today_goals"]["top_3_priorities"]:
        if t["title"] in task_map:
            t["id"] = task_map[t["title"]].id
            t["status"] = task_map[t["title"]].status

    for t in plan_data["today_goals"]["other_tasks"]:
        if t["title"] in task_map:
            t["id"] = task_map[t["title"]].id
            t["status"] = task_map[t["title"]].status

    plan_data["plan_id"] = plan_record.id
    return plan_record, plan_data


def mark_farm_task_complete(
    db: Session,
    task_id: int,
    status: str = "completed",
    notes: Optional[str] = None
) -> Dict[str, Any]:
    """
    Marks task complete or pending and creates a historical entry in FarmPlanCompletion (Farm Diary).
    Captures live weather and sensor readings as context in the digital diary.
    """
    task = db.query(FarmPlanTask).filter(FarmPlanTask.id == task_id).first()
    if not task:
        raise ValueError(f"Task #{task_id} not found")

    task.status = status
    task.updated_at = datetime.now(timezone.utc)

    plan = db.query(FarmPlan).filter(FarmPlan.id == task.farm_plan_id).first()
    farm = db.query(Farm).filter(Farm.id == plan.farm_id).first() if plan else None

    # Capture snapshots for the farm diary
    weather_ctx = get_farm_weather_context(farm)
    iot_ctx = get_farm_iot_context(db, farm)

    weather_snap = {
        "temp": weather_ctx.get("current_temp"),
        "condition": weather_ctx.get("current_condition"),
        "wind": weather_ctx.get("current_wind_speed")
    } if weather_ctx.get("available") else None

    sensor_snap = {
        "soil_moisture": iot_ctx.get("soil_moisture"),
        "temp": iot_ctx.get("temperature"),
        "status": iot_ctx.get("moisture_status")
    } if iot_ctx.get("available") else None

    completion = None
    if status == "completed":
        completion = FarmPlanCompletion(
            task_id=task.id,
            farm_plan_id=task.farm_plan_id,
            task_title=task.title,
            category=task.category,
            growth_stage=task.growth_stage,
            crop_age_day=task.crop_age_day,
            completion_date=datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            completed_at=datetime.now(timezone.utc),
            farmer_notes=notes,
            sensor_snapshot_json=json.dumps(sensor_snap) if sensor_snap else None,
            weather_snapshot_json=json.dumps(weather_snap) if weather_snap else None
        )
        db.add(completion)

    db.commit()
    db.refresh(task)

    return {
        "task_id": task.id,
        "status": task.status,
        "updated_at": task.updated_at.isoformat(),
        "notes": notes,
        "completion_recorded": completion is not None
    }


def add_task_farmer_note(
    db: Session,
    task_id: int,
    notes: str
) -> Dict[str, Any]:
    """Adds or updates a farmer observation note for a specific task."""
    task = db.query(FarmPlanTask).filter(FarmPlanTask.id == task_id).first()
    if not task:
        raise ValueError(f"Task #{task_id} not found")

    completion = db.query(FarmPlanCompletion).filter(
        FarmPlanCompletion.task_id == task_id
    ).order_by(desc(FarmPlanCompletion.id)).first()

    if completion:
        completion.farmer_notes = notes
    else:
        # If not already completed, record note against task
        completion = FarmPlanCompletion(
            task_id=task.id,
            farm_plan_id=task.farm_plan_id,
            task_title=task.title,
            category=task.category,
            growth_stage=task.growth_stage,
            crop_age_day=task.crop_age_day,
            completion_date=datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            completed_at=datetime.now(timezone.utc),
            farmer_notes=notes
        )
        db.add(completion)

    db.commit()
    return {"task_id": task.id, "notes": notes, "success": True}


def get_farm_diary_history(db: Session, farm_plan_id: int) -> List[Dict[str, Any]]:
    """Retrieves all completed tasks and historical observations for the farm diary."""
    completions = db.query(FarmPlanCompletion).filter(
        FarmPlanCompletion.farm_plan_id == farm_plan_id
    ).order_by(desc(FarmPlanCompletion.completed_at)).all()

    records = []
    for c in completions:
        records.append({
            "id": c.id,
            "task_id": c.task_id,
            "task_title": c.task_title,
            "category": c.category,
            "growth_stage": c.growth_stage,
            "crop_age_day": c.crop_age_day,
            "completion_date": c.completion_date,
            "completed_at": c.completed_at.isoformat() if c.completed_at else None,
            "completed_at_display": c.completed_at.strftime("%d/%m/%Y %I:%M %p") if c.completed_at else c.completion_date,
            "farmer_notes": c.farmer_notes,
            "sensor_snapshot": json.loads(c.sensor_snapshot_json) if c.sensor_snapshot_json else None,
            "weather_snapshot": json.loads(c.weather_snapshot_json) if c.weather_snapshot_json else None
        })
    return records
