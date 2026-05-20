from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, SystemMessage
from app.langgraph.state import TrialState
from app.database import AsyncSessionLocal
import json
import re
import httpx
import certifi

_http_client = httpx.AsyncClient(verify=certifi.where())
llm = ChatOpenAI(model="gpt-4o", temperature=0.3, http_async_client=_http_client)


# ══════════════════════════════════════════════════════════════
# Tool 정의 - 판사 AI가 스스로 호출할 도구들
# ══════════════════════════════════════════════════════════════

@tool
async def search_similar_verdicts(query: str) -> str:
    """
    과거 유사 판례를 시맨틱 검색으로 조회한다.
    판사가 판결 시 참고할 유사 사건의 판결 결과를 반환한다.

    Args:
        query: 검색할 사건 내용 (예: "연락 관련 싸움", "외출 허락 문제")
    """
    from app.services.similarity import find_similar_cases
    from langchain_openai import OpenAIEmbeddings

    embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
    query_vector = await embeddings.aembed_query(query)

    async with AsyncSessionLocal() as db:
        from sqlalchemy import text
        sql = text("""
            SELECT
                ve.case_id,
                1 - (ve.embedding <=> CAST(:query_vector AS vector)) AS similarity
            FROM verdict_embeddings ve
            ORDER BY ve.embedding <=> CAST(:query_vector AS vector)
            LIMIT 3
        """)
        result = await db.execute(sql, {"query_vector": str(query_vector)})
        rows = result.fetchall()

        if not rows:
            return "유사한 판례가 없습니다. 첫 번째 사건으로 독립적으로 판결하세요."

        from sqlalchemy import select
        from app.models import Case, Verdict

        precedents = []
        for row in rows:
            case_result = await db.execute(
                select(Case, Verdict)
                .join(Verdict, Case.id == Verdict.case_id)
                .where(Case.id == row.case_id)
            )
            pair = case_result.first()
            if pair:
                case, verdict = pair
                precedents.append(
                    f"- 사건: {case.title} | "
                    f"원고 잘못 {verdict.plaintiff_ratio}% / 피고 잘못 {verdict.defendant_ratio}% | "
                    f"유사도: {round(row.similarity * 100, 1)}%"
                )

        return "유사 판례:\n" + "\n".join(precedents)


# Tool Use용 LLM (도구 바인딩)
llm_with_tools = ChatOpenAI(model="gpt-4o", temperature=0.3).bind_tools(
    [search_similar_verdicts]
)


# ══════════════════════════════════════════════════════════════
# 노드 함수들
# ══════════════════════════════════════════════════════════════

# ── 노드 1: 감정 분석 ───────────────────────────────────────
async def analyze_emotion(state: TrialState) -> TrialState:
    """양측 메시지에서 감정 상태를 분석한다"""
    from app.core.trial_ws import trial_manager
    await trial_manager.broadcast(state["case_id"], 1, 6, "⚖️ 감정 분석 중...")

    prompt = ChatPromptTemplate.from_template("""
당신은 커플 심리 전문가입니다.
아래 메시지들을 분석하여 이 사람의 감정 상태를 2~3문장으로 요약하세요.
분노, 서운함, 억울함 등 구체적인 감정을 포함해주세요.

메시지 목록:
{messages}

감정 분석 결과:
""")

    chain = prompt | llm

    plaintiff_result = await chain.ainvoke({
        "messages": "\n".join(state["plaintiff_messages"])
    })
    defendant_result = await chain.ainvoke({
        "messages": "\n".join(state["defendant_messages"])
    })

    return {
        **state,
        "plaintiff_emotion": plaintiff_result.content,
        "defendant_emotion": defendant_result.content,
    }


# ── 노드 2: 사실관계 정리 + 주장 요약 ──────────────────────
async def summarize_facts(state: TrialState) -> TrialState:
    """양측 주장을 요약하고 핵심 쟁점을 추출한다"""
    from app.core.trial_ws import trial_manager
    await trial_manager.broadcast(state["case_id"], 2, 6, "📋 사실 정리 중...")

    prompt = ChatPromptTemplate.from_template("""
당신은 법원 서기입니다. 아래 원고와 피고의 주장을 읽고 정리해주세요.

[원고 주장]
{plaintiff_messages}

[피고 주장]
{defendant_messages}

다음 형식으로 JSON만 출력하세요 (다른 텍스트 없이):
{{
    "plaintiff_summary": "원고 주장 2~3문장 요약",
    "defendant_summary": "피고 주장 2~3문장 요약",
    "key_issues": ["쟁점1", "쟁점2", "쟁점3"]
}}
""")

    chain = prompt | llm
    result = await chain.ainvoke({
        "plaintiff_messages": "\n".join(state["plaintiff_messages"]),
        "defendant_messages": "\n".join(state["defendant_messages"]),
    })

    raw = re.sub(r"```json|```", "", result.content.strip()).strip()
    parsed = json.loads(raw)

    return {
        **state,
        "plaintiff_summary": parsed["plaintiff_summary"],
        "defendant_summary": parsed["defendant_summary"],
        "key_issues": parsed["key_issues"],
    }


# ── 노드 3: 판사 판결 (Tool Use 핵심) ──────────────────────
async def judge(state: TrialState) -> TrialState:
    """
    판사 AI가 스스로 판단해서 유사 판례 검색 도구를 호출하고
    판례를 참고해서 판결문을 작성한다. (Tool Use + RAG)
    """

    from app.core.trial_ws import trial_manager
    await trial_manager.broadcast(state["case_id"], 3, 6, "🔍 유사 판례 검색 중...")

    if state.get("judge_style") == "spicy":
        from app.langgraph.prompts.judge_spicy_prompt import SYSTEM_PROMPT, build_user_prompt
    else:
        from app.langgraph.prompts.judge_default_prompt import SYSTEM_PROMPT, build_user_prompt

    system_prompt = SYSTEM_PROMPT
    user_prompt = build_user_prompt(
        state["plaintiff_summary"],
        state["defendant_summary"],
        state["key_issues"],
        state["plaintiff_emotion"],
        state["defendant_emotion"],
    )

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt),
    ]

    # 1차 호출: AI가 도구 호출 여부 결정
    response = await llm_with_tools.ainvoke(messages)
    messages.append(response)

    # Tool Use: AI가 search_similar_verdicts 호출했으면 실행
    if response.tool_calls:
        for tool_call in response.tool_calls:
            if tool_call["name"] == "search_similar_verdicts":
                tool_result = await search_similar_verdicts.ainvoke(
                    tool_call["args"]["query"]
                )
                from langchain_core.messages import ToolMessage
                messages.append(
                    ToolMessage(
                        content=tool_result,
                        tool_call_id=tool_call["id"],
                    )
                )

        # 2차 호출 전: 판결 작성 단계 알림
        await trial_manager.broadcast(state["case_id"], 4, 6, "⚖️ 판결 중...")
        final_response = await llm_with_tools.ainvoke(messages)
        judgment = final_response.content
    else:
        await trial_manager.broadcast(state["case_id"], 4, 6, "⚖️ 판결 중...")
        judgment = response.content

    return {**state, "judgment": judgment}


# ── 노드 4: 잘못 비율 판정 ─────────────────────────────────
async def determine_ratio(state: TrialState) -> TrialState:
    """판결문을 기반으로 잘못 비율을 수치화한다"""
    from app.core.trial_ws import trial_manager
    await trial_manager.broadcast(state["case_id"], 5, 6, "📊 잘못 비율 계산 중...")

    prompt = ChatPromptTemplate.from_template("""
아래 판결문을 읽고 원고와 피고의 잘못 비율을 숫자로만 판단하세요.
합계는 반드시 100이 되어야 합니다.

판결문:
{judgment}

JSON만 출력하세요:
{{
    "plaintiff_ratio": 숫자,
    "defendant_ratio": 숫자
}}
""")

    chain = prompt | llm
    result = await chain.ainvoke({"judgment": state["judgment"]})

    raw = re.sub(r"```json|```", "", result.content.strip()).strip()
    parsed = json.loads(raw)

    return {
        **state,
        "plaintiff_ratio": parsed["plaintiff_ratio"],
        "defendant_ratio": parsed["defendant_ratio"],
    }


# ── 노드 5: 화해미션 생성 ──────────────────────────────────
async def generate_missions(state: TrialState) -> TrialState:
    """판결 결과를 바탕으로 화해미션을 생성한다"""
    from app.core.trial_ws import trial_manager
    await trial_manager.broadcast(state["case_id"], 6, 6, "🤝 화해 미션 생성 중...")

    prompt = ChatPromptTemplate.from_template("""
커플 상담 전문가로서, 아래 판결 결과를 바탕으로
두 사람이 화해할 수 있는 현실적인 미션 3가지를 제안해주세요.

[판결문]
{judgment}

[잘못 비율]
원고: {plaintiff_ratio}%, 피고: {defendant_ratio}%

미션은 구체적이고 실행 가능해야 합니다.
(예: "오늘 저녁 직접 만나서 30분 대화하기", "먼저 사과 문자 보내기")

JSON만 출력하세요:
{{
    "missions": ["미션1", "미션2", "미션3"]
}}
""")

    chain = prompt | llm
    result = await chain.ainvoke({
        "judgment": state["judgment"],
        "plaintiff_ratio": state["plaintiff_ratio"],
        "defendant_ratio": state["defendant_ratio"],
    })

    raw = re.sub(r"```json|```", "", result.content.strip()).strip()
    parsed = json.loads(raw)

    return {**state, "missions": parsed["missions"]}
