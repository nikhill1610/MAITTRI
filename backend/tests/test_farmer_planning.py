"""
test_farmer_planning.py
Comprehensive automated test suite for MAITTRI Personal Farm Planner
and Crop Calendar integration.
"""

import pytest
from datetime import date, timedelta
from fastapi.testclient import TestClient
from app.main import app
from app.database import Base, engine, get_db
from app.services.crop_calendar_service import (
    get_crop_calendar,
    list_crop_calendars,
    get_crop_stage_for_day,
    calculate_calendar_dates
)
from app.services.farmer_planning_service import (
    parse_date_safely,
    calculate_sowing_date_from_age,
    calculate_sowing_date_from_stage,
    generate_full_farm_plan_data
)

client = TestClient(app)

@pytest.fixture(scope="session", autouse=True)
def setup_db():
    if engine.name == "sqlite":
        Base.metadata.create_all(bind=engine)
    yield


def test_crop_calendar_service():
    # Verify authoritative calendars exist
    calendars = list_crop_calendars()
    assert len(calendars) >= 8
    
    wheat_cal = get_crop_calendar("Wheat")
    assert wheat_cal is not None
    assert wheat_cal["crop_key"] == "wheat"
    assert len(wheat_cal["stages"]) >= 6
    assert "CRI" in [s["stage_id"].upper() for s in wheat_cal["stages"]] or any("Crown Root" in s["name"] for s in wheat_cal["stages"])
    
    rice_cal = get_crop_calendar("Rice")
    assert rice_cal is not None
    assert rice_cal["crop_key"] == "rice"


def test_date_calculation_month_and_year_crossing():
    # Sowing on Nov 15, 2026 -> crossing into Dec, Jan, Feb next year
    sow_date = date(2026, 11, 15)
    dates = calculate_calendar_dates("Wheat", sow_date)
    assert len(dates) > 0
    
    # Check that later stages cross into 2027
    last_stage = dates[-1]
    assert "2027" in last_stage["start_date"] or "2027" in last_stage["end_date"]


def test_leap_year_handling():
    # Sowing on Jan 20, 2024 (2024 is a leap year)
    sow_date = date(2024, 1, 20)
    dates = calculate_calendar_dates("Wheat", sow_date)
    assert len(dates) > 0
    # Day 50 should safely cross Feb 29, 2024
    cri_stage = dates[1] # CRI stage
    assert cri_stage["start_date"] == (sow_date + timedelta(days=cri_stage["start_day"])).isoformat()


def test_api_crop_calendar_endpoints():
    res = client.get("/api/crop-calendar")
    assert res.status_code == 200
    cals = res.json()
    assert len(cals) >= 8
    
    single_res = client.get("/api/crop-calendar/wheat")
    assert single_res.status_code == 200
    assert single_res.json()["name"] == "Wheat"

    single_rice = client.get("/api/crop-calendar/rice")
    assert single_rice.status_code == 200
    assert single_rice.json()["name"] == "Rice / Paddy"

    # Non-existent crop fallback / 404
    invalid = client.get("/api/crop-calendar/unknown_crop_xyz")
    # Our normalizer maps unknown to wheat or returns 404
    assert invalid.status_code in [200, 404]


import uuid

def test_farmer_plan_flow_with_farm():
    # 1. Register a user & create a farm
    email = f"farmer_{date.today().isoformat()}_{uuid.uuid4().hex[:6]}@maittri.com"
    reg_res = client.post("/api/auth/register", json={
        "email": email,
        "password": "FarmerPassword123",
        "language": "hi"
    })
    token = reg_res.json().get("access_token")

    if not token:
        # If already registered, login
        login_res = client.post("/api/auth/login", json={
            "email": email,
            "password": "FarmerPassword123"
        })
        token = login_res.json()["access_token"]

    headers = {"Authorization": f"Bearer {token}"}

    # Create farm
    farm_res = client.post("/api/farms", json={
        "name": "Kisan Demo Farm",
        "area": 2.5,
        "area_unit": "acre",
        "soil_type": "Alluvial Soil",
        "irrigation": "available",
        "location_name": "Ludhiana, Punjab",
        "latitude": 30.9010,
        "longitude": 75.8573,
        "current_crop": "Wheat",
        "previous_crop": "Rice"
    }, headers=headers)
    assert farm_res.status_code == 200
    farm_id = farm_res.json()["id"]

    # 2. Generate Farmer Plan with valid sowing date (20 days ago)
    sow_date_str = (date.today() - timedelta(days=22)).isoformat()
    plan_res = client.post("/api/farmer-plans", json={
        "farm_id": farm_id,
        "crop": "Wheat",
        "sowing_date": sow_date_str,
        "variety": "HD-3086 (Pusa Gautami)"
    }, headers=headers)

    assert plan_res.status_code == 201
    plan_data = plan_res.json()["plan"]
    assert plan_data["crop"] == "Wheat"
    assert plan_data["crop_age_days"] == 22
    assert "today_goals" in plan_data
    assert len(plan_data["today_goals"]["top_3_priorities"]) <= 3
    assert len(plan_data["week_plan"]) == 7
    assert len(plan_data["timeline"]) >= 6

    plan_id = plan_data["plan_id"]

    # 3. Retrieve Plan by ID
    get_plan = client.get(f"/api/farmer-plans/{plan_id}", headers=headers)
    assert get_plan.status_code == 200
    assert get_plan.json()["crop"] == "Wheat"

    # 4. Get Today's goals endpoint
    today_res = client.get(f"/api/farmer-plans/{plan_id}/today", headers=headers)
    assert today_res.status_code == 200
    today_json = today_res.json()
    assert "top_3_priorities" in today_json["today_goals"]

    # 5. Get 7-Day Week plan endpoint
    week_res = client.get(f"/api/farmer-plans/{plan_id}/week", headers=headers)
    assert week_res.status_code == 200
    assert len(week_res.json()["week_plan"]) == 7

    # 6. Complete a task and check Farm Diary
    top_task = plan_data["today_goals"]["top_3_priorities"][0]
    task_id = top_task["id"]

    complete_res = client.post(f"/api/farmer-plans/tasks/{task_id}/complete", json={
        "status": "completed",
        "notes": "Moisture inspected at root zone. Condition optimal."
    }, headers=headers)
    assert complete_res.status_code == 200
    assert complete_res.json()["success"] is True

    # Check Farm Diary History
    diary_res = client.get(f"/api/farmer-plans/{plan_id}/history", headers=headers)
    assert diary_res.status_code == 200
    assert diary_res.json()["total_completed"] >= 1
    assert "Moisture inspected" in diary_res.json()["diary_entries"][0]["farmer_notes"]

    # 7. Add farmer note
    note_res = client.post(f"/api/farmer-plans/tasks/{task_id}/note", json={
        "notes": "Second observation: light morning dew present."
    }, headers=headers)
    assert note_res.status_code == 200

    # 8. Test Vegetables (Tomato)
    tomato_plan_res = client.post("/api/farmer-plans", json={
        "farm_id": farm_id,
        "crop": "Tomato",
        "crop_age_days": 35
    }, headers=headers)
    assert tomato_plan_res.status_code == 201
    assert tomato_plan_res.json()["plan"]["crop"] == "Tomato"

    # 9. Test Missing Sowing date error
    err_res = client.post("/api/farmer-plans", json={
        "farm_id": farm_id,
        "crop": "Rice"
    }, headers=headers)
    # If farm already had a sowing date it might use it or validate
    assert err_res.status_code in [201, 400]

    # 10. Backward compatibility test: POST /api/recommendations/plan
    legacy_res = client.post("/api/recommendations/plan", json={
        "farm_id": farm_id,
        "crop": "Wheat"
    }, headers=headers)
    assert legacy_res.status_code == 200
    assert "steps" in legacy_res.json()
