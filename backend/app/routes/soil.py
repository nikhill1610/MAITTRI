from fastapi import APIRouter, HTTPException, Query
from ..schemas import SoilEstimateRequest
from ..services.soil_estimation_service import estimate_soil_type, INDIAN_SOIL_TYPES

router = APIRouter()

@router.post("/estimate", deprecated=True, summary="[DEPRECATED] Estimate soil type - Use /api/location/soil-estimate")
def estimate_soil_post(payload: SoilEstimateRequest):
    """[DEPRECATED] Estimate probable soil type from coordinates. Prefer /api/location/soil-estimate."""
    try:
        return estimate_soil_type(payload.latitude, payload.longitude)
    except Exception as e:
        raise HTTPException(500, f"Error estimating soil type: {str(e)}")

@router.get("/estimate", deprecated=True, summary="[DEPRECATED] Estimate soil type - Use /api/location/soil-estimate")
def estimate_soil_get(
    latitude: float = Query(..., ge=-90.0, le=90.0),
    longitude: float = Query(..., ge=-180.0, le=180.0)
):
    """[DEPRECATED] Estimate probable soil type from coordinates. Prefer /api/location/soil-estimate."""
    try:
        return estimate_soil_type(latitude, longitude)
    except Exception as e:
        raise HTTPException(500, f"Error estimating soil type: {str(e)}")

@router.get("/types")
def get_soil_types():
    """Returns the comprehensive list of Indian agricultural soil types."""
    return {"soil_types": INDIAN_SOIL_TYPES}
