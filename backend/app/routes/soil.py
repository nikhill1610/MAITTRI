from fastapi import APIRouter, HTTPException, Query
from ..schemas import SoilEstimateRequest
from ..soil_estimation_service import estimate_soil_type, INDIAN_SOIL_TYPES

router = APIRouter()

@router.post("/estimate")
def estimate_soil_post(payload: SoilEstimateRequest):
    """Estimate probable soil type from coordinates."""
    try:
        return estimate_soil_type(payload.latitude, payload.longitude)
    except Exception as e:
        raise HTTPException(500, f"Error estimating soil type: {str(e)}")

@router.get("/estimate")
def estimate_soil_get(
    latitude: float = Query(..., ge=-90.0, le=90.0),
    longitude: float = Query(..., ge=-180.0, le=180.0)
):
    """Estimate probable soil type from coordinates."""
    try:
        return estimate_soil_type(latitude, longitude)
    except Exception as e:
        raise HTTPException(500, f"Error estimating soil type: {str(e)}")

@router.get("/types")
def get_soil_types():
    """Returns the comprehensive list of Indian agricultural soil types."""
    return {"soil_types": INDIAN_SOIL_TYPES}
