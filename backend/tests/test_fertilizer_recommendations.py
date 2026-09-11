import pytest
from fastapi.testclient import TestClient
import uuid
from app.main import app

client = TestClient(app)

@pytest.fixture(scope="module")
def auth_context():
    random_email = f"farmer_{uuid.uuid4().hex[:8]}@maittri.agri"
    reg_resp = client.post("/api/auth/register", json={
        "email": random_email,
        "password": "Password123!",
        "language": "hi"
    })
    token = reg_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Create a test farm
    farm_resp = client.post("/api/farms", json={
        "name": "Kalyanpur Experimental Farm",
        "area": 2.5,
        "area_unit": "acre",
        "soil_type": "Alluvial soil",
        "previous_crop": "Rice",
        "current_crop": "Wheat",
        "soil_ph": 7.4,
        "soil_n": 180.0,  # Low N
        "soil_p": 24.0,   # Moderate P
        "soil_k": 210.0,  # Moderate K
        "irrigation": "available",
        "latitude": 26.8467,
        "longitude": 80.9462,
        "location_name": "Lucknow, Uttar Pradesh"
    }, headers=headers)
    assert farm_resp.status_code == 200
    farm_id = farm_resp.json()["id"]

    return {"headers": headers, "farm_id": farm_id}


# Test Case 1: Wheat after Rice
def test_wheat_after_rice(auth_context):
    payload = {
        "farm_id": auth_context["farm_id"],
        "current_crop": "Wheat",
        "previous_crop": "Rice",
        "soil_type": "Alluvial soil",
        "crop_stage": "Tillering",
        "soil_n": 190.0,
        "soil_ph": 7.4
    }
    res = client.post("/api/fertilizer/recommend", json=payload, headers=auth_context["headers"])
    assert res.status_code == 200
    data = res.json()
    
    # Verify section A: previous crop analysis notes Rice depletion & puddling
    sec_a = data["section_A_soil_crop_analysis"]
    assert "Rice" in sec_a["previous_crop"]["previous_crop"]
    assert "Likely depleted" in str(sec_a["previous_crop"]["depletion_tendency"].get("Nitrogen", ""))
    assert "hardpan" in sec_a["previous_crop"]["soil_effect"].lower() or "denitrification" in sec_a["previous_crop"]["soil_effect"].lower()

    # Verify section E: chemical N recommendation is justified by Low N
    sec_e = data["section_E_chemical_fertilizer_options"]
    assert any("Urea" in opt["name"] for opt in sec_e)

    # Verify no pest recommendation because no pest was entered
    sec_f = data["section_F_pest_disease_analysis"]
    assert sec_f["evidence_found"] is False
    assert "Preventive monitoring" in sec_f["status"] or "Preventive monitoring" in sec_f.get("verdict", "")
    assert len(data["section_G_chemical_pesticide_options"]) == 0


# Test Case 2: Wheat after Maize
def test_wheat_after_maize(auth_context):
    payload = {
        "current_crop": "Wheat",
        "previous_crop": "Maize",
        "soil_type": "Loamy soil",
        "crop_stage": "Crown Root Initiation (CRI)"
    }
    res = client.post("/api/fertilizer/analyze", json=payload)
    assert res.status_code == 200
    data = res.json()
    sec_a = data["section_A_soil_crop_analysis"]
    assert "Maize" in sec_a["previous_crop"]["previous_crop"]
    assert "Likely depleted" in str(sec_a["previous_crop"]["depletion_tendency"].get("Nitrogen", ""))


# Test Case 3: Rice after Wheat
def test_rice_after_wheat(auth_context):
    payload = {
        "current_crop": "Rice",
        "previous_crop": "Wheat",
        "soil_type": "Clay loam",
        "crop_stage": "Tillering"
    }
    res = client.post("/api/fertilizer/analyze", json=payload)
    assert res.status_code == 200
    data = res.json()
    sec_a = data["section_A_soil_crop_analysis"]
    assert "Wheat" in sec_a["previous_crop"]["previous_crop"]


# Test Case 4: Low Nitrogen Condition
def test_low_nitrogen_condition():
    payload = {
        "current_crop": "Wheat",
        "soil_n": 150.0,  # Below 280 kg/ha -> Low
        "soil_p": 22.0,
        "soil_k": 200.0,
        "crop_stage": "Tillering"
    }
    res = client.post("/api/fertilizer/analyze", json=payload)
    assert res.status_code == 200
    data = res.json()
    sec_b = data["section_B_nutrient_status"]
    n_entry = next((n for n in sec_b["nutrients"] if n["symbol"] == "N"), None)
    assert n_entry is not None
    assert n_entry["status"] == "Low"
    assert "Nitrogen" in sec_b["deficits"]

    # Chemical option should specifically address Low Nitrogen
    sec_e = data["section_E_chemical_fertilizer_options"]
    assert any("Nitrogenous" in opt.get("category", "") for opt in sec_e)


# Test Case 5: Adequate Nitrogen Condition
def test_adequate_nitrogen_condition():
    payload = {
        "current_crop": "Wheat",
        "soil_n": 350.0,  # 280-560 -> Moderate/Adequate
        "soil_p": 20.0,
        "soil_k": 220.0,
        "crop_stage": "Tillering"
    }
    res = client.post("/api/fertilizer/analyze", json=payload)
    assert res.status_code == 200
    data = res.json()
    sec_b = data["section_B_nutrient_status"]
    n_entry = next((n for n in sec_b["nutrients"] if n["symbol"] == "N"), None)
    assert n_entry["status"] in ("Moderate", "Adequate")
    assert "Nitrogen" not in sec_b["deficits"]


# Test Case 6: Unknown Nitrogen Condition
def test_unknown_nitrogen_condition():
    payload = {
        "current_crop": "Wheat",
        "soil_n": None,
        "soil_p": None,
        "soil_k": None
    }
    res = client.post("/api/fertilizer/analyze", json=payload)
    assert res.status_code == 200
    data = res.json()
    sec_b = data["section_B_nutrient_status"]
    n_entry = next((n for n in sec_b["nutrients"] if n["symbol"] == "N"), None)
    assert n_entry["status"] == "Unknown"
    assert n_entry["value"] is None


# Test Case 7: pH Available Condition
def test_ph_available():
    payload = {
        "current_crop": "Wheat",
        "soil_ph": 7.4
    }
    res = client.post("/api/fertilizer/analyze", json=payload)
    assert res.status_code == 200
    sec_a = res.json()["section_A_soil_crop_analysis"]
    ph_data = sec_a["soil"]["ph_analysis"]
    assert ph_data["value"] == 7.4
    assert ph_data["status"] == "Near Neutral"


# Test Case 8: pH Unavailable Condition (Confidence reduced, not blocked)
def test_ph_unavailable():
    payload = {
        "current_crop": "Wheat",
        "soil_ph": None
    }
    res = client.post("/api/fertilizer/analyze", json=payload)
    assert res.status_code == 200
    sec_a = res.json()["section_A_soil_crop_analysis"]
    ph_data = sec_a["soil"]["ph_analysis"]
    assert ph_data["value"] is None
    assert "confidence reduced" in ph_data["confidence_note"].lower()


# Test Case 9: Sensor Data Available (Sensor-based indicative label)
def test_sensor_data_available():
    payload = {
        "current_crop": "Wheat",
        "data_source": "sensor",
        "soil_n": 210.0,
        "soil_p": 16.0,
        "soil_k": 180.0
    }
    res = client.post("/api/fertilizer/analyze", json=payload)
    assert res.status_code == 200
    data = res.json()
    sec_b = data["section_B_nutrient_status"]
    assert "Sensor-based indicative reading" in sec_b["source"]
    assert sec_b["is_sensor"] is True
    assert sec_b["sensor_caveat"] is not None


# Test Case 10: Sensor Data Unavailable
def test_sensor_data_unavailable():
    payload = {
        "current_crop": "Wheat",
        "data_source": "farmer_input"
    }
    res = client.post("/api/fertilizer/analyze", json=payload)
    assert res.status_code == 200
    sec_b = res.json()["section_B_nutrient_status"]
    assert sec_b["is_sensor"] is False


# Test Case 11: Laboratory Soil Report Available (High Confidence)
def test_laboratory_soil_report_available():
    payload = {
        "current_crop": "Wheat",
        "data_source": "laboratory",
        "soil_ph": 7.2,
        "soil_n": 220.0,
        "soil_p": 18.0,
        "soil_k": 190.0,
        "crop_stage": "Tillering"
    }
    res = client.post("/api/fertilizer/recommend", json=payload)
    assert res.status_code == 200
    data = res.json()
    sec_k = data["section_K_confidence_and_explanation"]
    assert sec_k["confidence_level"] == "High"
    assert any("Laboratory" in r for r in sec_k["confidence_reasons"])


# Test Case 12: No Soil Report
def test_no_soil_report():
    payload = {
        "current_crop": "Wheat",
        "data_source": "estimated"
    }
    res = client.post("/api/fertilizer/recommend", json=payload)
    assert res.status_code == 200
    data = res.json()
    sec_k = data["section_K_confidence_and_explanation"]
    assert sec_k["confidence_level"] in ("Medium", "Low")


# Test Case 13: Pest Identified (Evidence-based IPM + Chemical option)
def test_pest_identified():
    payload = {
        "crop": "Wheat",
        "pest_observed": "Yellow Rust",
        "symptoms": "Yellow stripe pustules on leaf blades",
        "affected_area_pct": 12.0,
        "crop_stage": "Heading"
    }
    res = client.post("/api/pest/recommend", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["evidence_found"] is True
    assert data["target_identified"] is True
    assert "Yellow Rust" in data["pest_name"]
    # Biological & cultural controls must be provided first
    assert len(data["natural_biological_options"]) > 0
    # Chemical control is present with PPE warnings and label compliance
    chem = data["chemical_option"]
    assert chem is not None
    assert "Propiconazole" in chem["active_ingredient"] or "Tebuconazole" in chem["active_ingredient"]
    assert chem["ppe_warning"] is not None
    assert chem["pre_harvest_interval"] is not None


# Test Case 14: No Pest Identified (Preventive monitoring only, NO chemical)
def test_no_pest_identified():
    payload = {
        "crop": "Wheat",
        "pest_observed": None,
        "disease_observed": None,
        "symptoms": None
    }
    res = client.post("/api/pest/recommend", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["evidence_found"] is False
    assert "Preventive monitoring" in data["verdict"]
    assert len(data["chemical_options"]) == 0


# Test Case 15: Unknown Pest
def test_unknown_pest():
    payload = {
        "crop": "Wheat",
        "pest_observed": "Strange unidentified black crawling beetle",
        "symptoms": "Leaf nibbling in small corner",
        "affected_area_pct": 2.0
    }
    res = client.post("/api/pest/recommend", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["evidence_found"] is True
    assert data["target_identified"] is False
    assert len(data["chemical_options"]) == 0
    assert "KVK" in str(data["natural_ipm_guidance"])


# Test Case 16: Weather Data Available (Rain / Wind warning)
def test_weather_data_warnings():
    from app.services.fertilizer_recommendation_service import evaluate_weather_risks
    fake_weather = {
        "current": {"temperature_2m": 24.0, "relative_humidity_2m": 60.0, "wind_speed_10m": 18.0},  # High wind
        "hourly": {"precipitation_probability": [75, 80, 85], "wind_speed_10m": [18, 20, 19]},      # Heavy rain
        "daily": {"precipitation_sum": [15.0, 5.0]}
    }
    advisories = evaluate_weather_risks(fake_weather, {"crop": "Wheat"})
    assert any("Wash-off" in adv["title"] for adv in advisories)
    assert any("Spray Drift" in adv["title"] for adv in advisories)


# Test Case 17: Weather Unavailable
def test_weather_unavailable():
    from app.services.fertilizer_recommendation_service import evaluate_weather_risks
    advisories = evaluate_weather_risks(None, {"crop": "Wheat"})
    assert len(advisories) == 1
    assert "Not Linked" in advisories[0]["title"]


# Test Case 18: Incomplete Farm History
def test_incomplete_farm_history():
    payload = {
        "current_crop": "Mustard",
        "previous_crop": None,
        "soil_type": None,
        "soil_ph": None,
        "soil_n": None
    }
    res = client.post("/api/fertilizer/recommend", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["farm_context"]["current_crop"] == "Mustard"
    # Fallback to Alluvial soil without failure
    assert data["section_A_soil_crop_analysis"]["soil"]["soil_type"] is not None


# Test Case 19: Validation Rejections
def test_validation_rejections():
    # Invalid pH < 3.0
    res_ph = client.post("/api/fertilizer/analyze", json={
        "current_crop": "Wheat",
        "soil_ph": 1.5
    })
    assert res_ph.status_code == 422 or res_ph.status_code == 400

    # Invalid Moisture > 100%
    res_moist = client.post("/api/fertilizer/analyze", json={
        "current_crop": "Wheat",
        "soil_moisture": 120.0
    })
    assert res_moist.status_code == 422 or res_moist.status_code == 400

    # Missing current crop
    res_crop = client.post("/api/fertilizer/analyze", json={
        "current_crop": ""
    })
    assert res_crop.status_code == 422 or res_crop.status_code == 400


# Test Case 20: History Logging & Sources API
def test_history_logging_and_sources(auth_context):
    # Log a fertilizer application
    app_res = client.post("/api/fertilizer/history", json={
        "farm_id": auth_context["farm_id"],
        "crop": "Wheat",
        "fertilizer_type": "organic",
        "fertilizer_name": "Vermicompost",
        "application_stage": "Basal",
        "rate_per_acre": "1 tonne",
        "application_method": "Row placement",
        "notes": "Field well prepared"
    }, headers=auth_context["headers"])
    assert app_res.status_code == 200
    assert app_res.json()["status"] == "success"

    # Fetch history
    hist_res = client.get(f"/api/fertilizer/history?farm_id={auth_context['farm_id']}", headers=auth_context["headers"])
    assert hist_res.status_code == 200
    hist_data = hist_res.json()
    assert len(hist_data["logged_applications"]) > 0
    assert hist_data["logged_applications"][0]["fertilizer_name"] == "Vermicompost"

    # Fetch sources
    src_res = client.get("/api/fertilizer/sources")
    assert src_res.status_code == 200
    assert any("ICAR" in s["name"] for s in src_res.json()["sources"])

    pest_src_res = client.get("/api/pest/sources")
    assert pest_src_res.status_code == 200
    assert any("CIBRC" in s["name"] for s in pest_src_res.json()["sources"])

    # Sensor latest
    sensor_res = client.get("/api/fertilizer/sensor-latest")
    assert sensor_res.status_code == 200
    assert "Sensor-based indicative reading" in sensor_res.json()["type"]
