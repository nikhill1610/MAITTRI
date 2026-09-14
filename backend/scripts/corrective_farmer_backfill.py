"""
MAITRI Platform — Phase 5 Targeted Corrective Farmer Backfill
============================================================
Performs idempotent backfill for the 4 genuinely missing legacy farmer records:
- MT-FARM-000005 (Legacy ID 5, user_id 117)
- MT-FARM-000006 (Legacy ID 6, user_id 118)
- MT-FARM-000008 (Legacy ID 8, user_id 1)
- MT-FARM-000010 (Legacy ID 10, user_id 16)

Source of truth: backups/pre_migration_backup/agri.db (READ-ONLY)
Conflict key: maittri_farmer_id (Authoritative identity)

Updates verified farm relationships:
- Target Farm 39 (Source Farm 38) -> Farmer MT-FARM-000005
- Target Farm 40 (Source Farm 39) -> Farmer MT-FARM-000006
- Target Farm 9  (Source Farm 2)  -> Farmer MT-FARM-000008
"""

import os
import sys
import json
import sqlite3
import logging
from pathlib import Path
from datetime import datetime
from dotenv import dotenv_values
from sqlalchemy import create_engine, text

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("maitri.corrective_backfill")

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
BACKUP_DB = ROOT_DIR / "backups" / "pre_migration_backup" / "agri.db"
MAPPINGS_FILE = ROOT_DIR / "scratch" / "migration_id_mappings.json"

vals = dotenv_values(ROOT_DIR / "backend" / ".env")
db_url = vals.get("DATABASE_URL")
if not db_url:
    raise RuntimeError("DATABASE_URL not configured in backend/.env")

engine = create_engine(
    db_url,
    pool_pre_ping=True,
    connect_args={"connect_timeout": 20, "sslmode": "require"}
)

# Open SQLite source in read-only mode
sqlite_uri = f"file:{os.path.abspath(str(BACKUP_DB))}?mode=ro"
sconn = sqlite3.connect(sqlite_uri, uri=True)
sconn.row_factory = sqlite3.Row

# Load current mappings
with open(MAPPINGS_FILE, "r", encoding="utf-8") as f:
    mappings = json.load(f)

user_map = {int(k): v for k, v in mappings.get("users", {}).items()}
farmer_map = {int(k): v for k, v in mappings.get("farmers", {}).items()}
farm_map = {int(k): v for k, v in mappings.get("farms", {}).items()}

TARGET_MFIDS = [
    "MT-FARM-000005",
    "MT-FARM-000006",
    "MT-FARM-000008",
    "MT-FARM-000010"
]

def run_backfill():
    logger.info("Starting targeted corrective farmer backfill...")
    
    # Query source records
    source_records = sconn.execute("""
        SELECT * FROM farmers 
        WHERE maittri_farmer_id IN (?, ?, ?, ?)
        ORDER BY id
    """, tuple(TARGET_MFIDS)).fetchall()

    logger.info(f"Retrieved {len(source_records)} source farmer records from SQLite backup.")

    inserted_farmers = []
    skipped_farmers = []

    with engine.begin() as conn:
        for sf in source_records:
            sf_dict = dict(sf)
            mfid = sf_dict["maittri_farmer_id"]
            leg_id = sf_dict["id"]
            legacy_uid = sf_dict["user_id"]
            target_uid = user_map.get(legacy_uid) if legacy_uid else None

            # 1. Idempotency check: check by authoritative maittri_farmer_id ONLY
            existing = conn.execute(
                text("SELECT id, name, user_id FROM public.farmers WHERE maittri_farmer_id = :mfid"),
                {"mfid": mfid}
            ).fetchone()

            if existing:
                target_id = existing[0]
                logger.info(f"Farmer {mfid} already exists in Supabase as ID {target_id}. Skipping insert.")
                farmer_map[leg_id] = target_id
                skipped_farmers.append({
                    "legacy_id": leg_id,
                    "maittri_farmer_id": mfid,
                    "target_id": target_id,
                    "name": existing[1],
                    "status": "ALREADY_EXISTS"
                })
                continue

            # 2. Insert new farmer record preserving all original fields
            res = conn.execute(text("""
                INSERT INTO public.farmers (
                    maittri_farmer_id, user_id, operator_id, name, mobile_number, alternate_mobile,
                    state, district, block, village, farm_area, area_unit, land_ownership,
                    irrigation, soil_type, soil_test_available, current_crop, previous_crop,
                    planned_crop, sowing_date, crop_variety, preferred_language, sms_consent,
                    ivr_consent, qr_code_data, created_at, updated_at
                ) VALUES (
                    :maittri_farmer_id, :user_id, :operator_id, :name, :mobile_number, :alternate_mobile,
                    :state, :district, :block, :village, :farm_area, :area_unit, :land_ownership,
                    :irrigation, :soil_type, :soil_test_available, :current_crop, :previous_crop,
                    :planned_crop, :sowing_date, :crop_variety, :preferred_language, :sms_consent,
                    :ivr_consent, :qr_code_data, :created_at, :updated_at
                ) RETURNING id;
            """), {
                "maittri_farmer_id": mfid,
                "user_id": target_uid,
                "operator_id": None,
                "name": sf_dict["name"],
                "mobile_number": sf_dict["mobile_number"],
                "alternate_mobile": sf_dict["alternate_mobile"],
                "state": sf_dict["state"],
                "district": sf_dict["district"],
                "block": sf_dict["block"],
                "village": sf_dict["village"],
                "farm_area": sf_dict["farm_area"],
                "area_unit": sf_dict["area_unit"] or "acre",
                "land_ownership": sf_dict["land_ownership"],
                "irrigation": sf_dict["irrigation"],
                "soil_type": sf_dict["soil_type"],
                "soil_test_available": bool(sf_dict["soil_test_available"]),
                "current_crop": sf_dict["current_crop"],
                "previous_crop": sf_dict["previous_crop"],
                "planned_crop": sf_dict["planned_crop"],
                "sowing_date": sf_dict["sowing_date"],
                "crop_variety": sf_dict["crop_variety"],
                "preferred_language": sf_dict["preferred_language"] or "hi",
                "sms_consent": bool(sf_dict["sms_consent"]),
                "ivr_consent": bool(sf_dict["ivr_consent"]),
                "qr_code_data": sf_dict["qr_code_data"],
                "created_at": sf_dict["created_at"] or datetime.utcnow(),
                "updated_at": sf_dict["updated_at"] or datetime.utcnow()
            })
            new_target_id = res.scalar()
            farmer_map[leg_id] = new_target_id
            logger.info(f"Successfully inserted farmer {mfid} ('{sf_dict['name']}') -> Supabase ID {new_target_id}")
            inserted_farmers.append({
                "legacy_id": leg_id,
                "maittri_farmer_id": mfid,
                "target_id": new_target_id,
                "name": sf_dict["name"],
                "user_id": target_uid,
                "status": "INSERTED"
            })

        # 3. Update verified farm foreign-key relationships
        # Verify Farm 38: source farmer_id = 5 -> Target Farm 39
        target_farm_39_id = farm_map.get(38)
        target_farmer_5_id = farmer_map.get(5)
        farm_updates = []

        if target_farm_39_id and target_farmer_5_id:
            conn.execute(
                text("UPDATE public.farms SET farmer_id = :fid, updated_at = now() WHERE id = :farm_id"),
                {"fid": target_farmer_5_id, "farm_id": target_farm_39_id}
            )
            logger.info(f"Updated Target Farm {target_farm_39_id} (Source 38) -> farmer_id={target_farmer_5_id}")
            farm_updates.append({
                "target_farm_id": target_farm_39_id,
                "source_farm_id": 38,
                "farm_name": "North Field",
                "old_farmer_id": 1,
                "new_farmer_id": target_farmer_5_id,
                "farmer_mfid": "MT-FARM-000005"
            })

        # Verify Farm 39: source farmer_id = 6 -> Target Farm 40
        target_farm_40_id = farm_map.get(39)
        target_farmer_6_id = farmer_map.get(6)
        if target_farm_40_id and target_farmer_6_id:
            conn.execute(
                text("UPDATE public.farms SET farmer_id = :fid, updated_at = now() WHERE id = :farm_id"),
                {"fid": target_farmer_6_id, "farm_id": target_farm_40_id}
            )
            logger.info(f"Updated Target Farm {target_farm_40_id} (Source 39) -> farmer_id={target_farmer_6_id}")
            farm_updates.append({
                "target_farm_id": target_farm_40_id,
                "source_farm_id": 39,
                "farm_name": "North Field",
                "old_farmer_id": 1,
                "new_farmer_id": target_farmer_6_id,
                "farmer_mfid": "MT-FARM-000006"
            })

        # Verify Farm 2: source farmer_id = 8 -> Target Farm 9
        target_farm_9_id = farm_map.get(2)
        target_farmer_8_id = farmer_map.get(8)
        if target_farm_9_id and target_farmer_8_id:
            conn.execute(
                text("UPDATE public.farms SET farmer_id = :fid, updated_at = now() WHERE id = :farm_id"),
                {"fid": target_farmer_8_id, "farm_id": target_farm_9_id}
            )
            logger.info(f"Updated Target Farm {target_farm_9_id} (Source 2) -> farmer_id={target_farmer_8_id}")
            farm_updates.append({
                "target_farm_id": target_farm_9_id,
                "source_farm_id": 2,
                "farm_name": "Kashi Organic Farm",
                "old_farmer_id": 1,
                "new_farmer_id": target_farmer_8_id,
                "farmer_mfid": "MT-FARM-000008"
            })

    sconn.close()

    # Save updated mappings
    mappings["farmers"] = {str(k): v for k, v in farmer_map.items()}
    with open(MAPPINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(mappings, f, indent=2)
    logger.info(f"Updated mappings saved to {MAPPINGS_FILE}")

    backfill_summary = {
        "timestamp": datetime.utcnow().isoformat(),
        "inserted_farmers": inserted_farmers,
        "skipped_farmers": skipped_farmers,
        "farm_updates": farm_updates
    }

    summary_file = ROOT_DIR / "scratch" / "corrective_backfill_summary.json"
    with open(summary_file, "w", encoding="utf-8") as f:
        json.dump(backfill_summary, f, indent=2)

    logger.info(f"Backfill summary written to {summary_file}")
    return backfill_summary

if __name__ == "__main__":
    summary = run_backfill()
    print("\nBackfill execution completed successfully:")
    print(json.dumps(summary, indent=2))
