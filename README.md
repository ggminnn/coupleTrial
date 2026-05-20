# ⚖️ 커플 재판소

> **"사랑싸움도 공정하게"** — AI가 커플의 싸움을 판결하고 화해 미션을 제안하는 서비스

커플이 각자의 입장에서 주장을 작성하면, GPT-4o 기반 AI 판사가 감정을 분석하고 잘못 비율을 판정합니다.  
판결 결과는 이메일로 발송되며, 과거 유사 판례를 참고해 일관성 있는 판결을 내립니다.

---

## 📸 스크린샷

| 사건 목록 | 주장 입력 | 판결 결과 |
|:---------:|:---------:|:---------:|
| ![cases](./docs/screenshot-cases.png) | ![chat](./docs/screenshot-chat.png) | ![verdict](./docs/screenshot-verdict.png) |

---

## ✨ 주요 기능

### 🔐 인증
- 이메일/닉네임 기반 회원가입 및 로그인
- JWT 토큰 인증 (60분 만료)

### ⚖️ 재판 진행
- 원고가 사건을 생성하고 초대 링크로 피고를 초대
- 양측이 **독립된 공간**에서 주장 작성 (상대방 주장은 볼 수 없음)
- AI 모더레이션: 심한 욕설·비방 자동 차단 (맥락 기반 판단)

### 🤖 AI 판결 파이프라인 (LangGraph)
양측 모두 제출하면 5단계 AI 파이프라인이 자동 실행됩니다:

```
감정 분석 → 사실 정리 → 판결 (유사 판례 참고) → 잘못 비율 → 화해 미션
```

1. **감정 분석** — 양측 메시지에서 분노·서운함·억울함 등 감정 상태 파악
2. **사실 정리** — 핵심 쟁점 추출 및 양측 주장 요약
3. **AI 판결** — Tool Use로 유사 판례를 검색한 후 판결문 작성
4. **잘못 비율** — 원고/피고 잘못 비율 수치화 (합계 100%)
5. **화해 미션** — 두 사람이 화해할 수 있는 현실적인 미션 3가지 제안

### 📊 유사 판례 추천
- 판결문을 벡터로 변환 (OpenAI `text-embedding-3-small`)
- pgvector 코사인 유사도로 유사한 과거 사건 3건 추천
- AI 판사가 판례를 참고해 일관성 있는 판결

### 📧 자동 이메일 발송
- 판결 완료 시 원고·피고 양측에 판결문 이메일 자동 발송
- 잘못 비율, 판결문, 화해 미션 포함

---

## 🏗️ 아키텍처

```
┌──────────────────────────────────────────────────────────┐
│                     Frontend (React)                      │
│  LoginPage → CasesPage → ChatPage → VerdictPage          │
│  Axios + React Router + Tailwind CSS                      │
└────────────────────┬─────────────────────────────────────┘
                     │ REST API
┌────────────────────▼─────────────────────────────────────┐
│                  Backend (FastAPI)                        │
│                                                          │
│  /auth    → JWT 인증                                     │
│  /cases   → 사건 CRUD + 제출 처리                        │
│  /chat    → 메시지 저장 + AI 모더레이션                  │
│  /verdicts → 판결 조회 + 유사 판례                       │
│                                                          │
│  ┌─────────────────────────────────────────────────┐    │
│  │           LangGraph 판결 파이프라인              │    │
│  │  analyze_emotion → summarize_facts → judge      │    │
│  │  → determine_ratio → generate_missions          │    │
│  └─────────────────────────────────────────────────┘    │
└──────┬───────────────────────────────────────┬──────────┘
       │                                       │
┌──────▼──────┐                    ┌──────────▼──────────┐
│  PostgreSQL  │                    │    OpenAI API        │
│  + pgvector  │                    │  GPT-4o              │
│              │                    │  text-embedding-3    │
└─────────────┘                    └─────────────────────┘
```

---

## 🛠️ 기술 스택

### Backend
| 기술 | 용도 |
|------|------|
| **FastAPI** | 비동기 REST API 서버 |
| **SQLAlchemy** (async) | ORM, DB 쿼리 |
| **PostgreSQL** + **pgvector** | 데이터 저장 + 벡터 유사도 검색 |
| **LangGraph** | AI 판결 파이프라인 오케스트레이션 |
| **LangChain** | LLM 프롬프팅 |
| **OpenAI GPT-4o** | 감정 분석, 판결, 모더레이션 |
| **OpenAI Embeddings** | 판결문 벡터화 |
| **fastapi-mail** | Gmail SMTP 이메일 발송 |
| **PyJWT + bcrypt** | 인증/보안 |

### Frontend
| 기술 | 용도 |
|------|------|
| **React 18** | UI 컴포넌트 |
| **React Router 6** | 클라이언트 사이드 라우팅 |
| **Axios** | HTTP 클라이언트 (토큰 자동 주입) |
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
docker compose up
```

- API 서버: `http://localhost:8000`
- API 문서: `http://localhost:8000/docs`
- DB는 컨테이너 내에서 자동 실행 및 테이블 생성

### 3. 프론트엔드 실행

```bash
cd frontend
npm install
npm run dev
```

- 프론트엔드: `http://localhost:5173`

---

## 📂 프로젝트 구조

```
coupleTrial/
├── app/
│   ├── main.py
│   ├── database.py
│   ├── models/          # SQLAlchemy ORM 모델
│   ├── schemas/         # Pydantic 요청/응답 스키마
│   ├── routers/         # auth, cases, chat, verdict
│   ├── core/            # config, security, dependencies
│   ├── services/        # moderation, similarity, email
│   └── langgraph/       # state, nodes, graph
├── frontend/
│   └── src/
│       ├── pages/       # 6개 페이지 컴포넌트
│       ├── components/  # Layout
│       ├── contexts/    # AuthContext
│       └── lib/         # api.js (Axios)
├── docker-compose.yml
├── Dockerfile
└── requirements.txt
```

---

## 🔄 서비스 플로우

```
1. 원고가 사건 생성 → 초대 링크 발급
2. 피고가 초대 링크로 입장
3. 양측 각자의 공간에서 주장 작성 (상대방 주장 비공개)
4. 양측 모두 "제출 완료" 클릭
5. AI 판결 파이프라인 자동 실행 (약 30~60초)
6. 판결 결과 화면 자동 전환
7. 양측에게 판결 이메일 자동 발송
```

---

## 🎯 기술적 포인트

- **LangGraph Tool Use**: AI 판사가 스스로 판단해 유사 판례 검색 도구를 호출하는 에이전틱 패턴
- **RAG 판결**: 과거 판결문 벡터를 pgvector로 검색해 일관성 있는 판결 생성
- **메시지 격리**: 양측이 서로의 주장을 볼 수 없는 독립 채팅 공간
- **비동기 판결**: FastAPI의 `asyncio.create_task`로 AI 파이프라인을 논블로킹 백그라운드 실행
- **AI 모더레이션**: 단순 키워드 필터가 아닌 GPT-4o의 맥락 기반 욕설 판단

---

## 📝 라이선스

MIT License
