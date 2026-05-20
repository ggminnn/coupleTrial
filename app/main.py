from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.database import init_db
from app.routers import auth, cases, chat, verdict
from app.routers import trial_ws, stats

import app.models  # noqa
import app.services.similarity  # noqa - VerdictEmbedding을 Base.metadata에 등록


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 앱 시작 시: pgvector 확장 활성화 + 테이블 생성
    await init_db()
    yield


app = FastAPI(
    title="커플 재판소 API",
    description="AI가 커플 싸움을 판결해주는 서비스",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(cases.router)
app.include_router(chat.router)
app.include_router(verdict.router)
app.include_router(trial_ws.router)
app.include_router(stats.router)


@app.get("/")
async def root():
    return {"message": "커플 재판소 API"}
