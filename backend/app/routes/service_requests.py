"""
Service Request Tracking API Routes
------------------------------------
General assistance requests:
SOIL_TEST, CROP_ADVISORY, PEST_ADVISORY, FERTILIZER_ADVISORY,
DOCUMENT_ASSISTANCE, SCHEME_ASSISTANCE, INSURANCE_ASSISTANCE
"""

from typing import List, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import User, Farmer, Farm, ServiceRequest
from ..schemas import ServiceRequestCreate, ServiceRequestUpdate, ServiceRequestResponse
from ..deps import get_current_user, require_farmer_or_operator
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

    user_role = (getattr(current_user, "role", "FARMER") or "FARMER").upper()
    is_elevated = user_role in ("AUTHORIZED_OPERATOR", "OPERATOR", "ADMIN")
    if not is_elevated and str(farmer.user_id) != str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: You cannot create a service request for another farmer."
        )

    req_id = generate_service_request_id(db)

    sr = ServiceRequest(
        request_id=req_id,
        farmer_id=payload.farmer_id,
        farm_id=payload.farm_id,
        operator_id=current_user.id if getattr(current_user, "role", "") == "AUTHORIZED_OPERATOR" else None,
        service_type=payload.service_type,
        status="REQUESTED",
        description=payload.description
    )
    db.add(sr)
    db.commit()
    db.refresh(sr)

    # Notify farmer
    create_and_dispatch_notification(
        db=db,
        farmer_id=farmer.id,
        user_id=farmer.user_id,
        title="सेवा अनुरोध दर्ज (Service Request Submitted)",
        message=f"आपका सेवा अनुरोध ({sr.service_type}) आईडी {req_id} दर्ज कर लिया गया है।",
        category="service",
        channel="ALL"
    )

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
    user_role = (getattr(current_user, "role", "FARMER") or "FARMER").upper()

    if user_role not in ("AUTHORIZED_OPERATOR", "ADMIN"):
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

    user_role = (getattr(current_user, "role", "FARMER") or "FARMER").upper()
    is_elevated = user_role in ("AUTHORIZED_OPERATOR", "OPERATOR", "ADMIN")
    if not is_elevated:
        farmer = db.query(Farmer).filter(Farmer.id == sr.farmer_id).first()
        if not farmer or str(farmer.user_id) != str(current_user.id):
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

    user_role = (getattr(current_user, "role", "FARMER") or "FARMER").upper()
    is_elevated = user_role in ("AUTHORIZED_OPERATOR", "OPERATOR", "ADMIN")
    farmer = db.query(Farmer).filter(Farmer.id == sr.farmer_id).first()
    is_owner = farmer and str(farmer.user_id) == str(current_user.id)

    if not is_elevated and not is_owner:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: You cannot modify another farmer's service request."
        )

    # Farmers can only cancel their own request; resolving or updating notes requires an operator
    if not is_elevated:
        if payload.status not in ("CANCELLED",):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Farmers may only cancel pending requests. Status resolution requires an Authorized Operator."
            )

    old_status = sr.status
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
        create_and_dispatch_notification(
            db=db,
            farmer_id=farmer.id,
            user_id=farmer.user_id,
            title="सेवा अनुरोध स्थिति (Service Request Status)",
            message=f"अनुरोध {req_id} की स्थिति: {payload.status}। {payload.resolution_notes or ''}",
            category="service",
                channel="SMS" if payload.status == "COMPLETED" else "WEB"
            )

    return sr
