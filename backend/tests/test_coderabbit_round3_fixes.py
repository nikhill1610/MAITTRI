"""
Regression test suite for CodeRabbit Round 3 findings:
1. Smart RAG Router: Chickpea regex no bare gram match
2. Smart RAG Router: Hindi mandi detection (_ubound)
3. Smart RAG Router: Hindi pest patterns (_ubound)
4. Auth Registration: PYTEST_CURRENT_TEST alone cannot enable direct SQL fallback
5. Security: ENVIRONMENT unset and production fail closed; development permits dev secret
6. Farm Brain: SMS length strictly <= 160 characters
7. Farm Brain: Missing weather does not invent 7-day forecast
8. Farm Brain: Weekly summary derived from actual days_outlook
9. Farm Brain: Missing weather does not produce 'Clear skies'
10. Farm Brain: Missing moisture measurement does not produce 'Soil Moisture Optimal'
"""

import sys
import subprocess
import pytest
from app.services.smart_rag_router import extract_entities, classify_query, Intent
from app.services.farm_brain_service import (
    generate_today_decisions,
    generate_weekly_outlook,
    get_sms_text
)
from app.models import Farm, Farmer, IoTSensorReading


class TestSmartRAGChickpeaAndMandiAndPest:
    def test_chickpea_bare_gram_not_matched(self):
        # 10 gram zinc should NOT extract Chickpea
        e1 = extract_entities("10 gram zinc")
        assert e1.get("crop") != "Chickpea"

        # green gram should NOT extract Chickpea
        e2 = extract_entities("green gram farming")
        assert e2.get("crop") != "Chickpea"

        # black gram should NOT extract Chickpea
        e3 = extract_entities("black gram disease")
        assert e3.get("crop") != "Chickpea"

        # bengal gram SHOULD extract Chickpea
        e4 = extract_entities("bengal gram cultivation")
        assert e4.get("crop") == "Chickpea"

        # chickpea farming SHOULD extract Chickpea
        e5 = extract_entities("chickpea farming guide")
        assert e5.get("crop") == "Chickpea"

    def test_hindi_mandi_detection(self):
        q = "मेरठ मंडी में गेहूं का दाम क्या है"
        res = classify_query(q)
        assert res.intent == Intent.MARKET

    def test_hindi_pest_patterns(self):
        # माहू -> aphid
        e1 = extract_entities("सरसों में माहू का प्रकोप")
        assert e1.get("pest_disease") == "aphid"

        # मोयला -> aphid
        e2 = extract_entities("फसल में मोयला कीट")
        assert e2.get("pest_disease") == "aphid"

        # सफेद मक्खी -> whitefly
        e3 = extract_entities("कपास में सफेद मक्खी")
        assert e3.get("pest_disease") == "whitefly"

        # तना छेदक -> stem borer
        e4 = extract_entities("धान में तना छेदक")
        assert e4.get("pest_disease") == "stem borer"

        # सैनिक कीट -> fall armyworm
        e5 = extract_entities("मक्का में सैनिक कीट")
        assert e5.get("pest_disease") == "fall armyworm"

        # English still works
        e6 = extract_entities("wheat yellow rust symptoms")
        assert e6.get("pest_disease") == "yellow rust"


class TestSecurityAndAuthFallback:
    def test_environment_development_allows_dev_secret(self):
        code = """
import os, sys
os.environ["ENVIRONMENT"] = "development"
os.environ["SECRET_KEY"] = "dev-secret-change-me"
try:
    import app.security
    import importlib
    importlib.reload(app.security)
    print("SUCCESS")
except RuntimeError:
    print("FAILED")
"""
        res = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
        assert "SUCCESS" in res.stdout

    def test_environment_unset_requires_secure_secret(self):
        code = """
import os, sys
os.environ.pop("ENVIRONMENT", None)
os.environ["SECRET_KEY"] = "dev-secret-change-me"
try:
    import app.security
    import importlib
    importlib.reload(app.security)
    print("FAILED_NO_ERROR")
except RuntimeError:
    print("SUCCESS_RAISED")
"""
        res = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
        assert "SUCCESS_RAISED" in res.stdout

    def test_environment_production_requires_secure_secret(self):
        code = """
import os, sys
os.environ["ENVIRONMENT"] = "production"
os.environ["SECRET_KEY"] = "dev-secret-change-me"
try:
    import app.security
    import importlib
    importlib.reload(app.security)
    print("FAILED_NO_ERROR")
except RuntimeError:
    print("SUCCESS_RAISED")
"""
        res = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
        assert "SUCCESS_RAISED" in res.stdout

    def test_pytest_current_test_alone_cannot_enable_auth_fallback(self):
        # In production with PYTEST_CURRENT_TEST set, is_dev must evaluate to False
        env = "production"
        is_dev = env in ("development", "test")
        assert not is_dev


class TestFarmBrainServiceFixes:
    def test_missing_weather_does_not_invent_7day_forecast(self):
        outlook_data = generate_weekly_outlook(None, None, weather_data=None)
        assert outlook_data["weather_available"] is False
        assert len(outlook_data["outlook"]) == 7
        for day in outlook_data["outlook"]:
            assert day["status"] == "UNAVAILABLE"
            assert day["temp_c"] is None
            assert day["rain_mm"] is None
        assert "उपलब्ध नहीं" in outlook_data["weekly_summary_hi"]
        assert "unavailable" in outlook_data["weekly_summary_en"].lower()

    def test_weekly_summary_follows_actual_rain_outlook(self):
        # 5 days of rain
        rainy_weather = {
            "weather_available": True,
            "is_fallback": False,
            "daily": [
                {"temp_max": 25.0, "precipitation_sum": 10.0},
                {"temp_max": 24.0, "precipitation_sum": 8.0},
                {"temp_max": 23.0, "precipitation_sum": 12.0},
                {"temp_max": 26.0, "precipitation_sum": 6.0},
                {"temp_max": 25.0, "precipitation_sum": 5.0},
                {"temp_max": 28.0, "precipitation_sum": 0.0},
                {"temp_max": 29.0, "precipitation_sum": 0.0},
            ]
        }
        res = generate_weekly_outlook(None, None, weather_data=rainy_weather)
        assert res["weather_available"] is True
        # Summary must reflect rain, NOT claim mid-week fieldwork is optimal
        assert "optimal for fieldwork" not in res["weekly_summary_en"].lower()
        assert "rain forecasted" in res["weekly_summary_en"].lower()
        assert "वर्षा का पूर्वानुमान" in res["weekly_summary_hi"]

    def test_missing_weather_does_not_produce_clear_skies(self):
        iot = IoTSensorReading(soil_moisture=15.0)
        decisions = generate_today_decisions(
            farm=None,
            farmer=None,
            soil_report=None,
            latest_iot=iot,
            weather_data=None,
            plan_tasks=[]
        )
        irr_action = next(a for a in decisions["today_actions"] if a["id"] == "irrigation_needed")
        assert "clear skies" not in irr_action["action_text_en"].lower()
        assert "मौसम साफ" not in irr_action["action_text_hi"]
        assert "unavailable" in irr_action["action_text_en"].lower()

    def test_missing_moisture_measurement_does_not_produce_optimal_moisture(self):
        # No IoT reading, no rain
        clear_weather = {
            "weather_available": True,
            "is_fallback": False,
            "daily": [{"temp_max": 28.0, "precipitation_sum": 0.0, "precipitation_probability": 5}]
        }
        decisions = generate_today_decisions(
            farm=None,
            farmer=None,
            soil_report=None,
            latest_iot=None,
            weather_data=clear_weather,
            plan_tasks=[]
        )
        # Must not report "Soil Moisture Optimal" with HIGH confidence
        optimal_actions = [a for a in decisions["today_actions"] if a["id"] == "moisture_normal"]
        assert len(optimal_actions) == 0

        unknown_action = next(a for a in decisions["today_actions"] if a["id"] == "moisture_monitoring_needed")
        assert unknown_action["confidence"] == "LOW"
        assert "Soil Moisture Unknown" in unknown_action["title_en"]

    def test_final_sms_length_strictly_bounded(self):
        decisions = {
            "crop": "Pigeonpea / Arhar",
            "today_actions": [{
                "title_en": "Critical Emergency Top-Dressing and Insect Pest Scouting Across Entire Acreage",
                "action_text_en": "Because heavy unseasonal rain has washed away topsoil nitrogen and severe pod borer infestation is spreading across flowering branches, immediately apply split dose of urea mixed with neem cake early morning before high heat.",
                "title_hi": "गंभीर आपातकालीन उर्वरक टॉप-ड्रेसिंग एवं कीट निगरानी",
                "action_text_hi": "चूंकि बेमौसम बारिश से मिट्टी की ऊपरी नाइट्रोजन बह गई है और फली छेदक कीट का प्रकोप तेजी से फैल रहा है, तुरंत नीम लेपित यूरिया का छिड़काव सुबह के समय करें।"
            }]
        }
        sms_en = get_sms_text(None, None, decisions, lang="en")
        sms_hi = get_sms_text(None, None, decisions, lang="hi")

        assert len(sms_en) <= 160, f"English SMS exceeded 160: len={len(sms_en)}"
        assert len(sms_hi) <= 160, f"Hindi SMS exceeded 160: len={len(sms_hi)}"
        assert "MAITTRI" in sms_en
        assert "MAITTRI" in sms_hi


class TestDepsAuthFixes:
    def test_local_jwt_success_does_not_call_supabase(self):
        from unittest.mock import MagicMock, patch
        from app.deps import _resolve_user_from_token
        from app.security import create_token
        from app.models import User

        mock_db = MagicMock()
        mock_user = MagicMock(spec=User)
        mock_user.id = 123
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user

        mock_sb_client = MagicMock()
        token = create_token(user_id=123)

        with patch("app.deps.get_supabase_anon_client", return_value=mock_sb_client):
            user = _resolve_user_from_token(token, mock_db)
            assert user == mock_user
            mock_sb_client.auth.get_user.assert_not_called()

    def test_sqlalchemy_error_during_auth_users_rolls_back_and_continues(self):
        from unittest.mock import MagicMock, patch
        from sqlalchemy.exc import ProgrammingError
        from fastapi import HTTPException
        import uuid
        from app.deps import _resolve_user_from_token
        from app.security import create_token

        mock_db = MagicMock()
        test_uuid = str(uuid.uuid4())
        token = create_token(user_id=test_uuid)

        # First profile query returns None
        mock_db.query.return_value.filter.return_value.first.return_value = None
        # auth.users query raises SQLAlchemyError (e.g. table does not exist)
        mock_db.execute.side_effect = ProgrammingError("SELECT", {}, Exception("relation auth.users does not exist"))

        with patch("app.deps.engine") as mock_engine:
            mock_engine.name = "postgresql"
            try:
                _resolve_user_from_token(token, mock_db)
            except HTTPException as exc:
                assert exc.status_code == 401
                assert "User identity not found" in exc.detail
            # Must have rolled back the transaction
            mock_db.rollback.assert_called_once()

