from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models import User
from app.schemas import RegisterRequest, LoginRequest, TokenResponse, UserResponse
from app.core.security import hash_password, verify_password, create_access_token
from app.core.dependencies import get_current_user

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/register", response_model=UserResponse, status_code=201)
async def register(body: RegisterRequest, db: AsyncSession = Depends(get_db)):
    # 이메일 중복 체크
    result = await db.execute(select(User).where(User.email == body.email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="이미 사용 중인 이메일입니다")

    user = User(
        email=body.email,
        nickname=body.nickname,
        hashed_password=hash_password(body.password),
    )
    db.add(user)
    await db.flush()
    return user


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()

    if not user or not verify_password(body.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="이메일 또는 비밀번호가 올바르지 않습니다")

    token = create_access_token({"sub": user.id})
    return {"access_token": token}


@router.get("/me", response_model=UserResponse)
async def me(current_user: User = Depends(get_current_user)):
    return current_user
