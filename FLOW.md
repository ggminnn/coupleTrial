# 커플 재판소 - 전체 흐름 완전 해설

---

## 목차
1. [서버 켜는 방법](#1-서버-켜는-방법)
2. [전체 흐름 한눈에 보기](#2-전체-흐름-한눈에-보기)
3. [회원가입 / 로그인](#3-회원가입--로그인)
4. [재판 생성과 초대](#4-재판-생성과-초대)
5. [주장 입력과 AI 모더레이션](#5-주장-입력과-ai-모더레이션)
6. [제출 → AI 판결 파이프라인](#6-제출--ai-판결-파이프라인)
7. [벡터 DB란 무엇이고 어떻게 쓰이나](#7-벡터-db란-무엇이고-어떻게-쓰이나)
8. [판결 결과 화면](#8-판결-결과-화면)
9. [이메일 자동 발송](#9-이메일-자동-발송)
10. [확인하는 방법 (로그 / DB)](#10-확인하는-방법-로그--db)

---

## 1. 서버 켜는 방법

### 전체 구조
이 앱은 세 개의 프로세스가 동시에 떠 있어야 합니다:

```
[Docker] PostgreSQL DB      ← 데이터 저장소
[Docker] FastAPI 백엔드     ← API 서버 (포트 8000)
[로컬]   React 프론트엔드   ← 화면 (포트 5173)
```

### 실행 순서

**터미널 1** — 백엔드 + DB 실행:
```bash
cd /mnt/c/sideProject/coupleTrial   # 프로젝트 루트로 이동
docker compose up                    # DB + API 서버 동시 실행
```

처음 실행할 때 이런 로그가 뜨면 정상입니다:
```
db-1   | database system is ready to accept connections
api-1  | INFO: Application startup complete.
```

**터미널 2** — 프론트엔드 실행:
```bash
cd /mnt/c/sideProject/coupleTrial/frontend
npm run dev
```

이렇게 뜨면 정상:
```
  VITE v5.x.x  ready in xxx ms
  ➜  Local:   http://localhost:5173/
```

### 종료하는 방법
```bash
# 터미널 1에서 Ctrl+C 누른 후
docker compose down   # 컨테이너 종료 (데이터는 보존됨)
```

### 재시작 (코드 수정 후)
- **백엔드 코드 수정**: 자동 반영 (`--reload` 옵션 덕분). 저장하면 바로 적용.
- **프론트엔드 코드 수정**: 자동 반영 (Vite HMR). 저장하면 바로 적용.
- **환경변수(.env) 수정**: `docker compose down && docker compose up` 필요.
- **requirements.txt 수정**: `docker compose up --build` 필요 (이미지 재빌드).

---

## 2. 전체 흐름 한눈에 보기

```
사용자 액션              파일 위치                  일어나는 일
─────────────────────────────────────────────────────────────────────
1. 회원가입/로그인   → app/routers/auth.py       JWT 토큰 발급
                      app/core/security.py       bcrypt 비밀번호 해싱

2. 재판 생성        → app/routers/cases.py       Case DB 저장, invite_token 생성
   초대 링크 공유   → (UUID 기반 랜덤 토큰)

3. 피고 입장        → app/routers/cases.py       defendant_id 설정
                      (POST /cases/join/{token})  status: WAITING → IN_PROGRESS

4. 주장 입력        → app/routers/chat.py        AI 모더레이션 통과 시 DB 저장
   욕설 필터링      → app/services/moderation.py GPT-4o로 맥락 판단

5. 제출 완료        → app/routers/cases.py       plaintiff/defendant_submitted = True
   (양측 모두)      → app/langgraph/graph.py     백그라운드로 run_trial() 실행

6. AI 판결          → app/langgraph/nodes.py     5단계 파이프라인 실행
   (자동, 30~60초)  → OpenAI GPT-4o 호출        판결문 생성

7. 판결 저장        → app/langgraph/graph.py     Verdict DB 저장
                                                  Case status → JUDGED

8. 후처리 (자동)    → app/services/email.py      양측에 이메일 발송
                      app/services/similarity.py  판결문 벡터화 → DB 저장

9. 결과 확인        → app/routers/verdict.py     판결 조회
                      frontend/VerdictPage.jsx    화면에 표시
```

---

## 3. 회원가입 / 로그인

### 파일: `app/routers/auth.py`

**회원가입 흐름:**
```
프론트엔드 입력 (이메일, 닉네임, 비밀번호)
    ↓
POST /auth/register
    ↓
app/routers/auth.py → RegisterRequest 스키마 검증
    ↓
이메일 중복 체크 (SELECT * FROM users WHERE email = ?)
    ↓
bcrypt로 비밀번호 해싱 (app/core/security.py)
    예) "1234" → "$2b$12$xyz..." (복호화 불가능한 해시)
    ↓
User 모델을 DB에 저장
    ↓
JWT 토큰 발급해서 응답
    예) {"access_token": "eyJhbGci...", "token_type": "bearer"}
```

**JWT 토큰이란?**
- 로그인 후 발급되는 "신분증"
- 프론트엔드(`frontend/src/lib/api.js`)가 모든 API 요청에 자동으로 헤더에 붙임:
  ```
  Authorization: Bearer eyJhbGci...
  ```
- 백엔드는 이 토큰을 보고 "누가 요청했는지" 판단 (`app/core/dependencies.py`)
- 60분 후 만료됨

---

## 4. 재판 생성과 초대

### 파일: `app/routers/cases.py`

**재판 생성:**
```
POST /cases  (body: {"title": "연락 안 한 것 때문에 싸운 사건"})
    ↓
Case 모델 생성:
  - id: UUID (자동 생성)
  - title: "연락 안 한 것 때문에..."
  - status: WAITING
  - plaintiff_id: 현재 로그인한 유저 ID
  - defendant_id: NULL (피고 아직 없음)
  - invite_token: UUID (자동 생성, 초대 링크용)
    ↓
DB 저장
```

**초대 링크:**
```
invite_token = "da52f5f7-991e-491f-8792-6dc2eb502029"
초대 링크 = "http://localhost:5173/join/da52f5f7-..."
```

**피고가 링크를 클릭하면:**
```
/join/{token} → frontend/src/pages/JoinPage.jsx
    ↓
로그인 안 했으면 → /login?redirect=/join/{token} 으로 이동
로그인 했으면 → POST /cases/join/{token}
    ↓
app/routers/cases.py
    - Case 조회 (invite_token으로)
    - defendant_id = 현재 유저 ID로 업데이트
    - status: WAITING → IN_PROGRESS
    ↓
/cases/{id}/chat 으로 이동 (주장 입력 화면)
```

---

## 5. 주장 입력과 AI 모더레이션

### 파일: `app/routers/chat.py`, `app/services/moderation.py`

**메시지 전송 흐름:**
```
사용자가 텍스트 입력 후 전송
    ↓
POST /chat/{case_id}/messages  (body: {"content": "너가 먼저 약속 어겼잖아"})
    ↓
app/routers/chat.py
    ↓
1. 사건 조회 + 권한 확인 (내가 이 사건의 원고 또는 피고?)
    ↓
2. AI 모더레이션 실행 (app/services/moderation.py)
   GPT-4o에게 물어봄:
   "이 메시지가 심각한 비방이나 욕설인가요?"
   → {"is_blocked": false, "reason": "", "cleaned": ""}
   → {"is_blocked": true, "reason": "심한 욕설 포함", "cleaned": "화가 났어요"}
    ↓
3. 차단이면 → 403 에러 반환 (프론트에서 "차단됨" 메시지 표시)
   허용이면 → Message DB 저장
              - role: PLAINTIFF (원고) 또는 DEFENDANT (피고)
              - content: 메시지 내용
```

**왜 상대방 메시지가 안 보이나?**

`GET /chat/{case_id}/messages` 에서:
```python
# app/routers/chat.py
.where(Message.user_id == current_user.id)  # 본인 메시지만 조회
```
쿼리에 `user_id = 내 ID` 조건이 붙어 있어서 상대방 것은 아예 조회 안 됨.

---

## 6. 제출 → AI 판결 파이프라인

### 파일: `app/routers/cases.py`, `app/langgraph/graph.py`, `app/langgraph/nodes.py`

**제출 처리:**
```
POST /cases/{case_id}/submit
    ↓
app/routers/cases.py
    - 원고가 누르면: plaintiff_submitted = True
    - 피고가 누르면: defendant_submitted = True
    ↓
양측 모두 True인지 체크
    ↓
모두 True → asyncio.create_task(run_trial(case_id))
             (백그라운드에서 실행, 요청은 즉시 응답)
    ↓
먼저 누른 사람: {"judging": false}  → ChatPage에서 대기
나중에 누른 사람: {"judging": true} → VerdictPage로 이동
```

**`asyncio.create_task`가 뭔가?**
- 일반 함수: A를 끝내야 B 실행 (순차)
- create_task: A 실행하는 동시에 B도 실행 (병렬)
- 판결은 30~60초 걸리니까, 사용자에게 응답 먼저 보내고 판결은 뒤에서 실행

---

### AI 판결 파이프라인 상세

**파일: `app/langgraph/graph.py`**

```python
async def run_trial(case_id):
    # 1. DB에서 메시지 로드
    messages = DB에서 해당 사건 메시지 전부 조회
    plaintiff_messages = [원고 메시지들]
    defendant_messages = [피고 메시지들]

    # 2. LangGraph 실행
    final_state = await trial_graph.ainvoke(initial_state)

    # 3. 결과 저장
    DB에 Verdict 저장
    Case status → JUDGED
```

**LangGraph가 뭔가?**
- 여러 AI 작업을 순서대로 연결하는 프레임워크
- 각 단계(노드)의 결과가 다음 단계의 입력이 됨
- 이 앱에서는 5개 노드가 순서대로 실행됨

**파일: `app/langgraph/nodes.py`**

```
노드 1: analyze_emotion (감정 분석)
────────────────────────────────────
입력: 원고 메시지들, 피고 메시지들
GPT-4o에게: "이 메시지들에서 감정 상태를 2~3문장으로 요약해줘"
출력:
  plaintiff_emotion: "원고는 약속이 지켜지지 않아 매우 서운하고 배신감을 느끼고 있습니다..."
  defendant_emotion: "피고는 억울함과 답답함을 느끼며 자신의 입장이 이해받지 못한다고..."

노드 2: summarize_facts (사실 정리)
────────────────────────────────────
입력: 원고 메시지들, 피고 메시지들
GPT-4o에게: "양측 주장을 요약하고 핵심 쟁점을 뽑아줘" (JSON 형식으로)
출력:
  plaintiff_summary: "원고는 피고가 약속한 저녁 약속을 취소했고..."
  defendant_summary: "피고는 갑작스러운 야근으로 어쩔 수 없었다고..."
  key_issues: ["약속 파기 여부", "사전 연락 유무", "보상 방법"]

노드 3: judge (판결) ← 핵심!
────────────────────────────────────
입력: 위의 모든 결과
특별한 점: GPT-4o가 스스로 "유사 판례 검색" 도구를 호출함 (Tool Use)

  GPT-4o: "판결 전에 유사 판례를 찾아봐야겠다"
      ↓
  search_similar_verdicts("약속 파기 연락 문제") 호출
      ↓
  pgvector DB에서 유사한 과거 판결 3개 검색
      ↓
  GPT-4o: "판례를 참고해서 판결문 작성"

출력:
  judgment: "본 재판부는 피고의 사전 연락 부재를 중대한 과실로 판단하는 바이다..."

노드 4: determine_ratio (비율 판정)
────────────────────────────────────
입력: judgment (판결문)
GPT-4o에게: "판결문을 읽고 원고/피고 잘못 비율을 숫자로만 (합계 100)"
출력:
  plaintiff_ratio: 30
  defendant_ratio: 70

노드 5: generate_missions (화해 미션)
────────────────────────────────────
입력: judgment, plaintiff_ratio, defendant_ratio
GPT-4o에게: "이 판결 결과를 바탕으로 화해 미션 3가지를 JSON으로"
출력:
  missions: [
    "오늘 저녁 직접 만나서 30분 대화하기",
    "피고가 먼저 사과 문자 보내기",
    "다음 약속은 서로 달력에 공유하기"
  ]
```

---

## 7. 벡터 DB란 무엇이고 어떻게 쓰이나

### 일반 DB vs 벡터 DB

**일반 DB (PostgreSQL)**
```
"약속" 이라는 단어를 검색하면 → "약속"이 포함된 것만 찾음
"연락 안 함" 검색 → "연락 안 함"이 포함된 것만 찾음
단어가 다르면 못 찾음
```

**벡터 DB (pgvector)**
```
"약속을 안 지킴" 검색 →
"연락이 없었음", "약속 파기", "카톡 무시" 같은
의미가 비슷한 것도 찾을 수 있음
```

### 어떻게 동작하나?

**1단계: 텍스트를 숫자 배열(벡터)로 변환**
```
"약속을 안 지킴"
    ↓  OpenAI text-embedding-3-small
[0.053, 0.072, -0.018, 0.046, ...] ← 1536개의 숫자
```
의미가 비슷한 문장은 비슷한 숫자 배열이 나옴.

**2단계: pgvector에 저장**
```
판결 완료 후 → app/services/similarity.py
판결문 텍스트를 벡터로 변환 → verdict_embeddings 테이블에 저장

verdict_embeddings 테이블:
┌─────────────────────────────────────────────────────────┐
│ case_id  │ embedding (1536개 숫자)                       │
├─────────────────────────────────────────────────────────┤
│ case-001 │ [0.053, 0.072, -0.018, ...]                   │
│ case-002 │ [0.031, 0.091, -0.022, ...]                   │
└─────────────────────────────────────────────────────────┘
```

**3단계: 새 사건 판결 시 유사 판례 검색**
```
judge 노드에서 search_similar_verdicts("약속 파기 연락 문제") 호출
    ↓
"약속 파기 연락 문제" → 벡터로 변환
    ↓
pgvector가 저장된 모든 판결과 거리 계산 (<=> 코사인 거리)
    ↓
가장 가까운(비슷한) 3개 반환
    ↓
"유사 판례: 연락 관련 싸움 | 원고 잘못 30% / 피고 잘못 70% | 유사도 87.3%"
```

**파일 경로:**
- 임베딩 저장: `app/services/similarity.py` → `save_verdict_embedding()`
- 유사도 검색: `app/services/similarity.py` → `find_similar_cases()`
- 판결 중 Tool Use 검색: `app/langgraph/nodes.py` → `search_similar_verdicts()`

---

## 8. 판결 결과 화면

### 파일: `app/routers/verdict.py`, `frontend/src/pages/VerdictPage.jsx`

**판결 데이터 조회:**
```
GET /verdicts/{case_id}
    ↓
verdicts 테이블에서 해당 사건 판결 조회
    ↓
{
  plaintiff_ratio: 30,
  defendant_ratio: 70,
  plaintiff_summary: "원고 주장 요약...",
  defendant_summary: "피고 주장 요약...",
  judgment: "본 재판부는...",
  missions: ["미션1", "미션2", "미션3"]
}
```

**승소/패소 판단 (프론트엔드):**
```javascript
// frontend/src/pages/VerdictPage.jsx
const myRatio = isPlaintiff ? verdict.plaintiff_ratio : verdict.defendant_ratio;
const isWinner = myRatio < 50;   // 내 잘못이 50% 미만이면 승소
```

**유사 판례 조회:**
```
GET /verdicts/{case_id}/similar
    ↓
현재 판결문을 벡터로 변환
    ↓
pgvector로 유사 사건 3개 검색
    ↓
화면 하단에 "유사 판례" 섹션으로 표시
```

**판결 화면 자동 전환 흐름:**
```
나중에 제출한 사람 → judging: true → navigate("/verdict") 즉시 이동
먼저 제출한 사람  → submitted 상태 → ChatPage에서 3초마다 /verdicts/{id} 폴링
                                       → 200 응답 오면 navigate("/verdict")
```

---

## 9. 이메일 자동 발송

### 파일: `app/langgraph/graph.py`, `app/services/email.py`

**판결 완료 직후 자동 실행:**
```python
# app/langgraph/graph.py
await db.commit()  # 판결 DB 저장 완료

# 이메일 발송
await send_verdict_to_both(
    plaintiff_email, plaintiff_nickname,
    defendant_email, defendant_nickname,
    case_title, plaintiff_ratio, defendant_ratio,
    judgment, missions
)
```

**Gmail 앱 비밀번호가 필요한 이유:**
- 일반 Gmail 비밀번호는 외부 앱에서 사용 불가
- Google 계정 → 2단계 인증 → 앱 비밀번호 생성 필요
- 생성된 앱 비밀번호(공백 포함 16자)를 `.env`의 `MAIL_PASSWORD`에 입력

**발송 확인 방법:**
```bash
docker compose logs api | grep "\[EMAIL\]"
# 출력 예시:
# [EMAIL] 판결 이메일 발송 완료: user1@gmail.com, user2@gmail.com
# [EMAIL ERROR] 이메일 발송 실패: ...
```

---

## 10. 확인하는 방법 (로그 / DB)

### API 로그 보기

```bash
# 실시간 로그 (계속 스트리밍)
docker compose logs api -f

# 최근 50줄만
docker compose logs api --tail=50

# 특정 키워드 검색
docker compose logs api | grep "ERROR"
docker compose logs api | grep "POST /cases"
docker compose logs api | grep "\[EMAIL\]"

# 판결 관련 로그만
docker compose logs api | grep -E "run_trial|Task exception|판결"
```

### DB 직접 확인

```bash
# PostgreSQL 접속
docker compose exec db psql -U postgres -d couple_trial

# 접속 후 사용할 수 있는 명령어:
\dt                          -- 테이블 목록 보기
SELECT * FROM users;         -- 가입된 유저 목록
SELECT * FROM cases;         -- 사건 목록
SELECT * FROM messages;      -- 메시지 목록
SELECT * FROM verdicts;      -- 판결 목록
SELECT case_id FROM verdict_embeddings;  -- 벡터 저장된 사건 목록

-- 특정 사건의 전체 흐름 확인
SELECT c.title, c.status, c.plaintiff_submitted, c.defendant_submitted
FROM cases c WHERE c.id = '사건ID';

-- 판결 결과 확인
SELECT plaintiff_ratio, defendant_ratio, judgment
FROM verdicts WHERE case_id = '사건ID';

-- 종료
\q
```

### API 직접 테스트

```bash
# API 문서 (브라우저에서)
http://localhost:8000/docs    # Swagger UI (직접 API 호출 가능)
http://localhost:8000/redoc   # ReDoc (읽기 좋은 문서)

# 예: 판결 조회
curl http://localhost:8000/verdicts/{case_id} \
  -H "Authorization: Bearer {JWT토큰}"
```

### 컨테이너 상태 확인

```bash
docker compose ps          # 컨테이너 실행 중인지 확인
docker compose exec api env | grep MAIL    # 이메일 환경변수 확인
docker compose exec api env | grep OPENAI  # OpenAI 키 확인
```

---

## 자주 생기는 문제

| 증상 | 원인 | 해결 |
|------|------|------|
| 판결이 안 남 | OpenAI API 에러 | `docker compose logs api \| grep "Task exception"` 로 에러 확인 |
| 이메일 안 옴 | 환경변수 미전달 | `docker compose exec api env \| grep MAIL` 확인 |
| 판결 후 화면 안 바뀜 | 폴링 중 | 최대 3초 기다리면 자동 전환됨 |
| 메시지 차단됨 | AI 모더레이션 | 욕설/비방 포함 시 정상 차단 |
| DB 내용 초기화하고 싶을 때 | — | `docker compose down -v && docker compose up` |
