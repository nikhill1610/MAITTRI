"""
Automated Test Suite for MAITTRI Insurance Planning and Government Schemes
Validates all 20 required scenarios specified in Section 43:
1. Uttar Pradesh + Wheat
2. Punjab + Wheat
3. Maharashtra + Soybean
4. Rajasthan + Mustard
5. Different farm sizes (Marginal, Small, Large)
6. Central schemes (Pan-India availability)
7. State schemes (Strict state isolation; UP vs Punjab vs Maharashtra)
8. Upcoming schemes (Deadline filtering)
9. Open schemes
10. Closed schemes
11. Missing district handling
12. Missing crop handling
13. Missing farm area handling
14. Unknown eligibility evaluation
15. Resilient error handling (404 on invalid IDs)
16. Official source link verification (Official URLs present)
17. Response structure verification (All Sections A-M present)
18. Weather risk evaluation in insurance analysis
19. Insurance + crop statutory premium caps (1.5% Rabi, 2% Kharif, 5% Commercial)
20. Government schemes + crop recommendation integration
"""

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
    return {"headers": headers}


# =========================================================================
# Test Case 1: Uttar Pradesh + Wheat (Insurance & Government Schemes)
# =========================================================================
def test_case_01_uttar_pradesh_wheat():
    # 1. Insurance Analysis for UP + Wheat
    res_ins = client.post("/api/insurance/analyze", json={
        "state": "Uttar Pradesh",
        "district": "Lucknow",
        "crop": "Wheat",
        "season": "rabi",
        "farm_area": 2.5
    })
    assert res_ins.status_code == 200
    ins_data = res_ins.json()
    assert ins_data["section_A_farmer_farm_profile"]["state"] == "Uttar Pradesh"
    assert ins_data["section_B_current_crop"]["crop_name"] == "Wheat"
    assert ins_data["section_G_premium_information"]["farmer_share_statutory_pct"] == "1.5%"
    assert "PMFBY" in ins_data["section_E_relevant_insurance"]["primary_scheme"]["name"]

    # 2. Government Schemes for UP
    res_sch = client.get("/api/government-schemes", params={"state": "Uttar Pradesh"})
    assert res_sch.status_code == 200
    schemes = res_sch.json()
    # Check that Central schemes AND UP schemes are present, but Punjab schemes are absent
    scheme_names = [s["scheme_name"] for s in schemes]
    assert any("PM-KISAN" in name for name in scheme_names)
    assert any("UP Krishi Yantra" in name or "UP" in name for name in scheme_names)
    assert not any("Punjab" in name for name in scheme_names)


# =========================================================================
# Test Case 2: Punjab + Wheat (State Scheme Isolation)
# =========================================================================
def test_case_02_punjab_wheat():
    res_sch = client.get("/api/government-schemes", params={"state": "Punjab"})
    assert res_sch.status_code == 200
    schemes = res_sch.json()
    scheme_names = [s["scheme_name"] for s in schemes]
    # Punjab CRM must be present, UP schemes must NOT be present
    assert any("Punjab Crop Residue" in name for name in scheme_names)
    assert not any("UP Krishi Yantra" in name for name in scheme_names)
    assert not any("Magel Tyala" in name for name in scheme_names)


# =========================================================================
# Test Case 3: Maharashtra + Soybean (Kharif Oilseed 2.0% Cap)
# =========================================================================
def test_case_03_maharashtra_soybean():
    res_ins = client.post("/api/insurance/analyze", json={
        "state": "Maharashtra",
        "district": "Yavatmal",
        "crop": "Soybean",
        "season": "kharif",
        "farm_area": 3.0
    })
    assert res_ins.status_code == 200
    ins_data = res_ins.json()
    # Kharif Soybean farmer premium cap is statutory 2.0%
    assert ins_data["section_G_premium_information"]["farmer_share_statutory_pct"] == "2.0%"
    assert ins_data["section_B_current_crop"]["crop_name"] == "Soybean"

    # Maharashtra state schemes check
    res_sch = client.get("/api/government-schemes", params={"state": "Maharashtra"})
    assert res_sch.status_code == 200
    m_schemes = res_sch.json()
    assert any("Magel Tyala Shet Tale" in s["scheme_name"] for s in m_schemes)


# =========================================================================
# Test Case 4: Rajasthan + Mustard (Rabi Oilseed 1.5% Cap)
# =========================================================================
def test_case_04_rajasthan_mustard():
    res_ins = client.post("/api/insurance/analyze", json={
        "state": "Rajasthan",
        "district": "Bharatpur",
        "crop": "Mustard",
        "season": "rabi",
        "farm_area": 4.0
    })
    assert res_ins.status_code == 200
    ins_data = res_ins.json()
    assert ins_data["section_G_premium_information"]["farmer_share_statutory_pct"] == "1.5%"
    assert ins_data["section_B_current_crop"]["crop_name"] == "Mustard / Rapeseed"

    res_sch = client.get("/api/government-schemes", params={"state": "Rajasthan"})
    assert res_sch.status_code == 200
    raj_schemes = res_sch.json()
    assert any("RajKisan" in s["scheme_name"] or "Rajasthan" in s["scheme_name"] for s in raj_schemes)


# =========================================================================
# Test Case 5: Different Farm Sizes (Marginal, Small, Large)
# =========================================================================
def test_case_05_different_farm_sizes():
    # 1. Marginal Farmer (1.0 Acre = 0.4 ha) for UP Borewell subsidy
    res_marginal = client.post("/api/government-schemes/check-eligibility", json={
        "scheme_id": 102, # UP Mukhyamantri Laghu Sinchayee (<2 ha)
        "state": "Uttar Pradesh",
        "farm_size_acres": 1.0,
        "farmer_category": "Small/Marginal"
    })
    assert res_marginal.status_code == 200
    assert res_marginal.json()["eligibility_status"] == "Potentially Eligible"

    # 2. Large Farmer (15.0 Acres = 6.07 ha) for UP Borewell subsidy (<2 ha limit)
    res_large = client.post("/api/government-schemes/check-eligibility", json={
        "scheme_id": 102,
        "state": "Uttar Pradesh",
        "farm_size_acres": 15.0,
        "farmer_category": "General"
    })
    assert res_large.status_code == 200
    assert res_large.json()["eligibility_status"] == "Not Eligible"


# =========================================================================
# Test Case 6: Central Schemes (Pan-India Presence)
# =========================================================================
def test_case_06_central_schemes():
    # Central schemes should appear regardless of whether state is UP, Punjab, or None
    for st in ["Uttar Pradesh", "Punjab", "Maharashtra", None]:
        params = {"state": st} if st else {}
        res = client.get("/api/government-schemes", params=params)
        assert res.status_code == 200
        data = res.json()
        central_schemes = [s for s in data if s["level"] == "central"]
        assert len(central_schemes) >= 10
        names = [s["scheme_name"] for s in central_schemes]
        assert any("PM-KISAN" in n for n in names)
        assert any("PMFBY" in n for n in names)
        assert any("PM-KUSUM" in n for n in names)


# =========================================================================
# Test Case 7: Strict State Scheme Isolation
# =========================================================================
def test_case_07_state_scheme_isolation():
    # UP should not have Punjab or Maharashtra schemes
    res_up = client.get("/api/government-schemes", params={"state": "Uttar Pradesh"})
    up_names = [s["scheme_name"] for s in res_up.json()]
    assert not any("Punjab" in n for n in up_names)
    assert not any("Maharashtra" in n for n in up_names)
    assert not any("Rajasthan" in n for n in up_names)

    # Maharashtra should not have UP or Haryana schemes
    res_mh = client.get("/api/government-schemes", params={"state": "Maharashtra"})
    mh_names = [s["scheme_name"] for s in res_mh.json()]
    assert not any("UP Krishi" in n for n in mh_names)
    assert not any("Mera Pani" in n for n in mh_names)


# =========================================================================
# Test Case 8: Upcoming Schemes (Deadline / Season Windows)
# =========================================================================
def test_case_08_upcoming_schemes():
    res = client.get("/api/government-schemes/upcoming", params={"state": "Uttar Pradesh"})
    assert res.status_code == 200
    data = res.json()
    assert len(data) > 0
    # Every scheme in upcoming should have status Upcoming, Closing Soon, or Open
    for s in data:
        assert s["status"] in ["Upcoming", "Closing Soon", "Open"]


# =========================================================================
# Test Case 9: Open Schemes
# =========================================================================
def test_case_09_open_schemes():
    res = client.get("/api/government-schemes", params={"status": "Open"})
    assert res.status_code == 200
    data = res.json()
    assert len(data) > 0
    for s in data:
        assert s["status"] == "Open"


# =========================================================================
# Test Case 10: Closed Schemes
# =========================================================================
def test_case_10_closed_schemes():
    res = client.get("/api/government-schemes", params={"status": "Closed"})
    assert res.status_code == 200
    data = res.json()
    assert len(data) > 0
    for s in data:
        assert s["status"] == "Closed"


# =========================================================================
# Test Case 11: Missing District Handling
# =========================================================================
def test_case_11_missing_district():
    res = client.post("/api/insurance/analyze", json={
        "state": "Uttar Pradesh",
        "district": None,
        "crop": "Wheat",
        "season": "rabi"
    })
    assert res.status_code == 200
    data = res.json()
    # District should be defaulted gracefully without throwing error
    assert data["section_A_farmer_farm_profile"]["district"] is not None


# =========================================================================
# Test Case 12: Missing Crop Handling
# =========================================================================
def test_case_12_missing_crop():
    res = client.post("/api/insurance/analyze", json={
        "state": "Uttar Pradesh",
        "crop": None
    })
    assert res.status_code == 200
    data = res.json()
    # Should default gracefully to standard crop
    assert data["section_B_current_crop"]["crop_name"] is not None


# =========================================================================
# Test Case 13: Missing Farm Area Handling
# =========================================================================
def test_case_13_missing_farm_area():
    res = client.post("/api/insurance/analyze", json={
        "state": "Uttar Pradesh",
        "crop": "Wheat",
        "farm_area": None
    })
    assert res.status_code == 200
    data = res.json()
    assert data["section_A_farmer_farm_profile"]["farm_area_acres"] > 0


# =========================================================================
# Test Case 14: Unknown Eligibility Evaluation
# =========================================================================
def test_case_14_unknown_eligibility():
    # When critical state info is missing for a state-specific scheme
    res = client.post("/api/government-schemes/check-eligibility", json={
        "scheme_id": 101, # UP Krishi Yantra (State scheme)
        "state": None,
        "farm_size_acres": None
    })
    assert res.status_code == 200
    data = res.json()
    assert data["eligibility_status"] == "Insufficient Information"
    assert len(data["missing_information"]) > 0


# =========================================================================
# Test Case 15: Resilient Error Handling (404 on Invalid IDs)
# =========================================================================
def test_case_15_resilient_error_handling():
    res = client.get("/api/government-schemes/999999")
    assert res.status_code == 404
    assert "not found" in res.json()["detail"].lower()

    res_ins = client.get("/api/insurance/999999")
    assert res_ins.status_code == 404


# =========================================================================
# Test Case 16: Official Source Link Verification
# =========================================================================
def test_case_16_official_source_links():
    res = client.get("/api/government-schemes")
    assert res.status_code == 200
    schemes = res.json()
    for s in schemes:
        assert s["official_url"].startswith("http://") or s["official_url"].startswith("https://")
        assert s["official_source"] is not None
        assert s["last_verified"] is not None


# =========================================================================
# Test Case 17: Response Structure Verification (Sections A through M)
# =========================================================================
def test_case_17_sections_a_through_m_present():
    res = client.post("/api/insurance/analyze", json={
        "state": "Uttar Pradesh",
        "district": "Lucknow",
        "crop": "Wheat",
        "season": "rabi",
        "farm_area": 2.5
    })
    assert res.status_code == 200
    data = res.json()
    for section_letter in ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L", "M"]:
        key_matches = [k for k in data.keys() if f"section_{section_letter}_" in k]
        assert len(key_matches) == 1, f"Section {section_letter} missing from insurance response"


# =========================================================================
# Test Case 18: Weather Risk Evaluation in Insurance
# =========================================================================
def test_case_18_weather_risk_evaluation():
    res = client.post("/api/insurance/analyze", json={
        "state": "Uttar Pradesh",
        "crop": "Wheat",
        "season": "rabi",
        "include_weather_risk": True
    })
    assert res.status_code == 200
    data = res.json()
    sec_d = data["section_D_risk_analysis"]
    assert "Potential agricultural risk detected" in sec_d["mandatory_risk_disclaimer"]
    assert len(sec_d["potential_risks_detected"]) > 0


# =========================================================================
# Test Case 19: Statutory Premium Caps (Commercial 5% vs Foodgrain 1.5%/2.0%)
# =========================================================================
def test_case_19_statutory_premium_caps():
    # 1. Sugarcane (Commercial) -> 5.0%
    res_sugar = client.post("/api/insurance/analyze", json={
        "state": "Uttar Pradesh",
        "crop": "Sugarcane",
        "season": "commercial"
    })
    assert res_sugar.json()["section_G_premium_information"]["farmer_share_statutory_pct"] == "5.0%"

    # 2. Rice (Kharif Foodgrain) -> 2.0%
    res_rice = client.post("/api/insurance/analyze", json={
        "state": "Uttar Pradesh",
        "crop": "Rice",
        "season": "kharif"
    })
    assert res_rice.json()["section_G_premium_information"]["farmer_share_statutory_pct"] == "2.0%"

    # 3. Wheat (Rabi Foodgrain) -> 1.5%
    res_wheat = client.post("/api/insurance/analyze", json={
        "state": "Uttar Pradesh",
        "crop": "Wheat",
        "season": "rabi"
    })
    assert res_wheat.json()["section_G_premium_information"]["farmer_share_statutory_pct"] == "1.5%"


# =========================================================================
# Test Case 20: Government Schemes + Crop Search & Integration
# =========================================================================
def test_case_20_scheme_crop_and_keyword_search():
    # Search "tractor" should return mechanization schemes
    res_tractor = client.get("/api/government-schemes", params={"search": "tractor"})
    assert res_tractor.status_code == 200
    tractor_schemes = res_tractor.json()
    assert len(tractor_schemes) > 0
    assert any("Machinery" in s["category"] for s in tractor_schemes)

    # Search "solar" should return PM-KUSUM
    res_solar = client.get("/api/government-schemes", params={"search": "solar"})
    assert res_solar.status_code == 200
    assert any("KUSUM" in s["scheme_name"] for s in res_solar.json())
