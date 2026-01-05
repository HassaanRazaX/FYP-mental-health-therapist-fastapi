import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from jose import jwt
from passlib.context import CryptContext
from .config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(password: str, password_hash: str) -> bool:
    return pwd_context.verify(password, password_hash)

def _now() -> datetime:
    return datetime.now(timezone.utc)

def _jti() -> str:
    return secrets.token_urlsafe(32)

def sha256_hex(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()

def create_access_token(user_id: str) -> tuple[str, int]:
    ttl = int(settings.JWT_ACCESS_TTL_SECONDS)
    exp = _now() + timedelta(seconds=ttl)
    payload = {
        "sub": user_id,
        "iss": settings.JWT_ISSUER,
        "aud": settings.JWT_AUDIENCE,
        "iat": int(_now().timestamp()),
        "exp": int(exp.timestamp()),
        "typ": "access",
        "jti": _jti(),
    }
    token = jwt.encode(payload, settings.JWT_SECRET, algorithm="HS256")
    return token, ttl

def create_refresh_token(user_id: str) -> tuple[str, datetime, str]:
    exp = _now() + timedelta(days=int(settings.JWT_REFRESH_TTL_DAYS))
    jti = _jti()
    payload = {
        "sub": user_id,
        "iss": settings.JWT_ISSUER,
        "aud": settings.JWT_AUDIENCE,
        "iat": int(_now().timestamp()),
        "exp": int(exp.timestamp()),
        "typ": "refresh",
        "jti": jti,
    }
    token = jwt.encode(payload, settings.JWT_SECRET, algorithm="HS256")
    return token, exp, jti

def decode_token(token: str) -> dict:
    return jwt.decode(
        token,
        settings.JWT_SECRET,
        algorithms=["HS256"],
        audience=settings.JWT_AUDIENCE,
        issuer=settings.JWT_ISSUER,
        options={"verify_aud": True, "verify_iss": True},
    )
