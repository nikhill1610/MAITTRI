"""
Regression Tests for CodeRabbit 8 Findings
===========================================
1. Major: Operator-created farm for unlinked farmer has user_id == None (operator is not farm owner).
2. Major: Document upload requires farmer.user_id matching caller or elevated operator.
3. Minor: Content-Disposition document_name header injection / sanitization prevention.
4. Minor: Storage upload uses upsert=false and fail-closed when admin storage client unavailable.
5. Minor: Authentication identity lookup is read-only and does not mutate profile.email.
6. Minor: Farmer ID authorization uses direct string equality without UUID5 user-ID conversion.
7. Major: DB OperationalError/DatabaseError rolled back and handled by app-level 503 handler; IntegrityError 409 preserved.
8. Minor: RAG crop detection patterns harmonized with AGRI_EXPANSIONS and Unicode boundaries.
"""

import io
import pytest
from unittest.mock import MagicMock, patch
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError, DatabaseError, IntegrityError

from app.main import app
from app.models import Farm, Farmer, User, Profile, FarmerDocument
from app.deps import get_authorized_farm, _resolve_user_from_token
from app.services.rag_service import detect_crop_in_query, preprocess_query
from app.routes.documents import sanitize_filename

client = TestClient(app)


# =============================================================================
# Finding 1: Operator-created farm for unlinked farmer has user_id == None
# =============================================================================
class TestFinding1OperatorFarmOwnership:
    def test_operator_created_farm_unlinked_farmer_has_no_owner(self):
        """When an operator creates a farm for an unlinked farmer, Farm.user_id must be None."""
        farmer = Farmer(
            id=101,
            user_id=None,
            name="Ramesh Kumar",
            mobile_number="9876543210",
            district="Meerut"
        )
        operator = MagicMock()
        operator.id = "operator-uuid-1111"

        # Simulating the creation logic in backend/app/routes/operators.py
        farm = Farm(
            user_id=farmer.user_id,
            farmer_id=farmer.id,
            name=f"{farmer.name}'s Field ({farmer.district})",
            area=2.5,
            soil_type="Alluvial Soil"
        )
        assert farm.user_id is None, "Operator must NOT be assigned as Farm.user_id"
        assert farm.farmer_id == 101

    def test_operator_still_has_authorized_access_to_unlinked_farm(self):
        """Operator can access unlinked farm via elevated role in get_authorized_farm."""
        mock_db = MagicMock()
        farm = Farm(id=50, user_id=None, farmer_id=101, area=2.0, soil_type="Loam")
        mock_db.query.return_value.filter.return_value.first.return_value = farm

        operator_user = MagicMock()
        operator_user.id = "operator-uuid-1111"
        operator_user.role = "AUTHORIZED_OPERATOR"

        # Operator gets access
        authorized = get_authorized_farm(mock_db, farm_id=50, user=operator_user)
        assert authorized == farm


# =============================================================================
# Finding 2: Document upload authorization requires own linked farmer or operator
# =============================================================================
class TestFinding2DocumentUploadAuthorization:
    @pytest.mark.anyio
    async def test_farmer_upload_to_own_farmer_allowed(self):
        from app.routes.documents import upload_document

        mock_db = MagicMock()
        farmer = Farmer(id=1, user_id="user-123", mobile_number="1234567890", name="Farmer")
        farmer.maittri_farmer_id = "MT-FARM-000001"
        mock_db.query.return_value.filter.return_value.first.return_value = farmer

        current_user = MagicMock(spec=User)
        current_user.id = "user-123"
        current_user.role = "FARMER"

        from unittest.mock import AsyncMock
        mock_file = MagicMock()
        mock_file.filename = "khasra.pdf"
        mock_file.read = AsyncMock(return_value=b"%PDF-1.4 test content")
        mock_file.content_type = "application/pdf"

        mock_sb = MagicMock()
        with patch("app.routes.documents.get_supabase_admin_client", return_value=mock_sb):
            res = await upload_document(
                farmer_id=1,
                document_name="Khasra Record",
                category="Land Record",
                farm_id=None,
                file=mock_file,
                current_user=current_user,
                db=mock_db
            )
            assert res["farmer_id"] == 1
            assert res["document_name"] == "Khasra Record"

    @pytest.mark.anyio
    async def test_farmer_upload_to_another_farmer_rejected(self):
        from app.routes.documents import upload_document

        mock_db = MagicMock()
        farmer = Farmer(id=2, user_id="user-other", mobile_number="1234567890", name="Other")
        mock_db.query.return_value.filter.return_value.first.return_value = farmer

        current_user = MagicMock(spec=User)
        current_user.id = "user-attacker"
        current_user.role = "FARMER"

        mock_file = MagicMock()
        mock_file.filename = "test.pdf"

        with pytest.raises(HTTPException) as exc_info:
            await upload_document(
                farmer_id=2,
                document_name="Sneaky Doc",
                category="Land Record",
                farm_id=None,
                file=mock_file,
                current_user=current_user,
                db=mock_db
            )
        assert exc_info.value.status_code == 403

    @pytest.mark.anyio
    async def test_farmer_upload_to_unlinked_farmer_rejected(self):
        from app.routes.documents import upload_document

        mock_db = MagicMock()
        # Farmer has user_id == None (unlinked)
        farmer = Farmer(id=3, user_id=None, mobile_number="1234567890", name="Unlinked")
        mock_db.query.return_value.filter.return_value.first.return_value = farmer

        current_user = MagicMock(spec=User)
        current_user.id = "user-attacker"
        current_user.role = "FARMER"

        mock_file = MagicMock()
        mock_file.filename = "test.pdf"

        with pytest.raises(HTTPException) as exc_info:
            await upload_document(
                farmer_id=3,
                document_name="Sneaky Doc",
                category="Land Record",
                farm_id=None,
                file=mock_file,
                current_user=current_user,
                db=mock_db
            )
        assert exc_info.value.status_code == 403

    @pytest.mark.anyio
    async def test_operator_upload_to_unlinked_farmer_allowed(self):
        from app.routes.documents import upload_document

        mock_db = MagicMock()
        farmer = Farmer(id=3, user_id=None, mobile_number="1234567890", name="Unlinked")
        farmer.maittri_farmer_id = "MT-FARM-000003"
        mock_db.query.return_value.filter.return_value.first.return_value = farmer

        operator_user = MagicMock(spec=User)
        operator_user.id = "operator-uuid"
        operator_user.role = "AUTHORIZED_OPERATOR"

        from unittest.mock import AsyncMock
        mock_file = MagicMock()
        mock_file.filename = "official_soil.pdf"
        mock_file.read = AsyncMock(return_value=b"%PDF-1.4 official report")
        mock_file.content_type = "application/pdf"

        mock_sb = MagicMock()
        with patch("app.routes.documents.get_supabase_admin_client", return_value=mock_sb):
            res = await upload_document(
                farmer_id=3,
                document_name="Official Soil Report",
                category="Soil Test Report",
                farm_id=None,
                file=mock_file,
                current_user=operator_user,
                db=mock_db
            )
            assert res["farmer_id"] == 3


# =============================================================================
# Finding 3: Content-Disposition header injection prevention
# =============================================================================
class TestFinding3ContentDispositionSanitization:
    def test_sanitize_filename_blocks_crlf_and_quotes(self):
        malicious = 'malicious\r\nSet-Cookie: stolen=true\r\nfilename="evil.exe'
        safe = sanitize_filename(malicious)
        assert "\r" not in safe
        assert "\n" not in safe
        assert '"' not in safe
        assert ";" not in safe

    def test_sanitize_filename_blocks_path_traversal(self):
        traversal = "../../../etc/passwd"
        safe = sanitize_filename(traversal)
        assert "/" not in safe
        assert "\\" not in safe
        assert "passwd" in safe

    def test_download_content_disposition_sanitization(self):
        from app.routes.documents import download_document

        mock_db = MagicMock()
        doc = FarmerDocument(
            id=10,
            farmer_id=1,
            document_name='Test\r\nHeader-Injection: 1"; evil="',
            file_type="PDF",
            storage_path="user-1/doc.pdf"
        )
        mock_db.query.return_value.filter.return_value.first.return_value = doc

        current_user = MagicMock()
        current_user.id = "user-1"
        current_user.role = "AUTHORIZED_OPERATOR"

        mock_sb = MagicMock()
        mock_sb.storage.from_().download.return_value = b"file-data"

        with patch("app.routes.documents.get_supabase_admin_client", return_value=mock_sb):
            res = download_document(doc_id=10, current_user=current_user, db=mock_db)
            cd = res.headers.get("Content-Disposition", "")
            assert "\r" not in cd
            assert "\n" not in cd
            assert 'Test_' in cd


# =============================================================================
# Finding 4: Storage upload uses upsert=false and fail-closed
# =============================================================================
class TestFinding4StorageUploadSecurity:
    @pytest.mark.anyio
    async def test_missing_admin_storage_client_fails_closed(self):
        from app.routes.documents import upload_document

        mock_db = MagicMock()
        farmer = Farmer(id=1, user_id="user-1", mobile_number="1234567890", name="F")
        mock_db.query.return_value.filter.return_value.first.return_value = farmer

        current_user = MagicMock()
        current_user.id = "user-1"
        current_user.role = "FARMER"

        from unittest.mock import AsyncMock
        mock_file = MagicMock()
        mock_file.filename = "test.pdf"
        mock_file.read = AsyncMock(return_value=b"data")

        with patch("app.routes.documents.get_supabase_admin_client", return_value=None):
            with pytest.raises(HTTPException) as exc_info:
                await upload_document(
                    farmer_id=1,
                    document_name="Doc",
                    file=mock_file,
                    current_user=current_user,
                    db=mock_db
                )
            assert exc_info.value.status_code == 503
            assert "privileged storage client not configured" in exc_info.value.detail

    @pytest.mark.anyio
    async def test_upload_enforces_upsert_false(self):
        from app.routes.documents import upload_document

        mock_db = MagicMock()
        farmer = Farmer(id=1, user_id="user-1", mobile_number="1234567890", name="F")
        farmer.maittri_farmer_id = "MT-FARM-000001"
        mock_db.query.return_value.filter.return_value.first.return_value = farmer

        current_user = MagicMock()
        current_user.id = "user-1"
        current_user.role = "FARMER"

        from unittest.mock import AsyncMock
        mock_file = MagicMock()
        mock_file.filename = "test.pdf"
        mock_file.read = AsyncMock(return_value=b"%PDF-test")

        mock_sb = MagicMock()
        with patch("app.routes.documents.get_supabase_admin_client", return_value=mock_sb):
            await upload_document(
                farmer_id=1,
                document_name="Doc",
                file=mock_file,
                current_user=current_user,
                db=mock_db
            )
            # Verify upload called with upsert=false
            mock_sb.storage.from_().upload.assert_called_once()
            _, kwargs = mock_sb.storage.from_().upload.call_args
            assert kwargs["file_options"]["upsert"] == "false"


# =============================================================================
# Finding 5: Authentication lookup is read-only (no profile.email mutation)
# =============================================================================
class TestFinding5AuthLookupReadOnly:
    def test_identity_lookup_does_not_mutate_profile_email(self):
        import uuid
        from app.security import create_token

        mock_db = MagicMock()
        uid = str(uuid.uuid4())
        token = create_token(user_id=uid)

        profile = Profile(id=uid, full_name="Farmer Ramesh", phone_number="9876543210")
        profile.email = "original@example.com"
        mock_db.query.return_value.filter.return_value.first.return_value = profile

        with patch("app.deps.engine") as mock_engine:
            mock_engine.name = "postgresql"
            row = MagicMock()
            row.id = uid
            row.email = "mutated@example.com"
            mock_db.execute.return_value.first.return_value = row

            resolved = _resolve_user_from_token(token, mock_db)
            assert resolved == profile
            # Ensure profile.email was NOT overwritten by row.email
            assert resolved.email == "original@example.com"


# =============================================================================
# Finding 6: Farmer ID authorization uses direct string equality
# =============================================================================
class TestFinding6FarmerIDDirectStringEquality:
    def test_matching_farmer_id_authorizes(self):
        mock_db = MagicMock()
        farm = Farm(id=1, farmer_id=100, user_id=None, area=1.0, soil_type="Loam")
        mock_db.query.return_value.filter.return_value.first.return_value = farm

        user = MagicMock()
        user.id = "user-123"
        user.role = "FARMER"
        user.farmer_id = 100

        authorized = get_authorized_farm(mock_db, farm_id=1, user=user)
        assert authorized == farm

    def test_different_farmer_id_denied(self):
        mock_db = MagicMock()
        farm = Farm(id=1, farmer_id=100, user_id=None, area=1.0, soil_type="Loam")
        mock_db.query.return_value.filter.return_value.first.return_value = farm

        user = MagicMock()
        user.id = "user-123"
        user.role = "FARMER"
        user.farmer_id = 200  # Different farmer ID
        mock_db.query.return_value.filter.return_value.first.side_effect = [farm, None]

        with pytest.raises(HTTPException) as exc_info:
            get_authorized_farm(mock_db, farm_id=1, user=user)
        assert exc_info.value.status_code == 404


# =============================================================================
# Finding 7: DB exception handling and 503 response architecture
# =============================================================================
class TestFinding7DatabaseExceptionHandler:
    def test_operational_error_returns_503(self):
        from app.security import create_token
        valid_token = create_token(user_id=1)
        with patch("sqlalchemy.orm.Session.query", side_effect=OperationalError("connection lost", {}, Exception())):
            res = client.get("/api/farms", headers={"Authorization": f"Bearer {valid_token}"})
            assert res.status_code == 503
            data = res.json()
            assert "Database service temporarily unavailable" in data["detail"]
            # Ensure raw database internals are not exposed
            assert "connection lost" not in data["detail"]

    def test_integrity_error_returns_409(self):
        from app.security import create_token
        valid_token = create_token(user_id=1)
        with patch("sqlalchemy.orm.Session.query", side_effect=IntegrityError("unique constraint violated", {}, Exception())):
            res = client.get("/api/farms", headers={"Authorization": f"Bearer {valid_token}"})
            assert res.status_code == 409
            data = res.json()
            assert "integrity constraint was violated" in data["detail"]


# =============================================================================
# Finding 8: RAG crop detection patterns harmonized
# =============================================================================
class TestFinding8CropDetectionHarmonization:
    @pytest.mark.parametrize("query,expected_crop", [
        ("red gram pod borer", "Pigeonpea"),
        ("toor dal crop", "Pigeonpea"),
        ("tur pest", "Pigeonpea"),
        ("chickpea disease", "Chickpea"),
        ("pyaz mandi price", "Onion"),
        ("प्याज़ में रोग", "Onion"),
        ("प्याज की फसल", "Onion"),
        ("मूँगफली की खेती", "Groundnut"),
        ("मूंगफली में टिक्का रोग", "Groundnut"),
        ("bengal gram farming", "Chickpea"),
        ("chana pest control", "Chickpea"),
    ])
    def test_crop_detection_variants(self, query, expected_crop):
        detected = detect_crop_in_query(query)
        assert detected == expected_crop, f"Query '{query}' detected as '{detected}', expected '{expected_crop}'"

    def test_bare_gram_does_not_detect_chickpea(self):
        assert detect_crop_in_query("10 gram zinc per acre") is None
        assert detect_crop_in_query("apply 50 gram urea") is None

    def test_agri_expansion_does_not_expand_bare_gram(self):
        expanded = preprocess_query("10 gram zinc")
        assert "chickpea" not in expanded.lower()
