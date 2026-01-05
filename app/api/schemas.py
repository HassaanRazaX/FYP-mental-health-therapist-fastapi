from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List

class TokenBundle(BaseModel):
    accessToken: str
    refreshToken: str
    expiresIn: int

class UserOut(BaseModel):
    id: str
    name: str
    email: str
    profileImageUrl: Optional[str] = None

class SignupRequest(BaseModel):
    name: str
    email: str
    password: str = Field(min_length=8)
    gender: str
    dateOfBirth: str  # DD/MM/YYYY
    profileImage: Optional[str] = None  # base64 or null

class LoginRequest(BaseModel):
    email: str
    password: str

class AuthResponse(BaseModel):
    token: TokenBundle
    user: UserOut

class RefreshRequest(BaseModel):
    refreshToken: str

class LogoutRequest(BaseModel):
    refreshToken: str

class GoogleOAuthRequest(BaseModel):
    idToken: str

class FirebaseOAuthRequest(BaseModel):
    idToken: str

class ProfileOut(BaseModel):
    id: str
    name: str
    email: str
    gender: str
    dateOfBirth: str  # DD-MM-YYYY
    profileImageUrl: Optional[str] = None

class ProfilePatch(BaseModel):
    name: Optional[str] = None
    dateOfBirth: Optional[str] = None  # DD-MM-YYYY or DD/MM/YYYY

class ChatMessageIn(BaseModel):
    sessionId: Optional[str] = None
    message: str
    disorderHint: Optional[str] = ""  # optional

class ChatSessionOut(BaseModel):
    id: str
    title: str
    createdAt: str

class AssistantMessageOut(BaseModel):
    id: str
    text: str
    createdAt: str
    meta: Optional[Dict[str, Any]] = None

class ChatMessageResponse(BaseModel):
    session: ChatSessionOut
    assistantMessage: AssistantMessageOut

class SessionsPage(BaseModel):
    page: int
    limit: int
    total: int
    items: List[ChatSessionOut]

class SessionDetail(BaseModel):
    session: ChatSessionOut
    messages: List[Dict[str, Any]]

class FeedbackIn(BaseModel):
    sessionId: Optional[str] = None
    rating: int = Field(ge=1, le=5)
    comment: Optional[str] = None
