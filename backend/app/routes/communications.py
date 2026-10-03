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

import os
import hmac
import hashlib
import base64
from xml.sax.saxutils import escape as xml_escape
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
from ..deps import get_current_user, require_farmer_or_operator, require_operator, is_elevated_user, is_same_user
from ..services.sms_service import dispatch_sms
from ..services.ivr_service import handle_ivr_interaction

router = APIRouter()


def validate_twilio_signature(url: str, post_data: dict, signature: str, auth_token: str) -> bool:
    """Validates Twilio webhook request HMAC-SHA1 signature."""
    s = url
    for k in sorted(post_data.keys()):
        s += f"{k}{post_data[k]}"
    computed = base64.b64encode(
        hmac.new(auth_token.encode("utf-8"), s.encode("utf-8"), hashlib.sha1).digest()
    ).decode("utf-8")
    return hmac.compare_digest(computed, signature)


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

    if not is_elevated_user(current_user) and not is_same_user(farmer.user_id, current_user.id):
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

    if not is_elevated_user(current_user) and not is_same_user(farmer.user_id, current_user.id):
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
    limit: int = Query(50, ge=1, le=500, description="Max logs to return"),
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

    # In production, missing Twilio auth token must fail closed
    is_prod = os.getenv("ENVIRONMENT", "production").lower() == "production"
    twilio_auth_token = os.getenv("TWILIO_AUTH_TOKEN")
    allow_dev_sim = (not is_prod) and (
        os.getenv("ALLOW_IVR_SIMULATION", "true").lower() in ("true", "1") or
        os.getenv("PYTEST_CURRENT_TEST") is not None
    )

    if not twilio_auth_token:
        if is_prod or not allow_dev_sim:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Twilio integration not configured in production."
            )
    else:
        signature = request.headers.get("X-Twilio-Signature")
        if not signature:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Missing Twilio signature header."
            )
        # Proxy-safe URL reconstruction
        proto = request.headers.get("X-Forwarded-Proto") or request.url.scheme
        host = request.headers.get("X-Forwarded-Host") or request.headers.get("Host") or request.url.netloc
        path = request.url.path
        query = f"?{request.url.query}" if request.url.query else ""
        canonical_url = f"{proto}://{host}{path}{query}"

        form_dict = {k: str(v) for k, v in form_data.items()}
        is_valid = validate_twilio_signature(canonical_url, form_dict, signature, twilio_auth_token)
        if not is_valid and canonical_url != str(request.url):
            is_valid = validate_twilio_signature(str(request.url), form_dict, signature, twilio_auth_token)
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid Twilio webhook signature."
            )

    digits = form_data.get("Digits") or form_data.get("dtmf") or ""
    caller = form_data.get("From") or form_data.get("CallFrom") or ""
    call_sid = form_data.get("CallSid") or form_data.get("call_sid") or None
    session_id = str(call_sid).strip() if call_sid else None

    # Load existing IVR session state if available
    current_menu = "main"
    language = "hi"
    if session_id:
        existing_session = db.query(IVRSession).filter(IVRSession.session_id == session_id).first()
        if existing_session:
            current_menu = existing_session.current_menu or "main"
            language = existing_session.language or "hi"

    result = handle_ivr_interaction(
        db=db,
        session_id=session_id,
        phone_number=str(caller),
        digits_pressed=str(digits) if digits else None,
        current_menu=current_menu,
        language=language
    )
    res_lang = result.get("language") or language or "hi"
    if res_lang == "en":
        raw_text = result.get("audio_text_en") or result.get("audio_text") or result.get("audio_text_hi") or ""
        say_lang = "en-IN"
    else:
        raw_text = result.get("audio_text_hi") or result.get("audio_text") or result.get("audio_text_en") or ""
        say_lang = "hi-IN"
    safe_audio_text = xml_escape(str(raw_text))
    twiml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<Response>\n'
        f'    <Say language="{say_lang}">{safe_audio_text}</Say>\n'
        '    <Gather numDigits="1" timeout="10" />\n'
        '</Response>'
    )
    return Response(content=twiml, media_type="application/xml")
