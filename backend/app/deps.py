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
from .database import get_db, engine
from .models import User, Profile
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


def _resolve_user_from_token(token: str, db: Session) -> Any:
    """
    Resolves user from bearer token:
    1. Attempts Supabase Auth API verification if anon client is configured.
       Never falls back to service_role credentials for client token verification.
    2. Local JWT decoding (strict signature check via SECRET_KEY).
    """
    # 1. Attempt Supabase Auth verification via public anon client ONLY
    sb_client = get_supabase_anon_client()
    if sb_client:
        try:
            sb_res = sb_client.auth.get_user(token)
            if sb_res and getattr(sb_res, "user", None):
                sb_u = sb_res.user
                profile = db.query(Profile).filter(Profile.id == str(sb_u.id)).first()
                if profile:
                    return profile
                meta = getattr(sb_u, "user_metadata", None) or {}
                return AuthenticatedUser(
                    id=str(sb_u.id),
                    email=getattr(sb_u, "email", "") or "",
                    role=meta.get("role", "FARMER"),
                    full_name=meta.get("full_name"),
                    phone_number=meta.get("phone_number"),
                    language=meta.get("language", "en")
                )
        except Exception:
            pass

    # 2. Local JWT decoding (strict signature check via SECRET_KEY)
    try:
        payload = decode_token_payload(token)
        sub = str(payload.get("sub", ""))
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired authentication token."
        )

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

    # Check authoritative Supabase Auth by sub (UUID) or email if running PostgreSQL
    email = payload.get("email") or (sub if "@" in sub else None)
    if engine.name == "postgresql":
        row = None
        try:
            import uuid as _uuid_mod
            _uuid_mod.UUID(sub)
            row = db.execute(
                text("SELECT id, email, raw_user_meta_data FROM auth.users WHERE id = :sub"),
                {"sub": sub}
            ).first()
        except (ValueError, AttributeError):
            pass

        if not row and email:
            row = db.execute(
                text("SELECT id, email, raw_user_meta_data FROM auth.users WHERE lower(email) = :email"),
                {"email": email.lower()}
            ).first()

        if row:
            uid_str = str(row.id)
            profile = db.query(Profile).filter(Profile.id == uid_str).first()
            if profile:
                profile.email = row.email
                return profile
            meta = row.raw_user_meta_data if isinstance(row.raw_user_meta_data, dict) else {}
            return AuthenticatedUser(
                id=uid_str,
                email=row.email,
                role=meta.get("role", "FARMER"),
                full_name=meta.get("full_name"),
                phone_number=meta.get("phone_number"),
                language=meta.get("language", "hi")
            )

    # Check User table by email if available
    if email:
        user = db.query(User).filter(User.email == email).first()
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
    Enforces that the current authenticated user has the AUTHORIZED_OPERATOR role.
    """
    user_role = (getattr(user, "role", None) or "FARMER").upper()
    if user_role not in ("AUTHORIZED_OPERATOR", "OPERATOR", "ADMIN"):
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
    if user_role not in ("FARMER", "AUTHORIZED_OPERATOR", "OPERATOR", "ADMIN"):
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


