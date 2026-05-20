import asyncio
import httpx
import certifi
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, and_

from app.database import get_db
from app.models import User, Case, Verdict, CaseStatus
from app.core.dependencies import get_current_user

router = APIRouter(prefix="/stats", tags=["Stats"])

_http_client = httpx.AsyncClient(verify=certifi.where())

FIGHT_CATEGORIES = {
    "연락 문제": "카톡 답장 안함 전화 안 받음 연락 두절 메시지 무시 연락 늦음",
    "약속 파기": "약속 취소 지각 늦음 데이트 계획 변경 약속 어김 바람",
    "감정 표현": "무시 상처 주는 말 감정 무시 공감 부족 냉대 화 폭발",
    "외출·시간": "외출 허락 귀가 시간 친구 만남 개인 시간 남사친 여사친",
    "경제적 갈등": "더치페이 선물 데이트 비용 돈 금전 계산",
}

_category_vecs: dict[str, list[float]] = {}


def _cosine_sim(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = sum(x ** 2 for x in a) ** 0.5
    norm_b = sum(x ** 2 for x in b) ** 0.5
    return dot / (norm_a * norm_b) if norm_a * norm_b > 0 else 0.0


async def _get_category_vecs() -> dict[str, list[float]]:
    if not _category_vecs:
        from langchain_openai import OpenAIEmbeddings
        emb = OpenAIEmbeddings(model="text-embedding-3-small", http_async_client=_http_client)
        results = await asyncio.gather(*[emb.aembed_query(desc) for desc in FIGHT_CATEGORIES.values()])
        for name, vec in zip(FIGHT_CATEGORIES.keys(), results):
            _category_vecs[name] = vec
    return _category_vecs


async def _classify(title: str, judgment: str) -> str:
    from langchain_openai import OpenAIEmbeddings
    emb = OpenAIEmbeddings(model="text-embedding-3-small", http_async_client=_http_client)
    cat_vecs = await _get_category_vecs()
    case_vec = await emb.aembed_query(f"{title}. {judgment[:200]}")
    best, best_score = "기타", -1.0
    for name, vec in cat_vecs.items():
        score = _cosine_sim(case_vec, vec)
        if score > best_score:
            best_score, best = score, name
    return best


@router.get("/{case_id}")
async def get_stats(
    case_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """커플의 전체 재판 통계 반환"""
    result = await db.execute(select(Case).where(Case.id == case_id))
    base_case = result.scalar_one_or_none()

    if not base_case:
        raise HTTPException(status_code=404, detail="사건을 찾을 수 없습니다")
    if current_user.id not in [base_case.plaintiff_id, base_case.defendant_id]:
        raise HTTPException(status_code=403, detail="접근 권한이 없습니다")
    if not base_case.defendant_id:
        raise HTTPException(status_code=400, detail="아직 피고가 없는 사건입니다")

    p_id = base_case.plaintiff_id
    d_id = base_case.defendant_id

    # 두 유저가 함께한 모든 완료된 사건 (양방향)
    result = await db.execute(
        select(Case)
        .where(
            Case.status == CaseStatus.JUDGED,
            or_(
                and_(Case.plaintiff_id == p_id, Case.defendant_id == d_id),
                and_(Case.plaintiff_id == d_id, Case.defendant_id == p_id),
            ),
        )
        .order_by(Case.created_at)
    )
    all_cases = result.scalars().all()

    if not all_cases:
        raise HTTPException(status_code=404, detail="완료된 재판이 없습니다")

    # 유저 정보
    p_res = await db.execute(select(User).where(User.id == p_id))
    plaintiff_user = p_res.scalar_one_or_none()
    d_res = await db.execute(select(User).where(User.id == d_id))
    defendant_user = d_res.scalar_one_or_none()

    # 판결 로드 (병렬)
    verdict_results = await asyncio.gather(*[
        db.execute(select(Verdict).where(Verdict.case_id == c.id))
        for c in all_cases
    ])
    verdicts = [r.scalar_one_or_none() for r in verdict_results]

    case_verdict_pairs = [
        (c, v) for c, v in zip(all_cases, verdicts) if v is not None
    ]

    if not case_verdict_pairs:
        raise HTTPException(status_code=404, detail="판결된 사건이 없습니다")

    # 싸움 유형 분류 (병렬)
    fight_types_list = await asyncio.gather(*[
        _classify(c.title, v.judgment) for c, v in case_verdict_pairs
    ])

    # 통계 집계
    trend = []
    type_counts: dict[str, int] = {}
    total_p, total_d = 0, 0

    for (case, verdict), fight_type in zip(case_verdict_pairs, fight_types_list):
        # p_id 기준으로 비율 정규화 (역할이 뒤바뀐 경우 보정)
        if case.plaintiff_id == p_id:
            p_ratio, d_ratio = verdict.plaintiff_ratio, verdict.defendant_ratio
        else:
            p_ratio, d_ratio = verdict.defendant_ratio, verdict.plaintiff_ratio

        total_p += p_ratio
        total_d += d_ratio

        trend.append({
            "caseId": case.id,
            "title": case.title,
            "date": case.created_at.strftime("%Y-%m-%d"),
            "plaintiffRatio": p_ratio,
            "defendantRatio": d_ratio,
        })
        type_counts[fight_type] = type_counts.get(fight_type, 0) + 1

    count = len(trend)
    fight_types = [
        {"type": k, "count": v}
        for k, v in sorted(type_counts.items(), key=lambda x: -x[1])
    ]

    return {
        "totalCases": count,
        "plaintiffNickname": plaintiff_user.nickname if plaintiff_user else "",
        "defendantNickname": defendant_user.nickname if defendant_user else "",
        "avgPlaintiffRatio": round(total_p / count, 1),
        "avgDefendantRatio": round(total_d / count, 1),
        "trend": trend,
        "fightTypes": fight_types,
    }
