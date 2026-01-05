from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ...core.db import get_db
from ..deps import get_current_user
from ...models import User, Feedback
from ..schemas import FeedbackIn

router = APIRouter(prefix="/feedback", tags=["feedback"])

@router.post("")
def create_feedback(payload: FeedbackIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    fb = Feedback(user_id=user.id, session_id=payload.sessionId, rating=payload.rating, comment=payload.comment)
    db.add(fb)
    db.commit()
    return {"ok": True}
