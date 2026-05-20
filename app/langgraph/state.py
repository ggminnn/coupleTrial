from typing import TypedDict


class TrialState(TypedDict):
    case_id: str

    # 입력 데이터
    plaintiff_messages: list[str]    # 원고 메시지 목록
    defendant_messages: list[str]    # 피고 메시지 목록

    # 노드 처리 결과
    plaintiff_summary: str           # 원고 주장 요약
    defendant_summary: str           # 피고 주장 요약
    plaintiff_emotion: str           # 원고 감정 분석
    defendant_emotion: str           # 피고 감정 분석
    key_issues: list[str]            # 핵심 쟁점 목록
    judgment: str                    # 판결문
    plaintiff_ratio: int             # 원고 잘못 비율 (0~100)
    defendant_ratio: int             # 피고 잘못 비율 (0~100)
    missions: list[str]              # 화해미션 목록
