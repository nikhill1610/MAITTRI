"""
test_security_authorization.py
--------------------------------
Comprehensive automated test suite verifying MAITRI backend security hardening:
1. Strict cryptographic JWT validation (zero unverified token acceptance)
2. Role enforcement & privilege escalation rejection
3. Multi-tenant isolation & IDOR prevention across all sensitive resources
4. IoT device preshared token authentication (X-Device-Token)
5. Production-disabled debug and simulation endpoints
6. Health endpoint resilient error handling
"""

import os
import uuid
from datetime import datetime, timezone, timedelta
import pytest
from jose import jwt
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from sqlalchemy import text
from app.main import app
from app.database import get_db, Base, engine
from app.models import User, Profile, Farmer, Farm, FarmerDocument, SoilTestRequest, ServiceRequest, IoTDevice
from app.security import create_access_token, SECRET_KEY, ALGORITHM, get_password_hash
from app.services.iot_service import hash_device_token

client = TestClient(app)

@pytest.fixture(scope="module")
def db_session():
    """Provides test database session."""
    db = next(get_db())
    try:
        yield db
    finally:
        db.close()


def _provision_test_identity(db_session: Session, email: str, role: str, full_name: str):
    uid_str = str(uuid.uuid4())
    if engine.name == "postgresql":
        with engine.begin() as conn:
            conn.execute(text("""
                INSERT INTO auth.users (id, aud, role, email, created_at, updated_at)
                VALUES (:uid, 'authenticated', 'authenticated', :email, now(), now())
                ON CONFLICT (id) DO NOTHING;
            """), {"uid": uid_str, "email": email})
            conn.execute(text("""
                INSERT INTO public.profiles (id, role, full_name, preferred_language)
                VALUES (:uid, :role, :full_name, 'hi')
                ON CONFLICT (id) DO UPDATE SET role = :role, full_name = :full_name;
            """), {"uid": uid_str, "role": role, "full_name": full_name})

    user = User(
        email=email,
        password_hash=get_password_hash("SecretPassword123!"),
        full_name=full_name,
        role=role
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    user.auth_uid = uid_str
    return user, uid_str


@pytest.fixture(scope="module")
def user_farmer_a(db_session: Session):
    email = f"farmer_a_{uuid.uuid4().hex[:6]}@maitri-test.org"
    user, uid_str = _provision_test_identity(db_session, email, "FARMER", "Farmer Alpha")
    target_user_id = uid_str if engine.name == "postgresql" else user.id

    farmer = Farmer(
        user_id=target_user_id,
        maittri_farmer_id=f"MTR-A-{uuid.uuid4().hex[:4].upper()}",
        full_name="Farmer Alpha",
        state="Haryana",
        district="Karnal",
        preferred_language="hi"
    )
    db_session.add(farmer)
    db_session.commit()
    db_session.refresh(farmer)

    farm = Farm(
        user_id=target_user_id,
        name="Alpha Organic Farm",
        size_acres=5.0,
        crop="Wheat",
        soil_type="Alluvial Soil",
        latitude=29.6857,
        longitude=76.9905
    )
    db_session.add(farm)
    db_session.commit()
    db_session.refresh(farm)

    return {"user": user, "farmer": farmer, "farm": farm, "uid": uid_str}


@pytest.fixture(scope="module")
def user_farmer_b(db_session: Session):
    email = f"farmer_b_{uuid.uuid4().hex[:6]}@maitri-test.org"
    user, uid_str = _provision_test_identity(db_session, email, "FARMER", "Farmer Beta")
    target_user_id = uid_str if engine.name == "postgresql" else user.id

    farmer = Farmer(
        user_id=target_user_id,
        maittri_farmer_id=f"MTR-B-{uuid.uuid4().hex[:4].upper()}",
        full_name="Farmer Beta",
        state="Punjab",
        district="Ludhiana",
        preferred_language="pa"
    )
    db_session.add(farmer)
    db_session.commit()
    db_session.refresh(farmer)

    farm = Farm(
        user_id=target_user_id,
        name="Beta Wheat Farm",
        size_acres=8.0,
        crop="Wheat",
        soil_type="Alluvial Soil",
        latitude=30.9010,
        longitude=75.8573
    )
    db_session.add(farm)
    db_session.commit()
    db_session.refresh(farm)

    return {"user": user, "farmer": farmer, "farm": farm, "uid": uid_str}


@pytest.fixture(scope="module")
def user_operator(db_session: Session):
    email = f"operator_{uuid.uuid4().hex[:6]}@maitri-test.org"
    user, uid_str = _provision_test_identity(db_session, email, "AUTHORIZED_OPERATOR", "Kisan Seva Kendra Operator")
    return {"user": user, "uid": uid_str}


# ==============================================================================
# 1. Cryptographic JWT Verification Tests
# ==============================================================================

def test_jwt_forged_signature_rejected(user_farmer_a):
    """Tokens signed with wrong secret key MUST be rejected with 401."""
    payload = {
        "sub": user_farmer_a["user"].email,
        "role": "ADMIN",
        "exp": datetime.now(timezone.utc) + timedelta(hours=1)
    }
    forged_token = jwt.encode(payload, "completely-wrong-attacker-secret-key", algorithm=ALGORITHM)
    res = client.get("/api/auth/me", headers={"Authorization": f"Bearer {forged_token}"})
    assert res.status_code == 401
    assert "Invalid or expired" in res.json()["detail"]


def test_jwt_expired_token_rejected(user_farmer_a):
    """Expired tokens MUST be rejected with 401."""
    payload = {
        "sub": user_farmer_a["user"].email,
        "role": "FARMER",
        "exp": datetime.now(timezone.utc) - timedelta(hours=1)
    }
    expired_token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    res = client.get("/api/auth/me", headers={"Authorization": f"Bearer {expired_token}"})
    assert res.status_code == 401


def test_jwt_malformed_token_rejected():
    """Malformed non-JWT strings MUST be rejected with 401."""
    res = client.get("/api/auth/me", headers={"Authorization": "Bearer not-a-real-jwt-token"})
    assert res.status_code == 401


def test_jwt_valid_signature_accepted(user_farmer_a):
    """Legitimate token signed with SECRET_KEY MUST succeed."""
    token = create_access_token({"sub": user_farmer_a["user"].email, "role": "FARMER"})
    res = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    assert res.json()["email"] == user_farmer_a["user"].email


# ==============================================================================
# 2. Role Enforcement & Privilege Escalation Tests
# ==============================================================================

def test_farmer_cannot_access_operator_routes(user_farmer_a):
    """Farmers cannot access operator-only administration routes."""
    farmer_token = create_access_token({"sub": user_farmer_a["user"].email, "role": "FARMER"})
    headers = {"Authorization": f"Bearer {farmer_token}"}

    # Operator dashboard
    res_dash = client.get("/api/operators/dashboard", headers=headers)
    assert res_dash.status_code == 403

    # SMS broadcast
    res_sms = client.post("/api/communications/sms/send", json={
        "recipient_phone": "+919876543210",
        "message_text": "Unauthorized broadcast"
    }, headers=headers)
    assert res_sms.status_code == 403


def test_operator_can_access_operator_routes(user_operator):
    """Authorized operators can access operator management routes."""
    op_token = create_access_token({"sub": user_operator["user"].email, "role": "AUTHORIZED_OPERATOR"})
    headers = {"Authorization": f"Bearer {op_token}"}
    res_dash = client.get("/api/operators/dashboard", headers=headers)
    assert res_dash.status_code == 200


# ==============================================================================
# 3. Multi-Tenant Isolation & IDOR Protection Tests
# ==============================================================================

def test_idor_farm_brain_isolation(user_farmer_a, user_farmer_b):
    """Farmer B cannot access Farmer A's Farm Brain dashboard."""
    token_b = create_access_token({"sub": user_farmer_b["user"].email, "role": "FARMER"})
    headers_b = {"Authorization": f"Bearer {token_b}"}

    farm_a_id = user_farmer_a["farm"].id
    res_today = client.get(f"/api/farm-brain/today/{farm_a_id}", headers=headers_b)
    assert res_today.status_code in (403, 404)

    res_week = client.get(f"/api/farm-brain/week/{farm_a_id}", headers=headers_b)
    assert res_week.status_code in (403, 404)


def test_idor_farmer_qr_profile_isolation(user_farmer_a, user_farmer_b):
    """Farmer B cannot access Farmer A's QR card / farm ID."""
    token_b = create_access_token({"sub": user_farmer_b["user"].email, "role": "FARMER"})
    headers_b = {"Authorization": f"Bearer {token_b}"}

    farmer_a_id = user_farmer_a["farmer"].id
    res_qr = client.get(f"/api/farmer-profile/qr/{farmer_a_id}", headers=headers_b)
    assert res_qr.status_code == 403


def test_idor_communication_preferences_isolation(user_farmer_a, user_farmer_b):
    """Farmer B cannot view or modify Farmer A's SMS/IVR preferences."""
    token_b = create_access_token({"sub": user_farmer_b["user"].email, "role": "FARMER"})
    headers_b = {"Authorization": f"Bearer {token_b}"}

    farmer_a_id = user_farmer_a["farmer"].id
    res_get = client.get(f"/api/communications/preferences/{farmer_a_id}", headers=headers_b)
    assert res_get.status_code == 403

    res_patch = client.patch(f"/api/communications/preferences/{farmer_a_id}", json={
        "sms_enabled": False
    }, headers=headers_b)
    assert res_patch.status_code == 403


def test_idor_document_vault_download(db_session: Session, user_farmer_a, user_farmer_b):
    """Farmer B cannot download Farmer A's documents."""
    doc_a = FarmerDocument(
        farmer_id=user_farmer_a["farmer"].id,
        farm_id=user_farmer_a["farm"].id,
        document_name="Confidential Land Deed",
        category="Land Record",
        file_path="",
        storage_path=f"{user_farmer_a.get('uid') or user_farmer_a['user'].id}/land_deed.pdf",
        file_type="PDF",
        uploaded_by_user_id=user_farmer_a.get('uid') if engine.name == "postgresql" else user_farmer_a["user"].id,
        uploader_role="FARMER",
        status="VERIFIED"
    )
    db_session.add(doc_a)
    db_session.commit()
    db_session.refresh(doc_a)

    token_b = create_access_token({"sub": user_farmer_b["user"].email, "role": "FARMER"})
    headers_b = {"Authorization": f"Bearer {token_b}"}

    res_dl = client.get(f"/api/documents/download/{doc_a.id}", headers=headers_b)
    assert res_dl.status_code == 403

    res_url = client.get(f"/api/documents/signed-url/{doc_a.id}", headers=headers_b)
    assert res_url.status_code == 403

    res_del = client.delete(f"/api/documents/{doc_a.id}", headers=headers_b)
    assert res_del.status_code == 403


# ==============================================================================
# 4. IoT Device Authentication Tests
# ==============================================================================

def test_iot_telemetry_token_authentication(db_session: Session):
    """IoT devices with registered token hashes require matching X-Device-Token header."""
    device_id = f"TEST_NODE_{uuid.uuid4().hex[:6]}"
    raw_token = "ultra-secure-pre-shared-iot-secret-token-12345"
    token_hash = hash_device_token(raw_token)

    now = datetime.now(timezone.utc)
    device = IoTDevice(
        device_id=device_id,
        controller_type="ESP32",
        name="Test Sensor Node",
        device_token_hash=token_hash,
        is_active=True,
        last_seen=now,
        created_at=now
    )
    db_session.add(device)
    db_session.commit()

    payload = {
        "device_id": device_id,
        "temperature": 25.5,
        "humidity": 65.0,
        "soil_moisture": 45.0
    }

    # 1. Missing token header should be rejected
    res_missing = client.post("/api/iot/sensor-data", json=payload)
    assert res_missing.status_code == 403

    # 2. Invalid token should be rejected
    res_wrong = client.post(
        "/api/iot/sensor-data",
        json=payload,
        headers={"X-Device-Token": "wrong-token"}
    )
    assert res_wrong.status_code == 403

    # 3. Correct token should succeed
    res_correct = client.post(
        "/api/iot/sensor-data",
        json=payload,
        headers={"X-Device-Token": raw_token}
    )
    assert res_correct.status_code == 200
    assert res_correct.json()["status"] == "success"


# ==============================================================================
# 5. Production Disabled Endpoints Tests
# ==============================================================================

def test_production_disabled_endpoints():
    """Endpoints meant only for development must return 403 in production environment."""
    current_env = os.getenv("ENVIRONMENT", "production").lower()
    if current_env == "production":
        # /api/chat/debug
        res_debug = client.post("/api/chat/debug", json={"query": "test"})
        assert res_debug.status_code == 403

        # /api/iot/simulate
        res_sim = client.post("/api/iot/simulate", json={"device_id": "TEST"})
        assert res_sim.status_code == 403

        # /api/iot/lan-info
        res_lan = client.get("/api/iot/lan-info")
        assert res_lan.status_code == 403


# ==============================================================================
# 6. Health Check API
# ==============================================================================

def test_health_check_returns_healthy():
    """Health check returns status healthy and database connected."""
    res = client.get("/api/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "healthy"
    assert data["database"] == "connected"
    assert data["rag"] == "pgvector"
    assert data["storage"] == "farmer-vault"
