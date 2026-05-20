# 커플 재판소 - CLAUDE.md

## 프로젝트 개요

AI가 커플의 싸움을 판결하는 서비스. 원고/피고가 각자 주장을 입력하면 LangGraph 파이프라인이 감정 분석 → 사실 정리 → 판결 → 잘못 비율 → 화해 미션을 순차적으로 생성한다.

## 기술 스택

**Backend**: FastAPI + SQLAlchemy(async) + PostgreSQL + pgvector  
**AI**: LangGraph + LangChain + OpenAI GPT-4o + text-embedding-3-small  
**Frontend**: React 18 + React Router 6 + Tailwind CSS + Vite  
**Infra**: Docker Compose (api + db 두 컨테이너)

## 폴더 구조

```
coupleTrial/
├── app/
│   ├── main.py                  # FastAPI 앱 진입점, lifespan으로 DB 초기화
│   ├── database.py              # SQLAlchemy 엔진, AsyncSessionLocal, get_db
│   ├── models/__init__.py       # ORM 모델: User, Case, Message, Verdict, VerdictEmbedding
│   ├── schemas/__init__.py      # Pydantic 스키마
│   ├── routers/
│   │   ├── auth.py              # POST /auth/register, /auth/login, GET /auth/me
│   │   ├── cases.py             # CRUD + POST /cases/{id}/submit (판결 트리거)
│   │   ├── chat.py              # GET/POST /chat/{id}/messages (REST), WebSocket 유지
│   │   └── verdict.py           # GET /verdicts/{id}, GET /verdicts/{id}/similar
│   ├── core/
│   │   ├── config.py            # Settings (pydantic-settings, .env 로드)
│   │   ├── security.py          # JWT 발급/검증, bcrypt 해싱
│   │   └── dependencies.py      # get_current_user 의존성
│   ├── services/
│   │   ├── moderation.py        # GPT-4o 기반 욕설/비방 필터 (맥락 판단)
│   │   ├── similarity.py        # pgvector 코사인 유사도 검색 + 임베딩 저장
│   │   └── email.py             # Gmail SMTP (fastapi-mail)
│   └── langgraph/
│       ├── state.py             # TrialState TypedDict
│       ├── nodes.py             # 5개 노드 함수 + search_similar_verdicts Tool
│       └── graph.py             # 그래프 조립 + run_trial() 실행
├── frontend/src/
│   ├── pages/
│   │   ├── LoginPage.jsx        # 로그인/회원가입
│   │   ├── CasesPage.jsx        # 사건 목록 (3초 폴링)
│   │   ├── NewCasePage.jsx      # 새 사건 생성
│   │   ├── JoinPage.jsx         # 초대 링크 입장
│   │   ├── ChatPage.jsx         # 주장 입력 + 제출 후 verdict 폴링 → 자동 이동
│   │   └── VerdictPage.jsx      # 판결 결과 (1초 폴링 + 유사 판례)
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

# 2. 백엔드 + DB 실행
docker compose up

# 3. 프론트엔드 실행 (별도 터미널)
cd frontend && npm install && npm run dev

# 4. 접속
# 프론트엔드: http://localhost:5173
# API 문서:   http://localhost:8000/docs
```

**주의**: `docker-compose.yml`이 `env_file: .env`로 전체 로드. DATABASE_URL은 compose 파일에 하드코딩되어 있으므로 `.env`에 넣지 않아도 됨.

## AI 판결 파이프라인 (LangGraph)

```
submit (양측 모두) → asyncio.create_task(run_trial())
                              ↓
                    analyze_emotion      # 감정 분석
                              ↓
                    summarize_facts      # 주장 요약 + 핵심 쟁점
                              ↓
                    judge                # Tool Use: 유사 판례 검색 후 판결문
                              ↓
                    determine_ratio      # 잘못 비율 수치화 (합 = 100)
                              ↓
                    generate_missions    # 화해 미션 3개
                              ↓
                    DB 저장 + 이메일 발송 + 벡터 임베딩 저장
```

## 주요 데이터 모델

```
User ──< Case >── User          # 원고(plaintiff) / 피고(defendant)
         │
         ├──< Message          # role: PLAINTIFF | DEFENDANT
         └──── Verdict         # plaintiff_ratio, defendant_ratio, judgment, missions[]
                  │
                  └── VerdictEmbedding   # Vector(1536) for pgvector
```

**CaseStatus 흐름**: `WAITING` → (피고 입장) → `IN_PROGRESS` → (판결 완료) → `JUDGED`

## 주요 설계 결정 및 주의사항

- **채팅은 REST API**: WebSocket이 아닌 `POST /chat/{id}/messages`. WebSocket 코드는 남아 있지만 프론트는 REST 사용.
- **메시지 격리**: 각 유저는 본인 메시지만 조회 가능. 상대 주장은 판결 완료 후 summary로만 공개.
- **asyncio.create_task**: 판결은 백그라운드 실행. 에러가 "Task exception was never retrieved"로 로그에 찍히니 로그 확인 필요.
- **pgvector SQL**: asyncpg에서 `::vector` 캐스트 불가. 반드시 `CAST(:param AS vector)` 사용.
- **Docker SSL**: WSL2 환경에서 MTU 1450 설정 필요 (docker-compose.yml에 적용됨). certifi 패키지로 SSL 인증서 처리.
- **이메일 앱 비밀번호**: Gmail 앱 비밀번호는 공백 포함 16자. `.env`에 그대로 입력, docker-compose는 `env_file`로 로드.
- **승소 기준**: `myRatio < 50` (내 잘못 비율이 50% 미만이면 승소).

## 환경변수 목록

| 변수 | 설명 |
|------|------|
| `SECRET_KEY` | JWT 서명 키 |
| `OPENAI_API_KEY` | OpenAI API 키 |
| `MAIL_USERNAME` | Gmail 계정 |
| `MAIL_PASSWORD` | Gmail 앱 비밀번호 |
| `MAIL_FROM` | 발신자 이메일 |
