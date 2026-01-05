"""OAuth / third-party identity verification.

Two supported flows:

1) Google Sign-In (client obtains a Google ID token; backend verifies it).
   Endpoint: POST /auth/oauth/google

2) Firebase Auth (recommended): client signs in using Firebase (Google, Apple, etc),
   then sends Firebase ID token; backend verifies it and issues its own JWT.
   Endpoint: POST /auth/oauth/firebase

Why issue our own JWT?
- Keeps backend stateless and independent of the frontend auth provider.
- Enables uniform authorization, refresh tokens, and per-user data ownership.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Optional

from google.auth.transport import requests as grequests
from google.oauth2 import id_token

from ..core.config import settings


@dataclass
class ExternalIdentity:
    provider: str  # "google" | "firebase"
    subject: str
    email: str
    name: Optional[str] = None
    picture: Optional[str] = None


def verify_google_id_token(token: str) -> ExternalIdentity:
    if not settings.GOOGLE_CLIENT_ID:
        raise RuntimeError("GOOGLE_CLIENT_ID is not configured")

    req = grequests.Request()
    payload = id_token.verify_oauth2_token(token, req, audience=settings.GOOGLE_CLIENT_ID)

    sub = payload.get("sub")
    email = payload.get("email")
    if not sub or not email:
        raise ValueError("Invalid Google token payload")
    return ExternalIdentity(
        provider="google",
        subject=sub,
        email=email.lower(),
        name=payload.get("name"),
        picture=payload.get("picture"),
    )


def verify_firebase_id_token(token: str) -> ExternalIdentity:
    """Verify Firebase ID token via firebase-admin if configured.

    This requires FIREBASE_PROJECT_ID and FIREBASE_SERVICE_ACCOUNT_JSON.
    """
    if not settings.FIREBASE_PROJECT_ID or not settings.FIREBASE_SERVICE_ACCOUNT_JSON:
        raise RuntimeError("Firebase verification is not configured")

    import firebase_admin
    from firebase_admin import auth, credentials

    # init once
    if not firebase_admin._apps:
        cred_dict = json.loads(settings.FIREBASE_SERVICE_ACCOUNT_JSON)
        cred = credentials.Certificate(cred_dict)
        firebase_admin.initialize_app(cred, {"projectId": settings.FIREBASE_PROJECT_ID})

    decoded = auth.verify_id_token(token)
    sub = decoded.get("uid")
    email = (decoded.get("email") or "").lower()
    if not sub or not email:
        raise ValueError("Invalid Firebase token payload")
    return ExternalIdentity(
        provider="firebase",
        subject=sub,
        email=email,
        name=decoded.get("name"),
        picture=decoded.get("picture"),
    )
