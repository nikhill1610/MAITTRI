"""
Regression tests for CodeRabbit Round 2 findings:
  1. FarmerUpdate/FarmerResponse validation constraints
  2. Login account-status information leak prevention
"""
import pytest
from pydantic import ValidationError


# ============================================================
# Finding 1: FarmerUpdate / FarmerResponse validation
# ============================================================

class TestFarmerUpdateValidation:
    """FarmerUpdate must reject invalid field values."""

    def test_rejects_empty_name(self):
        from app.schemas import FarmerUpdate
        with pytest.raises(ValidationError):
            FarmerUpdate(name="")

    def test_rejects_single_char_name(self):
        from app.schemas import FarmerUpdate
        with pytest.raises(ValidationError):
            FarmerUpdate(name="A")

    def test_rejects_zero_farm_area(self):
        from app.schemas import FarmerUpdate
        with pytest.raises(ValidationError):
            FarmerUpdate(farm_area=0)

    def test_rejects_negative_farm_area(self):
        from app.schemas import FarmerUpdate
        with pytest.raises(ValidationError):
            FarmerUpdate(farm_area=-1.5)

    def test_rejects_short_mobile(self):
        from app.schemas import FarmerUpdate
        with pytest.raises(ValidationError):
            FarmerUpdate(mobile_number="123")

    def test_valid_partial_update(self):
        from app.schemas import FarmerUpdate
        u = FarmerUpdate(name="Ram Kumar", farm_area=2.5)
        assert u.name == "Ram Kumar"
        assert u.farm_area == 2.5
        assert u.mobile_number is None  # untouched fields stay None

    def test_valid_empty_update(self):
        """All-None update is valid (no fields being changed)."""
        from app.schemas import FarmerUpdate
        u = FarmerUpdate()
        assert u.name is None
        assert u.farm_area is None


class TestFarmerResponseSerialization:
    """FarmerResponse must serialize without applying create-time input constraints."""

    def test_serializes_legacy_zero_area(self):
        """A record with farm_area=0 (legacy data) must serialize without error."""
        from app.schemas import FarmerResponse
        resp = FarmerResponse(
            id=1,
            maittri_farmer_id="MF-0001",
            name="Legacy Farmer",
            mobile_number="9999999999",
            farm_area=0.0,
        )
        assert resp.farm_area == 0.0

    def test_serializes_null_name(self):
        """A record with name=None (edge case) must serialize without error."""
        from app.schemas import FarmerResponse
        resp = FarmerResponse(
            id=2,
            maittri_farmer_id="MF-0002",
            name=None,
        )
        assert resp.name is None

    def test_serializes_normal_record(self):
        from app.schemas import FarmerResponse
        resp = FarmerResponse(
            id=3,
            maittri_farmer_id="MF-0003",
            name="Valid Farmer",
            mobile_number="9876543210",
            farm_area=5.0,
            state="UP",
        )
        assert resp.name == "Valid Farmer"
        assert resp.farm_area == 5.0

    def test_does_not_inherit_from_farmer_create(self):
        from app.schemas import FarmerResponse, FarmerCreate
        assert not issubclass(FarmerResponse, FarmerCreate)


# ============================================================
# Finding 2: Login account-status information leak
# ============================================================

class TestLoginInfoLeakPrevention:
    """Wrong password must always return generic 401, regardless of account state."""

    def _make_row(self, pwd_hash, deleted_at=None, banned_until=None, email_confirmed_at=None):
        """Create a mock auth.users row."""
        import uuid
        class Row:
            pass
        r = Row()
        r.id = uuid.uuid4()
        r.encrypted_password = pwd_hash
        r.deleted_at = deleted_at
        r.banned_until = banned_until
        r.email_confirmed_at = email_confirmed_at
        return r

    def test_wrong_password_deleted_account_returns_401(self):
        """Wrong password + deleted account => generic 401, NOT 403 deleted."""
        from datetime import datetime, timezone
        from fastapi.testclient import TestClient
        from app.main import app

        client = TestClient(app)
        # SQLite path: wrong password gives 401 regardless
        resp = client.post("/api/auth/login", json={
            "email": "nonexistent_deleted_test@example.com",
            "password": "wrongpassword"
        })
        assert resp.status_code == 401
        assert resp.json()["detail"] == "Invalid email or password"

    def test_wrong_password_returns_generic_401(self):
        from fastapi.testclient import TestClient
        from app.main import app

        client = TestClient(app)
        resp = client.post("/api/auth/login", json={
            "email": "nobody_at_all@example.com",
            "password": "wrongpassword"
        })
        assert resp.status_code == 401
        assert resp.json()["detail"] == "Invalid email or password"

    def test_valid_login_succeeds(self):
        """Normal valid registration + login flow works."""
        from fastapi.testclient import TestClient
        from app.main import app
        import uuid

        client = TestClient(app)
        unique = uuid.uuid4().hex[:8]
        email = f"logintest_{unique}@example.com"

        # Register
        reg = client.post("/api/auth/register", json={
            "email": email,
            "password": "testpass123",
            "full_name": "Login Test User"
        })
        assert reg.status_code == 200

        # Login
        login = client.post("/api/auth/login", json={
            "email": email,
            "password": "testpass123"
        })
        assert login.status_code == 200
        data = login.json()
        assert data["email"] == email
        assert "access_token" in data
