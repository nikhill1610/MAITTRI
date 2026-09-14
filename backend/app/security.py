from datetime import datetime, timedelta, timezone
from jose import jwt
import os
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, VerificationError, InvalidHashError
import bcrypt

SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-me")
ALGORITHM = "HS256"

# Fail-fast production validation for SECRET_KEY
_env = os.getenv("ENVIRONMENT", "development").lower()
if _env == "production":
    _insecure_defaults = {
        "dev-secret-change-me",
        "change-this-in-production-to-a-secure-random-string",
        "secret",
        "changeme"
    }
    if not SECRET_KEY or SECRET_KEY in _insecure_defaults or len(SECRET_KEY) < 32:
        raise RuntimeError(
            "Production security violation: SECRET_KEY must be set to a cryptographically "
            "secure string with at least 32 characters. Do not use default or weak secrets."
        )

# Modern Argon2id password hasher
_hasher = PasswordHasher()

def hash_password(password: str) -> str:
    """Hash password using Argon2id."""
    return _hasher.hash(password)

def verify_password(password: str, hashed: str) -> bool:
    """
    Verify password against hashed string.
    Supports modern Argon2id hashes, with fallback to legacy bcrypt hashes.
    """
    if not hashed or not password:
        return False

    # Check for Argon2 hash ($argon2i$, $argon2d$, $argon2id$)
    if hashed.startswith("$argon2"):
        try:
            return _hasher.verify(hashed, password)
        except (VerifyMismatchError, VerificationError, InvalidHashError):
            return False

    # Fallback to bcrypt for legacy hashes ($2a$, $2b$, $2y$)
    if hashed.startswith(("$2a$", "$2b$", "$2y$")):
        try:
            return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))
        except Exception:
            return False

    return False

def create_token(user_id, extra_claims: dict = None) -> str:
    if isinstance(user_id, dict):
        payload = dict(user_id)
        if "exp" not in payload:
            payload["exp"] = datetime.now(timezone.utc) + timedelta(days=7)
        if extra_claims:
            payload.update(extra_claims)
        return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

    payload = {
        "sub": str(user_id),
        "exp": datetime.now(timezone.utc) + timedelta(days=7)
    }
    if extra_claims:
        payload.update(extra_claims)
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

create_access_token = create_token
get_password_hash = hash_password

def decode_token(token: str) -> str:
    """
    Cryptographically verifies and decodes token, returning subject identifier (str).
    Raises exception if invalid, expired, forged, or missing subject.
    Never uses unverified claims in runtime authentication.
    """
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    sub = payload.get("sub")
    if not sub:
        raise ValueError("Token missing subject identity.")
    return str(sub)

def decode_token_payload(token: str) -> dict:
    """
    Cryptographically verifies and returns the JWT payload dictionary.
    Raises exception if signature, expiration, or claims are invalid.
    Zero unverified claims allowed in runtime authentication.
    """
    return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
