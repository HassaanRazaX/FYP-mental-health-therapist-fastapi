from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from datetime import datetime
import json

from ...core.db import get_db
from ..deps import get_current_user
from ...models import User, ChatSession, ChatMessage, ScreeningSession
from ..schemas import ChatMessageIn, ChatMessageResponse, ChatSessionOut, AssistantMessageOut, ChatSessionOut, SessionsPage, SessionDetail
from ...conversation.orchestrator import handle_turn, build_report, DISCLAIMER
from ...core.config import settings

router = APIRouter(prefix="/chat", tags=["chat"])

def _iso(dt: datetime) -> str:
    return dt.replace(microsecond=0).isoformat() + "Z"

@router.post("/message", response_model=ChatMessageResponse)
async def message(payload: ChatMessageIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    text = payload.message.strip()
    if not text:
        raise HTTPException(status_code=422, detail="message required")

    session: ChatSession | None = None
    if payload.sessionId:
        session = db.query(ChatSession).filter(ChatSession.id == payload.sessionId, ChatSession.user_id == user.id).first()
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
    else:
        session = ChatSession(user_id=user.id, title=text[:80])
        db.add(session)
        db.commit()
        db.refresh(session)
        screening = ScreeningSession(session_id=session.id)
        db.add(screening)
        db.commit()

    # persist user message
    um = ChatMessage(session_id=session.id, role="user", text=text)
    db.add(um)

    # load screening state
    screening = db.query(ScreeningSession).filter(ScreeningSession.session_id == session.id).first()
    if not screening:
        screening = ScreeningSession(session_id=session.id)
        db.add(screening)
        db.commit()
        db.refresh(screening)

    state = {
        "phase": screening.phase,
        "readiness": screening.readiness,
        "track": screening.track,
        "presenting_concern": screening.presenting_concern,
        "subject_type": screening.subject_type,
        "age_years": screening.age_years,
        "hypotheses_json": screening.hypotheses_json,
        "active_disorder_id": screening.active_disorder_id,
        "progress_summaries": screening.progress_summaries,
        "closure_prompted": screening.closure_prompted,
        "closure_ack": screening.closure_ack,
        "turns": screening.turns,
        "slots_json": screening.slots_json,
        "slot_state_json": screening.slot_state_json,
        "last_intent": screening.last_intent,
        "last_question_fingerprint": screening.last_question_fingerprint,
        "domain": None,
    }

    new_state, reply_text, meta = await handle_turn(state, text)

    # persist assistant message
    am = ChatMessage(session_id=session.id, role="assistant", text=reply_text)
    db.add(am)

    # update screening row
    screening.phase = new_state.get("phase", screening.phase)
    screening.readiness = new_state.get("readiness", screening.readiness)
    screening.track = new_state.get("track", screening.track)
    screening.presenting_concern = new_state.get("presenting_concern")
    screening.subject_type = new_state.get("subject_type")
    screening.age_years = new_state.get("age_years")
    screening.hypotheses_json = new_state.get("hypotheses_json", screening.hypotheses_json)
    screening.active_disorder_id = new_state.get("active_disorder_id")
    screening.progress_summaries = int(new_state.get("progress_summaries", screening.progress_summaries))
    screening.closure_prompted = bool(new_state.get("closure_prompted", screening.closure_prompted))
    screening.closure_ack = bool(new_state.get("closure_ack", screening.closure_ack))
    screening.turns = int(new_state.get("turns", screening.turns))
    screening.slots_json = new_state.get("slots_json", screening.slots_json)
    screening.slot_state_json = new_state.get("slot_state_json", screening.slot_state_json)
    screening.last_intent = new_state.get("last_intent", screening.last_intent)
    screening.last_question_fingerprint = new_state.get("last_question_fingerprint", screening.last_question_fingerprint)

    session.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(session)
    db.refresh(am)

    # include meta optionally (dev)
    meta_out = meta if settings.ALLOW_DEV_DEBUG_META else None

    return ChatMessageResponse(
        session=ChatSessionOut(id=session.id, title=session.title, createdAt=_iso(session.created_at)),
        assistantMessage=AssistantMessageOut(id=am.id, text=reply_text, createdAt=_iso(am.created_at), meta=meta_out),
    )

@router.get("/sessions", response_model=SessionsPage)
def list_sessions(page: int = Query(1, ge=1), limit: int = Query(20, ge=1, le=50), db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    q = db.query(ChatSession).filter(ChatSession.user_id == user.id).order_by(ChatSession.updated_at.desc())
    total = q.count()
    items = q.offset((page-1)*limit).limit(limit).all()
    return SessionsPage(
        page=page, limit=limit, total=total,
        items=[ChatSessionOut(id=s.id, title=s.title, createdAt=_iso(s.created_at)) for s in items]
    )

@router.get("/sessions/{session_id}", response_model=SessionDetail)
def session_detail(session_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    s = db.query(ChatSession).filter(ChatSession.id == session_id, ChatSession.user_id == user.id).first()
    if not s:
        raise HTTPException(status_code=404, detail="Session not found")
    msgs = db.query(ChatMessage).filter(ChatMessage.session_id == s.id).order_by(ChatMessage.created_at.asc()).all()
    return SessionDetail(
        session=ChatSessionOut(id=s.id, title=s.title, createdAt=_iso(s.created_at)),
        messages=[{"id": m.id, "role": m.role, "text": m.text, "createdAt": _iso(m.created_at)} for m in msgs]
    )

@router.delete("/sessions/{session_id}")
def delete_session(session_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    s = db.query(ChatSession).filter(ChatSession.id == session_id, ChatSession.user_id == user.id).first()
    if not s:
        return {"ok": True}
    db.delete(s)
    db.commit()
    return {"ok": True}

@router.delete("/sessions")
def delete_all_sessions(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    sessions = db.query(ChatSession).filter(ChatSession.user_id == user.id).all()
    for s in sessions:
        db.delete(s)
    db.commit()
    return {"ok": True}

@router.get("/sessions/{session_id}/report")
def get_report(session_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    s = db.query(ChatSession).filter(ChatSession.id == session_id, ChatSession.user_id == user.id).first()
    if not s:
        raise HTTPException(status_code=404, detail="Session not found")
    screening = db.query(ScreeningSession).filter(ScreeningSession.session_id == s.id).first()
    if not screening:
        raise HTTPException(status_code=404, detail="Screening not found")
    state = {
        "active_disorder_id": screening.active_disorder_id,
        "slots_json": screening.slots_json,
        "hypotheses_json": screening.hypotheses_json,
    }
    return build_report(state)
