# 영양제 첫걸음

다이소 영양제를 처음 고르는 성인을 위한 **설문 추천 · 두 제품 비교 · 출처 있는 AI 상담** 웹 서비스.

**[서비스 열기](https://vitastep-guide.onrender.com/)** · [기획서](docs/project-plan.md) · [기능 요구 명세서](docs/functional-requirements.md) · [피드백 기록](docs/user-feedback.md) · [발표 자료](docs/presentation.pdf)

![홈 화면](docs/screenshots/vitastep-home.png)

> 다이소의 공식·제휴 서비스가 아닌 학습 프로젝트입니다. 진단·처방·개인별 복용량·의약품 병용 판단은 하지 않습니다.

## 목차

1. [무엇을 하는 앱인가](#1-무엇을-하는-앱인가)
2. [왜 만들었나](#2-왜-만들었나)
3. [기술 스택](#3-기술-스택)
4. [개발 중 이슈와 해결](#4-개발-중-이슈와-해결)
5. [팀원과 라이선스](#5-팀원과-라이선스)
6. [사용 설명서](#6-사용-설명서)

## 1. 무엇을 하는 앱인가

매장이나 다이소몰에서 영양제를 보다가 폰으로 열어, 사기 전에 표시를 이해하고 후보를 좁히는 데 쓴다. 계정은 없다.

| 기능 | 하는 일 |
|---|---|
| **추천받기** | 5단계 설문(관심 분야 · 식습관 · 이미 먹는 제품 · 주의조건 · 예산/제형) → 서버 규칙이 후보 최대 3개를 고르고, AI가 왜 이 후보인지 출처를 들어 설명 |
| **AI에게 물어보기** | 질문을 보고 모델이 도구 7개 중 필요한 것을 골라(Agent) 제품 표시·영양 지식을 검색(RAG)한 뒤 출처가 붙은 답을 냄. 근거가 없으면 "찾지 못했다"고 말함 |
| **비교하기** | 두 제품의 표시를 한 표로 놓고 차이만 보기. 원하면 AI 차이 해설 |
| **제품 찾기** | 검수한 87개 제품의 성분 · 함량 · 기준 · 섭취법 · 주의 · 알레르기 · 출처 URL · 관찰일 |
| **중복 확인** | 이미 먹는 제품끼리 겹치는 성분과 하루 표시 합계(예: 마그네슘 315 mg + 315 mg = 630 mg) |

제품 정보는 다이소몰 공식 표시를 88개 전부 사람이 대조해 넣었고(공개 87, 보류 1), 일반 영양 지식은 NIH ODS(미국 국립보건원 보충제 사무국)와 식약처 공개 자료 12종을 카드 35장으로 정리했다. 모든 값에 출처와 관찰일이 붙어 있다.

## 2. 왜 만들었나

영양제가 약국이 아니라 다이소 매대에 3천~5천 원으로 놓이면서 "하나 먹어 볼까" 하는 사람이 많아졌다. 그런데 막상 매대 앞에 서면 같은 비타민B가 정제·구미·분말, 10일분·30일분으로 여섯 가지쯤 갈라져 있고, "315mg"이나 "영양성분 기준치 100%"가 무슨 뜻인지 설명해 주는 곳은 없다. 검색하면 광고와 체험담이 먼저 나온다.

우리가 풀고 싶었던 것은 "무엇을 먹어야 건강해지는가"가 아니다. 그건 우리가 답할 수 있는 질문이 아니다. 풀고 싶었던 것은 **사기 전에 표시를 읽고 후보를 좁히는 10분**이다. 그래서 세 가지를 원칙으로 정했다.

- **출처 없는 말은 하지 않는다.** AI 답변의 인용은 서버가 검색 결과와 대조하고, 검색 풀 밖의 출처가 나오면 답을 버린다. 근거가 없으면 모른다고 한다.
- **추천은 규칙이 하고 AI는 설명만 한다.** 같은 설문에는 같은 후보가 나와야 믿을 수 있다. AI가 죽어도 후보는 나온다.
- **건강 개인정보는 받지도 보내지도 않는다.** 설문은 선택지만, 대화에 병명·약 이름이 적히면 AI로 보내지 않고 안내로 끝낸다.

## 3. 기술 스택

| 층 | 선택 | 왜 |
|---|---|---|
| 프런트 | React 19 · TypeScript · Vite | 매장에서 폰으로 쓰는 단일 화면. 정적 빌드라 무료 호스팅 |
| 서버 | Python 3.13 · FastAPI · Pydantic | 수집·검수 스크립트가 Python이라 같은 언어로. 설문 값을 서버에서 검증 |
| 데이터 | SQLite(읽기 전용) + JSON | 제품 88개 규모라 DB 서버 불필요. 파일째 Git과 Docker 이미지에 들어감 |
| AI | 코디세이 COPA `gpt-5.4` · OpenAI Python SDK | 과정 제공 API라 평가 기간 할당량 걱정 없음. 함수 호출·구조화 출력 사용 |
| 배포 | Render 무료 Static Site + Docker Web Service | `production` 브랜치에 병합하면 자동 배포 |
| 품질 | pytest 171 · Node 테스트 23 · 데이터 검사 14,587건 · GitHub Actions | AI 키 없이 PR마다 CI 4개 |

```
[브라우저 React SPA] ──HTTPS──▶ [FastAPI · Render Docker]
  동의 · 설문 · 추천                 policy.py     규칙 추천 · 성분 중복
  제품 찾기 · 상세 · 비교             repository.py SQLite 검색(RAG)
  AI 대화                            knowledge.py  영양 지식 카드 검색(RAG)
                                     agent.py      도구 선택 → 검색 → 인용 검증
                                     privacy.py    건강 개인정보 차단
                                            │ 걸러진 질문 + 검색 결과만
                                            ▼
                                     [코디세이 COPA gpt-5.4]
```

브랜치는 `main`(초기 프로토타입 보존) 아래 **`canary → dev → production`**으로 승격한다. 개발은 `canary`, CI 통과 후 `dev`, 운영 확인 뒤 `production`. `dev`·`production`은 PR과 CI 4개 통과가 필수이고 강제 push·삭제가 막혀 있다. 자세한 규칙은 [CONTRIBUTING.md](CONTRIBUTING.md).

## 4. 개발 중 이슈와 해결

일주일 동안 부딪힌 것 중 코드와 기록이 남은 것만 적는다.

**첫 질문이 503을 냈다.** 시작 질문 "함량과 기준량의 차이가 궁금해요"는 개념 질문인데, 검색이 상품 표시 원문만 뒤져서 "함량"이라는 낱말이 없었고, 결과 없음을 서버 장애로 돌려줬다. 표시 읽기 개념을 설명하는 공식 안내 경로(`backend/label_guide.py`)를 따로 두고, 진짜 근거가 없을 때는 오류가 아니라 "질문을 구체화해 달라"는 200 응답으로 바꿨다. → [docs/chat-label-reading-fix.md](docs/chat-label-reading-fix.md), 커밋 `c8fa914`

**Gemini 무료 키가 평가 기간을 못 버텼다.** 멘토링 다음 날 과정에서 제공하는 코디세이 COPA(OpenAI 호환)로 바꿨다. 그런데 COPA가 `tool_choice=required`와 `response_format=json_schema`를 거부해서, 도구 선택은 `auto`로 두고 첫 응답에 도구 호출이 없으면 실패로 처리하며, 답 형식은 메시지로 지시하고 서버의 Pydantic이 검증하도록 했다. 어떤 옵션이 되고 안 되는지는 실제 호출로 확인해 JSON으로 남겼다. → [docs/codyssey-gpt.md](docs/codyssey-gpt.md), PR #3

**AI가 없는 출처를 인용할 수 있었다.** 답을 구조화 JSON(`text` · `citationIds` · `productIds`)으로만 받고, 인용 ID가 이번 검색 풀에 없으면 답을 버린다(`AI_INVALID_EVIDENCE`). 근거 0이면 "아직 공식 근거를 찾지 못했다"고 안내한다. 실패를 성공처럼 포장하지 않는 게 이 서비스의 핵심이라 여기엔 예외를 두지 않았다. → `backend/agent.py`

**"일상의 활력"에 마그네슘이 나왔다.** 성분 연결로 후보를 고르니 관련 성분이 넓게 끌려오고, 포장만 다른 제품이 나란히 나왔다. 표시상 직접 목적(활력은 비타민B군)과 관련 성분을 나누어 후보는 직접 목적에서만 고르고, 브랜드·제형·하루 정량이 같은 변형은 묶어 대표 1개만 올렸다. 부족한 분야는 개수를 채우려 승격하지 않고 "부족하다"고 말한다. → [docs/recommendation-policy-v2.md](docs/recommendation-policy-v2.md), 커밋 `b75f847`

**사용자가 병명을 적으면 외부 AI로 나간다.** 서버 정규식이 질환·약 이름·"저는 ~복용 중" 같은 문장을 먼저 잡아 AI로 보내지 않고 로컬 안내만 낸다. 설문의 주의조건·식습관도 AI에 전송하지 않는다. → `backend/privacy.py`

**브랜치가 `main` 하나였다.** 멘토링에서 감점 항목이라고 지적받았다. `canary → dev → production` 3단계와 GitHub Rulesets 3개(이력 보호 · 소유자 관리 · 통합 검사), CI 4개, PR 템플릿을 하루에 세웠다. → [CONTRIBUTING.md](CONTRIBUTING.md), PR #1 · #2

**무료 서버가 첫 접속에 1분 자다.** 처음 여는 사람에게는 고장처럼 보였다. 프런트가 75초까지 2초 간격으로 재시도하며 "서버를 깨우고 있어요"를 보여 주고, 서버 재시작으로 동의 세션이 사라지면 다시 동의하도록 안내한다. → `frontend/src/connection.ts`

## 5. 팀원과 라이선스

| 팀원 | 배정 역할 | 확인된 기여 근거 |
|---|---|---|
| 이승현 | **주 개발**: 프런트·백엔드·AI 추천 공동 개발 주도, 통합·운영 관리 | 본인 계정 `sayknow`, [PR #3](https://github.com/sayknow/M2-1/pull/3)·[PR #4](https://github.com/sayknow/M2-1/pull/4)·[PR #5](https://github.com/sayknow/M2-1/pull/5)·[PR #6](https://github.com/sayknow/M2-1/pull/6) |
| 김재욱 | 자료 수집·검수·RAG 자료 정리 | 역할 배정. 본인 요약·개인 수행 링크 보완 필요 |
| 윤준서 | 기획·요구 명세·설계 문서 | 역할 배정. 본인 요약·개인 수행 링크 보완 필요 |
| 배창민 | 테스트·피드백·진행 문서 | 역할 배정. 본인 요약·개인 수행 링크 보완 필요 |
| 조준수 | **부 개발**: 프런트·백엔드·AI 추천 공동 개발, 구현/검증 보조 | 개발 참여를 팀이 확인. 본인 요약·개인 수행 링크 보완 필요 |

[팀원별 상세 역할·증빙 표](docs/final/team-contributions.md). 역할 배정과 실제 개인 작성 이력을 구분한다. 현재 모든 커밋/PR 계정이 `sayknow`이므로 타인의 개인 작성 이력으로 임의 배정하지 않았다.

**라이선스**: 이 저장소의 코드와 문서는 [MIT License](LICENSE)를 따른다. 단, `data/products/`의 제품 표시·가격 데이터와 제품 사진은 다이소몰 공식 상품 페이지에서 가져온 것으로 출처 표기만 했으며 MIT 대상이 아니다. 영양 지식 카드의 원문은 NIH ODS·식약처 공개 자료다.

## 6. 사용 설명서

### 그냥 써 보기

[https://vitastep-guide.onrender.com/](https://vitastep-guide.onrender.com/) 에 접속한다. 계정은 없다. 첫 접속은 서버가 깨어나는 1분 정도를 기다린다. 제품 찾기·상세·비교는 바로 되고, 추천·AI 대화는 동의 3개(성인 · 정보 처리 · AI 전송) 뒤에 된다. 실제 질환·복용 약은 적지 않는다.

### 로컬에서 돌리기

필요한 것: Python 3.11 이상(검증 3.13), Node 22.12 이상(검증 24), 코디세이 COPA 키(AI 기능에만 필요. 없어도 제품 조회·규칙 추천은 됨).

```sh
git clone https://github.com/sayknow/M2-1.git
cd M2-1

# 1) 서버 의존성
python -m venv .venv
.venv/bin/python -m pip install -r backend/requirements.lock     # Windows: .venv\Scripts\python

# 2) 키 설정 — 루트 .env 하나뿐. 프런트 VITE_ 변수에는 넣지 않는다
cp .env.example .env                                              # Windows: copy .env.example .env
#    .env의 COPA_API_KEY= 오른쪽에 본인 키를 적는다

# 3) 서버 (터미널 1)
.venv/bin/python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --no-access-log

# 4) 화면 (터미널 2)
cd frontend
npm ci
npm run dev -- --port 5173
```

브라우저에서 `http://127.0.0.1:5173/`을 연다. API 문서는 `http://127.0.0.1:8000/docs`. 포트를 바꾸면 프런트 `VITE_API_BASE_URL`과 서버 `.env`의 `ALLOWED_ORIGINS`를 맞춘다.

### 검사

AI 키 없이 전부 돌아간다. Windows에서는 pytest 앞에 `set PYTHONUTF8=1`(PowerShell은 `$env:PYTHONUTF8=1`)을 둔다.

```sh
.venv/bin/python -m pytest -q                      # 서버 171
python scripts/validate_product_database.py        # 데이터 14,587건
cd frontend && npm test && npm run build           # 화면 23 + 빌드
```

### 폴더

```
backend/     FastAPI · agent.py(도구 7개) · policy.py(규칙 추천) · repository.py · knowledge.py · privacy.py · tests/
frontend/    React · src/App.tsx · services.ts · connection.ts · tests/
data/        products.sqlite3(검수 DB) · recommendation/classification-v2.json
docs/        기획서 · 명세서 · 피드백 기록 · 발표 자료 · 개발 기록 · screenshots/
scripts/     데이터 검증 · 운영 API 점검
```

문서 기준일 2026-10-24 · 운영 브랜치 `production` · 제품 표시 관찰일 2026-10-19
