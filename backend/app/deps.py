from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from .database import get_db
from .models import User
from .security import decode_token

bearer = HTTPBearer()
bearer_optional = HTTPBearer(auto_error=False)

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer),
    db: Session = Depends(get_db)
):
    try:
        user_id = decode_token(credentials.credentials)
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user

def get_optional_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_optional),
    db: Session = Depends(get_db)
):
    if not credentials:
        return None
    try:
        user_id = decode_token(credentials.credentials)
        return db.query(User).filter(User.id == user_id).first()
    except Exception:
        return None

