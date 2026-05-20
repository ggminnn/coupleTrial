# 커플 재판소 - CLAUDE.md

## 프로젝트 개요

AI가 커플의 싸움을 판결하는 서비스. 원고/피고가 각자 주장을 입력하면 LangGraph 파이프라인이 감정 분석 → 사실 정리 → 판결 → 잘못 비율 → 화해 미션을 순차적으로 생성한다.

## 기술 스택

**Backend**: FastAPI + SQLAlchemy(async) + PostgreSQL + pgvector  
**AI**: LangGraph + LangChain + OpenAI GPT-4o + text-embedding-3-small  
**Frontend**: React 18 + React Router 6 + Tailwind CSS + Recharts + Vite  
**Infra**: Docker Compose (api + db 두 컨테이너)

## 폴더 구조

```
coupleTrial/
├── app/
│   ├── main.py                  # FastAPI 앱 진입점, lifespan으로 DB 초기화
│   ├── database.py              # SQLAlchemy 엔진, AsyncSessionLocal, get_db
│   ├── models/__init__.py       # ORM 모델: User, Case, Message, Verdict, VerdictEmbedding
│   │                            # Enum: CaseStatus, Role, JudgeStyle
│   ├── schemas/__init__.py      # Pydantic 스키마 (CaseCreate.judgeStyle 포함)
│   ├── routers/
│   │   ├── auth.py              # POST /auth/register, /auth/login, GET /auth/me
│   │   ├── cases.py             # CRUD + POST /cases/{id}/submit (판결 트리거)
│   │   ├── chat.py              # GET/POST /chat/{id}/messages
│   │   ├── verdict.py           # GET /verdicts/{id}, GET /verdicts/{id}/similar
│   │   ├── trial_ws.py          # WS /ws/trial/{case_id} (판결 진행 상태 실시간)
│   │   └── stats.py             # GET /stats/{case_id} (커플 재판 통계)
│   ├── core/
│   │   ├── config.py            # Settings (pydantic-settings, .env 로드)
│   │   ├── security.py          # JWT 발급/검증, bcrypt 해싱
│   │   ├── dependencies.py      # get_current_user 의존성
│   │   └── trial_ws.py          # TrialProgressManager 싱글턴 (WS 연결 관리)
│   ├── services/
│   │   ├── moderation.py        # GPT-4o 기반 욕설/비방 필터 (맥락 판단)
│   │   ├── similarity.py        # pgvector 코사인 유사도 검색 + 임베딩 저장
│   │   └── email.py             # Gmail SMTP (fastapi-mail)
│   └── langgraph/
│       ├── state.py             # TrialState TypedDict (judge_style 포함)
│       ├── nodes.py             # 5개 노드 함수 + 각 노드에서 WS progress broadcast
│       ├── graph.py             # 그래프 조립 + run_trial() + broadcast_done()
│       └── prompts/
│           ├── judge_default_prompt.py   # 기본 판사 (공정하고 차분한 톤)
│           └── judge_spicy_prompt.py     # 매운맛 판사 (직설적이고 독설 톤)
├── frontend/src/
│   ├── pages/
│   │   ├── LoginPage.jsx        # 로그인/회원가입
│   │   ├── CasesPage.jsx        # 사건 목록 (3초 폴링)
│   │   ├── NewCasePage.jsx      # 새 사건 생성 + 판사 스타일 카드 선택 UI
│   │   ├── JoinPage.jsx         # 초대 링크 입장
│   │   ├── ChatPage.jsx         # 주장 입력 + 제출 후 verdict 폴링 → 자동 이동
│   │   ├── VerdictPage.jsx      # WebSocket 진행 상태 → 판결 결과 + "통계 보기" 버튼
│   │   └── StatsPage.jsx        # 커플 통계 (파이/라인/바 차트, Recharts)
│   ├── contexts/AuthContext.jsx  # 인증 상태 전역 관리
│   ├── components/Layout.jsx    # 헤더/푸터
│   └── lib/api.js               # Axios (토큰 자동 주입, 401 처리)
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
└── .env                         # 환경변수 (아래 참고)
```

## 실행 방법

```bash
# 1. .env 파일 생성 (프로젝트 루트)
SECRET_KEY=your-secret-key
OPENAI_API_KEY=sk-...
MAIL_USERNAME=your@gmail.com
MAIL_PASSWORD=gmail-app-password   # Gmail 앱 비밀번호 (공백 포함)
MAIL_FROM=your@gmail.com

# 2. 백엔드 + DB 실행 (DB 스키마 변경 시 -v 플래그로 초기화 필요)
docker compose down -v && docker compose up

# 3. 프론트엔드 실행 (별도 터미널)
cd frontend && npm install && npm run dev

# 4. 접속
# 프론트엔드: http://localhost:5173
# API 문서:   http://localhost:8000/docs
```

**주의**: `docker compose down -v`는 DB 볼륨까지 삭제한다. judge_style Enum 컬럼 추가 후 기존 DB에는 반드시 실행해야 한다.

## AI 판결 파이프라인 (LangGraph)

```
submit (양측 모두) → asyncio.create_task(run_trial())
                              ↓
                    analyze_emotion      # 감정 분석 + WS broadcast(1/6)
                              ↓
                    summarize_facts      # 주장 요약 + 핵심 쟁점 + WS broadcast(2/6)
                              ↓
                    judge                # WS broadcast(3/6 유사 판례 검색)
                              │          # Tool Use: search_similar_verdicts
                              │          # WS broadcast(4/6 판결 중)
                              ↓
                    determine_ratio      # 잘못 비율 수치화 + WS broadcast(5/6)
                              ↓
                    generate_missions    # 화해 미션 3개 + WS broadcast(6/6)
                              ↓
                    broadcast_done()     # WS "done" 전송
                              ↓
                    DB 저장 + 이메일 발송 + 벡터 임베딩 저장
```

## 판사 스타일 (JudgeStyle)

| 값 | 설명 | 프롬프트 파일 |
|---|---|---|
| `default` | 공정하고 차분한 톤 | `judge_default_prompt.py` |
| `spicy` | 직설적이고 독설 톤 | `judge_spicy_prompt.py` |

- 재판 생성 시 원고가 선택 (`CaseCreate.judgeStyle`)
- `Case.judge_style` 컬럼에 저장 (PostgreSQL Enum)
- `run_trial()`에서 `case.judge_style.value`로 읽어 `TrialState.judge_style`에 전달
- `judge()` 노드에서 분기해 해당 프롬프트 import

## WebSocket 판결 진행 상태

```
클라이언트          WS /ws/trial/{case_id}?token=JWT
     │ connect
     ◄─────────── {"type": "progress", "step": 1, "total": 6, "message": "⚖️ 감정 분석 중..."}
     ◄─────────── {"type": "progress", "step": 2, ...}
     ...
     ◄─────────── {"type": "done", "message": "✅ 판결 완료!"}
     │ → loadVerdict() → 결과 화면 전환
```

- `app/core/trial_ws.py`: `TrialProgressManager` 싱글턴 (case_id별 WS 목록 관리)
- `app/routers/trial_ws.py`: WS 엔드포인트 (JWT 검증 → connect → receive_text loop)
- 각 노드에서 `trial_manager.broadcast()` 호출
- WS 실패 시 프론트엔드가 폴링으로 폴백

## 통계 API

```
GET /stats/{case_id}
→ 두 유저가 함께한 모든 JUDGED 사건 조회 (양방향: 역할 바뀐 경우 포함)
→ 싸움 유형 분류: 5개 카테고리 임베딩을 캐싱해두고 코사인 유사도로 자동 분류
→ asyncio.gather로 분류 병렬 처리

응답 (camelCase):
{
  totalCases, plaintiffNickname, defendantNickname,
  avgPlaintiffRatio, avgDefendantRatio,
  trend: [{caseId, title, date, plaintiffRatio, defendantRatio}],
  fightTypes: [{type, count}]
}
```

싸움 유형 카테고리: 연락 문제 / 약속 파기 / 감정 표현 / 외출·시간 / 경제적 갈등 / 기타

## 주요 데이터 모델

```
User ──< Case >── User          # 원고(plaintiff) / 피고(defendant)
         │
         ├──< Message          # role: PLAINTIFF | DEFENDANT
         └──── Verdict         # plaintiff_ratio, defendant_ratio, judgment, missions[]
                  │
                  └── VerdictEmbedding   # Vector(1536) for pgvector

Case 추가 컬럼:
  judge_style: JudgeStyle  # "default" | "spicy" (Enum)
```

**CaseStatus 흐름**: `WAITING` → (피고 입장) → `IN_PROGRESS` → (판결 완료) → `JUDGED`

## 주요 설계 결정 및 주의사항

- **채팅은 REST API**: WebSocket이 아닌 `POST /chat/{id}/messages`. WebSocket 코드는 남아 있지만 프론트는 REST 사용.
- **메시지 격리**: 각 유저는 본인 메시지만 조회 가능. 상대 주장은 판결 완료 후 summary로만 공개.
- **asyncio.create_task**: 판결은 백그라운드 실행. 에러가 "Task exception was never retrieved"로 로그에 찍히니 로그 확인 필요.
- **pgvector SQL**: asyncpg에서 `::vector` 캐스트 불가. 반드시 `CAST(:param AS vector)` 사용.
- **Docker SSL**: WSL2 환경에서 MTU 1450 설정 필요 (docker-compose.yml에 적용됨). certifi 패키지로 SSL 인증서 처리.
- **이메일 앱 비밀번호**: Gmail 앱 비밀번호는 공백 포함 16자. `.env`에 그대로 입력.
- **승소 기준**: `myRatio < 50` (내 잘못 비율이 50% 미만이면 승소).
- **camelCase 규칙**: 새로 추가하는 API 요청 파라미터는 camelCase (`judgeStyle`). 기존 응답 필드는 snake_case 유지. 프론트엔드 JS 변수는 항상 camelCase.
- **카테고리 임베딩 캐싱**: `stats.py`의 `_category_vecs` 딕셔너리는 프로세스 수명 동안 유지. 첫 요청에만 OpenAI API 호출.
- **WS 폴백**: VerdictPage는 WebSocket 오류 시 2초 간격 폴링으로 자동 전환.

## 환경변수 목록

| 변수 | 설명 |
|------|------|
| `SECRET_KEY` | JWT 서명 키 |
| `OPENAI_API_KEY` | OpenAI API 키 |
| `MAIL_USERNAME` | Gmail 계정 |
| `MAIL_PASSWORD` | Gmail 앱 비밀번호 |
| `MAIL_FROM` | 발신자 이메일 |
