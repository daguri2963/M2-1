# 영양제 첫걸음

다이소 영양제를 처음 고르는 성인을 위한 공식 제품 정보·설문 기반 후보 추천·비교·AI 대화 서비스입니다. 다이소와 제휴한 공식 서비스가 아닌 학습 프로젝트입니다. 질환 진단·치료·개인별 용량 처방은 제공하지 않습니다.

## 개발 참여와 운영 관리

`main`은 기준 프로토타입으로 보존하며 **`canary → dev → production`** 순서로 반영합니다. 대표 브랜치와 Render 배포 기준은 `production`입니다. 소유자 `sayknow`가 통합·운영을 관리하고, 쓰기 권한을 받은 팀원은 `canary`에서 참여합니다. 삭제·강제 푸시 보호와 필수 자동 검사를 적용하며 다른 팀원의 승인은 필수가 아닙니다. 별도 시험 서버는 만들지 않습니다. [참여 방법·권한·배포 절차](CONTRIBUTING.md)를 먼저 확인하세요.

## canary: 코디세이 GPT 전환 준비

현재 canary 코드는 코디세이의 `gpt-5.4` Chat Completions를 사용하도록 변경 중입니다. 실제 키 검증 전이며 운영 홈페이지는 기존 Gemini 버전을 유지합니다. 프로젝트 루트 `.env`의 `COPA_API_KEY=`에 가상 키를 입력하는 방법과 검증 명령은 [코디세이 GPT 연결 안내](docs/codyssey-gpt.md)를 확인하세요. DB·추천 정책은 유지하며 dev·production 반영은 실제 호환 검증 이후 진행합니다. 아래 Gemini 실행 결과는 기존 운영 버전의 기록입니다.

## 현재 구현

- 공식 표시 검수 완료 **87개**를 SQLite에서 조회합니다. 전체 수집 88개 중 보류 1개는 공개 목록에서 제외합니다.
- 다이소몰 공식 썸네일 88개를 확보하고 공개 제품 87개의 실제 사진을 연결했습니다.
- 관심 분야·기존 제품·주의조건·예산·제형을 반영해 최대 3개 후보와 표시 근거를 제시합니다. 조건 부족·추천 제한·빈 결과를 구분합니다.
- 기존 제품의 표시 성분 중복을 검사하고, 확인 가능한 하루 기준·단위에서만 합산합니다. 병용 안전성 판정은 하지 않습니다.
- 두 제품의 가격·성분·기준량·섭취방법·주의사항을 실제 서버에서 비교합니다.
- 영양제 AI 상담가가 검수 제품과 공식 영양 지식을 검색해 성분 역할·식사·보관·일반 주의사항을 설명합니다. 주요 성분 10종, 지식 35항목과 표시 읽기 안내를 사용하며 개인별 복용 판단·실제 건강정보는 서버에서 별도로 처리합니다. 초기 연결·AI 생성·실패·재시도를 구분합니다.
- 모바일 중심 홈·설문·결과·상세·비교·AI 대화, 성인·개인정보·AI 전송 동의와 입력 초기화를 제공합니다.

실제 Gemini 키로 도구 호출·근거 검색·응답 검증을 확인했습니다. **[배포된 서비스 열기](https://vitastep-guide.onrender.com/)** — Render 무료 홈페이지와 백엔드에 배포하고 외부 API에서도 실제 Gemini 추천·대화를 확인했습니다. 실제 타깃 사용자 5명 피드백·개선은 후속 단계입니다. 초기 기획서·기여 기록·발표 자료는 실제 최종 수행 결과에 맞춰 보완해야 합니다.

평가자는 위 홈페이지로 접속하면 됩니다. 별도 로그인 계정은 필요 없으며, 추천·대화 전 이용 안내에 동의해야 합니다. 백엔드가 대기 상태라면 처음 연결에 약 1분이 걸릴 수 있으며 화면의 준비 안내 뒤 자동으로 이어집니다. 과제 결과 안내를 받을 때까지 서비스를 유지합니다.

## 기술 선택

| 구성 | 선택 이유 |
|---|---|
| React·TypeScript·Vite | 기존 모바일 UI 유지, 입력·응답 형식 검사, 정적 배포 가능 |
| Python·FastAPI | 기존 데이터 작업과 언어 통일, 입력 검증·비동기 AI 연결·API 문서 |
| SQLite | 88개 규모의 검수 DB 재사용, 별도 DB 서버 없이 읽기 전용 배포 |
| OpenAI Python SDK | 코디세이 호환 함수 호출과 구조화 출력 연결 |
| Gemini 3.5 Flash Lite | 실제 계정에서 도구·출처 검증을 확인하고 상품 설명 응답 지연을 줄이기 위해 선택 |

## 로컬 실행

Python 3.11 이상(검증: 3.13), Node.js 22.12 이상(검증: 24)이 필요합니다.

```sh
# 저장소 루트에서 최초 한 번
python3 -m venv .venv
.venv/bin/python -m pip install -r backend/requirements.lock
# .env가 없는 경우에만 예시를 복사하고 서버용 Gemini 키를 직접 입력
cp -n .env.example .env
```

canary의 코디세이 키는 루트 `.env`의 `COPA_API_KEY`에 저장합니다. 값은 대화·로그·소스에 복사하지 않습니다. `.env`는 Git 제외 대상이며 프런트의 `VITE_` 변수에 비밀키를 넣지 않습니다. 모델은 `COPA_MODEL`로 설정합니다. 키를 변경하면 백엔드를 다시 실행합니다.

```sh
# 터미널 1: 백엔드
.venv/bin/python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --no-access-log
```

```sh
# 터미널 2: 프런트엔드
cd frontend
npm ci
npm run dev -- --port 5173
# 완성 빌드 미리보기
npm run build
npm run preview -- --port 4173
```

[개발 화면](http://127.0.0.1:5173/) · [완성 화면](http://127.0.0.1:4173/) · [API 문서](http://127.0.0.1:8000/docs).

로컬 UI는 기본 8000번 백엔드에 연결합니다. 외부 정적 배포는 `frontend/.env.example`의 공개 `VITE_API_BASE_URL` 설정과 서버 `ALLOWED_ORIGINS`를 맞춥니다. 상품 DB는 배포 파일에 포함하며 Dockerfile도 제공합니다. 현재 Render 배포 설정·사용량·재현 절차는 [외부 배포 기록](docs/deployment.md)을 참고합니다.

## 검증

```sh
# 저장소 루트: 키 없이 실행 가능한 자동 검사
.venv/bin/python -m pytest -q
python3 scripts/validate_product_database.py
python3 scripts/validate_product_thumbnails.py
cd frontend
npm test
npm run build
```

```sh
# 저장소 루트: 실제 Gemini 호출 (API 사용량 발생)
.venv/bin/python scripts/check_copa_compatibility.py --run-live
# 로컬 백엔드를 켠 상태의 전체 HTTP 검사
.venv/bin/python scripts/check_backend.py
```

실제 사용자 건강정보 대신 가상 선택지와 공개 상품으로 확인합니다. 자동 검사는 영양학·임상 검증이나 독립 제2검수를 의미하지 않습니다. 결과와 재현 방법은 [백엔드 검증 기록](docs/backend-test-results.md)에 있습니다.

## 문서와 데이터

- [핵심8개 기능 요구·평가 재현](docs/functional-requirements.md)
- [추천 정책·지원 범위·정량 규칙](docs/recommendation-policy.md)
- [시스템 구조·API·Gemini·RAG·정보 처리](docs/backend-api.md)
- [외부 배포·평가자 접속·사용량](docs/deployment.md)
- [영양제 AI 상담가·지식 출처·질문 구분·평가](docs/ai-counselor.md)
- [화면 설계와 이동 흐름](docs/ui-design.md)
- [검수 DB와 출처](docs/product-database.md)
- [표시정보 검수 보고](docs/product-label-review.md)
- [공식 썸네일 수집·검증](docs/product-thumbnails.md)
- [프런트 검증 기록](docs/frontend-test-results.md)
- [초기 기획서](docs/project-plan.md) — 초기 제안·이전 진행 상태는 당시 기록입니다.

공식 표시·가격 관찰은 주로 2026-10-19, 표시 검수는 2026-10-19~20, 사진 확인은 2026-10-21입니다. 실시간 가격·재고가 아니며 자료 날짜를 일괄 현재 날짜로 바꾸지 않습니다. 사진 수집과 표시 검수, 추천 정책의 후보 평가는 서로 구분합니다.

## 소스 구조

```text
backend/main.py             API·동의·임시 연결·오류 처리
backend/repository.py       읽기 전용 검수 SQLite 조회·비교·근거 검색
backend/policy.py           후보 선정·제한·성분 중복·정량 기준
backend/agent.py            Gemini 도구 실행 루프·인용/응답 검증
backend/privacy.py          제공자 전송 최소화·로컬 입력 제한
backend/tests/              규칙·API·Agent·개인정보 경계 검사
frontend/src/App.tsx        화면·설문·결과·비교·대화·철회
frontend/src/services.ts    실제 HTTP 연결·메모리 세션
frontend/src/connection.ts  최초 서버 기동 대기·재시도
frontend/public/            검수 완료 상품의 공식 썸네일
scripts/                   원본 수집·DB 재생성·무결성·실제 연결 검사
```

설문·대화는 브라우저 메모리에 두며 새로고침·입력 초기화로 삭제합니다. 서버는 건강 입력·대화 원문을 영구 저장하지 않습니다. Google의 처리 범위는 서비스 서버와 다르므로 이용 전 동의 안내를 확인해야 합니다. Gemini가 없거나 실패해도 정적 예시를 실제 AI 응답으로 보여주지 않습니다.
