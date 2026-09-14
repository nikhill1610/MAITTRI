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
    user_id: Optional[int] = None,
    category: str = "general",
    priority: str = "NORMAL",
    channel: str = "WEB"
) -> Notification:
    """
    Creates in-app notification and optionally dispatches via SMS if consented and requested.
    """
    notif = Notification(
        farmer_id=farmer_id,
        user_id=user_id,
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
