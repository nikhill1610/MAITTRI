import uuid
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.database import get_db
from app.models import Profile, User

client = TestClient(app)

@pytest.fixture(scope="module")
def portal_users():
    suffix = uuid.uuid4().hex[:8]
    farmer_email = f"farmer_test_{suffix}@maittri.org"
    operator_email = f"official_test_{suffix}@maittri.org"
    password = "SecurePassword123!"

    # 1. Register Farmer
    r_farmer = client.post("/api/auth/register", json={
        "email": farmer_email,
        "password": password,
        "role": "FARMER",
        "full_name": "Kisan Ram",
        "phone_number": "9876543201",
        "language": "hi"
    })
    assert r_farmer.status_code == 200
    farmer_user_id = str(r_farmer.json()["user_id"])

    # 2. Register Operator
    r_op = client.post("/api/auth/register", json={
        "email": operator_email,
        "password": password,
        "role": "AUTHORIZED_OPERATOR",
        "full_name": "Seva Officer Vikas",
        "phone_number": "9876543202",
        "language": "en"
    })
    assert r_op.status_code == 200
    operator_user_id = str(r_op.json()["user_id"])

    # Authoritatively assign AUTHORIZED_OPERATOR role in database
    db = next(get_db())
    try:
        prof = db.query(Profile).filter(Profile.id == operator_user_id).first()
        if prof:
            prof.role = "AUTHORIZED_OPERATOR"
            db.commit()
        if operator_user_id.isdigit():
            u = db.query(User).filter(User.id == int(operator_user_id)).first()
            if u:
                u.role = "AUTHORIZED_OPERATOR"
                db.commit()
    finally:
        db.close()

    return {
        "farmer_email": farmer_email,
        "operator_email": operator_email,
        "password": password,
        "farmer_id": farmer_user_id,
        "operator_id": operator_user_id
    }


def test_farmer_login_authenticates_with_farmer_role(portal_users):
    """Case 1: Farmer login returns token and authoritative FARMER role."""
    res = client.post("/api/auth/login", json={
        "email": portal_users["farmer_email"],
        "password": portal_users["password"]
    })
    assert res.status_code == 200
    data = res.json()
    assert "access_token" in data
    assert data["role"] == "FARMER"


def test_official_login_authenticates_with_authorized_operator_role(portal_users):
    """Case 2: Official / Seva Nirmata login returns token and authoritative AUTHORIZED_OPERATOR role."""
    res = client.post("/api/auth/login", json={
        "email": portal_users["operator_email"],
        "password": portal_users["password"]
    })
    assert res.status_code == 200
    data = res.json()
    assert "access_token" in data
    assert data["role"] == "AUTHORIZED_OPERATOR"


def test_auth_me_returns_authoritative_role_on_refresh(portal_users):
    """Case 3 & 9: /api/auth/me returns authoritative roles for state hydration and refresh."""
    # Farmer
    login_farmer = client.post("/api/auth/login", json={
        "email": portal_users["farmer_email"],
        "password": portal_users["password"]
    }).json()
    me_farmer = client.get("/api/auth/me", headers={"Authorization": f"Bearer {login_farmer['access_token']}"})
    assert me_farmer.status_code == 200
    assert me_farmer.json()["role"] == "FARMER"

    # Official
    login_op = client.post("/api/auth/login", json={
        "email": portal_users["operator_email"],
        "password": portal_users["password"]
    }).json()
    me_op = client.get("/api/auth/me", headers={"Authorization": f"Bearer {login_op['access_token']}"})
    assert me_op.status_code == 200
    assert me_op.json()["role"] == "AUTHORIZED_OPERATOR"


def test_farmer_blocked_from_operator_portal_endpoints(portal_users):
    """Case 6: Farmer attempting to access operator endpoints is denied with 403 Forbidden."""
    login_farmer = client.post("/api/auth/login", json={
        "email": portal_users["farmer_email"],
        "password": portal_users["password"]
    }).json()
    farmer_headers = {"Authorization": f"Bearer {login_farmer['access_token']}"}

    res = client.get("/api/operators/stats", headers=farmer_headers)
    assert res.status_code == 403
    assert "restricted to Authorized Agriculture / Seva Operators" in res.json()["detail"]


def test_official_allowed_access_to_operator_portal_endpoints(portal_users):
    """Case 7: Official accessing operator endpoints is granted access (200 OK)."""
    login_op = client.post("/api/auth/login", json={
        "email": portal_users["operator_email"],
        "password": portal_users["password"]
    }).json()
    op_headers = {"Authorization": f"Bearer {login_op['access_token']}"}

    res = client.get("/api/operators/stats", headers=op_headers)
    assert res.status_code == 200
    data = res.json()
    assert "total_registered_farmers" in data
    assert "pending_soil_tests" in data


def test_unauthenticated_user_denied_from_operator_endpoints():
    """Case 8: Unauthenticated access to operator endpoints is rejected (401/403)."""
    res = client.get("/api/operators/stats")
    assert res.status_code in (401, 403)


def test_assisted_farmer_registration_workflow_by_official(portal_users):
    """Case 10: Existing assisted farmer registration workflow works as intended."""
    login_op = client.post("/api/auth/login", json={
        "email": portal_users["operator_email"],
        "password": portal_users["password"]
    }).json()
    op_headers = {"Authorization": f"Bearer {login_op['access_token']}"}

    assisted_payload = {
        "name": "Chhotelal Yadav",
        "mobile_number": f"98{uuid.uuid4().int % 100000000:08d}",
        "state": "Uttar Pradesh",
        "district": "Varanasi",
        "block": "Harahua",
        "village": "Babatpur",
        "farm_area": 2.5,
        "area_unit": "acre",
        "land_ownership": "owner",
        "irrigation": "canal",
        "soil_type": "Alluvial Soil",
        "current_crop": "Wheat",
        "previous_crop": "Rice",
        "preferred_language": "hi",
        "sms_consent": True,
        "ivr_consent": True
    }

    res = client.post("/api/operators/farmers", json=assisted_payload, headers=op_headers)
    assert res.status_code == 200
    farmer = res.json()
    assert "maittri_farmer_id" in farmer
    assert farmer["maittri_farmer_id"].startswith("MT-FARM-")
    assert farmer["name"] == "Chhotelal Yadav"
    assert farmer["qr_code_data"] is not None
