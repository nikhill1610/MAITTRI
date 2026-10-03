import os
import json
import pytest
from datetime import datetime, timezone
from sqlalchemy.dialects import postgresql, sqlite
from sqlalchemy.dialects.postgresql import JSONB as PG_JSONB
from sqlalchemy.types import Text
from sqlalchemy.orm import sessionmaker

from app.models import FertilizerRecommendation, Farm, JSONType
from app.database import engine


def test_fertilizer_recommendation_column_postgresql_dialect_resolves_to_jsonb():
    """Verify that FertilizerRecommendation.recommendation_json maps to JSONB in PostgreSQL."""
    pg_dialect = postgresql.dialect()
    json_impl = FertilizerRecommendation.recommendation_json.type.load_dialect_impl(pg_dialect)
    assert isinstance(json_impl, PG_JSONB) or json_impl.__class__.__name__ == "JSONB"


def test_fertilizer_recommendation_column_sqlite_dialect_resolves_to_text():
    """Verify that FertilizerRecommendation.recommendation_json maps to Text in SQLite."""
    sq_dialect = sqlite.dialect()
    assert isinstance(FertilizerRecommendation.recommendation_json.type.load_dialect_impl(sq_dialect), Text)


def test_fertilizer_recommendation_persistence_with_string_and_dict():
    """Verify that FertilizerRecommendation persists both json strings and dicts cleanly."""
    Session = sessionmaker(bind=engine)
    db = Session()
    try:
        farm = db.query(Farm).first()
        if not farm:
            farm = Farm(name="Test Fert Farm", area=2.0, soil_type="Alluvial soil")
            db.add(farm)
            db.commit()

        sample_rec_dict = {
            "crop": "Wheat",
            "section_C_fertilizer_recommendation": {"summary": "Apply Urea and DAP based on soil test."},
            "section_K_confidence_and_explanation": {"confidence_level": "High"}
        }

        # 1. String JSON (matches current fertilizer route: json.dumps(recommendation))
        rec_str = FertilizerRecommendation(
            farm_id=farm.id,
            user_id=farm.user_id,
            crop="Wheat",
            previous_crop="Rice",
            stage="Tillering",
            soil_type="Alluvial soil",
            recommendation_json=json.dumps(sample_rec_dict),
            confidence="High",
            explanation_summary="Apply Urea and DAP based on soil test."
        )
        db.add(rec_str)
        db.commit()

        fetched_str = db.query(FertilizerRecommendation).filter_by(id=rec_str.id).first()
        assert fetched_str is not None
        # Must be parseable with json.loads as expected by GET /fertilizer/history
        parsed_str = json.loads(fetched_str.recommendation_json) if isinstance(fetched_str.recommendation_json, str) else fetched_str.recommendation_json
        assert parsed_str["crop"] == "Wheat"
        assert parsed_str["section_C_fertilizer_recommendation"]["summary"] == "Apply Urea and DAP based on soil test."

        db.delete(rec_str)
        db.commit()

        # 2. Dict input directly
        rec_dict = FertilizerRecommendation(
            farm_id=farm.id,
            user_id=farm.user_id,
            crop="Wheat",
            previous_crop="Rice",
            stage="CRI",
            soil_type="Alluvial soil",
            recommendation_json=sample_rec_dict,
            confidence="High",
            explanation_summary="CRI stage fertilizer"
        )
        db.add(rec_dict)
        db.commit()

        fetched_dict = db.query(FertilizerRecommendation).filter_by(id=rec_dict.id).first()
        assert fetched_dict is not None
        parsed_dict = json.loads(fetched_dict.recommendation_json) if isinstance(fetched_dict.recommendation_json, str) else fetched_dict.recommendation_json
        assert parsed_dict["crop"] == "Wheat"

        db.delete(rec_dict)
        db.commit()

    finally:
        db.close()


def test_live_supabase_fertilizer_recommendation_insert_and_cleanup():
    """
    If connection to Supabase is available, perform an actual live insert
    verifying that PostgreSQL JSONB type matching works with zero DatatypeMismatch errors.
    """
    import psycopg

    pooler_url = "postgresql+psycopg://postgres.uxyhccentpqotdjxkqob:Maittri%40%2302@aws-0-ap-south-1.pooler.supabase.com:5432/postgres"
    from sqlalchemy import create_engine
    try:
        pg_engine = create_engine(pooler_url, connect_args={"connect_timeout": 3})
        PgSession = sessionmaker(bind=pg_engine)
        pg_db = PgSession()

        farm = pg_db.query(Farm).first()
        if not farm:
            pg_db.close()
            pytest.skip("No farm available on live Supabase")

        rec = FertilizerRecommendation(
            farm_id=farm.id,
            user_id=farm.user_id,
            crop="Wheat",
            previous_crop="Rice",
            stage="Tillering",
            soil_type="Alluvial soil",
            recommendation_json=json.dumps({"test": "live_supabase_validation", "n_kg": 120}),
            confidence="High",
            explanation_summary="Live validation summary"
        )
        pg_db.add(rec)
        pg_db.commit()
        assert rec.id is not None

        # Read back
        fetched = pg_db.query(FertilizerRecommendation).filter_by(id=rec.id).first()
        assert fetched is not None
        parsed = json.loads(fetched.recommendation_json)
        assert parsed["test"] == "live_supabase_validation"
        assert parsed["n_kg"] == 120

        # Clean up
        pg_db.delete(rec)
        pg_db.commit()
        pg_db.close()
    except Exception as e:
        # If network/firewall restricts external pooler connection in runner, skip gracefully
        if "connect" in str(e).lower() or "timeout" in str(e).lower():
            pytest.skip(f"Live Supabase connection unavailable in current environment: {e}")
        raise
