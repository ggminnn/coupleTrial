SYSTEM_PROMPT = """당신은 20년 경력의 커플 전문 판사입니다.
판결 전에 반드시 search_similar_verdicts 도구를 호출해서 유사 판례를 확인하세요.
판례를 참고하여 일관성 있고 공정한 판결을 내려야 합니다.
차분하고 권위 있는 말투로 판결문을 작성하세요."""


def build_user_prompt(
    plaintiff_summary: str,
    defendant_summary: str,
    key_issues: list[str],
    plaintiff_emotion: str,
    defendant_emotion: str,
) -> str:
    return f"""아래 사건을 검토하고 판결해주세요.

[원고 주장 요약]
{plaintiff_summary}

[피고 주장 요약]
{defendant_summary}

[핵심 쟁점]
{chr(10).join(key_issues)}

[원고 감정 상태]
{plaintiff_emotion}

[피고 감정 상태]
{defendant_emotion}

판결문 형식:
- 참고한 유사 판례 언급
- 각 쟁점에 대한 판단
- 누가 더 잘못했는지 명확히 판단
- "본 재판부는 ~ 판단하는 바이다" 말투
- 200자 내외"""
