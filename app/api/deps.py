from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from ..core.db import get_db
from ..core.security import decode_token
from ..models import User

bearer = HTTPBearer(auto_error=False)

def get_current_user(
    creds: HTTPAuthorizationCredentials = Depends(bearer),
    db: Session = Depends(get_db),
) -> User:
    if creds is None or not creds.credentials:
        raise HTTPException(status_code=401, detail="Missing Authorization Bearer token")
    try:
        payload = decode_token(creds.credentials)
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")
    if payload.get("typ") != "access":
        raise HTTPException(status_code=401, detail="Invalid token type")
    user_id = payload.get("sub")
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    if user.is_disabled:
        raise HTTPException(status_code=403, detail="Account disabled")
    return user
