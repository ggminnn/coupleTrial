from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import text
from app.core.config import settings

engine = create_async_engine(settings.DATABASE_URL, echo=True)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def init_db():
    """앱 시작 시 실행 - pgvector 확장 활성화 + 테이블 생성"""
    async with engine.begin() as conn:
        # pgvector 확장 활성화 (없으면 생성)
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        # 모든 테이블 자동 생성
        await conn.run_sync(Base.metadata.create_all)


async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
