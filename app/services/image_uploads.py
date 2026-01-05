"""Image upload helpers.

Production requirement: use Cloudinary (not local disk).

These helpers are used by:
- /auth/signup (optional base64 profile image)
- /users/me/avatar (multipart upload)

If Cloudinary env vars are not set, we raise a clear error.
"""

from __future__ import annotations

import base64
import uuid
from typing import Optional

import cloudinary
import cloudinary.uploader

from ..core.config import settings


def _cloudinary_enabled() -> bool:
    return all([
        settings.CLOUDINARY_CLOUD_NAME,
        settings.CLOUDINARY_API_KEY,
        settings.CLOUDINARY_API_SECRET,
    ])


def _init_cloudinary() -> None:
    if not _cloudinary_enabled():
        raise RuntimeError(
            "Cloudinary is not configured. Set CLOUDINARY_CLOUD_NAME, "
            "CLOUDINARY_API_KEY, CLOUDINARY_API_SECRET."
        )
    cloudinary.config(
        cloud_name=settings.CLOUDINARY_CLOUD_NAME,
        api_key=settings.CLOUDINARY_API_KEY,
        api_secret=settings.CLOUDINARY_API_SECRET,
        secure=True,
    )


def upload_profile_image_base64(b64: str) -> str:
    """Upload a base64 image string to Cloudinary and return the secure URL."""
    _init_cloudinary()

    # Accept raw base64 or data-url
    if b64.strip().lower().startswith("data:") and "," in b64:
        b64 = b64.split(",", 1)[1]
    # Validate base64 (will raise if invalid)
    base64.b64decode(b64)
    data_url = f"data:image/png;base64,{b64}"

    public_id = f"{settings.CLOUDINARY_FOLDER}/avatars/{uuid.uuid4()}"
    res = cloudinary.uploader.upload(
        data_url,
        public_id=public_id,
        overwrite=True,
        resource_type="image",
    )
    return res["secure_url"]


def upload_profile_image_file(file_bytes: bytes, filename: Optional[str] = None) -> str:
    """Upload multipart image bytes to Cloudinary and return the secure URL."""
    _init_cloudinary()
    public_id = f"{settings.CLOUDINARY_FOLDER}/avatars/{uuid.uuid4()}"
    res = cloudinary.uploader.upload(
        file_bytes,
        public_id=public_id,
        overwrite=True,
        resource_type="image",
    )
    return res["secure_url"]
