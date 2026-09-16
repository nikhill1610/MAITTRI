"""
MAITTRI Farm Brain API Endpoints
---------------------------------
Delivers central decision intelligence across Web Dashboard, SMS, and IVR.
Grounded in real farm coordinates, meteorological forecasts, and certified soil data.
Strictly isolated per-tenant.
"""

import logging
from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import (
    User, Farm, Farmer, SoilTestReport, IoTSensorReading, FarmPlan, FarmPlanTask
)
from ..deps import get_current_user, is_same_user
from ..services.farm_brain_service import (
    generate_today_decisions, generate_weekly_outlook
)

logger = logging.getLogger("maitri.farm_brain")
router = APIRouter()


def _fetch_farm_weather(farm: Farm) -> Optional[Dict[str, Any]]:
    """Fetches real weather for farm coordinates; returns None on failure without fabricating mock data."""
    if not farm.latitude or not farm.longitude:
        return None
    try:
        from .weather import fetch_weather_data
        w = fetch_weather_data(farm.latitude, farm.longitude, forecast_days=7)
        if w and "daily" in w:
            return {"daily": w["daily"]}
    except Exception as e:
        logger.warning(f"Live weather lookup failed for farm {farm.id}: {e}")
    return None


@router.get("/today/{farm_id}")
def get_farm_brain_today(
    farm_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Returns 'WHAT SHOULD I DO TODAY?' priority recommendations for the specified farm.
    Enforces multi-tenant ownership: only farm owners and authorized operators can access.
    """
    farm = db.query(Farm).filter(Farm.id == farm_id).first()
    if not farm:
        raise HTTPException(status_code=404, detail="Farm record not found")

    user_role = (getattr(current_user, "role", "FARMER") or "FARMER").upper()
    is_elevated = user_role in ("AUTHORIZED_OPERATOR", "OPERATOR", "ADMIN")
    if not is_elevated and not is_same_user(farm.user_id, current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: You cannot view Farm Brain intelligence for another user's farm."
        )

    farmer = None
    if farm.farmer_id:
        farmer = db.query(Farmer).filter(Farmer.id == farm.farmer_id).first()
    elif farm.user_id:
        farmer = db.query(Farmer).filter(Farmer.user_id == farm.user_id).first()

    # Retrieve latest certified soil report
    soil_report = None
    if farmer:
        soil_report = db.query(SoilTestReport).filter(
            SoilTestReport.farmer_id == farmer.id
        ).order_by(SoilTestReport.id.desc()).first()

    # Retrieve latest indicative IoT sensor telemetry for this farm
    from ..models import IoTDevice
    farm_devices = db.query(IoTDevice).filter(IoTDevice.farm_id == farm.id).all()
    device_table_ids = [d.id for d in farm_devices]
    device_ids = [d.device_id for d in farm_devices]

    latest_iot = None
    if device_table_ids or device_ids:
        latest_iot = db.query(IoTSensorReading).filter(
            (IoTSensorReading.device_table_id.in_(device_table_ids)) |
            (IoTSensorReading.device_id.in_(device_ids))
        ).order_by(IoTSensorReading.id.desc()).first()

    # Retrieve scheduled plan tasks
    plan_tasks = []
    plan = db.query(FarmPlan).filter(FarmPlan.farm_id == farm_id).first()
    if plan:
        plan_tasks = db.query(FarmPlanTask).filter(
            FarmPlanTask.farm_plan_id == plan.id,
            FarmPlanTask.status == "pending"
        ).limit(3).all()

    # Fetch real weather context from farm coordinates (no fake hardcoded weather)
    weather_ctx = _fetch_farm_weather(farm)

    decisions = generate_today_decisions(
        farm=farm,
        farmer=farmer,
        soil_report=soil_report,
        latest_iot=latest_iot,
        weather_data=weather_ctx,
        plan_tasks=plan_tasks
    )
    return decisions


@router.get("/week/{farm_id}")
def get_farm_brain_week(
    farm_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Returns 7-day agronomic and operational outlook.
    Enforces multi-tenant ownership: only farm owners and authorized operators can access.
    """
    farm = db.query(Farm).filter(Farm.id == farm_id).first()
    if not farm:
        raise HTTPException(status_code=404, detail="Farm record not found")

    user_role = (getattr(current_user, "role", "FARMER") or "FARMER").upper()
    is_elevated = user_role in ("AUTHORIZED_OPERATOR", "OPERATOR", "ADMIN")
    if not is_elevated and not is_same_user(farm.user_id, current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: You cannot view Farm Brain intelligence for another user's farm."
        )

    farmer = None
    if farm.farmer_id:
        farmer = db.query(Farmer).filter(Farmer.id == farm.farmer_id).first()
    elif farm.user_id:
        farmer = db.query(Farmer).filter(Farmer.user_id == farm.user_id).first()

    # Fetch real weather context from farm coordinates (no fake hardcoded weather)
    weather_ctx = _fetch_farm_weather(farm)

    outlook = generate_weekly_outlook(farm, farmer, weather_ctx)
    return outlook
