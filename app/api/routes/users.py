from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.orm import Session
from ...core.db import get_db
from ..deps import get_current_user
from ...models import User
from ..schemas import ProfileOut, ProfilePatch
from ...utils.dates import iso_to_ddmmyyyy, normalize_ddmmyyyy, ddmmyyyy_to_iso
from ...services.image_uploads import upload_profile_image_file

router = APIRouter(prefix="/users", tags=["users"])

@router.get("/me", response_model=ProfileOut)
def me(user: User = Depends(get_current_user)):
    return ProfileOut(
        id=user.id,
        name=user.name,
        email=user.email,
        gender=user.gender,
        dateOfBirth=iso_to_ddmmyyyy(user.date_of_birth_iso),
        profileImageUrl=user.profile_image_url,
    )

@router.patch("/me", response_model=ProfileOut)
def patch_me(payload: ProfilePatch, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if payload.name is not None:
        user.name = payload.name.strip()
    if payload.dateOfBirth is not None:
        # accept DD-MM-YYYY or DD/MM/YYYY
        norm = normalize_ddmmyyyy(payload.dateOfBirth)
        dd, mm, yyyy = norm.split("-")
        user.date_of_birth_iso = f"{yyyy}-{mm}-{dd}"
    db.commit()
    db.refresh(user)
    return ProfileOut(
        id=user.id,
        name=user.name,
        email=user.email,
        gender=user.gender,
        dateOfBirth=iso_to_ddmmyyyy(user.date_of_birth_iso),
        profileImageUrl=user.profile_image_url,
    )

@router.post("/me/avatar")
def upload_avatar(file: UploadFile = File(...), db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=415, detail="Only image uploads supported")
    data = file.file.read()
    user.profile_image_url = upload_profile_image_file(data, filename=file.filename)
    db.commit()
    return {"profileImageUrl": user.profile_image_url}
