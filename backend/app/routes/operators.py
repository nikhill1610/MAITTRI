"""
Authorized Agriculture / Seva Operator API Routes
--------------------------------------------------
Role-based endpoints allowing certified Seva operators to assist farmers who:
- Do not have smartphones or mobile data
- Are uncomfortable with digital forms
- Need assisted farm registration, soil test booking, and document uploads
"""

import uuid
import json
from typing import List, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_

from ..database import get_db
from ..models import (
    User, Farmer, Farm, SoilTestRequest, ServiceRequest,
    OperatorActivityLog, FarmerDocument, SoilTestReport
)
from ..schemas import FarmerCreate, FarmerUpdate, FarmerResponse
from ..deps import require_operator, get_current_user

router = APIRouter()


def generate_maittri_farmer_id(db: Session) -> str:
    """Generates next canonical MAITTRI Farm ID like MT-FARM-000001."""
    count = db.query(Farmer).count() + 1
    candidate = f"MT-FARM-{count:06d}"
    while db.query(Farmer).filter(Farmer.maittri_farmer_id == candidate).first():
        count += 1
        candidate = f"MT-FARM-{count:06d}"
    return candidate


@router.get("/stats")
@router.get("/dashboard")
def get_operator_stats(
    operator: User = Depends(require_operator),
    db: Session = Depends(get_db)
):
    """Returns overview metrics for the Seva Operator dashboard."""
    total_farmers = db.query(Farmer).count()
    pending_soil_tests = db.query(SoilTestRequest).filter(
        SoilTestRequest.status.in_(["REQUESTED", "SCHEDULED", "SAMPLE_COLLECTED", "LAB_PROCESSING"])
    ).count()
    open_service_requests = db.query(ServiceRequest).filter(
        ServiceRequest.status.in_(["REQUESTED", "IN_PROGRESS", "SCHEDULED"])
    ).count()
    total_documents = db.query(FarmerDocument).count()

    recent_activities = db.query(OperatorActivityLog).order_by(
        OperatorActivityLog.id.desc()
    ).limit(8).all()

    return {
        "total_registered_farmers": total_farmers,
        "pending_soil_tests": pending_soil_tests,
        "open_service_requests": open_service_requests,
        "total_documents_archived": total_documents,
        "recent_activities": [
            {
                "id": a.id,
                "action_type": a.action_type,
                "farmer_id": a.farmer_id,
                "details": a.details_json,
                "created_at": a.created_at.strftime("%Y-%m-%d %H:%M") if a.created_at else ""
            }
            for a in recent_activities
        ]
    }


@router.post("/farmers", response_model=FarmerResponse)
def register_assisted_farmer(
    payload: FarmerCreate,
    operator: User = Depends(require_operator),
    db: Session = Depends(get_db)
):
    """
    Assisted registration of a farmer conducted by an Authorized Seva Operator.
    Assigns unique MT-FARM-XXXXXX and creates initial Farm record.
    """
    farmer_id_str = generate_maittri_farmer_id(db)
    qr_payload = f"MAITTRI:{farmer_id_str}:{uuid.uuid4().hex[:8]}"

    farmer = Farmer(
        maittri_farmer_id=farmer_id_str,
        operator_id=operator.id,
        name=payload.name.strip(),
        mobile_number=payload.mobile_number.strip(),
        alternate_mobile=payload.alternate_mobile,
        state=payload.state,
        district=payload.district,
        block=payload.block,
        village=payload.village,
        farm_area=payload.farm_area,
        area_unit=payload.area_unit,
        land_ownership=payload.land_ownership,
        irrigation=payload.irrigation,
        soil_type=payload.soil_type,
        soil_test_available=payload.soil_test_available,
        current_crop=payload.current_crop,
        previous_crop=payload.previous_crop,
        planned_crop=payload.planned_crop,
        sowing_date=payload.sowing_date,
        crop_variety=payload.crop_variety,
        preferred_language=payload.preferred_language,
        sms_consent=payload.sms_consent,
        ivr_consent=payload.ivr_consent,
        qr_code_data=qr_payload
    )
    db.add(farmer)
    db.commit()
    db.refresh(farmer)

    # Automatically create linked Farm record for backward compatibility
    farm = Farm(
        user_id=operator.id,  # Owned/managed under operator account
        farmer_id=farmer.id,
        name=f"{farmer.name}'s Field ({farmer.village or farmer.district})",
        area=farmer.farm_area,
        area_unit=farmer.area_unit,
        soil_type=farmer.soil_type,
        irrigation=farmer.irrigation or "available",
        current_crop=farmer.current_crop or "Wheat",
        previous_crop=farmer.previous_crop,
        location_name=f"{farmer.village or ''}, {farmer.district or ''}, {farmer.state or ''}".strip(", "),
        sowing_date=farmer.sowing_date
    )
    db.add(farm)

    # Log audit event
    audit = OperatorActivityLog(
        operator_id=operator.id,
        action_type="REGISTER_FARMER",
        farmer_id=farmer.id,
        farm_id=farm.id,
        details_json=f"Assisted registration for {farmer.name} ({farmer.maittri_farmer_id}) from {farmer.district}"
    )
    db.add(audit)
    db.commit()

    return farmer


@router.get("/farmers", response_model=List[FarmerResponse])
def search_farmers(
    q: Optional[str] = Query(None, description="Search term for name, phone, village, or MT-FARM ID"),
    limit: int = 50,
    operator: User = Depends(require_operator),
    db: Session = Depends(get_db)
):
    """
    Search and list registered farmers.
    """
    query = db.query(Farmer)
    if q and q.strip():
        term = f"%{q.strip()}%"
        query = query.filter(
            or_(
                Farmer.name.ilike(term),
                Farmer.mobile_number.ilike(term),
                Farmer.village.ilike(term),
                Farmer.district.ilike(term),
                Farmer.maittri_farmer_id.ilike(term)
            )
        )
    return query.order_by(Farmer.id.desc()).limit(limit).all()


@router.get("/farmers/{farmer_id}", response_model=FarmerResponse)
def get_farmer_detail(
    farmer_id: int,
    operator: User = Depends(require_operator),
    db: Session = Depends(get_db)
):
    """Retrieve full farmer profile by primary key ID."""
    farmer = db.query(Farmer).filter(Farmer.id == farmer_id).first()
    if not farmer:
        raise HTTPException(status_code=404, detail="Farmer record not found")
    return farmer


@router.patch("/farmers/{farmer_id}", response_model=FarmerResponse)
def update_farmer(
    farmer_id: int,
    payload: FarmerUpdate,
    operator: User = Depends(require_operator),
    db: Session = Depends(get_db)
):
    """Update farmer profile details."""
    farmer = db.query(Farmer).filter(Farmer.id == farmer_id).first()
    if not farmer:
        raise HTTPException(status_code=404, detail="Farmer record not found")

    update_data = payload.model_dump(exclude_unset=True)
    for k, v in update_data.items():
        setattr(farmer, k, v)

    farmer.updated_at = datetime.now(timezone.utc)

    # Sync linked farm if present
    farm = db.query(Farm).filter(Farm.farmer_id == farmer.id).first()
    if farm:
        if payload.farm_area is not None:
            farm.area = payload.farm_area
        if payload.soil_type is not None:
            farm.soil_type = payload.soil_type
        if payload.current_crop is not None:
            farm.current_crop = payload.current_crop

    # Log audit event
    audit = OperatorActivityLog(
        operator_id=operator.id,
        action_type="UPDATE_FARMER",
        farmer_id=farmer.id,
        details_json=f"Updated profile for {farmer.name} ({farmer.maittri_farmer_id})"
    )
    db.add(audit)
    db.commit()
    db.refresh(farmer)
    return farmer


@router.get("/activity-logs")
def get_operator_activity_logs(
    limit: int = 50,
    operator: User = Depends(require_operator),
    db: Session = Depends(get_db)
):
    """Retrieve audit activity logs."""
    logs = db.query(OperatorActivityLog).order_by(OperatorActivityLog.id.desc()).limit(limit).all()
    return [
        {
            "id": l.id,
            "operator_id": l.operator_id,
            "action_type": l.action_type,
            "farmer_id": l.farmer_id,
            "farm_id": l.farm_id,
            "details": l.details_json,
            "timestamp": l.created_at.strftime("%Y-%m-%d %H:%M UTC") if l.created_at else ""
        }
        for l in logs
    ]
