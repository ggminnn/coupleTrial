from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional


# ── Auth ───────────────────────────────────────────────────
class RegisterRequest(BaseModel):
    email: EmailStr
    nickname: str
    password: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: str
    email: str
    nickname: str
    created_at: datetime

    class Config:
        from_attributes = True


# ── Case ───────────────────────────────────────────────────
class CaseCreate(BaseModel):
    title: str
    judgeStyle: str = "default"


class CaseResponse(BaseModel):
    id: str
    title: str
    status: str
    invite_token: str
    plaintiff_id: str
    defendant_id: Optional[str]
    plaintiff_submitted: bool
    defendant_submitted: bool
    judge_style: str = "default"
    created_at: datetime

    class Config:
        from_attributes = True


# ── Message ────────────────────────────────────────────────
class MessageCreate(BaseModel):
    content: str


class MessageResponse(BaseModel):
    id: str
    case_id: str
    role: str
    content: str
    created_at: datetime

    class Config:
        from_attributes = True


# ── Verdict ────────────────────────────────────────────────
class VerdictResponse(BaseModel):
    id: str
    case_id: str
    plaintiff_ratio: int
    defendant_ratio: int
    plaintiff_summary: str
    defendant_summary: str
    judgment: str
    missions: list[str]
    created_at: datetime

    class Config:
        from_attributes = True
