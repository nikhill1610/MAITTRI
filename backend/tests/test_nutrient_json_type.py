import json
import pytest
from sqlalchemy.dialects import postgresql, sqlite
from sqlalchemy.dialects.postgresql import JSONB as PG_JSONB
from sqlalchemy.types import Text
from sqlalchemy.orm import sessionmaker

from app.models import JSONType, NutrientAnalysisRecord, Farm
from app.database import engine, Base


def test_postgresql_dialect_resolves_to_jsonb():
    jt = JSONType()
    pg_dialect = postgresql.dialect()
    impl = jt.load_dialect_impl(pg_dialect)
    assert isinstance(impl, PG_JSONB) or impl.__class__.__name__ == "JSONB"


def test_sqlite_dialect_resolves_to_text():
    jt = JSONType()
    sq_dialect = sqlite.dialect()
    impl = jt.load_dialect_impl(sq_dialect)
    assert isinstance(impl, Text) or impl.__class__.__name__ == "Text"


def test_dict_list_values_serialize_correctly():
    jt = JSONType()
    pg_dialect = postgresql.dialect()
    sq_dialect = sqlite.dialect()

    sample_dict = {"nitrogen": 45.0, "status": "optimal", "elements": ["N", "P", "K"]}
    sample_list = ["N", "P", "K"]

    # PostgreSQL: preserves dict/list for native JSONB binding
    assert jt.process_bind_param(sample_dict, pg_dialect) == sample_dict
    assert jt.process_bind_param(sample_list, pg_dialect) == sample_list

    # SQLite: serializes to JSON string
    sq_bound_dict = jt.process_bind_param(sample_dict, sq_dialect)
    assert isinstance(sq_bound_dict, str)
    assert json.loads(sq_bound_dict) == sample_dict

    sq_bound_list = jt.process_bind_param(sample_list, sq_dialect)
    assert isinstance(sq_bound_list, str)
    assert json.loads(sq_bound_list) == sample_list

    # Result processing: returns JSON string to preserve compatibility with route json.loads()
    assert json.loads(jt.process_result_value(sample_dict, pg_dialect)) == sample_dict
    assert json.loads(jt.process_result_value(sample_list, pg_dialect)) == sample_list


def test_valid_json_strings_handled_correctly():
    jt = JSONType()
    pg_dialect = postgresql.dialect()
    sq_dialect = sqlite.dialect()

    raw_json_str = '{"farm_id": 467, "score": 92.5}'

    # PostgreSQL: decodes JSON string into dict so JSONB binding does not fail with DatatypeMismatch
    pg_bound = jt.process_bind_param(raw_json_str, pg_dialect)
    assert isinstance(pg_bound, dict)
    assert pg_bound["farm_id"] == 467

    # SQLite: keeps JSON string as-is for Text storage
    sq_bound = jt.process_bind_param(raw_json_str, sq_dialect)
    assert isinstance(sq_bound, str)
    assert sq_bound == raw_json_str

    # Result processing for string remains string
    assert jt.process_result_value(raw_json_str, pg_dialect) == raw_json_str
    assert jt.process_result_value(raw_json_str, sq_dialect) == raw_json_str


def test_none_remains_none():
    jt = JSONType()
    pg_dialect = postgresql.dialect()
    sq_dialect = sqlite.dialect()

    # Bind param None
    assert jt.process_bind_param(None, pg_dialect) is None
    assert jt.process_bind_param(None, sq_dialect) is None

    # Result value None
    assert jt.process_result_value(None, pg_dialect) is None
    assert jt.process_result_value(None, sq_dialect) is None


def test_nutrient_record_persistence_in_test_database():
    """Verify that NutrientAnalysisRecord with JSONType persists and queries cleanly."""
    Session = sessionmaker(bind=engine)
    db = Session()
    try:
        # Create a test farm if needed or find existing
        farm = db.query(Farm).first()
        if not farm:
            farm = Farm(name="Test Nutrient Farm", area=1.0, soil_type="Loamy Soil")
            db.add(farm)
            db.commit()

        analysis_payload = {
            "farm_id": farm.id,
            "soil_type": "Loamy Soil",
            "nutrients": [{"symbol": "N", "status": "Deficient"}]
        }

        # 1. Persist using json.dumps string (as route currently does)
        rec = NutrientAnalysisRecord(
            farm_id=farm.id,
            user_id=farm.user_id,
            analysis_json=json.dumps(analysis_payload)
        )
        db.add(rec)
        db.commit()

        # Query back and verify result is a JSON string compatible with json.loads
        fetched = db.query(NutrientAnalysisRecord).filter(NutrientAnalysisRecord.id == rec.id).first()
        assert fetched is not None
        assert isinstance(fetched.analysis_json, str)
        parsed = json.loads(fetched.analysis_json)
        assert parsed["nutrients"][0]["symbol"] == "N"

        # Cleanup
        db.delete(fetched)
        db.commit()
    finally:
        db.close()
