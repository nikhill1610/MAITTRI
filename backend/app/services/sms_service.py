"""
MAITTRI SMS Service — Provider-Agnostic Telephony Engine
---------------------------------------------------------
Principles:
- Never hardcodes any single SMS provider (Twilio, MSG91, Exotel, etc.)
- Transparent fallback to safe DEMO MODE if credentials are unconfigured
- Records all delivery attempts in SQLite `sms_logs` table
- Clearly labels simulation in Demo Mode; never claims actual SMS was delivered without credentials
"""

import os
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from datetime import datetime, timezone
import requests
from sqlalchemy.orm import Session

from ..models import SMSLog, Farmer

logger = logging.getLogger("maittri.sms")


class SMSProvider(ABC):
    """Abstract interface for SMS delivery gateways."""

    @abstractmethod
    def send(self, to: str, message: str, template_id: Optional[str] = None) -> Dict[str, Any]:
        """Dispatch SMS. Returns dict with keys: success (bool), status (str), provider (str), error (optional str)."""
        pass


class DemoSMSAdapter(SMSProvider):
    """
    Simulation adapter used during development or when external credentials are not set.
    Safe: Logs to database and returns simulated confirmation with clear DEMO MODE indicator.
    """

    def send(self, to: str, message: str, template_id: Optional[str] = None) -> Dict[str, Any]:
        logger.info(f"[DEMO SMS] Simulated message to {to}: {message[:60]}...")
        return {
            "success": True,
            "status": "SIMULATED_DEMO",
            "provider": "demo",
            "is_demo_mode": True,
            "message": "Demo SMS generated successfully. (External provider credentials not configured)",
            "dispatched_at": datetime.now(timezone.utc).isoformat()
        }


class TwilioSMSAdapter(SMSProvider):
    """Adapter for Twilio SMS REST API."""

    def __init__(self, account_sid: str, auth_token: str, sender_number: str):
        self.account_sid = account_sid
        self.auth_token = auth_token
        self.sender = sender_number

    def send(self, to: str, message: str, template_id: Optional[str] = None) -> Dict[str, Any]:
        url = f"https://api.twilio.com/2010-04-01/Accounts/{self.account_sid}/Messages.json"
        payload = {
            "From": self.sender,
            "To": to,
            "Body": message
        }
        try:
            resp = requests.post(
                url,
                data=payload,
                auth=(self.account_sid, self.auth_token),
                timeout=10
            )
            if resp.status_code in (200, 201):
                return {"success": True, "status": "SENT", "provider": "twilio", "is_demo_mode": False}
            return {
                "success": False,
                "status": "FAILED",
                "provider": "twilio",
                "is_demo_mode": False,
                "error": resp.text[:200]
            }
        except Exception as e:
            return {
                "success": False,
                "status": "FAILED",
                "provider": "twilio",
                "is_demo_mode": False,
                "error": str(e)
            }


class Msg91SMSAdapter(SMSProvider):
    """Adapter for MSG91 Indian SMS Gateway with DLT support."""

    def __init__(self, auth_key: str, sender_id: str):
        self.auth_key = auth_key
        self.sender_id = sender_id

    def send(self, to: str, message: str, template_id: Optional[str] = None) -> Dict[str, Any]:
        url = "https://control.msg91.com/api/v5/flow/"
        headers = {
            "authkey": self.auth_key,
            "Content-Type": "application/json"
        }
        clean_num = to.replace("+", "").replace("-", "").replace(" ", "")
        payload = {
            "template_id": template_id or os.getenv("SMS_TEMPLATE_ID", ""),
            "sender": self.sender_id,
            "short_url": "0",
            "recipients": [{"mobiles": clean_num, "VAR1": message[:30], "VAR2": message[30:60]}]
        }
        try:
            resp = requests.post(url, json=payload, headers=headers, timeout=10)
            if resp.status_code == 200:
                return {"success": True, "status": "SENT", "provider": "msg91", "is_demo_mode": False}
            return {
                "success": False,
                "status": "FAILED",
                "provider": "msg91",
                "is_demo_mode": False,
                "error": resp.text[:200]
            }
        except Exception as e:
            return {
                "success": False,
                "status": "FAILED",
                "provider": "msg91",
                "is_demo_mode": False,
                "error": str(e)
            }


def get_sms_provider() -> SMSProvider:
    """Factory returning configured provider or defaulting safely to Demo adapter."""
    provider_name = (os.getenv("SMS_PROVIDER") or "demo").lower().strip()
    api_key = os.getenv("SMS_API_KEY", "").strip()

    if provider_name == "twilio" and api_key and os.getenv("SMS_API_SECRET"):
        return TwilioSMSAdapter(
            account_sid=api_key,
            auth_token=os.getenv("SMS_API_SECRET", ""),
            sender_number=os.getenv("SMS_SENDER_ID", "+1234567890")
        )
    elif provider_name == "msg91" and api_key:
        return Msg91SMSAdapter(
            auth_key=api_key,
            sender_id=os.getenv("SMS_SENDER_ID", "MAITRI")
        )

    # Safe fallback
    return DemoSMSAdapter()


def dispatch_sms(
    db: Session,
    mobile_number: str,
    message: str,
    farmer_id: Optional[int] = None,
    template_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Dispatches SMS through configured gateway, logs attempt to database, and returns result.
    """
    provider = get_sms_provider()
    result = provider.send(to=mobile_number, message=message, template_id=template_id)

    # Persist in audit log
    log_entry = SMSLog(
        farmer_id=farmer_id,
        mobile_number=mobile_number,
        message_content=message,
        provider=result.get("provider", "demo"),
        status=result.get("status", "SENT"),
        error_message=result.get("error"),
        is_demo_mode=result.get("is_demo_mode", True)
    )
    try:
        db.add(log_entry)
        db.commit()
        db.refresh(log_entry)
        result["log_id"] = log_entry.id
    except Exception as e:
        db.rollback()
        logger.warning(f"Could not persist SMS log: {e}")

    return result
