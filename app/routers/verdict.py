from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models import User, Case, Verdict
from app.schemas import VerdictResponse
from app.core.dependencies import get_current_user

router = APIRouter(prefix="/verdicts", tags=["Verdict"])


@router.get("/{case_id}", response_model=VerdictResponse)
async def get_verdict(
    case_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """판결 결과 조회 (원고/피고만 가능)"""
    # 사건 권한 확인
    result = await db.execute(select(Case).where(Case.id == case_id))
    case = result.scalar_one_or_none()

    if not case:
        raise HTTPException(status_code=404, detail="사건을 찾을 수 없습니다")

    if current_user.id not in [case.plaintiff_id, case.defendant_id]:
        raise HTTPException(status_code=403, detail="접근 권한이 없습니다")

    # 판결 조회
    result = await db.execute(select(Verdict).where(Verdict.case_id == case_id))
    verdict = result.scalar_one_or_none()

    if not verdict:
        raise HTTPException(status_code=404, detail="아직 판결이 나지 않았습니다")

    return verdict


@router.get("/{case_id}/similar")
async def get_similar_cases(
    case_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    현재 판결과 유사한 과거 사건 추천.
    pgvector 코사인 유사도 기반.
    예: '이런 싸움은 보통 피고 잘못이 더 많았어요'
    """
    # 권한 확인
    result = await db.execute(select(Case).where(Case.id == case_id))
    case = result.scalar_one_or_none()

    if not case or current_user.id not in [case.plaintiff_id, case.defendant_id]:
        raise HTTPException(status_code=403, detail="접근 권한이 없습니다")

    # 판결문 조회
    result = await db.execute(select(Verdict).where(Verdict.case_id == case_id))
    verdict = result.scalar_one_or_none()

    if not verdict:
        raise HTTPException(status_code=404, detail="판결이 아직 완료되지 않았습니다")

    # 유사 사건 검색
    from app.services.similarity import find_similar_cases
    similar = await find_similar_cases(
        judgment=verdict.judgment,
        db=db,
        limit=3,
        exclude_case_id=case_id,
    )

    return {
        "similar_cases": similar,
        "message": f"유사한 싸움 {len(similar)}건을 찾았어요" if similar else "아직 유사한 사건이 없어요",
    }
