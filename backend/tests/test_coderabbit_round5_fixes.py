"""
Regression Tests for CodeRabbit Round 5 Hardening (10 Findings)
==============================================================
Finding 1 (Minor): IoTSensorReading authoritative device_table_id lookup (no bare device_id fallback).
Finding 2 (Minor): Generic safe client error messages on storage vault failures.
Finding 3 (Minor): Orphaned storage object cleanup on DB commit failure.
Finding 4 (Minor): GUID TypeDecorator strictly validates UUID format on PostgreSQL dialect.
Finding 5 (Minor): Local auth.users fallback requires explicit ALLOW_LOCAL_AUTH_INSERT=true opt-in.
Finding 6 (Minor): Compound crop aliases for chick pea and pigeon pea to prevent token split as Pea.
Finding 7 (Major): IVR Weather reports authentic weather data or unavailable, never fake hardcoded defaults.
Finding 8 (Major): IVR Guided Pest Step 1 requires explicit digit '3' for root rot, rejects invalid/missing digits.
Finding 9 (Major): IVR Market Price queries authoritative service for registered crop, never hardcodes wheat/mustard.
Finding 10 (Major): IntegrityError exception handler logs exception class name without exposing raw SQL or params.
"""

import os
import uuid
import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.main import app
from app.models import GUID, Farm, Farmer, IoTDevice, IoTSensorReading, FarmerDocument
from app.schemas import RegisterRequest
from app.services.crop_recommendation_service import normalize_crop_name
from app.services.ivr_service import handle_ivr_interaction

client = TestClient(app)


# =============================================================================
# Finding 1: IoTSensorReading Authoritative device_table_id Lookup
# =============================================================================
class TestFinding1FarmBrainIoTTelemetry:
    def test_current_linked_device_reading_included(self):
        """Telemetry must be matched using device_table_id corresponding to farm's IoTDevice."""
        mock_db = MagicMock()
        farm = Farm(id=1, name="My Farm", area=2.5)

        # Linked device
        linked_device = IoTDevice(id=10, farm_id=1, device_id="ESP-TEST-001")
        mock_db.query.return_value.filter.return_value.all.return_value = [linked_device]

        # The filter query should match device_table_id in [10]
        reading = IoTSensorReading(id=500, device_table_id=10, device_id="ESP-TEST-001", temperature=28.5)
        mock_db.query.return_value.filter.return_value.order_by.return_value.first.return_value = reading

        from app.routes.farm_brain import get_farm_brain_today
        user = MagicMock()
        user.id = "user-1"
        user.role = "FARMER"

        with patch("app.routes.farm_brain.get_authorized_farm", return_value=farm), \
             patch("app.routes.farm_brain._fetch_farm_weather", return_value={}), \
             patch("app.routes.farm_brain.generate_today_decisions", return_value={"decisions": []}) as mock_gen:
            get_farm_brain_today(farm_id=1, current_user=user, db=mock_db)
            # Verify latest_iot passed to generate_today_decisions is the reading with device_table_id=10
            assert mock_gen.call_args.kwargs.get("latest_iot") == reading

    def test_old_reading_with_different_table_id_excluded(self):
        """Old readings from same device_id but different device_table_id must NOT be queried."""
        mock_db = MagicMock()
        farm = Farm(id=1, name="My Farm", area=2.5)
        linked_device = IoTDevice(id=10, farm_id=1, device_id="REUSED-ESP")
        query_map = {}
        def mock_query(model):
            m = MagicMock()
            query_map[model] = m
            if model == IoTDevice:
                m.filter.return_value.all.return_value = [linked_device]
            elif model == IoTSensorReading:
                m.filter.return_value.order_by.return_value.first.return_value = None
            else:
                m.filter.return_value.order_by.return_value.first.return_value = None
                m.filter.return_value.order_by.return_value.limit.return_value.all.return_value = []
            return m
        mock_db.query.side_effect = mock_query

        from app.routes.farm_brain import get_farm_brain_today
        user = MagicMock()
        user.id = "user-1"
        user.role = "FARMER"

        with patch("app.routes.farm_brain.get_authorized_farm", return_value=farm), \
             patch("app.routes.farm_brain._fetch_farm_weather", return_value={}), \
             patch("app.routes.farm_brain.generate_today_decisions", return_value={"decisions": []}):
            get_farm_brain_today(farm_id=1, current_user=user, db=mock_db)

            # Check that the filter called on IoTSensorReading only used device_table_id
            assert IoTSensorReading in query_map
            filter_call = query_map[IoTSensorReading].filter.call_args
            filter_expr_str = str(filter_call[0][0])
            assert "device_table_id" in filter_expr_str
            assert "device_id" not in filter_expr_str

    def test_another_farm_readings_cannot_influence_farm_brain(self):
        """A farm with no linked devices retrieves no IoT telemetry."""
        mock_db = MagicMock()
        farm = Farm(id=2, name="Another Farm", area=3.0)
        mock_db.query.return_value.filter.return_value.all.return_value = []  # No devices for this farm

        from app.routes.farm_brain import get_farm_brain_today
        user = MagicMock()
        user.id = "user-2"
        user.role = "FARMER"

        with patch("app.routes.farm_brain.get_authorized_farm", return_value=farm), \
             patch("app.routes.farm_brain._fetch_farm_weather", return_value={}), \
             patch("app.routes.farm_brain.generate_today_decisions", return_value={"decisions": []}) as mock_gen:
            get_farm_brain_today(farm_id=2, current_user=user, db=mock_db)
            assert mock_gen.call_args.kwargs.get("latest_iot") is None


# =============================================================================
# Finding 2: Generic Safe Client Messages on Storage Vault Failures
# =============================================================================
class TestFinding2DocumentStorageErrorSanitization:
    @pytest.mark.anyio
    async def test_upload_storage_vault_failure_returns_safe_message(self):
        from app.routes.documents import upload_document

        mock_db = MagicMock()
        farmer = Farmer(id=1, user_id="user-123", mobile_number="1234567890", name="Farmer")
        farmer.maittri_farmer_id = "MT-FARM-000001"
        mock_db.query.return_value.filter.return_value.first.return_value = farmer

        current_user = MagicMock()
        current_user.id = "user-123"
        current_user.role = "FARMER"

        mock_file = MagicMock()
        mock_file.filename = "khasra.pdf"
        mock_file.read = AsyncMock(return_value=b"%PDF-1.4 sample content")
        mock_file.content_type = "application/pdf"

        mock_sb = MagicMock()
        # Internal exception with sensitive bucket details
        mock_sb.storage.from_.return_value.upload.side_effect = Exception(
            "Supabase Internal 500: could not connect to s3://secret-bucket-token@internal.supabase.co"
        )

        with patch("app.routes.documents.get_supabase_admin_client", return_value=mock_sb), \
             patch("app.routes.documents.logger") as mock_logger:
            with pytest.raises(HTTPException) as exc_info:
                await upload_document(
                    farmer_id=1,
                    document_name="Khasra Record",
                    category="Land Record",
                    file=mock_file,
                    current_user=current_user,
                    db=mock_db
                )
            assert exc_info.value.status_code == 502
            # Detail must be generic and NOT contain internal bucket details
            assert exc_info.value.detail == "Storage vault upload failed. Please try again later."
            assert "secret-bucket-token" not in exc_info.value.detail
            # Server-side logging must have captured the exception
            mock_logger.error.assert_called()

    def test_signed_url_failure_returns_safe_message(self):
        from app.routes.documents import get_signed_url

        mock_db = MagicMock()
        doc = FarmerDocument(
            id=10,
            farmer_id=1,
            document_name="Doc1",
            storage_path="user-123/doc1.pdf",
            uploaded_by_user_id="user-123"
        )
        farmer = Farmer(id=1, user_id="user-123")
        mock_db.query.return_value.filter.return_value.first.side_effect = [doc, farmer]

        current_user = MagicMock()
        current_user.id = "user-123"
        current_user.role = "FARMER"

        mock_sb = MagicMock()
        mock_sb.storage.from_.return_value.create_signed_url.side_effect = Exception(
            "PostgreSQL SSL failure: connection terminated with secret_key=xyz"
        )

        with patch("app.routes.documents.get_supabase_admin_client", return_value=mock_sb), \
             patch("app.routes.documents.logger") as mock_logger:
            with pytest.raises(HTTPException) as exc_info:
                get_signed_url(
                    doc_id=10,
                    expires_in=3600,
                    current_user=current_user,
                    db=mock_db
                )
            assert exc_info.value.status_code == 500
            assert exc_info.value.detail == "Failed to generate secure document URL."
            assert "secret_key" not in exc_info.value.detail
            mock_logger.error.assert_called()


# =============================================================================
# Finding 3: Orphaned Storage Object Cleanup on DB Commit Failure
# =============================================================================
class TestFinding3DocumentUploadCommitFailureCleanup:
    @pytest.mark.anyio
    async def test_storage_upload_succeeds_db_commit_succeeds_retains_object(self):
        from app.routes.documents import upload_document

        mock_db = MagicMock()
        farmer = Farmer(id=1, user_id="user-123", mobile_number="1234567890", name="Farmer")
        farmer.maittri_farmer_id = "MT-FARM-000001"
        mock_db.query.return_value.filter.return_value.first.return_value = farmer

        current_user = MagicMock()
        current_user.id = "user-123"
        current_user.role = "FARMER"

        mock_file = MagicMock()
        mock_file.filename = "khasra.pdf"
        mock_file.read = AsyncMock(return_value=b"%PDF-1.4 content")
        mock_file.content_type = "application/pdf"

        mock_sb = MagicMock()

        with patch("app.routes.documents.get_supabase_admin_client", return_value=mock_sb):
            res = await upload_document(
                farmer_id=1,
                document_name="Khasra",
                category="Land Record",
                file=mock_file,
                current_user=current_user,
                db=mock_db
            )
            assert "document_name" in res
            mock_sb.storage.from_.return_value.upload.assert_called_once()
            # remove must NOT be called on success
            mock_sb.storage.from_.return_value.remove.assert_not_called()

    @pytest.mark.anyio
    async def test_storage_upload_succeeds_db_commit_fails_cleans_up_storage(self):
        from app.routes.documents import upload_document

        mock_db = MagicMock()
        farmer = Farmer(id=1, user_id="user-123", mobile_number="1234567890", name="Farmer")
        farmer.maittri_farmer_id = "MT-FARM-000001"
        mock_db.query.return_value.filter.return_value.first.return_value = farmer

        # Simulate DB commit failure
        db_error = IntegrityError("INSERT INTO farmer_documents", {}, Exception("Duplicate key"))
        mock_db.commit.side_effect = db_error

        current_user = MagicMock()
        current_user.id = "user-123"
        current_user.role = "FARMER"

        mock_file = MagicMock()
        mock_file.filename = "khasra.pdf"
        mock_file.read = AsyncMock(return_value=b"%PDF-1.4 content")
        mock_file.content_type = "application/pdf"

        mock_sb = MagicMock()

        with patch("app.routes.documents.get_supabase_admin_client", return_value=mock_sb):
            with pytest.raises(IntegrityError):
                await upload_document(
                    farmer_id=1,
                    document_name="Khasra",
                    category="Land Record",
                    file=mock_file,
                    current_user=current_user,
                    db=mock_db
                )
            # Must attempt to clean up the uploaded storage object
            mock_sb.storage.from_.return_value.remove.assert_called_once()
            called_paths = mock_sb.storage.from_.return_value.remove.call_args[0][0]
            assert any("MT-FARM-000001" in p for p in called_paths)

    @pytest.mark.anyio
    async def test_cleanup_failure_logged_and_original_db_exception_preserved(self):
        from app.routes.documents import upload_document

        mock_db = MagicMock()
        farmer = Farmer(id=1, user_id="user-123", mobile_number="1234567890", name="Farmer")
        farmer.maittri_farmer_id = "MT-FARM-000001"
        mock_db.query.return_value.filter.return_value.first.return_value = farmer

        db_error = SQLAlchemyError("Database disk full")
        mock_db.commit.side_effect = db_error

        current_user = MagicMock()
        current_user.id = "user-123"
        current_user.role = "FARMER"

        mock_file = MagicMock()
        mock_file.filename = "khasra.pdf"
        mock_file.read = AsyncMock(return_value=b"%PDF-1.4 content")
        mock_file.content_type = "application/pdf"

        mock_sb = MagicMock()
        # Storage remove fails as well
        mock_sb.storage.from_.return_value.remove.side_effect = Exception("Storage network timeout")

        with patch("app.routes.documents.get_supabase_admin_client", return_value=mock_sb), \
             patch("app.routes.documents.logger") as mock_logger:
            with pytest.raises(SQLAlchemyError) as exc_info:
                await upload_document(
                    farmer_id=1,
                    document_name="Khasra",
                    category="Land Record",
                    file=mock_file,
                    current_user=current_user,
                    db=mock_db
                )
            assert exc_info.value == db_error
            # Verify cleanup error was logged
            mock_logger.error.assert_called()


# =============================================================================
# Finding 4: GUID TypeDecorator Validates UUID Format on PostgreSQL
# =============================================================================
class TestFinding4GUIDValidation:
    def setup_method(self):
        self.guid = GUID()
        self.pg_dialect = MagicMock()
        self.pg_dialect.name = "postgresql"
        self.sqlite_dialect = MagicMock()
        self.sqlite_dialect.name = "sqlite"

    def test_valid_uuid_string_accepted(self):
        valid_uuid_str = "12345678-1234-5678-1234-567812345678"
        result = self.guid.process_bind_param(valid_uuid_str, self.pg_dialect)
        assert result == valid_uuid_str

    def test_uuid_object_accepted(self):
        u = uuid.UUID("12345678-1234-5678-1234-567812345678")
        result = self.guid.process_bind_param(u, self.pg_dialect)
        assert result == str(u)

    def test_invalid_uuid_raises_value_error(self):
        with pytest.raises(ValueError, match="Invalid UUID value for GUID column"):
            self.guid.process_bind_param("not-a-valid-uuid-string", self.pg_dialect)

    def test_sqlite_dialect_accepts_strings(self):
        """SQLite dialect should allow string values without PostgreSQL UUID validation."""
        val = "legacy-string-identifier"
        result = self.guid.process_bind_param(val, self.sqlite_dialect)
        assert result == val

    def test_none_value_handled(self):
        assert self.guid.process_bind_param(None, self.pg_dialect) is None


# =============================================================================
# Finding 5: Auth Local Insert Requires Explicit Opt-In
# =============================================================================
class TestFinding5AuthLocalInsertOptIn:
    def test_dev_with_explicit_opt_in_allows_fallback(self):
        """In development with ALLOW_LOCAL_AUTH_INSERT=true, fallback SQL runs on Supabase error."""
        from app.routes.auth import register
        mock_db = MagicMock()
        mock_db.execute.return_value.first.return_value = None  # user does not exist in auth.users
        mock_db.query.return_value.filter.return_value.first.return_value = None

        mock_sb_admin = MagicMock()
        mock_sb_admin.auth.admin.create_user.side_effect = Exception("Supabase unreachable")

        payload = RegisterRequest(
            email="farmer1@example.com",
            password="StrongPassword123!",
            full_name="Farmer One",
            phone_number="9876543210"
        )

        with patch("app.routes.auth.engine") as mock_engine, \
             patch("app.routes.auth.get_supabase_admin_client", return_value=mock_sb_admin), \
             patch.dict(os.environ, {"ENVIRONMENT": "development", "ALLOW_LOCAL_AUTH_INSERT": "true"}):
            mock_engine.name = "postgresql"
            res = register(payload=payload, db=mock_db)
            assert "access_token" in res
            mock_db.execute.assert_called()

    def test_dev_without_opt_in_does_not_fallback(self):
        """In development without ALLOW_LOCAL_AUTH_INSERT, Supabase error raises 500."""
        from app.routes.auth import register
        mock_db = MagicMock()
        mock_db.execute.return_value.first.return_value = None

        mock_sb_admin = MagicMock()
        mock_sb_admin.auth.admin.create_user.side_effect = Exception("Supabase connection timeout")

        payload = RegisterRequest(
            email="farmer2@example.com",
            password="StrongPassword123!",
            full_name="Farmer Two",
            phone_number="9876543210"
        )

        with patch("app.routes.auth.engine") as mock_engine, \
             patch("app.routes.auth.get_supabase_admin_client", return_value=mock_sb_admin), \
             patch.dict(os.environ, {"ENVIRONMENT": "development", "ALLOW_LOCAL_AUTH_INSERT": "false"}):
            mock_engine.name = "postgresql"
            with pytest.raises(HTTPException) as exc_info:
                register(payload=payload, db=mock_db)
            assert exc_info.value.status_code == 500
            assert exc_info.value.detail == "Failed to register user in authoritative store."

    def test_test_env_without_opt_in_does_not_fallback(self):
        """In test environment without opt-in, Supabase error raises 500."""
        from app.routes.auth import register
        mock_db = MagicMock()
        mock_db.execute.return_value.first.return_value = None

        mock_sb_admin = MagicMock()
        mock_sb_admin.auth.admin.create_user.side_effect = Exception("Rate limit exceeded")

        payload = RegisterRequest(
            email="farmer3@example.com",
            password="StrongPassword123!",
            full_name="Farmer Three",
            phone_number="9876543210"
        )

        with patch("app.routes.auth.engine") as mock_engine, \
             patch("app.routes.auth.get_supabase_admin_client", return_value=mock_sb_admin), \
             patch.dict(os.environ, {"ENVIRONMENT": "test", "ALLOW_LOCAL_AUTH_INSERT": "false"}):
            mock_engine.name = "postgresql"
            with pytest.raises(HTTPException) as exc_info:
                register(payload=payload, db=mock_db)
            assert exc_info.value.status_code == 500

    def test_production_env_never_falls_back(self):
        """In production environment, fallback never occurs even if ALLOW_LOCAL_AUTH_INSERT is set."""
        from app.routes.auth import register
        mock_db = MagicMock()
        mock_db.execute.return_value.first.return_value = None

        mock_sb_admin = MagicMock()
        mock_sb_admin.auth.admin.create_user.side_effect = Exception("Supabase error")

        payload = RegisterRequest(
            email="farmer4@example.com",
            password="StrongPassword123!",
            full_name="Farmer Four",
            phone_number="9876543210"
        )

        with patch("app.routes.auth.engine") as mock_engine, \
             patch("app.routes.auth.get_supabase_admin_client", return_value=mock_sb_admin), \
             patch.dict(os.environ, {"ENVIRONMENT": "production", "ALLOW_LOCAL_AUTH_INSERT": "true"}):
            mock_engine.name = "postgresql"
            with pytest.raises(HTTPException) as exc_info:
                register(payload=payload, db=mock_db)
            assert exc_info.value.status_code == 500

    def test_production_failure_logs_exc_type_not_pii(self):
        """Production Supabase failure logs exc_type only — no email, password, or PII."""
        import logging
        from app.routes.auth import register

        mock_db = MagicMock()
        mock_db.execute.return_value.first.return_value = None

        mock_sb_admin = MagicMock()
        # Use an exception whose message contains a realistic Supabase error
        # that could inadvertently include user-supplied data if logged naively.
        exc_message = "Connection timeout reaching supabase endpoint"
        mock_sb_admin.auth.admin.create_user.side_effect = Exception(exc_message)

        payload = RegisterRequest(
            email="sensitiveuser@example.com",
            password="SuperSecret999!",
            full_name="Sensitive User",
            phone_number="9876543210"
        )

        log_records = []

        class CapturingHandler(logging.Handler):
            def emit(self, record):
                log_records.append(record)

        capturing = CapturingHandler()
        auth_logger = logging.getLogger("maitri.auth")
        auth_logger.addHandler(capturing)
        auth_logger.setLevel(logging.DEBUG)
        try:
            with patch("app.routes.auth.engine") as mock_engine, \
                 patch("app.routes.auth.get_supabase_admin_client", return_value=mock_sb_admin), \
                 patch.dict(os.environ, {"ENVIRONMENT": "production", "ALLOW_LOCAL_AUTH_INSERT": "false"}):
                mock_engine.name = "postgresql"
                with pytest.raises(HTTPException) as exc_info:
                    register(payload=payload, db=mock_db)
        finally:
            auth_logger.removeHandler(capturing)

        assert exc_info.value.status_code == 500
        assert exc_info.value.detail == "Failed to register user in authoritative store."

        # At least one log record must have been emitted
        assert log_records, "Expected at least one log record from maitri.auth on Supabase failure"

        # The log record must contain exc_type, but MUST NOT contain PII
        combined_log = " ".join(r.getMessage() for r in log_records)
        assert "Exception" in combined_log, "Log should include the exception type name"
        assert "sensitiveuser@example.com" not in combined_log, "Email must not appear in logs"
        assert "SuperSecret999!" not in combined_log, "Password must not appear in logs"

    def test_null_user_response_logs_and_returns_500(self):
        """If Supabase returns a response with no user object, a 500 is returned and logged."""
        import logging
        from app.routes.auth import register

        mock_db = MagicMock()
        mock_db.execute.return_value.first.return_value = None

        mock_sb_admin = MagicMock()
        # Simulate Supabase returning a response but with user=None
        null_response = MagicMock()
        null_response.user = None
        mock_sb_admin.auth.admin.create_user.return_value = null_response

        payload = RegisterRequest(
            email="nulluser@example.com",
            password="StrongPassword123!",
            full_name="Null User",
            phone_number="9876543210"
        )

        log_records = []

        class CapturingHandler(logging.Handler):
            def emit(self, record):
                log_records.append(record)

        capturing = CapturingHandler()
        auth_logger = logging.getLogger("maitri.auth")
        auth_logger.addHandler(capturing)
        auth_logger.setLevel(logging.DEBUG)
        try:
            with patch("app.routes.auth.engine") as mock_engine, \
                 patch("app.routes.auth.get_supabase_admin_client", return_value=mock_sb_admin), \
                 patch.dict(os.environ, {"ENVIRONMENT": "production"}):
                mock_engine.name = "postgresql"
                with pytest.raises(HTTPException) as exc_info:
                    register(payload=payload, db=mock_db)
        finally:
            auth_logger.removeHandler(capturing)

        assert exc_info.value.status_code == 500
        assert exc_info.value.detail == "Failed to register user in authoritative store."

        # Must log the NullUserResponse path
        combined_log = " ".join(r.getMessage() for r in log_records)
        assert "NullUserResponse" in combined_log
        assert "nulluser@example.com" not in combined_log
        assert "StrongPassword123!" not in combined_log

    def test_auth_api_error_logged_safely_with_status_and_message(self):
        """AuthApiError logs exc_type, status, code, and bounded message without leaking secrets."""
        import logging
        from app.routes.auth import register
        from supabase_auth.errors import AuthApiError

        mock_db = MagicMock()
        mock_db.execute.return_value.first.return_value = None

        mock_sb_admin = MagicMock()
        auth_error = AuthApiError(
            message="Email signup is disabled for this project",
            status=400,
            code="email_provider_disabled"
        )
        mock_sb_admin.auth.admin.create_user.side_effect = auth_error

        payload = RegisterRequest(
            email="farmer_test@example.com",
            password="SuperSecretPassword123!",
            full_name="Farmer Test",
            phone_number="9876543210"
        )

        log_records = []

        class CapturingHandler(logging.Handler):
            def emit(self, record):
                log_records.append(record)

        capturing = CapturingHandler()
        auth_logger = logging.getLogger("maitri.auth")
        auth_logger.addHandler(capturing)
        auth_logger.setLevel(logging.DEBUG)
        try:
            with patch("app.routes.auth.engine") as mock_engine, \
                 patch("app.routes.auth.get_supabase_admin_client", return_value=mock_sb_admin), \
                 patch.dict(os.environ, {"ENVIRONMENT": "production", "ALLOW_LOCAL_AUTH_INSERT": "false"}):
                mock_engine.name = "postgresql"
                with pytest.raises(HTTPException) as exc_info:
                    register(payload=payload, db=mock_db)
        finally:
            auth_logger.removeHandler(capturing)

        assert exc_info.value.status_code == 500
        assert exc_info.value.detail == "Failed to register user in authoritative store."

        assert log_records, "Expected at least one log record from maitri.auth on Supabase failure"
        combined_log = " ".join(r.getMessage() for r in log_records)
        assert "exc_type=AuthApiError" in combined_log
        assert "status=400" in combined_log
        assert "[email_provider_disabled]" in combined_log
        assert "Email signup is disabled" in combined_log
        assert "stage=supabase_create_user" in combined_log
        assert "SuperSecretPassword123!" not in combined_log
        assert "farmer_test@example.com" not in combined_log


# =============================================================================
# Finding 6: Crop Recommendation Pea & Compound Aliasing
# =============================================================================
class TestFinding6CropRecommendationPeaAliasing:
    def test_chick_pea_maps_to_gram_chickpea(self):
        assert normalize_crop_name("chick pea") == "Gram/Chickpea"

    def test_chickpea_maps_to_gram_chickpea(self):
        assert normalize_crop_name("chickpea") == "Gram/Chickpea"

    def test_pigeon_pea_maps_to_red_gram(self):
        assert normalize_crop_name("pigeon pea") == "Red Gram"

    def test_pigeonpea_maps_to_red_gram(self):
        assert normalize_crop_name("pigeonpea") == "Red Gram"

    def test_pea_alone_maps_to_pea(self):
        assert normalize_crop_name("pea") == "Pea"

    def test_red_gram_maps_to_red_gram(self):
        assert normalize_crop_name("red gram") == "Red Gram"

    def test_black_gram_maps_to_black_gram(self):
        assert normalize_crop_name("black gram") == "Black Gram"

    def test_green_gram_maps_to_green_gram(self):
        assert normalize_crop_name("green gram") == "Green Gram"


# =============================================================================
# Finding 7: IVR Weather Live Data vs Safe Unavailable
# =============================================================================
class TestFinding7IVRWeatherAuthenticData:
    def test_valid_weather_data_reported(self):
        """When valid weather data is available, IVR reports actual temperature and condition."""
        mock_db = MagicMock()
        farmer = Farmer(id=1, mobile_number="9876543210", district="Meerut")
        farm = Farm(id=1, farmer_id=1, latitude=28.98, longitude=77.70, location_name="Meerut Field")
        mock_db.query.return_value.filter.return_value.first.side_effect = [farmer, farm, None]

        weather_res = {
            "current": {"temperature": 31.5, "condition": "साफ मौसम"},
            "daily_forecast": [{"temp_min": 24.0, "temp_max": 33.0}],
            "advisories": []
        }

        with patch("app.routes.weather.fetch_weather_data", return_value=weather_res):
            res = handle_ivr_interaction(
                db=mock_db,
                session_id="IVR-TEST-W1",
                phone_number="9876543210",
                digits_pressed="2",
                current_menu="main",
                language="hi"
            )
            # Response must report actual weather and temperature
            assert "31" in res["audio_text_hi"] or "33" in res["audio_text_hi"]
            assert "22 से 28" not in res["audio_text_hi"]  # Must not use fake hardcoded 22-28 range

    def test_weather_with_severe_alert_reports_alert(self):
        """When advisories contain severe storm alert, alert is communicated."""
        mock_db = MagicMock()
        farmer = Farmer(id=1, mobile_number="9876543210", district="Agra")
        farm = Farm(id=1, farmer_id=1, latitude=27.18, longitude=78.01)
        mock_db.query.return_value.filter.return_value.first.side_effect = [farmer, farm, None]

        weather_res = {
            "current": {"temperature": 29.0, "condition": "तूफानी बारिश"},
            "daily_forecast": [{"temp_min": 22.0, "temp_max": 30.0}],
            "advisories": ["Severe thunderstorm and heavy rain alert for your area"]
        }

        with patch("app.routes.weather.fetch_weather_data", return_value=weather_res):
            res = handle_ivr_interaction(
                db=mock_db,
                session_id="IVR-TEST-W2",
                phone_number="9876543210",
                digits_pressed="2",
                current_menu="main",
                language="en"
            )
            assert "alert" in res["audio_text_en"].lower()

    def test_weather_unavailable_reports_safe_message(self):
        """When weather fetch fails, IVR explicitly reports unavailable, never fake values."""
        mock_db = MagicMock()
        farmer = Farmer(id=1, mobile_number="9876543210", district="Bareilly")
        farm = Farm(id=1, farmer_id=1, latitude=28.36, longitude=79.41)
        mock_db.query.return_value.filter.return_value.first.side_effect = [farmer, farm, None]

        with patch("app.routes.weather.fetch_weather_data", side_effect=Exception("API timeout")):
            res = handle_ivr_interaction(
                db=mock_db,
                session_id="IVR-TEST-W3",
                phone_number="9876543210",
                digits_pressed="2",
                current_menu="main",
                language="hi"
            )
            assert "उपलब्ध नहीं है" in res["audio_text_hi"]
            assert "22 से 28" not in res["audio_text_hi"]

    def test_no_location_farm_reports_unavailable(self):
        """When farmer has no farm coordinates, safe unavailable message is returned."""
        mock_db = MagicMock()
        farmer = Farmer(id=1, mobile_number="9876543210", district=None)
        mock_db.query.return_value.filter.return_value.first.side_effect = [farmer, None, None]

        res = handle_ivr_interaction(
            db=mock_db,
            session_id="IVR-TEST-W4",
            phone_number="9876543210",
            digits_pressed="2",
            current_menu="main",
            language="en"
        )
        assert "unavailable" in res["audio_text_en"].lower()
        assert "22 to 28" not in res["audio_text_en"]


# =============================================================================
# Finding 8: IVR Guided Pest Step 1 Input Validation
# =============================================================================
class TestFinding8IVRPestSelectionValidation:
    def test_valid_selection_1_returns_fungal_rust(self):
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = None
        res = handle_ivr_interaction(
            db=mock_db,
            session_id="IVR-PEST-1",
            phone_number="9876543210",
            digits_pressed="1",
            current_menu="pest_step_1",
            language="en"
        )
        assert "Fungal Rust" in res["audio_text_en"]
        assert res["current_menu"] == "action_done"

    def test_valid_selection_2_returns_aphid_infestation(self):
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = None
        res = handle_ivr_interaction(
            db=mock_db,
            session_id="IVR-PEST-2",
            phone_number="9876543210",
            digits_pressed="2",
            current_menu="pest_step_1",
            language="en"
        )
        assert "Aphid" in res["audio_text_en"] or "Caterpillar" in res["audio_text_en"]
        assert res["current_menu"] == "action_done"

    def test_valid_selection_3_returns_root_rot(self):
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = None
        res = handle_ivr_interaction(
            db=mock_db,
            session_id="IVR-PEST-3",
            phone_number="9876543210",
            digits_pressed="3",
            current_menu="pest_step_1",
            language="en"
        )
        assert "Root rot" in res["audio_text_en"]
        assert res["current_menu"] == "action_done"

    def test_invalid_0_does_not_diagnose_root_rot(self):
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = None
        res = handle_ivr_interaction(
            db=mock_db,
            session_id="IVR-PEST-0",
            phone_number="9876543210",
            digits_pressed="0",
            current_menu="pest_step_1",
            language="en"
        )
        assert "Root rot" not in res["audio_text_en"]
        assert "Invalid selection" in res["audio_text_en"]
        assert res["current_menu"] == "pest_step_1"

    def test_invalid_9_does_not_diagnose_root_rot(self):
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = None
        res = handle_ivr_interaction(
            db=mock_db,
            session_id="IVR-PEST-9",
            phone_number="9876543210",
            digits_pressed="9",
            current_menu="pest_step_1",
            language="en"
        )
        assert "Root rot" not in res["audio_text_en"]
        # In Round 6 Finding 9, 9 returns to main menu
        assert res["current_menu"] == "main"

    def test_invalid_digit_does_not_diagnose_root_rot(self):
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = None
        res = handle_ivr_interaction(
            db=mock_db,
            session_id="IVR-PEST-4",
            phone_number="9876543210",
            digits_pressed="4",
            current_menu="pest_step_1",
            language="en"
        )
        assert "Root rot" not in res["audio_text_en"]
        assert "Invalid selection" in res["audio_text_en"]
        assert res["current_menu"] == "pest_step_1"

    def test_missing_input_does_not_diagnose_root_rot(self):
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = None
        res = handle_ivr_interaction(
            db=mock_db,
            session_id="IVR-PEST-NONE",
            phone_number="9876543210",
            digits_pressed="",
            current_menu="pest_step_1",
            language="en"
        )
        assert "Root rot" not in res["audio_text_en"]
        assert "Invalid selection" in res["audio_text_en"]
        assert res["current_menu"] == "pest_step_1"

    def test_arbitrary_unsupported_digit_does_not_diagnose_root_rot(self):
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = None
        res = handle_ivr_interaction(
            db=mock_db,
            session_id="IVR-PEST-ARB",
            phone_number="9876543210",
            digits_pressed="7",
            current_menu="pest_step_1",
            language="hi"
        )
        assert "जड़ गलन" not in res["audio_text_hi"]
        assert "अमान्य विकल्प" in res["audio_text_hi"]
        assert res["current_menu"] == "pest_step_1"


# =============================================================================
# Finding 9: IVR Market Price Authentic Lookup
# =============================================================================
class TestFinding9IVRMarketPriceAuthenticLookup:
    def test_existing_crop_with_available_market_data(self):
        mock_db = MagicMock()
        farmer = Farmer(id=1, mobile_number="9876543210", current_crop="Wheat", state="Uttar Pradesh", district="Meerut")
        farm = Farm(id=1, farmer_id=1, current_crop="Wheat")
        mock_db.query.return_value.filter.return_value.first.side_effect = [farmer, farm, None]

        price_data = {
            "crop": "Wheat",
            "market": "Meerut Mandi",
            "price": {"modal": 2420, "unit": "quintal"},
            "source": "Agmarknet Mandi Feed",
            "date": "03-10-2026"
        }

        with patch("app.services.market_price_service.get_latest_market_price", return_value=price_data):
            res = handle_ivr_interaction(
                db=mock_db,
                session_id="IVR-MKT-1",
                phone_number="9876543210",
                digits_pressed="5",
                current_menu="main",
                language="hi"
            )
            assert "2420" in res["audio_text_hi"]
            assert "Wheat" in res["audio_text_hi"] or "गेहूं" in res["audio_text_hi"] or "Meerut Mandi" in res["audio_text_hi"]

    def test_different_crop_not_wheat_mustard_fallback(self):
        """Farmer registered with Soybean must NOT receive hardcoded Wheat Rs 2350 / Mustard Rs 5400."""
        mock_db = MagicMock()
        farmer = Farmer(id=1, mobile_number="9876543210", current_crop="Soybean", state="Madhya Pradesh")
        farm = Farm(id=1, farmer_id=1, current_crop="Soybean")
        mock_db.query.return_value.filter.return_value.first.side_effect = [farmer, farm, None]

        price_data = {
            "crop": "Soybean",
            "market": "Indore Mandi",
            "price": {"modal": 4650, "unit": "quintal"},
            "source": "State Mandi Board",
            "date": "03-10-2026"
        }

        with patch("app.services.market_price_service.get_latest_market_price", return_value=price_data):
            res = handle_ivr_interaction(
                db=mock_db,
                session_id="IVR-MKT-2",
                phone_number="9876543210",
                digits_pressed="5",
                current_menu="main",
                language="en"
            )
            assert "Soybean" in res["audio_text_en"]
            assert "4650" in res["audio_text_en"]
            # Must NOT report wheat 2350 or mustard 5400
            assert "2350" not in res["audio_text_en"]
            assert "5400" not in res["audio_text_en"]

    def test_no_market_data_reports_unavailable(self):
        """When market data is unavailable, IVR explicitly reports unavailable."""
        mock_db = MagicMock()
        farmer = Farmer(id=1, mobile_number="9876543210", current_crop="Dragonfruit")
        farm = Farm(id=1, farmer_id=1, current_crop="Dragonfruit")
        mock_db.query.return_value.filter.return_value.first.side_effect = [farmer, farm, None]

        with patch("app.services.market_price_service.get_latest_market_price", return_value=None):
            res = handle_ivr_interaction(
                db=mock_db,
                session_id="IVR-MKT-3",
                phone_number="9876543210",
                digits_pressed="5",
                current_menu="main",
                language="en"
            )
            assert "unavailable" in res["audio_text_en"].lower()
            assert "2350" not in res["audio_text_en"]

    def test_no_claim_of_latest_verified_without_source(self):
        """When no crop is registered, safe unavailable response is returned without fake claims."""
        mock_db = MagicMock()
        farmer = Farmer(id=1, mobile_number="9876543210", current_crop=None)
        mock_db.query.return_value.filter.return_value.first.side_effect = [farmer, None, None]

        res = handle_ivr_interaction(
            db=mock_db,
            session_id="IVR-MKT-4",
            phone_number="9876543210",
            digits_pressed="5",
            current_menu="main",
            language="en"
        )
        assert "unavailable" in res["audio_text_en"].lower()
        assert "2350" not in res["audio_text_en"]


# =============================================================================
# Finding 10: IntegrityError Logging Sanity
# =============================================================================
class TestFinding10IntegrityErrorLogging:
    @pytest.mark.anyio
    async def test_integrity_error_handler_409_status_and_sanitized_logging(self):
        from app.main import integrity_error_handler

        mock_request = MagicMock()
        # Simulated IntegrityError containing SQL statement and sensitive parameters
        statement = "INSERT INTO users (email, phone) VALUES ('secret_farmer@gmail.com', '9876543210')"
        params = {"email": "secret_farmer@gmail.com", "phone": "9876543210"}
        exc = IntegrityError(statement, params, Exception("UNIQUE constraint failed: users.email"))

        with patch("app.main.logger") as mock_logger:
            response = await integrity_error_handler(mock_request, exc)
            assert response.status_code == 409
            body = response.body.decode("utf-8")
            assert "A database uniqueness or integrity constraint was violated." in body
            assert "secret_farmer@gmail.com" not in body

            # Verify logger was called with exc.__class__.__name__ and not the raw exception
            mock_logger.warning.assert_called_once()
            log_args = mock_logger.warning.call_args[0]
            assert "IntegrityError" in log_args[1]
            # Ensure the raw SQL and params were not in the log message
            assert "secret_farmer@gmail.com" not in str(log_args)
            assert "INSERT INTO" not in str(log_args)


class TestDatabaseErrorSanitizedLogging:
    def test_sanitize_db_error_strips_sql_and_parameters(self):
        from app.database import sanitize_db_error
        from sqlalchemy.exc import ProgrammingError

        statement = "INSERT INTO nutrient_analyses (farm_id, user_id, analysis_json) VALUES (1, 'secret-uid', 'sensitive_data')"
        params = {"farm_id": 1, "user_id": "secret-uid", "analysis_json": "sensitive_data"}
        orig_err = Exception('column "analysis_json" is of type jsonb but expression is of type character varying')
        exc = ProgrammingError(statement, params, orig_err)

        sanitized = sanitize_db_error(exc)
        assert 'column "analysis_json" is of type jsonb but expression is of type character varying' in sanitized
        assert "sensitive_data" not in sanitized
        assert "secret-uid" not in sanitized
        assert "INSERT INTO" not in sanitized

    @pytest.mark.anyio
    async def test_database_error_handler_sanitized_logging(self):
        from app.main import database_error_handler
        from sqlalchemy.exc import ProgrammingError

        mock_request = MagicMock()
        statement = "INSERT INTO test (secret) VALUES ('secret_value')"
        params = {"secret": "secret_value"}
        orig_err = Exception('column "analysis_json" is of type jsonb but expression is of type character varying')
        exc = ProgrammingError(statement, params, orig_err)

        with patch("app.main.logger") as mock_logger:
            response = await database_error_handler(mock_request, exc)
            assert response.status_code == 503
            mock_logger.error.assert_called_once()
            log_str = str(mock_logger.error.call_args)
            assert "ProgrammingError" in log_str
            assert 'column "analysis_json" is of type jsonb' in log_str
            assert "secret_value" not in log_str
            assert "INSERT INTO" not in log_str
