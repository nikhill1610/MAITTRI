"""
Test Suite: CodeRabbit Final Hardening Pass Regression & Validation Tests
--------------------------------------------------------------------------
Validates all 12 CodeRabbit findings across the MAITTRI backend:
1. app/routes/iot.py — Simulation token rotation & explicit designation
2. app/routes/soil_tests.py — Farm ID mismatch HTTP 400
3. app/routes/soil_tests.py — Duplicate REPORT_AVAILABLE terminal rejection
4. app/routes/chat.py — Context.farm_id exact match and ownership validation
5. app/services/web_search_service.py — SafeSearchCache list copy immunity
6. app/services/web_search_service.py — PII Aadhaar/Phone regex ordering & boundary protection
7. app/services/parali_management_service.py — Multi-crop disambiguation
8. app/services/parali_management_service.py — Explicit zero residue quantity preservation
9. app/services/parali_management_service.py — Machinery matching vs generic residue words
10. app/services/parali_management_service.py — Residue quantity source labeling
11. app/services/market_price_service.py — Truthful static/synthetic benchmark labeling
12. app/services/market_price_service.py — Mandi & district requested vs resolved separation
"""

import os
import math
import uuid
import pytest
from unittest.mock import MagicMock, patch
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models import IoTDevice, SoilTestRequest, SoilTestReport, Farm, Farmer, User
from app.deps import AuthenticatedUser
from app.routes.iot import is_simulation_device, simulate_telemetry
from app.routes.soil_tests import submit_soil_lab_report, update_soil_test_status
from app.routes.chat import _enrich_user_farm_context, ChatContext
from app.routes.auth import register
from app.schemas import SoilTestReportCreate, SoilTestRequestUpdate, RegisterRequest
from app.services.web_search_service import SafeSearchCache, sanitize_and_enrich_query, extract_domain
from app.services.parali_management_service import (
    analyze_crop_residue,
    check_machinery_overlap,
    detect_matching_crop_keys,
    normalize_machine_tokens
)
from app.services.market_price_service import (
    get_latest_market_price,
    get_other_crop_prices_in_state,
    get_crop_price_history
)
from sqlalchemy import text
from app.database import SessionLocal, engine
from app.services.crop_recommendation_service import normalize_crop_name
from app.routes.farmer_profile import ensure_farmer_record, update_my_farmer_profile
from app.schemas import FarmerUpdate




# =====================================================================
# 1. IoT Simulation Token Rotation & Explicit Designation
# =====================================================================
class TestIoTSimulationTokenRotation:
    def test_hardware_like_device_name_rejected_without_explicit_simulation_designation(self):
        device = IoTDevice(device_id="MAITRI_ESP8266_01", name="Standard Hardware Sensor", device_token_hash=None)
        assert is_simulation_device(device.device_id, device) is False

        mock_db = MagicMock(spec=Session)
        mock_db.query.return_value.filter.return_value.first.return_value = device
        operator = AuthenticatedUser(id="op-1", email="op@maittri.in", role="AUTHORIZED_OPERATOR")

        with patch.dict(os.environ, {"ENVIRONMENT": "development"}):
            with pytest.raises(HTTPException) as exc:
                simulate_telemetry(device_id="MAITRI_ESP8266_01", db=mock_db, user=operator)
            assert exc.value.status_code == 403
            assert "non-simulation" in exc.value.detail.lower()

    def test_explicitly_simulation_designated_device_can_receive_token_in_non_prod(self):
        device = IoTDevice(device_id="maitri_sim_node_42", name="Simulation Node 42", device_token_hash=None)
        assert is_simulation_device(device.device_id, device) is True

        mock_db = MagicMock(spec=Session)
        mock_db.query.return_value.filter.return_value.first.return_value = device
        operator = AuthenticatedUser(id="op-1", email="op@maittri.in", role="AUTHORIZED_OPERATOR")

        with patch.dict(os.environ, {"ENVIRONMENT": "development"}), \
             patch("app.routes.iot.process_incoming_sensor_data", return_value={"status": "online"}):
            res = simulate_telemetry(device_id="maitri_sim_node_42", db=mock_db, user=operator)
            assert res["status"] == "success"
            assert device.device_token_hash is not None
            mock_db.flush.assert_called_once()
            mock_db.commit.assert_called_once()

    def test_failed_ingestion_rolls_back_token_hash(self):
        original_hash = "sha256_original_hash_value"
        device = IoTDevice(device_id="maitri_sim_node_42", name="Sim Node", device_token_hash=original_hash)

        mock_db = MagicMock(spec=Session)
        mock_db.query.return_value.filter.return_value.first.return_value = device
        operator = AuthenticatedUser(id="op-1", email="op@maittri.in", role="AUTHORIZED_OPERATOR")

        with patch.dict(os.environ, {"ENVIRONMENT": "development"}), \
             patch("app.routes.iot.process_incoming_sensor_data", side_effect=RuntimeError("Ingestion DB error")):
            with pytest.raises(HTTPException) as exc:
                simulate_telemetry(device_id="maitri_sim_node_42", db=mock_db, user=operator)
            assert exc.value.status_code == 500
            assert "ingestion failed" in exc.value.detail.lower()
            # Must rollback and restore the original hash
            mock_db.rollback.assert_called_once()
            assert device.device_token_hash == original_hash

    def test_production_rejects_simulation(self):
        mock_db = MagicMock(spec=Session)
        operator = AuthenticatedUser(id="op-1", email="op@maittri.in", role="AUTHORIZED_OPERATOR")

        with patch.dict(os.environ, {"ENVIRONMENT": "production"}):
            with pytest.raises(HTTPException) as exc:
                simulate_telemetry(device_id="maitri_sim_node_42", db=mock_db, user=operator)
            assert exc.value.status_code == 403
            assert "disabled in production" in exc.value.detail

    def test_elevated_authentication_mandatory(self):
        mock_db = MagicMock(spec=Session)
        device = IoTDevice(device_id="maitri_sim_node_42", name="Sim Node", device_token_hash=None)
        mock_db.query.return_value.filter.return_value.first.return_value = device

        with patch.dict(os.environ, {"ENVIRONMENT": "development"}):
            with pytest.raises(HTTPException) as exc:
                simulate_telemetry(device_id="maitri_sim_node_42", db=mock_db, user=None)
            assert exc.value.status_code == 403
            assert "elevated operator privileges" in exc.value.detail


# =====================================================================
# 2. Soil Tests — Farm ID Mismatch
# =====================================================================
class TestSoilTestsFarmIdMismatch:
    def test_payload_farm_id_mismatch_returns_400(self):
        mock_db = MagicMock(spec=Session)
        operator = AuthenticatedUser(id="op-1", email="op@maittri.in", role="AUTHORIZED_OPERATOR")

        soil_req = SoilTestRequest(
            id=101,
            request_id="STR-101",
            farmer_id=5,
            farm_id=10,
            status="SAMPLE_COLLECTED"
        )
        mock_db.query.return_value.filter.return_value.first.return_value = soil_req

        payload = SoilTestReportCreate(
            request_id="STR-101",
            farmer_id=5,
            farm_id=99,  # Mismatch with soil_req.farm_id (10)
            lab_name="Central Lab",
            ph=6.5
        )

        with pytest.raises(HTTPException) as exc:
            submit_soil_lab_report(req_id="STR-101", payload=payload, db=mock_db, current_user=operator)
        assert exc.value.status_code == 400
        assert "Payload farm_id does not match the soil test request." in exc.value.detail

    def test_matching_or_omitted_farm_id_proceeds(self):
        mock_db = MagicMock(spec=Session)
        operator = AuthenticatedUser(id="op-1", email="op@maittri.in", role="AUTHORIZED_OPERATOR")

        soil_req = SoilTestRequest(
            id=101,
            request_id="STR-101",
            farmer_id=5,
            farm_id=10,
            status="SAMPLE_COLLECTED"
        )
        farmer = Farmer(id=5, user_id="u-5")
        farm = Farm(id=10, farmer_id=5)

        def mock_query(model):
            q = MagicMock()
            if model == SoilTestRequest:
                q.filter.return_value.first.return_value = soil_req
            elif model == Farmer:
                q.filter.return_value.first.return_value = farmer
            elif model == Farm:
                q.filter.return_value.first.return_value = farm
            return q

        mock_db.query.side_effect = mock_query

        payload = SoilTestReportCreate(
            request_id="STR-101",
            farmer_id=5,
            farm_id=10,  # Matches
            lab_name="Central Lab",
            ph=6.8
        )

        with patch("app.routes.soil_tests.create_and_dispatch_notification"):
            res = submit_soil_lab_report(req_id="STR-101", payload=payload, db=mock_db, current_user=operator)
            assert res is not None
            assert soil_req.status == "REPORT_AVAILABLE"


# =====================================================================
# 3. Soil Tests — Duplicate REPORT_AVAILABLE Terminal Rejection
# =====================================================================
class TestSoilTestsDuplicateReportTerminal:
    def test_report_available_is_terminal_and_rejects_resubmission(self):
        mock_db = MagicMock(spec=Session)
        operator = AuthenticatedUser(id="op-1", email="op@maittri.in", role="AUTHORIZED_OPERATOR")

        soil_req = SoilTestRequest(
            id=102,
            request_id="STR-102",
            farmer_id=5,
            farm_id=10,
            status="REPORT_AVAILABLE"
        )
        mock_db.query.return_value.filter.return_value.first.return_value = soil_req

        payload = SoilTestReportCreate(
            request_id="STR-102",
            farmer_id=5,
            farm_id=10,
            lab_name="Central Lab",
            ph=7.0
        )

        with pytest.raises(HTTPException) as exc:
            submit_soil_lab_report(req_id="STR-102", payload=payload, db=mock_db, current_user=operator)
        assert exc.value.status_code == 400
        assert "report_available" in exc.value.detail.lower()
        # Ensure no new report created
        mock_db.add.assert_not_called()


# =====================================================================
# 4. Chat — Respect context.farm_id & Disallow Cross-User Access
# =====================================================================
class TestChatRespectContextFarmId:
    def test_requested_owned_farm_is_used(self):
        mock_db = MagicMock(spec=Session)
        user = AuthenticatedUser(id="user-123", email="farmer@maittri.in", role="FARMER")

        farm1 = Farm(id=1, user_id="user-123", name="Farm One", current_crop="Wheat")
        farm2 = Farm(id=2, user_id="user-123", name="Farm Two", current_crop="Rice")

        def query_side_effect(*args):
            query_mock = MagicMock()
            def filter_side_effect(*f_args):
                filter_mock = MagicMock()
                # If filtering for Farm.id == 1
                filter_mock.first.return_value = farm1
                return filter_mock
            query_mock.filter.side_effect = filter_side_effect
            return query_mock

        mock_db.query.side_effect = query_side_effect

        context = ChatContext(farm_id=1)
        res = _enrich_user_farm_context(mock_db, user, context)
        assert res is not None
        assert res.get("crop") == "Wheat"
        assert res.get("farm_name") == "Farm One"

    def test_requested_different_owned_farm_used_instead_of_newest(self):
        mock_db = MagicMock(spec=Session)
        user = AuthenticatedUser(id="user-123", email="farmer@maittri.in", role="FARMER")

        farm_older = Farm(id=1, user_id="user-123", name="Old Farm", current_crop="Mustard")

        mock_db.query.return_value.filter.return_value.first.return_value = farm_older

        context = ChatContext(farm_id=1)
        res = _enrich_user_farm_context(mock_db, user, context)
        assert res["farm_name"] == "Old Farm"
        assert res["crop"] == "Mustard"

    def test_another_users_farm_is_not_loaded(self):
        mock_db = MagicMock(spec=Session)
        user = AuthenticatedUser(id="user-123", email="farmer@maittri.in", role="FARMER")

        # Query with Farm.user_id == user.id returns None because user doesn't own farm 999
        mock_db.query.return_value.filter.return_value.first.return_value = None

        context = ChatContext(farm_id=999)
        res = _enrich_user_farm_context(mock_db, user, context)
        # Must not load another user's farm data
        assert res.get("crop") is None
        assert res.get("farm_id") is None
        assert res.get("farm_name") is None

    def test_absent_farm_id_falls_back_to_newest_farm(self):
        mock_db = MagicMock(spec=Session)
        user = AuthenticatedUser(id="user-123", email="farmer@maittri.in", role="FARMER")

        newest_farm = Farm(id=5, user_id="user-123", name="Newest Farm", current_crop="Barley")
        mock_db.query.return_value.filter.return_value.order_by.return_value.first.return_value = newest_farm

        context = ChatContext(farm_id=None)
        res = _enrich_user_farm_context(mock_db, user, context)
        assert res is not None
        assert res["farm_name"] == "Newest Farm"
        assert res["crop"] == "Barley"


# =====================================================================
# 5. Web Search — Cached List Copy Mutation Immunity
# =====================================================================
class TestWebSearchCacheCopy:
    def test_cache_read_returns_safe_copy(self):
        cache = SafeSearchCache(ttl_seconds=60)
        original_data = [{"title": "Item 1"}, {"title": "Item 2"}]
        cache.set("test_key", original_data)

        # First read
        read1 = cache.get("test_key")
        assert len(read1) == 2

        # Caller mutates read1
        read1.clear()
        read1.append({"title": "Corrupted Item"})

        # Subsequent read must remain intact
        read2 = cache.get("test_key")
        assert len(read2) == 2
        assert read2[0]["title"] == "Item 1"
        assert read2[1]["title"] == "Item 2"


# =====================================================================
# 6. Web Search — PII Regex Ordering & Boundary Protection
# =====================================================================
class TestPIIRegexOrderingAndBoundaries:
    def test_normal_indian_phone_redacted(self):
        q = sanitize_and_enrich_query("Call me at 9876543210 about seeds")
        assert "9876543210" not in q

    def test_plus_91_phone_redacted(self):
        q = sanitize_and_enrich_query("Call me at +91-9876543210 urgently")
        assert "9876543210" not in q

    def test_spaced_and_hyphenated_aadhaar_redacted(self):
        q1 = sanitize_and_enrich_query("My aadhaar is 1234 5678 9012 for verification")
        assert "1234 5678 9012" not in q1
        assert "1234" not in q1

        q2 = sanitize_and_enrich_query("My aadhaar is 1234-5678-9012 for verification")
        assert "1234-5678-9012" not in q2
        assert "5678" not in q2

    def test_contiguous_aadhaar_redacted(self):
        q = sanitize_and_enrich_query("Aadhaar: 123456789012")
        assert "123456789012" not in q

    def test_aadhaar_beginning_with_6_to_9_not_partially_eaten_by_phone(self):
        # 9876 begins with 9, which phone regex would greedily match if phone ran first
        q = sanitize_and_enrich_query("Aadhaar: 9876 5432 1098")
        assert "9876 5432 1098" not in q
        assert "9876" not in q
        assert "1098" not in q

    def test_long_numeric_string_does_not_lose_arbitrary_substring(self):
        # 16-digit order ID should not have its inner 10 digits replaced
        q = sanitize_and_enrich_query("Order ID is 1234567890123456 status")
        assert "1234567890123456" in q


# =====================================================================
# 7. Parali Management — Multiple Crops Detection
# =====================================================================
class TestParaliMultipleCrops:
    def test_single_crop_succeeds(self):
        res = analyze_crop_residue(crop="rice", area=2.0)
        assert res.get("status") != "ambiguous_input"
        assert res["crop"] == "Rice / Paddy"

    def test_crop_aliases_succeed(self):
        res = analyze_crop_residue(crop="dhan", area=2.0)
        assert res["crop"] == "Rice / Paddy"

    def test_multiple_crops_returns_ambiguous_status(self):
        res = analyze_crop_residue(crop="cotton stalks and wheat straw", area=2.0)
        assert res["status"] == "ambiguous_input"
        assert "Multiple distinct crops detected" in res["message"]
        assert "cotton" in res["detected_crops"]
        assert "wheat" in res["detected_crops"]
        assert res["is_farmer_override"] is False

    def test_duplicate_aliases_for_same_crop_not_ambiguous(self):
        res = analyze_crop_residue(crop="rice and paddy", area=2.0)
        assert res.get("status") != "ambiguous_input"
        assert res["crop"] == "Rice / Paddy"


# =====================================================================
# 8. Parali Management — Explicit Zero Residue Preservation
# =====================================================================
class TestParaliExplicitZeroResidue:
    def test_none_residue_estimates_agronomic_benchmark(self):
        res = analyze_crop_residue(crop="rice", area=2.0, residue_quantity=None)
        assert res["estimated_residue_mid"] > 0
        assert res["residue_quantity_source"] == "benchmark"

    def test_explicit_zero_residue_preserved(self):
        res = analyze_crop_residue(crop="rice", area=2.0, residue_quantity=0)
        assert res["estimated_residue_low"] == 0.0
        assert res["estimated_residue_mid"] == 0.0
        assert res["estimated_residue_high"] == 0.0

    def test_positive_residue_preserved(self):
        res = analyze_crop_residue(crop="rice", area=2.0, residue_quantity=7.5)
        assert res["estimated_residue_mid"] == 7.5


# =====================================================================
# 9. Parali Management — Machinery Matching
# =====================================================================
class TestParaliMachineryMatching:
    def test_generic_material_words_do_not_match(self):
        # "straw" is generic residue material and must not trigger match between reaper and baler
        req = ["Straw Reaper / Thresher"]
        avail = ["straw baler"]
        assert check_machinery_overlap(req, avail) is False

    def test_genuine_equipment_matches(self):
        req = ["Tractor Operated Round Baler"]
        avail = ["baler"]
        assert check_machinery_overlap(req, avail) is True

        req2 = ["Paddy Mulcher"]
        avail2 = ["mulcher"]
        assert check_machinery_overlap(req2, avail2) is True


# =====================================================================
# 10. Parali Management — Residue Quantity Source Labeling
# =====================================================================
class TestParaliResidueQuantitySource:
    def test_positive_farmer_measurement(self):
        res = analyze_crop_residue(crop="rice", area=3.0, residue_quantity=6.0, residue_quantity_source="farmer_measurement")
        assert res["is_farmer_override"] is True
        assert "Farmer Provided" in res["estimate_confidence"]
        assert "measured and provided directly by the farmer" in " ".join(res["limitations"]).lower()

    def test_positive_estimated_value(self):
        res = analyze_crop_residue(crop="rice", area=3.0, residue_quantity=6.0, residue_quantity_source="estimated")
        assert res["is_farmer_override"] is False
        assert "Farmer Provided" not in res["estimate_confidence"]
        assert "Medium (Estimated Quantity)" in res["estimate_confidence"]
        assert "unverified estimate" in " ".join(res["limitations"]).lower()
        assert res["residue_quantity_source"] == "estimated"

    def test_benchmark_default_estimate(self):
        res = analyze_crop_residue(crop="rice", area=3.0, residue_quantity=None)
        assert res["is_farmer_override"] is False
        assert res["residue_quantity_source"] == "benchmark"
        assert "Agronomic Benchmark Estimate" in res["estimate_confidence"]

    def test_explicit_zero_distinguishes_source(self):
        res_est = analyze_crop_residue(crop="rice", area=3.0, residue_quantity=0, residue_quantity_source="estimated")
        assert res_est["is_farmer_override"] is False
        assert res_est["estimate_confidence"] == "Specified Zero Quantity"

        res_farmer = analyze_crop_residue(crop="rice", area=3.0, residue_quantity=0, residue_quantity_source="farmer_measurement")
        assert res_farmer["is_farmer_override"] is True
        assert "Farmer Provided" in res_farmer["estimate_confidence"]


# =====================================================================
# 11. Market Price — Truthful Benchmark / Synthetic Labeling
# =====================================================================
class TestMarketPriceBenchmarkSyntheticLabeling:
    def test_benchmark_data_labeled_benchmark_static_not_official_mandi(self):
        prices = get_other_crop_prices_in_state("Uttar Pradesh")
        assert len(prices) > 0
        for p in prices:
            assert "Official Mandi Data" not in p["source"]
            assert "Benchmark reference (static" in p["source"]
            assert p["data_tier"] == "state_benchmark"
            assert p["freshness"] == "benchmark_reference"

    def test_synthetic_history_has_synthetic_true(self):
        hist = get_crop_price_history("Wheat", "Uttar Pradesh", days=30)
        assert hist["synthetic"] is True
        assert hist["freshness"] == "synthetic_benchmark"
        assert "synthetic" in hist["source"].lower()
        assert len(hist["series"]) > 0
        for rec in hist["series"]:
            assert rec["synthetic"] is True


# =====================================================================
# 12. Market Price — Requested vs Resolved Mandi/District
# =====================================================================
class TestMarketPriceMandiDistrictMismatch:
    def test_exact_mandi_match(self):
        # UP Wheat benchmark source is Meerut Mandi
        data = get_latest_market_price("Wheat", "Uttar Pradesh", mandi="Meerut Mandi")
        assert data is not None
        assert data["is_mandi_specific"] is True
        assert data["resolved_mandi"] == "Meerut Mandi"
        assert data["requested_mandi"] == "Meerut Mandi"

    def test_different_requested_mandi(self):
        data = get_latest_market_price("Wheat", "Uttar Pradesh", mandi="Varanasi Mandi")
        assert data is not None
        assert data["is_mandi_specific"] is False
        assert data["resolved_mandi"] == "Meerut Mandi"
        assert data["requested_mandi"] == "Varanasi Mandi"
        assert data["market"] == "Meerut Mandi"  # Does NOT claim benchmark price belongs to Varanasi

    def test_district_request_matching_benchmark(self):
        data = get_latest_market_price("Wheat", "Uttar Pradesh", district="Meerut")
        assert data is not None
        assert data["is_mandi_specific"] is True
        assert data["resolved_district"] == "Meerut"
        assert data["requested_district"] == "Meerut"

    def test_district_request_nonmatching_benchmark(self):
        data = get_latest_market_price("Wheat", "Uttar Pradesh", district="Agra")
        assert data is not None
        assert data["is_mandi_specific"] is False
        assert data["resolved_district"] == "Meerut"
        assert data["requested_district"] == "Agra"


# =====================================================================
# 13. Soil Tests — State Machine & REPORT_AVAILABLE Guards
# =====================================================================
class TestSoilTestStateMachineAndGuards:
    def test_sample_collected_cannot_directly_become_report_available_via_status_endpoint(self):
        req = SoilTestRequest(
            id=1,
            request_id="STR-SC-01",
            farmer_id=10,
            status="SAMPLE_COLLECTED"
        )
        mock_db = MagicMock(spec=Session)
        mock_db.query.return_value.filter.return_value.first.return_value = req
        operator = AuthenticatedUser(id="op-1", email="op@maittri.in", role="AUTHORIZED_OPERATOR")

        payload = SoilTestRequestUpdate(status="REPORT_AVAILABLE")
        with pytest.raises(HTTPException) as exc_info:
            update_soil_test_status(req_id="STR-SC-01", payload=payload, current_user=operator, db=mock_db)
        assert exc_info.value.status_code == 400
        assert "Invalid status transition" in exc_info.value.detail
        assert req.status == "SAMPLE_COLLECTED"

    def test_lab_processing_cannot_directly_become_report_available_via_status_endpoint(self):
        req = SoilTestRequest(
            id=2,
            request_id="STR-LP-01",
            farmer_id=10,
            status="LAB_PROCESSING"
        )
        mock_db = MagicMock(spec=Session)
        mock_db.query.return_value.filter.return_value.first.return_value = req
        operator = AuthenticatedUser(id="op-1", email="op@maittri.in", role="AUTHORIZED_OPERATOR")

        payload = SoilTestRequestUpdate(status="REPORT_AVAILABLE")
        with pytest.raises(HTTPException) as exc_info:
            update_soil_test_status(req_id="STR-LP-01", payload=payload, current_user=operator, db=mock_db)
        assert exc_info.value.status_code == 400
        assert "Invalid status transition" in exc_info.value.detail
        assert req.status == "LAB_PROCESSING"

    def test_submit_soil_lab_report_creates_report_and_moves_to_report_available(self):
        req = SoilTestRequest(
            id=3,
            request_id="STR-SUBMIT-01",
            farmer_id=10,
            status="LAB_PROCESSING"
        )
        farmer = Farmer(id=10, name="Ramesh", user_id="u-1")
        mock_db = MagicMock(spec=Session)

        def mock_query(model):
            q = MagicMock()
            if model == SoilTestRequest:
                q.filter.return_value.first.return_value = req
            elif model == Farmer:
                q.filter.return_value.first.return_value = farmer
            elif model == Farm:
                q.filter.return_value.first.return_value = None
            return q

        mock_db.query.side_effect = mock_query
        operator = AuthenticatedUser(id="op-1", email="op@maittri.in", role="AUTHORIZED_OPERATOR")
        payload = SoilTestReportCreate(
            request_id="STR-SUBMIT-01",
            farmer_id=10,
            lab_name="ICAR Central Soil Lab",
            nitrogen=240.0,
            phosphorus=22.0,
            potassium=180.0,
            ph=6.8
        )

        res = submit_soil_lab_report(req_id="STR-SUBMIT-01", payload=payload, current_user=operator, db=mock_db)
        assert req.status == "REPORT_AVAILABLE"
        assert res.lab_name == "ICAR Central Soil Lab"
        assert farmer.soil_test_available is True
        mock_db.add.assert_called()

    def test_submit_soil_lab_report_rejects_scheduled_status(self):
        req = SoilTestRequest(id=4, request_id="STR-SCH-01", farmer_id=10, status="SCHEDULED")
        mock_db = MagicMock(spec=Session)
        mock_db.query.return_value.filter.return_value.first.return_value = req
        operator = AuthenticatedUser(id="op-1", email="op@maittri.in", role="AUTHORIZED_OPERATOR")
        payload = SoilTestReportCreate(request_id="STR-SCH-01", farmer_id=10, lab_name="Lab", nitrogen=200.0)

        with pytest.raises(HTTPException) as exc_info:
            submit_soil_lab_report(req_id="STR-SCH-01", payload=payload, current_user=operator, db=mock_db)
        assert exc_info.value.status_code == 400
        assert "SCHEDULED" in exc_info.value.detail

    def test_submit_soil_lab_report_rejects_requested_status(self):
        req = SoilTestRequest(id=5, request_id="STR-REQ-01", farmer_id=10, status="REQUESTED")
        mock_db = MagicMock(spec=Session)
        mock_db.query.return_value.filter.return_value.first.return_value = req
        operator = AuthenticatedUser(id="op-1", email="op@maittri.in", role="AUTHORIZED_OPERATOR")
        payload = SoilTestReportCreate(request_id="STR-REQ-01", farmer_id=10, lab_name="Lab", nitrogen=200.0)

        with pytest.raises(HTTPException) as exc_info:
            submit_soil_lab_report(req_id="STR-REQ-01", payload=payload, current_user=operator, db=mock_db)
        assert exc_info.value.status_code == 400
        assert "REQUESTED" in exc_info.value.detail

    def test_submit_soil_lab_report_rejects_duplicate_when_already_report_available(self):
        req = SoilTestRequest(id=6, request_id="STR-DUP-01", farmer_id=10, status="REPORT_AVAILABLE")
        mock_db = MagicMock(spec=Session)
        mock_db.query.return_value.filter.return_value.first.return_value = req
        operator = AuthenticatedUser(id="op-1", email="op@maittri.in", role="AUTHORIZED_OPERATOR")
        payload = SoilTestReportCreate(request_id="STR-DUP-01", farmer_id=10, lab_name="Lab", nitrogen=200.0)

        with pytest.raises(HTTPException) as exc_info:
            submit_soil_lab_report(req_id="STR-DUP-01", payload=payload, current_user=operator, db=mock_db)
        assert exc_info.value.status_code == 400
        assert "REPORT_AVAILABLE" in exc_info.value.detail


# =====================================================================
# 14. IoT Simulation — Exception Information Leakage Prevention
# =====================================================================
class TestIoTExceptionLeakagePrevention:
    def test_simulation_failure_does_not_leak_internal_exception_details(self):
        device = IoTDevice(
            device_id="MAITRI_SIM_001",
            name="Virtual Sim Sensor",
            device_token_hash="previous_hash_value"
        )
        mock_db = MagicMock(spec=Session)
        mock_db.query.return_value.filter.return_value.first.return_value = device
        operator = AuthenticatedUser(id="op-1", email="op@maittri.in", role="AUTHORIZED_OPERATOR")

        secret_error_message = "FATAL: connection to server at '10.0.1.99', port 5432 failed: password authentication failed for user 'pg_internal_admin'"

        with patch.dict(os.environ, {"ENVIRONMENT": "development"}), \
             patch("app.routes.iot.is_simulation_device", return_value=True), \
             patch("app.routes.iot.process_incoming_sensor_data", side_effect=RuntimeError(secret_error_message)):
            with pytest.raises(HTTPException) as exc_info:
                simulate_telemetry(device_id="MAITRI_SIM_001", db=mock_db, user=operator)

            assert exc_info.value.status_code == 500
            assert "Simulation telemetry ingestion failed." == exc_info.value.detail
            # Must NOT leak injected database connection string, IP, or credentials
            assert secret_error_message not in exc_info.value.detail
            assert "pg_internal_admin" not in exc_info.value.detail
            assert "10.0.1.99" not in exc_info.value.detail

            # Token hash rollback preserved
            assert device.device_token_hash == "previous_hash_value"
            mock_db.rollback.assert_called()


# =====================================================================
# 15. Auth — Development Fallback Email Confirmation
# =====================================================================
class TestAuthDevFallbackEmailConfirmed:
    def test_dev_fallback_insert_sets_email_confirmed_at(self):
        mock_db = MagicMock(spec=Session)
        mock_db.execute.return_value.first.return_value = None
        mock_db.query.return_value.filter.return_value.first.return_value = None

        mock_sb_admin = MagicMock()
        mock_sb_admin.auth.admin.create_user.side_effect = Exception("Supabase unreachable")

        payload = RegisterRequest(
            email="farmer_test@maittri.in",
            password="SecurePassword123!",
            full_name="Test Farmer",
            phone_number="9876543210"
        )

        with patch("app.routes.auth.engine") as mock_engine, \
             patch("app.routes.auth.get_supabase_admin_client", return_value=mock_sb_admin), \
             patch.dict(os.environ, {"ENVIRONMENT": "development", "ALLOW_LOCAL_AUTH_INSERT": "true"}):
            mock_engine.name = "postgresql"
            res = register(payload=payload, db=mock_db)
            assert "access_token" in res

            # Verify that email_confirmed_at was in the SQL statement
            sql_executed = None
            for call_args in mock_db.execute.call_args_list:
                sql_str = str(call_args[0][0])
                if "INSERT INTO auth.users" in sql_str:
                    sql_executed = sql_str
                    break

            assert sql_executed is not None
            assert "email_confirmed_at" in sql_executed
            assert "now()" in sql_executed


# =====================================================================
# 16. Web Search — Hostname Parsing
# =====================================================================
class TestWebSearchHostnameParsing:
    def test_normal_domain(self):
        assert extract_domain("https://icar.org.in/crop-advisory") == "icar.org.in"
        assert extract_domain("https://www.icar.org.in/crop-advisory") == "icar.org.in"

    def test_domain_with_port(self):
        assert extract_domain("https://evil.com:443/path?param=1") == "evil.com"
        assert extract_domain("http://localhost:8000/api") == "localhost"

    def test_url_with_userinfo(self):
        assert extract_domain("https://attacker:secret@agricoop.nic.in/portal") == "agricoop.nic.in"

    def test_uppercase_hostname(self):
        assert extract_domain("HTTPS://WWW.UPAGRIPARIKSHAN.GOV.IN/SOIL") == "upagriparikshan.gov.in"

    def test_malformed_url(self):
        assert extract_domain("not-a-valid-url") == ""
        assert extract_domain("http://") == ""
        assert extract_domain(None) == ""


# =====================================================================
# 17. Chat — Anonymous Farm ID Protection & Ownership Verification
# =====================================================================
class TestChatAnonymousFarmIdProtection:
    def test_anonymous_farm_id_is_stripped(self):
        mock_db = MagicMock(spec=Session)
        client_ctx = ChatContext(farm_id=99, crop="Rice")

        enriched = _enrich_user_farm_context(mock_db, user=None, client_context=client_ctx)
        assert "farm_id" not in enriched
        assert enriched.get("crop") == "Rice"

    def test_authenticated_owned_farm_is_loaded_and_kept(self):
        user = User(id="user-123", email="user@test.in")
        farm = Farm(id=42, user_id="user-123", name="Shri Krishna Farm", current_crop="Wheat")

        mock_db = MagicMock(spec=Session)
        mock_db.query.return_value.filter.return_value.first.return_value = farm

        client_ctx = ChatContext(farm_id=42)
        enriched = _enrich_user_farm_context(mock_db, user=user, client_context=client_ctx)

        assert enriched.get("farm_id") == 42
        assert enriched.get("farm_name") == "Shri Krishna Farm"
        assert enriched.get("crop") == "Wheat"

    def test_authenticated_other_user_farm_is_rejected_and_stripped(self):
        user = User(id="user-123", email="user@test.in")
        # Farm belongs to another user
        mock_db = MagicMock(spec=Session)
        mock_db.query.return_value.filter.return_value.first.return_value = None  # Not found under user-123

        client_ctx = ChatContext(farm_id=88)  # Belongs to user-456
        enriched = _enrich_user_farm_context(mock_db, user=user, client_context=client_ctx)

        assert "farm_id" not in enriched

    def test_authenticated_request_without_farm_id_retains_newest_fallback(self):
        user = User(id="user-123", email="user@test.in")
        farm = Farm(id=55, user_id="user-123", name="Newest Farm", current_crop="Mustard")

        mock_db = MagicMock(spec=Session)
        mock_db.query.return_value.filter.return_value.order_by.return_value.first.return_value = farm

        client_ctx = ChatContext()
        enriched = _enrich_user_farm_context(mock_db, user=user, client_context=client_ctx)

        assert enriched.get("farm_id") == 55
        assert enriched.get("farm_name") == "Newest Farm"
        assert enriched.get("crop") == "Mustard"


# =====================================================================
# 18. Parali Management — Strict Implement-Specific Machinery Matching
# =====================================================================
class TestParaliMachineryMatchingHardened:
    def test_farmer_machinery_tractor_does_not_match_baler_method(self):
        req = ["Square or Round Baler", "Tractor-Trolley"]
        avail = ["Tractor"]
        assert check_machinery_overlap(req, avail) is False

    def test_tractor_trolley_does_not_create_false_implement_match(self):
        req = ["Straw Reaper / Thresher", "Tractor-Trolley"]
        avail = ["Tractor-Trolley"]
        assert check_machinery_overlap(req, avail) is False

        avail2 = ["Tractor", "Trolley"]
        assert check_machinery_overlap(req, avail2) is False

    def test_tractor_stalk_puller_chipper_matches_specific_chipper(self):
        req = ["Tractor Stalk Puller / Chipper", "Trolley"]
        avail = ["Chipper"]
        assert check_machinery_overlap(req, avail) is True

    def test_baler_still_matches_baler(self):
        req = ["Square or Round Baler"]
        avail = ["Baler"]
        assert check_machinery_overlap(req, avail) is True

    def test_generic_material_words_do_not_produce_matches(self):
        generic_words = ["straw", "residue", "stalk", "crops", "fodder", "trash", "parali", "biomass"]
        for word in generic_words:
            req = [f"Specialized {word.capitalize()} Machine"]
            avail = [word]
            assert check_machinery_overlap(req, avail) is False


# =====================================================================
# 19. Startup Migration — IoT Sensor Readings has_table Guard
# =====================================================================
class TestStartupMigrationIoTTableGuard:
    def test_migration_checks_has_table_before_getting_columns(self):
        import inspect as py_inspect
        import app.main as app_main
        source = py_inspect.getsource(app_main)
        # Verify that has_table is called before get_columns for iot_sensor_readings
        assert 'if inspect(engine).has_table("iot_sensor_readings"):' in source
        assert 'get_columns("iot_sensor_readings")' in source


# =====================================================================
# 20. Crop Recommendation Service — Compound Separator Variants & Fallback Protection
# =====================================================================
class TestCropRecommendationCompoundSeparators:
    def test_black_gram_separator_variants_resolve_identically(self):
        bg_space = normalize_crop_name("black gram")
        bg_hyphen = normalize_crop_name("black-gram")
        bg_underscore = normalize_crop_name("black_gram")
        bg_compact = normalize_crop_name("blackgram")

        assert bg_space == "Black Gram"
        assert bg_hyphen == "Black Gram"
        assert bg_underscore == "Black Gram"
        assert bg_compact == "Black Gram"
        assert bg_space == bg_hyphen == bg_underscore == bg_compact

    def test_pigeon_pea_separator_variants_resolve_identically(self):
        pp_space = normalize_crop_name("pigeon pea")
        pp_hyphen = normalize_crop_name("pigeon-pea")
        pp_underscore = normalize_crop_name("pigeon_pea")
        pp_compact = normalize_crop_name("pigeonpea")

        assert pp_space == "Red Gram"
        assert pp_hyphen == "Red Gram"
        assert pp_underscore == "Red Gram"
        assert pp_compact == "Red Gram"
        assert pp_space == pp_hyphen == pp_underscore == pp_compact

    def test_no_incorrect_fallback_to_chickpea_or_gram(self):
        # "black-gram" must NEVER fall back through "gram" to Gram/Chickpea
        assert normalize_crop_name("black-gram") != "Gram/Chickpea"
        assert normalize_crop_name("black-gram") != "Gram"
        assert normalize_crop_name("black-gram") == "Black Gram"

        # "pigeon-pea" must NEVER fall back through "pea" to generic Pea
        assert normalize_crop_name("pigeon-pea") != "Pea"
        assert normalize_crop_name("pigeon-pea") == "Red Gram"

        # Authentic gram / chickpea queries correctly resolve to Gram/Chickpea
        assert normalize_crop_name("chickpea") == "Gram/Chickpea"
        assert normalize_crop_name("gram") == "Gram/Chickpea"
        assert normalize_crop_name("chick pea") == "Gram/Chickpea"
        assert normalize_crop_name("chick-pea") == "Gram/Chickpea"

        # Generic pea resolves to Pea
        assert normalize_crop_name("pea") == "Pea"

    def test_parenthesis_compound_name_normalized(self):
        assert normalize_crop_name("Kharif (black-gram)") == "Black Gram"
        assert normalize_crop_name("Pulse (pigeon_pea)") == "Red Gram"


# =====================================================================
# 21. Farmer Profile — Concurrent Creation & Safe MT-FARM ID Derivation
# =====================================================================
class TestFarmerProfileConcurrentCreationAndSafeID:
    @pytest.fixture
    def db(self):
        session = SessionLocal()
        try:
            yield session
        finally:
            session.close()

    def _provision_farmer_user(self, name="Kisan Lal", mobile="9876543210"):
        uid_str = str(uuid.uuid4())
        email = f"farmer_{uuid.uuid4().hex[:6]}@test.in"
        if engine.name == "postgresql":
            with engine.begin() as conn:
                conn.execute(text("""
                    INSERT INTO auth.users (id, aud, role, email, created_at, updated_at)
                    VALUES (:uid, 'authenticated', 'authenticated', :email, now(), now())
                    ON CONFLICT (id) DO NOTHING;
                """), {"uid": uid_str, "email": email})
                conn.execute(text("""
                    INSERT INTO public.profiles (id, role, full_name, preferred_language)
                    VALUES (:uid, 'FARMER', :name, 'hi')
                    ON CONFLICT (id) DO UPDATE SET role = 'FARMER', full_name = :name;
                """), {"uid": uid_str, "name": name})

        return AuthenticatedUser(
            id=uid_str,
            email=email,
            role="FARMER",
            full_name=name,
            phone_number=mobile
        )

    def test_mt_farm_id_derived_from_database_row_id(self, db):
        user = self._provision_farmer_user("Kisan Lal", "9876543210")
        farmer = ensure_farmer_record(user, db)
        assert farmer is not None
        assert farmer.id is not None
        assert farmer.maittri_farmer_id == f"MT-FARM-{farmer.id:06d}"
        assert farmer.qr_code_data.startswith(f"MAITTRI:{farmer.maittri_farmer_id}:")
        assert str(farmer.user_id) == str(user.id)

    def test_subsequent_call_returns_existing_without_duplicate_row(self, db):
        user = self._provision_farmer_user("Radha Rani", "9876543211")
        farmer1 = ensure_farmer_record(user, db)
        farmer2 = ensure_farmer_record(user, db)
        assert farmer1.id == farmer2.id
        assert farmer1.maittri_farmer_id == farmer2.maittri_farmer_id

        # Exactly 1 Farmer record for this user_id
        count = db.query(Farmer).filter(Farmer.user_id == user.id).count()
        assert count == 1

    def test_concurrent_integrity_error_recovers_gracefully(self, db):
        user = self._provision_farmer_user("Suresh Kumar", "9876543212")
        farmer1 = ensure_farmer_record(user, db)
        farmer2 = ensure_farmer_record(user, db)
        assert farmer1.id == farmer2.id
        assert farmer1.maittri_farmer_id == farmer2.maittri_farmer_id

    def test_multithreaded_concurrent_creation_safe(self):
        import threading
        user = self._provision_farmer_user("Ramesh Patel", "9876543214")
        results = []
        errors = []

        def _worker():
            session = SessionLocal()
            try:
                f = ensure_farmer_record(user, session)
                results.append((f.id, f.maittri_farmer_id))
            except Exception as e:
                errors.append(e)
            finally:
                session.close()

        threads = [threading.Thread(target=_worker) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0, f"Concurrent execution errors: {errors}"
        assert len(results) == 5
        # All threads must receive the EXACT same canonical Farmer record
        first_id, first_mt_id = results[0]
        for fid, mfid in results:
            assert fid == first_id
            assert mfid == first_mt_id
            assert mfid == f"MT-FARM-{first_id:06d}"

        # Verify exactly one record in the database
        verify_session = SessionLocal()
        try:
            db_count = verify_session.query(Farmer).filter(Farmer.user_id == user.id).count()
            assert db_count == 1
        finally:
            verify_session.close()

    def test_update_profile_does_not_nullify_not_null_fields(self, db):
        user = self._provision_farmer_user("Valid Name", "9876543213")
        farmer = ensure_farmer_record(user, db)
        orig_name = farmer.name
        orig_mobile = farmer.mobile_number

        # Attempt to update with empty/None name and mobile_number
        payload = FarmerUpdate()  # all defaults None
        updated = update_my_farmer_profile(payload=payload, current_user=user, db=db)
        assert updated.name == orig_name
        assert updated.name is not None
        assert updated.mobile_number == orig_mobile
        assert updated.mobile_number is not None



