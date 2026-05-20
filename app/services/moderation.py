from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
import json
import re
import httpx
import certifi

_http_client = httpx.AsyncClient(verify=certifi.where())
llm = ChatOpenAI(model="gpt-4o", temperature=0, http_async_client=_http_client)


async def check_moderation(content: str) -> dict:
    """
    메시지 내용을 AI로 검토.
    단순 키워드 필터가 아니라 맥락을 파악해서 판단.

    Returns:
        {
            "is_blocked": bool,
            "reason": str,       # 차단 사유 (허용이면 "")
            "cleaned": str       # 순화된 표현 제안 (차단 시)
        }
    """
    prompt = ChatPromptTemplate.from_template("""
당신은 커플 재판소의 콘텐츠 검토 AI입니다.
아래 메시지가 상대방을 심각하게 비방하거나 욕설을 포함하는지 판단하세요.

판단 기준:
- 허용: 감정 표현, 서운함, 억울함, 일반적인 불만 ("너무 화가 났어", "이건 진짜 아니야")
- 차단: 인신공격, 심한 욕설, 협박, 혐오 표현

메시지: {content}

JSON만 출력하세요:
{{
    "is_blocked": true/false,
    "reason": "차단 사유 (허용이면 빈 문자열)",
    "cleaned": "순화된 표현 제안 (허용이면 빈 문자열)"
}}
""")

    try:
        chain = prompt | llm
        result = await chain.ainvoke({"content": content})
        raw = result.content.strip()
        raw = re.sub(r"```json|```", "", raw).strip()
        return json.loads(raw)
    except Exception:
        return {"is_blocked": False, "reason": "", "cleaned": ""}
