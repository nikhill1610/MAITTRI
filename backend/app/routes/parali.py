from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional, List
import json
import logging

from ..database import get_db
from ..models import Farm, ParaliAnalysisRecord
from ..schemas import ParaliAnalyzeRequest, ParaliActionPlanRequest
from ..deps import get_optional_current_user
from ..services.parali_management_service import (
    analyze_crop_residue,
    get_all_residue_methods,
    get_supported_parali_crops,
    RESIDUE_METHODS_CATALOG,
    CROP_RESIDUE_DATABASE,
)

logger = logging.getLogger("maitri.parali")
router = APIRouter()

@router.get("/crops")
def list_supported_crops():
    """
    Returns list of supported crops and their residue metadata.
    """
    return get_supported_parali_crops()

@router.get("/methods")
def list_management_methods():
    """
    Returns all scientific crop residue management methods catalog.
    """
    return get_all_residue_methods()

@router.post("/analyze")
def analyze_parali(
    payload: ParaliAnalyzeRequest,
    db: Session = Depends(get_db),
    user = Depends(get_optional_current_user)
):
    """
    Orchestrates full crop residue / parali analysis without open-field burning.
    Estimates residue quantity, evaluates nutrient & environmental destruction,
    ranks crop-compatible management methods, and generates dynamic action plans.
    """
    farm = None
    if payload.farm_id:
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required to analyze a specific farm."
            )
        farm_query = db.query(Farm).filter(Farm.id == payload.farm_id)
        user_role = (getattr(user, "role", "FARMER") or "FARMER").upper()
        if user_role not in ("AUTHORIZED_OPERATOR", "OPERATOR", "ADMIN"):
            farm_query = farm_query.filter(Farm.user_id == user.id)
        farm = farm_query.first()
        if not farm:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Farm not found or access denied")

    # Precedence: Explicit payload > Associated Farm Profile > Defaults
    crop = payload.crop or (farm.current_crop if farm and farm.current_crop else "rice")
    area = payload.area if payload.area and payload.area > 0 else (farm.area if farm and farm.area else 1.0)
    area_unit = payload.area_unit or (farm.area_unit if farm and farm.area_unit else "acre")
    lat = payload.latitude if payload.latitude is not None else (farm.latitude if farm else None)
    lon = payload.longitude if payload.longitude is not None else (farm.longitude if farm else None)
    soil_type = payload.soil_type or (farm.soil_type if farm else None)
    prev_crop = payload.previous_crop or (farm.previous_crop if farm else None)
    curr_crop = payload.current_crop or (farm.current_crop if farm else None)

    analysis_result = analyze_crop_residue(
        crop=crop,
        area=area,
        area_unit=area_unit,
        residue_quantity=payload.residue_quantity,
        residue_quantity_source=payload.residue_quantity_source,
        farmer_goal=payload.farmer_goal,
        machinery_available=payload.machinery_available,
        machinery=payload.machinery,
        latitude=lat,
        longitude=lon,
        soil_type=soil_type,
        previous_crop=prev_crop,
        current_crop=curr_crop,
        farm_id=farm.id if farm else None,
    )

    # Attach farm metadata if available
    if farm:
        analysis_result["farm"] = {
            "id": farm.id,
            "name": farm.name,
            "latitude": farm.latitude,
            "longitude": farm.longitude,
            "location_name": farm.location_name,
            "soil_type": farm.soil_type,
        }

    # Persist record if user is authenticated
    if user:
        try:
            record = ParaliAnalysisRecord(
                user_id=user.id,
                farm_id=farm.id if farm else None,
                crop=analysis_result.get("crop", crop),
                residue_type=analysis_result.get("residue_type", "Crop Residue"),
                area=area,
                area_unit=area_unit,
                analysis_json=json.dumps(analysis_result),
            )
            db.add(record)
            db.commit()
            analysis_result["analysis_id"] = record.id
        except Exception as e:
            logger.error(f"Error persisting parali record to database: {e}")
            db.rollback()

    return analysis_result

@router.post("/action-plan")
def get_custom_action_plan(payload: ParaliActionPlanRequest):
    """
    Returns step-by-step action plan for a specific chosen residue management method.
    """
    method = RESIDUE_METHODS_CATALOG.get(payload.method_id)
    if not method:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Method '{payload.method_id}' not found in scientific catalog."
        )

    return {
        "method_id": payload.method_id,
        "method_name": method["name"],
        "method_name_hi": method["name_hi"],
        "crop": payload.crop,
        "machinery_needed": method["machinery_needed"],
        "machinery_needed_hi": method["machinery_needed_hi"],
        "time_required": method["time_required"],
        "time_required_hi": method["time_required_hi"],
        "steps": method["steps"],
    }
