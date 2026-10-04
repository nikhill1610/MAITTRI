import json
import pytest
from datetime import datetime, timezone
from sqlalchemy.dialects import postgresql, sqlite
from sqlalchemy.dialects.postgresql import JSONB as PG_JSONB
from sqlalchemy.types import Text
from sqlalchemy.orm import sessionmaker

from app.models import FarmPlan, FarmPlanCompletion, Farm, JSONType
from app.database import engine


def test_farm_plan_columns_postgresql_dialect_resolves_to_jsonb():
    pg_dialect = postgresql.dialect()
    
    # 1. FarmPlan.plan_json
    plan_json_impl = FarmPlan.plan_json.type.load_dialect_impl(pg_dialect)
    assert isinstance(plan_json_impl, PG_JSONB) or plan_json_impl.__class__.__name__ == "JSONB"

    # 2. FarmPlan.plan_data_json
    plan_data_impl = FarmPlan.plan_data_json.type.load_dialect_impl(pg_dialect)
    assert isinstance(plan_data_impl, PG_JSONB) or plan_data_impl.__class__.__name__ == "JSONB"

    # 3. FarmPlanCompletion.sensor_snapshot_json
    sensor_impl = FarmPlanCompletion.sensor_snapshot_json.type.load_dialect_impl(pg_dialect)
    assert isinstance(sensor_impl, PG_JSONB) or sensor_impl.__class__.__name__ == "JSONB"

    # 4. FarmPlanCompletion.weather_snapshot_json
    weather_impl = FarmPlanCompletion.weather_snapshot_json.type.load_dialect_impl(pg_dialect)
    assert isinstance(weather_impl, PG_JSONB) or weather_impl.__class__.__name__ == "JSONB"


def test_farm_plan_columns_sqlite_dialect_resolves_to_text():
    sq_dialect = sqlite.dialect()

    assert isinstance(FarmPlan.plan_json.type.load_dialect_impl(sq_dialect), Text)
    assert isinstance(FarmPlan.plan_data_json.type.load_dialect_impl(sq_dialect), Text)
    assert isinstance(FarmPlanCompletion.sensor_snapshot_json.type.load_dialect_impl(sq_dialect), Text)
    assert isinstance(FarmPlanCompletion.weather_snapshot_json.type.load_dialect_impl(sq_dialect), Text)


def test_farm_plan_persistence_with_dict_and_string_json():
    """Verify that FarmPlan persists both json strings and dict/list payloads cleanly."""
    Session = sessionmaker(bind=engine)
    db = Session()
    try:
        farm = db.query(Farm).first()
        if not farm:
            farm = Farm(name="Test Plan Farm", area=2.0, soil_type="Alluvial Soil")
            db.add(farm)
            db.commit()

        timeline_data = [
            {"stage_id": "sowing", "name": "Sowing", "start_day": 0, "end_day": 10},
            {"stage_id": "vegetative", "name": "Vegetative", "start_day": 11, "end_day": 30}
        ]
        full_plan_data = {
            "crop": "Wheat",
            "crop_age_days": 15,
            "current_stage": {"id": "vegetative", "name": "Vegetative"},
            "timeline": timeline_data
        }

        # 1. Persist using json.dumps string (as farmer_planning_service does)
        plan_str = FarmPlan(
            farm_id=farm.id,
            user_id=farm.user_id,
            selected_crop="Wheat",
            sowing_date="2026-09-15",
            variety="HD-2967",
            current_stage="Vegetative",
            plan_json=json.dumps(timeline_data),
            plan_data_json=json.dumps(full_plan_data)
        )
        db.add(plan_str)
        db.commit()

        fetched_str = db.query(FarmPlan).filter(FarmPlan.id == plan_str.id).first()
        assert fetched_str is not None
        assert json.loads(fetched_str.plan_json) == timeline_data
        assert json.loads(fetched_str.plan_data_json)["crop"] == "Wheat"

        # 2. Persist using native dict/list
        plan_dict = FarmPlan(
            farm_id=farm.id,
            user_id=farm.user_id,
            selected_crop="Mustard",
            sowing_date="2026-10-01",
            variety="Pusa Bold",
            current_stage="Sowing",
            plan_json=timeline_data,
            plan_data_json=full_plan_data
        )
        db.add(plan_dict)
        db.commit()

        fetched_dict = db.query(FarmPlan).filter(FarmPlan.id == plan_dict.id).first()
        assert fetched_dict is not None
        assert json.loads(fetched_dict.plan_json) == timeline_data
        assert json.loads(fetched_dict.plan_data_json)["crop"] == "Wheat"

        # Cleanup
        db.delete(fetched_str)
        db.delete(fetched_dict)
        db.commit()
    finally:
        db.close()


def test_farm_plan_completion_persistence_with_dict_and_string_json():
    """Verify that FarmPlanCompletion persists sensor and weather snapshots cleanly."""
    Session = sessionmaker(bind=engine)
    db = Session()
    try:
        farm = db.query(Farm).first()
        if not farm:
            farm = Farm(name="Test Completion Farm", area=1.5, soil_type="Black Soil")
            db.add(farm)
            db.commit()

        plan = FarmPlan(
            farm_id=farm.id,
            selected_crop="Rice",
            sowing_date="2026-06-15",
            plan_json="[]"
        )
        db.add(plan)
        db.commit()

        sensor_data = {"soil_moisture": 42.0, "soil_temp": 24.5, "moisture_status": "Optimal"}
        weather_data = {"temp": 28.0, "humidity": 65, "condition": "Partly Cloudy"}

        # 1. String JSON input (as farmer_planning_service does)
        comp_str = FarmPlanCompletion(
            farm_plan_id=plan.id,
            task_title="Inspect Root Zone Moisture",
            completion_date="2026-10-04",
            sensor_snapshot_json=json.dumps(sensor_data),
            weather_snapshot_json=json.dumps(weather_data),
            farmer_notes="Field looks healthy."
        )
        db.add(comp_str)
        db.commit()

        fetched_str = db.query(FarmPlanCompletion).filter(FarmPlanCompletion.id == comp_str.id).first()
        assert fetched_str is not None
        assert json.loads(fetched_str.sensor_snapshot_json)["soil_moisture"] == 42.0
        assert json.loads(fetched_str.weather_snapshot_json)["temp"] == 28.0

        # 2. None values
        comp_none = FarmPlanCompletion(
            farm_plan_id=plan.id,
            task_title="Manual Weeding",
            completion_date="2026-10-04",
            sensor_snapshot_json=None,
            weather_snapshot_json=None
        )
        db.add(comp_none)
        db.commit()

        fetched_none = db.query(FarmPlanCompletion).filter(FarmPlanCompletion.id == comp_none.id).first()
        assert fetched_none is not None
        assert fetched_none.sensor_snapshot_json is None
        assert fetched_none.weather_snapshot_json is None

        # Cleanup
        db.delete(plan)
        db.commit()
    finally:
        db.close()
