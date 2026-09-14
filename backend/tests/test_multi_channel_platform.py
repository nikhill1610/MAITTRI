"""
MAITTRI Multi-Channel Platform Integration Test Suite
------------------------------------------------------
Validates:
1. Role-based access control (FARMER vs AUTHORIZED_OPERATOR)
2. Assisted Farmer registration with unique MT-FARM-XXXXXX ID
3. Soil Test Request & Report lifecycle
4. Service Request tracking
5. MAITTRI Farm Brain Today's Decision engine
6. SMS Provider-Agnostic Dispatch with safe DEMO MODE
7. IVR interactive voice simulation
8. Existing endpoints backward-compatibility
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.database import Base, engine, SessionLocal
from app.models import User, Farmer, Farm

client = TestClient(app)


import uuid

@pytest.fixture(scope="module")
def setup_test_users():
    """Sets up a test farmer and an authorized seva operator."""
    suffix = uuid.uuid4().hex[:8]
    farmer_email = f"test_farmer_{suffix}@maittri.org"
    op_email = f"test_operator_{suffix}@maittri.org"

    # Register Farmer
    r_farmer = client.post("/api/auth/register", json={
        "email": farmer_email,
        "password": "Password123!",
        "role": "FARMER",
        "full_name": "Ramesh Kumar",
        "phone_number": "9876543210",
        "language": "hi"
    })
    assert r_farmer.status_code == 200, f"Farmer registration failed: {r_farmer.text}"
    farmer_token = r_farmer.json()["access_token"]

    # Register Authorized Operator
    r_op = client.post("/api/auth/register", json={
        "email": op_email,
        "password": "Password123!",
        "role": "AUTHORIZED_OPERATOR",
        "full_name": "Suresh Seva Officer",
        "phone_number": "9123456780",
        "language": "en"
    })
    assert r_op.status_code == 200, f"Operator registration failed: {r_op.text}"
    op_token = r_op.json()["access_token"]

    return {
        "farmer_token": farmer_token,
        "operator_token": op_token
    }



def test_role_based_access_control(setup_test_users):
    """Verifies that farmers cannot access operator-only management routes."""
    farmer_headers = {"Authorization": f"Bearer {setup_test_users['farmer_token']}"}
    op_headers = {"Authorization": f"Bearer {setup_test_users['operator_token']}"}

    # Farmer should be forbidden (403) from operator stats
    res_forbidden = client.get("/api/operators/stats", headers=farmer_headers)
    assert res_forbidden.status_code == 403

    # Operator should succeed (200)
    res_allowed = client.get("/api/operators/stats", headers=op_headers)
    assert res_allowed.status_code == 200
    data = res_allowed.json()
    assert "total_registered_farmers" in data
    assert "pending_soil_tests" in data


def test_assisted_farmer_registration_by_operator(setup_test_users):
    """Verifies operator can register a non-smartphone farmer and generate MT-FARM ID."""
    op_headers = {"Authorization": f"Bearer {setup_test_users['operator_token']}"}

    payload = {
        "name": "Brijesh Patel",
        "mobile_number": "9811223344",
        "alternate_mobile": "9811223345",
        "state": "Uttar Pradesh",
        "district": "Varanasi",
        "block": "Kashi Vidyapeeth",
        "village": "Shivpur",
        "farm_area": 3.5,
        "area_unit": "acre",
        "land_ownership": "owner",
        "irrigation": "tubewell",
        "soil_type": "Alluvial Soil",
        "current_crop": "Wheat",
        "previous_crop": "Rice",
        "preferred_language": "hi",
        "sms_consent": True,
        "ivr_consent": True
    }

    res = client.post("/api/operators/farmers", json=payload, headers=op_headers)
    assert res.status_code == 200
    farmer_data = res.json()
    assert "MT-FARM-" in farmer_data["maittri_farmer_id"]
    assert farmer_data["name"] == "Brijesh Patel"
    assert farmer_data["qr_code_data"] is not None

    # Search for this farmer
    search_res = client.get("/api/operators/farmers", params={"q": "Brijesh"}, headers=op_headers)
    assert search_res.status_code == 200
    results = search_res.json()
    assert len(results) >= 1
    assert any(f["name"] == "Brijesh Patel" for f in results)


def test_soil_test_booking_lifecycle(setup_test_users):
    """Verifies soil test booking, status progression, and certified lab report submission."""
    op_headers = {"Authorization": f"Bearer {setup_test_users['operator_token']}"}

    # Get a farmer
    farmers = client.get("/api/operators/farmers", headers=op_headers).json()
    assert len(farmers) > 0
    farmer_id = farmers[0]["id"]

    # 1. Book soil test
    book_res = client.post("/api/soil-tests", json={
        "farmer_id": farmer_id,
        "location": "North Plot, Shivpur",
        "crop": "Wheat",
        "notes": "Suspected nitrogen deficiency and low organic carbon"
    }, headers=op_headers)
    assert book_res.status_code == 200
    st_data = book_res.json()
    assert "MT-STR-" in st_data["request_id"]
    assert st_data["status"] == "REQUESTED"
    req_id = st_data["request_id"]

    # 2. Update status to SCHEDULED
    update_res = client.patch(f"/api/soil-tests/{req_id}/status", json={
        "status": "SCHEDULED",
        "lab_name": "KVK Regional Agricultural Laboratory"
    }, headers=op_headers)
    assert update_res.status_code == 200
    assert update_res.json()["status"] == "SCHEDULED"

    # 3. Submit certified lab report
    report_res = client.post(f"/api/soil-tests/{req_id}/report", json={
        "request_id": req_id,
        "farmer_id": farmer_id,
        "lab_name": "KVK Regional Agricultural Laboratory",
        "nitrogen": 190.5,
        "phosphorus": 14.2,
        "potassium": 160.0,
        "ph": 7.3,
        "ec": 0.42,
        "organic_carbon": 0.38,
        "zinc": 0.65
    }, headers=op_headers)
    assert report_res.status_code == 200
    rep_data = report_res.json()
    assert rep_data["is_certified_lab_test"] is True
    assert rep_data["nitrogen"] == 190.5


def test_service_request_lifecycle(setup_test_users):
    """Verifies creation and resolution of general seva service requests."""
    op_headers = {"Authorization": f"Bearer {setup_test_users['operator_token']}"}
    farmers = client.get("/api/operators/farmers", headers=op_headers).json()
    farmer_id = farmers[0]["id"]

    create_res = client.post("/api/service-requests", json={
        "farmer_id": farmer_id,
        "service_type": "PEST_ADVISORY",
        "description": "Aphids observed on mustard crop. Seeking biological control guidance."
    }, headers=op_headers)
    assert create_res.status_code == 200
    sr_data = create_res.json()
    assert "MT-REQ-" in sr_data["request_id"]
    assert sr_data["status"] == "REQUESTED"
    req_id = sr_data["request_id"]

    resolve_res = client.patch(f"/api/service-requests/{req_id}", json={
        "status": "COMPLETED",
        "resolution_notes": "Advised 5ml/L Neem Oil (1500 ppm) spray early morning. Provided IPM leaflet."
    }, headers=op_headers)
    assert resolve_res.status_code == 200
    assert resolve_res.json()["status"] == "COMPLETED"


def test_farm_brain_decision_engine(setup_test_users):
    """Verifies Farm Brain synthesizes today's priority actions with explainable reasons and data used."""
    farmer_headers = {"Authorization": f"Bearer {setup_test_users['farmer_token']}"}

    # Get farmer's farm
    farms_res = client.get("/api/farms", headers=farmer_headers)
    farms = farms_res.json()
    if not farms:
        # Create a farm for farmer
        farm_create = client.post("/api/farms", json={
            "name": "Ramesh Primary Farm",
            "area": 2.0,
            "soil_type": "Alluvial Soil",
            "irrigation": "tubewell",
            "current_crop": "Wheat"
        }, headers=farmer_headers)
        farm_id = farm_create.json()["id"]
    else:
        farm_id = farms[0]["id"]

    brain_res = client.get(f"/api/farm-brain/today/{farm_id}", headers=farmer_headers)
    assert brain_res.status_code == 200
    data = brain_res.json()

    assert "today_actions" in data
    assert len(data["today_actions"]) > 0

    top_action = data["today_actions"][0]
    assert "title_hi" in top_action or "title_en" in top_action
    assert "priority" in top_action
    assert top_action["priority"] in ("HIGH", "MEDIUM", "NORMAL")
    assert "why_needed_hi" in top_action or "why_needed_en" in top_action
    assert "data_used" in top_action

    # Week outlook
    week_res = client.get(f"/api/farm-brain/week/{farm_id}", headers=farmer_headers)
    assert week_res.status_code == 200
    week_data = week_res.json()
    assert len(week_data["outlook"]) == 7


def test_sms_service_demo_mode(setup_test_users):
    """Verifies SMS broadcast executes gracefully in DEMO MODE without crashing when unconfigured."""
    op_headers = {"Authorization": f"Bearer {setup_test_users['operator_token']}"}

    res = client.post("/api/communications/sms/send", json={
        "mobile_numbers": ["9876543210"],
        "message": "MAITTRI Alert: Weather is clear today. Check irrigation advisory.",
        "category": "weather"
    }, headers=op_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["dispatched_count"] == 1
    assert data["results"][0]["status"] in ("SENT", "SIMULATED_DEMO")


def test_ivr_simulator(setup_test_users):
    """Verifies interactive IVR keypad tree responds with proper speech text and options."""
    farmer_headers = {"Authorization": f"Bearer {setup_test_users['farmer_token']}"}

    # 1. Initial greeting
    res_init = client.post("/api/communications/ivr/simulate", json={
        "phone_number": "9876543210",
        "current_menu": "main",
        "language": "hi"
    }, headers=farmer_headers)
    assert res_init.status_code == 200
    data_init = res_init.json()
    assert "मैत्री किसान सेवा" in data_init["audio_text_hi"]
    assert len(data_init["options"]) > 0

    # 2. Press 1 for Today's Farm Action
    res_opt1 = client.post("/api/communications/ivr/simulate", json={
        "phone_number": "9876543210",
        "current_menu": "main",
        "digits_pressed": "1",
        "language": "hi"
    }, headers=farmer_headers)
    assert res_opt1.status_code == 200
    data_opt1 = res_opt1.json()
    assert len(data_opt1["audio_text_hi"]) > 10

    # 3. Press 4 for Pest & Disease Diagnostic
    res_opt4 = client.post("/api/communications/ivr/simulate", json={
        "phone_number": "9876543210",
        "current_menu": "main",
        "digits_pressed": "4",
        "language": "hi"
    }, headers=farmer_headers)
    assert res_opt4.status_code == 200
    data_opt4 = res_opt4.json()
    assert data_opt4["current_menu"] == "pest_step_1"
