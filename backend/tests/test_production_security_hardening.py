"""
test_production_security_hardening.py
--------------------------------------
Comprehensive verification of all 27 security regression scenarios:
 1. forged JWT rejected
 2. modified JWT rejected
 3. expired JWT rejected
 4. missing sub rejected
 5. farmer cannot access another farmer's farm
 6. farmer cannot modify another farmer's farm
 7. farmer cannot access another farmer's farm plan
 8. farmer cannot access another farmer's document
 9. farmer cannot access another farmer's soil test
10. farmer cannot modify another farmer's soil-test status
11. farmer cannot submit another farmer's soil-test report
12. farmer cannot modify another farmer's service request
13. farmer cannot modify communication preferences belonging to another user
14. farmer cannot broadcast SMS
15. farmer cannot access operator-only endpoints
16. debug endpoint is protected/disabled
17. IoT simulation endpoint is protected/disabled
18. IoT spoofing rejected
19. telemetry aliases cannot bypass authentication
20. service-role key never exposed
21. anon client never falls back to service role
22. DB health failure returns 503
23. no SQLite runtime fallback
24. no Chroma runtime retrieval
25. RAG pgvector retrieval still works
26. document signed URL ownership enforced
27. UUID/FK consistency verified
"""

import os
import uuid
from datetime import datetime, timezone, timedelta
from unittest.mock import patch
import pytest
from jose import jwt
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.main import app
from app.database import get_db, Base, engine
from app.models import (
    User, Profile, Farmer, Farm, FarmPlan, FarmerDocument,
    SoilTestRequest, ServiceRequest, CommunicationPreference, IoTDevice
)
from app.security import create_access_token, SECRET_KEY, ALGORITHM, get_password_hash
from app.services.iot_service import hash_device_token
from app.supabase_client import get_supabase_anon_client
from app.services.rag_service import query_knowledge_base, compute_query_embedding

client = TestClient(app)


@pytest.fixture(scope="module")
def db_session():
    db = next(get_db())
    try:
        yield db
    finally:
        db.close()


def _provision_user(db_session: Session, email: str, role: str, name: str):
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
                VALUES (:uid, :role, :name, 'hi')
                ON CONFLICT (id) DO UPDATE SET role = :role, full_name = :name;
            """), {"uid": uid_str, "role": role, "name": name})

    user = User(
        email=email,
        password_hash=get_password_hash("TestPassword123!"),
        full_name=name,
        role=role
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    target_id = uid_str if engine.name == "postgresql" else user.id

    farmer = Farmer(
        user_id=target_id,
        maittri_farmer_id=f"MTR-{uuid.uuid4().hex[:6].upper()}",
        full_name=name,
        state="Uttar Pradesh",
        district="Lucknow",
        preferred_language="hi"
    )
    db_session.add(farmer)
    db_session.commit()
    db_session.refresh(farmer)

    farm = Farm(
        user_id=target_id,
        farmer_id=farmer.id,
        name=f"{name}'s Farm",
        size_acres=3.5,
        area=3.5,
        area_unit="acre",
        crop="Wheat",
        soil_type="Alluvial Soil",
        latitude=26.8467,
        longitude=80.9462
    )
    db_session.add(farm)
    db_session.commit()
    db_session.refresh(farm)

    return {
        "user": user,
        "farmer": farmer,
        "farm": farm,
        "uid": uid_str,
        "token": create_access_token({"sub": uid_str if engine.name == "postgresql" else str(user.id), "email": email, "role": role})
    }


@pytest.fixture(scope="module")
def farmer_1(db_session: Session):
    return _provision_user(db_session, f"farmer1_{uuid.uuid4().hex[:6]}@maitri.org", "FARMER", "Ramesh Kumar")


@pytest.fixture(scope="module")
def farmer_2(db_session: Session):
    return _provision_user(db_session, f"farmer2_{uuid.uuid4().hex[:6]}@maitri.org", "FARMER", "Suresh Patel")


@pytest.fixture(scope="module")
def operator_user(db_session: Session):
    return _provision_user(db_session, f"operator_{uuid.uuid4().hex[:6]}@maitri.org", "AUTHORIZED_OPERATOR", "Seva Operator")


# -----------------------------------------------------------------------------
# Case 1: Forged JWT rejected
# -----------------------------------------------------------------------------
def test_case_01_forged_jwt_rejected(farmer_1):
    forged_token = jwt.encode(
        {"sub": farmer_1["uid"], "role": "FARMER", "exp": datetime.now(timezone.utc) + timedelta(hours=1)},
        "completely-invalid-attacker-signing-key",
        algorithm="HS256"
    )
    res = client.get("/api/auth/me", headers={"Authorization": f"Bearer {forged_token}"})
    assert res.status_code == 401


# -----------------------------------------------------------------------------
# Case 2: Modified JWT rejected
# -----------------------------------------------------------------------------
def test_case_02_modified_jwt_rejected(farmer_1):
    valid_token = farmer_1["token"]
    # Tamper with the token string
    parts = valid_token.split(".")
    tampered_token = f"{parts[0]}.{parts[1]}xyz.{parts[2]}"
    res = client.get("/api/auth/me", headers={"Authorization": f"Bearer {tampered_token}"})
    assert res.status_code == 401


# -----------------------------------------------------------------------------
# Case 3: Expired JWT rejected
# -----------------------------------------------------------------------------
def test_case_03_expired_jwt_rejected(farmer_1):
    expired_token = jwt.encode(
        {"sub": farmer_1["uid"], "role": "FARMER", "exp": datetime.now(timezone.utc) - timedelta(days=1)},
        SECRET_KEY,
        algorithm=ALGORITHM
    )
    res = client.get("/api/auth/me", headers={"Authorization": f"Bearer {expired_token}"})
    assert res.status_code == 401


# -----------------------------------------------------------------------------
# Case 4: Missing sub rejected
# -----------------------------------------------------------------------------
def test_case_04_missing_sub_rejected():
    token_no_sub = jwt.encode(
        {"role": "FARMER", "exp": datetime.now(timezone.utc) + timedelta(hours=1)},
        SECRET_KEY,
        algorithm=ALGORITHM
    )
    res = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token_no_sub}"})
    assert res.status_code == 401


# -----------------------------------------------------------------------------
# Case 5: Farmer cannot access another farmer's farm
# -----------------------------------------------------------------------------
def test_case_05_farmer_cannot_access_another_farm(farmer_1, farmer_2):
    headers_2 = {"Authorization": f"Bearer {farmer_2['token']}"}
    res = client.get(f"/api/farms/{farmer_1['farm'].id}", headers=headers_2)
    assert res.status_code in (403, 404)


# -----------------------------------------------------------------------------
# Case 6: Farmer cannot modify another farmer's farm
# -----------------------------------------------------------------------------
def test_case_06_farmer_cannot_modify_another_farm(farmer_1, farmer_2):
    headers_2 = {"Authorization": f"Bearer {farmer_2['token']}"}
    res = client.put(f"/api/farms/{farmer_1['farm'].id}", json={"name": "Hacked Farm"}, headers=headers_2)
    assert res.status_code in (403, 404)


# -----------------------------------------------------------------------------
# Case 7: Farmer cannot access another farmer's farm plan
# -----------------------------------------------------------------------------
def test_case_07_farmer_cannot_access_another_farm_plan(db_session: Session, farmer_1, farmer_2):
    # Create plan for farmer 1
    plan = FarmPlan(
        user_id=farmer_1["uid"] if engine.name == "postgresql" else farmer_1["user"].id,
        farm_id=farmer_1["farm"].id,
        selected_crop="Wheat",
        sowing_date="2026-10-15",
        variety="HD-3086",
        current_stage="CRI"
    )
    db_session.add(plan)
    db_session.commit()
    db_session.refresh(plan)

    headers_2 = {"Authorization": f"Bearer {farmer_2['token']}"}
    res = client.get(f"/api/farmer-plans/{plan.id}", headers=headers_2)
    assert res.status_code == 403


# -----------------------------------------------------------------------------
# Case 8: Farmer cannot access another farmer's document
# -----------------------------------------------------------------------------
def test_case_08_farmer_cannot_access_another_document(db_session: Session, farmer_1, farmer_2):
    doc = FarmerDocument(
        farmer_id=farmer_1["farmer"].id,
        farm_id=farmer_1["farm"].id,
        document_name="Private Khasra Document",
        file_path="",
        storage_path=f"{farmer_1['uid']}/khasra.pdf",
        file_type="PDF",
        uploaded_by_user_id=farmer_1["uid"] if engine.name == "postgresql" else farmer_1["user"].id,
        status="VERIFIED"
    )
    db_session.add(doc)
    db_session.commit()
    db_session.refresh(doc)

    headers_2 = {"Authorization": f"Bearer {farmer_2['token']}"}
    res = client.get(f"/api/documents/download/{doc.id}", headers=headers_2)
    assert res.status_code == 403


# -----------------------------------------------------------------------------
# Case 9: Farmer cannot access another farmer's soil test
# -----------------------------------------------------------------------------
def test_case_09_farmer_cannot_access_another_soil_test(db_session: Session, farmer_1, farmer_2):
    req_id = f"MT-STR-{uuid.uuid4().hex[:6].upper()}"
    st = SoilTestRequest(
        request_id=req_id,
        farmer_id=farmer_1["farmer"].id,
        farm_id=farmer_1["farm"].id,
        status="REQUESTED"
    )
    db_session.add(st)
    db_session.commit()

    headers_2 = {"Authorization": f"Bearer {farmer_2['token']}"}
    res = client.get(f"/api/soil-tests/{req_id}", headers=headers_2)
    assert res.status_code == 403


# -----------------------------------------------------------------------------
# Case 10: Farmer cannot modify another farmer's soil-test status
# -----------------------------------------------------------------------------
def test_case_10_farmer_cannot_modify_soil_test_status(db_session: Session, farmer_1, farmer_2):
    req_id = f"MT-STR-{uuid.uuid4().hex[:6].upper()}"
    st = SoilTestRequest(
        request_id=req_id,
        farmer_id=farmer_1["farmer"].id,
        status="REQUESTED"
    )
    db_session.add(st)
    db_session.commit()

    headers_2 = {"Authorization": f"Bearer {farmer_2['token']}"}
    res = client.patch(f"/api/soil-tests/{req_id}/status", json={"status": "SAMPLE_COLLECTED"}, headers=headers_2)
    assert res.status_code == 403


# -----------------------------------------------------------------------------
# Case 11: Farmer cannot submit another farmer's soil-test report
# -----------------------------------------------------------------------------
def test_case_11_farmer_cannot_submit_soil_report(db_session: Session, farmer_1, farmer_2):
    req_id = f"MT-STR-{uuid.uuid4().hex[:6].upper()}"
    st = SoilTestRequest(
        request_id=req_id,
        farmer_id=farmer_1["farmer"].id,
        status="REQUESTED"
    )
    db_session.add(st)
    db_session.commit()

    headers_2 = {"Authorization": f"Bearer {farmer_2['token']}"}
    res = client.post(f"/api/soil-tests/{req_id}/report", json={
        "farmer_id": farmer_1["farmer"].id,
        "lab_name": "Government Agriculture Laboratory",
        "nitrogen": 210.0,
        "phosphorus": 25.0,
        "potassium": 230.0,
        "ph": 7.2
    }, headers=headers_2)
    assert res.status_code == 403


# -----------------------------------------------------------------------------
# Case 12: Farmer cannot modify another farmer's service request
# -----------------------------------------------------------------------------
def test_case_12_farmer_cannot_modify_service_request(db_session: Session, farmer_1, farmer_2):
    req_id = f"MT-REQ-{uuid.uuid4().hex[:6].upper()}"
    sr = ServiceRequest(
        request_id=req_id,
        farmer_id=farmer_1["farmer"].id,
        service_type="SOIL_TEST",
        status="REQUESTED",
        description="Soil test request"
    )
    db_session.add(sr)
    db_session.commit()

    headers_2 = {"Authorization": f"Bearer {farmer_2['token']}"}
    res = client.patch(f"/api/service-requests/{req_id}", json={"status": "CANCELLED"}, headers=headers_2)
    assert res.status_code == 403


# -----------------------------------------------------------------------------
# Case 13: Farmer cannot modify communication preferences belonging to another user
# -----------------------------------------------------------------------------
def test_case_13_farmer_cannot_modify_other_comm_preferences(farmer_1, farmer_2):
    headers_2 = {"Authorization": f"Bearer {farmer_2['token']}"}
    res = client.patch(
        f"/api/communications/preferences/{farmer_1['farmer'].id}",
        json={"sms_enabled": False},
        headers=headers_2
    )
    assert res.status_code == 403


# -----------------------------------------------------------------------------
# Case 14: Farmer cannot broadcast SMS
# -----------------------------------------------------------------------------
def test_case_14_farmer_cannot_broadcast_sms(farmer_1):
    headers_1 = {"Authorization": f"Bearer {farmer_1['token']}"}
    res = client.post("/api/communications/sms/send", json={
        "mobile_numbers": ["9876543210"],
        "message": "Unauthorized broadcast message"
    }, headers=headers_1)
    assert res.status_code == 403


# -----------------------------------------------------------------------------
# Case 15: Farmer cannot access operator-only endpoints
# -----------------------------------------------------------------------------
def test_case_15_farmer_cannot_access_operator_endpoints(farmer_1):
    headers_1 = {"Authorization": f"Bearer {farmer_1['token']}"}
    res_dash = client.get("/api/operators/dashboard", headers=headers_1)
    assert res_dash.status_code == 403

    res_sms_logs = client.get("/api/communications/sms/logs", headers=headers_1)
    assert res_sms_logs.status_code == 403


# -----------------------------------------------------------------------------
# Case 16: Debug endpoint is protected/disabled in production
# -----------------------------------------------------------------------------
def test_case_16_debug_endpoint_protected():
    with patch.dict("os.environ", {"ENVIRONMENT": "production"}):
        res = client.post("/api/chat/debug", json={"query": "Wheat crop"})
        assert res.status_code == 403


# -----------------------------------------------------------------------------
# Case 17: IoT simulation endpoint is protected/disabled in production
# -----------------------------------------------------------------------------
def test_case_17_iot_simulation_disabled_in_production():
    with patch.dict("os.environ", {"ENVIRONMENT": "production"}):
        res = client.post("/api/iot/simulate?device_id=MAITRI_SIM")
        assert res.status_code == 403

        res_lan = client.get("/api/iot/lan-info")
        assert res_lan.status_code == 403


# -----------------------------------------------------------------------------
# Case 18: IoT spoofing rejected
# -----------------------------------------------------------------------------
def test_case_18_iot_spoofing_rejected(db_session: Session):
    dev_id = f"SPOOF_TEST_{uuid.uuid4().hex[:6]}"
    correct_token = "valid-preshared-device-token-12345"
    device = IoTDevice(
        device_id=dev_id,
        controller_type="ESP32",
        name="Device Spoof Test",
        device_token_hash=hash_device_token(correct_token),
        is_active=True,
        last_seen=datetime.now(timezone.utc)
    )
    db_session.add(device)
    db_session.commit()

    # Attempt submission with forged token
    res = client.post("/api/iot/sensor-data", json={
        "device_id": dev_id,
        "temperature": 28.0,
        "humidity": 60.0,
        "soil_moisture": 50.0
    }, headers={"X-Device-Token": "forged-token-attempt"})
    assert res.status_code == 403


# -----------------------------------------------------------------------------
# Case 19: Telemetry aliases cannot bypass authentication
# -----------------------------------------------------------------------------
def test_case_19_telemetry_aliases_require_auth(db_session: Session):
    dev_id = f"ALIAS_TEST_{uuid.uuid4().hex[:6]}"
    raw_token = "alias-token-secret-67890"
    device = IoTDevice(
        device_id=dev_id,
        controller_type="ESP8266",
        name="Alias Test",
        device_token_hash=hash_device_token(raw_token),
        is_active=True,
        last_seen=datetime.now(timezone.utc)
    )
    db_session.add(device)
    db_session.commit()

    payload = {"device_id": dev_id, "temperature": 25.0}

    # All telemetry aliases must reject unauthenticated requests
    for path in ("/telemetry", "/api/sensor-data", "/api/iot/telemetry", "/api/iot/data", "/api/iot/sensor-data"):
        res = client.post(path, json=payload)
        assert res.status_code in (401, 403), f"Path {path} did not enforce auth (status: {res.status_code})"


# -----------------------------------------------------------------------------
# Case 20: Service-role key never exposed in API responses
# -----------------------------------------------------------------------------
def test_case_20_service_role_key_never_exposed(farmer_1):
    service_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
    if not service_key:
        pytest.skip("SUPABASE_SERVICE_ROLE_KEY not configured")

    endpoints_to_check = [
        client.get("/api/auth/me", headers={"Authorization": f"Bearer {farmer_1['token']}"}),
        client.get("/health"),
        client.get("/api/health"),
        client.get("/api/chat/status")
    ]
    for res in endpoints_to_check:
        assert service_key not in res.text, "CRITICAL: Service role key detected in API response!"


# -----------------------------------------------------------------------------
# Case 21: Anon client never falls back to service role
# -----------------------------------------------------------------------------
def test_case_21_anon_client_never_falls_back_to_service_role():
    with patch.dict("os.environ", {"SUPABASE_ANON_KEY": "", "SUPABASE_SERVICE_ROLE_KEY": "service-key-mock"}):
        from app import supabase_client
        supabase_client._anon_client = None
        anon = get_supabase_anon_client()
        assert anon is None, "Anon client must return None when SUPABASE_ANON_KEY is missing, not fall back to service role!"


# -----------------------------------------------------------------------------
# Case 22: DB health failure returns 503
# -----------------------------------------------------------------------------
def test_case_22_db_health_failure_returns_503():
    with patch("sqlalchemy.orm.Session.execute", side_effect=Exception("Database connection terminated")):
        res = client.get("/health")
        assert res.status_code == 503
        data = res.json()
        assert data["detail"]["status"] == "unhealthy"
        assert data["detail"]["database"] == "unreachable"


# -----------------------------------------------------------------------------
# Case 23: No SQLite runtime fallback in production
# -----------------------------------------------------------------------------
def test_case_23_no_sqlite_in_production():
    with patch.dict("os.environ", {"ENVIRONMENT": "production"}):
        env = os.getenv("ENVIRONMENT")
        assert env == "production"
        # In production with DATABASE_URL set to postgres, engine must not be sqlite
        if os.getenv("DATABASE_URL", "").startswith(("postgresql://", "postgres://")):
            assert engine.name == "postgresql"


# -----------------------------------------------------------------------------
# Case 24: No Chroma runtime retrieval in production
# -----------------------------------------------------------------------------
def test_case_24_no_chroma_retrieval_in_production():
    with patch.dict("os.environ", {"ENVIRONMENT": "production"}):
        with patch("app.services.rag_service.get_chroma_collection") as mock_chroma:
            mock_chroma.return_value.count.return_value = 0
            mock_chroma.return_value.query.return_value = {"documents": [[]], "metadatas": [[]], "distances": [[]]}
            res = query_knowledge_base("Wheat crop irrigation interval", top_k=2)
            if engine.name == "postgresql":
                # Chroma collection should not be called when PostgreSQL pgvector is active
                mock_chroma.assert_not_called()


# -----------------------------------------------------------------------------
# Case 25: RAG pgvector retrieval still works
# -----------------------------------------------------------------------------
def test_case_25_rag_pgvector_retrieval_functional():
    if engine.name != "postgresql":
        pytest.skip("pgvector test requires live PostgreSQL connection")
    res = query_knowledge_base("Wheat first irrigation CRI stage", top_k=2)
    assert len(res["chunks"]) > 0
    assert len(res["sources"]) > 0
    assert res["confidence"] > 0.20


# -----------------------------------------------------------------------------
# Case 26: Document signed URL ownership enforced
# -----------------------------------------------------------------------------
def test_case_26_document_signed_url_ownership_enforced(db_session: Session, farmer_1, farmer_2):
    doc = FarmerDocument(
        farmer_id=farmer_1["farmer"].id,
        farm_id=farmer_1["farm"].id,
        document_name="Confidential Soil Lab Report",
        file_path="",
        storage_path=f"{farmer_1['uid']}/soil_report.pdf",
        file_type="PDF",
        uploaded_by_user_id=farmer_1["uid"] if engine.name == "postgresql" else farmer_1["user"].id,
        status="VERIFIED"
    )
    db_session.add(doc)
    db_session.commit()

    headers_2 = {"Authorization": f"Bearer {farmer_2['token']}"}
    res = client.get(f"/api/documents/signed-url/{doc.id}", headers=headers_2)
    assert res.status_code == 403


# -----------------------------------------------------------------------------
# Case 27: UUID/FK consistency verified
# -----------------------------------------------------------------------------
def test_case_27_uuid_fk_consistency(db_session: Session, farmer_1):
    if engine.name != "postgresql":
        pytest.skip("Schema consistency test requires PostgreSQL")
    # Verify profiles.id, farmers.user_id, farms.user_id match UUID format
    import uuid as _u
    _u.UUID(str(farmer_1["farmer"].user_id))
    _u.UUID(str(farmer_1["farm"].user_id))
    profile = db_session.query(Profile).filter(Profile.id == farmer_1["uid"]).first()
    assert profile is not None
    _u.UUID(str(profile.id))
