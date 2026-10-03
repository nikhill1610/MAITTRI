"""
Test Suite: CodeRabbit Hardening Round 7 Regression & Validation Tests
----------------------------------------------------------------------
Validates all 10 findings from CodeRabbit Round 7:
1. Notification.user_id integer PK architecture & safe UUID handling
2. deps.py safe identity handling without invalid integer-to-GUID DB queries
3. Parali farmer-provided residue measurement without artificial uncertainty
4. RAG fallback bounded timeout and removal of hardcoded sslmode="require"
5. Parali area strict validation and HTTP 400/422 error mapping
6. Document download error semantics distinguishing 404 vs 502/503
7. Document upload server-derived MIME type ignoring untrusted client MIME
8. Document upload memory exhaustion protection with bounded file.read()
9. IoT simulation token security strictly requiring elevated operator authorization
10. Soil estimation regional coverage for Western Coastal Lateritic & Bengal Delta
"""

import os
import io
import uuid
import asyncio
import pytest
from unittest.mock import MagicMock, patch
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.models import User, Profile, Farm, Farmer, FarmerDocument, IoTDevice, Notification
from app.deps import (
    AuthenticatedUser,
    is_valid_uuid,
    get_farmer_for_user,
    get_authorized_farm,
    is_same_user,
    is_elevated_user
)
from app.services.notification_service import create_and_dispatch_notification
from app.services.parali_management_service import (
    analyze_crop_residue,
    convert_to_acres,
    CROP_RESIDUE_DATABASE
)
from app.services.soil_estimation_service import _estimate_from_regional_icar
from app.routes.documents import (
    MAX_FILE_SIZE_BYTES,
    EXTENSION_TO_MIME,
    upload_document,
    download_document
)


# =====================================================================
# Finding 1: Notification.user_id Architecture & Safe Handling
# =====================================================================
class TestFinding1NotificationUserId:
    """
    Notification.user_id references local users.id (Integer PK).
    External non-integer UUIDs are safely handled without throwing PostgreSQL DatatypeMismatch errors.
    """

    def test_notification_with_supabase_uuid_does_not_crash(self):
        mock_db = MagicMock(spec=Session)
        user_uuid = str(uuid.uuid4())
        farmer_id = 10

        notif = create_and_dispatch_notification(
            db=mock_db,
            title="Weather Alert",
            message="Heavy rain forecast.",
            farmer_id=farmer_id,
            user_id=user_uuid,
            channel="WEB"
        )
        assert notif.user_id is None
        assert notif.farmer_id == farmer_id
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()

    def test_notification_with_integer_user_id_stored_correctly(self):
        mock_db = MagicMock(spec=Session)
        notif = create_and_dispatch_notification(
            db=mock_db,
            title="Advisory",
            message="Fertilizer advisory updated.",
            farmer_id=1,
            user_id=42,
            channel="WEB"
        )
        assert notif.user_id == 42
        mock_db.add.assert_called_once()

    def test_notification_with_stringified_integer_user_id(self):
        mock_db = MagicMock(spec=Session)
        notif = create_and_dispatch_notification(
            db=mock_db,
            title="Task",
            message="Irrigation cycle complete.",
            farmer_id=2,
            user_id="123",
            channel="WEB"
        )
        assert notif.user_id == 123
        mock_db.add.assert_called_once()


# =====================================================================
# Finding 2: deps.py Identity Compatibility (Integer vs GUID)
# =====================================================================
class TestFinding2DepsIdentityCompatibility:
    """
    Never pass an integer user ID into a PostgreSQL GUID column.
    Safely handle valid UUIDs, legacy integer identities, and malformed strings.
    """

    def test_is_valid_uuid_validation(self):
        valid = str(uuid.uuid4())
        assert is_valid_uuid(valid) is True
        assert is_valid_uuid(5) is False
        assert is_valid_uuid("5") is False
        assert is_valid_uuid("not-a-uuid") is False
        assert is_valid_uuid(None) is False

    def test_get_farmer_for_user_with_integer_returns_none_without_db_query(self):
        mock_db = MagicMock(spec=Session)
        farmer = get_farmer_for_user(mock_db, 5)
        assert farmer is None
        # Must not have executed a query that binds an integer to GUID column
        mock_db.query.assert_not_called()

    def test_get_farmer_for_user_with_malformed_string_returns_none(self):
        mock_db = MagicMock(spec=Session)
        farmer = get_farmer_for_user(mock_db, "malformed-string")
        assert farmer is None
        mock_db.query.assert_not_called()

    def test_get_farmer_for_user_with_valid_uuid_queries_database(self):
        mock_db = MagicMock(spec=Session)
        valid_uuid = str(uuid.uuid4())
        expected_farmer = Farmer(id=1, name="Ramesh", user_id=valid_uuid)
        mock_db.query.return_value.filter.return_value.first.return_value = expected_farmer

        farmer = get_farmer_for_user(mock_db, valid_uuid)
        assert farmer == expected_farmer
        mock_db.query.assert_called_once()

    def test_get_authorized_farm_with_legacy_integer_identity(self):
        mock_db = MagicMock(spec=Session)
        legacy_user = AuthenticatedUser(id=5, email="legacy@example.com", role="FARMER")
        farm = Farm(id=10, user_id=5, farmer_id=None, name="My Legacy Farm")
        mock_db.query.return_value.filter.return_value.first.return_value = farm

        auth_farm = get_authorized_farm(mock_db, farm_id=10, user=legacy_user)
        assert auth_farm.id == 10

    def test_get_authorized_farm_unauthorized_user_raises_404_or_403(self):
        mock_db = MagicMock(spec=Session)
        other_user = AuthenticatedUser(id=99, email="other@example.com", role="FARMER")
        farm = Farm(id=10, user_id="some-owner-uuid", farmer_id=1, name="Protected Farm")
        mock_db.query.return_value.filter.return_value.first.return_value = farm

        with pytest.raises(HTTPException) as exc_info:
            get_authorized_farm(mock_db, farm_id=10, user=other_user, detail_forbidden="Access denied")
        assert exc_info.value.status_code == 403


# =====================================================================
# Finding 3: Farmer-Provided Residue Measurement Without Uncertainty Range
# =====================================================================
class TestFinding3FarmerResidueMeasurement:
    """
    Farmer-provided residue measurement sets low = mid = high = known_qty.
    Does not create an artificial +/-15% uncertainty range.
    """

    def test_explicit_farmer_measurement_sets_exact_values(self):
        result = analyze_crop_residue(
            crop="rice",
            area=5.0,
            area_unit="acre",
            residue_quantity=12.5,
            residue_quantity_source="farmer_measurement"
        )
        assert result["is_farmer_override"] is True
        assert result["estimated_residue_low"] == 12.5
        assert result["estimated_residue_mid"] == 12.5
        assert result["estimated_residue_high"] == 12.5
        assert "Farmer Provided" in result["estimate_confidence"]

        # Limitations must describe the value as farmer-provided measurement, not an estimate
        limitations_text = " ".join(result["limitations"]).lower()
        assert "measured and provided directly by the farmer" in limitations_text
        assert "12.5 tonnes" in limitations_text

    def test_non_farmer_estimate_calculates_agronomic_range(self):
        result = analyze_crop_residue(
            crop="rice",
            area=5.0,
            area_unit="acre",
            residue_quantity=None
        )
        assert result["is_farmer_override"] is False
        assert result["estimated_residue_low"] < result["estimated_residue_mid"]
        assert result["estimated_residue_mid"] < result["estimated_residue_high"]
        assert "estimate calculated from average residue-to-grain ratios" in " ".join(result["limitations"]).lower()


# =====================================================================
# Finding 4: RAG Synchronous Retry and SSL Handling
# =====================================================================
class TestFinding4RAGRetryAndSSL:
    """
    RAG pgvector fallback connects with bounded timeout and does not force sslmode="require".
    """

    def test_fallback_does_not_force_sslmode(self):
        from app.services.rag_service import query_knowledge_base_pgvector
        with patch.dict(os.environ, {
            "DATABASE_URL": "postgresql://test_user:pass@localhost:5432/test_db",
            "ENVIRONMENT": "production"
        }), patch("app.services.rag_service.compute_query_embedding", return_value=[0.1] * 768), \
           patch("app.database.engine.connect", side_effect=Exception("Pool unavailable")), \
           patch("psycopg2.connect") as mock_connect:

            mock_conn = MagicMock()
            mock_cursor = MagicMock()
            mock_cursor.fetchall.return_value = []
            mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
            mock_connect.return_value = mock_conn

            query_knowledge_base_pgvector("wheat rust treatment")

            mock_connect.assert_called_once()
            _, kwargs = mock_connect.call_args
            assert kwargs.get("connect_timeout") == 3
            assert "sslmode" not in kwargs  # Must not hardcode sslmode="require"

    def test_fallback_returns_none_on_connection_error_without_long_blocking(self):
        from app.services.rag_service import query_knowledge_base_pgvector
        with patch.dict(os.environ, {
            "DATABASE_URL": "postgresql://user:pass@localhost:5432/db",
            "ENVIRONMENT": "production"
        }), patch("app.services.rag_service.compute_query_embedding", return_value=[0.1] * 768), \
           patch("app.database.engine.connect", side_effect=Exception("Pool unavailable")), \
           patch("psycopg2.connect", side_effect=Exception("Database connection timeout")):

            res = query_knowledge_base_pgvector("pest control")
            assert res is None


# =====================================================================
# Finding 5: Parali Area Strict Validation
# =====================================================================
class TestFinding5ParaliAreaValidation:
    """
    Area must be > 0 and numeric. Missing/zero/negative values are rejected.
    """

    def test_valid_positive_area_accepted(self):
        res = analyze_crop_residue(crop="wheat", area=2.5, area_unit="acre")
        assert res["area"] == 2.5
        assert res["area_normalized_acres"] == 2.5

    def test_zero_area_rejected(self):
        with pytest.raises(ValueError) as exc:
            analyze_crop_residue(crop="wheat", area=0.0, area_unit="acre")
        assert "greater than 0" in str(exc.value)

    def test_negative_area_rejected(self):
        with pytest.raises(ValueError) as exc:
            analyze_crop_residue(crop="wheat", area=-3.0, area_unit="acre")
        assert "greater than 0" in str(exc.value)

    def test_missing_area_rejected(self):
        with pytest.raises(ValueError) as exc:
            analyze_crop_residue(crop="wheat", area=None, area_unit="acre")
        assert "explicitly provided" in str(exc.value)

    def test_non_numeric_area_rejected(self):
        with pytest.raises(ValueError) as exc:
            analyze_crop_residue(crop="wheat", area="five", area_unit="acre")
        assert "numeric value" in str(exc.value)

    def test_unsupported_unit_rejected(self):
        with pytest.raises(ValueError) as exc:
            analyze_crop_residue(crop="wheat", area=2.0, area_unit="gaj")
        assert "Unsupported area unit" in str(exc.value)

    def test_valid_kanal_conversion(self):
        res = analyze_crop_residue(crop="wheat", area=8.0, area_unit="kanal")
        # 8 kanal = 1 acre
        assert res["area"] == 8.0
        assert res["area_normalized_acres"] == 1.0

    def test_route_maps_invalid_area_to_400(self):
        client = TestClient(app)
        resp = client.post("/api/parali/analyze", json={
            "crop": "rice",
            "area": -1.0,
            "area_unit": "acre"
        })
        assert resp.status_code in (400, 422)


# =====================================================================
# Finding 6: Document Download Error Semantics (404 vs 502/503)
# =====================================================================
class TestFinding6DocumentDownloadErrorSemantics:
    """
    Distinguish between missing file (404) and storage backend failure (502/503).
    """

    def test_file_missing_in_storage_returns_404(self):
        mock_db = MagicMock(spec=Session)
        user = AuthenticatedUser(id="farmer-uuid", email="f@test.com", role="FARMER")
        doc = FarmerDocument(
            id=1,
            farmer_id=10,
            document_name="Soil Card",
            storage_path="farmer-uuid/doc1.pdf",
            file_type="PDF"
        )
        mock_db.query.return_value.filter.return_value.first.return_value = doc

        mock_sb = MagicMock()
        mock_sb.storage.from_.return_value.download.side_effect = Exception("Object not found: 404")

        with patch("app.routes.documents.get_supabase_admin_client", return_value=mock_sb), \
             patch("app.routes.documents.authorize_document_access"):
            with pytest.raises(HTTPException) as exc_info:
                download_document(doc_id=1, current_user=user, db=mock_db)
            assert exc_info.value.status_code == 404

    def test_storage_service_failure_returns_502(self):
        mock_db = MagicMock(spec=Session)
        user = AuthenticatedUser(id="farmer-uuid", email="f@test.com", role="FARMER")
        doc = FarmerDocument(
            id=2,
            farmer_id=10,
            document_name="Kisan Card",
            storage_path="farmer-uuid/doc2.pdf",
            file_type="PDF"
        )
        mock_db.query.return_value.filter.return_value.first.return_value = doc

        mock_sb = MagicMock()
        mock_sb.storage.from_.return_value.download.side_effect = Exception("500 Internal Server Error: Gateway timeout")

        with patch("app.routes.documents.get_supabase_admin_client", return_value=mock_sb), \
             patch("app.routes.documents.authorize_document_access"):
            with pytest.raises(HTTPException) as exc_info:
                download_document(doc_id=2, current_user=user, db=mock_db)
            assert exc_info.value.status_code == 502

    def test_privileged_storage_client_unavailable_returns_503(self):
        mock_db = MagicMock(spec=Session)
        user = AuthenticatedUser(id="farmer-uuid", email="f@test.com", role="FARMER")
        doc = FarmerDocument(
            id=3,
            farmer_id=10,
            document_name="Doc",
            storage_path="farmer-uuid/doc3.pdf",
            file_type="PDF"
        )
        mock_db.query.return_value.filter.return_value.first.return_value = doc

        with patch("app.routes.documents.get_supabase_admin_client", return_value=None), \
             patch("app.routes.documents.authorize_document_access"):
            with pytest.raises(HTTPException) as exc_info:
                download_document(doc_id=3, current_user=user, db=mock_db)
            assert exc_info.value.status_code == 503


# =====================================================================
# Finding 7: Server-Side Authoritative MIME Type
# =====================================================================
class TestFinding7ServerSideMIMEType:
    """
    Client-supplied MIME type is ignored; server derives MIME strictly from validated extension.
    """

    def test_malicious_client_mime_type_ignored(self):
        mock_db = MagicMock(spec=Session)
        user = AuthenticatedUser(id="user-1", email="u@test.com", role="FARMER")
        farmer = Farmer(id=5, maittri_farmer_id="MT-FARM-000001", user_id="user-1")
        mock_db.query.return_value.filter.return_value.first.return_value = farmer

        mock_file = MagicMock()
        mock_file.filename = "land_record.png"
        mock_file.content_type = "text/html"  # Malicious client-supplied MIME
        mock_file.read = MagicMock()

        # Async read mock returning valid PNG signature bytes
        async def fake_read(size=-1):
            return b"\x89PNG\r\n\x1a\n" + b"\x00" * 100

        mock_file.read = fake_read

        mock_sb = MagicMock()
        with patch("app.routes.documents.get_supabase_admin_client", return_value=mock_sb):
            asyncio.run(upload_document(
                file=mock_file,
                farmer_id=5,
                document_name="Land Record",
                category="land_record",
                db=mock_db,
                current_user=user
            ))

        # Inspect call to Supabase upload: content-type must be image/png, NOT text/html
        mock_sb.storage.from_.return_value.upload.assert_called_once()
        _, kwargs = mock_sb.storage.from_.return_value.upload.call_args
        file_opts = kwargs.get("file_options", {})
        assert file_opts.get("content-type") == "image/png"


# =====================================================================
# Finding 8: Document Upload Bounded Read & Memory Exhaustion Prevention
# =====================================================================
class TestFinding8UploadMemoryExhaustion:
    """
    file.read() is strictly bounded to MAX_FILE_SIZE_BYTES + 1.
    """

    def test_file_exceeding_max_limit_rejected_immediately(self):
        mock_db = MagicMock(spec=Session)
        user = AuthenticatedUser(id="user-1", email="u@test.com", role="FARMER")
        farmer = Farmer(id=5, maittri_farmer_id="MT-FARM-000001", user_id="user-1")
        mock_db.query.return_value.filter.return_value.first.return_value = farmer

        mock_file = MagicMock()
        mock_file.filename = "oversized.pdf"
        mock_file.content_type = "application/pdf"

        # Simulates reading MAX_FILE_SIZE_BYTES + 1 bytes
        async def fake_read(size=-1):
            assert size == MAX_FILE_SIZE_BYTES + 1
            return b"A" * (MAX_FILE_SIZE_BYTES + 1)

        mock_file.read = fake_read

        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(upload_document(
                file=mock_file,
                farmer_id=5,
                document_name="Big Doc",
                category="land_record",
                db=mock_db,
                current_user=user
            ))
        assert exc_info.value.status_code == 400
        assert "exceeds 10MB limit" in exc_info.value.detail


# =====================================================================
# Finding 9: IoT Simulation Token Security
# =====================================================================
class TestFinding9IoTSimulationTokenSecurity:
    """
    Simulation token assignment strictly requires an authenticated elevated operator.
    Device names alone (MAITRI_SIM_*, names with 'simulat') are NOT sufficient authorization.
    """

    def test_anonymous_simulation_token_assignment_rejected(self):
        from app.routes.iot import simulate_telemetry
        mock_db = MagicMock(spec=Session)
        sim_device = IoTDevice(device_id="MAITRI_SIM_99", name="Simulation Node", device_token_hash=None)
        mock_db.query.return_value.filter.return_value.first.return_value = sim_device

        with patch.dict(os.environ, {"ENVIRONMENT": "development"}):
            with pytest.raises(HTTPException) as exc:
                simulate_telemetry(device_id="MAITRI_SIM_99", db=mock_db, user=None)
            assert exc.value.status_code == 403
            assert "elevated operator privileges" in exc.value.detail

    def test_normal_farmer_simulation_token_assignment_rejected(self):
        from app.routes.iot import simulate_telemetry
        mock_db = MagicMock(spec=Session)
        sim_device = IoTDevice(device_id="MAITRI_SIM_99", name="Simulation Node", device_token_hash=None)
        mock_db.query.return_value.filter.return_value.first.return_value = sim_device

        farmer_user = AuthenticatedUser(id="f-1", email="farmer@test.com", role="FARMER")

        with patch.dict(os.environ, {"ENVIRONMENT": "development"}):
            with pytest.raises(HTTPException) as exc:
                simulate_telemetry(device_id="MAITRI_SIM_99", db=mock_db, user=farmer_user)
            assert exc.value.status_code == 403
            assert "elevated operator privileges" in exc.value.detail

    def test_elevated_operator_allowed_in_development(self):
        from app.routes.iot import simulate_telemetry
        mock_db = MagicMock(spec=Session)
        sim_device = IoTDevice(device_id="MAITRI_SIM_NODE", name="Sim Node", device_token_hash=None)
        mock_db.query.return_value.filter.return_value.first.return_value = sim_device

        operator_user = AuthenticatedUser(id="op-1", email="op@test.com", role="AUTHORIZED_OPERATOR")

        with patch.dict(os.environ, {"ENVIRONMENT": "development"}), \
             patch("app.routes.iot.process_incoming_sensor_data", return_value={"status": "online"}):
            res = simulate_telemetry(device_id="MAITRI_SIM_NODE", db=mock_db, user=operator_user)
            assert res["status"] == "success"
            assert sim_device.device_token_hash is not None

    def test_production_environment_blocks_simulation_even_for_operator(self):
        from app.routes.iot import simulate_telemetry
        mock_db = MagicMock(spec=Session)
        operator_user = AuthenticatedUser(id="op-1", email="op@test.com", role="AUTHORIZED_OPERATOR")

        with patch.dict(os.environ, {"ENVIRONMENT": "production"}):
            with pytest.raises(HTTPException) as exc:
                simulate_telemetry(device_id="MAITRI_SIM_NODE", db=mock_db, user=operator_user)
            assert exc.value.status_code == 403
            assert "disabled in production" in exc.value.detail


# =====================================================================
# Finding 10: Soil Estimation Regional Coverage
# =====================================================================
class TestFinding10SoilEstimationRegionalCoverage:
    """
    Validates coastal lateritic (Goa, Mangalore, Kannur) and Lower Gangetic Delta (Kolkata)
    without degrading existing regional classifications.
    """

    def test_goa_classified_as_laterite_soil(self):
        res = _estimate_from_regional_icar(15.5, 73.8)
        assert res["probable_soil_type"] == "Laterite Soil"
        assert "Western Ghats & Coastal Lateritic Belt" in res["region"]

    def test_mangalore_classified_as_laterite_soil(self):
        res = _estimate_from_regional_icar(12.9, 74.85)
        assert res["probable_soil_type"] == "Laterite Soil"

    def test_kannur_classified_as_laterite_soil(self):
        res = _estimate_from_regional_icar(11.87, 75.37)
        assert res["probable_soil_type"] == "Laterite Soil"

    def test_kolkata_classified_as_alluvial_soil(self):
        res = _estimate_from_regional_icar(22.57, 88.36)
        assert res["probable_soil_type"] == "Alluvial Soil"
        assert "Lower Gangetic Plain & Bengal Delta" in res["region"]

    def test_existing_regions_preserved(self):
        # Delhi -> Indo-Gangetic Alluvial
        delhi = _estimate_from_regional_icar(28.6139, 77.2090)
        assert delhi["probable_soil_type"] == "Alluvial Soil"

        # Jodhpur -> Thar Arid
        jodhpur = _estimate_from_regional_icar(26.2389, 73.0243)
        assert jodhpur["probable_soil_type"] == "Desert/Arid Soil"

        # Nagpur -> Deccan Trap Black Soil
        nagpur = _estimate_from_regional_icar(21.1458, 79.0882)
        assert nagpur["probable_soil_type"] == "Black Soil"
