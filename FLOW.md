# 커플 재판소 - 전체 흐름 완전 해설

---

## 목차
1. [서버 켜는 방법](#1-서버-켜는-방법)
2. [전체 흐름 한눈에 보기](#2-전체-흐름-한눈에-보기)
3. [회원가입 / 로그인](#3-회원가입--로그인)
4. [재판 생성과 판사 스타일 선택](#4-재판-생성과-판사-스타일-선택)
5. [주장 입력과 AI 모더레이션](#5-주장-입력과-ai-모더레이션)
6. [제출 → AI 판결 파이프라인](#6-제출--ai-판결-파이프라인)
7. [WebSocket 실시간 진행 상태](#7-websocket-실시간-진행-상태)
8. [벡터 DB란 무엇이고 어떻게 쓰이나](#8-벡터-db란-무엇이고-어떻게-쓰이나)
9. [판결 결과 화면](#9-판결-결과-화면)
10. [이메일 자동 발송](#10-이메일-자동-발송)
11. [커플 통계 (StatsPage)](#11-커플-통계-statspage)
12. [확인하는 방법 (로그 / DB)](#12-확인하는-방법-로그--db)

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
# DB 스키마가 바뀌었으면 -v 옵션으로 볼륨까지 초기화
docker compose down -v && docker compose up
```

처음 실행할 때 이런 로그가 뜨면 정상입니다:
```
db-1   | database system is ready to accept connections
api-1  | INFO: Application startup complete.
```

**터미널 2** — 프론트엔드 실행:
```bash
cd frontend
npm run dev
```

### 종료하는 방법
```bash
# 터미널 1에서 Ctrl+C 누른 후
docker compose down        # 컨테이너 종료 (데이터 보존)
docker compose down -v     # 컨테이너 + DB 데이터까지 초기화
```

### 재시작 (코드 수정 후)
- **백엔드 코드 수정**: 자동 반영 (`--reload` 옵션). 저장하면 바로 적용.
- **프론트엔드 코드 수정**: 자동 반영 (Vite HMR).
- **환경변수(.env) 수정**: `docker compose down && docker compose up` 필요.
- **requirements.txt 수정**: `docker compose up --build` 필요 (이미지 재빌드).

---

## 2. 전체 흐름 한눈에 보기

```
사용자 액션                파일 위치                    일어나는 일
───────────────────────────────────────────────────────────────────────
1. 회원가입/로그인    → app/routers/auth.py           JWT 토큰 발급
                        app/core/security.py           bcrypt 비밀번호 해싱

2. 재판 생성          → app/routers/cases.py           Case DB 저장
   판사 스타일 선택   → app/models (JudgeStyle Enum)   judge_style 컬럼 저장
   초대 링크 공유     → (UUID 기반 invite_token)

3. 피고 입장          → app/routers/cases.py           defendant_id 설정
                        (POST /cases/join/{token})      status: WAITING → IN_PROGRESS

4. 주장 입력          → app/routers/chat.py            AI 모더레이션 통과 시 DB 저장
   욕설 필터링        → app/services/moderation.py     GPT-4o 맥락 판단

5. 제출 완료          → app/routers/cases.py           plaintiff/defendant_submitted = True
   (양측 모두)        → app/langgraph/graph.py         백그라운드로 run_trial() 실행

6. AI 판결            → app/langgraph/nodes.py         5단계 파이프라인 실행
   (자동, 30~60초)    → app/core/trial_ws.py           각 단계 WS로 실시간 전송

7. 판결 저장          → app/langgraph/graph.py         Verdict DB 저장
                                                        Case status → JUDGED
                                                        broadcast_done() → WS "done" 전송

8. 후처리 (자동)      → app/services/email.py          양측에 이메일 발송
                        app/services/similarity.py      판결문 벡터화 → DB 저장

9. 결과 확인          → app/routers/verdict.py         판결 조회
                        frontend/VerdictPage.jsx        WS done 수신 후 자동 전환

10. 통계 확인         → app/routers/stats.py           커플 전체 재판 통계
                         frontend/StatsPage.jsx          파이/라인/바 차트
```

---

## 3. 회원가입 / 로그인

### 파일: `app/routers/auth.py`, `app/core/security.py`

**회원가입 흐름:**
```
프론트엔드 입력 (이메일, 닉네임, 비밀번호)
    ↓
POST /auth/register
    ↓
이메일 중복 체크 → bcrypt 비밀번호 해싱 → User DB 저장 → JWT 토큰 발급
```

**JWT 토큰이란?**
- 로그인 후 발급되는 "신분증". `localStorage.getItem("token")`에 저장.
- `frontend/src/lib/api.js`가 모든 API 요청 헤더에 자동 삽입:
  ```
  Authorization: Bearer eyJhbGci...
  ```
- 백엔드는 이 토큰을 보고 누가 요청했는지 판단 (`app/core/dependencies.py`)
- 60분 후 만료

---

## 4. 재판 생성과 판사 스타일 선택

### 파일: `app/routers/cases.py`, `app/models/__init__.py`, `frontend/src/pages/NewCasePage.jsx`

**NewCasePage UI:**
```
사건 제목 입력
    +
판사 스타일 카드 선택 (라디오 카드 형태)
  ┌─────────────────┐  ┌─────────────────┐
  │  ⚖️  기본 판사   │  │  🌶️ 매운맛 판사  │
  │ 공정하고 차분한 톤│  │ 직설적이고 독설 톤│
  └─────────────────┘  └─────────────────┘
    ↓
POST /cases  body: { title: "...", judgeStyle: "default" | "spicy" }
```

**백엔드 처리:**
```python
# app/routers/cases.py
style = JudgeStyle.SPICY if body.judgeStyle == "spicy" else JudgeStyle.DEFAULT
case = Case(title=body.title, plaintiff_id=current_user.id, judge_style=style)
```

**JudgeStyle Enum:**
```python
# app/models/__init__.py
class JudgeStyle(str, enum.Enum):
    DEFAULT = "default"  # app/langgraph/prompts/judge_default_prompt.py
    SPICY   = "spicy"    # app/langgraph/prompts/judge_spicy_prompt.py
```

**피고 초대:**
```
invite_token = UUID 자동 생성
초대 링크 = "http://localhost:5173/join/{invite_token}"
    ↓
피고가 링크 클릭 → POST /cases/join/{token}
    → defendant_id 설정, status: WAITING → IN_PROGRESS
```

---

## 5. 주장 입력과 AI 모더레이션

### 파일: `app/routers/chat.py`, `app/services/moderation.py`

**메시지 전송 흐름:**
```
POST /chat/{case_id}/messages  (body: {"content": "너가 먼저 약속 어겼잖아"})
    ↓
권한 확인 (내가 이 사건의 원고 또는 피고?)
    ↓
AI 모더레이션 (app/services/moderation.py)
  GPT-4o: "이 메시지가 심각한 비방이나 욕설인가요?"
  → {"is_blocked": false}   → DB 저장
  → {"is_blocked": true}    → 400 에러 (차단)
```

**왜 상대방 메시지가 안 보이나?**
```python
# 본인 메시지만 조회
.where(Message.user_id == current_user.id)
```
쿼리에 `user_id = 내 ID` 조건이 붙어 있어 상대방 것은 아예 조회 안 됨.
상대방 주장은 판결 완료 후 `verdict.plaintiff_summary` / `verdict.defendant_summary`로만 공개.

---

## 6. 제출 → AI 판결 파이프라인

### 파일: `app/routers/cases.py`, `app/langgraph/graph.py`, `app/langgraph/nodes.py`

**제출 처리:**
```
POST /cases/{case_id}/submit
    ↓
원고 → plaintiff_submitted = True
피고 → defendant_submitted = True
    ↓
양측 모두 True → asyncio.create_task(run_trial(case_id))
                  (백그라운드 실행, 요청은 즉시 응답)
```

**`asyncio.create_task`가 뭔가?**
- 일반 함수: A를 끝내야 B 실행 (순차)
- create_task: A 실행하는 동시에 B도 실행 (병렬)
- 판결은 30~60초 걸리니까 사용자에게 응답 먼저 보내고 판결은 뒤에서 실행

---

### AI 판결 파이프라인 상세

**파일: `app/langgraph/nodes.py`**

```
노드 1: analyze_emotion  (WS: "⚖️ 감정 분석 중...")
────────────────────────────────────────────────────
입력:  원고 메시지들, 피고 메시지들
LLM:   "이 메시지들에서 감정 상태를 2~3문장으로 요약해줘"
출력:  plaintiff_emotion, defendant_emotion

노드 2: summarize_facts  (WS: "📋 사실 정리 중...")
────────────────────────────────────────────────────
입력:  원고·피고 메시지들
LLM:   "양측 주장을 요약하고 핵심 쟁점을 JSON으로"
출력:  plaintiff_summary, defendant_summary, key_issues[]

노드 3: judge  (WS: "🔍 유사 판례 검색 중..." → "⚖️ 판결 중...")
────────────────────────────────────────────────────
입력:  summary, emotion, key_issues, judge_style
1단계: judge_style에 따라 프롬프트 선택
       "default" → judge_default_prompt.py (차분한 톤)
       "spicy"   → judge_spicy_prompt.py  (독설 톤)
2단계: LLM 1차 호출 → AI가 스스로 search_similar_verdicts 도구 호출
3단계: pgvector로 유사 판례 3개 검색
4단계: LLM 2차 호출 → 판례 참고해서 최종 판결문 작성
출력:  judgment

노드 4: determine_ratio  (WS: "📊 잘못 비율 계산 중...")
────────────────────────────────────────────────────
입력:  judgment (판결문)
LLM:   "판결문을 읽고 원고/피고 잘못 비율을 JSON으로 (합계 100)"
출력:  plaintiff_ratio, defendant_ratio

노드 5: generate_missions  (WS: "🤝 화해 미션 생성 중...")
────────────────────────────────────────────────────
입력:  judgment, plaintiff_ratio, defendant_ratio
LLM:   "화해 미션 3가지를 JSON으로"
출력:  missions[]
```

**판결 완료 후:**
```python
broadcast_done(case_id)   # WS "done" 전송 → 프론트 자동 전환
DB: Verdict 저장, Case.status = JUDGED
이메일 발송
벡터 임베딩 저장
```

---

## 7. WebSocket 실시간 진행 상태

### 파일: `app/core/trial_ws.py`, `app/routers/trial_ws.py`, `frontend/src/pages/VerdictPage.jsx`

**연결 흐름:**
```
VerdictPage 진입
    ↓
먼저 GET /verdicts/{id} 시도
  ├─ 성공 (이미 JUDGED) → 판결 화면 바로 표시
  └─ 실패 (404) → WebSocket 연결
                     WS /ws/trial/{case_id}?token=JWT
                          ↓
           {"type": "progress", "step": 1, "total": 6, "message": "⚖️ 감정 분석 중..."}
           {"type": "progress", "step": 2, ...}
           ...
           {"type": "done", "message": "✅ 판결 완료!"}
                          ↓
           600ms 후 loadVerdict() → 판결 화면 전환
```

**WS 실패 시 폴링 폴백:**
```javascript
ws.onerror = () => {
  // 2초마다 GET /verdicts/{id} 폴링 재시도
};
```

**TrialProgressManager (싱글턴):**
```python
# app/core/trial_ws.py
_connections: dict[str, list[WebSocket]] = {}
# case_id 당 여러 WS 연결 관리 (새로고침하면 이전 연결 + 새 연결 공존 가능)

async def broadcast(case_id, step, total, message):
    # 연결된 모든 WS에 전송, 실패한 연결은 무시
```

**진행 상태 UI (VerdictPage ProgressScreen):**
```
Scale 아이콘 (애니메이션)
"AI 판사 심의 중"
"📋 사실 정리 중..."  ← 실시간 변경
━━━━━━━━━━━━━━━━━━━━━━  ← 프로그레스 바 (step/total * 100%)
● ● ○ ○ ○ ○          ← 단계 도트
"2 / 6 단계 완료"
```

---

## 8. 벡터 DB란 무엇이고 어떻게 쓰이나

### 일반 DB vs 벡터 DB

**일반 DB (PostgreSQL)**
```
"약속" 검색 → "약속"이 포함된 것만 찾음
단어가 다르면 못 찾음
```

**벡터 DB (pgvector)**
```
"약속을 안 지킴" 검색 →
"연락이 없었음", "약속 파기", "카톡 무시" 같은
의미가 비슷한 것도 찾을 수 있음
```

### 어떻게 동작하나?

**1단계: 텍스트 → 벡터 변환**
```
"약속을 안 지킴"
    ↓  OpenAI text-embedding-3-small
[0.053, 0.072, -0.018, ...] ← 1536개 숫자
```
의미가 비슷한 문장은 비슷한 숫자 배열이 나온다.

**2단계: pgvector에 저장**
```
판결 완료 → app/services/similarity.py → save_verdict_embedding()
판결문 텍스트를 벡터로 변환 → verdict_embeddings 테이블에 저장
```

**3단계: 유사 판례 검색 (Tool Use)**
```python
# app/langgraph/nodes.py - search_similar_verdicts Tool
query_vector = await embeddings.aembed_query(query)

sql = """
    SELECT ve.case_id,
           1 - (ve.embedding <=> CAST(:query_vector AS vector)) AS similarity
    FROM verdict_embeddings ve
    ORDER BY ve.embedding <=> CAST(:query_vector AS vector)
    LIMIT 3
"""
```

**4단계: 통계 싸움 유형 분류**
```python
# app/routers/stats.py
# 5개 카테고리 텍스트를 벡터화 (첫 요청에만, 이후 캐싱)
FIGHT_CATEGORIES = {
    "연락 문제": "카톡 답장 안함 전화 안 받음...",
    "약속 파기": "약속 취소 지각...",
    ...
}
# 판결문 벡터와 각 카테고리 벡터의 코사인 유사도 비교 → 가장 유사한 카테고리 배정
```

---

## 9. 판결 결과 화면

### 파일: `app/routers/verdict.py`, `frontend/src/pages/VerdictPage.jsx`

**승소/패소 판단:**
```javascript
const myRatio = isPlaintiff ? verdict.plaintiff_ratio : verdict.defendant_ratio;
const isWinner = myRatio < 50;   // 내 잘못이 50% 미만이면 승소
const isDraw   = verdict.plaintiff_ratio === verdict.defendant_ratio;
```

**유사 판례 조회:**
```
GET /verdicts/{case_id}/similar
    ↓
현재 판결문을 벡터로 변환 → pgvector로 유사 사건 3개 검색
    ↓
화면 하단에 "유사 판례" 섹션 표시
```

**"우리 통계 보기" 버튼:**
```
판결 결과 하단 → Link to="/stats/{caseId}"
```

---

## 10. 이메일 자동 발송

### 파일: `app/langgraph/graph.py`, `app/services/email.py`

```python
# broadcast_done() 직후 실행
await send_verdict_to_both(
    plaintiff_email, plaintiff_nickname,
    defendant_email, defendant_nickname,
    case_title, plaintiff_ratio, defendant_ratio,
    judgment, missions
)
```

**Gmail 앱 비밀번호 설정 방법:**
1. Google 계정 → 보안 → 2단계 인증 활성화
2. 앱 비밀번호 생성 → 16자리 코드 복사
3. `.env`의 `MAIL_PASSWORD`에 공백 포함 그대로 입력

**발송 확인:**
```bash
docker compose logs api | grep "\[EMAIL\]"
```

---

## 11. 커플 통계 (StatsPage)

### 파일: `app/routers/stats.py`, `frontend/src/pages/StatsPage.jsx`

**데이터 조회 흐름:**
```
GET /stats/{case_id}
    ↓
두 유저(원고/피고)가 함께한 모든 JUDGED 사건 조회
역할이 바뀐 경우도 포함 (양방향 쿼리)
    ↓
asyncio.gather로 모든 사건의 싸움 유형 병렬 분류
    ↓
{
  totalCases: 5,
  avgPlaintiffRatio: 42.5,
  avgDefendantRatio: 57.5,
  trend: [{caseId, title, date, plaintiffRatio, defendantRatio}, ...],
  fightTypes: [{type: "연락 문제", count: 2}, ...]
}
```

**싸움 유형 분류 (pgvector 활용):**
```python
# 카테고리 임베딩은 모듈 수준 딕셔너리에 캐싱 (첫 요청에만 API 호출)
_category_vecs: dict[str, list[float]] = {}

async def _classify(title, judgment) -> str:
    case_vec = await embeddings.aembed_query(f"{title}. {judgment[:200]}")
    # 5개 카테고리와 코사인 유사도 비교 → 가장 높은 것 반환
```

**Recharts 차트 3종:**
```
파이차트  → 원고/피고 평균 잘못 비율 (도넛형)
라인차트  → 재판별 잘못 비율 추이 (2회 이상일 때 표시)
바차트    → 싸움 유형별 빈도
```

**진입 경로:**
```
VerdictPage 하단 "📊 우리 통계 보기" 버튼 → /stats/{caseId}
```

---

## 12. 확인하는 방법 (로그 / DB)

### API 로그 보기

```bash
docker compose logs api -f                          # 실시간 스트리밍
docker compose logs api --tail=50                   # 최근 50줄
docker compose logs api | grep "Task exception"     # 판결 에러
docker compose logs api | grep "\[EMAIL\]"          # 이메일 발송 결과
docker compose logs api | grep "POST /cases"        # 제출 이벤트
```

### DB 직접 확인

```bash
docker compose exec db psql -U postgres -d couple_trial
```

```sql
-- 테이블 목록
\dt

-- 사건 상태 확인
SELECT title, status, judge_style, plaintiff_submitted, defendant_submitted
FROM cases ORDER BY created_at DESC;

-- 판결 결과
SELECT plaintiff_ratio, defendant_ratio, LEFT(judgment, 100)
FROM verdicts WHERE case_id = '사건ID';

-- 벡터 저장 확인
SELECT case_id FROM verdict_embeddings;

-- 커플의 전체 재판 이력
SELECT c.title, c.status, v.plaintiff_ratio, v.defendant_ratio
FROM cases c
LEFT JOIN verdicts v ON c.id = v.case_id
WHERE c.plaintiff_id = '유저ID' OR c.defendant_id = '유저ID'
ORDER BY c.created_at;

\q
```

### API 직접 테스트

```
http://localhost:8000/docs    # Swagger UI (직접 API 호출 가능)
http://localhost:8000/redoc   # ReDoc 문서
```

---

## 자주 생기는 문제

| 증상 | 원인 | 해결 |
|------|------|------|
| 판결이 안 남 | OpenAI API 에러 | `docker compose logs api \| grep "Task exception"` |
| WS 연결 안 됨 | CORS 또는 토큰 문제 | 브라우저 콘솔 → WS 오류 메시지 확인, 폴링 폴백 동작 여부 확인 |
| 이메일 안 옴 | 환경변수 미설정 | `docker compose exec api env \| grep MAIL` |
| 통계 페이지 빈 화면 | 완료된 재판 없음 | 같은 두 유저가 최소 1회 판결 완료해야 함 |
| DB 컬럼 에러 | judge_style 컬럼 미반영 | `docker compose down -v && docker compose up` |
| 메시지 차단됨 | AI 모더레이션 정상 작동 | 욕설/비방 포함 시 정상 차단 |
