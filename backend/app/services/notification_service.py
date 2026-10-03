"""
MAITTRI Multi-Channel Notification Dispatcher
---------------------------------------------
Decides notification channel (Web, SMS, IVR) based on priority and farmer consent.
"""

import logging
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session

from ..models import Notification, Farmer, CommunicationPreference
from .sms_service import dispatch_sms

logger = logging.getLogger("maittri.notifications")


def create_and_dispatch_notification(
    db: Session,
    title: str,
    message: str,
    farmer_id: Optional[int] = None,
    user_id: Optional[Any] = None,
    category: str = "general",
    priority: str = "NORMAL",
    channel: str = "WEB"
) -> Notification:
    """
    Creates in-app notification and optionally dispatches via SMS if consented and requested.
    Safely converts integer user_id while guarding against non-integer UUID strings to maintain
    PostgreSQL schema compatibility without destructive schema migrations.
    """
    safe_uid = None
    if user_id is not None:
        try:
            if isinstance(user_id, int):
                safe_uid = user_id
            elif str(user_id).isdigit():
                safe_uid = int(str(user_id))
        except Exception:
            safe_uid = None

    notif = Notification(
        farmer_id=farmer_id,
        user_id=safe_uid,
        title=title,
        message=message,
        category=category,
        channel=channel,
        priority=priority,
        read=False
    )
    db.add(notif)
    db.commit()
    db.refresh(notif)

    # Check if SMS dispatch is needed
    if channel in ("SMS", "ALL") and farmer_id:
        farmer = db.query(Farmer).filter(Farmer.id == farmer_id).first()
        if farmer and farmer.mobile_number:
            mob = farmer.mobile_number.strip()
            digits = "".join(c for c in mob if c.isdigit())
            if len(digits) >= 10 and not digits.startswith("00000"):
                pref = db.query(CommunicationPreference).filter(CommunicationPreference.farmer_id == farmer_id).first()
                # If consent is given or not explicitly opted out
                if not pref or pref.sms_enabled:
                    dispatch_sms(
                        db=db,
                        mobile_number=farmer.mobile_number,
                        message=f"MAITTRI Alert: {title}\n{message[:110]}",
                        farmer_id=farmer_id
                    )

    return notif
