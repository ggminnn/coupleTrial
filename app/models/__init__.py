import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, ForeignKey, Integer, Text, JSON, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base
import enum


# ── Enum 정의 ──────────────────────────────────────────────
class CaseStatus(str, enum.Enum):
    WAITING = "waiting"        # 피고 입장 대기
    IN_PROGRESS = "in_progress"  # 양측 주장 입력 중
    JUDGED = "judged"          # 판결 완료


class Role(str, enum.Enum):
    PLAINTIFF = "plaintiff"    # 원고
    DEFENDANT = "defendant"    # 피고


class JudgeStyle(str, enum.Enum):
    DEFAULT = "default"        # 기본 판사 - 공정하고 차분한 톤
    SPICY = "spicy"            # 매운맛 판사 - 직설적이고 독설 톤


# ── User ───────────────────────────────────────────────────
class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    email: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    nickname: Mapped[str] = mapped_column(String, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    cases_as_plaintiff = relationship("Case", foreign_keys="Case.plaintiff_id", back_populates="plaintiff")
    cases_as_defendant = relationship("Case", foreign_keys="Case.defendant_id", back_populates="defendant")


# ── Case ───────────────────────────────────────────────────
class Case(Base):
    __tablename__ = "cases"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    title: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[CaseStatus] = mapped_column(Enum(CaseStatus), default=CaseStatus.WAITING)

    plaintiff_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    defendant_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)

    plaintiff_submitted: Mapped[bool] = mapped_column(default=False)  # 원고 제출 여부
    defendant_submitted: Mapped[bool] = mapped_column(default=False)  # 피고 제출 여부

    judge_style: Mapped[JudgeStyle] = mapped_column(Enum(JudgeStyle), default=JudgeStyle.DEFAULT, nullable=False)

    invite_token: Mapped[str] = mapped_column(String, unique=True, default=lambda: str(uuid.uuid4()))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    plaintiff = relationship("User", foreign_keys=[plaintiff_id], back_populates="cases_as_plaintiff")
    defendant = relationship("User", foreign_keys=[defendant_id], back_populates="cases_as_defendant")
    messages = relationship("Message", back_populates="case", cascade="all, delete")
    verdict = relationship("Verdict", back_populates="case", uselist=False, cascade="all, delete")


# ── Message ────────────────────────────────────────────────
class Message(Base):
    __tablename__ = "messages"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    case_id: Mapped[str] = mapped_column(ForeignKey("cases.id"), nullable=False)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    role: Mapped[Role] = mapped_column(Enum(Role), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    case = relationship("Case", back_populates="messages")


# ── Verdict ────────────────────────────────────────────────
class Verdict(Base):
    __tablename__ = "verdicts"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    case_id: Mapped[str] = mapped_column(ForeignKey("cases.id"), unique=True, nullable=False)

    plaintiff_ratio: Mapped[int] = mapped_column(Integer)   # 원고 잘못 비율 0~100
    defendant_ratio: Mapped[int] = mapped_column(Integer)   # 피고 잘못 비율 0~100

    plaintiff_summary: Mapped[str] = mapped_column(Text)    # 원고 주장 요약
    defendant_summary: Mapped[str] = mapped_column(Text)    # 피고 주장 요약
    judgment: Mapped[str] = mapped_column(Text)             # 판결문
    missions: Mapped[list] = mapped_column(JSON)            # 화해미션 목록

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    case = relationship("Case", back_populates="verdict")
