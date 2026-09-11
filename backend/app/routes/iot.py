from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional, List, Dict, Any

from ..database import get_db
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

router = APIRouter()


@router.post("/sensor-data", status_code=status.HTTP_200_OK)
@router.post("/telemetry", status_code=status.HTTP_200_OK)
@router.post("/data", status_code=status.HTTP_200_OK)
def post_sensor_data(
    data: IoTSensorDataCreate,
    db: Session = Depends(get_db)
):
    """
    Ingests live telemetry from ESP8266 or ESP32 hardware prototype.
    Accepts temperature, humidity, soil moisture, water_distance_cm, and servo-ultrasonic scan array.
    Automatically computes nearest object distance & alert status.
    """
    try:
        print(f"[IoT API] >>> INGESTED TELEMETRY: device_id={data.device_id}, temp={data.temperature}, water_dist={data.water_distance_cm}, scan_points={len(data.scan)} <<<", flush=True)
        telemetry = process_incoming_sensor_data(db, data)
        return {
            "success": True,
            "status": "success",
            "message": "Sensor data received successfully",
            "data": telemetry
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to process IoT sensor data: {str(e)}"
        )


@router.get("/latest", response_model=IoTLatestResponse)
def get_latest(
    device_id: Optional[str] = Query(None, description="Optional filter by device ID (e.g. MAITRI_ESP8266_01)"),
    db: Session = Depends(get_db)
):
    """
    Retrieves the most recent sensor reading and ultrasonic radar scan.
    Calculates live device online/offline status based on configurable timeout.
    """
    telemetry = get_latest_telemetry(db, device_id)
    return telemetry


@router.get("/devices", response_model=List[IoTDeviceSummary])
def get_devices(
    db: Session = Depends(get_db)
):
    """
    Lists all registered IoT hardware controllers (ESP8266, ESP32) with live status.
    """
    return list_registered_devices(db)


@router.get("/history")
def get_history(
    device_id: Optional[str] = Query(None, description="Filter history by device ID"),
    limit: int = Query(30, ge=5, le=100, description="Max points to return"),
    db: Session = Depends(get_db)
):
    """
    Retrieves chronological sensor history for temperature, humidity, and soil moisture charts.
    """
    return get_telemetry_history(db, device_id, limit)


@router.get("/config")
def get_config():
    """
    Returns the current configurable distance thresholds and device timeout settings,
    plus host LAN IPv4 endpoints so edge hardware can be pointed to the right URL.
    """
    lan_ips, recommended_url = get_host_lan_ips()
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
    """
    lan_ips, recommended_url = get_host_lan_ips()
    return {
        "status": "success",
        "lan_ips": lan_ips,
        "recommended_url": recommended_url
    }


@router.post("/config")
def set_config(config: IoTThresholdConfig):
    """
    Updates configurable distance thresholds (CLEAR, WARNING, CRITICAL) and timeout.
    """
    updated = update_thresholds(config)
    return {
        "status": "success",
        "message": "Thresholds updated successfully",
        "thresholds": updated
    }


@router.post("/simulate")
def simulate_telemetry(
    device_id: str = Query("MAITRI_ESP8266_01", description="Target device ID to simulate"),
    controller_type: str = Query("ESP8266", description="ESP8266 or ESP32"),
    db: Session = Depends(get_db)
):
    """
    Simulates a single 20°-160° ultrasonic sweep with realistic environmental data.
    Useful for college/hackathon demonstration when physical hardware is not connected.
    """
    payload = generate_simulation_payload(device_id, controller_type)
    telemetry = process_incoming_sensor_data(db, payload)
    return {
        "status": "success",
        "message": f"Simulated radar sweep generated for {device_id}",
        "data": telemetry
    }
