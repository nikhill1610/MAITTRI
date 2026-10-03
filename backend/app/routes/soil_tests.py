"""
Soil Test Booking & Certified Laboratory Report API Routes
------------------------------------------------------------
Workflow:
REQUESTED -> SCHEDULED -> SAMPLE_COLLECTED -> LAB_PROCESSING -> REPORT_AVAILABLE -> CANCELLED

Note on Scientific Safety:
IoT sensor values are indicative; lab test reports are certified laboratory measurements.
"""

import logging
from typing import List, Optional
from datetime import datetime, timezone
import uuid
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import (
    User, Farmer, Farm, SoilTestRequest, SoilTestReport, Notification
)
from ..schemas import (
    SoilTestRequestCreate, SoilTestRequestUpdate, SoilTestRequestResponse,
    SoilTestReportCreate, SoilTestReportResponse
)
from ..deps import (
    get_current_user, require_farmer_or_operator, require_operator,
    is_same_user, is_elevated_user, farm_belongs_to_farmer, get_authorized_farm
)
from ..services.notification_service import create_and_dispatch_notification

logger = logging.getLogger("maitri.soil_tests")
router = APIRouter()


def generate_soil_test_id(db: Session) -> str:
    """Generates next canonical soil test request ID like MT-STR-000001."""
    count = db.query(SoilTestRequest).count() + 1
    req_id = f"MT-STR-{count:06d}"
    while db.query(SoilTestRequest).filter(SoilTestRequest.request_id == req_id).first():
        count += 1
        req_id = f"MT-STR-{count:06d}"
    return req_id


@router.post("", response_model=SoilTestRequestResponse)
def book_soil_test(
    payload: SoilTestRequestCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Books a certified laboratory soil test request."""
    farmer = db.query(Farmer).filter(Farmer.id == payload.farmer_id).first()
    if not farmer:
        raise HTTPException(status_code=404, detail="Farmer not found")

    is_elevated = is_elevated_user(current_user)
    if not is_elevated and not is_same_user(farmer.user_id, current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: You cannot book a soil test for another farmer."
        )

    if payload.farm_id:
        get_authorized_farm(
            db, payload.farm_id, user=current_user, farmer=farmer,
            detail_not_found="Farm not found.",
            detail_forbidden="Farm does not belong to the authenticated farmer.",
            forbidden_status_code=400
        )

    str_obj = SoilTestRequest(
        request_id=f"TEMP-{uuid.uuid4().hex[:8]}",
        farmer_id=payload.farmer_id,
        farm_id=payload.farm_id,
        location=payload.location or f"{farmer.village or ''}, {farmer.district or ''}".strip(", "),
        crop=payload.crop or farmer.current_crop or "General",
        sample_date=payload.sample_date or datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        status="REQUESTED",
        notes=payload.notes
    )
    db.add(str_obj)
    db.flush()
    str_obj.request_id = f"MT-STR-{str_obj.id:06d}"
    db.commit()
    db.refresh(str_obj)

    req_id = str_obj.request_id

    # Notify farmer via multi-channel dispatcher (isolated so notification failure does not fail booking)
    try:
        create_and_dispatch_notification(
            db=db,
            farmer_id=farmer.id,
            user_id=farmer.user_id,
            title="सॉइल टेस्ट बुकिंग दर्ज (Soil Test Booked)",
            message=f"आपकी सॉइल टेस्ट बुकिंग आईडी {req_id} सफलतापूर्वक दर्ज कर ली गई है। शीघ्र ही नमूना संग्रह की तिथि निर्धारित होगी।",
            category="soil_test",
            channel="ALL"
        )
    except Exception as notif_err:
        logger.warning(f"Notification dispatch failed for soil test {req_id}: {notif_err}")

    return str_obj


@router.get("", response_model=List[SoilTestRequestResponse])
def list_soil_tests(
    farmer_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Lists soil test requests with optional filtering."""
    query = db.query(SoilTestRequest)
    # If farmer, restrict to their own requests
    if not is_elevated_user(current_user):
        farmer = db.query(Farmer).filter(Farmer.user_id == current_user.id).first()
        if farmer:
            query = query.filter(SoilTestRequest.farmer_id == farmer.id)
        else:
            return []
    elif farmer_id:
        query = query.filter(SoilTestRequest.farmer_id == farmer_id)

    if status:
        query = query.filter(SoilTestRequest.status == status)

    return query.order_by(SoilTestRequest.id.desc()).all()


@router.get("/{req_id}", response_model=SoilTestRequestResponse)
def get_soil_test_detail(
    req_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Retrieve soil test request by request_id with strict tenant ownership verification."""
    str_obj = db.query(SoilTestRequest).filter(SoilTestRequest.request_id == req_id).first()
    if not str_obj:
        raise HTTPException(status_code=404, detail="Soil test request not found")

    is_elevated = is_elevated_user(current_user)
    if not is_elevated:
        farmer = db.query(Farmer).filter(Farmer.id == str_obj.farmer_id).first()
        if not farmer or not is_same_user(farmer.user_id, current_user.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access forbidden: You cannot view another farmer's soil test request."
            )
    return str_obj


@router.patch("/{req_id}/status", response_model=SoilTestRequestResponse)
def update_soil_test_status(
    req_id: str,
    payload: SoilTestRequestUpdate,
    current_user: User = Depends(require_operator),
    db: Session = Depends(get_db)
):
    """Updates soil test status and alerts the farmer. Restricts mutation to authorized operators."""
    str_obj = db.query(SoilTestRequest).filter(SoilTestRequest.request_id == req_id).first()
    if not str_obj:
        raise HTTPException(status_code=404, detail="Soil test request not found")

    ALLOWED_SOIL_STATUS_TRANSITIONS = {
        "REQUESTED": {"SCHEDULED", "SAMPLE_COLLECTED", "CANCELLED"},
        "SCHEDULED": {"SAMPLE_COLLECTED", "LAB_PROCESSING", "CANCELLED"},
        "SAMPLE_COLLECTED": {"LAB_PROCESSING", "CANCELLED"},
        "LAB_PROCESSING": {"CANCELLED"},
        "REPORT_AVAILABLE": set(),
        "CANCELLED": set()
    }
    old_status = str_obj.status
    if old_status not in ALLOWED_SOIL_STATUS_TRANSITIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown or invalid soil test status '{old_status}'."
        )
    if payload.status not in ALLOWED_SOIL_STATUS_TRANSITIONS[old_status]:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status transition from '{old_status}' to '{payload.status}'."
        )

    str_obj.status = payload.status
    if payload.lab_name:
        str_obj.lab_name = payload.lab_name
    if payload.notes:
        str_obj.notes = payload.notes
    str_obj.updated_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(str_obj)

    # Dispatch notification on status transition
    if old_status != payload.status:
        farmer = db.query(Farmer).filter(Farmer.id == str_obj.farmer_id).first()
        if farmer:
            status_labels_hi = {
                "SCHEDULED": "नमूना संग्रह निर्धारित (Scheduled)",
                "SAMPLE_COLLECTED": "नमूना एकत्रित (Sample Collected)",
                "LAB_PROCESSING": "प्रयोगशाला जांच जारी (Lab Processing)",
                "REPORT_AVAILABLE": "जांच रिपोर्ट तैयार (Report Available)",
                "CANCELLED": "अनुरोध निरस्त (Cancelled)"
            }
            msg = f"आपकी सॉइल टेस्ट आईडी {req_id} की वर्तमान स्थिति: {status_labels_hi.get(payload.status, payload.status)}।"
            try:
                create_and_dispatch_notification(
                    db=db,
                    farmer_id=farmer.id,
                    user_id=farmer.user_id,
                    title="सॉइल टेस्ट स्थिति अपडेट (Soil Test Status Update)",
                    message=msg,
                    category="soil_test",
                    channel="SMS" if payload.status in ("SAMPLE_COLLECTED", "REPORT_AVAILABLE") else "WEB"
                )
            except Exception as notif_err:
                logger.warning(f"Notification dispatch failed for status update on {req_id}: {notif_err}")

    return str_obj


@router.get("/{req_id}/report", response_model=SoilTestReportResponse)
def get_soil_lab_report(
    req_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Retrieves certified laboratory report with tenant isolation checks."""
    str_obj = db.query(SoilTestRequest).filter(SoilTestRequest.request_id == req_id).first()
    if not str_obj:
        raise HTTPException(status_code=404, detail="Soil test request not found")

    is_elevated = is_elevated_user(current_user)
    if not is_elevated:
        farmer = db.query(Farmer).filter(Farmer.id == str_obj.farmer_id).first()
        if not farmer or not is_same_user(farmer.user_id, current_user.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access forbidden: You cannot view another farmer's lab report."
            )

    report = db.query(SoilTestReport).filter(SoilTestReport.request_id == req_id).order_by(SoilTestReport.id.desc()).first()
    if not report:
        raise HTTPException(status_code=404, detail="Certified lab report not yet available for this request")
    return report


@router.post("/{req_id}/report", response_model=SoilTestReportResponse)
def submit_soil_lab_report(
    req_id: str,
    payload: SoilTestReportCreate,
    current_user: User = Depends(require_operator),
    db: Session = Depends(get_db)
):
    """Submits certified laboratory NPK and micro-nutrient test measurements. Restricted to operators."""
    str_obj = db.query(SoilTestRequest).filter(SoilTestRequest.request_id == req_id).first()
    if not str_obj:
        raise HTTPException(status_code=404, detail="Soil test request not found")

    if str_obj.status not in ("SAMPLE_COLLECTED", "LAB_PROCESSING"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot submit lab report for request in '{str_obj.status}' status. Request must be in 'SAMPLE_COLLECTED' or 'LAB_PROCESSING' status."
        )

    # Authoritative farmer comes from the authenticated soil test request record
    farmer = db.query(Farmer).filter(Farmer.id == str_obj.farmer_id).first()
    if not farmer:
        raise HTTPException(status_code=404, detail="Associated farmer not found")

    # If client supplied a farmer_id that conflicts with the request, reject
    if payload.farmer_id and payload.farmer_id != str_obj.farmer_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Payload farmer_id does not match the soil test request."
        )

    # If both request farm_id and payload farm_id exist and differ, reject
    if str_obj.farm_id and payload.farm_id and payload.farm_id != str_obj.farm_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Payload farm_id does not match the soil test request."
        )

    # Validate farm ownership to prevent modifying another farmer's farm
    target_farm_id = str_obj.farm_id or payload.farm_id
    target_farm = None
    if target_farm_id:
        target_farm = db.query(Farm).filter(Farm.id == target_farm_id).first()
        if not target_farm:
            raise HTTPException(status_code=404, detail="Farm not found.")
        if not farm_belongs_to_farmer(target_farm, farmer):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Farm does not belong to the farmer associated with this request."
            )

    # Update request status to REPORT_AVAILABLE
    str_obj.status = "REPORT_AVAILABLE"
    str_obj.lab_name = payload.lab_name
    str_obj.updated_at = datetime.now(timezone.utc)

    report = SoilTestReport(
        request_id=req_id,
        farmer_id=str_obj.farmer_id,
        farm_id=target_farm.id if target_farm else None,
        lab_name=payload.lab_name,
        test_date=payload.test_date or datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        nitrogen=payload.nitrogen,
        phosphorus=payload.phosphorus,
        potassium=payload.potassium,
        ph=payload.ph,
        ec=payload.ec,
        organic_carbon=payload.organic_carbon,
        zinc=payload.zinc,
        iron=payload.iron,
        boron=payload.boron,
        sulphur=payload.sulphur,
        is_certified_lab_test=True
    )
    db.add(report)

    # Mark soil test available on Farmer entity
    farmer.soil_test_available = True

    # Sync to farm only if validated to belong to this farmer
    if target_farm:
        if payload.nitrogen is not None:
            target_farm.soil_n = payload.nitrogen
        if payload.phosphorus is not None:
            target_farm.soil_p = payload.phosphorus
        if payload.potassium is not None:
            target_farm.soil_k = payload.potassium
        if payload.ph is not None:
            target_farm.soil_ph = payload.ph
        if payload.organic_carbon is not None:
            target_farm.organic_carbon = payload.organic_carbon

    db.commit()
    db.refresh(report)

    # Notify authoritative farmer
    try:
        create_and_dispatch_notification(
            db=db,
            farmer_id=farmer.id,
            user_id=farmer.user_id,
            title="सॉइल टेस्ट रिपोर्ट उपलब्ध (Soil Report Available)",
            message=f"सॉइल टेस्ट {req_id} की प्रमाणित लैब रिपोर्ट ({payload.lab_name}) तैयार है। पोर्टल अथवा सेवा केंद्र से रिपोर्ट प्राप्त करें।",
            category="soil_test",
            channel="ALL"
        )
    except Exception as notif_err:
        logger.warning(f"Notification dispatch failed for report on {req_id}: {notif_err}")

    return report
