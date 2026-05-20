from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_

from app.database import get_db
from app.models import User, Case, CaseStatus
from app.schemas import CaseCreate, CaseResponse
from app.core.dependencies import get_current_user

router = APIRouter(prefix="/cases", tags=["Cases"])


@router.post("", response_model=CaseResponse, status_code=201)
async def create_case(
    body: CaseCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """사건 생성 (원고가 만들고 invite_token을 피고에게 공유)"""
    from app.models import JudgeStyle
    style = JudgeStyle.SPICY if body.judgeStyle == "spicy" else JudgeStyle.DEFAULT
    case = Case(title=body.title, plaintiff_id=current_user.id, judge_style=style)
    db.add(case)
    await db.flush()
    return case


@router.get("", response_model=list[CaseResponse])
async def list_my_cases(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """내가 원고 또는 피고인 사건 목록"""
    result = await db.execute(
        select(Case).where(
            or_(
                Case.plaintiff_id == current_user.id,
                Case.defendant_id == current_user.id,
            )
        ).order_by(Case.created_at.desc())
    )
    return result.scalars().all()


@router.get("/{case_id}", response_model=CaseResponse)
async def get_case(
    case_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """사건 상세 조회"""
    result = await db.execute(select(Case).where(Case.id == case_id))
    case = result.scalar_one_or_none()

    if not case:
        raise HTTPException(status_code=404, detail="사건을 찾을 수 없습니다")

    # 원고 또는 피고만 조회 가능
    if current_user.id not in [case.plaintiff_id, case.defendant_id]:
        raise HTTPException(status_code=403, detail="접근 권한이 없습니다")

    return case


@router.post("/join/{invite_token}", response_model=CaseResponse)
async def join_case(
    invite_token: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """초대 링크로 피고 입장"""
    result = await db.execute(select(Case).where(Case.invite_token == invite_token))
    case = result.scalar_one_or_none()

    if not case:
        raise HTTPException(status_code=404, detail="유효하지 않은 초대 링크입니다")

    if case.plaintiff_id == current_user.id:
        raise HTTPException(status_code=400, detail="본인이 만든 사건에는 피고로 입장할 수 없습니다")

    if case.defendant_id:
        raise HTTPException(status_code=400, detail="이미 피고가 입장한 사건입니다")

    case.defendant_id = current_user.id
    case.status = CaseStatus.IN_PROGRESS
    await db.flush()
    return case


@router.post("/{case_id}/submit")
async def submit_argument(
    case_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """주장 제출 완료 - 양측 모두 제출 시 판결 트리거"""
    result = await db.execute(select(Case).where(Case.id == case_id))
    case = result.scalar_one_or_none()

    if not case:
        raise HTTPException(status_code=404, detail="사건을 찾을 수 없습니다")

    if case.status != CaseStatus.IN_PROGRESS:
        raise HTTPException(status_code=400, detail="진행 중인 사건이 아닙니다")

    # 원고/피고 제출 상태 업데이트
    if current_user.id == case.plaintiff_id:
        case.plaintiff_submitted = True
    elif current_user.id == case.defendant_id:
        case.defendant_submitted = True
    else:
        raise HTTPException(status_code=403, detail="접근 권한이 없습니다")

    await db.flush()

    # 양측 모두 제출 완료 → 판결 시작
    if case.plaintiff_submitted and case.defendant_submitted:
        from app.langgraph.graph import run_trial
        import asyncio
        asyncio.create_task(run_trial(case_id, db))
        return {"message": "양측 모두 제출 완료! 판결을 시작합니다.", "judging": True}

    return {"message": "제출 완료! 상대방의 제출을 기다리는 중입니다.", "judging": False}
