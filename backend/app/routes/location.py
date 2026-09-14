from fastapi import APIRouter, HTTPException, Query
import requests
from ..schemas import SoilEstimateRequest

router = APIRouter()

@router.get("/search")
def search_location(
    query: str = Query(..., min_length=2, description="City, district, or town name to search"),
    count: int = Query(6, ge=1, le=15)
):
    """Search for locations/cities using Open-Meteo Geocoding API with robust query sanitization."""
    try:
        raw_query = query.strip()
        # Open-Meteo geocoding takes a place name, not comma-separated full addresses
        primary_name = raw_query.split(",")[0].strip()
        search_term = primary_name if len(primary_name) >= 2 else raw_query

        url = "https://geocoding-api.open-meteo.com/v1/search"
        params = {
            "name": search_term,
            "count": count,
            "language": "en",
            "format": "json"
        }
        resp = requests.get(url, params=params, timeout=8)
        resp.raise_for_status()
        data = resp.json()
        results = data.get("results") or []

        formatted = []
        for item in results:
            name = item.get("name")
            district = item.get("admin2")
            state = item.get("admin1")
            country = item.get("country")

            # Build a human-friendly label (e.g. "Lucknow, Uttar Pradesh, India")
            parts = [name]
            if district and district != name:
                parts.append(district)
            if state and state != name and state != district:
                parts.append(state)
            if country:
                parts.append(country)

            display_name = ", ".join(parts)

            formatted.append({
                "id": item.get("id"),
                "name": name,
                "district": district,
                "state": state,
                "country": country,
                "latitude": item.get("latitude"),
                "longitude": item.get("longitude"),
                "timezone": item.get("timezone", "UTC"),
                "display_name": display_name
            })

        # If user searched with context like "UP" or "India", prioritize matches containing those terms
        if "," in raw_query:
            qualifier = raw_query.split(",", 1)[1].lower().strip()
            if qualifier:
                formatted.sort(key=lambda x: 0 if qualifier in x["display_name"].lower() else 1)

        return {"results": formatted}
    except Exception as e:
        raise HTTPException(502, f"Location search service unavailable: {str(e)}")

@router.get("/reverse")
def reverse_geocode(
    latitude: float = Query(..., ge=-90.0, le=90.0),
    longitude: float = Query(..., ge=-180.0, le=180.0)
):
    """Reverse-geocode latitude and longitude into human-readable address with dual-provider fallback."""
    # Provider 1: OpenStreetMap Nominatim
    try:
        url = "https://nominatim.openstreetmap.org/reverse"
        params = {
            "lat": latitude,
            "lon": longitude,
            "format": "json"
        }
        headers = {"User-Agent": "SmartAgricultureAI/1.0 (contact@smartagri.local)"}
        resp = requests.get(url, params=params, headers=headers, timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            address = data.get("address", {})
            city = (
                address.get("city") or
                address.get("town") or
                address.get("village") or
                address.get("county") or
                address.get("suburb") or
                address.get("state_district")
            )
            state = address.get("state")
            country = address.get("country")
            parts = [p for p in [city, state, country] if p]
            if parts:
                return {
                    "display_name": ", ".join(parts),
                    "city": city,
                    "state": state,
                    "country": country,
                    "latitude": latitude,
                    "longitude": longitude
                }
    except Exception:
        pass

    # Provider 2 Fallback: BigDataCloud free client reverse geocoding API
    try:
        bdc_url = f"https://api.bigdatacloud.net/data/reverse-geocode-client?latitude={latitude}&longitude={longitude}&localityLanguage=en"
        resp2 = requests.get(bdc_url, timeout=4)
        if resp2.status_code == 200:
            d2 = resp2.json()
            city = d2.get("city") or d2.get("locality") or d2.get("principalSubdivision")
            state = d2.get("principalSubdivision")
            country = d2.get("countryName")
            parts_dedup = []
            for p in [city, state, country]:
                if p and p not in parts_dedup:
                    parts_dedup.append(p)
            if parts_dedup:
                return {
                    "display_name": ", ".join(parts_dedup),
                    "city": city,
                    "state": state,
                    "country": country,
                    "latitude": latitude,
                    "longitude": longitude
                }
    except Exception:
        pass

    # Clean coordinate fallback if offline or third-party is unreachable
    return {
        "display_name": f"{latitude:.2f}, {longitude:.2f}",
        "city": None,
        "state": None,
        "country": None,
        "latitude": latitude,
        "longitude": longitude
    }

@router.post("/soil-estimate")
def get_soil_estimate_post(payload: SoilEstimateRequest):
    from ..services.soil_estimation_service import estimate_soil_type
    try:
        return estimate_soil_type(payload.latitude, payload.longitude)
    except Exception as e:
        raise HTTPException(500, f"Error estimating soil type: {str(e)}")

@router.get("/soil-estimate")
def get_soil_estimate_get(
    latitude: float = Query(..., ge=-90.0, le=90.0),
    longitude: float = Query(..., ge=-180.0, le=180.0)
):
    from ..services.soil_estimation_service import estimate_soil_type
    try:
        return estimate_soil_type(latitude, longitude)
    except Exception as e:
        raise HTTPException(500, f"Error estimating soil type: {str(e)}")

