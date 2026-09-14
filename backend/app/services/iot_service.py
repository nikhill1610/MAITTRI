import os
import json
import math
import random
import socket
import hashlib
import hmac
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import desc

from ..models import IoTDevice, IoTSensorReading, Farm, utcnow
from ..schemas import (
    IoTSensorDataCreate,
    RadarScanPoint,
    NearestObject,
    IoTLatestResponse,
    IoTDeviceSummary,
    IoTThresholdConfig
)

# Configurable prototype thresholds
DEFAULT_THRESHOLDS = {
    "clear_distance": 100.0,      # > 100 cm: CLEAR
    "warning_distance": 50.0,    # 20 cm < dist <= 50 cm: WARNING (50 < dist <= 100: OBJECT DETECTED)
    "critical_distance": 20.0,   # <= 20 cm: VERY CLOSE
    "offline_timeout_seconds": 45  # Generous timeout for physical hardware sweeps (45s)
}

_current_thresholds: Dict[str, Any] = dict(DEFAULT_THRESHOLDS)

# High-speed in-memory telemetry cache
_latest_telemetry: Dict[str, Dict[str, Any]] = {}
_latest_overall: Optional[Dict[str, Any]] = None


def check_device_access(db: Session, device_id: str, user: Optional[Any] = None) -> None:
    """
    Enforces that user can only access devices they own, or devices linked to their farms.
    Operators and Admins can access all devices.
    Unclaimed devices (user_id is None) can be viewed by anyone for prototyping.
    """
    if not user or not device_id:
        return
    role = (getattr(user, "role", None) or "FARMER").upper()
    if role in ("AUTHORIZED_OPERATOR", "ADMIN"):
        return

    device = db.query(IoTDevice).filter(IoTDevice.device_id == device_id).first()
    if device and device.user_id and str(device.user_id) != str(user.id):
        # Check if linked to one of user's farms
        if device.farm_id:
            farm = db.query(Farm).filter(Farm.id == device.farm_id, Farm.user_id == user.id).first()
            if farm:
                return
        raise PermissionError(f"Access denied: Device '{device_id}' is registered to another user.")


def hash_device_token(token: str) -> str:
    """Computes deterministic SHA-256 digest of device preshared token."""
    return hashlib.sha256(token.strip().encode("utf-8")).hexdigest()


def process_incoming_sensor_data(
    db: Session,
    data: Any,
    user: Optional[Any] = None,
    device_token: Optional[str] = None
) -> Dict[str, Any]:
    """
    Processes incoming sensor telemetry from ESP8266 or ESP32:
    - Authenticates hardware device via preshared X-Device-Token
    - Validates / re-classifies scan points
    - Computes nearest object and overall alert status
    - Upserts device registration in DB (linking user_id if authenticated)
    - Stores historical reading in DB linked to device_table_id
    - Updates in-memory fast cache
    """
    if isinstance(data, dict):
        data = IoTSensorDataCreate(**data)

    if not data.device_id or len(data.device_id.strip()) < 3:
        raise ValueError("Invalid device_id. Minimum 3 characters required.")

    now = datetime.now(timezone.utc)
    env = os.getenv("ENVIRONMENT", "production").lower()

    # 1. Device authentication and status verification
    device = db.query(IoTDevice).filter(IoTDevice.device_id == data.device_id).first()
    if device:
        if not device.is_active:
            raise PermissionError(f"Access denied: Device '{data.device_id}' is revoked or deactivated.")

        if device.device_token_hash:
            if not device_token or not hmac.compare_digest(hash_device_token(device_token), device.device_token_hash):
                raise PermissionError(f"Access denied: Invalid or missing device token for '{data.device_id}'.")
        elif env == "production":
            if not device_token:
                raise PermissionError(f"Access denied: Device '{data.device_id}' requires an X-Device-Token in production.")
            device.device_token_hash = hash_device_token(device_token)
    else:
        if env == "production" and not device_token:
            raise PermissionError(f"Access denied: Unregistered device '{data.device_id}' requires an X-Device-Token in production.")

        token_hash = hash_device_token(device_token) if device_token else None
        device = IoTDevice(
            device_id=data.device_id,
            user_id=user.id if user else None,
            farm_id=getattr(data, "farm_id", None),
            controller_type=data.controller_type or "ESP32",
            name=f"MAITRI {data.controller_type or 'ESP'} Node",
            device_token_hash=token_hash,
            is_active=True,
            last_seen=now,
            created_at=now
        )
        db.add(device)
        db.flush()

    # Check ownership conflict: if device is owned by User A, User B cannot claim/push to it
    if device.user_id and user and str(device.user_id) != str(user.id):
        role = (getattr(user, "role", None) or "FARMER").upper()
        if role not in ("AUTHORIZED_OPERATOR", "ADMIN"):
            raise PermissionError(f"Device '{data.device_id}' is registered to another user.")

    if not device.user_id and user:
        device.user_id = user.id

    farm_id = getattr(data, "farm_id", None)
    if not device.farm_id and farm_id:
        device.farm_id = farm_id

    device.controller_type = data.controller_type or device.controller_type
    device.last_seen = now
    device.is_active = True
    db.flush()

    # 2. Normalize, sanitize and re-classify scan points with current thresholds
    processed_scan: List[Dict[str, Any]] = []
    for pt in data.scan:
        raw_dist = pt.distance
        # Safe cleanup: treat negative distance or > 450cm as no echo
        if raw_dist is not None and (raw_dist <= 0.0 or raw_dist > 450.0):
            clean_dist = None
        else:
            clean_dist = round(float(raw_dist), 1) if raw_dist is not None else None

        det, st = classify_distance(clean_dist)
        processed_scan.append({
            "angle": int(pt.angle),
            "distance": clean_dist,
            "object_detected": det,
            "status": st
        })

    # 3. Calculate nearest obstacle
    nearest_obj, overall_status = calculate_nearest_object(processed_scan)
    if not nearest_obj and data.water_distance_cm is not None and data.water_distance_cm > 0:
        det, st = classify_distance(data.water_distance_cm)
        nearest_obj = {
            "angle": 90,
            "distance": round(float(data.water_distance_cm), 1),
            "status": st
        }
        overall_status = st

    # 4. Save reading to DB with device_table_id foreign key
    reading = IoTSensorReading(
        device_table_id=device.id,
        device_id=data.device_id,
        controller_type=data.controller_type or "ESP32",
        timestamp=now,
        temperature=round(float(data.temperature), 1) if data.temperature is not None else None,
        humidity=round(float(data.humidity), 1) if data.humidity is not None else None,
        soil_moisture=round(float(data.soil_moisture), 1) if data.soil_moisture is not None else None,
        water_distance_cm=round(float(data.water_distance_cm), 1) if data.water_distance_cm is not None else None,
        scan_json=json.dumps(processed_scan),
        nearest_distance=nearest_obj["distance"] if nearest_obj else None,
        nearest_angle=nearest_obj["angle"] if nearest_obj else None,
        object_status=overall_status,
        created_at=now
    )
    db.add(reading)
    db.commit()
    db.refresh(reading)

    lan_list, rec_url = get_host_lan_ips()

    # 5. Build telemetry payload
    telemetry = {
        "status": "ONLINE",
        "device_id": data.device_id,
        "controller_type": data.controller_type or "ESP32",
        "is_online": True,
        "temperature": reading.temperature,
        "humidity": reading.humidity,
        "soil_moisture": reading.soil_moisture,
        "water_distance_cm": reading.water_distance_cm,
        "scan": processed_scan,
        "nearest_object": nearest_obj,
        "object_status": overall_status,
        "timestamp": now.isoformat(),
        "last_seen": now.strftime("%H:%M:%S UTC"),
        "time_diff_seconds": 0.0,
        "thresholds": get_current_thresholds(),
        "lan_ips": lan_list,
        "recommended_url": rec_url
    }

    # 6. Update in-memory cache
    global _latest_overall
    _latest_telemetry[data.device_id] = telemetry
    _latest_overall = telemetry

    return telemetry


def get_host_lan_ips(port: int = 8000) -> Tuple[List[Dict[str, Any]], str]:
    """
    Returns list of host LAN IPv4 endpoints and recommended URL for ESP32/ESP8266.
    In cloud/production deployment, checks for PUBLIC_API_URL or IOT_SERVER_URL.
    """
    endpoints: List[Dict[str, Any]] = []
    recommended = f"http://192.168.137.1:{port}/api/iot/sensor-data"

    # Prioritize public production cloud endpoint if configured
    public_url = os.getenv("IOT_SERVER_URL") or os.getenv("PUBLIC_API_URL")
    if public_url:
        p_clean = public_url.rstrip("/")
        if not p_clean.endswith("/api/iot/sensor-data"):
            if p_clean.endswith("/api"):
                public_endpoint = f"{p_clean}/iot/sensor-data"
            else:
                public_endpoint = f"{p_clean}/api/iot/sensor-data"
        else:
            public_endpoint = p_clean

        endpoints.append({
            "ip": "Cloud Server",
            "label": "Production Cloud Backend (Field Stations)",
            "url": public_endpoint,
            "is_hotspot": False,
            "is_cloud": True
        })
        recommended = public_endpoint

    try:
        hostname = socket.gethostname()
        _, _, ips = socket.gethostbyname_ex(hostname)
        for ip in ips:
            if ip.startswith("127."):
                continue
            is_hotspot = ip.startswith("192.168.137.")
            label = "Windows Hotspot (Local Lab)" if is_hotspot else ("Local Wi-Fi Network" if ip.startswith("192.168.") or ip.startswith("10.") else "LAN Interface")
            url = f"http://{ip}:{port}/api/iot/sensor-data"
            item = {"ip": ip, "label": label, "url": url, "is_hotspot": is_hotspot}
            endpoints.append(item)
            if is_hotspot and not public_url:
                recommended = url
    except Exception:
        pass

    if not endpoints:
        endpoints.append({"ip": "192.168.137.1", "label": "Windows Hotspot", "url": f"http://192.168.137.1:{port}/api/iot/sensor-data", "is_hotspot": True})
        if not public_url:
            recommended = f"http://192.168.137.1:{port}/api/iot/sensor-data"

    return endpoints, recommended


def get_current_thresholds() -> Dict[str, Any]:
    return dict(_current_thresholds)


def update_thresholds(config: IoTThresholdConfig) -> Dict[str, Any]:
    global _current_thresholds
    _current_thresholds["clear_distance"] = config.clear_distance
    _current_thresholds["warning_distance"] = config.warning_distance
    _current_thresholds["critical_distance"] = config.critical_distance
    _current_thresholds["offline_timeout_seconds"] = config.offline_timeout_seconds
    return dict(_current_thresholds)


def classify_distance(distance: Optional[float]) -> Tuple[bool, str]:
    """
    Classifies an ultrasonic distance measurement against prototype thresholds:
    - distance > 100 cm -> CLEAR
    - 50 cm < distance <= 100 cm -> OBJECT DETECTED
    - 20 cm < distance <= 50 cm -> WARNING
    - distance <= 20 cm -> VERY CLOSE
    - No echo / None / <= 0 -> NO READING
    """
    if distance is None or distance <= 0.0 or distance > 400.0:
        return False, "NO READING"

    clear_th = _current_thresholds["clear_distance"]
    warn_th = _current_thresholds["warning_distance"]
    crit_th = _current_thresholds["critical_distance"]

    if distance > clear_th:
        return False, "CLEAR"
    elif distance > warn_th:
        return True, "OBJECT DETECTED"
    elif distance > crit_th:
        return True, "WARNING"
    else:
        return True, "VERY CLOSE"


def calculate_nearest_object(scan_points: List[Any]) -> Tuple[Optional[Dict[str, Any]], str]:
    """
    Finds the closest detected obstacle in the ultrasonic radar scan.
    Returns (nearest_object_dict, overall_scan_status).
    """
    closest_dist = float("inf")
    closest_point = None
    has_warning = False
    has_critical = False
    has_detected = False

    for pt in scan_points:
        # Support both Pydantic model and dict
        if isinstance(pt, dict):
            angle = pt.get("angle", 90)
            distance = pt.get("distance")
            status = pt.get("status", "CLEAR")
            detected = pt.get("object_detected", False)
        else:
            angle = pt.angle
            distance = pt.distance
            status = pt.status
            detected = pt.object_detected

        if distance is not None and distance > 0.0 and distance <= _current_thresholds["clear_distance"]:
            detected = True
            if distance < closest_dist:
                closest_dist = distance
                closest_point = {
                    "angle": int(angle),
                    "distance": round(float(distance), 1),
                    "status": status if status != "CLEAR" else classify_distance(distance)[1]
                }

        if status == "VERY CLOSE":
            has_critical = True
        elif status == "WARNING":
            has_warning = True
        elif status == "OBJECT DETECTED" or detected:
            has_detected = True

    overall_status = "CLEAR"
    if has_critical:
        overall_status = "VERY CLOSE"
    elif has_warning:
        overall_status = "WARNING"
    elif has_detected:
        overall_status = "OBJECT DETECTED"
    elif not scan_points:
        overall_status = "NO READING"

    return closest_point, overall_status


def get_default_demo_telemetry(device_id: str = "MAITRI_ESP32_01", controller_type: str = "ESP32") -> Dict[str, Any]:
    """
    Returns default calibrated prototype telemetry so the dashboard looks realistic
    and populated even before the physical hardware is plugged in.
    """
    now = datetime.now(timezone.utc)
    # Default 20° to 160° scan with a simulated crop obstacle around 70° at 34.2 cm
    angles = list(range(20, 161, 10))
    sample_scan = []
    for a in angles:
        if a in (60, 70, 80):
            # Target obstacle at ~34.2 cm
            d = 34.2 if a == 70 else (42.0 if a == 80 else 48.5)
            det, st = classify_distance(d)
        elif a in (40, 50):
            d = 63.0 if a == 50 else 70.0
            det, st = classify_distance(d)
        elif a == 90:
            d = 32.0
            det, st = classify_distance(d)
        else:
            d = round(110.0 + (a % 30), 1)
            det, st = classify_distance(d)

        sample_scan.append({
            "angle": a,
            "distance": d,
            "object_detected": det,
            "status": st
        })

    nearest_obj, overall_status = calculate_nearest_object(sample_scan)
    lan_list, rec_url = get_host_lan_ips()
    return {
        "device_id": device_id,
        "controller_type": controller_type,
        "status": "OFFLINE",
        "is_online": False,
        "temperature": 28.6,
        "humidity": 67.2,
        "soil_moisture": 45.0,
        "water_distance_cm": 32.0,
        "scan": sample_scan,
        "nearest_object": nearest_obj or {"angle": 70, "distance": 34.2, "status": "WARNING"},
        "object_status": "WARNING",
        "timestamp": now.isoformat(),
        "last_seen": now.strftime("%H:%M:%S UTC"),
        "time_diff_seconds": 999.0,
        "thresholds": get_current_thresholds(),
        "lan_ips": lan_list,
        "recommended_url": rec_url
    }




def get_latest_telemetry(db: Session, device_id: Optional[str] = None, user: Optional[Any] = None) -> Dict[str, Any]:
    """
    Returns the latest sensor reading and live status for the requested device
    (or any active device if none specified). Enforces ownership isolation.
    """
    if device_id:
        check_device_access(db, device_id, user)

    now = datetime.now(timezone.utc)
    timeout_sec = _current_thresholds["offline_timeout_seconds"]
    lan_list, rec_url = get_host_lan_ips()

    # Try in-memory cache first
    target_telemetry = None
    if device_id and device_id in _latest_telemetry:
        target_telemetry = _latest_telemetry[device_id]
    elif not device_id and _latest_overall:
        target_telemetry = _latest_overall

    if target_telemetry:
        # Check online / offline based on timestamp
        try:
            reading_time = datetime.fromisoformat(target_telemetry["timestamp"])
            diff_sec = max(0.0, (now - reading_time).total_seconds())
        except Exception:
            diff_sec = 0.0

        is_online = diff_sec <= timeout_sec
        target_telemetry["time_diff_seconds"] = round(diff_sec, 1)
        target_telemetry["is_online"] = is_online
        target_telemetry["status"] = "ONLINE" if is_online else "OFFLINE"
        target_telemetry["thresholds"] = get_current_thresholds()
        target_telemetry["lan_ips"] = lan_list
        target_telemetry["recommended_url"] = rec_url
        return target_telemetry

    # If not in cache, query DB
    query = db.query(IoTSensorReading)
    if device_id:
        query = query.filter(IoTSensorReading.device_id == device_id)
    last_reading = query.order_by(desc(IoTSensorReading.timestamp)).first()

    if last_reading:
        try:
            scan_points = json.loads(last_reading.scan_json or "[]")
        except Exception:
            scan_points = []

        nearest_obj = None
        if last_reading.nearest_distance is not None and last_reading.nearest_angle is not None:
            nearest_obj = {
                "angle": last_reading.nearest_angle,
                "distance": last_reading.nearest_distance,
                "status": last_reading.object_status or "CLEAR"
            }

        if last_reading.timestamp.tzinfo is None:
            ts_aware = last_reading.timestamp.replace(tzinfo=timezone.utc)
        else:
            ts_aware = last_reading.timestamp
        diff_sec = max(0.0, (now - ts_aware).total_seconds())
        is_online = diff_sec <= timeout_sec

        result = {
            "device_id": last_reading.device_id,
            "controller_type": last_reading.controller_type or "ESP8266",
            "status": "ONLINE" if is_online else "OFFLINE",
            "is_online": is_online,
            "temperature": last_reading.temperature,
            "humidity": last_reading.humidity,
            "soil_moisture": last_reading.soil_moisture,
            "water_distance_cm": getattr(last_reading, "water_distance_cm", None),
            "scan": scan_points,
            "nearest_object": nearest_obj,
            "object_status": last_reading.object_status or "CLEAR",
            "timestamp": last_reading.timestamp.isoformat(),
            "last_seen": last_reading.timestamp.strftime("%H:%M:%S UTC"),
            "time_diff_seconds": round(diff_sec, 1),
            "thresholds": get_current_thresholds(),
            "lan_ips": lan_list,
            "recommended_url": rec_url
        }
        return result

    # Fallback to demo default prototype so frontend renders cleanly
    return get_default_demo_telemetry(
        device_id=device_id or "MAITRI_ESP32_01",
        controller_type="ESP32" if not device_id or "32" in device_id else "ESP8266"
    )


def list_registered_devices(db: Session, user: Optional[Any] = None) -> List[Dict[str, Any]]:
    """
    Returns list of all known IoT devices with online/offline status.
    If authenticated as farmer, filters to devices owned by farmer or farmer's farms.
    """
    now = datetime.now(timezone.utc)
    timeout_sec = _current_thresholds["offline_timeout_seconds"]

    query = db.query(IoTDevice)
    if user:
        role = (getattr(user, "role", None) or "FARMER").upper()
        if role not in ("AUTHORIZED_OPERATOR", "ADMIN"):
            user_farm_ids = [f.id for f in db.query(Farm).filter(Farm.user_id == user.id).all()]
            query = query.filter(
                (IoTDevice.user_id == user.id) |
                (IoTDevice.farm_id.in_(user_farm_ids)) |
                (IoTDevice.user_id.is_(None))
            )

    devices = query.order_by(desc(IoTDevice.last_seen)).all()
    results = []

    # If no devices in DB, provide standard defaults
    if not devices:
        return [
            {
                "device_id": "MAITRI_ESP32_01",
                "controller_type": "ESP32",
                "name": "MAITRI ESP32 Node",
                "status": "OFFLINE",
                "is_online": False,
                "last_seen": "Never",
                "time_diff_seconds": 999.0,
                "latest_temperature": None,
                "latest_humidity": None,
                "latest_soil_moisture": None
            }
        ]

    for d in devices:
        if d.last_seen.tzinfo is None:
            last_seen_aware = d.last_seen.replace(tzinfo=timezone.utc)
        else:
            last_seen_aware = d.last_seen
        diff_sec = max(0.0, (now - last_seen_aware).total_seconds())
        is_online = diff_sec <= timeout_sec

        # Fetch latest reading values
        latest_r = db.query(IoTSensorReading).filter(IoTSensorReading.device_id == d.device_id).order_by(desc(IoTSensorReading.timestamp)).first()

        results.append({
            "device_id": d.device_id,
            "controller_type": d.controller_type or "ESP8266",
            "name": d.name or f"MAITRI {d.controller_type} Node",
            "status": "ONLINE" if is_online else "OFFLINE",
            "is_online": is_online,
            "last_seen": d.last_seen.strftime("%H:%M:%S UTC"),
            "time_diff_seconds": round(diff_sec, 1),
            "latest_temperature": latest_r.temperature if latest_r else None,
            "latest_humidity": latest_r.humidity if latest_r else None,
            "latest_soil_moisture": latest_r.soil_moisture if latest_r else None
        })

    return results


def get_telemetry_history(db: Session, device_id: Optional[str] = None, limit: int = 40, user: Optional[Any] = None) -> List[Dict[str, Any]]:
    """
    Returns recent historical readings for telemetry graphs. Enforces ownership isolation.
    """
    if device_id:
        check_device_access(db, device_id, user)

    query = db.query(IoTSensorReading)
    if device_id:
        query = query.filter(IoTSensorReading.device_id == device_id)
    elif user:
        role = (getattr(user, "role", None) or "FARMER").upper()
        if role not in ("AUTHORIZED_OPERATOR", "ADMIN"):
            user_farm_ids = [f.id for f in db.query(Farm).filter(Farm.user_id == user.id).all()]
            owned_device_ids = [d.device_id for d in db.query(IoTDevice).filter(
                (IoTDevice.user_id == user.id) | (IoTDevice.farm_id.in_(user_farm_ids)) | (IoTDevice.user_id.is_(None))
            ).all()]
            query = query.filter(IoTSensorReading.device_id.in_(owned_device_ids))

    readings = query.order_by(desc(IoTSensorReading.timestamp)).limit(limit).all()

    results = []
    for r in reversed(readings):
        results.append({
            "id": r.id,
            "device_id": r.device_id,
            "controller_type": r.controller_type,
            "timestamp": r.timestamp.isoformat(),
            "time": r.timestamp.strftime("%H:%M:%S"),
            "temperature": r.temperature,
            "humidity": r.humidity,
            "soil_moisture": r.soil_moisture,
            "water_distance_cm": getattr(r, "water_distance_cm", None),
            "nearest_distance": r.nearest_distance,
            "nearest_angle": r.nearest_angle,
            "object_status": r.object_status
        })

    return results


def generate_simulation_payload(device_id: str = "MAITRI_ESP8266_01", controller_type: str = "ESP8266") -> IoTSensorDataCreate:
    """
    Generates a dynamic radar sweep and sensor readings for live demo testing.
    """
    # Simulate an obstacle oscillating around 60° to 100° at distance 25 to 45 cm
    t = datetime.now().timestamp()
    obstacle_angle = int(60 + 40 * (0.5 + 0.5 * math.sin(t / 4.0)))
    obstacle_dist = round(32.0 + 15.0 * (0.5 + 0.5 * math.cos(t / 3.0)), 1)

    angles = list(range(20, 161, 10))
    scan = []
    for a in angles:
        # Distance calculation with falloff around obstacle
        angle_diff = abs(a - obstacle_angle)
        if angle_diff <= 15:
            d = round(obstacle_dist + angle_diff * 2.5, 1)
        elif a in (30, 40) and random.random() > 0.6:
            d = round(75.0 + random.uniform(-5, 10), 1)
        else:
            d = round(120.0 + random.uniform(5, 40), 1)

        det, st = classify_distance(d)
        scan.append(RadarScanPoint(
            angle=a,
            distance=d,
            object_detected=det,
            status=st
        ))

    temp = round(28.2 + 1.2 * math.sin(t / 10.0), 1)
    hum = round(66.5 + 2.0 * math.cos(t / 12.0), 1)
    soil = round(44.0 + 3.0 * math.sin(t / 15.0), 1)

    return IoTSensorDataCreate(
        device_id=device_id,
        controller_type=controller_type,
        temperature=temp,
        humidity=hum,
        soil_moisture=soil,
        scan=scan
    )
