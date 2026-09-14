from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
import json
from ..database import get_db
from ..models import Farm, NutrientAnalysisRecord
from ..schemas import NutrientAnalysisRequest
from ..deps import get_current_user
from ..services.nutrient_analysis_service import analyze_nutrient_depletion

router = APIRouter()

@router.post("/analyze")
def analyze_nutrients_endpoint(
    payload: NutrientAnalysisRequest,
    db: Session = Depends(get_db),
    user = Depends(get_current_user)
):
    """
    Analyzes nutrient depletion across 11 macro, secondary, and micro nutrients.
    Can be run for an existing farm or for in-memory farm parameters.
    """
    farm = None
    if payload.farm_id:
        user_role = (getattr(user, "role", "FARMER") or "FARMER").upper()
        farm_query = db.query(Farm).filter(Farm.id == payload.farm_id)
        if user_role not in ("AUTHORIZED_OPERATOR", "OPERATOR", "ADMIN"):
            farm_query = farm_query.filter(Farm.user_id == user.id)
        farm = farm_query.first()
        if not farm:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Farm not found or access denied")

    soil_type = payload.soil_type or (farm.soil_type if farm else "Loamy soil")
    soil_type_source = payload.soil_type_source or (farm.soil_type_source if farm else "farmer_selected")
    prev_crop = payload.previous_crop if payload.previous_crop is not None else (farm.previous_crop if farm else None)
    prev_period = payload.previous_crop_period if payload.previous_crop_period is not None else (farm.previous_crop_period if farm else None)
    curr_crop = payload.current_crop if payload.current_crop is not None else (farm.current_crop if farm else None)
    cultivation_count = payload.cultivation_count if payload.cultivation_count is not None else (farm.cultivation_count if farm else 1)
    soil_ph = payload.soil_ph if payload.soil_ph is not None else (farm.soil_ph if farm else None)
    soil_n = payload.soil_n if payload.soil_n is not None else (farm.soil_n if farm else None)
    soil_p = payload.soil_p if payload.soil_p is not None else (farm.soil_p if farm else None)
    soil_k = payload.soil_k if payload.soil_k is not None else (farm.soil_k if farm else None)
    org_c = payload.organic_carbon if payload.organic_carbon is not None else (farm.organic_carbon if farm else None)

    analysis_result = analyze_nutrient_depletion(
        soil_type=soil_type,
        previous_crop=prev_crop,
        previous_crop_period=prev_period,
        current_crop=curr_crop,
        cultivation_count=cultivation_count or 1,
        soil_ph=soil_ph,
        soil_n=soil_n,
        soil_p=soil_p,
        soil_k=soil_k,
        organic_carbon=org_c,
        soil_type_source=soil_type_source or "auto_detected"
    )

    # If associated with an existing farm, persist analysis record
    if farm:
        analysis_result["farm_id"] = farm.id
        analysis_result["farm_name"] = farm.name
        analysis_result["latitude"] = farm.latitude
        analysis_result["longitude"] = farm.longitude
        analysis_result["location_name"] = farm.location_name
        analysis_result["location_source"] = farm.location_source
        analysis_result["farm"] = {
            "id": farm.id,
            "name": farm.name,
            "latitude": farm.latitude,
            "longitude": farm.longitude,
            "location_name": farm.location_name,
            "location_source": farm.location_source,
            "soil_type": farm.soil_type,
            "soil_type_source": farm.soil_type_source,
            "soil_confidence": farm.soil_confidence,
            "soil_ph": farm.soil_ph,
            "previous_crop": farm.previous_crop,
            "previous_crop_period": farm.previous_crop_period,
            "current_crop": farm.current_crop,
            "cultivation_count": farm.cultivation_count
        }

        # Store or update latest analysis record
        existing_rec = db.query(NutrientAnalysisRecord).filter(NutrientAnalysisRecord.farm_id == farm.id).order_by(NutrientAnalysisRecord.id.desc()).first()
        if existing_rec:
            existing_rec.analysis_json = json.dumps(analysis_result)
            if not existing_rec.user_id:
                existing_rec.user_id = user.id
        else:
            new_rec = NutrientAnalysisRecord(farm_id=farm.id, user_id=user.id, analysis_json=json.dumps(analysis_result))
            db.add(new_rec)
        db.commit()

    return analysis_result


@router.get("/{farm_id}")
def get_farm_nutrient_analysis(
    farm_id: int,
    db: Session = Depends(get_db),
    user = Depends(get_current_user)
):
    """
    Retrieves or calculates the latest nutrient analysis for a farm.
    """
    user_role = (getattr(user, "role", "FARMER") or "FARMER").upper()
    farm_query = db.query(Farm).filter(Farm.id == farm_id)
    if user_role not in ("AUTHORIZED_OPERATOR", "OPERATOR", "ADMIN"):
        farm_query = farm_query.filter(Farm.user_id == user.id)
    farm = farm_query.first()
    if not farm:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Farm not found or access denied")

    # Check for stored record
    rec = db.query(NutrientAnalysisRecord).filter(NutrientAnalysisRecord.farm_id == farm.id).order_by(NutrientAnalysisRecord.id.desc()).first()
    if rec:
        try:
            return json.loads(rec.analysis_json)
        except Exception:
            pass

    # Compute freshly
    analysis_result = analyze_nutrient_depletion(
        soil_type=farm.soil_type,
        previous_crop=farm.previous_crop,
        previous_crop_period=farm.previous_crop_period,
        current_crop=farm.current_crop,
        cultivation_count=farm.cultivation_count or 1,
        soil_ph=farm.soil_ph,
        soil_n=farm.soil_n,
        soil_p=farm.soil_p,
        soil_k=farm.soil_k,
        organic_carbon=farm.organic_carbon,
        soil_type_source=farm.soil_type_source or "auto_detected"
    )
    analysis_result["farm_id"] = farm.id
    analysis_result["farm_name"] = farm.name
    analysis_result["latitude"] = farm.latitude
    analysis_result["longitude"] = farm.longitude
    analysis_result["location_name"] = farm.location_name
    analysis_result["location_source"] = farm.location_source
    analysis_result["farm"] = {
        "id": farm.id,
        "name": farm.name,
        "latitude": farm.latitude,
        "longitude": farm.longitude,
        "location_name": farm.location_name,
        "location_source": farm.location_source,
        "soil_type": farm.soil_type,
        "soil_type_source": farm.soil_type_source,
        "soil_confidence": farm.soil_confidence,
        "soil_ph": farm.soil_ph,
        "previous_crop": farm.previous_crop,
        "previous_crop_period": farm.previous_crop_period,
        "current_crop": farm.current_crop,
        "cultivation_count": farm.cultivation_count
    }

    new_rec = NutrientAnalysisRecord(farm_id=farm.id, user_id=user.id, analysis_json=json.dumps(analysis_result))
    db.add(new_rec)
    db.commit()

    return analysis_result
