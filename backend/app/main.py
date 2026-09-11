import os
from pathlib import Path

# Automatically load environment variables from .env
try:
    from dotenv import load_dotenv
    load_dotenv()
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
    load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env")
except ImportError:
    pass

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import inspect, text
from sqlalchemy.orm import Session
from .database import Base, engine, get_db
from .routes import auth, farms, recommendations, weather, location, nutrients, soil, parali, market_prices, fertilizer, government_schemes, insurance, iot, farmer_planning

Base.metadata.create_all(bind=engine)


# Safe SQLite migration for newly added columns
try:
    with engine.connect() as conn:
        cols = [c["name"] for c in inspect(engine).get_columns("farms")]
        migrations = [
            ("location_name", "VARCHAR(120)"),
            ("location_source", "VARCHAR(50) DEFAULT 'manual'"),
            ("soil_type_source", "VARCHAR(50) DEFAULT 'farmer_selected'"),
            ("soil_confidence", "VARCHAR(20) DEFAULT 'Medium'"),
            ("previous_crop_period", "VARCHAR(80)"),
            ("cultivation_count", "INTEGER DEFAULT 1"),
            ("sowing_date", "VARCHAR(40)"),
        ]
        for col_name, col_type in migrations:
            if col_name not in cols:
                conn.execute(text(f"ALTER TABLE farms ADD COLUMN {col_name} {col_type}"))

        # Migration for FarmPlan table
        if inspect(engine).has_table("farm_plans"):
            fp_cols = [c["name"] for c in inspect(engine).get_columns("farm_plans")]
            fp_migrations = [
                ("user_id", "INTEGER"),
                ("sowing_date", "VARCHAR(40)"),
                ("variety", "VARCHAR(80)"),
                ("current_stage", "VARCHAR(80)"),
                ("plan_data_json", "TEXT"),
                ("updated_at", "DATETIME")
            ]
            for col_name, col_type in fp_migrations:
                if col_name not in fp_cols:
                    conn.execute(text(f"ALTER TABLE farm_plans ADD COLUMN {col_name} {col_type}"))

        # Migration for IoT sensor readings table
        iot_cols = [c["name"] for c in inspect(engine).get_columns("iot_sensor_readings")]
        if "water_distance_cm" not in iot_cols:
            conn.execute(text("ALTER TABLE iot_sensor_readings ADD COLUMN water_distance_cm FLOAT"))

        conn.commit()
except Exception:
    pass

app = FastAPI(title="Smart Agriculture AI API", version="1.0.0")

# Start LAN IoT bridge so physical nodes (ESP32/ESP8266) can reach localhost:8000
try:
    from .services.lan_bridge import start_lan_bridge
    start_lan_bridge(port=8000)
except Exception:
    pass

@app.on_event("startup")
def startup_event():
    try:
        from .services.lan_bridge import start_lan_bridge
        start_lan_bridge(port=8000)
    except Exception:
        pass

_cors_env = os.getenv("CORS_ORIGINS")
_default_origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:5174",
    "http://127.0.0.1:5174",
]
_allowed_origins = [o.strip() for o in _cors_env.split(",") if o.strip()] if _cors_env else _default_origins

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1|192\.168\.\d+\.\d+|10\.\d+\.\d+\.\d+|172\.(1[6-9]|2\d|3[0-1])\.\d+\.\d+)(:\d+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/auth", tags=["Auth"])
app.include_router(farms.router, prefix="/api/farms", tags=["Farms"])
app.include_router(recommendations.router, prefix="/api/recommendations", tags=["Recommendations"])
app.include_router(weather.router, prefix="/api/weather", tags=["Weather"])
app.include_router(location.router, prefix="/api/location", tags=["Location"])
app.include_router(soil.router, prefix="/api/soil", tags=["Soil"])
app.include_router(nutrients.router, prefix="/api/nutrients", tags=["Nutrients"])
app.include_router(parali.router, prefix="/api/parali", tags=["Parali"])
app.include_router(market_prices.router, prefix="/api/market-prices", tags=["Market Prices"])
app.include_router(fertilizer.fertilizer_router, prefix="/api/fertilizer", tags=["Fertilizer"])
app.include_router(fertilizer.pest_router, prefix="/api/pest", tags=["Pest Management"])
app.include_router(government_schemes.router, prefix="/api/government-schemes", tags=["Government Schemes"])
app.include_router(insurance.router, prefix="/api/insurance", tags=["Insurance Planning"])
app.include_router(iot.router, prefix="/api/iot", tags=["IoT & Ultrasonic Radar"])
app.include_router(farmer_planning.router, prefix="/api/farmer-plans", tags=["Farmer Planning"])
app.include_router(farmer_planning.calendar_router, prefix="/api/crop-calendar", tags=["Crop Calendar"])


# Resilient fallbacks for microcontroller path variations
from .schemas import IoTSensorDataCreate
from .services.iot_service import process_incoming_sensor_data
from fastapi import Depends

@app.post("/sensor-data", status_code=200, tags=["IoT Fallback"])
@app.post("/api/sensor-data", status_code=200, tags=["IoT Fallback"])
@app.post("/telemetry", status_code=200, tags=["IoT Fallback"])
def fallback_sensor_data(data: IoTSensorDataCreate, db: Session = Depends(get_db)):
    telemetry = process_incoming_sensor_data(db, data)
    return {"success": True, "status": "success", "message": "Sensor data received successfully", "data": telemetry}

@app.get("/")
def root():
    return {"message": "Smart Agriculture AI API is running"}

@app.get("/api/health")
def health():
    return {"status": "ok"}
