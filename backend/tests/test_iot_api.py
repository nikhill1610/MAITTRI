import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app, headers={"X-Device-Token": "test-iot-preshared-token-12345"})


def test_get_iot_latest_default():
    """Verify GET /api/iot/latest returns 200 and standard telemetry structure."""
    response = client.get("/api/iot/latest")
    assert response.status_code == 200
    data = response.json()
    assert "device_id" in data
    assert "controller_type" in data
    assert "temperature" in data
    assert "humidity" in data
    assert "soil_moisture" in data
    assert "scan" in data
    assert "status" in data
    assert "is_online" in data
    assert isinstance(data["scan"], list)


def test_post_sensor_data_esp8266():
    """Verify POST /api/iot/sensor-data works with ESP8266 payload."""
    payload = {
        "device_id": "MAITRI_ESP8266_TEST",
        "controller_type": "ESP8266",
        "temperature": 29.4,
        "humidity": 65.0,
        "soil_moisture": 48.0,
        "scan": [
            {"angle": 20, "distance": 120.0, "object_detected": False, "status": "CLEAR"},
            {"angle": 30, "distance": 85.0, "object_detected": True, "status": "OBJECT DETECTED"},
            {"angle": 40, "distance": 42.5, "object_detected": True, "status": "WARNING"},
            {"angle": 50, "distance": 18.0, "object_detected": True, "status": "VERY CLOSE"},
            {"angle": 60, "distance": None, "object_detected": False, "status": "NO READING"}
        ]
    }
    response = client.post("/api/iot/sensor-data", json=payload)
    assert response.status_code == 200
    res_data = response.json()
    assert res_data["success"] is True
    assert res_data["status"] == "success"
    telemetry = res_data["data"]
    assert telemetry["device_id"] == "MAITRI_ESP8266_TEST"
    assert telemetry["controller_type"] == "ESP8266"
    assert telemetry["temperature"] == 29.4
    assert telemetry["humidity"] == 65.0
    assert telemetry["soil_moisture"] == 48.0
    assert telemetry["is_online"] is True
    assert telemetry["status"] == "ONLINE"

    # Nearest object should be 18.0 cm at 50 degrees (VERY CLOSE)
    assert telemetry["nearest_object"] is not None
    assert telemetry["nearest_object"]["angle"] == 50
    assert telemetry["nearest_object"]["distance"] == 18.0
    assert telemetry["nearest_object"]["status"] == "VERY CLOSE"
    assert telemetry["object_status"] == "VERY CLOSE"


def test_post_sensor_data_esp32_abstraction():
    """Verify ESP32 sends the exact same payload schema and is accepted transparently."""
    payload = {
        "device_id": "MAITRI_ESP32_FIELD_NODE",
        "controller_type": "ESP32",
        "temperature": 31.2,
        "humidity": 58.5,
        "soil_moisture": 38.0,
        "scan": [
            {"angle": 70, "distance": 34.2, "object_detected": True, "status": "WARNING"},
            {"angle": 80, "distance": 62.0, "object_detected": True, "status": "OBJECT DETECTED"}
        ]
    }
    response = client.post("/api/iot/sensor-data", json=payload)
    assert response.status_code == 200
    telemetry = response.json()["data"]
    assert telemetry["controller_type"] == "ESP32"
    assert telemetry["nearest_object"]["angle"] == 70
    assert telemetry["nearest_object"]["distance"] == 34.2
    assert telemetry["nearest_object"]["status"] == "WARNING"


def test_post_sensor_data_exact_user_esp32_payload():
    """Verify POST /api/iot/sensor-data accepts the exact JSON from the user's ESP32."""
    payload = {
        "temperature": 28.50,
        "humidity": 62.30,
        "soil_moisture": 45,
        "water_distance_cm": 18.50,
        "device": "ESP32"
    }
    response = client.post("/api/iot/sensor-data", json=payload)
    assert response.status_code == 200
    res_data = response.json()
    assert res_data["success"] is True
    assert res_data["message"] == "Sensor data received successfully"
    telemetry = res_data["data"]
    assert telemetry["temperature"] == 28.5
    assert telemetry["humidity"] == 62.3
    assert telemetry["soil_moisture"] == 45.0
    assert telemetry["water_distance_cm"] == 18.5
    assert telemetry["device_id"] == "MAITRI_ESP32_01"
    assert telemetry["nearest_object"]["distance"] == 18.5
    assert telemetry["nearest_object"]["status"] == "VERY CLOSE"
    assert telemetry["is_online"] is True


def test_validation_errors():
    """Verify Pydantic validation rejects out-of-range or malformed inputs."""
    # Invalid angle > 180
    res_angle = client.post("/api/iot/sensor-data", json={
        "device_id": "TEST",
        "scan": [{"angle": 210, "distance": 50.0, "object_detected": True, "status": "WARNING"}]
    })
    assert res_angle.status_code == 422

    # Invalid negative angle
    res_neg_angle = client.post("/api/iot/sensor-data", json={
        "device_id": "TEST",
        "scan": [{"angle": -10, "distance": 50.0, "object_detected": True, "status": "WARNING"}]
    })
    assert res_neg_angle.status_code == 422

    # Invalid distance > 450
    res_dist = client.post("/api/iot/sensor-data", json={
        "device_id": "TEST",
        "scan": [{"angle": 90, "distance": 999.0, "object_detected": False, "status": "CLEAR"}]
    })
    assert res_dist.status_code == 422

    # Empty device_id
    res_empty_id = client.post("/api/iot/sensor-data", json={
        "device_id": "",
        "scan": []
    })
    assert res_empty_id.status_code == 422


def test_nearest_object_none_when_clear():
    """Verify that when all scan points are > 100cm (CLEAR), nearest_object is None."""
    payload = {
        "device_id": "MAITRI_CLEAR_TEST",
        "controller_type": "ESP8266",
        "temperature": 27.0,
        "humidity": 60.0,
        "soil_moisture": 50.0,
        "scan": [
            {"angle": 40, "distance": 150.0, "object_detected": False, "status": "CLEAR"},
            {"angle": 90, "distance": 180.0, "object_detected": False, "status": "CLEAR"},
            {"angle": 140, "distance": 220.0, "object_detected": False, "status": "CLEAR"}
        ]
    }
    response = client.post("/api/iot/sensor-data", json=payload)
    assert response.status_code == 200
    telemetry = response.json()["data"]
    assert telemetry["nearest_object"] is None
    assert telemetry["object_status"] == "CLEAR"


def test_device_list():
    """Verify GET /api/iot/devices returns registered hardware nodes."""
    response = client.get("/api/iot/devices")
    assert response.status_code == 200
    devices = response.json()
    assert isinstance(devices, list)
    assert len(devices) >= 1
    dev_ids = [d["device_id"] for d in devices]
    assert "MAITRI_ESP8266_TEST" in dev_ids


def test_telemetry_history():
    """Verify GET /api/iot/history returns recorded time-series points."""
    response = client.get("/api/iot/history?device_id=MAITRI_ESP8266_TEST&limit=10")
    assert response.status_code == 200
    history = response.json()
    assert isinstance(history, list)
    assert len(history) >= 1


def test_config_endpoints():
    """Verify GET and POST /api/iot/config for dynamic thresholds."""
    get_res = client.get("/api/iot/config")
    assert get_res.status_code == 200
    th = get_res.json()["thresholds"]
    assert "clear_distance" in th
    assert "warning_distance" in th
    assert "critical_distance" in th

    post_res = client.post("/api/iot/config", json={
        "clear_distance": 110.0,
        "warning_distance": 55.0,
        "critical_distance": 25.0,
        "offline_timeout_seconds": 25
    })
    assert post_res.status_code == 200
    assert post_res.json()["thresholds"]["clear_distance"] == 110.0


def test_simulate_endpoint():
    """Verify POST /api/iot/simulate returns complete synthetic radar sweep."""
    with patch.dict("os.environ", {"ENVIRONMENT": "development"}):
        response = client.post("/api/iot/simulate?device_id=MAITRI_SIM_NODE&controller_type=ESP32")
        assert response.status_code == 200
        res_data = response.json()
        assert res_data["status"] == "success"
        telemetry = res_data["data"]
        assert telemetry["device_id"] == "MAITRI_SIM_NODE"
        assert telemetry["controller_type"] == "ESP32"
        assert len(telemetry["scan"]) == 15  # 20° to 160° in steps of 10°
        assert telemetry["is_online"] is True
