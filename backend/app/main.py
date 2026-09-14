import os
from pathlib import Path
from contextlib import asynccontextmanager

# Automatically load environment variables from .env
try:
    from dotenv import load_dotenv
    load_dotenv()
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
    load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env")
except ImportError:
    pass

import logging
logger = logging.getLogger("maitri.main")

from fastapi import FastAPI, HTTPException, status, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import inspect, text
from sqlalchemy.orm import Session
from .database import Base, engine, get_db
from .routes import (
    auth, farms, recommendations, weather, location, nutrients, soil,
    parali, market_prices, fertilizer, government_schemes, insurance,
    iot, farmer_planning, chat, operators, farmer_profile, soil_tests,
    service_requests, documents, farm_brain, communications
)

_environment = os.getenv("ENVIRONMENT", "production").lower()

if engine.name == "sqlite" and _environment == "development":
    Base.metadata.create_all(bind=engine)
    # Safe SQLite migration for newly added columns in local development mode
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

            # Migration for users table (role, full_name, phone_number)
            if inspect(engine).has_table("users"):
                user_cols = [c["name"] for c in inspect(engine).get_columns("users")]
                user_migrations = [
                    ("role", "VARCHAR(50) DEFAULT 'FARMER'"),
                    ("full_name", "VARCHAR(120)"),
                    ("phone_number", "VARCHAR(20)")
                ]
                for col_name, col_type in user_migrations:
                    if col_name not in user_cols:
                        conn.execute(text(f"ALTER TABLE users ADD COLUMN {col_name} {col_type}"))

            # Migration for farms table (farmer_id)
            if "farmer_id" not in cols:
                conn.execute(text("ALTER TABLE farms ADD COLUMN farmer_id INTEGER"))

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
    except Exception as e:
        logger.warning(f"Local dev SQLite migration warning: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Start LAN IoT bridge only in local development mode
    if _environment == "development":
        try:
            from .services.lan_bridge import start_lan_bridge
            start_lan_bridge(port=int(os.getenv("PORT", 8000)))
        except Exception as e:
            logger.warning(f"LAN bridge startup failed: {e}")
    yield


app = FastAPI(title="Smart Agriculture AI API", version="1.0.0", lifespan=lifespan)

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

# In production mode, remove permissive subnet regex and enforce explicit origins
_allow_origin_regex = (
    r"^https?://(localhost|127\.0\.0\.1|192\.168\.\d+\.\d+|10\.\d+\.\d+\.\d+|172\.(1[6-9]|2\d|3[0-1])\.\d+\.\d+)(:\d+)?$"
    if _environment == "development"
    else None
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_origin_regex=_allow_origin_regex,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["Authorization", "Content-Type", "Accept", "Origin", "X-Requested-With", "X-Device-Token"],
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
app.include_router(chat.router, prefix="/api/chat", tags=["Maitri Krishi Assistant Chatbot"])

# Multi-Channel MAITTRI Platform Routers
app.include_router(operators.router, prefix="/api/operators", tags=["Authorized Agriculture / Seva Operator"])
app.include_router(farmer_profile.router, prefix="/api/farmer-profile", tags=["Farmer Profile & MAITTRI Farm ID"])
app.include_router(soil_tests.router, prefix="/api/soil-tests", tags=["Soil Test Booking & Lab Reports"])
app.include_router(service_requests.router, prefix="/api/service-requests", tags=["Service Requests"])
app.include_router(documents.router, prefix="/api/documents", tags=["Document Vault"])
app.include_router(farm_brain.router, prefix="/api/farm-brain", tags=["MAITTRI Farm Brain"])
app.include_router(communications.router, prefix="/api/communications", tags=["Multi-Channel Communications (SMS & IVR)"])


# Resilient fallbacks for microcontroller path variations
from .schemas import IoTSensorDataCreate
from .services.iot_service import process_incoming_sensor_data

@app.post("/sensor-data", status_code=200, tags=["IoT Fallback"])
@app.post("/api/sensor-data", status_code=200, tags=["IoT Fallback"])
@app.post("/telemetry", status_code=200, tags=["IoT Fallback"])
def fallback_sensor_data(
    data: IoTSensorDataCreate,
    x_device_token: str = Header(None, alias="X-Device-Token"),
    db: Session = Depends(get_db)
):
    try:
        telemetry = process_incoming_sensor_data(db, data, device_token=x_device_token)
        return {"success": True, "status": "success", "message": "Sensor data received successfully", "data": telemetry}
    except PermissionError as pe:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(pe))
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))

@app.get("/")
def root():
    return {"message": "Smart Agriculture AI API is running"}

@app.get("/health", tags=["System"])
@app.get("/api/health", tags=["System"])
def health(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "status": "unhealthy",
                "environment": _environment,
                "database": "unreachable",
                "error": "Database connection failed"
            }
        )

    return {
        "status": "healthy",
        "environment": _environment,
        "database": db_status,
        "rag": "pgvector",
        "storage": "farmer-vault",
        "version": "1.0.0"
    }
