"""
FastAPI route endpoints for Market Prices (मंडी भाव).
Supports state/district/mandi cascading selection, crop price queries,
multi-crop comparisons, historical trends, and farm profit estimations.
"""

from fastapi import APIRouter, Query, HTTPException
from typing import Optional, List
from ..services.market_price_service import (
    get_all_states,
    get_districts_for_state,
    get_mandis_for_district,
    get_available_crops,
    get_latest_market_price,
    get_other_crop_prices_in_state,
    get_crop_price_history,
    compare_multiple_crops,
    get_state_wise_crop_comparison,
    calculate_farm_profit_projection
)

router = APIRouter()

@router.get("/states")
def list_states():
    """Returns standardized list of all 36 Indian states and Union Territories."""
    return {"states": get_all_states()}

@router.get("/districts")
def list_districts(state: str = Query(..., min_length=2, description="Indian State Name")):
    """Returns available districts for the selected state."""
    districts = get_districts_for_state(state)
    return {
        "state": state,
        "districts": districts,
        "has_district_data": len(districts) > 0
    }

@router.get("/mandis")
def list_mandis(
    state: str = Query(..., min_length=2, description="Indian State Name"),
    district: str = Query(..., min_length=2, description="District Name")
):
    """Returns available mandis for the selected state and district."""
    mandis = get_mandis_for_district(state, district)
    return {
        "state": state,
        "district": district,
        "mandis": mandis,
        "has_mandi_data": len(mandis) > 0
    }

@router.get("/crops")
def list_crops():
    """Returns list of crops tracked in the market database."""
    return {"crops": get_available_crops()}

@router.get("/latest")
def get_latest_price(
    crop: str = Query(..., min_length=2, description="Crop name e.g. Wheat, Mustard"),
    state: str = Query(..., min_length=2, description="State name e.g. Uttar Pradesh"),
    district: Optional[str] = Query(None, description="Optional District name"),
    mandi: Optional[str] = Query(None, description="Optional Mandi/Market name")
):
    """Returns latest available market/mandi price for the crop in the selected location."""
    data = get_latest_market_price(crop, state, district, mandi)
    if not data:
        raise HTTPException(
            status_code=404,
            detail="Market price data is currently unavailable for this crop/location."
        )
    return data

@router.get("/state-crops")
def list_state_crops(
    state: str = Query(..., min_length=2, description="State name"),
    selected_crop: Optional[str] = Query(None, description="Selected crop to highlight")
):
    """Returns market prices of other crops in the selected state."""
    crops_data = get_other_crop_prices_in_state(state, exclude_crop=selected_crop)
    return {
        "state": state,
        "crops": crops_data,
        "count": len(crops_data)
    }

@router.get("/history")
def get_price_history(
    crop: str = Query(..., min_length=2, description="Crop name"),
    state: str = Query(..., min_length=2, description="State name"),
    district: Optional[str] = Query(None, description="Optional district"),
    mandi: Optional[str] = Query(None, description="Optional mandi"),
    days: int = Query(30, ge=7, le=180, description="Trend days: 7, 30, 90, or 180")
):
    """Returns historical price trends over the requested number of days."""
    history = get_crop_price_history(crop, state, district, mandi, days=days)
    return history

@router.get("/compare")
def compare_crops(
    state: str = Query(..., min_length=2, description="State name"),
    crops: str = Query(..., description="Comma-separated crop names e.g. 'Wheat,Mustard,Rice'")
):
    """Compares 2 to 5 crops side-by-side in the selected state."""
    crop_list = [c.strip() for c in crops.split(",") if c.strip()]
    if not crop_list:
        raise HTTPException(status_code=400, detail="Please provide at least one crop to compare.")
    results = compare_multiple_crops(state, crop_list)
    return {
        "state": state,
        "compared_crops": results,
        "count": len(results)
    }

@router.get("/state-comparison")
def state_comparison(
    crop: str = Query(..., min_length=2, description="Crop name e.g. Wheat")
):
    """Returns state-wise comparison for the selected crop across Indian states."""
    data = get_state_wise_crop_comparison(crop)
    return {
        "crop": crop,
        "states": data,
        "count": len(data),
        "advisory": "Prices vary by mandi, quality, grade, transportation, demand and date."
    }

@router.get("/profit-estimate")
def profit_estimate(
    crop: str = Query(..., min_length=2, description="Crop name"),
    state: str = Query(..., min_length=2, description="State name"),
    farm_area: float = Query(..., gt=0, description="Farm area"),
    area_unit: str = Query("acre", description="Area unit (acre, hectare, bigha)")
):
    """Calculates estimated gross revenue and profit based on farm area and indicative market price."""
    estimate = calculate_farm_profit_projection(farm_area, area_unit, crop, state)
    return estimate
