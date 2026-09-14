"""
Multi-Channel Communication API Routes (SMS & IVR)
---------------------------------------------------
Provides:
1. Farmer communication preferences & explicit consent management
2. SMS dispatch & broadcast dispatcher with safe DEMO MODE
3. SMS delivery audit logs
4. Interactive IVR testing simulator for keypad phone verification
5. Incoming telephony webhook for real or simulated IVR systems
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import User, Farmer, CommunicationPreference, SMSLog, IVRSession
from ..schemas import (
    CommunicationPreferenceUpdate, CommunicationPreferenceResponse,
    SMSBroadcastRequest, SMSLogResponse,
    IVRSimulateRequest, IVRSimulateResponse
)
from ..deps import get_current_user, require_farmer_or_operator, require_operator
from ..services.sms_service import dispatch_sms
from ..services.ivr_service import handle_ivr_interaction

router = APIRouter()


@router.get("/preferences/{farmer_id}", response_model=CommunicationPreferenceResponse)
def get_communication_preferences(
    farmer_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Retrieves farmer's communication preferences and consent status with ownership verification."""
    farmer = db.query(Farmer).filter(Farmer.id == farmer_id).first()
    if not farmer:
        raise HTTPException(status_code=404, detail="Farmer not found")

    user_role = (getattr(current_user, "role", "FARMER") or "FARMER").upper()
    is_elevated = user_role in ("AUTHORIZED_OPERATOR", "OPERATOR", "ADMIN")
    if not is_elevated and str(farmer.user_id) != str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: You cannot view communication preferences for another farmer."
        )

    pref = db.query(CommunicationPreference).filter(
        CommunicationPreference.farmer_id == farmer_id
    ).first()
    if not pref:
        # Default initialize
        pref = CommunicationPreference(farmer_id=farmer_id)
        db.add(pref)
        db.commit()
        db.refresh(pref)
    return pref


@router.patch("/preferences/{farmer_id}", response_model=CommunicationPreferenceResponse)
def update_communication_preferences(
    farmer_id: int,
    payload: CommunicationPreferenceUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Updates farmer's communication preferences with ownership verification."""
    farmer = db.query(Farmer).filter(Farmer.id == farmer_id).first()
    if not farmer:
        raise HTTPException(status_code=404, detail="Farmer not found")

    user_role = (getattr(current_user, "role", "FARMER") or "FARMER").upper()
    is_elevated = user_role in ("AUTHORIZED_OPERATOR", "OPERATOR", "ADMIN")
    if not is_elevated and str(farmer.user_id) != str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: You cannot update communication preferences for another farmer."
        )

    pref = db.query(CommunicationPreference).filter(
        CommunicationPreference.farmer_id == farmer_id
    ).first()
    if not pref:
        pref = CommunicationPreference(farmer_id=farmer_id)
        db.add(pref)

    update_data = payload.model_dump(exclude_unset=True)
    for k, v in update_data.items():
        setattr(pref, k, v)

    db.commit()
    db.refresh(pref)
    return pref


@router.post("/sms/send")
def send_sms_broadcast(
    payload: SMSBroadcastRequest,
    db: Session = Depends(get_db),
    operator: User = Depends(require_operator)
):
    """
    Dispatches SMS to targeted farmers or mobile numbers. Restricted to authorized operators.
    Runs transparently in DEMO MODE if external provider credentials are not configured.
    """
    destinations = []
    if payload.mobile_numbers:
        for num in payload.mobile_numbers:
            destinations.append((num, None))

    if payload.farmer_ids:
        farmers = db.query(Farmer).filter(Farmer.id.in_(payload.farmer_ids)).all()
        for f in farmers:
            if f.mobile_number:
                destinations.append((f.mobile_number, f.id))

    if not destinations:
        raise HTTPException(status_code=400, detail="No valid mobile numbers or farmer IDs provided")

    results = []
    for mobile, f_id in destinations:
        res = dispatch_sms(
            db=db,
            mobile_number=mobile,
            message=payload.message,
            farmer_id=f_id
        )
        results.append({
            "mobile": mobile,
            "farmer_id": f_id,
            "status": res.get("status"),
            "is_demo_mode": res.get("is_demo_mode", True)
        })

    is_any_demo = any(r.get("is_demo_mode") for r in results)
    return {
        "dispatched_count": len(results),
        "results": results,
        "is_demo_mode": is_any_demo,
        "notice": "Messages recorded in DEMO MODE (Safe prototype execution)." if is_any_demo else "Dispatched via live SMS provider."
    }


@router.get("/sms/logs", response_model=List[SMSLogResponse])
def get_sms_logs(
    farmer_id: Optional[int] = Query(None),
    limit: int = 50,
    db: Session = Depends(get_db),
    operator: User = Depends(require_operator)
):
    """Retrieves outbound SMS transmission logs."""
    query = db.query(SMSLog)
    if farmer_id:
        query = query.filter(SMSLog.farmer_id == farmer_id)
    return query.order_by(SMSLog.id.desc()).limit(limit).all()


@router.post("/ivr/simulate", response_model=IVRSimulateResponse)
def simulate_ivr_call(
    payload: IVRSimulateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_farmer_or_operator)
):
    """
    Interactive IVR simulator allowing operators and developers to test the voice tree
    using DTMF keypad button presses without needing actual telecom hardware.
    """
    result = handle_ivr_interaction(
        db=db,
        phone_number=payload.phone_number,
        digits_pressed=payload.digits_pressed,
        current_menu=payload.current_menu,
        language=payload.language,
        diagnostic_step=payload.diagnostic_step or 0,
        diagnostic_answers=payload.diagnostic_answers
    )
    return result


@router.post("/ivr/webhook")
async def ivr_telephony_webhook(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Standard voice webhook endpoint compatible with telephony providers (Twilio / Exotel).
    Returns basic TwiML voice XML response.
    """
    form_data = await request.form()
    digits = form_data.get("Digits") or form_data.get("dtmf") or ""
    caller = form_data.get("From") or form_data.get("CallFrom") or "9876543210"

    result = handle_ivr_interaction(
        db=db,
        phone_number=str(caller),
        digits_pressed=str(digits) if digits else None,
        current_menu="main",
        language="hi"
    )

    twiml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<Response>\n'
        f'    <Say language="hi-IN">{result.get("audio_text_hi")}</Say>\n'
        '    <Gather numDigits="1" timeout="10" />\n'
        '</Response>'
    )
    return Response(content=twiml, media_type="application/xml")
