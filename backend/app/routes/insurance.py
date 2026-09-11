"""
Insurance Planning API Routes for MAITTRI Platform
Tagline: "किसान का साथी, समृद्धि की शुरुआत"
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from ..database import get_db
from ..schemas import InsuranceAnalyzeRequest, InsuranceEligibilityRequest
from ..services.insurance_service import (
    analyze_crop_insurance,
    NOTIFIED_CROPS_REGISTRY,
    SCHEME_COMPARISON_DATA,
    OFFICIAL_INSURANCE_DISCLAIMER
)
from ..services.government_scheme_service import get_supported_states

router = APIRouter()

@router.get("/states", response_model=List[str])
def list_insurance_states():
    """Retrieve all supported Indian states for crop insurance planning."""
    return get_supported_states()

@router.get("/crops")
def list_insurance_crops():
    """Retrieve all officially notified crops under PMFBY and state insurance programs."""
    crops = []
    for k, v in NOTIFIED_CROPS_REGISTRY.items():
        crops.append({
            "key": k,
            "crop_name": v["crop_name"],
            "hindi_name": v["hindi_name"],
            "seasons": v["seasons"],
            "category": v["category"],
            "statutory_farmer_premium_pct": v["farmer_premium_pct"]
        })
    return crops

@router.get("/upcoming")
def list_insurance_upcoming():
    """Retrieve upcoming insurance application windows and critical claim reporting deadlines."""
    return [
        {
            "event": "Rabi Crop Insurance Enrollment Deadline",
            "date": "December 31",
            "status": "Open",
            "scheme": "Pradhan Mantri Fasal Bima Yojana (PMFBY)",
            "action": "Ensure premium deduction before cut-off date through bank or CSC portal."
        },
        {
            "event": "Kharif Crop Insurance Enrollment Deadline",
            "date": "July 31",
            "status": "Annual Kharif Window",
            "scheme": "PMFBY / RWBCIS",
            "action": "Submit sowing certificate and land records before cut-off."
        },
        {
            "event": "Localized Calamity Mandatory Intimation Window",
            "date": "Within 72 Hours of Peril Occurrence",
            "status": "Strict Regulatory Rule",
            "scheme": "All Government Crop Insurance Schemes",
            "action": "Call National Toll-Free 14447 or inform bank/agriculture office with geo-tagged photos."
        }
    ]

@router.get("")
def list_insurance_plans(
    state: Optional[str] = Query(None),
    crop: Optional[str] = Query(None),
    season: Optional[str] = Query(None)
):
    """Retrieve available crop insurance schemes, comparison matrices, and policy frameworks."""
    return {
        "schemes": SCHEME_COMPARISON_DATA,
        "notified_crops_count": len(NOTIFIED_CROPS_REGISTRY),
        "official_portal": "https://pmfby.gov.in/",
        "national_helpline": "14447",
        "official_disclaimer": OFFICIAL_INSURANCE_DISCLAIMER
    }

@router.get("/{insurance_id}")
def get_insurance_plan(insurance_id: int):
    """Retrieve detailed scheme parameters by ID."""
    if insurance_id == 1:
        return {
            "id": 1,
            "scheme_name": "Pradhan Mantri Fasal Bima Yojana (PMFBY)",
            "details": SCHEME_COMPARISON_DATA[0],
            "official_portal": "https://pmfby.gov.in/"
        }
    elif insurance_id == 2:
        return {
            "id": 2,
            "scheme_name": "Restructured Weather Based Crop Insurance Scheme (RWBCIS)",
            "details": SCHEME_COMPARISON_DATA[1],
            "official_portal": "https://pmfby.gov.in/"
        }
    elif insurance_id == 3:
        return {
            "id": 3,
            "scheme_name": "Bihar Rajya Fasal Sahayata Yojana (BRFSY)",
            "details": SCHEME_COMPARISON_DATA[2],
            "official_portal": "https://state.bihar.gov.in/cooperative/"
        }
    raise HTTPException(status_code=404, detail="Insurance scheme not found.")

@router.post("/check-eligibility")
def check_insurance_eligibility(payload: InsuranceEligibilityRequest):
    """
    Check if a specific crop is notified in the selected state and season.
    """
    crop_key = payload.crop.strip().lower() if payload.crop else "wheat"
    crop_info = NOTIFIED_CROPS_REGISTRY.get(crop_key)
    state = payload.state.strip().title() if payload.state else "Uttar Pradesh"
    season = payload.season.strip().lower() if payload.season else "rabi"

    if not crop_info:
        return {
            "crop": payload.crop or "Unknown",
            "state": state,
            "season": season,
            "notified_status": "No verified applicable insurance information found for this crop in the selected location/season.",
            "eligible": False,
            "farmer_premium_pct": None,
            "guidance": "Consult the district agriculture office or pmfby.gov.in for localized notified crop lists."
        }

    is_notified_state = any(state.lower() in s.lower() for s in crop_info["notified_states"])
    is_notified_season = season in crop_info["seasons"] or "all" in crop_info["seasons"]
    eligible = is_notified_state and is_notified_season

    return {
        "crop": crop_info["crop_name"],
        "state": state,
        "season": season.capitalize(),
        "eligible": eligible,
        "notified_status": (
            f"Verified notified crop in {state} for {season.capitalize()} season."
            if eligible else
            f"Not standardly notified for {season.capitalize()} in {state}. Verify localized block-level notification."
        ),
        "statutory_farmer_premium_pct": crop_info["farmer_premium_pct"] if eligible else None,
        "category": crop_info["category"],
        "major_risks": crop_info["major_risks"],
        "official_disclaimer": OFFICIAL_INSURANCE_DISCLAIMER
    }

@router.post("/analyze")
def analyze_insurance(payload: InsuranceAnalyzeRequest):
    """
    Comprehensive Crop Insurance Planning analysis generating Sections A through M:
    - Farmer & Farm Profile (Auto-retrieved & Editable)
    - Current Crop & Season verification
    - Weather risk evaluation with agricultural risk alert
    - Statutory farmer premium cap (1.5% Rabi, 2% Kharif, 5% Commercial)
    - Coverage scope & 72-hour claim roadmap
    - Dynamic document checklist & comparison matrix
    - Official sources & helpline citations
    """
    # If weather check requested, we can supply simulated current conditions or pass through
    weather_context = None
    if payload.include_weather_risk:
        weather_context = {
            "current": {
                "temperature_2m": 28.5,
                "relative_humidity_2m": 65.0,
                "wind_speed_10m": 12.0,
                "precipitation": 0.0
            }
        }

    analysis = analyze_crop_insurance(
        state=payload.state,
        district=payload.district,
        crop=payload.crop,
        season=payload.season,
        farm_area=payload.farm_area,
        sowing_date=payload.sowing_date,
        expected_harvest=payload.expected_harvest,
        irrigation=payload.irrigation,
        farm_type=payload.farm_type,
        farmer_category=payload.farmer_category,
        weather_data=weather_context
    )
    return analysis
