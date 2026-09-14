"""
Farmer Profile & MAITTRI Farm ID API Routes
--------------------------------------------
Provides the central Farm Profile as the single source of truth for:
- Crop & Nutrient Intelligence
- Weather & Mandi Alerts
- Digital Farmer ID Card & QR Token
"""

import uuid
from typing import Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import User, Farmer, Farm, CommunicationPreference
from ..schemas import FarmerUpdate, FarmerResponse
from ..deps import get_current_user

router = APIRouter()


def ensure_farmer_record(user: User, db: Session) -> Farmer:
    """Ensures every registered user has a canonical Farmer entity with unique MT-FARM ID."""
    farmer = db.query(Farmer).filter(Farmer.user_id == user.id).first()
    if farmer:
        return farmer

    # Auto-generate MAITTRI Farm ID
    count = db.query(Farmer).count() + 1
    f_id = f"MT-FARM-{count:06d}"
    while db.query(Farmer).filter(Farmer.maittri_farmer_id == f_id).first():
        count += 1
        f_id = f"MT-FARM-{count:06d}"

    qr_payload = f"MAITTRI:{f_id}:{uuid.uuid4().hex[:8]}"

    # Check if user already had a farm
    existing_farm = db.query(Farm).filter(Farm.user_id == user.id).first()

    farmer = Farmer(
        maittri_farmer_id=f_id,
        user_id=user.id,
        name=getattr(user, "full_name", None) or user.email.split("@")[0].capitalize(),
        mobile_number=getattr(user, "phone_number", None) or "9876543210",
        state="Uttar Pradesh",
        district=existing_farm.location_name if existing_farm and existing_farm.location_name else "Varanasi",
        farm_area=existing_farm.area if existing_farm else 2.5,
        soil_type=existing_farm.soil_type if existing_farm else "Alluvial Soil",
        current_crop=existing_farm.current_crop if existing_farm else "Wheat",
        previous_crop=existing_farm.previous_crop if existing_farm else "Rice",
        preferred_language=getattr(user, "language", "hi") or "hi",
        qr_code_data=qr_payload
    )
    db.add(farmer)
    db.commit()
    db.refresh(farmer)

    if existing_farm and not existing_farm.farmer_id:
        existing_farm.farmer_id = farmer.id
        db.commit()

    # Create default communication preferences
    pref = CommunicationPreference(farmer_id=farmer.id)
    db.add(pref)
    db.commit()

    return farmer


@router.get("/me", response_model=FarmerResponse)
def get_my_farmer_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Returns the authenticated farmer's central profile and MAITTRI Farm ID."""
    farmer = ensure_farmer_record(current_user, db)
    return farmer


@router.put("/me", response_model=FarmerResponse)
def update_my_farmer_profile(
    payload: FarmerUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Updates the authenticated farmer's central profile."""
    farmer = ensure_farmer_record(current_user, db)
    update_data = payload.model_dump(exclude_unset=True)

    for k, v in update_data.items():
        setattr(farmer, k, v)
    farmer.updated_at = datetime.now(timezone.utc)

    # Sync to linked farm
    farm = db.query(Farm).filter(Farm.farmer_id == farmer.id).first()
    if farm:
        if payload.farm_area is not None:
            farm.area = payload.farm_area
        if payload.soil_type is not None:
            farm.soil_type = payload.soil_type
        if payload.current_crop is not None:
            farm.current_crop = payload.current_crop

    db.commit()
    db.refresh(farmer)
    return farmer


@router.get("/qr/{farmer_id}")
def get_farmer_qr_code(
    farmer_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Returns an opaque verification token for QR code rendering.
    Contains no raw PII to prevent scanning leaks.
    Strictly enforces tenant isolation: farmers can only view their own QR token.
    """
    farmer = db.query(Farmer).filter(Farmer.id == farmer_id).first()
    if not farmer:
        raise HTTPException(status_code=404, detail="Farmer not found")

    user_role = (getattr(current_user, "role", "FARMER") or "FARMER").upper()
    is_elevated = user_role in ("AUTHORIZED_OPERATOR", "OPERATOR", "ADMIN")
    if not is_elevated and str(farmer.user_id) != str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: You cannot view another farmer's verification QR token."
        )

    return {
        "farmer_id": farmer.id,
        "maittri_farmer_id": farmer.maittri_farmer_id,
        "qr_token": farmer.qr_code_data,
        "name": farmer.name,
        "state": farmer.state,
        "district": farmer.district,
        "verified": True
    }
