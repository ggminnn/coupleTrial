# ⚖️ 커플 재판소

> **"사랑싸움도 공정하게"** — AI가 커플의 싸움을 판결하고 화해 미션을 제안하는 서비스

커플이 각자의 입장에서 주장을 작성하면, GPT-4o 기반 AI 판사가 감정을 분석하고 잘못 비율을 판정합니다.  
판결 진행 상태는 WebSocket으로 실시간 표시되며, 과거 유사 판례를 참고해 일관성 있는 판결을 내립니다.

---

## ✨ 주요 기능

### 🔐 인증
- 이메일/닉네임 기반 회원가입 및 로그인
- JWT 토큰 인증 (60분 만료)

### ⚖️ 재판 진행
- 원고가 사건을 생성하고 초대 링크로 피고를 초대
- 양측이 **독립된 공간**에서 주장 작성 (상대방 주장은 볼 수 없음)
- AI 모더레이션: 심한 욕설·비방 자동 차단 (맥락 기반 판단)

### 🎭 판사 스타일 선택
재판 생성 시 원고가 판사 스타일을 선택합니다:

| 스타일 | 특징 |
|--------|------|
| ⚖️ **기본 판사** | 공정하고 차분한 톤으로 판결 |
| 🌶️ **매운맛 판사** | 직설적이고 독설 넘치는 판결 |

### 🤖 AI 판결 파이프라인 (LangGraph)
양측 모두 제출하면 5단계 AI 파이프라인이 자동 실행됩니다:

```
감정 분석 → 사실 정리 → 유사 판례 검색 → 판결 → 잘못 비율 → 화해 미션
```

1. **감정 분석** — 양측 메시지에서 분노·서운함·억울함 등 감정 상태 파악
2. **사실 정리** — 핵심 쟁점 추출 및 양측 주장 요약
3. **AI 판결** — Tool Use로 유사 판례를 검색한 후 판결문 작성
4. **잘못 비율** — 원고/피고 잘못 비율 수치화 (합계 100%)
5. **화해 미션** — 두 사람이 화해할 수 있는 현실적인 미션 3가지 제안

### 📡 실시간 진행 상태 (WebSocket)
- 판결 시작부터 완료까지 6단계 진행 상태를 실시간으로 표시
- 프로그레스 바 + 단계 도트 + 단계별 텍스트
- 완료 시 자동으로 판결 결과 화면으로 전환

### 📊 커플 통계
- 두 사람의 전체 재판 이력을 차트로 시각화
- **파이차트**: 평균 잘못 비율 (원고 vs 피고)
- **라인차트**: 재판별 잘못 비율 추이
- **바차트**: 싸움 유형별 빈도 (pgvector 임베딩 유사도로 자동 분류)

### 📊 유사 판례 추천
- 판결문을 벡터로 변환 (OpenAI `text-embedding-3-small`)
- pgvector 코사인 유사도로 유사한 과거 사건 3건 추천

### 📧 자동 이메일 발송
- 판결 완료 시 원고·피고 양측에 판결문 이메일 자동 발송

---

## 🏗️ 아키텍처

```
┌──────────────────────────────────────────────────────────────┐
│                      Frontend (React 18)                      │
│                                                              │
│  LoginPage → CasesPage → NewCasePage (판사 스타일 선택)       │
│           → ChatPage → VerdictPage (WS 진행 상태) → StatsPage │
│                                                              │
│  Axios + React Router 6 + Tailwind CSS + Recharts            │
└──────────────────┬────────────────────┬──────────────────────┘
                   │ REST API           │ WebSocket
┌──────────────────▼────────────────────▼──────────────────────┐
│                      Backend (FastAPI)                        │
│                                                              │
│  /auth      → JWT 인증                                       │
│  /cases     → 사건 CRUD + 판사 스타일 저장 + 제출 처리        │
│  /chat      → 메시지 저장 + AI 모더레이션                    │
│  /verdicts  → 판결 조회 + 유사 판례                          │
│  /ws/trial  → 판결 진행 상태 WebSocket                       │
│  /stats     → 커플 전체 재판 통계 + 싸움 유형 분류           │
│                                                              │
│  ┌───────────────────────────────────────────────────────┐  │
│  │              LangGraph 판결 파이프라인                 │  │
│  │  analyze_emotion → summarize_facts → judge            │  │
│  │  → determine_ratio → generate_missions                │  │
│  │  (각 단계에서 WebSocket으로 진행 상태 broadcast)        │  │
│  └───────────────────────────────────────────────────────┘  │
└──────────┬────────────────────────────────────┬─────────────┘
           │                                    │
┌──────────▼──────────┐              ┌──────────▼──────────────┐
│     PostgreSQL       │              │       OpenAI API         │
│     + pgvector       │              │  GPT-4o (판결/모더레이션) │
│  (판결 벡터 저장      │              │  text-embedding-3-small  │
│   유사도 검색)        │              │  (판례 검색, 유형 분류)   │
└─────────────────────┘              └─────────────────────────┘
```

---

## 🛠️ 기술 스택

### Backend
| 기술 | 용도 |
|------|------|
| **FastAPI** | 비동기 REST API + WebSocket 서버 |
| **SQLAlchemy** (async) | ORM, DB 쿼리 |
| **PostgreSQL** + **pgvector** | 데이터 저장 + 벡터 유사도 검색 |
| **LangGraph** | AI 판결 파이프라인 오케스트레이션 |
| **LangChain** | LLM 프롬프팅 |
| **OpenAI GPT-4o** | 감정 분석, 판결, 화해미션, 모더레이션 |
| **OpenAI Embeddings** | 판결문 벡터화, 싸움 유형 분류 |
| **fastapi-mail** | Gmail SMTP 이메일 발송 |
| **PyJWT + bcrypt** | 인증/보안 |

### Frontend
| 기술 | 용도 |
|------|------|
| **React 18** | UI 컴포넌트 |
| **React Router 6** | 클라이언트 사이드 라우팅 |
| **Axios** | HTTP 클라이언트 (토큰 자동 주입) |
| **Recharts** | 통계 차트 (파이/라인/바) |
| **Tailwind CSS** | 스타일링 |
| **Vite** | 빌드 도구 |

### Infrastructure
| 기술 | 용도 |
|------|------|
| **Docker Compose** | 컨테이너 오케스트레이션 |
| **pgvector/pgvector:pg16** | PostgreSQL + 벡터 확장 |

---

## 🚀 실행 방법

### 사전 요구사항
- Docker & Docker Compose
- Node.js 18+
- OpenAI API 키
- Gmail 앱 비밀번호 ([설정 방법](https://support.google.com/accounts/answer/185833))

### 1. 환경변수 설정

프로젝트 루트에 `.env` 파일 생성:

```env
SECRET_KEY=your-secret-key-32chars-minimum
OPENAI_API_KEY=sk-...
MAIL_USERNAME=your@gmail.com
MAIL_PASSWORD=xxxx xxxx xxxx xxxx
MAIL_FROM=your@gmail.com
```

### 2. 백엔드 실행

```bash
# 처음 실행하거나 DB 스키마가 바뀐 경우
docker compose down -v && docker compose up

# 이후 실행
docker compose up
```

- API 서버: `http://localhost:8000`
- API 문서: `http://localhost:8000/docs`

### 3. 프론트엔드 실행

```bash
cd frontend
npm install
npm run dev
```

- 프론트엔드: `http://localhost:5173`

---

## 🔄 서비스 플로우

```
1. 원고가 사건 생성 + 판사 스타일 선택 (기본/매운맛)
2. 초대 링크를 피고에게 공유
3. 피고가 초대 링크로 입장
4. 양측이 각자의 공간에서 주장 작성 (상대방 주장 비공개)
5. 양측 모두 "제출 완료" 클릭
6. AI 판결 파이프라인 자동 실행 (약 30~60초)
   → WebSocket으로 단계별 진행 상태 실시간 표시
7. 판결 결과 화면 자동 전환
8. 양측에게 판결 이메일 자동 발송
9. "우리 통계 보기"에서 커플의 재판 이력 차트 확인
```

---

## 📂 프로젝트 구조

```
coupleTrial/
├── app/
│   ├── main.py
│   ├── database.py
│   ├── models/              # User, Case(+judge_style), Message, Verdict
│   ├── schemas/             # Pydantic 스키마 (CaseCreate.judgeStyle)
│   ├── routers/
│   │   ├── auth.py
│   │   ├── cases.py
│   │   ├── chat.py
│   │   ├── verdict.py
│   │   ├── trial_ws.py      # WS /ws/trial/{case_id}
│   │   └── stats.py         # GET /stats/{case_id}
│   ├── core/
│   │   ├── config.py
│   │   ├── security.py
│   │   ├── dependencies.py
│   │   └── trial_ws.py      # TrialProgressManager 싱글턴
│   ├── services/
│   │   ├── moderation.py
│   │   ├── similarity.py
│   │   └── email.py
│   └── langgraph/
│       ├── state.py          # TrialState (judge_style 포함)
│       ├── nodes.py          # 5개 노드 + WS broadcast
│       ├── graph.py          # run_trial() + broadcast_done()
│       └── prompts/
│           ├── judge_default_prompt.py
│           └── judge_spicy_prompt.py
├── frontend/src/
│   ├── pages/
│   │   ├── LoginPage.jsx
│   │   ├── CasesPage.jsx
│   │   ├── NewCasePage.jsx   # 판사 스타일 카드 선택
│   │   ├── JoinPage.jsx
│   │   ├── ChatPage.jsx
│   │   ├── VerdictPage.jsx   # WS 진행 상태 + 판결 결과
│   │   └── StatsPage.jsx     # Recharts 통계 차트
│   ├── contexts/AuthContext.jsx
│   ├── components/Layout.jsx
│   └── lib/api.js
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
├── CLAUDE.md                 # 개발자용 레퍼런스 (구조, 설계 결정)
├── FLOW.md                   # 전체 흐름 상세 해설
└── README.md                 # 이 파일
```

---

## 🎯 기술적 포인트

- **LangGraph Tool Use**: AI 판사가 스스로 판단해 유사 판례 검색 도구를 호출하는 에이전틱 패턴
- **RAG 판결**: 과거 판결문 벡터를 pgvector로 검색해 일관성 있는 판결 생성
- **판사 스타일 분기**: 프롬프트 파일 분리(`judge_default_prompt.py` / `judge_spicy_prompt.py`)로 확장 가능한 구조
- **WebSocket 진행 상태**: 판결 파이프라인 각 노드에서 `TrialProgressManager.broadcast()`로 실시간 전송, WS 실패 시 폴링 폴백
- **메시지 격리**: 양측이 서로의 주장을 볼 수 없는 독립 채팅 공간
- **비동기 판결**: FastAPI의 `asyncio.create_task`로 AI 파이프라인을 논블로킹 백그라운드 실행
- **AI 모더레이션**: 단순 키워드 필터가 아닌 GPT-4o의 맥락 기반 욕설 판단
- **임베딩 기반 유형 분류**: 사전 정의된 카테고리 임베딩을 캐싱해두고 코사인 유사도로 싸움 유형 자동 분류

---

## 📝 라이선스

MIT License
