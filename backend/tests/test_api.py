import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

@pytest.fixture(scope="module")
def auth_header():
    import uuid
    random_email = f"test_{uuid.uuid4().hex[:8]}@example.com"
    reg_resp = client.post("/api/auth/register", json={
        "email": random_email,
        "password": "Password123!",
        "language": "en"
    })
    assert reg_resp.status_code == 200, f"Registration failed: {reg_resp.text}"
    token = reg_resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_root_and_health():
    res_root = client.get("/")
    assert res_root.status_code == 200
    assert "Smart Agriculture AI API" in res_root.json()["message"]

    res_health = client.get("/api/health")
    assert res_health.status_code == 200
    assert res_health.json() == {"status": "ok"}


def test_email_validator_enforcement():
    # Valid email succeeds
    import uuid
    valid_email = f"farmer_{uuid.uuid4().hex[:6]}@agri-domain.org"
    res_valid = client.post("/api/auth/register", json={
        "email": valid_email,
        "password": "Password123!",
        "language": "en"
    })
    assert res_valid.status_code == 200
    assert "access_token" in res_valid.json()

    # Invalid email fails with 422 Unprocessable Entity via email-validator
    res_invalid = client.post("/api/auth/register", json={
        "email": "not-a-valid-email-format",
        "password": "Password123!",
        "language": "en"
    })
    assert res_invalid.status_code == 422


def test_auth_login():
    import uuid
    email = f"login_test_{uuid.uuid4().hex[:6]}@example.com"
    client.post("/api/auth/register", json={
        "email": email,
        "password": "SecretPassword123",
        "language": "hi"
    })

    # Correct login
    res_login = client.post("/api/auth/login", json={
        "email": email,
        "password": "SecretPassword123"
    })
    assert res_login.status_code == 200
    assert "access_token" in res_login.json()

    # Wrong password
    res_wrong = client.post("/api/auth/login", json={
        "email": email,
        "password": "WrongPassword"
    })
    assert res_wrong.status_code == 401


def test_farm_lifecycle(auth_header):
    # 1. Create farm
    farm_data = {
        "name": "Green Valley Farm",
        "latitude": 18.5204,
        "longitude": 73.8567,
        "location_name": "Pune, Maharashtra",
        "area": 2.5,
        "area_unit": "acre",
        "soil_type": "Loamy soil",
        "irrigation": "available",
        "previous_crop": "Rice",
        "soil_n": 55.0,
        "soil_p": 25.0,
        "soil_k": 35.0,
        "soil_ph": 6.8
    }
    create_res = client.post("/api/farms", json=farm_data, headers=auth_header)
    assert create_res.status_code == 200, f"Farm creation failed: {create_res.text}"
    farm_id = create_res.json()["id"]
    assert farm_id is not None
    assert create_res.json()["name"] == "Green Valley Farm"

    # 2. List farms
    list_res = client.get("/api/farms", headers=auth_header)
    assert list_res.status_code == 200
    farms = list_res.json()
    assert any(f["id"] == farm_id for f in farms)

    # 3. Get specific farm
    get_res = client.get(f"/api/farms/{farm_id}", headers=auth_header)
    assert get_res.status_code == 200
    assert get_res.json()["location_name"] == "Pune, Maharashtra"

    # 4. Update farm
    update_res = client.put(f"/api/farms/{farm_id}", json={"name": "Updated Farm Name", "area": 3.0}, headers=auth_header)
    assert update_res.status_code == 200
    assert update_res.json()["name"] == "Updated Farm Name"
    assert update_res.json()["area"] == 3.0

    # 5. Get recommendations
    rec_res = client.post("/api/recommendations", json={
        "farm_id": farm_id,
        "season": "rabi",
        "budget": 50000,
        "market_preference": "balanced"
    }, headers=auth_header)
    assert rec_res.status_code == 200
    rec_data = rec_res.json()
    assert "recommendations" in rec_data
    assert len(rec_data["recommendations"]) > 0
    first_crop = rec_data["recommendations"][0]["crop"]

    # 6. Create farming plan
    plan_res = client.post("/api/recommendations/plan", json={
        "farm_id": farm_id,
        "crop": first_crop
    }, headers=auth_header)
    assert plan_res.status_code == 200
    plan_data = plan_res.json()
    assert plan_data["crop"].lower() == first_crop.lower()
    assert "steps" in plan_data
    assert len(plan_data["steps"]) > 0

    # 7. Plan for nonexistent crop
    invalid_plan = client.post("/api/recommendations/plan", json={
        "farm_id": farm_id,
        "crop": "NonExistentCrop123"
    }, headers=auth_header)
    assert invalid_plan.status_code == 400

    # 8. Delete farm
    del_res = client.delete(f"/api/farms/{farm_id}", headers=auth_header)
    assert del_res.status_code == 200

    # 9. Verify 404 after deletion
    get_del = client.get(f"/api/farms/{farm_id}", headers=auth_header)
    assert get_del.status_code == 404


def test_weather_endpoint():
    import time
    for attempt in range(2):
        res = client.post("/api/weather", json={
            "latitude": 18.5204,
            "longitude": 73.8567,
            "location_name": "Pune, Maharashtra",
            "forecast_days": 7
        })
        if res.status_code == 200:
            break
        time.sleep(1)
    assert res.status_code == 200
    data = res.json()
    assert "current" in data
    assert "daily" in data
    assert "hourly" in data
    assert "advisories" in data
    assert "spraying" in data["advisories"]
    assert "irrigation" in data["advisories"]


def test_location_search_and_reverse():
    import time
    # Location Search with retry for public API rate limits
    for attempt in range(2):
        search_res = client.get("/api/location/search", params={"query": "Pune", "count": 3})
        if search_res.status_code == 200:
            break
        time.sleep(1)
    assert search_res.status_code == 200
    results = search_res.json().get("results", [])
    assert len(results) > 0
    assert any("Pune" in r["display_name"] for r in results)

    # Reverse Geocoding
    for attempt in range(2):
        reverse_res = client.get("/api/location/reverse", params={"latitude": 18.5204, "longitude": 73.8567})
        if reverse_res.status_code == 200:
            break
        time.sleep(1)
    assert reverse_res.status_code == 200
    rev_data = reverse_res.json()
    assert "display_name" in rev_data


def test_soil_estimation_endpoints():
    # 1. POST /api/soil/estimate
    post_res = client.post("/api/soil/estimate", json={"latitude": 28.6139, "longitude": 77.2090})
    assert post_res.status_code == 200
    data = post_res.json()
    assert "probable_soil_type" in data
    assert data["confidence"] in ["High", "Medium", "Low"]
    assert "source" in data
    assert "methodology" in data
    assert "disclaimer" in data

    # 2. GET /api/soil/estimate
    get_res = client.get("/api/soil/estimate", params={"latitude": 19.0760, "longitude": 72.8777})
    assert get_res.status_code == 200
    assert "probable_soil_type" in get_res.json()

    # 3. GET /api/soil/types
    types_res = client.get("/api/soil/types")
    assert types_res.status_code == 200
    types_list = types_res.json().get("soil_types", [])
    assert "Alluvial Soil" in types_list
    assert "Black Soil" in types_list
    assert "Red Soil" in types_list


def test_nutrient_analysis_lifecycle(auth_header):
    # 1. Create a test farm with crop sequence and optional pH
    farm_data = {
        "name": "Agri Intelligence Test Plot",
        "latitude": 26.8467,
        "longitude": 80.9462,
        "location_name": "Lucknow, Uttar Pradesh",
        "location_source": "gps",
        "area": 4.0,
        "area_unit": "acre",
        "soil_type": "Alluvial Soil",
        "soil_type_source": "auto_detected",
        "soil_confidence": "High",
        "soil_ph": 7.2,
        "irrigation": "available",
        "previous_crop": "Wheat",
        "previous_crop_period": "November - April",
        "current_crop": "Mustard",
        "cultivation_count": 2
    }
    farm_res = client.post("/api/farms", json=farm_data, headers=auth_header)
    assert farm_res.status_code == 200
    farm_id = farm_res.json()["id"]

    try:
        # 2. POST /api/nutrients/analyze using farm_id
        analysis_res = client.post("/api/nutrients/analyze", json={"farm_id": farm_id}, headers=auth_header)
        assert analysis_res.status_code == 200
        analysis = analysis_res.json()

        # Verify Farm context
        assert analysis["farm"]["name"] == "Agri Intelligence Test Plot"
        assert analysis["farm"]["soil_type"] == "Alluvial Soil"
        assert analysis["farm"]["previous_crop"] == "Wheat"
        assert analysis["farm"]["current_crop"] == "Mustard"
        assert analysis["farm"]["soil_ph"] == 7.2

        # Verify 11 nutrients present
        nutrients = analysis["nutrients"]
        assert len(nutrients) == 11
        symbols = [n["symbol"] for n in nutrients]
        for expected in ["N", "P", "K", "S", "Ca", "Mg", "Zn", "Fe", "B", "Mn", "Cu"]:
            assert expected in symbols

        # Verify nutrient fields structure
        for n in nutrients:
            assert n["status"] in ["Likely depleted", "Possibly depleted", "Likely adequate", "Unknown / requires soil test"]
            assert n["confidence"] in ["High", "Medium", "Low"]
            assert len(n["reason"]) > 0
            assert len(n["verification"]) > 0

        # Verify summary breakdown
        summary = analysis["summary"]
        assert "potentially_depleted" in summary
        assert "possibly_depleted" in summary
        assert "likely_adequate" in summary
        assert "requires_testing" in summary

        # 3. GET /api/nutrients/{farm_id}
        get_nutrients = client.get(f"/api/nutrients/{farm_id}", headers=auth_header)
        assert get_nutrients.status_code == 200
        saved_nutrients = get_nutrients.json()
        assert "nutrients" in saved_nutrients
        assert len(saved_nutrients["nutrients"]) == 11

        # 4. Ad-hoc analysis without saving farm (raw request)
        adhoc_res = client.post("/api/nutrients/analyze", json={
            "soil_type": "Sandy Soil",
            "previous_crop": "Rice",
            "current_crop": "Wheat",
            "cultivation_count": 3
        }, headers=auth_header)
        assert adhoc_res.status_code == 200
        adhoc_data = adhoc_res.json()
        assert len(adhoc_data["nutrients"]) == 11
        # In sandy soil with intensive rice-wheat rotation, N is high demand
        n_elem = next(x for x in adhoc_data["nutrients"] if x["symbol"] == "N")
        assert n_elem["status"] in ["Likely depleted", "Possibly depleted"]

    finally:
        # Cleanup
        client.delete(f"/api/farms/{farm_id}", headers=auth_header)


def test_parali_crops_and_methods_endpoints():
    # 1. GET /api/parali/crops
    res_crops = client.get("/api/parali/crops")
    assert res_crops.status_code == 200
    crops = res_crops.json()
    assert len(crops) >= 8
    keys = [c["key"] for c in crops]
    assert "rice" in keys
    assert "wheat" in keys
    assert "cotton" in keys
    assert "sugarcane" in keys

    # 2. GET /api/parali/methods
    res_methods = client.get("/api/parali/methods")
    assert res_methods.status_code == 200
    methods = res_methods.json()
    assert len(methods) >= 6
    m_ids = [m["method_id"] for m in methods]
    assert "in_situ_mulch_direct_seeding" in m_ids
    assert "in_situ_incorporation" in m_ids
    assert "ex_situ_baling" in m_ids


def test_parali_scenarios_and_burning_warning(auth_header):
    # TEST 1: Rice, 5 acres, No machinery, Goal = "recommend_best"
    res1 = client.post("/api/parali/analyze", json={
        "crop": "rice",
        "area": 5.0,
        "area_unit": "acre",
        "machinery_available": "no",
        "farmer_goal": "recommend_best",
    }, headers=auth_header)
    assert res1.status_code == 200
    data1 = res1.json()
    assert data1["crop"] == "Rice / Paddy"
    assert data1["residue_type"] == "Paddy Straw / Rice Straw"
    assert data1["estimated_residue_low"] > 0
    assert data1["estimated_residue_mid"] > data1["estimated_residue_low"]
    assert "🚫 DO NOT BURN" in data1["burning_warning"]["title"]
    assert data1["burning_warning"]["nutrient_losses"]["nitrogen_kg"] > 0
    assert data1["recommended_method"] is not None
    assert len(data1["alternative_methods"]) > 0
    assert len(data1["action_plan"]["steps"]) >= 6

    # TEST 2: Rice, 2 acres, Happy Seeder available, Goal = "Manage in field"
    res2 = client.post("/api/parali/analyze", json={
        "crop": "rice",
        "area": 2.0,
        "area_unit": "acre",
        "machinery_available": "yes",
        "machinery": ["Happy Seeder", "Super Seeder"],
        "farmer_goal": "in_field",
    }, headers=auth_header)
    assert res2.status_code == 200
    data2 = res2.json()
    # In-situ surface mulching direct seeding should rank #1 with high score
    assert data2["recommended_method"]["method_id"] == "in_situ_mulch_direct_seeding"
    assert data2["recommended_method"]["score"] >= 85

    # TEST 3: Wheat, 10 acres, Baler available, Goal = "Sell/use as biomass"
    res3 = client.post("/api/parali/analyze", json={
        "crop": "wheat",
        "area": 10.0,
        "area_unit": "acre",
        "machinery_available": "yes",
        "machinery": ["Baler", "Rake"],
        "farmer_goal": "biomass",
    }, headers=auth_header)
    assert res3.status_code == 200
    data3 = res3.json()
    assert data3["recommended_method"]["method_id"] == "ex_situ_baling"
    assert "biomass" in data3["recommended_method"]["economic_potential"].lower() or "baling" in data3["recommended_method"]["name"].lower()

    # TEST 4: Farmer override with known residue quantity
    res4 = client.post("/api/parali/analyze", json={
        "crop": "rice",
        "area": 3.0,
        "area_unit": "acre",
        "residue_quantity": 12.5,
        "residue_quantity_source": "farmer_known",
    }, headers=auth_header)
    assert res4.status_code == 200
    data4 = res4.json()
    assert data4["is_farmer_override"] is True
    assert data4["estimated_residue_mid"] == 12.5
    assert "Farmer Provided" in data4["estimate_confidence"]

    # TEST 5: Farmer does not provide location (works seamlessly)
    res5 = client.post("/api/parali/analyze", json={
        "crop": "maize",
        "area": 4.0,
        "area_unit": "acre",
        "latitude": None,
        "longitude": None,
    })
    assert res5.status_code == 200
    assert res5.json()["crop"] == "Maize"

    # TEST 6: Scientific safety & crop awareness (Cotton cannot be livestock feed)
    res6 = client.post("/api/parali/analyze", json={
        "crop": "cotton",
        "area": 4.0,
        "farmer_goal": "livestock",
    })
    assert res6.status_code == 200
    data6 = res6.json()
    assert "STRICTLY UNFIT FOR LIVESTOCK" in data6["livestock_warning"]
    method_ids = [m["method_id"] for m in [data6["recommended_method"]] + data6["alternative_methods"]]
    assert "untreated_livestock_fodder" not in method_ids
    assert "treated_livestock_fodder" not in method_ids

    # TEST 7: Dynamic action plan endpoint
    res7 = client.post("/api/parali/action-plan", json={
        "method_id": "bio_decomposer_spray",
        "crop": "rice",
    })
    assert res7.status_code == 200
    plan = res7.json()
    assert plan["method_id"] == "bio_decomposer_spray"
    assert len(plan["steps"]) >= 6


def test_market_prices_suite():
    # 1. State list endpoint
    res_states = client.get("/api/market-prices/states")
    assert res_states.status_code == 200
    states = res_states.json()["states"]
    assert len(states) >= 36
    assert "Uttar Pradesh" in states
    assert "Punjab" in states
    assert "Maharashtra" in states

    # 2. Crop list endpoint
    res_crops = client.get("/api/market-prices/crops")
    assert res_crops.status_code == 200
    crops = res_crops.json()["crops"]
    assert "Wheat" in crops
    assert "Mustard" in crops
    assert "Rice" in crops

    # TEST 1: State = Uttar Pradesh, Crop = Wheat
    res_up_wheat = client.get("/api/market-prices/latest?state=Uttar%20Pradesh&crop=Wheat")
    assert res_up_wheat.status_code == 200
    d_up = res_up_wheat.json()
    assert d_up["crop"] == "Wheat"
    assert d_up["state"] == "Uttar Pradesh"
    assert d_up["price"]["modal"] > 0
    assert d_up["price"]["min"] <= d_up["price"]["modal"] <= d_up["price"]["max"]
    assert d_up["price"]["unit"] == "quintal"
    assert d_up["freshness"] == "latest_available"
    assert "source" in d_up

    # TEST 2: State = Punjab, Crop = Wheat
    res_pb_wheat = client.get("/api/market-prices/latest?state=Punjab&crop=Wheat")
    assert res_pb_wheat.status_code == 200
    d_pb = res_pb_wheat.json()
    assert d_pb["crop"] == "Wheat"
    assert d_pb["state"] == "Punjab"
    assert d_pb["price"]["modal"] >= 2000

    # TEST 3: State = Maharashtra, Crop = Soybean
    res_mh_soy = client.get("/api/market-prices/latest?state=Maharashtra&crop=Soybean")
    assert res_mh_soy.status_code == 200
    d_mh = res_mh_soy.json()
    assert d_mh["crop"] == "Soybean"
    assert d_mh["state"] == "Maharashtra"
    assert d_mh["price"]["modal"] > 3500

    # TEST 4: State selected but no district (Graceful state-level fallback)
    res_state_only = client.get("/api/market-prices/latest?state=Rajasthan&crop=Mustard")
    assert res_state_only.status_code == 200
    assert res_state_only.json()["price"]["modal"] > 0

    # TEST 5: District selected but no mandi
    res_dist_only = client.get("/api/market-prices/latest?state=Uttar%20Pradesh&crop=Wheat&district=Meerut")
    assert res_dist_only.status_code == 200
    assert res_dist_only.json()["district"] == "Meerut"

    # TEST 6: Crop with no available price
    res_nonexistent = client.get("/api/market-prices/latest?state=Punjab&crop=NonExistentCropXYZ")
    assert res_nonexistent.status_code == 404

    # TEST 7: Historical data endpoint (7d, 30d, 90d)
    res_hist = client.get("/api/market-prices/history?state=Uttar%20Pradesh&crop=Wheat&days=30")
    assert res_hist.status_code == 200
    d_hist = res_hist.json()
    assert d_hist["available"] is True
    assert len(d_hist["series"]) > 0
    assert "modal_price" in d_hist["series"][0]

    # TEST 8: Compare crops endpoint (2-5 crops)
    res_compare = client.get("/api/market-prices/compare?state=Uttar%20Pradesh&crops=Wheat,Mustard,Rice")
    assert res_compare.status_code == 200
    d_comp = res_compare.json()
    assert len(d_comp["compared_crops"]) == 3

    # TEST 9: State-wise comparison for a crop
    res_state_comp = client.get("/api/market-prices/state-comparison?crop=Wheat")
    assert res_state_comp.status_code == 200
    d_s_comp = res_state_comp.json()
    assert len(d_s_comp["states"]) >= 4
    assert "advisory" in d_s_comp

    # TEST 10: Profit estimate integration
    res_profit = client.get("/api/market-prices/profit-estimate?state=Uttar%20Pradesh&crop=Wheat&farm_area=2.5&area_unit=acre")
    assert res_profit.status_code == 200
    d_prof = res_profit.json()
    assert d_prof["available"] is True
    assert d_prof["estimated_gross_revenue"] > 0
    assert d_prof["estimated_net_profit"] is not None
    assert d_prof["is_guaranteed"] is False



