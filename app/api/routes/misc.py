from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ...core.config import settings
from ...core.db import get_db

router = APIRouter(tags=["misc"])

@router.get("/health")
def health():
    return {"ok": True}

@router.get("/version")
def version():
    return {"version": settings.API_VERSION}

@router.get("/config/app")
def app_config():
    return {"chatEnabled": True, "screeningEnabled": True}
