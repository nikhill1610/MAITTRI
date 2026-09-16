import time
import math
import logging
from datetime import datetime, date, timedelta, timezone
from fastapi import APIRouter, HTTPException, Query
from typing import Optional, Dict, Any, Tuple
import requests
from ..schemas import WeatherRequest

logger = logging.getLogger("maitri.weather")
router = APIRouter()

# 15-minute in-memory LRU cache: (lat, lon, days) -> (timestamp, data)
_WEATHER_CACHE: Dict[Tuple[float, float, int], Tuple[float, dict]] = {}
CACHE_TTL_SECONDS = 900  # 15 minutes

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

def generate_fallback_weather_data(lat: float, lon: float, location_name: Optional[str] = None, forecast_days: int = 7) -> dict:
    """
    Generates realistic, climatologically consistent agronomic weather data
    when upstream Open-Meteo is temporarily unreachable or offline.
    """
    now = datetime.now()
    month = now.month
    forecast_days = max(1, min(forecast_days, 14))

    # Base climatology for Indian subcontinent by season
    if month in (11, 12, 1, 2):  # Rabi / Winter
        base_max, base_min = 26.0, 13.0
        base_humidity = 58.0
        base_rain_prob = 10
        wmo_code = 1  # Mainly clear
    elif month in (3, 4, 5):      # Zaid / Summer
        base_max, base_min = 38.0, 24.0
        base_humidity = 35.0
        base_rain_prob = 15
        wmo_code = 0  # Clear sky
    elif month in (6, 7, 8, 9):   # Kharif / Monsoon
        base_max, base_min = 32.0, 25.0
        base_humidity = 82.0
        base_rain_prob = 55
        wmo_code = 61  # Slight rain
    else:                         # Transition (October)
        base_max, base_min = 31.0, 20.0
        base_humidity = 65.0
        base_rain_prob = 20
        wmo_code = 2  # Partly cloudy

    # Subtle latitude modulation
    lat_mod = (lat - 22.0) * -0.3
    curr_temp = round((base_max + base_min) / 2.0 + lat_mod, 1)
    curr_hum = round(base_humidity, 1)
    desc = get_weather_desc(wmo_code)

    current = {
        "temperature_2m": curr_temp,
        "relative_humidity_2m": curr_hum,
        "apparent_temperature": round(curr_temp + 1.2, 1),
        "precipitation": 2.5 if wmo_code == 61 else 0.0,
        "weather_code": wmo_code,
        "wind_speed_10m": 8.5,
        "wind_direction_10m": 120,
        "surface_pressure": 1012.0,
        "is_day": 1,
        "condition": desc["label"],
        "icon": desc["icon"],
        "is_rain": desc["is_rain"]
    }

    # Daily Forecast
    daily = []
    t_max_list, t_min_list, p_sum_list, p_prob_list, w_max_list = [], [], [], [], []
    today = date.today()
    for i in range(forecast_days):
        d_date = (today + timedelta(days=i)).isoformat()
        t_high = round(base_max + lat_mod + (i % 3 - 1) * 0.8, 1)
        t_low = round(base_min + lat_mod + (i % 2 - 1) * 0.5, 1)
        p_prob = max(5, min(90, base_rain_prob + (i % 4 - 2) * 5))
        p_sum = round(p_prob * 0.08, 1) if p_prob > 30 else 0.0
        d_code = 61 if p_prob > 50 else wmo_code
        d_desc = get_weather_desc(d_code)

        t_max_list.append(t_high)
        t_min_list.append(t_low)
        p_sum_list.append(p_sum)
        p_prob_list.append(p_prob)
        w_max_list.append(12.0)

        daily.append({
            "date": d_date,
            "weather_code": d_code,
            "condition": d_desc["label"],
            "icon": d_desc["icon"],
            "temp_max": t_high,
            "temp_min": t_low,
            "precipitation_sum": p_sum,
            "precipitation_probability": p_prob,
            "wind_speed_max": 12.0,
            "uv_index_max": 6.5
        })

    # Hourly Forecast (24 hours)
    hourly = []
    h_temps, h_humids, h_probs, h_rains, h_winds = [], [], [], [], []
    for h in range(24):
        h_time = (now + timedelta(hours=h)).strftime("%Y-%m-%dT%H:00")
        hour_of_day = (now.hour + h) % 24
        # Diurnal temperature cycle
        temp_cycle = math.sin((hour_of_day - 9) * math.pi / 12.0)
        h_temp = round(curr_temp + temp_cycle * ((base_max - base_min) / 2.0), 1)
        h_hum = round(max(30.0, min(95.0, curr_hum - temp_cycle * 20.0)), 1)
        h_rain_prob = max(5, min(80, base_rain_prob + (h % 3) * 5))
        h_rain = 0.5 if h_rain_prob > 50 else 0.0
        h_wind = round(6.0 + abs(temp_cycle) * 5.0, 1)
        h_code = 61 if h_rain > 0 else wmo_code
        h_desc = get_weather_desc(h_code)

        h_temps.append(h_temp)
        h_humids.append(h_hum)
        h_probs.append(h_rain_prob)
        h_rains.append(h_rain)
        h_winds.append(h_wind)

        hourly.append({
            "time": h_time,
            "temperature": h_temp,
            "humidity": h_hum,
            "rain_probability": h_rain_prob,
            "precipitation": h_rain,
            "wind_speed": h_wind,
            "condition": h_desc["label"],
            "icon": h_desc["icon"]
        })

    daily_raw = {
        "temperature_2m_max": t_max_list,
        "temperature_2m_min": t_min_list,
        "precipitation_sum": p_sum_list,
        "precipitation_probability_max": p_prob_list,
        "wind_speed_10m_max": w_max_list
    }
    hourly_raw = {
        "precipitation_probability": h_probs,
        "wind_speed_10m": h_winds
    }
    advisories = generate_agricultural_advisories(current, daily_raw, hourly_raw)

    return {
        "location": {
            "latitude": lat,
            "longitude": lon,
            "name": location_name or f"{lat:.2f}, {lon:.2f}",
            "timezone": "Asia/Kolkata"
        },
        "current": current,
        "daily": daily,
        "hourly": hourly,
        "advisories": advisories,
        "alerts": advisories.get("alerts", []),
        "is_fallback": True,
        "cached": False,
        "status": "fallback",
        "advisory_note": "Offline meteorological estimation"
    }

def fetch_weather_data(lat: float, lon: float, location_name: Optional[str] = None, forecast_days: int = 7) -> dict:
    forecast_days = max(1, min(forecast_days, 14))
    cache_key = (round(float(lat), 3), round(float(lon), 3), int(forecast_days))

    # 1. Check in-memory cache
    cached_entry = _WEATHER_CACHE.get(cache_key)
    if cached_entry:
        cached_time, cached_data = cached_entry
        if time.time() - cached_time < CACHE_TTL_SECONDS:
            res = dict(cached_data)
            res["cached"] = True
            return res

    # 2. Query Open-Meteo upstream API
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "current": "temperature_2m,relative_humidity_2m,apparent_temperature,precipitation,weather_code,wind_speed_10m,wind_direction_10m,surface_pressure,is_day",
        "hourly": "temperature_2m,relative_humidity_2m,precipitation_probability,precipitation,wind_speed_10m,weather_code",
        "daily": "weather_code,temperature_2m_max,temperature_2m_min,precipitation_sum,precipitation_probability_max,wind_speed_10m_max,uv_index_max,sunrise,sunset",
        "forecast_days": forecast_days,
        "timezone": "auto"
    }

    try:
        r = requests.get(url, params=params, timeout=7)
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

        result = {
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
            "alerts": advisories.get("alerts", []),
            "cached": False,
            "is_fallback": False
        }

        # Store in cache
        _WEATHER_CACHE[cache_key] = (time.time(), result)
        return result

    except Exception as exc:
        logger.warning(f"Open-Meteo upstream call failed ({exc}). Falling back to cached/simulated data.")
        # If any cached entry exists (even expired), return it
        if cached_entry:
            res = dict(cached_entry[1])
            res["cached"] = True
            res["is_fallback"] = False
            return res
        # Otherwise, generate realistic fallback
        return generate_fallback_weather_data(lat, lon, location_name, forecast_days)

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
        logger.error(f"Unexpected error in weather POST endpoint: {e}")
        return generate_fallback_weather_data(payload.latitude, payload.longitude, payload.location_name, payload.forecast_days)

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
        logger.error(f"Unexpected error in weather GET endpoint: {e}")
        return generate_fallback_weather_data(latitude, longitude, location_name, forecast_days)

