import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, Boolean, ForeignKey, Text, Integer, UniqueConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .core.db import Base

def _uuid() -> str:
    return str(uuid.uuid4())

class User(Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(200))
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    # For email/password users, password_hash is set.
    # For OAuth users, password_hash is NULL.
    password_hash: Mapped[str | None] = mapped_column(String(300), nullable=True)
    auth_provider: Mapped[str] = mapped_column(String(40), default="password")  # password|google|firebase
    provider_subject: Mapped[str | None] = mapped_column(String(200), nullable=True)  # provider user id
    gender: Mapped[str] = mapped_column(String(20))
    date_of_birth_iso: Mapped[str] = mapped_column(String(10))  # YYYY-MM-DD
    profile_image_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    is_disabled: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    refresh_tokens: Mapped[list["RefreshToken"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    sessions: Mapped[list["ChatSession"]] = relationship(back_populates="user", cascade="all, delete-orphan")

class RefreshToken(Base):
    __tablename__ = "refresh_tokens"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    token_jti: Mapped[str] = mapped_column(String(64), unique=True, index=True)  # hashed jti string
    expires_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    revoked: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user: Mapped["User"] = relationship(back_populates="refresh_tokens")

class ChatSession(Base):
    __tablename__ = "chat_sessions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)

    user: Mapped["User"] = relationship(back_populates="sessions")
    messages: Mapped[list["ChatMessage"]] = relationship(back_populates="session", cascade="all, delete-orphan")
    screening: Mapped["ScreeningSession"] = relationship(back_populates="session", cascade="all, delete-orphan", uselist=False)

class ChatMessage(Base):
    __tablename__ = "chat_messages"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    session_id: Mapped[str] = mapped_column(String(36), ForeignKey("chat_sessions.id", ondelete="CASCADE"), index=True)
    role: Mapped[str] = mapped_column(String(20))  # user/assistant/system
    text: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)

    session: Mapped["ChatSession"] = relationship(back_populates="messages")

class ScreeningSession(Base):
    __tablename__ = "screening_sessions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    session_id: Mapped[str] = mapped_column(String(36), ForeignKey("chat_sessions.id", ondelete="CASCADE"), unique=True, index=True)
    # state machine
    phase: Mapped[str] = mapped_column(String(30), default="INTAKE")  # INTAKE, EXPLORATION, SCREENING, REPORT_READY
    readiness: Mapped[str] = mapped_column(String(20), default="WARMING")  # UNREADY/WARMING/READY
    track: Mapped[str] = mapped_column(String(20), default="RELATIONAL")  # RELATIONAL/CLINICAL
    # session memory
    presenting_concern: Mapped[str | None] = mapped_column(Text, nullable=True)
    subject_type: Mapped[str | None] = mapped_column(String(20), nullable=True)  # self/other/unknown
    age_years: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # hypothesis json
    hypotheses_json: Mapped[str] = mapped_column(Text, default="{}")
    active_disorder_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    # progress markers
    progress_summaries: Mapped[int] = mapped_column(Integer, default=0)
    closure_prompted: Mapped[bool] = mapped_column(Boolean, default=False)
    closure_ack: Mapped[bool] = mapped_column(Boolean, default=False)
    turns: Mapped[int] = mapped_column(Integer, default=0)
    # slots state json
    slots_json: Mapped[str] = mapped_column(Text, default="{}")
    slot_state_json: Mapped[str] = mapped_column(Text, default="{}")  # slot->UNASKED/ASKED/PARTIAL/RESOLVED
    last_intent: Mapped[str | None] = mapped_column(String(80), nullable=True)
    last_question_fingerprint: Mapped[str | None] = mapped_column(String(64), nullable=True)

    session: Mapped["ChatSession"] = relationship(back_populates="screening")

class Feedback(Base):
    __tablename__ = "feedback"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    session_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("chat_sessions.id", ondelete="SET NULL"), nullable=True)
    rating: Mapped[int] = mapped_column(Integer)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

Index("ix_chat_messages_session_created", ChatMessage.session_id, ChatMessage.created_at)
