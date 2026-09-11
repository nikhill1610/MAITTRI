"""
Government Schemes API Routes for MAITTRI Platform
Tagline: "किसान का साथी, समृद्धि की शुरुआत"
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from ..database import get_db
from ..schemas import SchemeEligibilityRequest, SchemeEligibilityResponse
from ..services.government_scheme_service import (
    get_government_schemes,
    get_supported_states,
    get_scheme_categories,
    get_upcoming_schemes,
    get_scheme_by_id
)
from ..services.scheme_eligibility_service import (
    evaluate_scheme_eligibility,
    check_bulk_eligibility,
    OFFICIAL_DISCLAIMER
)

router = APIRouter()

@router.get("/states", response_model=List[str])
def list_states():
    """Retrieve all supported Indian states for government scheme filtering."""
    return get_supported_states()

@router.get("/categories")
def list_categories():
    """Retrieve 14 standard agricultural scheme categories."""
    return get_scheme_categories()

@router.get("/upcoming")
def list_upcoming(state: Optional[str] = Query(None)):
    """Retrieve schemes with upcoming application windows or closing soon deadlines."""
    return get_upcoming_schemes(state=state)

@router.get("")
def list_schemes(
    state: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    crop: Optional[str] = Query(None),
    level: Optional[str] = Query(None)
):
    """
    Retrieve government schemes with state-wise isolation and multi-faceted filters.
    Strict rule: Selecting Uttar Pradesh will never return Punjab or Maharashtra state schemes.
    """
    return get_government_schemes(
        state=state,
        category=category,
        status=status,
        search=search,
        crop=crop,
        level=level
    )

@router.get("/{scheme_id}")
def get_scheme(scheme_id: int):
    """Retrieve full details for a single verified government scheme."""
    scheme = get_scheme_by_id(scheme_id)
    if not scheme:
        raise HTTPException(status_code=404, detail="Government scheme not found.")
    return scheme

@router.post("/check-eligibility")
def check_eligibility(payload: SchemeEligibilityRequest):
    """
    Evaluate personalized scheme eligibility based on farmer profile, state, crop, and farm size.
    Outputs: Eligible, Potentially Eligible, Not Eligible, Insufficient Information, Unknown.
    """
    if payload.scheme_id:
        scheme = get_scheme_by_id(payload.scheme_id)
        if not scheme:
            raise HTTPException(status_code=404, detail="Requested scheme not found.")
        eval_res = evaluate_scheme_eligibility(
            scheme=scheme,
            state=payload.state,
            district=payload.district,
            crop=payload.crop,
            season=payload.season,
            farm_size_acres=payload.farm_size_acres,
            farmer_category=payload.farmer_category,
            land_ownership=payload.land_ownership,
            irrigation_type=payload.irrigation_type,
            solar_pump_needed=payload.solar_pump_needed,
            equipment_needed=payload.equipment_needed
        )
        return eval_res

    # Bulk evaluation across all applicable schemes for state
    bulk_results = check_bulk_eligibility(
        state=payload.state,
        district=payload.district,
        crop=payload.crop,
        season=payload.season,
        farm_size_acres=payload.farm_size_acres,
        farmer_category=payload.farmer_category,
        land_ownership=payload.land_ownership,
        irrigation_type=payload.irrigation_type,
        solar_pump_needed=payload.solar_pump_needed,
        equipment_needed=payload.equipment_needed
    )
    return {
        "total_schemes_evaluated": len(bulk_results),
        "state_applied": payload.state or "All (Pan-India Central)",
        "results": bulk_results,
        "official_disclaimer": OFFICIAL_DISCLAIMER
    }
