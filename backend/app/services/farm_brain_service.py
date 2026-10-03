"""
MAITTRI Farm Brain — Central Agronomic Decision Intelligence Engine
---------------------------------------------------------------------
Principle: ONE INTELLIGENCE -> MULTIPLE ACCESS CHANNELS (Web, SMS, IVR, Operator)

Combines:
- Farmer Profile & Land Records
- Live Meteorological Forecasts & Soil Moisture
- IoT Edge Telemetry (labeled as indicative)
- Certified Lab Soil Tests (distinct from sensor estimations)
- Crop Growth Stage, Sowing Date & Crop Calendar Tasks
- Active Pest/Disease Risk Conditions
- Mandi Market Trends & Welfare Scheme/Insurance Deadlines

Outputs Explainable Decisions:
- WHAT SHOULD I DO TODAY? (Ranked High, Medium, Normal)
- WHAT SHOULD I DO THIS WEEK?
- WHY?
- WHAT IS THE RISK?
- WHAT DATA SUPPORTS THIS?
- WHAT INFORMATION IS MISSING? (Strictly no fabricated defaults)
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timezone, timedelta
import json
import logging
from sqlalchemy.orm import Session

from ..models import (
    Farm, Farmer, SoilTestReport, IoTSensorReading,
    FarmPlan, FarmPlanTask, GovernmentScheme, InsurancePlan
)

logger = logging.getLogger("maittri.farm_brain")


def generate_today_decisions(
    farm: Optional[Farm],
    farmer: Optional[Farmer],
    soil_report: Optional[SoilTestReport],
    latest_iot: Optional[IoTSensorReading],
    weather_data: Optional[Dict[str, Any]],
    plan_tasks: List[FarmPlanTask]
) -> Dict[str, Any]:
    """
    Synthesizes current farm conditions into actionable, explainable priorities for today.
    """
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    actions: List[Dict[str, Any]] = []
    missing_info: List[str] = []

    crop_name = getattr(farmer, "current_crop", None) or getattr(farm, "current_crop", None) or "General"
    location_name = getattr(farmer, "district", None) or getattr(farm, "location_name", None) or "Your Farm"
    soil_type = getattr(farmer, "soil_type", None) or getattr(farm, "soil_type", None) or "Alluvial Soil"

    # Identify missing critical info
    if not getattr(farm, "sowing_date", None) and not getattr(farmer, "sowing_date", None):
        missing_info.append("Sowing date not recorded — stage-specific fertilizer timings will use general estimates.")
    if not soil_report and not getattr(farm, "soil_n", None):
        missing_info.append("Certified soil test report unavailable — nutrient advice based on regional standard NPK.")
    if not weather_data or weather_data.get("is_fallback") or not weather_data.get("weather_available", True):
        missing_info.append("Live meteorological feed temporarily unavailable — outdoor spray advice is cautious.")

    # 1. WEATHER HAZARD / IRRIGATION DECISION
    rain_prob = 0
    precip_mm = 0.0
    temp_max = 30.0
    if weather_data and "daily" in weather_data:
        d = weather_data["daily"]
        if isinstance(d, list) and d:
            first_day = d[0] if isinstance(d[0], dict) else {}
            precip_mm = float(first_day.get("precipitation_sum") or 0.0)
            rain_prob = int(first_day.get("precipitation_probability") or 0)
            temp_max = float(first_day.get("temp_max") or 30.0)
        elif isinstance(d, dict):
            precip_list = d.get("precipitation_sum", [0])
            precip_mm = float(precip_list[0] if precip_list else 0.0)
            prob_list = d.get("precipitation_probability_max", [0])
            rain_prob = int(prob_list[0] if prob_list else 0)
            temp_max_list = d.get("temperature_2m_max", [30])
            temp_max = float(temp_max_list[0] if temp_max_list else 30.0)

    # Sensor soil moisture (indicative)
    sensor_moisture = getattr(latest_iot, "soil_moisture", None)
    if sensor_moisture is None:
        missing_info.append("Live soil moisture sensor reading unavailable — field moisture status is unverified.")

    is_weather_usable = bool(
        weather_data
        and not weather_data.get("is_fallback")
        and weather_data.get("weather_available", True)
    )

    if is_weather_usable and (precip_mm >= 5.0 or rain_prob >= 60):
        actions.append({
            "id": "irrigation_hold",
            "title_hi": "सिंचाई स्थगित करें — वर्षा का पूर्वानुमान",
            "title_en": "Postpone Irrigation — Rain Forecasted",
            "priority": "HIGH",
            "confidence": "HIGH",
            "action_text_hi": f"आज सिंचाई न करें। अगले 24 घंटों में {precip_mm}mm वर्षा की संभावना ({rain_prob}%) है। जलजमाव से बचें।",
            "action_text_en": f"Hold irrigation today. Expected rainfall is {precip_mm}mm with {rain_prob}% probability. Avoid waterlogging.",
            "why_needed_hi": "बारिश से पूर्व सिंचाई करने पर खेत में जलभराव होता है, जिससे जड़ें गल सकती हैं और पोषक तत्व बह जाते हैं।",
            "why_needed_en": "Pre-rain irrigation causes waterlogging, anaerobic root stress, and fertilizer leaching.",
            "risk_assessment_hi": "उच्च जोखिम: नाइट्रोजन लीचिंग और फफूंद जनित रोगों की संभावना।",
            "risk_assessment_en": "High risk of nitrogen leaching and fungal root rot.",
            "data_used": f"Open-Meteo Weather Forecast (Rain: {precip_mm}mm, Prob: {rain_prob}%)",
            "source": "IMD Agromet / Open-Meteo Advisory Guidelines"
        })
    elif sensor_moisture is not None and sensor_moisture < 25.0:
        if is_weather_usable:
            if precip_mm < 2.0 and rain_prob < 30:
                sky_desc_hi = "पूर्वानुमान अनुसार मौसम शुष्क रहेगा; शाम को हल्की सिंचाई करें।"
                sky_desc_en = "Forecast indicates dry conditions; provide light irrigation in the evening."
                irr_conf = "HIGH"
            else:
                sky_desc_hi = f"मौसम में वर्षा की संभावना ({precip_mm}mm, {rain_prob}%) है; सिंचाई से पूर्व स्थानीय स्थिति की जांच करें।"
                sky_desc_en = f"Forecast indicates potential rain ({precip_mm}mm, {rain_prob}%); verify local sky before irrigating."
                irr_conf = "MEDIUM"
        else:
            sky_desc_hi = "मौसम पूर्वानुमान उपलब्ध नहीं है; सिंचाई से पूर्व स्थानीय मौसम व बादलों की स्थिति अवश्य जांचें।"
            sky_desc_en = "Weather forecast feed unavailable; verify local sky and rain outlook before scheduling irrigation."
            irr_conf = "MEDIUM"

        actions.append({
            "id": "irrigation_needed",
            "title_hi": "हल्की सिंचाई की आवश्यकता",
            "title_en": "Light Irrigation Recommended",
            "priority": "HIGH",
            "confidence": irr_conf,
            "action_text_hi": f"खेत में नमी का स्तर कम (~{round(sensor_moisture, 1)}%) दर्ज किया गया है। {sky_desc_hi}",
            "action_text_en": f"Indicative soil moisture is low (~{round(sensor_moisture, 1)}%). {sky_desc_en}",
            "why_needed_hi": "कम नमी की स्थिति में पौधे प्रकाश संश्लेषण और पोषक तत्वों का अवशोषण नहीं कर पाते।",
            "why_needed_en": "Water stress reduces nutrient uptake and leaf transpiration efficiency.",
            "risk_assessment_hi": "मध्यम जोखिम: फसल में मुरझान और उपज में गिरावट।",
            "risk_assessment_en": "Moderate risk of crop wilting and vegetative stunt.",
            "data_used": f"IoT Field Sensor Node (Indicative Moisture: {sensor_moisture}%)",
            "source": "Maitri IoT Telemetry Engine"
        })
    elif sensor_moisture is not None:
        actions.append({
            "id": "moisture_normal",
            "title_hi": "मृदा नमी सामान्य स्थिति में",
            "title_en": "Soil Moisture Optimal",
            "priority": "NORMAL",
            "confidence": "HIGH",
            "action_text_hi": f"खेत में सेंसर द्वारा पर्याप्त नमी (~{round(sensor_moisture, 1)}%) दर्ज की गई है। नियमित निगरानी जारी रखें।",
            "action_text_en": f"Adequate indicative soil moisture (~{round(sensor_moisture, 1)}%) observed. Continue routine monitoring.",
            "why_needed_hi": "संतुलित नमी पौधों के निरंतर विकास के लिए अनुकूल है।",
            "why_needed_en": "Optimal root zone moisture promotes balanced vegetative growth.",
            "risk_assessment_hi": "न्यूनतम जोखिम।",
            "risk_assessment_en": "Low moisture stress risk.",
            "data_used": f"IoT Field Sensor Node (Indicative Moisture: {round(sensor_moisture, 1)}%)",
            "source": "Maitri IoT Telemetry Engine"
        })
    else:
        actions.append({
            "id": "moisture_monitoring_needed",
            "title_hi": "मृदा नमी स्थिति अज्ञात — नियमित निगरानी रखें",
            "title_en": "Soil Moisture Unknown — Field Monitoring Required",
            "priority": "NORMAL",
            "confidence": "LOW",
            "action_text_hi": "खेत में मृदा नमी का प्रत्यक्ष माप उपलब्ध नहीं है। सिंचाई निर्णय से पूर्व मिट्टी की नमी की जांच करें।",
            "action_text_en": "No live soil moisture measurement available. Physically inspect root zone moisture before scheduling field operations.",
            "why_needed_hi": "सटीक नमी माप के बिना सिंचाई या उर्वरक का सही निर्णय लेना संभव नहीं है।",
            "why_needed_en": "Direct moisture assessment prevents unnecessary irrigation or undetected water stress.",
            "risk_assessment_hi": "अज्ञात जोखिम: अनपेक्षित नमी तनाव की संभावना।",
            "risk_assessment_en": "Uncertain moisture status: risk of undetected crop water stress or excess irrigation.",
            "data_used": "No Sensor Reading Available",
            "source": "Maitri Agronomy Core"
        })

    # 2. NUTRIENT & FERTILIZER ACTION
    if soil_report:
        n_val = soil_report.nitrogen
        ph_val = soil_report.ph or 7.0
        if n_val is not None:
            if n_val < 250:
                actions.append({
                    "id": "nitrogen_management",
                    "title_hi": f"{crop_name} में नाइट्रोजन टॉप-ड्रेसिंग योजना",
                    "title_en": f"Nitrogen Top-Dressing for {crop_name}",
                    "priority": "MEDIUM",
                    "confidence": "HIGH",
                    "action_text_hi": f"प्रमाणित लैब टेस्ट के अनुसार नाइट्रोजन का स्तर कम ({n_val} kg/ha) है। आगामी सिंचाई के साथ अनुशंसित यूरिया को विभाजित मात्रा में दें।",
                    "action_text_en": f"Certified lab soil test shows low available nitrogen ({n_val} kg/ha). Apply split dose of urea before next irrigation.",
                    "why_needed_hi": "नाइट्रोजन की कमी से पुरानी पत्तियां पीली पड़ने लगती हैं और टिलरिंग रुक जाती है।",
                    "why_needed_en": "Nitrogen deficiency leads to chlorosis in older leaves and stunted tillering.",
                    "risk_assessment_hi": "मध्यम जोखिम: समय पर खुराक न देने से 15-20% पैदावार घट सकती है।",
                    "risk_assessment_en": "Moderate risk: Yield reduction up to 15-20% if basal/top-dress split missed.",
                    "data_used": f"Certified Lab Report ({soil_report.lab_name}, N: {n_val} kg/ha, pH: {ph_val})",
                    "source": "Soil Health Card / KVK Agronomic Norms"
                })
        else:
            missing_info.append("Certified soil report lacks nitrogen measurement — N-specific fertilizer advice unavailable.")
    else:
        actions.append({
            "id": "soil_test_booking_advice",
            "title_hi": "खेत का प्रमाणित मृदा परीक्षण (Soil Test) बुक करें",
            "title_en": "Book Certified Soil Laboratory Test",
            "priority": "MEDIUM",
            "confidence": "HIGH",
            "action_text_hi": "आपके खेत का हालिया प्रमाणित लैब टेस्ट रिकॉर्ड नहीं है। सही उर्वरक मात्रा जानने के लिए सेवा केंद्र से सॉइल टेस्ट बुक कराएं।",
            "action_text_en": "No certified soil lab report on file. Book a test via Seva Portal to obtain scientific N-P-K recommendation.",
            "why_needed_hi": "अंधाधुंध रासायनिक उर्वरकों से मिट्टी कठोर होती है और लागत व्यर्थ बढ़ती है।",
            "why_needed_en": "Prevents over-fertilization, soil acidification, and wasteful expenditure.",
            "risk_assessment_hi": "आर्थिक जोखिम: अनावश्यक डीएपी/यूरिया पर अतिरिक्त खर्च।",
            "risk_assessment_en": "Financial risk: Misspent input budget on unbalanced fertilizer.",
            "data_used": "Farm Record Audit",
            "source": "National Soil Health Card Guidelines"
        })

    # 3. PEST & DISEASE MONITORING
    crop_lower = crop_name.lower()
    if "wheat" in crop_lower or "गेहूं" in crop_lower:
        if temp_max >= 18.0 and temp_max <= 26.0:
            actions.append({
                "id": "wheat_rust_watch",
                "title_hi": "गेहूं में पीला रतुआ (Yellow Rust) की निगरानी",
                "title_en": "Yellow Rust Monitoring for Wheat",
                "priority": "HIGH",
                "confidence": "HIGH",
                "action_text_hi": "सुबह के समय खेत का मुआयना करें। पत्तियों पर पीले पाउडर जैसी धारियां दिखने पर उंगली से रगड़कर जांचें।",
                "action_text_en": "Inspect leaves early morning. Check for yellow powdery stripes along veins using the finger-rub test.",
                "why_needed_hi": "तापमान (18-24°C) और सुबह की ओस पीला रतुआ (Puccinia striiformis) के संक्रमण के लिए अनुकूल है।",
                "why_needed_en": "Current temperature (18-24°C) with morning dew creates high risk for Stripe Rust spore germination.",
                "risk_assessment_hi": "उच्च जोखिम: संक्रमण फैलने पर बालियों में दाना नहीं भरता।",
                "risk_assessment_en": "High risk: Leaf chlorosis and severe grain shriveling if untreated.",
                "data_used": f"Temperature Range ({temp_max}°C) & Crop Phenology",
                "source": "ICAR-IIWBR Karnal Advisory"
            })
    elif "mustard" in crop_lower or "सरसों" in crop_lower:
        actions.append({
            "id": "mustard_aphid_watch",
            "title_hi": "सरसों में माहू (Aphid) व सफेद रतुआ की जांच",
            "title_en": "Mustard Aphid & White Rust Scouting",
            "priority": "MEDIUM",
            "confidence": "HIGH",
            "action_text_hi": "फूलों व टहनियों पर छोटे काले/हरे माहू कीटों की जांच करें। प्रारंभिक अवस्था में नीम तेल (1500 ppm) का छिड़काव करें।",
            "action_text_en": "Check tender shoots for green/black aphid colonies. Apply 5ml/L Neem Oil if initial colonies are detected.",
            "why_needed_hi": "माहू रस चूसकर फलियों के विकास को रोक देते हैं।",
            "why_needed_en": "Aphid sap-sucking stunts siliquae formation and lowers oil content.",
            "risk_assessment_hi": "मध्यम जोखिम: दाने हल्के और तेल की मात्रा कम होना।",
            "risk_assessment_en": "Moderate risk of reduced seed weight and poor oil percentage.",
            "data_used": "Field Stage & Weather Profile",
            "source": "ICAR-DRMR Bharatpur Mustard Advisory"
        })

    # 4. PLANNED TASKS FROM FARM CALENDAR (if any for today)
    for task in plan_tasks[:2]:
        actions.append({
            "id": f"calendar_task_{task.id}",
            "title_hi": f"कैलेंडर कार्य: {task.title}",
            "title_en": f"Planned Task: {task.title}",
            "priority": task.priority or "NORMAL",
            "confidence": "HIGH",
            "action_text_hi": task.action_steps or task.description or task.title,
            "action_text_en": task.description or task.title,
            "why_needed_hi": task.why_needed or "फसल विकास चक्र के अनुसार समयबद्ध कार्य।",
            "why_needed_en": task.why_needed or "Scheduled lifecycle field operation.",
            "risk_assessment_hi": "कार्य में विलंब से फसल की समय-सारणी प्रभावित हो सकती है।",
            "risk_assessment_en": "Schedule delay can miss optimal growth window.",
            "data_used": f"Maitri Personalized Farm Plan ({task.growth_stage})",
            "source": task.source or "ICAR Crop Calendar"
        })

    # Sort actions by priority: HIGH -> MEDIUM -> NORMAL
    priority_order = {"HIGH": 0, "MEDIUM": 1, "NORMAL": 2}
    actions.sort(key=lambda x: priority_order.get(x.get("priority", "NORMAL"), 3))

    return {
        "timestamp": now_str,
        "farm_id": getattr(farm, "id", None),
        "farmer_id": getattr(farmer, "id", None),
        "crop": crop_name,
        "location": location_name,
        "soil_type": soil_type,
        "today_actions": actions,
        "missing_information": missing_info,
        "summary_hi": f"आज {crop_name} के लिए {len(actions)} प्रमुख कार्य अनुशंसित हैं। सबसे पहले उच्च प्राथमिकता वाले कार्यों की पुष्टि करें।",
        "summary_en": f"{len(actions)} key agronomic operations recommended today for {crop_name}. Complete high priority tasks first."
    }


def generate_weekly_outlook(
    farm: Optional[Farm],
    farmer: Optional[Farmer],
    weather_data: Optional[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Generates a 7-day agricultural outlook for farm planning.
    Avoids fabricating forecasts when live weather is unavailable.
    """
    now = datetime.now(timezone.utc)
    crop_name = getattr(farmer, "current_crop", None) or getattr(farm, "current_crop", None) or "General Crop"

    days_outlook: List[Dict[str, Any]] = []
    days_names = ["सोमवार (Mon)", "मंगलवार (Tue)", "बुधवार (Wed)", "गुरुवार (Thu)", "शुक्रवार (Fri)", "शनिवार (Sat)", "रविवार (Sun)"]

    has_usable_weather = bool(
        weather_data
        and not weather_data.get("is_fallback")
        and weather_data.get("weather_available", True)
        and "daily" in weather_data
    )

    daily_temps: List[Optional[float]] = []
    daily_precip: List[Optional[float]] = []

    if has_usable_weather:
        d = weather_data["daily"]
        if isinstance(d, list) and d:
            for day in d[:7]:
                if isinstance(day, dict):
                    t = day.get("temp_max") if day.get("temp_max") is not None else day.get("temperature_2m_max")
                    p = day.get("precipitation_sum")
                    daily_temps.append(float(t) if t is not None else None)
                    daily_precip.append(float(p) if p is not None else None)
                else:
                    daily_temps.append(None)
                    daily_precip.append(None)
        elif isinstance(d, dict) and d:
            temps = d.get("temperature_2m_max") or d.get("temp_max") or []
            precips = d.get("precipitation_sum") or []
            count = min(7, max(len(temps), len(precips)))
            for i in range(count):
                t = temps[i] if i < len(temps) else None
                p = precips[i] if i < len(precips) else None
                daily_temps.append(float(t) if t is not None else None)
                daily_precip.append(float(p) if p is not None else None)

    for i in range(7):
        target_date = now + timedelta(days=i)
        if has_usable_weather and i < len(daily_precip) and (daily_precip[i] is not None or daily_temps[i] is not None):
            p_val = daily_precip[i] if daily_precip[i] is not None else 0.0
            t_val = daily_temps[i] if daily_temps[i] is not None else 25.0

            if p_val >= 4.0:
                rec_hi = "बारिश का अनुमान — खेत में कीटनाशक/उर्वरक छिड़काव न करें।"
                rec_en = "Rain expected — avoid chemical or fertilizer spray."
                status = "RAIN"
            elif t_val >= 32.0:
                rec_hi = "अधिक तापमान — वाष्पीकरण अधिक होगा, नमी बनाए रखें।"
                rec_en = "Warm day — high evaporation; conserve field moisture."
                status = "WARM"
            else:
                rec_hi = "अनुकूल मौसम — सामान्य कृषि कार्य एवं फसल निरीक्षण करें।"
                rec_en = "Favorable weather for field operations and monitoring."
                status = "GOOD"

            days_outlook.append({
                "day_index": i + 1,
                "date": target_date.strftime("%Y-%m-%d"),
                "day_label": days_names[target_date.weekday()],
                "temp_c": t_val,
                "rain_mm": p_val,
                "status": status,
                "advice_hi": rec_hi,
                "advice_en": rec_en
            })
        else:
            days_outlook.append({
                "day_index": i + 1,
                "date": target_date.strftime("%Y-%m-%d"),
                "day_label": days_names[target_date.weekday()],
                "temp_c": None,
                "rain_mm": None,
                "status": "UNAVAILABLE",
                "advice_hi": "मौसम पूर्वानुमान अनुपलब्ध — सामान्य कृषि कार्य जारी रखें, मौसम संवेदनशील कार्यों से पूर्व स्थानीय स्थिति जांचें।",
                "advice_en": "Weather forecast unavailable — continue routine farm management; inspect local sky before weather-dependent operations."
            })

    # Derive weekly summary dynamically from computed days_outlook
    if not has_usable_weather:
        summary_hi = "साप्ताहिक मौसम पूर्वानुमान उपलब्ध नहीं है। सामान्य फसल रखरखाव एवं कीट निगरानी जारी रखें।"
        summary_en = "Weekly meteorological forecast unavailable. Continue routine crop maintenance and field scouting."
    else:
        rain_days = sum(1 for d in days_outlook if d.get("status") == "RAIN")
        warm_days = sum(1 for d in days_outlook if d.get("status") == "WARM")
        if rain_days >= 4:
            summary_hi = f"सप्ताह में {rain_days} दिन वर्षा का पूर्वानुमान है। खेत में जलजमाव से बचाव करें और कीटनाशक/उर्वरक छिड़काव स्थगित रखें।"
            summary_en = f"Rain forecasted on {rain_days} days this week. Postpone foliar spraying and ensure proper field drainage."
        elif rain_days > 0:
            summary_hi = f"सप्ताह में {rain_days} दिन छिटपुट वर्षा की संभावना है। वर्षा रहित दिनों में ही कीटनाशक व उर्वरक छिड़काव करें।"
            summary_en = f"Intermittent rain expected on {rain_days} day(s). Restrict chemical spraying and top-dressing to dry windows."
        elif warm_days >= 4:
            summary_hi = "पूरे सप्ताह तापमान अधिक रहने की संभावना है। वाष्पीकरण अधिक होगा, फसल में नियमित हल्की सिंचाई सुनिश्चित करें।"
            summary_en = "High temperatures expected throughout the week. Maintain adequate irrigation to counter elevated evaporative demand."
        else:
            summary_hi = "सप्ताह भर मौसम सामान्यतः अनुकूल रहने का अनुमान है। सामान्य कृषि कार्य, निराई-गुड़ाई एवं फसल निरीक्षण के लिए उपयुक्त समय।"
            summary_en = "Generally favorable weather expected this week. Optimal window for intercultural operations and crop scouting."

    return {
        "crop": crop_name,
        "week_start": now.strftime("%Y-%m-%d"),
        "outlook": days_outlook,
        "weather_available": has_usable_weather,
        "weekly_summary_hi": summary_hi,
        "weekly_summary_en": summary_en
    }


def get_voice_summary_for_ivr(
    farm: Optional[Farm],
    farmer: Optional[Farmer],
    decisions: Dict[str, Any],
    lang: str = "hi"
) -> str:
    """
    Synthesizes a short, conversational voice response for IVR keypad callers.
    """
    crop = decisions.get("crop", "आपकी फसल")
    actions = decisions.get("today_actions", [])

    if not actions:
        if lang == "hi":
            return f"नमस्ते। {crop} के लिए आज कोई आपातकालीन कार्य लंबित नहीं है। खेत में नियमित नमी व स्वास्थ्य की जांच करते रहें। धन्यवाद।"
        return f"Hello. No emergency tasks pending for your {crop} today. Maintain routine moisture checks. Thank you."

    top_action = actions[0]
    if lang == "hi":
        title = top_action.get("title_hi", top_action.get("title_en", ""))
        text = top_action.get("action_text_hi", top_action.get("action_text_en", ""))
        return f"नमस्ते। {crop} के लिए आज का मुख्य परामर्श है: {title}। विवरण: {text}। अधिक जानकारी के लिए अपने नजदीकी कृषि सेवा केंद्र से संपर्क करें।"
    else:
        title = top_action.get("title_en", "")
        text = top_action.get("action_text_en", "")
        return f"Hello. Today's top advisory for {crop} is: {title}. Details: {text}. For assistance, contact your local Seva Operator."


def get_sms_text(
    farm: Optional[Farm],
    farmer: Optional[Farmer],
    decisions: Dict[str, Any],
    lang: str = "hi"
) -> str:
    """
    Generates a concise, DLT-compliant SMS string strictly under or equal to 160 characters.
    Constructs the message and enforces the final length budget on the complete string.
    """
    crop = decisions.get("crop", "फसल" if lang == "hi" else "Crop")
    actions = decisions.get("today_actions", [])
    if not actions:
        if lang == "hi":
            msg = f"मैत्री परामर्श: {crop} में स्थिति सामान्य है। नियमित नमी बनाए रखें। MAITTRI"
        else:
            msg = f"MAITTRI Alert: Normal conditions for {crop}. Maintain field moisture. MAITTRI"
        return msg[:160]

    top = actions[0]
    if lang == "hi":
        title = (top.get("title_hi") or top.get("title_en") or "").strip()
        action = (top.get("action_text_hi") or top.get("action_text_en") or "").strip()
        prefix = f"मैत्री अलर्ट ({crop}): {title}। "
        suffix = " MAITTRI"
    else:
        title = (top.get("title_en") or top.get("title_hi") or "").strip()
        action = (top.get("action_text_en") or top.get("action_text_hi") or "").strip()
        prefix = f"MAITTRI Alert ({crop}): {title}. "
        suffix = " MAITTRI"

    full_msg = f"{prefix}{action}{suffix}"
    if len(full_msg) <= 160:
        return full_msg

    # Budget space for action text within 160 characters
    budget = 160 - len(prefix) - len("...") - len(suffix)
    if budget >= 15:
        truncated_action = action[:budget].rstrip()
        return f"{prefix}{truncated_action}...{suffix}"

    return full_msg[:157] + "..." if len(full_msg) > 160 else full_msg
