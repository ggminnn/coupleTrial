from langchain_openai import OpenAIEmbeddings
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from pgvector.sqlalchemy import Vector
from sqlalchemy import Column, String
from app.database import Base
from app.models import Verdict, Case

embeddings = OpenAIEmbeddings(model="text-embedding-3-small")


# ── 판결 임베딩 모델 ────────────────────────────────────────
class VerdictEmbedding(Base):
    """판결문의 벡터 임베딩을 저장하는 테이블"""
    __tablename__ = "verdict_embeddings"

    case_id = Column(String, primary_key=True)
    embedding = Column(Vector(1536))   # text-embedding-3-small 차원


# ── 임베딩 저장 ─────────────────────────────────────────────
async def save_verdict_embedding(case_id: str, judgment: str, db: AsyncSession):
    """
    판결 완료 후 판결문을 벡터로 변환해서 저장.
    유사 사건 추천에 사용됨.
    """
    vector = await embeddings.aembed_query(judgment)

    existing = await db.execute(
        select(VerdictEmbedding).where(VerdictEmbedding.case_id == case_id)
    )
    if existing.scalar_one_or_none():
        return  # 이미 저장됨

    db.add(VerdictEmbedding(case_id=case_id, embedding=vector))
    await db.flush()


# ── 유사 사건 검색 ──────────────────────────────────────────
async def find_similar_cases(
    judgment: str,
    db: AsyncSession,
    limit: int = 3,
    exclude_case_id: str = None,
) -> list[dict]:
    """
    현재 판결문과 가장 유사한 과거 사건 추천.
    코사인 유사도 기반 (pgvector의 <=> 연산자 사용)

    면접 포인트:
    - OpenAI Embedding으로 판결문을 벡터화
    - pgvector로 코사인 유사도 검색
    - "이런 싸움은 보통 피고 잘못이 더 많았어요" 형태로 UX 제공
    """
    query_vector = await embeddings.aembed_query(judgment)

    # pgvector 코사인 유사도 검색 (1 - 거리 = 유사도)
    sql = text("""
        SELECT
            ve.case_id,
            1 - (ve.embedding <=> CAST(:query_vector AS vector)) AS similarity
        FROM verdict_embeddings ve
        WHERE (CAST(:exclude_case_id AS VARCHAR) IS NULL OR ve.case_id != CAST(:exclude_case_id AS VARCHAR))
        ORDER BY ve.embedding <=> CAST(:query_vector AS vector)
        LIMIT :limit
    """)

    result = await db.execute(sql, {
        "query_vector": str(query_vector),
        "exclude_case_id": exclude_case_id,
        "limit": limit,
    })
    rows = result.fetchall()

    if not rows:
        return []

    # 사건 + 판결 정보 조회
    similar = []
    for row in rows:
        case_result = await db.execute(
            select(Case, Verdict)
            .join(Verdict, Case.id == Verdict.case_id)
            .where(Case.id == row.case_id)
        )
        pair = case_result.first()
        if pair:
            case, verdict = pair
            similar.append({
                "case_id": case.id,
                "title": case.title,
                "plaintiff_ratio": verdict.plaintiff_ratio,
                "defendant_ratio": verdict.defendant_ratio,
                "similarity": round(row.similarity * 100, 1),  # 퍼센트로 표시
            })

    return similar
