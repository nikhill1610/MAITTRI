from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import Optional, List, Dict, Any
import json
import requests
from datetime import datetime, timezone

from ..database import get_db
from ..models import (
    Farm, User, FertilizerRecommendation, PesticideRecommendation,
    FertilizerApplication, PesticideApplication, NutrientObservation
)
from ..schemas import (
    FertilizerAnalyzeRequest, FertilizerRecommendRequest,
    PestAnalyzeRequest, PestRecommendRequest,
    FertilizerApplicationCreate, PesticideApplicationCreate
)
from ..deps import get_optional_current_user, get_current_user
from ..services.fertilizer_recommendation_service import (
    generate_comprehensive_recommendation,
    analyze_crop,
    analyze_previous_crop,
    analyze_soil,
    analyze_nutrients_status,
    analyze_pest_and_disease,
    evaluate_weather_risks,
    get_authoritative_sources,
)

fertilizer_router = APIRouter()
pest_router = APIRouter()

def _fetch_weather(lat: Optional[float], lon: Optional[float]) -> Optional[Dict[str, Any]]:
    """Helper to fetch weather forecast safely with a short timeout."""
    if lat is None or lon is None:
        return None
    try:
        url = (
            f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}"
            "&current=temperature_2m,relative_humidity_2m,wind_speed_10m,weather_code"
            "&hourly=precipitation_probability,wind_speed_10m,temperature_2m"
            "&daily=precipitation_sum,precipitation_probability_max,temperature_2m_max,temperature_2m_min"
            "&timezone=auto&forecast_days=3"
        )
        res = requests.get(url, timeout=3.5)
        if res.status_code == 200:
            return res.json()
    except Exception:
        pass
    return None


# =====================================================================
# FERTILIZER ENDPOINTS
# =====================================================================

@fertilizer_router.post("/analyze")
def analyze_fertilizer_endpoint(
    payload: FertilizerAnalyzeRequest,
    db: Session = Depends(get_db),
    user: Optional[User] = Depends(get_optional_current_user)
):
    """
    Detailed agronomic analysis of soil, nutrients, previous crop, and current crop.
    Does NOT prescribe rigid chemical fertilizers blindly.
    """
    farm = None
    if payload.farm_id:
        farm = db.query(Farm).filter(Farm.id == payload.farm_id).first()

    lat = payload.latitude or (farm.latitude if farm else None)
    lon = payload.longitude or (farm.longitude if farm else None)
    weather_data = _fetch_weather(lat, lon)

    # Use farm values if not explicitly provided
    soil_type = payload.soil_type or (farm.soil_type if farm else "Alluvial soil")
    prev_crop = payload.previous_crop or (farm.previous_crop if farm else None)
    soil_ph = payload.soil_ph if payload.soil_ph is not None else (farm.soil_ph if farm else None)
    soil_n = payload.soil_n if payload.soil_n is not None else (farm.soil_n if farm else None)
    soil_p = payload.soil_p if payload.soil_p is not None else (farm.soil_p if farm else None)
    soil_k = payload.soil_k if payload.soil_k is not None else (farm.soil_k if farm else None)

    try:
        res = generate_comprehensive_recommendation(
            current_crop=payload.current_crop,
            previous_crop=prev_crop,
            previous_crop_harvest_season=payload.previous_crop_harvest_season,
            crop_stage=payload.crop_stage,
            soil_type=soil_type,
            soil_ph=soil_ph,
            soil_moisture=payload.soil_moisture,
            soil_temperature=payload.soil_temperature,
            soil_n=soil_n,
            soil_p=soil_p,
            soil_k=soil_k,
            secondary_nutrients=payload.secondary_nutrients,
            micronutrients=payload.micronutrients,
            data_source=payload.data_source or "farmer_input",
            farm_location=payload.farm_location or (farm.location_name if farm else None),
            irrigation=payload.irrigation or (farm.irrigation if farm else "available"),
            pest_observed=payload.pest_observed,
            disease_observed=payload.disease_observed,
            pest_symptoms=payload.pest_symptoms,
            affected_area_pct=payload.affected_area_pct,
            weather_data=weather_data,
            residue_handling=payload.residue_handling or "removed"
        )
        return res
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@fertilizer_router.post("/recommend")
def recommend_fertilizer_endpoint(
    payload: FertilizerRecommendRequest,
    db: Session = Depends(get_db),
    user: Optional[User] = Depends(get_optional_current_user)
):
    """
    Generates a full evidence-based fertilizer recommendation across all 12 sections.
    Persists recommendation in database if farm or user is present.
    """
    farm = None
    if payload.farm_id:
        farm = db.query(Farm).filter(Farm.id == payload.farm_id).first()

    lat = payload.latitude or (farm.latitude if farm else None)
    lon = payload.longitude or (farm.longitude if farm else None)
    weather_data = _fetch_weather(lat, lon) if payload.include_weather else None

    soil_type = payload.soil_type or (farm.soil_type if farm else "Alluvial soil")
    prev_crop = payload.previous_crop or (farm.previous_crop if farm else None)
    soil_ph = payload.soil_ph if payload.soil_ph is not None else (farm.soil_ph if farm else None)
    soil_n = payload.soil_n if payload.soil_n is not None else (farm.soil_n if farm else None)
    soil_p = payload.soil_p if payload.soil_p is not None else (farm.soil_p if farm else None)
    soil_k = payload.soil_k if payload.soil_k is not None else (farm.soil_k if farm else None)

    try:
        recommendation = generate_comprehensive_recommendation(
            current_crop=payload.current_crop,
            previous_crop=prev_crop,
            previous_crop_harvest_season=payload.previous_crop_harvest_season,
            crop_stage=payload.crop_stage,
            soil_type=soil_type,
            soil_ph=soil_ph,
            soil_moisture=payload.soil_moisture,
            soil_temperature=payload.soil_temperature,
            soil_n=soil_n,
            soil_p=soil_p,
            soil_k=soil_k,
            secondary_nutrients=payload.secondary_nutrients,
            micronutrients=payload.micronutrients,
            data_source=payload.data_source or "farmer_input",
            farm_location=payload.farm_location or (farm.location_name if farm else None),
            irrigation=payload.irrigation or (farm.irrigation if farm else "available"),
            pest_observed=payload.pest_observed,
            disease_observed=payload.disease_observed,
            pest_symptoms=payload.pest_symptoms,
            affected_area_pct=payload.affected_area_pct,
            weather_data=weather_data,
            residue_handling=payload.residue_handling or "removed"
        )

        # Persist recommendation if farm is specified
        if farm:
            rec_row = FertilizerRecommendation(
                farm_id=farm.id,
                user_id=user.id if user else farm.user_id,
                crop=payload.current_crop,
                previous_crop=prev_crop,
                stage=payload.crop_stage or "Unspecified",
                soil_type=soil_type,
                recommendation_json=json.dumps(recommendation),
                confidence=recommendation["section_K_confidence_and_explanation"]["confidence_level"],
                explanation_summary=recommendation["section_C_fertilizer_recommendation"]["summary"]
            )
            db.add(rec_row)
            db.commit()

        return recommendation
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@fertilizer_router.get("/history")
def get_fertilizer_history(
    farm_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    user: Optional[User] = Depends(get_optional_current_user)
):
    """
    Retrieves stored fertilizer recommendations and farmer application records.
    """
    query_recs = db.query(FertilizerRecommendation)
    query_apps = db.query(FertilizerApplication)

    if farm_id:
        query_recs = query_recs.filter(FertilizerRecommendation.farm_id == farm_id)
        query_apps = query_apps.filter(FertilizerApplication.farm_id == farm_id)
    elif user:
        # Get all farms of current user
        user_farm_ids = [f.id for f in db.query(Farm).filter(Farm.user_id == user.id).all()]
        query_recs = query_recs.filter(FertilizerRecommendation.farm_id.in_(user_farm_ids))
        query_apps = query_apps.filter(FertilizerApplication.farm_id.in_(user_farm_ids))

    recs = query_recs.order_by(FertilizerRecommendation.created_at.desc()).limit(15).all()
    apps = query_apps.order_by(FertilizerApplication.applied_at.desc()).limit(20).all()

    history_records = []
    for r in recs:
        try:
            parsed = json.loads(r.recommendation_json)
        except Exception:
            parsed = {}
        history_records.append({
            "id": r.id,
            "farm_id": r.farm_id,
            "crop": r.crop,
            "previous_crop": r.previous_crop,
            "stage": r.stage,
            "confidence": r.confidence,
            "summary": r.explanation_summary,
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "details": parsed
        })

    applications = [{
        "id": a.id,
        "farm_id": a.farm_id,
        "crop": a.crop,
        "fertilizer_type": a.fertilizer_type,
        "fertilizer_name": a.fertilizer_name,
        "application_stage": a.application_stage,
        "rate_per_acre": a.rate_per_acre,
        "application_method": a.application_method,
        "applied_at": a.applied_at.isoformat() if a.applied_at else None,
        "notes": a.notes
    } for a in apps]

    return {
        "recommendations": history_records,
        "logged_applications": applications
    }


@fertilizer_router.post("/history")
def log_fertilizer_application(
    payload: FertilizerApplicationCreate,
    db: Session = Depends(get_db),
    user: Optional[User] = Depends(get_optional_current_user)
):
    """
    Logs a farmer's actual fertilizer application for historical tracking.
    """
    farm = db.query(Farm).filter(Farm.id == payload.farm_id).first()
    if not farm:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Farm not found")

    entry = FertilizerApplication(
        farm_id=farm.id,
        crop=payload.crop,
        fertilizer_type=payload.fertilizer_type,
        fertilizer_name=payload.fertilizer_name,
        application_stage=payload.application_stage,
        rate_per_acre=payload.rate_per_acre,
        application_method=payload.application_method,
        notes=payload.notes,
        applied_at=datetime.now(timezone.utc)
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)

    return {"status": "success", "message": "Fertilizer application logged successfully", "id": entry.id}


@fertilizer_router.get("/sources")
def get_fertilizer_sources():
    """Returns authoritative sources for soil, crop, and fertilizer recommendations."""
    return {"sources": get_authoritative_sources()}


@fertilizer_router.get("/sensor-latest")
def get_sensor_latest(
    farm_id: Optional[int] = Query(None),
    db: Session = Depends(get_db)
):
    """
    Retrieves the latest IoT sensor reading for a farm.
    If no physical device is linked, returns an indicative calibrated profile.
    """
    if farm_id:
        obs = db.query(NutrientObservation).filter(
            NutrientObservation.farm_id == farm_id,
            NutrientObservation.source == "sensor"
        ).order_by(NutrientObservation.observed_at.desc()).first()

        if obs:
            return {
                "source": "MAITTRI IoT Soil Sensor",
                "type": "Sensor-based indicative reading",
                "timestamp": obs.observed_at.isoformat(),
                "values": {
                    "nitrogen": obs.nitrogen,
                    "phosphorus": obs.phosphorus,
                    "potassium": obs.potassium,
                    "ph": obs.ph,
                    "moisture": obs.moisture,
                    "temperature": obs.temperature,
                    "ec": obs.ec
                },
                "caveat": "Sensor reading reflects real-time in-situ electrical conductivity and optical responses. It does not replace a chemical laboratory extraction."
            }

    # Default calibrated indicative reading for demonstration
    return {
        "source": "MAITTRI Smart Sensor Module (Demo Calibration)",
        "type": "Sensor-based indicative reading",
        "timestamp": datetime.now(timezone.utc).strftime("%H:%M UTC"),
        "values": {
            "nitrogen": 195.0,
            "phosphorus": 18.5,
            "potassium": 160.0,
            "ph": 7.4,
            "moisture": 42.0,
            "temperature": 26.5,
            "ec": 0.85
        },
        "caveat": "Sensor reading reflects real-time in-situ measurements. It does not replace a certified laboratory soil test."
    }


# =====================================================================
# PEST & DISEASE ENDPOINTS
# =====================================================================

@pest_router.post("/analyze")
def analyze_pest_endpoint(payload: PestAnalyzeRequest):
    """
    Analyzes pest/disease symptoms according to IPM hierarchy.
    """
    try:
        res = analyze_pest_and_disease(
            crop=payload.crop,
            pest_observed=payload.pest_observed,
            disease_observed=payload.disease_observed,
            symptoms=payload.symptoms,
            affected_area_pct=payload.affected_area_pct,
            crop_stage=payload.crop_stage
        )
        return res
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@pest_router.post("/recommend")
def recommend_pest_endpoint(
    payload: PestRecommendRequest,
    db: Session = Depends(get_db),
    user: Optional[User] = Depends(get_optional_current_user)
):
    """
    Generates IPM-compliant pest/disease management recommendation.
    Recommends chemical pesticides ONLY if confirmed evidence and registered chemistry exists.
    """
    try:
        res = analyze_pest_and_disease(
            crop=payload.crop,
            pest_observed=payload.pest_observed,
            disease_observed=payload.disease_observed,
            symptoms=payload.symptoms,
            affected_area_pct=payload.affected_area_pct,
            crop_stage=payload.crop_stage
        )

        if payload.farm_id:
            farm = db.query(Farm).filter(Farm.id == payload.farm_id).first()
            if farm:
                rec_row = PesticideRecommendation(
                    farm_id=farm.id,
                    user_id=user.id if user else farm.user_id,
                    crop=payload.crop,
                    pest_or_disease=res.get("pest_name") or payload.pest_observed or "General",
                    recommendation_json=json.dumps(res),
                    confidence="High" if res.get("target_identified") else "Medium",
                    explanation_summary=res.get("verdict") or "IPM Evaluation"
                )
                db.add(rec_row)
                db.commit()

        return res
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@pest_router.post("/history")
def log_pesticide_application(
    payload: PesticideApplicationCreate,
    db: Session = Depends(get_db)
):
    """
    Logs farmer pesticide spray for record-keeping and PHI compliance.
    """
    farm = db.query(Farm).filter(Farm.id == payload.farm_id).first()
    if not farm:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Farm not found")

    entry = PesticideApplication(
        farm_id=farm.id,
        crop=payload.crop,
        target_pest_or_disease=payload.target_pest_or_disease,
        pesticide_name=payload.pesticide_name,
        active_ingredient=payload.active_ingredient,
        dosage=payload.dosage,
        application_method=payload.application_method,
        notes=payload.notes,
        applied_at=datetime.now(timezone.utc)
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)

    return {"status": "success", "message": "Pesticide application logged successfully", "id": entry.id}


@pest_router.get("/sources")
def get_pest_sources():
    """Returns authoritative plant protection and CIBRC sources."""
    return {
        "sources": [
            {
                "name": "Central Insecticides Board & Registration Committee (CIBRC)",
                "role": "Approves all legal agricultural insecticides, fungicides, and herbicides in India, including approved crop labels, dosage caps, and pre-harvest intervals (PHI).",
                "url": "http://cibrc.nic.in"
            },
            {
                "name": "National Centre for Integrated Pest Management (ICAR-NCIPM)",
                "role": "Formulates national IPM packages emphasizing economic threshold levels (ETL), bio-control agents, and resistance prevention.",
                "url": "https://ncipm.icar.gov.in"
            },
            {
                "name": "Directorate of Plant Protection, Quarantine & Storage (DPPQ&S)",
                "role": "Regulates plant quarantine, pest surveillance, and locust control operations across India.",
                "url": "https://ppqs.gov.in"
            }
        ]
    }
