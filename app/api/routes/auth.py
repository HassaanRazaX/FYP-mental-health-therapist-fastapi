from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime
from ...core.db import get_db
from ...core.security import (
    hash_password, verify_password,
    create_access_token, create_refresh_token, decode_token, sha256_hex
)
from ...models import User, RefreshToken
from ..schemas import (
    SignupRequest, LoginRequest, AuthResponse, TokenBundle, UserOut,
    RefreshRequest, LogoutRequest, GoogleOAuthRequest, FirebaseOAuthRequest,
)
from ...services.image_uploads import upload_profile_image_base64
from ...services.oauth import verify_google_id_token, verify_firebase_id_token
from ...utils.dates import ddmmyyyy_to_iso, iso_to_ddmmyyyy

router = APIRouter(prefix="/auth", tags=["auth"])

GENDER_ENUM = {"Male","Female","Other"}


def _issue_tokens(db: Session, user: User) -> AuthResponse:
    access, ttl = create_access_token(user.id)
    refresh, exp, jti = create_refresh_token(user.id)
    db.add(RefreshToken(user_id=user.id, token_jti=sha256_hex(jti), expires_at=exp))
    db.commit()
    return AuthResponse(
        token=TokenBundle(accessToken=access, refreshToken=refresh, expiresIn=ttl),
        user=UserOut(id=user.id, name=user.name, email=user.email, profileImageUrl=user.profile_image_url),
    )

@router.post("/signup", response_model=AuthResponse)
def signup(req: SignupRequest, db: Session = Depends(get_db)):
    if req.gender not in GENDER_ENUM:
        raise HTTPException(status_code=422, detail="Invalid gender")
    if db.query(User).filter(User.email == req.email.lower()).first():
        raise HTTPException(status_code=409, detail="Email already exists")
    dob_iso = ddmmyyyy_to_iso(req.dateOfBirth)
    profile_url = None
    if req.profileImage:
        profile_url = upload_profile_image_base64(req.profileImage)

    user = User(
        name=req.name.strip(),
        email=req.email.lower().strip(),
        password_hash=hash_password(req.password),
        gender=req.gender,
        date_of_birth_iso=dob_iso,
        profile_image_url=profile_url,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    return _issue_tokens(db, user)

@router.post("/login", response_model=AuthResponse)
def login(req: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == req.email.lower().strip()).first()
    if not user:
        raise HTTPException(status_code=404, detail="Account not found")
    if user.is_disabled:
        raise HTTPException(status_code=403, detail="Account disabled")
    if not user.password_hash:
        raise HTTPException(status_code=401, detail="Password login not available for this account")
    if not verify_password(req.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    return _issue_tokens(db, user)


def _upsert_oauth_user(db: Session, provider: str, subject: str, email: str, name: str | None, picture: str | None) -> User:
    user = db.query(User).filter(User.email == email).first()
    if user:
        # Link provider (by email) if not already linked
        user.auth_provider = provider
        user.provider_subject = subject
        if picture and not user.profile_image_url:
            user.profile_image_url = picture
        if name and user.name.strip() == "":
            user.name = name
        db.commit()
        db.refresh(user)
        return user

    # New OAuth user; minimal required fields
    user = User(
        name=name or email.split("@")[0],
        email=email,
        password_hash=None,
        auth_provider=provider,
        provider_subject=subject,
        gender="Other",
        date_of_birth_iso="1970-01-01",  # unknown; can be updated later in /users/me
        profile_image_url=picture,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/oauth/google", response_model=AuthResponse)
def oauth_google(req: GoogleOAuthRequest, db: Session = Depends(get_db)):
    """Exchange a Google ID token for our JWT.

Flutter typically obtains the Google ID token via google_sign_in.
"""
    try:
        ident = verify_google_id_token(req.idToken)
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Invalid Google token: {e}")

    user = _upsert_oauth_user(db, ident.provider, ident.subject, ident.email, ident.name, ident.picture)
    if user.is_disabled:
        raise HTTPException(status_code=403, detail="Account disabled")
    return _issue_tokens(db, user)


@router.post("/oauth/firebase", response_model=AuthResponse)
def oauth_firebase(req: FirebaseOAuthRequest, db: Session = Depends(get_db)):
    """Exchange a Firebase ID token for our JWT.

Recommended setup: use Firebase Auth on Flutter for Google sign-in.
"""
    try:
        ident = verify_firebase_id_token(req.idToken)
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Invalid Firebase token: {e}")

    user = _upsert_oauth_user(db, ident.provider, ident.subject, ident.email, ident.name, ident.picture)
    if user.is_disabled:
        raise HTTPException(status_code=403, detail="Account disabled")
    return _issue_tokens(db, user)

@router.post("/refresh", response_model=AuthResponse)
def refresh(req: RefreshRequest, db: Session = Depends(get_db)):
    try:
        payload = decode_token(req.refreshToken)
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    if payload.get("typ") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid token type")
    user_id = payload.get("sub")
    jti = payload.get("jti")
    if not user_id or not jti:
        raise HTTPException(status_code=401, detail="Invalid refresh token payload")

    token_row = db.query(RefreshToken).filter(RefreshToken.token_jti == sha256_hex(jti)).first()
    if not token_row or token_row.revoked:
        raise HTTPException(status_code=401, detail="Refresh token revoked")
    if token_row.expires_at < datetime.utcnow():
        raise HTTPException(status_code=401, detail="Refresh token expired")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    if user.is_disabled:
        raise HTTPException(status_code=403, detail="Account disabled")

    # rotate refresh token
    token_row.revoked = True
    access, ttl = create_access_token(user.id)
    refresh2, exp2, jti2 = create_refresh_token(user.id)
    db.add(RefreshToken(user_id=user.id, token_jti=sha256_hex(jti2), expires_at=exp2, revoked=False))
    db.commit()

    return AuthResponse(
        token=TokenBundle(accessToken=access, refreshToken=refresh2, expiresIn=ttl),
        user=UserOut(id=user.id, name=user.name, email=user.email, profileImageUrl=user.profile_image_url),
    )

@router.post("/logout")
def logout(req: LogoutRequest, db: Session = Depends(get_db)):
    # idempotent revoke
    try:
        payload = decode_token(req.refreshToken)
    except Exception:
        return {"ok": True}
    if payload.get("typ") != "refresh":
        return {"ok": True}
    jti = payload.get("jti")
    if not jti:
        return {"ok": True}
    row = db.query(RefreshToken).filter(RefreshToken.token_jti == sha256_hex(jti)).first()
    if row:
        row.revoked = True
        db.commit()
    return {"ok": True}
