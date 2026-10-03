import uuid
import logging
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from ..database import get_db, engine
from ..models import User, Profile
from ..schemas import RegisterRequest, LoginRequest, TokenResponse
from ..security import hash_password, verify_password, create_token
from ..supabase_client import get_supabase_admin_client
from ..deps import get_current_user

logger = logging.getLogger("maitri.auth")

router = APIRouter()

@router.post("/register", response_model=TokenResponse)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    email = payload.email.lower().strip()
    # Public registration MUST always create a FARMER account.
    # Elevated roles (AUTHORIZED_OPERATOR, OPERATOR, ADMIN) can only be assigned via admin/server flow.
    role_val = "FARMER"

    if engine.name == "postgresql":
        # Check existing in auth.users
        existing = db.execute(
            text("SELECT id FROM auth.users WHERE lower(email) = :email"),
            {"email": email}
        ).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )

        supabase_admin = get_supabase_admin_client()
        if not supabase_admin:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Authoritative authentication service is currently unavailable."
            )

        uid_str = None
        try:
            from supabase_auth.types import AdminUserAttributes
            attrs = AdminUserAttributes(
                email=email,
                password=payload.password,
                email_confirm=True,
                user_metadata={
                    "full_name": payload.full_name,
                    "role": "FARMER",
                    "phone_number": payload.phone_number,
                    "language": payload.language or "hi"
                }
            )
            res = supabase_admin.auth.admin.create_user(attrs)
            if not res or not res.user or not res.user.id:
                logger.error(
                    "Supabase create_user returned no user object. "
                    "exc_type=NullUserResponse stage=supabase_create_user"
                )
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to register user in authoritative store."
                )
            uid_str = str(res.user.id)
        except HTTPException:
            raise
        except Exception as e:
            exc_type = type(e).__name__
            status_val = getattr(e, "status", getattr(e, "status_code", "None"))
            err_code = getattr(e, "code", None)
            raw_msg = getattr(e, "message", None) or str(e) or ""
            safe_msg = str(raw_msg).replace("\r", " ").replace("\n", " ").strip()
            if payload.password and payload.password in safe_msg:
                safe_msg = safe_msg.replace(payload.password, "[REDACTED]")
            if payload.email and payload.email in safe_msg:
                safe_msg = safe_msg.replace(payload.email, "[REDACTED]")
            if err_code and str(err_code) not in safe_msg:
                safe_msg = f"[{err_code}] {safe_msg}"
            safe_msg = safe_msg[:200]

            err = safe_msg.lower()
            if "already registered" in err or "already exists" in err:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Email already registered"
                )
            # In development/test mode, fallback to SQL insert only if external Supabase URL is mock/unreachable
            # AND explicitly opted in via ALLOW_LOCAL_AUTH_INSERT=true
            import os
            is_dev = os.getenv("ENVIRONMENT", "production").lower() in (
                "development",
                "test",
            )
            allow_local_insert = os.getenv("ALLOW_LOCAL_AUTH_INSERT", "false").lower() in (
                "true",
                "1",
                "yes",
            )
            if is_dev and allow_local_insert:
                uid_str = str(uuid.uuid4())
                pwd_hash = hash_password(payload.password)
                try:
                    db.execute(text("""
                        INSERT INTO auth.users (id, aud, role, email, encrypted_password, email_confirmed_at, created_at, updated_at)
                        VALUES (:uid, 'authenticated', 'authenticated', :email, :pwd, now(), now(), now())
                        ON CONFLICT (id) DO NOTHING;
                    """), {"uid": uid_str, "email": email, "pwd": pwd_hash})
                    db.commit()
                except IntegrityError:
                    db.rollback()
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Email already registered"
                    )
            else:
                logger.error(
                    "Supabase create_user failed. exc_type=%s status=%s message=%s stage=supabase_create_user",
                    exc_type,
                    status_val,
                    safe_msg,
                )
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to register user in authoritative store."
                )

        if not uid_str:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Failed to obtain authoritative user identifier from auth service."
            )

        profile = db.query(Profile).filter(Profile.id == uid_str).first()
        if not profile:
            profile = Profile(
                id=uid_str,
                role=role_val,
                full_name=payload.full_name,
                phone_number=payload.phone_number,
                preferred_language=payload.language or "hi"
            )
            try:
                db.add(profile)
                db.commit()
            except IntegrityError:
                db.rollback()
                profile = db.query(Profile).filter(Profile.id == uid_str).first()
                if not profile:
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail="Failed to create user profile."
                    )

        return {
            "access_token": create_token(uid_str),
            "token_type": "bearer",
            "role": role_val,
            "user_id": uid_str,
            "email": email,
            "full_name": payload.full_name
        }

    # SQLite development-only fallback
    existing = db.query(User).filter(User.email == email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    user = User(
        email=email,
        password_hash=hash_password(payload.password),
        role=role_val,
        full_name=payload.full_name,
        phone_number=payload.phone_number,
        language=payload.language
    )
    try:
        db.add(user)
        db.commit()
        db.refresh(user)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    return {
        "access_token": create_token(user.id),
        "token_type": "bearer",
        "role": getattr(user, "role", "FARMER"),
        "user_id": user.id,
        "email": user.email,
        "full_name": getattr(user, "full_name", None)
    }

@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    email = payload.email.lower().strip()

    if engine.name == "postgresql":
        # 1. Authoritative Supabase Auth lookup
        row = db.execute(
            text("SELECT id, encrypted_password, banned_until, deleted_at, email_confirmed_at FROM auth.users WHERE lower(email) = :email"),
            {"email": email}
        ).first()

        if not row:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )

        # 2. Verify password FIRST — prevents account-state info leakage
        if not row.encrypted_password or not verify_password(payload.password, row.encrypted_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )

        from datetime import datetime, timezone
        now = datetime.now(timezone.utc)

        # 3. Account-status checks (only after successful password verification)
        # Check deleted status
        if getattr(row, "deleted_at", None) is not None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account has been deactivated or deleted."
            )

        # Check banned status
        banned_until = getattr(row, "banned_until", None)
        if banned_until is not None:
            if isinstance(banned_until, datetime):
                if banned_until.tzinfo is None:
                    banned_until = banned_until.replace(tzinfo=timezone.utc)
                if banned_until > now:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Account has been temporarily suspended."
                    )
            else:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Account has been suspended."
                )

        # Check email confirmation if required
        import os
        if os.getenv("REQUIRE_EMAIL_CONFIRMATION", "false").lower() in ("true", "1"):
            if getattr(row, "email_confirmed_at", None) is None:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Email address has not been confirmed."
                )

        # 4. Authenticated — issue token
        uid_str = str(row.id)
        profile = db.query(Profile).filter(Profile.id == uid_str).first()
        role_val = getattr(profile, "role", "FARMER") if profile else "FARMER"
        name_val = getattr(profile, "full_name", None) if profile else None
        return {
            "access_token": create_token(uid_str),
            "token_type": "bearer",
            "role": role_val or "FARMER",
            "user_id": uid_str,
            "email": email,
            "full_name": name_val
        }

    # SQLite development-only fallback
    user = db.query(User).filter(User.email == email).first()
    if not user or not user.password_hash or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

    return {
        "access_token": create_token(user.id),
        "token_type": "bearer",
        "role": getattr(user, "role", "FARMER") or "FARMER",
        "user_id": user.id,
        "email": user.email,
        "full_name": getattr(user, "full_name", None)
    }


@router.get("/me")
def get_current_user_profile(user: Any = Depends(get_current_user)):
    """Returns current authenticated user identity and profile."""
    return {
        "id": getattr(user, "id", None),
        "email": getattr(user, "email", None),
        "role": getattr(user, "role", "FARMER"),
        "full_name": getattr(user, "full_name", None),
        "phone_number": getattr(user, "phone_number", None),
        "language": getattr(user, "language", getattr(user, "preferred_language", "hi"))
    }
