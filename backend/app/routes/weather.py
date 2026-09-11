from fastapi import APIRouter, HTTPException, Query
from typing import Optional
import requests
from ..schemas import WeatherRequest

router = APIRouter()

WMO_CODE_MAP = {
    0: {"label": "Clear Sky", "icon": "sun", "is_rain": False},
    1: {"label": "Mainly Clear", "icon": "sun", "is_rain": False},
    2: {"label": "Partly Cloudy", "icon": "cloud-sun", "is_rain": False},
    3: {"label": "Overcast", "icon": "cloud", "is_rain": False},
    45: {"label": "Fog", "icon": "cloud-fog", "is_rain": False},
    48: {"label": "Depositing Rime Fog", "icon": "cloud-fog", "is_rain": False},
    51: {"label": "Light Drizzle", "icon": "cloud-drizzle", "is_rain": True},
    53: {"label": "Moderate Drizzle", "icon": "cloud-drizzle", "is_rain": True},
    55: {"label": "Dense Drizzle", "icon": "cloud-drizzle", "is_rain": True},
    61: {"label": "Slight Rain", "icon": "cloud-rain", "is_rain": True},
    63: {"label": "Moderate Rain", "icon": "cloud-rain", "is_rain": True},
    65: {"label": "Heavy Rain", "icon": "cloud-rain", "is_rain": True},
    71: {"label": "Slight Snow", "icon": "cloud-snow", "is_rain": False},
    73: {"label": "Moderate Snow", "icon": "cloud-snow", "is_rain": False},
    75: {"label": "Heavy Snow", "icon": "cloud-snow", "is_rain": False},
    80: {"label": "Slight Rain Showers", "icon": "cloud-rain", "is_rain": True},
    81: {"label": "Moderate Rain Showers", "icon": "cloud-rain", "is_rain": True},
    82: {"label": "Violent Rain Showers", "icon": "cloud-lightning", "is_rain": True},
    95: {"label": "Thunderstorm", "icon": "cloud-lightning", "is_rain": True},
    96: {"label": "Thunderstorm with Slight Hail", "icon": "cloud-lightning", "is_rain": True},
    99: {"label": "Thunderstorm with Heavy Hail", "icon": "cloud-lightning", "is_rain": True},
}

def get_weather_desc(code: Optional[int]) -> dict:
    if code is None:
        return {"label": "Unknown", "icon": "cloud-sun", "is_rain": False}
    return WMO_CODE_MAP.get(int(code), {"label": "Partly Cloudy", "icon": "cloud-sun", "is_rain": False})

def generate_agricultural_advisories(current: dict, daily: dict, hourly: dict) -> dict:
    """Generate actionable, crop-focused advisories based on meteorological metrics."""
    curr_temp = current.get("temperature_2m") if current.get("temperature_2m") is not None else 25
    curr_humidity = current.get("relative_humidity_2m") if current.get("relative_humidity_2m") is not None else 50
    curr_wind = current.get("wind_speed_10m") if current.get("wind_speed_10m") is not None else 5

    # Next 24 hours stats
    rain_probs = [p for p in hourly.get("precipitation_probability", [])[:24] if p is not None]
    max_rain_prob_24h = max(rain_probs) if rain_probs else 0
    winds_24h = [w for w in hourly.get("wind_speed_10m", [])[:24] if w is not None]
    max_wind_24h = max(winds_24h) if winds_24h else curr_wind

    # Next 48 hours rain sum
    precip_sums = [p for p in daily.get("precipitation_sum", [])[:2] if p is not None]
    rain_sum_48h = sum(precip_sums) if precip_sums else 0
    daily_rain_probs = [p for p in daily.get("precipitation_probability_max", [])[:2] if p is not None]
    max_rain_prob_48h = max(daily_rain_probs) if daily_rain_probs else max_rain_prob_24h

    # 1. Spraying Suitability
    if curr_wind > 15 or max_wind_24h > 18:
        spraying = {
            "status": "unfavorable",
            "badge": "Unfavorable",
            "title": "High Wind: Spray Drift Hazard",
            "reason": f"Wind speeds ({curr_wind} km/h, up to {max_wind_24h} km/h) cause chemical spray drift, poor foliar coverage, and non-target damage.",
            "recommendation": "Postpone herbicide/pesticide spraying until wind drops below 12 km/h (typically early morning)."
        }
    elif max_rain_prob_24h >= 40:
        spraying = {
            "status": "unfavorable",
            "badge": "Unfavorable",
            "title": "Rain Risk: Chemical Washout",
            "reason": f"Precipitation probability is {max_rain_prob_24h}% within 24h. Rain within 4–6 hours of application washes away active ingredients.",
            "recommendation": "Delay spraying operations until after rain passes and crop leaves dry."
        }
    else:
        spraying = {
            "status": "favorable",
            "badge": "Favorable",
            "title": "Optimal Spraying Conditions",
            "reason": f"Calm wind ({curr_wind} km/h) and low rain risk ({max_rain_prob_24h}%) ensure excellent droplet retention and absorption.",
            "recommendation": "Ideal window for foliar fertilizers, bio-stimulants, and crop protection sprays."
        }

    # 2. Irrigation Guidance
    if rain_sum_48h >= 10 or max_rain_prob_48h >= 65:
        irrigation = {
            "status": "postpone",
            "badge": "Postpone",
            "title": "Natural Rainfall Imminent",
            "reason": f"Expected rainfall ({rain_sum_48h:.1f} mm) or high rain probability ({max_rain_prob_48h}%) in the next 48 hours.",
            "recommendation": "Hold off on irrigation to avoid soil waterlogging, nutrient leaching, and unnecessary water expenditure."
        }
    elif curr_temp >= 36 and curr_humidity <= 30:
        irrigation = {
            "status": "alert",
            "badge": "Irrigate Soon",
            "title": "High Evaporative Demand",
            "reason": f"High temperature ({curr_temp}°C) combined with dry air ({curr_humidity}% humidity) increases crop evapotranspiration.",
            "recommendation": "Schedule light, frequent irrigation during early morning or evening to prevent plant moisture stress."
        }
    else:
        irrigation = {
            "status": "normal",
            "badge": "Normal",
            "title": "Standard Moisture Management",
            "reason": "Atmospheric demand and precipitation outlook are within steady ranges.",
            "recommendation": "Maintain standard irrigation intervals suited to your current crop stage and soil moisture."
        }

    # 3. Disease & Pest Risk
    if curr_humidity >= 80 and (18 <= curr_temp <= 32):
        disease = {
            "status": "warning",
            "badge": "Elevated Risk",
            "title": "Fungal Disease Environment",
            "reason": f"Warm temperatures ({curr_temp}°C) and high humidity ({curr_humidity}%) favor spore germination (rust, blight, downy mildew).",
            "recommendation": "Scout dense canopy areas for leaf spots or lesions; avoid overhead sprinkler irrigation."
        }
    else:
        disease = {
            "status": "low",
            "badge": "Low Risk",
            "title": "Low Disease Pressure",
            "reason": "Humidity and temperature levels do not indicate accelerated fungal incubation.",
            "recommendation": "Routine monitoring is sufficient."
        }

    # 4. Temperature Stress Alerts
    t_max_list = [t for t in daily.get("temperature_2m_max", []) if t is not None]
    max_temp_week = max(t_max_list) if t_max_list else curr_temp
    t_min_list = [t for t in daily.get("temperature_2m_min", []) if t is not None]
    min_temp_week = min(t_min_list) if t_min_list else curr_temp

    temp_alerts = []
    if max_temp_week >= 40:
        temp_alerts.append({
            "level": "critical",
            "title": "Severe Heat Stress Warning",
            "message": f"Maximum temperature will reach {max_temp_week}°C. Risk of flower drop, pollen sterility, and rapid soil drying. Provide shade if cultivating sensitive vegetables."
        })
    if min_temp_week <= 4:
        temp_alerts.append({
            "level": "critical",
            "title": "Frost / Cold Injury Alert",
            "message": f"Minimum temperature drops to {min_temp_week}°C. Potential chilling injury for sensitive crops. Consider mulch or light evening irrigation."
        })

    return {
        "spraying": spraying,
        "irrigation": irrigation,
        "disease": disease,
        "alerts": temp_alerts
    }

def fetch_weather_data(lat: float, lon: float, location_name: Optional[str] = None, forecast_days: int = 7) -> dict:
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "current": "temperature_2m,relative_humidity_2m,apparent_temperature,precipitation,weather_code,wind_speed_10m,wind_direction_10m,surface_pressure,is_day",
        "hourly": "temperature_2m,relative_humidity_2m,precipitation_probability,precipitation,wind_speed_10m,weather_code",
        "daily": "weather_code,temperature_2m_max,temperature_2m_min,precipitation_sum,precipitation_probability_max,wind_speed_10m_max,uv_index_max,sunrise,sunset",
        "forecast_days": max(1, min(forecast_days, 14)),
        "timezone": "auto"
    }
    r = requests.get(url, params=params, timeout=10)
    r.raise_for_status()
    raw = r.json()

    current_raw = raw.get("current", {})
    daily_raw = raw.get("daily", {})
    hourly_raw = raw.get("hourly", {})

    # Enrich current weather
    current_code = current_raw.get("weather_code")
    current_desc = get_weather_desc(current_code)
    current = {
        **current_raw,
        "condition": current_desc["label"],
        "icon": current_desc["icon"],
        "is_rain": current_desc["is_rain"]
    }

    # Enrich daily forecast
    daily_times = daily_raw.get("time", [])
    daily_codes = daily_raw.get("weather_code", [])
    t_max = daily_raw.get("temperature_2m_max", [])
    t_min = daily_raw.get("temperature_2m_min", [])
    precip_sums = daily_raw.get("precipitation_sum", [])
    precip_probs = daily_raw.get("precipitation_probability_max", [])
    wind_maxs = daily_raw.get("wind_speed_10m_max", [])
    uv_maxs = daily_raw.get("uv_index_max", [])

    daily_forecast = []
    for i in range(len(daily_times)):
        code = daily_codes[i] if i < len(daily_codes) else 0
        desc = get_weather_desc(code)
        daily_forecast.append({
            "date": daily_times[i],
            "weather_code": code,
            "condition": desc["label"],
            "icon": desc["icon"],
            "temp_max": t_max[i] if i < len(t_max) else None,
            "temp_min": t_min[i] if i < len(t_min) else None,
            "precipitation_sum": precip_sums[i] if i < len(precip_sums) else 0,
            "precipitation_probability": precip_probs[i] if i < len(precip_probs) else 0,
            "wind_speed_max": wind_maxs[i] if i < len(wind_maxs) else 0,
            "uv_index_max": uv_maxs[i] if i < len(uv_maxs) else 0
        })

    # Hourly (first 24 hours)
    hourly_times = hourly_raw.get("time", [])[:24]
    hourly_temps = hourly_raw.get("temperature_2m", [])[:24]
    hourly_humids = hourly_raw.get("relative_humidity_2m", [])[:24]
    hourly_rain_probs = hourly_raw.get("precipitation_probability", [])[:24]
    hourly_rains = hourly_raw.get("precipitation", [])[:24]
    hourly_winds = hourly_raw.get("wind_speed_10m", [])[:24]
    hourly_codes = hourly_raw.get("weather_code", [])[:24]

    hourly_forecast = []
    for i in range(len(hourly_times)):
        code = hourly_codes[i] if i < len(hourly_codes) else 0
        desc = get_weather_desc(code)
        hourly_forecast.append({
            "time": hourly_times[i],
            "temperature": hourly_temps[i] if i < len(hourly_temps) else None,
            "humidity": hourly_humids[i] if i < len(hourly_humids) else None,
            "rain_probability": hourly_rain_probs[i] if i < len(hourly_rain_probs) else 0,
            "precipitation": hourly_rains[i] if i < len(hourly_rains) else 0,
            "wind_speed": hourly_winds[i] if i < len(hourly_winds) else 0,
            "condition": desc["label"],
            "icon": desc["icon"]
        })

    # Generate advisories
    advisories = generate_agricultural_advisories(current_raw, daily_raw, hourly_raw)

    return {
        "location": {
            "latitude": lat,
            "longitude": lon,
            "name": location_name or f"{lat:.2f}, {lon:.2f}",
            "timezone": raw.get("timezone", "auto")
        },
        "current": current,
        "daily": daily_forecast,
        "hourly": hourly_forecast,
        "advisories": advisories,
        "alerts": advisories.get("alerts", [])
    }

@router.post("")
def get_weather_post(payload: WeatherRequest):
    try:
        return fetch_weather_data(
            lat=payload.latitude,
            lon=payload.longitude,
            location_name=payload.location_name,
            forecast_days=payload.forecast_days
        )
    except Exception as e:
        raise HTTPException(502, f"Weather service unavailable: {str(e)}")

@router.get("")
def get_weather_get(
    latitude: float = Query(..., ge=-90.0, le=90.0),
    longitude: float = Query(..., ge=-180.0, le=180.0),
    location_name: Optional[str] = Query(None),
    forecast_days: int = Query(7, ge=1, le=14)
):
    try:
        return fetch_weather_data(
            lat=latitude,
            lon=longitude,
            location_name=location_name,
            forecast_days=forecast_days
        )
    except Exception as e:
        raise HTTPException(502, f"Weather service unavailable: {str(e)}")
