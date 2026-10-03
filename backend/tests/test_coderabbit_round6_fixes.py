"""
Comprehensive Regression Test Suite for CodeRabbit Round 6 Hardening
=====================================================================
Covers 13 Findings:
1.  IoT simulation token security (backend/app/routes/iot.py)
2.  Chat debug endpoint authorization and top_k bounds (backend/app/routes/chat.py)
3.  Documents anon storage fallback removal (backend/app/routes/documents.py)
4.  Farm ownership validation for document upload (backend/app/routes/documents.py)
5.  Notification.user_id GUID architecture (backend/app/models.py, backend/app/services/notification_service.py)
6.  Document access authorization & historical uploader isolation (backend/app/routes/documents.py)
7.  Storage deletion failure protection (backend/app/routes/documents.py)
8.  IVR market-price exception handling (backend/app/services/ivr_service.py)
9.  IVR pest diagnostic option 9 & invalid input handling (backend/app/services/ivr_service.py)
10. SMS phone normalization & placeholder validation (backend/app/services/sms_service.py)
11. Parali area units validation & kanal support (backend/app/services/parali_management_service.py)
12. Parali machinery token/tag matching (backend/app/services/parali_management_service.py)
13. Parali crop normalization & alias boundary matching (backend/app/services/parali_management_service.py)
"""

import os
import uuid
import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.models import Farmer, Farm, FarmerDocument, User, Profile, Notification, IoTDevice
from app.deps import AuthenticatedUser
from app.services.ivr_service import handle_ivr_interaction
from app.services.sms_service import dispatch_sms
from app.services.notification_service import create_and_dispatch_notification
from app.services.parali_management_service import (
    convert_to_acres,
    compute_method_score,
    normalize_crop_key,
    normalize_machine_tokens,
    check_machinery_overlap,
    RESIDUE_METHODS_CATALOG
)


# =====================================================================
# Finding 1: IoT Simulation Token Security
# =====================================================================
class TestFinding1IoTSimulationTokenSecurity:
    """
    Simulate endpoint must not assign dev-simulation-token to arbitrary existing devices.
    Only explicit simulation devices or elevated operators can simulate.
    Production must block simulate endpoint.
    """

    def test_production_blocks_simulation(self):
        client = TestClient(app)
        with patch.dict(os.environ, {"ENVIRONMENT": "production"}):
            resp = client.post("/api/iot/simulate?device_id=MAITRI_ESP8266_01")
            assert resp.status_code == 403
            assert "disabled in production" in resp.json()["detail"].lower()

    def test_arbitrary_device_without_token_hash_rejected_for_regular_caller(self):
        client = TestClient(app)
        from app.routes.iot import simulate_telemetry

        mock_db = MagicMock(spec=Session)
        real_device = IoTDevice(
            device_id="FIELD_NODE_REAL_99",
            name="Field Hardware Sensor",
            device_token_hash=None
        )
        mock_db.query.return_value.filter.return_value.first.return_value = real_device

        regular_user = AuthenticatedUser(id="farmer-uuid-1", email="farmer@example.com", role="FARMER")

        with patch.dict(os.environ, {"ENVIRONMENT": "development"}):
            with pytest.raises(HTTPException) as exc_info:
                simulate_telemetry(
                    device_id="FIELD_NODE_REAL_99",
                    controller_type="ESP32",
                    db=mock_db,
                    user=regular_user
                )
            assert exc_info.value.status_code == 403
            assert "Cannot assign simulation credentials" in exc_info.value.detail

    def test_legitimate_simulation_device_flow_succeeds(self):
        from app.routes.iot import simulate_telemetry

        mock_db = MagicMock(spec=Session)
        sim_device = IoTDevice(
            device_id="MAITRI_ESP8266_01",
            name="Simulation Node",
            device_token_hash=None
        )
        mock_db.query.return_value.filter.return_value.first.return_value = sim_device
        operator_user = AuthenticatedUser(id="op-sim", email="opsim@example.com", role="AUTHORIZED_OPERATOR")

        with patch.dict(os.environ, {"ENVIRONMENT": "development"}), \
             patch("app.routes.iot.process_incoming_sensor_data", return_value={"status": "ok"}):
            res = simulate_telemetry(
                device_id="MAITRI_ESP8266_01",
                controller_type="ESP8266",
                db=mock_db,
                user=operator_user
            )
            assert res["status"] == "success"
            assert sim_device.device_token_hash is not None

    def test_elevated_operator_can_simulate_arbitrary_device(self):
        from app.routes.iot import simulate_telemetry

        mock_db = MagicMock(spec=Session)
        arbitrary_dev = IoTDevice(
            device_id="CUSTOM_PROTOTYPE_01",
            name="Custom Prototype",
            device_token_hash=None
        )
        mock_db.query.return_value.filter.return_value.first.return_value = arbitrary_dev
        operator_user = AuthenticatedUser(id="op-1", email="op@example.com", role="AUTHORIZED_OPERATOR")

        with patch.dict(os.environ, {"ENVIRONMENT": "development"}), \
             patch("app.routes.iot.process_incoming_sensor_data", return_value={"status": "ok"}):
            res = simulate_telemetry(
                device_id="CUSTOM_PROTOTYPE_01",
                controller_type="ESP8266",
                db=mock_db,
                user=operator_user
            )
            assert res["status"] == "success"
            assert arbitrary_dev.device_token_hash is not None


# =====================================================================
# Finding 2: Chat Debug Endpoint Security & Bounds
# =====================================================================
class TestFinding2ChatDebugEndpoint:
    """
    Chat debug endpoint must:
    - reject unauthenticated requests
    - reject non-operator authenticated requests
    - allow authorized operator access in non-production
    - validate/clamp top_k
    """

    def test_unauthenticated_request_rejected(self):
        client = TestClient(app)
        with patch.dict(os.environ, {"ENVIRONMENT": "development"}):
            resp = client.post("/api/chat/debug", json={"query": "wheat rust", "top_k": 4})
            assert resp.status_code in (401, 403)

    def test_non_operator_user_rejected(self):
        client = TestClient(app)
        farmer_user = AuthenticatedUser(id="farmer-1", email="farmer@test.com", role="FARMER")
        with patch("app.deps._resolve_user_from_token", return_value=farmer_user), \
             patch.dict(os.environ, {"ENVIRONMENT": "development"}):
            headers = {"Authorization": "Bearer fake-token"}
            resp = client.post("/api/chat/debug", json={"query": "wheat rust", "top_k": 4}, headers=headers)
            assert resp.status_code == 403
            assert "restricted to Authorized Agriculture / Seva Operators" in resp.json()["detail"]

    def test_authorized_operator_works_in_dev(self):
        client = TestClient(app)
        operator_user = AuthenticatedUser(id="op-1", email="op@test.com", role="AUTHORIZED_OPERATOR")
        mock_results = [{"chunk_id": 1, "text": "sample chunk", "score": 0.85}]

        with patch("app.deps._resolve_user_from_token", return_value=operator_user), \
             patch("app.routes.chat.query_knowledge_base", return_value=mock_results), \
             patch.dict(os.environ, {"ENVIRONMENT": "development"}):
            headers = {"Authorization": "Bearer fake-token"}
            resp = client.post("/api/chat/debug", json={"query": "wheat rust", "top_k": 4}, headers=headers)
            assert resp.status_code == 200
            assert resp.json() == mock_results

    def test_excessive_top_k_rejected(self):
        client = TestClient(app)
        operator_user = AuthenticatedUser(id="op-1", email="op@test.com", role="AUTHORIZED_OPERATOR")
        with patch("app.deps._resolve_user_from_token", return_value=operator_user), \
             patch.dict(os.environ, {"ENVIRONMENT": "development"}):
            headers = {"Authorization": "Bearer fake-token"}
            # top_k=50 exceeds le=20
            resp = client.post("/api/chat/debug", json={"query": "wheat rust", "top_k": 50}, headers=headers)
            assert resp.status_code == 422


# =====================================================================
# Finding 3: Documents Anon Storage Fallback Removal
# =====================================================================
class TestFinding3DocumentsAnonStorageFallback:
    """
    farmer-vault is private. Anon storage fallback must be removed.
    If privileged admin client is unavailable, return safe 503.
    """

    def test_download_privileged_client_unavailable_returns_503(self):
        from app.routes.documents import download_document
        mock_db = MagicMock(spec=Session)
        doc = FarmerDocument(
            id=10,
            farmer_id=1,
            document_name="Khasra",
            file_type="PDF",
            storage_path="user-1/khasra.pdf"
        )
        mock_db.query.return_value.filter.return_value.first.return_value = doc
        elevated_user = AuthenticatedUser(id="admin-1", email="admin@test.com", role="ADMIN")

        with patch("app.routes.documents.get_supabase_admin_client", return_value=None):
            with pytest.raises(HTTPException) as exc_info:
                download_document(doc_id=10, current_user=elevated_user, db=mock_db)
            assert exc_info.value.status_code == 503
            assert "Vault storage service unavailable" in exc_info.value.detail

    def test_signed_url_privileged_client_unavailable_returns_503(self):
        from app.routes.documents import get_signed_url
        mock_db = MagicMock(spec=Session)
        doc = FarmerDocument(
            id=11,
            farmer_id=1,
            document_name="SoilReport",
            storage_path="user-1/soil.pdf"
        )
        mock_db.query.return_value.filter.return_value.first.return_value = doc
        elevated_user = AuthenticatedUser(id="admin-1", email="admin@test.com", role="ADMIN")

        with patch("app.routes.documents.get_supabase_admin_client", return_value=None):
            with pytest.raises(HTTPException) as exc_info:
                get_signed_url(doc_id=11, expires_in=3600, current_user=elevated_user, db=mock_db)
            assert exc_info.value.status_code == 503
            assert "Vault storage service unavailable" in exc_info.value.detail


# =====================================================================
# Finding 4: Farm Ownership Validation on Document Upload
# =====================================================================
class TestFinding4FarmOwnershipValidation:
    """
    When farmer_id and farm_id are both provided, verify farm actually belongs to farmer.
    Prevent cross-tenant document attachment.
    """

    @pytest.mark.anyio
    async def test_mismatched_farmer_and_farm_rejected_with_400(self):
        from app.routes.documents import upload_document

        mock_db = MagicMock(spec=Session)
        farmer_a = Farmer(id=1, user_id="user-a", name="Farmer A")
        farm_b = Farm(id=99, farmer_id=2, user_id="user-b", name="Farm of Farmer B")

        def query_side_effect(model):
            mock_query = MagicMock()
            if model == Farmer:
                mock_query.filter.return_value.first.return_value = farmer_a
            elif model == Farm:
                mock_query.filter.return_value.first.return_value = farm_b
            return mock_query

        mock_db.query.side_effect = query_side_effect
        operator = AuthenticatedUser(id="op-1", email="op@example.com", role="AUTHORIZED_OPERATOR")

        mock_file = MagicMock()
        mock_file.filename = "soil_test.pdf"

        with pytest.raises(HTTPException) as exc_info:
            await upload_document(
                farmer_id=1,
                farm_id=99,
                document_name="Soil Test",
                category="Soil Test Report",
                file=mock_file,
                current_user=operator,
                db=mock_db
            )
        assert exc_info.value.status_code == 400
        assert "Farm does not belong to the specified farmer" in exc_info.value.detail

    @pytest.mark.anyio
    async def test_unauthorized_farm_rejected_with_403(self):
        from app.routes.documents import upload_document

        mock_db = MagicMock(spec=Session)
        farmer_a = Farmer(id=1, user_id="user-a", name="Farmer A")
        farm_other = Farm(id=99, farmer_id=2, user_id="user-other", name="Farm Other")

        def query_side_effect(model):
            mock_query = MagicMock()
            if model == Farmer:
                mock_query.filter.return_value.first.return_value = farmer_a
            elif model == Farm:
                mock_query.filter.return_value.first.return_value = farm_other
            return mock_query

        mock_db.query.side_effect = query_side_effect
        # Regular farmer user A attempts to upload for farm_other
        farmer_user = AuthenticatedUser(id="user-a", email="a@example.com", role="FARMER")

        mock_file = MagicMock()
        mock_file.filename = "khasra.pdf"

        with pytest.raises(HTTPException) as exc_info:
            await upload_document(
                farmer_id=1,
                farm_id=99,
                document_name="Khasra",
                category="Land Record",
                file=mock_file,
                current_user=farmer_user,
                db=mock_db
            )
        assert exc_info.value.status_code == 403


# =====================================================================
# Finding 5: Notification.user_id GUID Architecture
# =====================================================================
class TestFinding5NotificationUserIdArchitecture:
    """
    Notification.user_id references users.id (Integer primary key in PostgreSQL).
    Service must safely handle legacy integer IDs as integers and guard UUIDs to prevent
    PostgreSQL DatatypeMismatch errors when user_id is an uncastable string/UUID.
    """

    def test_notification_with_supabase_uuid_dispatched_and_stored(self):
        mock_db = MagicMock(spec=Session)
        user_uuid = str(uuid.uuid4())
        farmer_id = 42

        notif = create_and_dispatch_notification(
            db=mock_db,
            title="Weather Alert",
            message="Heavy rain expected tomorrow.",
            farmer_id=farmer_id,
            user_id=user_uuid,
            channel="WEB"
        )
        # Uncastable UUID is safely set to None to avoid Postgres Integer DatatypeMismatch
        assert notif.user_id is None
        assert notif.farmer_id == farmer_id
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()

    def test_notification_with_legacy_integer_id_supported(self):
        mock_db = MagicMock(spec=Session)
        notif = create_and_dispatch_notification(
            db=mock_db,
            title="Task Due",
            message="Fertilizer application scheduled.",
            farmer_id=1,
            user_id=101,
            channel="WEB"
        )
        assert notif.user_id == 101
        mock_db.add.assert_called_once()

    def test_notification_with_stringified_integer_id_supported(self):
        mock_db = MagicMock(spec=Session)
        notif = create_and_dispatch_notification(
            db=mock_db,
            title="Task Due",
            message="Fertilizer application scheduled.",
            farmer_id=1,
            user_id="202",
            channel="WEB"
        )
        assert notif.user_id == 202
        mock_db.add.assert_called_once()


# =====================================================================
# Finding 6: Document Access Authorization & Historical Uploader Isolation
# =====================================================================
class TestFinding6DocumentAccessAuthorization:
    """
    Access must be based on current ownership of doc.farmer_id plus elevated roles.
    Historical uploader must NOT retain access if farmer ownership changes.
    """

    def test_farmer_owner_can_access_own_document(self):
        from app.routes.documents import authorize_document_access
        mock_db = MagicMock(spec=Session)
        farmer = Farmer(id=5, user_id="farmer-uuid-5", name="Owner Farmer")
        doc = FarmerDocument(id=1, farmer_id=5, uploaded_by_user_id="operator-uuid-1")
        mock_db.query.return_value.filter.return_value.first.return_value = farmer

        current_user = AuthenticatedUser(id="farmer-uuid-5", email="farmer5@test.com", role="FARMER")
        # Should succeed without raising exception
        authorize_document_access(doc, current_user, mock_db, action="download")

    def test_unrelated_farmer_denied_access(self):
        from app.routes.documents import authorize_document_access
        mock_db = MagicMock(spec=Session)
        farmer = Farmer(id=5, user_id="farmer-uuid-5", name="Owner Farmer")
        doc = FarmerDocument(id=1, farmer_id=5, uploaded_by_user_id="operator-uuid-1")
        mock_db.query.return_value.filter.return_value.first.return_value = farmer

        unrelated_user = AuthenticatedUser(id="unrelated-uuid", email="other@test.com", role="FARMER")
        with pytest.raises(HTTPException) as exc_info:
            authorize_document_access(doc, unrelated_user, mock_db, action="download")
        assert exc_info.value.status_code == 403
        assert "another farmer's vault" in exc_info.value.detail

    def test_historical_uploader_denied_when_no_longer_owner(self):
        from app.routes.documents import authorize_document_access
        mock_db = MagicMock(spec=Session)
        # Farmer's current owner is farmer-new-owner
        farmer = Farmer(id=5, user_id="farmer-new-owner", name="New Owner")
        # Document was originally uploaded by historical-uploader
        doc = FarmerDocument(id=1, farmer_id=5, uploaded_by_user_id="historical-uploader")
        mock_db.query.return_value.filter.return_value.first.return_value = farmer

        # Historical uploader is a regular farmer user now
        historical_user = AuthenticatedUser(id="historical-uploader", email="old@test.com", role="FARMER")
        with pytest.raises(HTTPException) as exc_info:
            authorize_document_access(doc, historical_user, mock_db, action="download")
        assert exc_info.value.status_code == 403
        assert "another farmer's vault" in exc_info.value.detail

    def test_elevated_role_granted_access(self):
        from app.routes.documents import authorize_document_access
        mock_db = MagicMock(spec=Session)
        doc = FarmerDocument(id=1, farmer_id=5, uploaded_by_user_id="historical-uploader")
        operator = AuthenticatedUser(id="op-1", email="op@test.com", role="AUTHORIZED_OPERATOR")
        # Should succeed without error
        authorize_document_access(doc, operator, mock_db, action="download")

    def test_delete_authorization_enforced(self):
        from app.routes.documents import authorize_document_access
        mock_db = MagicMock(spec=Session)
        farmer = Farmer(id=5, user_id="farmer-uuid-5", name="Owner")
        doc = FarmerDocument(id=1, farmer_id=5, uploaded_by_user_id="operator-1")
        mock_db.query.return_value.filter.return_value.first.return_value = farmer

        unrelated = AuthenticatedUser(id="unrelated-user", email="un@test.com", role="FARMER")
        with pytest.raises(HTTPException) as exc_info:
            authorize_document_access(doc, unrelated, mock_db, action="delete")
        assert exc_info.value.status_code == 403


# =====================================================================
# Finding 7: Storage Deletion Failure Protection
# =====================================================================
class TestFinding7StorageDeletionFailure:
    """
    When deleting a document:
    - attempt storage removal first
    - if storage removal fails, DO NOT delete DB row, return 502/503
    - if storage removal succeeds, delete DB row
    """

    def test_storage_removal_fails_db_row_not_deleted(self):
        from app.routes.documents import delete_document
        mock_db = MagicMock(spec=Session)
        doc = FarmerDocument(id=20, farmer_id=1, storage_path="user-1/file.pdf")
        mock_db.query.return_value.filter.return_value.first.return_value = doc

        mock_sb = MagicMock()
        mock_sb.storage.from_.return_value.remove.side_effect = Exception("Storage S3 API error")

        admin_user = AuthenticatedUser(id="admin-1", email="admin@test.com", role="ADMIN")

        with patch("app.routes.documents.get_supabase_admin_client", return_value=mock_sb):
            with pytest.raises(HTTPException) as exc_info:
                delete_document(doc_id=20, current_user=admin_user, db=mock_db)
            assert exc_info.value.status_code == 502
            assert "Database record preserved for retry" in exc_info.value.detail
            # DB record MUST NOT be deleted
            mock_db.delete.assert_not_called()

    def test_storage_removal_succeeds_db_row_deleted(self):
        from app.routes.documents import delete_document
        mock_db = MagicMock(spec=Session)
        doc = FarmerDocument(id=20, farmer_id=1, storage_path="user-1/file.pdf")
        mock_db.query.return_value.filter.return_value.first.return_value = doc

        mock_sb = MagicMock()
        mock_sb.storage.from_.return_value.remove.return_value = [{"name": "file.pdf"}]

        admin_user = AuthenticatedUser(id="admin-1", email="admin@test.com", role="ADMIN")

        with patch("app.routes.documents.get_supabase_admin_client", return_value=mock_sb):
            res = delete_document(doc_id=20, current_user=admin_user, db=mock_db)
            assert res["status"] == "success"
            mock_db.delete.assert_called_once_with(doc)
            mock_db.commit.assert_called_once()


# =====================================================================
# Finding 8: IVR Market-Price Exception Handling
# =====================================================================
class TestFinding8IVRMarketPriceExceptionHandling:
    """
    If get_latest_market_price throws an exception:
    - safely caught
    - no price fabricated
    - fallback message returned
    - IVR session kept alive
    """

    def test_market_service_exception_does_not_crash_ivr(self):
        mock_db = MagicMock(spec=Session)
        farmer = Farmer(id=1, name="Test Farmer", current_crop="Wheat", state="Uttar Pradesh", district="Meerut")
        mock_db.query.return_value.filter.return_value.first.return_value = farmer

        with patch("app.services.market_price_service.get_latest_market_price", side_effect=RuntimeError("Mandi API timeout")):
            res = handle_ivr_interaction(
                db=mock_db,
                session_id="IVR-TEST-FAIL",
                phone_number="9876543210",
                digits_pressed="5",
                current_menu="main",
                language="hi"
            )
            assert res["status"] == "ACTIVE"
            assert "मंडी भाव उपलब्ध नहीं है" in res["audio_text_hi"]
            assert res["current_menu"] == "action_done"


# =====================================================================
# Finding 9: IVR Pest Step 1 Option 9 & Invalid Digits
# =====================================================================
class TestFinding9IVRPestStep1Option9:
    """
    pest_step_1:
    1 = diagnosis
    2 = diagnosis
    3 = diagnosis
    9 = return to main menu
    anything else = invalid + stay on pest_step_1
    """

    def test_pest_step_1_option_9_returns_to_main_menu(self):
        mock_db = MagicMock(spec=Session)
        mock_db.query.return_value.filter.return_value.first.return_value = None

        res = handle_ivr_interaction(
            db=mock_db,
            session_id="IVR-PEST-9",
            phone_number="9876543210",
            digits_pressed="9",
            current_menu="pest_step_1",
            language="en"
        )
        assert res["current_menu"] == "main"
        assert "Welcome to Maitri Farmer Assistance" in res["audio_text_en"]

    def test_pest_step_1_invalid_digit_stays_on_pest_step_1(self):
        mock_db = MagicMock(spec=Session)
        mock_db.query.return_value.filter.return_value.first.return_value = None

        res = handle_ivr_interaction(
            db=mock_db,
            session_id="IVR-PEST-INV",
            phone_number="9876543210",
            digits_pressed="7",
            current_menu="pest_step_1",
            language="en"
        )
        assert res["current_menu"] == "pest_step_1"
        assert "Invalid selection" in res["audio_text_en"]
        assert "Root rot" not in res["audio_text_en"]


# =====================================================================
# Finding 10: SMS Phone Normalization & Placeholder Rejection
# =====================================================================
class TestFinding10SMSPhoneNormalization:
    """
    Normalize phone number before validation.
    Reject:
    - too short (<10 digits)
    - last10 starts with 00000
    - all identical digits
    Accept valid Indian and international numbers.
    """

    def test_reject_too_short(self):
        mock_db = MagicMock(spec=Session)
        res = dispatch_sms(mock_db, "12345", "Test alert")
        assert not res["success"]
        assert res["error"] == "Invalid or missing mobile number"

    def test_reject_last10_starts_with_00000(self):
        mock_db = MagicMock(spec=Session)
        # With Indian country code
        res1 = dispatch_sms(mock_db, "+910000012345", "Test alert")
        assert not res1["success"]
        assert res1["error"] == "Invalid or placeholder mobile number"

        # Direct 10 digits
        res2 = dispatch_sms(mock_db, "0000098765", "Test alert")
        assert not res2["success"]
        assert res2["error"] == "Invalid or placeholder mobile number"

    def test_reject_all_identical_digits(self):
        mock_db = MagicMock(spec=Session)
        res1 = dispatch_sms(mock_db, "9999999999", "Test alert")
        assert not res1["success"]
        assert res1["error"] == "Invalid or placeholder mobile number"

        res2 = dispatch_sms(mock_db, "+911111111111", "Test alert")
        assert not res2["success"]
        assert res2["error"] == "Invalid or placeholder mobile number"

    def test_accepts_valid_indian_number(self):
        mock_db = MagicMock(spec=Session)
        res = dispatch_sms(mock_db, "+919876543210", "Test alert")
        assert res["success"]

    def test_accepts_valid_international_number(self):
        mock_db = MagicMock(spec=Session)
        res = dispatch_sms(mock_db, "+14155552671", "Test alert")
        assert res["success"]


# =====================================================================
# Finding 11: Parali Area Units & Kanal Support
# =====================================================================
class TestFinding11ParaliAreaUnits:
    """
    Must support verified units: acre, hectare, bigha, kanal (0.125), sq_m, sq_ft.
    Must raise ValueError on unknown units; no silent fallback to acres.
    """

    def test_supported_units(self):
        assert convert_to_acres(2.0, "acre") == 2.0
        assert convert_to_acres(1.0, "hectare") == pytest.approx(2.47105, rel=1e-3)
        assert convert_to_acres(10.0, "bigha") == pytest.approx(6.2, rel=1e-2)

    def test_kanal_conversion_supported(self):
        # 1 Acre = 8 Kanals => 8 kanals = 1.0 acre
        assert convert_to_acres(8.0, "kanal") == pytest.approx(1.0, rel=1e-3)
        assert convert_to_acres(16.0, "कनाल") == pytest.approx(2.0, rel=1e-3)

    def test_unknown_unit_raises_value_error(self):
        with pytest.raises(ValueError) as exc_info:
            convert_to_acres(5.0, "furlong")
        assert "Unsupported area unit 'furlong'" in str(exc_info.value)

        with pytest.raises(ValueError) as exc_info:
            convert_to_acres(5.0, "yards")
        assert "Unsupported area unit 'yards'" in str(exc_info.value)


# =====================================================================
# Finding 12: Parali Machinery Matching
# =====================================================================
class TestFinding12ParaliMachineryMatching:
    """
    Machinery matching must avoid false matches from 'or', 'and', 'machine', 'tractor', 'trolley'.
    """

    def test_rotavator_does_not_match_unrelated_machinery_via_or(self):
        # "Super Seeder or Happy Seeder" contains "or", but rotavator must NOT match it
        req = ["Super Seeder or Happy Seeder"]
        avail = ["Rotavator"]
        assert not check_machinery_overlap(req, avail)

    def test_tractor_alone_does_not_match_unrelated_tractor_implements(self):
        req = ["Cotton Stalk Slasher / Shredder", "Reversible MB Plough"]
        avail = ["Tractor"]
        assert not check_machinery_overlap(req, avail)

    def test_baler_matches_square_and_round_baler(self):
        req = RESIDUE_METHODS_CATALOG["ex_situ_baling"]["machinery_needed"]
        assert check_machinery_overlap(req, ["Square Baler"])
        assert check_machinery_overlap(req, ["Round Baler"])
        assert check_machinery_overlap(req, ["Straw Baler"])

    def test_mulcher_chopper_matches_properly(self):
        req = RESIDUE_METHODS_CATALOG["in_situ_incorporation"]["machinery_needed"]
        assert check_machinery_overlap(req, ["Mulcher"])
        assert check_machinery_overlap(req, ["Paddy Chopper"])
        assert check_machinery_overlap(req, ["Rotavator"])
        assert not check_machinery_overlap(req, ["Water Pump"])


# =====================================================================
# Finding 13: Parali Crop Normalization
# =====================================================================
class TestFinding13ParaliCropNormalization:
    """
    Ensure supported crops like urad, arhar, tur, masoor, lentil, chickpea, soya
    normalize to correct canonical profile using whole-word boundary matching.
    """

    def test_pulses_canonical_normalization(self):
        assert normalize_crop_key("urad") == "pulses"
        assert normalize_crop_key("arhar") == "pulses"
        assert normalize_crop_key("tur") == "pulses"
        assert normalize_crop_key("masoor") == "pulses"
        assert normalize_crop_key("lentil") == "pulses"
        assert normalize_crop_key("chickpea") == "pulses"
        assert normalize_crop_key("moong") == "pulses"
        assert normalize_crop_key("chana") == "pulses"

    def test_soybean_canonical_normalization(self):
        assert normalize_crop_key("soya") == "soybean"
        assert normalize_crop_key("soybean") == "soybean"
        assert normalize_crop_key("सोयाबीन") == "soybean"

    def test_staples_normalization(self):
        assert normalize_crop_key("rice") == "rice"
        assert normalize_crop_key("paddy") == "rice"
        assert normalize_crop_key("wheat") == "wheat"
        assert normalize_crop_key("corn") == "maize"

    def test_no_substring_misclassification(self):
        # 'price' contains 'rice', but must not normalize to rice
        assert normalize_crop_key("price") == "other"
        # 'texture' contains 'tur', but must not normalize to pulses
        assert normalize_crop_key("texture") == "other"
        # 'cottonwood' contains 'cotton', but must not normalize to cotton
        assert normalize_crop_key("cottonwood") == "other"
