import uuid
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import text
from ..database import get_db, engine
from ..models import User, Profile
from ..schemas import RegisterRequest, LoginRequest, TokenResponse
from ..security import hash_password, verify_password, create_token
from ..supabase_client import get_supabase_admin_client
from ..deps import get_current_user

router = APIRouter()

@router.post("/register", response_model=TokenResponse)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    email = payload.email.lower().strip()
    role_val = (payload.role or "FARMER").upper()
    if role_val not in ("FARMER", "AUTHORIZED_OPERATOR"):
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
        uid_str = None
        if supabase_admin:
            try:
                from supabase_auth.types import AdminUserAttributes
                attrs = AdminUserAttributes(
                    email=email,
                    password=payload.password,
                    email_confirm=True,
                    user_metadata={
                        "full_name": payload.full_name,
                        "role": role_val,
                        "phone_number": payload.phone_number,
                        "language": payload.language or "hi"
                    }
                )
                res = supabase_admin.auth.admin.create_user(attrs)
                uid_str = str(res.user.id)
            except Exception as e:
                err = str(e)
                if "already registered" in err or "already exists" in err:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Email already registered"
                    )
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to create user in authoritative store: {err}"
                )
        
        if not uid_str:
            uid_str = str(uuid.uuid4())

        profile = db.query(Profile).filter(Profile.id == uid_str).first()
        if not profile:
            profile = Profile(
                id=uid_str,
                role=role_val,
                full_name=payload.full_name,
                phone_number=payload.phone_number,
                preferred_language=payload.language or "hi"
            )
            db.add(profile)
            db.commit()

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
    db.add(user)
    db.commit()
    db.refresh(user)

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
            text("SELECT id, encrypted_password FROM auth.users WHERE lower(email) = :email"),
            {"email": email}
        ).first()

        if row and row.encrypted_password:
            if verify_password(payload.password, row.encrypted_password):
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

    # 2. SQLite / local fallback lookup
    user = db.query(User).filter(User.email == email).first()
    if user and verify_password(payload.password, user.password_hash):
        return {
            "access_token": create_token(user.id),
            "token_type": "bearer",
            "role": getattr(user, "role", "FARMER") or "FARMER",
            "user_id": user.id,
            "email": user.email,
            "full_name": getattr(user, "full_name", None)
        }

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid email or password"
    )


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
