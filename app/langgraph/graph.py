from langgraph.graph import StateGraph, END
from sqlalchemy import select

from app.langgraph.state import TrialState
from app.langgraph.nodes import (
    analyze_emotion,
    summarize_facts,
    judge,
    determine_ratio,
    generate_missions,
)
from app.models import Case, Message, Verdict, CaseStatus, Role
from app.database import AsyncSessionLocal


# ── 그래프 조립 ─────────────────────────────────────────────
def build_trial_graph():
    graph = StateGraph(TrialState)

    graph.add_node("analyze_emotion", analyze_emotion)
    graph.add_node("summarize_facts", summarize_facts)
    graph.add_node("judge", judge)
    graph.add_node("determine_ratio", determine_ratio)
    graph.add_node("generate_missions", generate_missions)

    graph.set_entry_point("analyze_emotion")
    graph.add_edge("analyze_emotion", "summarize_facts")
    graph.add_edge("summarize_facts", "judge")
    graph.add_edge("judge", "determine_ratio")
    graph.add_edge("determine_ratio", "generate_missions")
    graph.add_edge("generate_missions", END)

    return graph.compile()


trial_graph = build_trial_graph()


# ── 판결 실행 함수 ──────────────────────────────────────────
async def run_trial(case_id: str, db=None):
    """
    판결 완료 후 자동으로 3가지 실행:
      1. DB에 판결 저장 + 사건 상태 업데이트
      2. 원고/피고에게 이메일 자동 발송
      3. 판결문 벡터 임베딩 저장 (유사 사건 추천용)
    """
    async with AsyncSessionLocal() as db:
        # 메시지 로드
        result = await db.execute(
            select(Message).where(Message.case_id == case_id).order_by(Message.created_at)
        )
        messages = result.scalars().all()

        plaintiff_messages = [m.content for m in messages if m.role == Role.PLAINTIFF]
        defendant_messages = [m.content for m in messages if m.role == Role.DEFENDANT]

        if not plaintiff_messages or not defendant_messages:
            return

        # LangGraph 실행
        initial_state: TrialState = {
            "case_id": case_id,
            "plaintiff_messages": plaintiff_messages,
            "defendant_messages": defendant_messages,
            "plaintiff_summary": "",
            "defendant_summary": "",
            "plaintiff_emotion": "",
            "defendant_emotion": "",
            "key_issues": [],
            "judgment": "",
            "plaintiff_ratio": 0,
            "defendant_ratio": 0,
            "missions": [],
        }

        final_state = await trial_graph.ainvoke(initial_state)

        # ── 1. 판결 DB 저장 ────────────────────────────────────
        verdict = Verdict(
            case_id=case_id,
            plaintiff_ratio=final_state["plaintiff_ratio"],
            defendant_ratio=final_state["defendant_ratio"],
            plaintiff_summary=final_state["plaintiff_summary"],
            defendant_summary=final_state["defendant_summary"],
            judgment=final_state["judgment"],
            missions=final_state["missions"],
        )
        db.add(verdict)

        case_result = await db.execute(select(Case).where(Case.id == case_id))
        case = case_result.scalar_one_or_none()
        if case:
            case.status = CaseStatus.JUDGED

        await db.commit()

        # ── 2. 자동화: 판결 이메일 양측 발송 ──────────────────
        from app.services.email import send_verdict_to_both
        from app.models import User

        p_result = await db.execute(select(User).where(User.id == case.plaintiff_id))
        plaintiff = p_result.scalar_one_or_none()

        d_result = await db.execute(select(User).where(User.id == case.defendant_id))
        defendant = d_result.scalar_one_or_none()

        if plaintiff and defendant:
            try:
                await send_verdict_to_both(
                    plaintiff_email=plaintiff.email,
                    plaintiff_nickname=plaintiff.nickname,
                    defendant_email=defendant.email,
                    defendant_nickname=defendant.nickname,
                    case_title=case.title,
                    plaintiff_ratio=final_state["plaintiff_ratio"],
                    defendant_ratio=final_state["defendant_ratio"],
                    judgment=final_state["judgment"],
                    missions=final_state["missions"],
                )
                print(f"[EMAIL] 판결 이메일 발송 완료: {plaintiff.email}, {defendant.email}")
            except Exception as e:
                print(f"[EMAIL ERROR] 이메일 발송 실패: {e}")

        # ── 3. 자동화: 벡터 임베딩 저장 (유사 사건 추천) ──────
        from app.services.similarity import save_verdict_embedding
        await save_verdict_embedding(case_id, final_state["judgment"], db)
        await db.commit()
