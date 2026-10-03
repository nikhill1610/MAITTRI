"""
Service Request Tracking API Routes
------------------------------------
General assistance requests:
SOIL_TEST, CROP_ADVISORY, PEST_ADVISORY, FERTILIZER_ADVISORY,
DOCUMENT_ASSISTANCE, SCHEME_ASSISTANCE, INSURANCE_ASSISTANCE
"""

from typing import List, Optional
from datetime import datetime, timezone
import uuid
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import User, Farmer, Farm, ServiceRequest
from ..schemas import ServiceRequestCreate, ServiceRequestUpdate, ServiceRequestResponse
from ..deps import (
    get_current_user, require_farmer_or_operator,
    is_same_user, is_elevated_user, farm_belongs_to_farmer, get_authorized_farm
)
from ..services.notification_service import create_and_dispatch_notification

router = APIRouter()


def generate_service_request_id(db: Session) -> str:
    """Generates canonical request ID like MT-REQ-000001."""
    count = db.query(ServiceRequest).count() + 1
    req_id = f"MT-REQ-{count:06d}"
    while db.query(ServiceRequest).filter(ServiceRequest.request_id == req_id).first():
        count += 1
        req_id = f"MT-REQ-{count:06d}"
    return req_id


@router.post("", response_model=ServiceRequestResponse)
def create_service_request(
    payload: ServiceRequestCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Submits an agronomic or administrative service request."""
    farmer = db.query(Farmer).filter(Farmer.id == payload.farmer_id).first()
    if not farmer:
        raise HTTPException(status_code=404, detail="Farmer not found")

    is_elevated = is_elevated_user(current_user)
    if not is_elevated and not is_same_user(farmer.user_id, current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: You cannot create a service request for another farmer."
        )

    if payload.farm_id:
        get_authorized_farm(
            db, payload.farm_id, user=current_user, farmer=farmer,
            detail_not_found="Farm not found.",
            detail_forbidden="Farm does not belong to the authenticated farmer.",
            forbidden_status_code=400
        )

    sr = ServiceRequest(
        request_id=f"TEMP-{uuid.uuid4().hex[:8]}",
        farmer_id=payload.farmer_id,
        farm_id=payload.farm_id,
        operator_id=current_user.id if (getattr(current_user, "role", "") or "").upper() in ("AUTHORIZED_OPERATOR", "OPERATOR") else None,
        service_type=payload.service_type,
        status="REQUESTED",
        description=payload.description
    )
    db.add(sr)
    db.flush()
    sr.request_id = f"MT-REQ-{sr.id:06d}"
    db.commit()
    db.refresh(sr)

    req_id = sr.request_id

    # Notify farmer (isolated so notification failure does not fail request creation)
    try:
        create_and_dispatch_notification(
            db=db,
            farmer_id=farmer.id,
            user_id=farmer.user_id,
            title="सेवा अनुरोध दर्ज (Service Request Submitted)",
            message=f"आपका सेवा अनुरोध ({sr.service_type}) आईडी {req_id} दर्ज कर लिया गया है।",
            category="service",
            channel="ALL"
        )
    except Exception as exc:
        import logging
        logging.getLogger(__name__).warning("Failed to dispatch service request notification: %s", exc)

    return sr


@router.get("", response_model=List[ServiceRequestResponse])
def list_service_requests(
    farmer_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    service_type: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Lists service requests with role-based filtering."""
    query = db.query(ServiceRequest)
    if not is_elevated_user(current_user):
        farmer = db.query(Farmer).filter(Farmer.user_id == current_user.id).first()
        if farmer:
            query = query.filter(ServiceRequest.farmer_id == farmer.id)
        else:
            return []
    elif farmer_id:
        query = query.filter(ServiceRequest.farmer_id == farmer_id)

    if status:
        query = query.filter(ServiceRequest.status == status)
    if service_type:
        query = query.filter(ServiceRequest.service_type == service_type)

    return query.order_by(ServiceRequest.id.desc()).all()


@router.get("/{req_id}", response_model=ServiceRequestResponse)
def get_service_request(
    req_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Retrieves service request details with tenant isolation verification."""
    sr = db.query(ServiceRequest).filter(ServiceRequest.request_id == req_id).first()
    if not sr:
        raise HTTPException(status_code=404, detail="Service request not found")

    is_elevated = is_elevated_user(current_user)
    if not is_elevated:
        farmer = db.query(Farmer).filter(Farmer.id == sr.farmer_id).first()
        if not farmer or not is_same_user(farmer.user_id, current_user.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access forbidden: You cannot view another farmer's service request."
            )
    return sr


@router.patch("/{req_id}", response_model=ServiceRequestResponse)
def update_service_request(
    req_id: str,
    payload: ServiceRequestUpdate,
    current_user: User = Depends(require_farmer_or_operator),
    db: Session = Depends(get_db)
):
    """Updates service request resolution status. Enforces ownership or operator privilege."""
    sr = db.query(ServiceRequest).filter(ServiceRequest.request_id == req_id).first()
    if not sr:
        raise HTTPException(status_code=404, detail="Service request not found")

    is_elevated = is_elevated_user(current_user)
    farmer = db.query(Farmer).filter(Farmer.id == sr.farmer_id).first()
    is_owner = farmer and is_same_user(farmer.user_id, current_user.id)

    if not is_elevated and not is_owner:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: You cannot modify another farmer's service request."
        )

    ALLOWED_SERVICE_STATUS_TRANSITIONS = {
        "REQUESTED": {"ASSIGNED", "IN_PROGRESS", "COMPLETED", "CANCELLED"},
        "ASSIGNED": {"IN_PROGRESS", "COMPLETED", "CANCELLED"},
        "IN_PROGRESS": {"COMPLETED", "CANCELLED"},
        "COMPLETED": set(),
        "CANCELLED": set()
    }
    old_status = sr.status
    if old_status in ("COMPLETED", "CANCELLED"):
        raise HTTPException(
            status_code=400,
            detail=f"Service request is already '{old_status}' and cannot be modified."
        )
    if old_status not in ALLOWED_SERVICE_STATUS_TRANSITIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown or invalid service request status '{old_status}'."
        )
    if payload.status not in ALLOWED_SERVICE_STATUS_TRANSITIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid service request status '{payload.status}'."
        )
    if payload.status != old_status and payload.status not in ALLOWED_SERVICE_STATUS_TRANSITIONS[old_status]:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status transition from '{old_status}' to '{payload.status}'."
        )

    # Farmers can only cancel their own request; resolving or updating notes requires an operator
    if not is_elevated:
        if payload.status not in ("CANCELLED",):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Farmers may only cancel pending requests. Status resolution requires an Authorized Operator."
            )
        if sr.status != "REQUESTED":
            raise HTTPException(
                status_code=400,
                detail=f"Cannot cancel service request in '{sr.status}' status. Only pending requests can be cancelled."
            )

    sr.status = payload.status
    if payload.resolution_notes:
        if not is_elevated and payload.resolution_notes != sr.resolution_notes:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only Authorized Operators may provide official resolution notes."
            )
        sr.resolution_notes = payload.resolution_notes
    sr.updated_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(sr)

    if old_status != payload.status and farmer:
        try:
            create_and_dispatch_notification(
                db=db,
                farmer_id=farmer.id,
                user_id=farmer.user_id,
                title="सेवा अनुरोध स्थिति (Service Request Status)",
                message=f"अनुरोध {req_id} की स्थिति: {payload.status}। {payload.resolution_notes or ''}",
                category="service",
                channel="SMS" if payload.status == "COMPLETED" else "WEB"
            )
        except Exception as exc:
            import logging
            logging.getLogger(__name__).warning("Failed to dispatch service request status notification: %s", exc)

    return sr
