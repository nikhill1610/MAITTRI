import copy
import math
import os
import time
import pytest
from unittest.mock import MagicMock, patch
from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.deps import AuthenticatedUser
from app.models import IoTDevice, Farmer, FarmerDocument
from app.services.iot_service import hash_device_token


# =====================================================================
# Finding 1: Weather Cache Deepcopy
# =====================================================================

class TestWeatherCacheDeepcopy:
    def test_fresh_cache_hit_returns_deepcopy(self):
        from app.routes.weather import _WEATHER_CACHE, _WEATHER_CACHE_LOCK, fetch_weather_data

        cache_key = (28.614, 77.209, 7)
        original_payload = {
            "location": {"latitude": 28.614, "longitude": 77.209, "name": "Delhi"},
            "current": {"temperature_2m": 30.5, "relative_humidity_2m": 60},
            "daily": [{"date": "2026-10-03", "temp_max": 35.0, "temp_min": 24.0}],
            "hourly": {"time": ["2026-10-03T00:00"], "temperature_2m": [25.0]},
            "advisories": {
                "spraying": {"status": "favorable", "reason": "Low wind"},
                "irrigation": {"status": "skip", "reason": "Rain expected"}
            },
            "is_fallback": False
        }

        with _WEATHER_CACHE_LOCK:
            _WEATHER_CACHE[cache_key] = (time.time(), copy.deepcopy(original_payload))

        result = fetch_weather_data(28.614, 77.209, "Delhi", 7)
        assert result["cached"] is True
        assert result["current"]["temperature_2m"] == 30.5

        # Mutate the returned result deeply
        result["current"]["temperature_2m"] = -999.0
        result["daily"][0]["temp_max"] = -999.0
        result["hourly"]["temperature_2m"][0] = -999.0
        result["advisories"]["spraying"]["status"] = "MUTATED"

        # Verify cache remains unmutated
        with _WEATHER_CACHE_LOCK:
            cached_data = _WEATHER_CACHE[cache_key][1]
            assert cached_data["current"]["temperature_2m"] == 30.5
            assert cached_data["daily"][0]["temp_max"] == 35.0
            assert cached_data["hourly"]["temperature_2m"][0] == 25.0
            assert cached_data["advisories"]["spraying"]["status"] == "favorable"

    def test_stale_cache_fallback_returns_deepcopy(self):
        from app.routes.weather import _WEATHER_CACHE, _WEATHER_CACHE_LOCK, fetch_weather_data

        cache_key = (25.123, 85.456, 5)
        original_payload = {
            "location": {"latitude": 25.123, "longitude": 85.456, "name": "Patna"},
            "current": {"temperature_2m": 28.0},
            "daily": [{"date": "2026-10-03", "temp_max": 32.0}],
            "hourly": {"temperature_2m": [26.0]},
            "advisories": {"spraying": {"status": "caution"}},
            "is_fallback": False
        }

        # Expired cache entry (older than 900s, but <= 6h)
        stale_time = time.time() - 1200
        with _WEATHER_CACHE_LOCK:
            _WEATHER_CACHE[cache_key] = (stale_time, copy.deepcopy(original_payload))

        with patch("requests.get", side_effect=Exception("Open-Meteo down")):
            result = fetch_weather_data(25.123, 85.456, "Patna", 5)

        assert result.get("is_stale") is True
        assert result["current"]["temperature_2m"] == 28.0

        # Mutate result
        result["current"]["temperature_2m"] = 888.0
        result["daily"][0]["temp_max"] = 888.0
        result["advisories"]["spraying"]["status"] = "CORRUPTED"

        # Verify cache is intact
        with _WEATHER_CACHE_LOCK:
            cached_data = _WEATHER_CACHE[cache_key][1]
            assert cached_data["current"]["temperature_2m"] == 28.0
            assert cached_data["daily"][0]["temp_max"] == 32.0
            assert cached_data["advisories"]["spraying"]["status"] == "caution"


# =====================================================================
# Finding 2: Documents Storage Path for Unlinked Farmers
# =====================================================================

class TestDocumentsStoragePath:
    @pytest.mark.anyio
    async def test_unlinked_farmer_uses_farmer_id_prefix_not_operator_id(self):
        from app.routes.documents import upload_document
        from starlette.datastructures import UploadFile
        import io

        mock_db = MagicMock(spec=Session)

        # Farmer with NULL user_id
        unlinked_farmer = Farmer(
            id=42,
            user_id=None,
            name="Ramesh Unlinked",
            maittri_farmer_id="MAITRI-F-4242"
        )
        mock_db.query.return_value.filter.return_value.first.return_value = unlinked_farmer

        operator_user = AuthenticatedUser(id="op-999-uuid", email="operator@maittri.org", role="AUTHORIZED_OPERATOR")

        fake_file = UploadFile(
            filename="soil_report.pdf",
            file=io.BytesIO(b"%PDF-1.4 sample pdf content")
        )

        mock_sb_client = MagicMock()
        mock_sb_client.storage.from_.return_value.upload.return_value = {"Key": "uploaded"}

        with patch("app.routes.documents.get_supabase_admin_client", return_value=mock_sb_client):
            doc = await upload_document(
                farmer_id=42,
                document_name="Soil Report",
                category="Land Record",
                farm_id=None,
                file=fake_file,
                current_user=operator_user,
                db=mock_db
            )

        # Storage path must begin with farmer-42/ and NOT op-999-uuid/
        storage_path = doc["storage_path"]
        assert storage_path.startswith("farmer-42/"), f"Expected farmer-42 prefix, got {storage_path}"
        assert "op-999-uuid" not in storage_path

    @pytest.mark.anyio
    async def test_linked_farmer_uses_farmer_user_id_prefix(self):
        from app.routes.documents import upload_document
        from starlette.datastructures import UploadFile
        import io

        mock_db = MagicMock(spec=Session)

        # Farmer with linked user_id
        linked_farmer = Farmer(
            id=55,
            user_id="farmer-auth-uuid-777",
            name="Suresh Linked",
            maittri_farmer_id="MAITRI-F-5555"
        )
        mock_db.query.return_value.filter.return_value.first.return_value = linked_farmer

        operator_user = AuthenticatedUser(id="op-999-uuid", email="operator@maittri.org", role="AUTHORIZED_OPERATOR")

        fake_file = UploadFile(
            filename="khasra.pdf",
            file=io.BytesIO(b"%PDF-1.4 sample pdf content")
        )

        mock_sb_client = MagicMock()
        mock_sb_client.storage.from_.return_value.upload.return_value = {"Key": "uploaded"}

        with patch("app.routes.documents.get_supabase_admin_client", return_value=mock_sb_client):
            doc = await upload_document(
                farmer_id=55,
                document_name="Khasra",
                category="Land Record",
                farm_id=None,
                file=fake_file,
                current_user=operator_user,
                db=mock_db
            )

        storage_path = doc["storage_path"]
        assert storage_path.startswith("farmer-auth-uuid-777/"), f"Expected farmer-auth-uuid-777 prefix, got {storage_path}"
        assert "op-999-uuid" not in storage_path


# =====================================================================
# Finding 3: IoT Simulation Token Security
# =====================================================================

class TestIoTSimulationSecurity:
    def test_anonymous_simulation_rejected(self):
        from app.routes.iot import simulate_telemetry
        mock_db = MagicMock(spec=Session)
        sim_dev = IoTDevice(device_id="MAITRI_SIM_01", name="Simulation Node")
        mock_db.query.return_value.filter.return_value.first.return_value = sim_dev

        with patch.dict(os.environ, {"ENVIRONMENT": "development"}):
            with pytest.raises(HTTPException) as exc:
                simulate_telemetry(device_id="MAITRI_SIM_01", db=mock_db, user=None)
            assert exc.value.status_code == 403
            assert "elevated operator privileges" in exc.value.detail

    def test_farmer_simulation_rejected(self):
        from app.routes.iot import simulate_telemetry
        mock_db = MagicMock(spec=Session)
        farmer_user = AuthenticatedUser(id="f-1", email="farmer@test.org", role="FARMER")

        with patch.dict(os.environ, {"ENVIRONMENT": "development"}):
            with pytest.raises(HTTPException) as exc:
                simulate_telemetry(device_id="MAITRI_SIM_01", db=mock_db, user=farmer_user)
            assert exc.value.status_code == 403
            assert "elevated operator privileges" in exc.value.detail

    def test_production_environment_blocks_simulation(self):
        from app.routes.iot import simulate_telemetry
        mock_db = MagicMock(spec=Session)
        op_user = AuthenticatedUser(id="op-1", email="op@maittri.org", role="AUTHORIZED_OPERATOR")

        with patch.dict(os.environ, {"ENVIRONMENT": "production"}):
            with pytest.raises(HTTPException) as exc:
                simulate_telemetry(device_id="MAITRI_SIM_01", db=mock_db, user=op_user)
            assert exc.value.status_code == 403
            assert "disabled in production" in exc.value.detail

    def test_simulation_on_non_simulation_device_rejected(self):
        from app.routes.iot import simulate_telemetry
        mock_db = MagicMock(spec=Session)
        real_dev = IoTDevice(device_id="FIELD_NODE_REAL_42", name="Field Hardware Sensor", device_token_hash=None)
        mock_db.query.return_value.filter.return_value.first.return_value = real_dev
        op_user = AuthenticatedUser(id="op-1", email="op@maittri.org", role="AUTHORIZED_OPERATOR")

        with patch.dict(os.environ, {"ENVIRONMENT": "development"}):
            with pytest.raises(HTTPException) as exc:
                simulate_telemetry(device_id="FIELD_NODE_REAL_42", db=mock_db, user=op_user)
            assert exc.value.status_code == 403
            assert "non-simulation devices" in exc.value.detail

    def test_operator_simulation_generates_cryptographic_random_token_and_stores_hash(self):
        from app.routes.iot import simulate_telemetry
        mock_db = MagicMock(spec=Session)
        sim_dev = IoTDevice(device_id="MAITRI_SIM_NODE_99", name="Virtual Sensor", device_token_hash=None)
        mock_db.query.return_value.filter.return_value.first.return_value = sim_dev
        op_user = AuthenticatedUser(id="op-1", email="op@maittri.org", role="AUTHORIZED_OPERATOR")

        captured_token = None
        def mock_process_incoming(db, payload, user=None, device_token=None):
            nonlocal captured_token
            captured_token = device_token
            return {"status": "telemetry_processed", "device_id": payload.device_id}

        with patch.dict(os.environ, {"ENVIRONMENT": "development"}), \
             patch("app.routes.iot.process_incoming_sensor_data", side_effect=mock_process_incoming):
            res = simulate_telemetry(device_id="MAITRI_SIM_NODE_99", db=mock_db, user=op_user)

            assert res["status"] == "success"
            token = res["simulation_token"]
            assert token is not None
            # Token must NOT be fixed static token
            assert token != "dev-simulation-token"
            assert len(token) >= 32
            # Stored hash must match
            assert sim_dev.device_token_hash == hash_device_token(token)
            # Process incoming sensor data must have received the secure random token
            assert captured_token == token


# =====================================================================
# Finding 4: Parali NaN and Infinity Validation
# =====================================================================

class TestParaliFiniteValidation:
    def test_pydantic_schema_rejects_nan_and_inf(self):
        from app.schemas import ParaliAnalyzeRequest, ParaliActionPlanRequest

        # NaN in area
        with pytest.raises(ValidationError):
            ParaliAnalyzeRequest(crop="rice", area=float("nan"))

        # +Inf in area
        with pytest.raises(ValidationError):
            ParaliAnalyzeRequest(crop="rice", area=float("inf"))

        # -Inf in area
        with pytest.raises(ValidationError):
            ParaliAnalyzeRequest(crop="rice", area=float("-inf"))

        # NaN in residue_quantity
        with pytest.raises(ValidationError):
            ParaliAnalyzeRequest(crop="rice", area=2.0, residue_quantity=float("nan"))

        # +Inf in residue_quantity
        with pytest.raises(ValidationError):
            ParaliAnalyzeRequest(crop="rice", area=2.0, residue_quantity=float("inf"))

        # ActionPlanRequest NaN
        with pytest.raises(ValidationError):
            ParaliActionPlanRequest(method_id="in_situ_incorporation", area=float("nan"))

        # Valid request passes
        valid = ParaliAnalyzeRequest(crop="rice", area=2.5, residue_quantity=4.0)
        assert valid.area == 2.5
        assert valid.residue_quantity == 4.0

    def test_service_layer_rejects_nan_and_inf(self):
        from app.services.parali_management_service import analyze_crop_residue

        with pytest.raises(ValueError, match="finite number greater than 0"):
            analyze_crop_residue(crop="rice", area=float("nan"))

        with pytest.raises(ValueError, match="finite number greater than 0"):
            analyze_crop_residue(crop="rice", area=float("inf"))

        with pytest.raises(ValueError, match="finite number greater than 0"):
            analyze_crop_residue(crop="rice", area=float("-inf"))

        with pytest.raises(ValueError, match="finite number"):
            analyze_crop_residue(crop="rice", area=2.0, residue_quantity=float("nan"))

        with pytest.raises(ValueError, match="finite number"):
            analyze_crop_residue(crop="rice", area=2.0, residue_quantity=float("inf"))

        with pytest.raises(ValueError, match="cannot be negative"):
            analyze_crop_residue(crop="rice", area=2.0, residue_quantity=-3.0)

        # Valid service call succeeds
        result = analyze_crop_residue(crop="rice", area=2.5, residue_quantity=5.0)
        assert result["crop"] == "Rice / Paddy"
        assert result["area"] == 2.5
        assert result["estimated_residue_mid"] == 5.0
        assert result["is_farmer_override"] is True
