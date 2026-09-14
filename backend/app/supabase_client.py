"""
MAITRI Smart Agriculture AI Platform — Supabase Backend Client
---------------------------------------------------------------
Provides server-side Supabase client configuration.
All privileged credentials (e.g. SUPABASE_SERVICE_ROLE_KEY) remain strictly
server-side and are NEVER exposed to client/browser applications.
"""

import os
import logging
from typing import Optional
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

logger = logging.getLogger("maitri.supabase_client")

_admin_client = None
_anon_client = None


def get_supabase_url() -> str:
    """
    Extracts or derives the Supabase Project URL.
    Prefers explicit SUPABASE_URL; falls back to parsing project ref from DATABASE_URL.
    """
    url = os.getenv("SUPABASE_URL", "").strip()
    if url:
        return url.rstrip("/")
    db_url = os.getenv("DATABASE_URL", "")
    if "postgres." in db_url and "@" in db_url:
        try:
            ref = db_url.split("postgres.", 1)[1].split(":", 1)[0]
            return f"https://{ref}.supabase.co"
        except Exception:
            pass
    return ""


def get_supabase_admin_client():
    """
    Returns the server-side Supabase Admin client with service_role privileges.
    Used for backend administrative tasks (e.g. Auth Admin user migration).
    NEVER exposed to frontend applications.
    """
    global _admin_client
    if _admin_client is not None:
        return _admin_client

    url = get_supabase_url()
    service_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()
    if not url or not service_key:
        logger.debug("SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY not configured. Admin client initialized on-demand when credentials are provided.")
        return None

    try:
        from supabase import create_client
        _admin_client = create_client(url, service_key)
        return _admin_client
    except Exception as e:
        logger.error(f"Failed to initialize Supabase admin client: {e}")
        return None


def get_supabase_anon_client():
    """
    Returns standard Supabase client with public anon key.
    Never falls back to SUPABASE_SERVICE_ROLE_KEY.
    """
    global _anon_client
    if _anon_client is not None:
        return _anon_client

    url = get_supabase_url()
    anon_key = os.getenv("SUPABASE_ANON_KEY", "").strip()
    if not url or not anon_key:
        logger.debug("SUPABASE_URL or SUPABASE_ANON_KEY not configured. Anon client unavailable.")
        return None

    try:
        from supabase import create_client
        _anon_client = create_client(url, anon_key)
        return _anon_client
    except Exception as e:
        logger.error(f"Failed to initialize Supabase anon client: {e}")
        return None
