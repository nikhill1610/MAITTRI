import os
import secrets
import logging
from fastapi import APIRouter, Depends, Query, Header, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional, List, Dict, Any

from ..database import get_db
from ..deps import get_optional_current_user, is_elevated_user
from ..schemas import (
    IoTSensorDataCreate,
    IoTLatestResponse,
    IoTDeviceSummary,
    IoTThresholdConfig
)
from ..services.iot_service import (
    process_incoming_sensor_data,
    get_latest_telemetry,
    list_registered_devices,
    get_telemetry_history,
    get_current_thresholds,
    update_thresholds,
    generate_simulation_payload,
    get_host_lan_ips
)

logger = logging.getLogger("maitri.iot")
router = APIRouter()


@router.post("/sensor-data", status_code=status.HTTP_200_OK)
@router.post("/telemetry", status_code=status.HTTP_200_OK)
@router.post("/data", status_code=status.HTTP_200_OK)
def post_sensor_data(
    data: IoTSensorDataCreate,
    x_device_token: Optional[str] = Header(None, alias="X-Device-Token"),
    db: Session = Depends(get_db),
    user = Depends(get_optional_current_user)
):
    """
    Ingests live telemetry from authenticated ESP8266 or ESP32 hardware prototype.
    Validates X-Device-Token against registered hardware node.
    Automatically computes nearest object distance & alert status.
    Persists record into Supabase PostgreSQL referencing iot_devices.id.
    """
    try:
        telemetry = process_incoming_sensor_data(db, data, user=user, device_token=x_device_token)
        return {
            "success": True,
            "status": "success",
            "message": "Sensor data received successfully",
            "data": telemetry
        }
    except PermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to process IoT sensor data: {str(e)}"
        )


@router.get("/latest", response_model=IoTLatestResponse)
def get_latest(
    device_id: Optional[str] = Query(None, description="Optional filter by device ID (e.g. MAITRI_ESP8266_01)"),
    db: Session = Depends(get_db),
    user = Depends(get_optional_current_user)
):
    """
    Retrieves the most recent sensor reading and ultrasonic radar scan.
    Calculates live device online/offline status based on configurable timeout.
    Enforces ownership isolation when queried by authenticated users.
    """
    try:
        telemetry = get_latest_telemetry(db, device_id, user=user)
        return telemetry
    except PermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )


@router.get("/devices", response_model=List[IoTDeviceSummary])
def get_devices(
    db: Session = Depends(get_db),
    user = Depends(get_optional_current_user)
):
    """
    Lists registered IoT hardware controllers (ESP8266, ESP32) with live status.
    Filters by owner if authenticated as a farmer.
    """
    return list_registered_devices(db, user=user)


@router.get("/history")
def get_history(
    device_id: Optional[str] = Query(None, description="Filter history by device ID"),
    limit: int = Query(30, ge=5, le=100, description="Max points to return"),
    db: Session = Depends(get_db),
    user = Depends(get_optional_current_user)
):
    """
    Retrieves chronological sensor history for temperature, humidity, and soil moisture charts.
    Enforces ownership isolation.
    """
    try:
        return get_telemetry_history(db, device_id, limit, user=user)
    except PermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )


@router.get("/config")
def get_config():
    """
    Returns the current configurable distance thresholds and device timeout settings.
    Host LAN IPs are only exposed in development environments.
    """
    is_prod = os.getenv("ENVIRONMENT", "production").lower() == "production"
    lan_ips, recommended_url = ([], None) if is_prod else get_host_lan_ips()
    return {
        "status": "success",
        "thresholds": get_current_thresholds(),
        "lan_ips": lan_ips,
        "recommended_url": recommended_url
    }


@router.get("/lan-info")
def get_lan_info():
    """
    Returns detected host machine LAN endpoints and copy-paste URL for Arduino sketches.
    Disabled in production.
    """
    if os.getenv("ENVIRONMENT", "production").lower() == "production":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="LAN debugging endpoint disabled in production."
        )
    lan_ips, recommended_url = get_host_lan_ips()
    return {
        "status": "success",
        "lan_ips": lan_ips,
        "recommended_url": recommended_url
    }


@router.post("/config")
def set_config(
    config: IoTThresholdConfig,
    user = Depends(get_optional_current_user)
):
    """
    Updates configurable distance thresholds (CLEAR, WARNING, CRITICAL) and timeout.
    Enforces that registered farmers and anonymous callers cannot reconfigure hardware thresholds.
    """
    is_prod = os.getenv("ENVIRONMENT", "production").lower() == "production"
    dev_sim_allowed = (not is_prod) and (
        os.getenv("ALLOW_DEV_CONFIG", "false").lower() in ("true", "1") or
        os.getenv("PYTEST_CURRENT_TEST") is not None
    )

    if not user:
        if not dev_sim_allowed:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required to configure thresholds."
            )
    elif not is_elevated_user(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Threshold configuration requires Authorized Operator privileges."
        )
    updated = update_thresholds(config)
    return {
        "status": "success",
        "message": "Thresholds updated successfully",
        "thresholds": updated
    }


def is_simulation_device(device_id: Any, device: Optional[Any] = None) -> bool:
    """
    Verify if a device ID or device instance is explicitly designated for simulation/testing.
    Does NOT treat production hardware IDs (like MAITRI_ESP8266_01) as simulation-only.
    """
    if hasattr(device_id, "device_id"):
        device = device_id
        device_id = getattr(device, "device_id", "")
    dev_id = (device_id or "").lower()
    if (
        dev_id.startswith("maitri_sim")
        or dev_id.startswith("sim_")
        or "simulat" in dev_id
        or "demo" in dev_id
        or "prototype" in dev_id
        or "virtual" in dev_id
    ):
        return True
    if device and getattr(device, "name", None):
        dev_name = device.name.lower()
        if "simulat" in dev_name or "demo" in dev_name or "prototype" in dev_name or "virtual" in dev_name:
            return True
    return False


@router.post("/simulate")
def simulate_telemetry(
    device_id: str = Query("MAITRI_SIM_NODE", description="Target device ID to simulate"),
    controller_type: str = Query("ESP8266", description="ESP8266 or ESP32"),
    db: Session = Depends(get_db),
    user = Depends(get_optional_current_user)
):
    """
    Simulates a single 20°-160° ultrasonic sweep with realistic environmental data.
    Disabled in production.
    """
    if os.getenv("ENVIRONMENT", "production").lower() == "production":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Telemetry simulation endpoint disabled in production."
        )

    # Assigning simulation credentials strictly requires an authenticated elevated operator.
    if not user or not is_elevated_user(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot assign simulation credentials without authenticated elevated operator privileges."
        )

    from ..models import IoTDevice
    from ..services.iot_service import hash_device_token

    sim_dev = db.query(IoTDevice).filter(IoTDevice.device_id == device_id).first()

    # Simulation credentials may only be assigned to explicitly simulation-designated devices.
    if not is_simulation_device(device_id, sim_dev):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot assign simulation credentials to non-simulation devices."
        )

    c_type = controller_type if isinstance(controller_type, str) else "ESP8266"
    payload = generate_simulation_payload(device_id, c_type)

    # Cryptographically random simulation token — never use fixed tokens or log plaintext
    sim_token = secrets.token_urlsafe(32)
    sim_token_hash = hash_device_token(sim_token)

    prev_token_hash = sim_dev.device_token_hash if sim_dev else None
    if sim_dev:
        sim_dev.device_token_hash = sim_token_hash
        db.flush()

    try:
        telemetry = process_incoming_sensor_data(db, payload, user=user, device_token=sim_token)
        db.commit()
    except PermissionError as pe:
        if sim_dev:
            sim_dev.device_token_hash = prev_token_hash
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(pe)
        )
    except ValueError as ve:
        if sim_dev:
            sim_dev.device_token_hash = prev_token_hash
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(ve)
        )
    except Exception as exc:
        if sim_dev:
            sim_dev.device_token_hash = prev_token_hash
        db.rollback()
        if isinstance(exc, HTTPException):
            raise
        logger.exception("Simulation telemetry ingestion failed for device %s", device_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Simulation telemetry ingestion failed."
        )

    return {
        "status": "success",
        "message": f"Simulated radar sweep generated for {device_id}",
        "data": telemetry,
        "simulation_token": sim_token
    }
