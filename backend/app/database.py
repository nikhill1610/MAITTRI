"""
MAITRI Smart Agriculture AI Platform — Core Database Engine & Session Management
---------------------------------------------------------------------------------
Supabase PostgreSQL is the authoritative persistent database in production.
SQLite is permitted ONLY for explicit local development (ENVIRONMENT=development).
Zero silent fallback to SQLite in production: connection failures produce clear HTTP 503/500 errors.
"""

import os
import logging
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.exc import OperationalError, DatabaseError
from fastapi import HTTPException, status
from dotenv import load_dotenv

# Ensure environment is loaded from backend/.env
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

logger = logging.getLogger("maitri.database")

ENVIRONMENT = os.getenv("ENVIRONMENT", "production").lower()
DATABASE_URL = os.getenv("DATABASE_URL", "").strip()

# Fallback only when explicitly in development environment
if not DATABASE_URL:
    if ENVIRONMENT == "development":
        DATABASE_URL = "sqlite:///./agri.db"
    else:
        raise RuntimeError(
            "CRITICAL: DATABASE_URL is not configured for production environment. "
            "Supabase PostgreSQL is authoritative in production. Halting startup."
        )

is_sqlite = DATABASE_URL.startswith("sqlite")
is_postgres = DATABASE_URL.startswith(("postgresql://", "postgres://"))

# Strict Production Guard: Zero SQLite fallback in production
if is_sqlite and ENVIRONMENT != "development":
    logger.critical("SQLite configuration rejected in production. Supabase PostgreSQL is authoritative.")
    raise RuntimeError(
        "Invalid database configuration: SQLite is permitted ONLY when ENVIRONMENT=development. "
        "Production deployment requires an authoritative Supabase PostgreSQL DATABASE_URL."
    )

if is_postgres:
    # Supabase PostgreSQL engine with robust pool pre-ping and connection recycling
    engine = create_engine(
        DATABASE_URL,
        pool_pre_ping=True,      # Liveness check on checkout prevents stale connections
        pool_recycle=60,         # Periodically recycle connections for Supavisor session pooler
        pool_size=5,
        max_overflow=5,
        pool_timeout=20,
        connect_args={"connect_timeout": 15}
    )
    logger.info("Connected to authoritative Supabase PostgreSQL database engine.")
elif is_sqlite and ENVIRONMENT == "development":
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False}
    )
    logger.warning("Running with SQLite local development database (ENVIRONMENT=development).")
else:
    raise RuntimeError(f"Unsupported database URL scheme: {DATABASE_URL[:12]}...")

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()


def get_db():
    """
    FastAPI dependency for scoped database sessions.
    Guarantees session rollback and cleanup on error.
    In production, database connection failures raise HTTP 503 with ZERO fallback to SQLite.
    """
    try:
        db = SessionLocal()
    except (OperationalError, DatabaseError) as e:
        logger.error(f"Database session allocation failed: {e.__class__.__name__}")
        if ENVIRONMENT != "development":
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Database service temporarily unavailable. Please retry shortly."
            )
        raise

    try:
        yield db
    except (OperationalError, DatabaseError) as e:
        db.rollback()
        logger.error(f"Database operation failed during transaction: {e.__class__.__name__}")
        if ENVIRONMENT != "development":
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Database error occurred during operation. Transaction rolled back."
            )
        raise
    finally:
        db.close()
