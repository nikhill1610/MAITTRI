"""
MAITRI Smart Agriculture AI Platform — Security & User Identity Dependencies
-----------------------------------------------------------------------------
Validates user identity against:
1. Supabase Auth JWTs (directly verified via Supabase server-side client)
2. Supabase public.profiles table (authoritative in production)
3. Local backend JWTs / SQLite User table (local development compatibility)
Privileged keys (service_role) are NEVER exposed to client/browser.
"""

import logging
from typing import Optional, Union, Any
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from .database import get_db, engine
from .models import User, Profile, Farm, Farmer
from .security import decode_token, decode_token_payload
from .supabase_client import get_supabase_anon_client

logger = logging.getLogger("maitri.deps")

bearer = HTTPBearer()
bearer_optional = HTTPBearer(auto_error=False)


class AuthenticatedUser:
    """
    Lightweight identity representation conforming to the User / Profile interface.
    Provides attribute access for routes and dependency checks.
    """
    def __init__(
        self,
        id: Any,
        email: str,
        role: str = "FARMER",
        full_name: Optional[str] = None,
        phone_number: Optional[str] = None,
        language: str = "en"
    ):
        self.id = id
        self.email = email
        self.role = role
        self.full_name = full_name
        self.phone_number = phone_number
        self.language = language

    def __repr__(self) -> str:
        return f"<AuthenticatedUser id={self.id} email={self.email} role={self.role}>"

def is_valid_uuid(val: Any) -> bool:
    """
    Checks if a value is a valid UUID string or UUID object.
    Prevents passing non-UUID values into PostgreSQL GUID columns.
    """
    if val is None:
        return False
    try:
        import uuid as _u
        _u.UUID(str(val).strip())
        return True
    except (ValueError, TypeError, AttributeError):
        return False


def get_farmer_for_user(db: Session, user_id: Any) -> Optional[Farmer]:
    """
    Safely retrieves a Farmer record by user_id.
    Ensures that non-UUID / legacy integer user IDs are never passed into
    the GUID-based Farmer.user_id column, avoiding PostgreSQL datatype mismatch errors.
    """
    if not is_valid_uuid(user_id):
        return None
    try:
        return db.query(Farmer).filter(Farmer.user_id == str(user_id)).first()
    except Exception as exc:
        logger.warning("Farmer query by user_id failed: %s", exc)
        db.rollback()
        return None


def is_same_user(uid1: Any, uid2: Any) -> bool:
    """
    Safely checks if two user IDs represent the same user.
    Handles raw equality, string equality, integer equality, and legacy uuid5 mapped values.
    """
    if uid1 is None or uid2 is None:
        return False
    s1, s2 = str(uid1), str(uid2)
    if s1 == s2:
        return True
    try:
        import uuid as _u
        if not s1.isdigit() and s2.isdigit():
            return s1 == str(_u.uuid5(_u.NAMESPACE_OID, s2))
        if not s2.isdigit() and s1.isdigit():
            return s2 == str(_u.uuid5(_u.NAMESPACE_OID, s1))
    except Exception:
        pass
    return False


_ELEVATED_ROLES = frozenset({"AUTHORIZED_OPERATOR", "OPERATOR", "ADMIN"})


def is_elevated_user(user: Any) -> bool:
    """
    Checks if the user has an elevated operational role (AUTHORIZED_OPERATOR, OPERATOR, or ADMIN).
    Defensively defaults missing or invalid roles to non-elevated (False).
    """
    if not user:
        return False
    user_role = (getattr(user, "role", None) or "FARMER").upper()
    return user_role in _ELEVATED_ROLES


def farm_belongs_to_farmer(farm: Any, farmer: Any) -> bool:
    """
    Checks whether a farm record is legitimately associated with the given farmer.
    Validates that:
    1. Both entities exist.
    2. If farm.farmer_id is present, it matches farmer.id (and does not conflict).
    3. If farm.user_id is present and farmer.user_id is present, it matches via is_same_user (and does not conflict).
    4. At least one of the identifiers (farmer_id or user_id) matches.
    """
    if not farm or not farmer:
        return False

    farm_farmer_id = getattr(farm, "farmer_id", None)
    farmer_id = getattr(farmer, "id", None)
    matches_farmer_id = farm_farmer_id is not None and farmer_id is not None and farm_farmer_id == farmer_id
    conflicts_farmer_id = farm_farmer_id is not None and farmer_id is not None and farm_farmer_id != farmer_id

    matches_user_id = False
    conflicts_user_id = False
    farm_user_id = getattr(farm, "user_id", None)
    farmer_user_id = getattr(farmer, "user_id", None)
    if farm_user_id is not None and farmer_user_id is not None:
        if is_same_user(farm_user_id, farmer_user_id):
            matches_user_id = True
        else:
            conflicts_user_id = True

    if conflicts_farmer_id or conflicts_user_id:
        return False

    return matches_farmer_id or matches_user_id


def get_authorized_farm(
    db: Session,
    farm_id: Any,
    user: Optional[Any] = None,
    farmer: Optional[Any] = None,
    detail_not_found: str = "Farm not found",
    detail_forbidden: Optional[str] = None,
    forbidden_status_code: int = status.HTTP_403_FORBIDDEN
) -> Farm:
    """
    Resolves and authorizes access to a Farm by its identifier.

    1. Resolves the requested Farm from the database; raises 404 if not found.
    2. Grants immediate access if the user has an elevated operational role (AUTHORIZED_OPERATOR, OPERATOR, ADMIN).
    3. Verifies ownership:
       - Matches if the farm belongs to the specified farmer entity (farm_belongs_to_farmer).
       - Matches if the farm.user_id matches user.id (is_same_user).
       - If farmer is not passed but farm.farmer_id is present, checks against user's linked Farmer record.
       - Matches if user.farmer_id matches farm.farmer_id.
    4. If not authorized:
       - Raises forbidden_status_code (default 403 FORBIDDEN) if detail_forbidden is provided.
       - Otherwise raises 404 NOT_FOUND with detail_not_found (preserving tenant isolation).
    """
    farm = db.query(Farm).filter(Farm.id == farm_id).first()
    if not farm:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail_not_found)

    if is_elevated_user(user):
        return farm

    # Check ownership via explicit farmer entity
    if farmer is not None and farm_belongs_to_farmer(farm, farmer):
        return farm

    # Check ownership via direct user identity
    user_id = getattr(user, "id", None)
    if user_id is not None and is_same_user(farm.user_id, user_id):
        return farm

    # Check ownership via user's linked farmer record
    if user_id is not None and farm.farmer_id is not None:
        user_farmer_id = getattr(user, "farmer_id", None)
        if user_farmer_id is not None and str(farm.farmer_id) == str(user_farmer_id):
            return farm
        user_farmer = get_farmer_for_user(db, user_id)
        if user_farmer is not None and farm_belongs_to_farmer(farm, user_farmer):
            return farm

    if detail_forbidden:
        raise HTTPException(
            status_code=forbidden_status_code,
            detail=detail_forbidden
        )

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=detail_not_found
    )



def _resolve_user_from_token(token: str, db: Session) -> Any:
    """
    Resolves user from bearer token:
    1. Local JWT decoding (strict signature check via SECRET_KEY).
    2. Fallback to Supabase Auth API verification if anon client is configured
       and local verification fails.
       Never falls back to service_role credentials for client token verification.
    """
    # 1. Cheap local signature check first
    payload = None
    try:
        payload = decode_token_payload(token)
    except Exception:
        payload = None

    # 2. Remote Supabase Auth verification only for tokens that are not local
    if payload is None:
        sb_client = get_supabase_anon_client()
        if sb_client:
            try:
                sb_res = sb_client.auth.get_user(token)
                if sb_res and getattr(sb_res, "user", None):
                    sb_u = sb_res.user
                    profile = db.query(Profile).filter(Profile.id == str(sb_u.id)).first()
                    if profile:
                        return profile
                    user_meta = getattr(sb_u, "user_metadata", None) or {}
                    app_meta = getattr(sb_u, "app_metadata", None) or {}
                    # Do NOT trust user-controlled user_metadata for role authorization.
                    # Only use server-controlled app_metadata or default to FARMER.
                    trusted_role = (app_meta.get("role") or "FARMER").upper()
                    return AuthenticatedUser(
                        id=str(sb_u.id),
                        email=getattr(sb_u, "email", "") or "",
                        role=trusted_role,
                        full_name=user_meta.get("full_name"),
                        phone_number=user_meta.get("phone_number"),
                        language=user_meta.get("language", "en")
                    )
            except Exception as exc:
                logger.debug("Supabase token verification failed: %s", exc)

    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired authentication token."
        )

    sub = str(payload.get("sub", ""))
    if not sub:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing subject identity."
        )

    # Check local SQLite / PostgreSQL User table if sub is numeric
    if sub.isdigit():
        user = db.query(User).filter(User.id == int(sub)).first()
        if user:
            return user

    # Check public.profiles by UUID
    try:
        import uuid as _uuid_mod
        _uuid_mod.UUID(sub)
        profile = db.query(Profile).filter(Profile.id == sub).first()
        if profile:
            return profile
    except (ValueError, AttributeError):
        pass

    # Check authoritative Supabase Auth by exact sub (UUID) if running PostgreSQL
    if engine.name == "postgresql":
        row = None
        try:
            import uuid as _uuid_mod
            _uuid_mod.UUID(sub)
            row = db.execute(
                text("SELECT id, email, raw_user_meta_data, raw_app_meta_data FROM auth.users WHERE id = :sub"),
                {"sub": sub}
            ).first()
        except (ValueError, AttributeError):
            pass
        except SQLAlchemyError as exc:
            logger.warning("auth.users lookup failed: %s", exc)
            db.rollback()

        if row:
            uid_str = str(row.id)
            profile = db.query(Profile).filter(Profile.id == uid_str).first()
            if profile:
                return profile
            user_meta = row.raw_user_meta_data if isinstance(row.raw_user_meta_data, dict) else {}
            app_meta = getattr(row, "raw_app_meta_data", None)
            if not isinstance(app_meta, dict):
                app_meta = {}
            # Do NOT trust user-controlled raw_user_meta_data for role
            trusted_role = (app_meta.get("role") or "FARMER").upper()
            return AuthenticatedUser(
                id=uid_str,
                email=row.email,
                role=trusted_role,
                full_name=user_meta.get("full_name"),
                phone_number=user_meta.get("phone_number"),
                language=user_meta.get("language", "hi")
            )

    # Check User table strictly by exact sub if sub is an email string
    if "@" in sub:
        user = db.query(User).filter(User.email == sub).first()
        if user:
            return user

    # If sub represents an existing profile or user registered via Supabase Auth
    # Check if a user with sub as string exists in Profile table
    profile = db.query(Profile).filter(Profile.id == sub).first()
    if profile:
        return profile

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="User identity not found in authoritative database."
    )


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer),
    db: Session = Depends(get_db)
) -> Any:
    return _resolve_user_from_token(credentials.credentials, db)


def get_optional_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_optional),
    db: Session = Depends(get_db)
) -> Optional[Any]:
    if not credentials or not credentials.credentials:
        return None
    try:
        return _resolve_user_from_token(credentials.credentials, db)
    except Exception:
        return None


def require_operator(user: Any = Depends(get_current_user)) -> Any:
    """
    Enforces that the current authenticated user has an elevated operator/admin role.
    """
    if not is_elevated_user(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access restricted to Authorized Agriculture / Seva Operators."
        )
    return user


def require_farmer_or_operator(user: Any = Depends(get_current_user)) -> Any:
    """
    Allows access for verified farmers, authorized seva operators, and administrators.
    Rejects unauthorized roles with 403 Forbidden.
    """
    user_role = (getattr(user, "role", None) or "FARMER").upper()
    if user_role != "FARMER" and not is_elevated_user(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access restricted to registered Farmers or Authorized Operators."
        )
    return user


def require_admin(user: Any = Depends(get_current_user)) -> Any:
    """
    Enforces that the current authenticated user has the ADMIN role.
    """
    user_role = (getattr(user, "role", None) or "").upper()
    if user_role != "ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrative privileges required."
        )
    return user


