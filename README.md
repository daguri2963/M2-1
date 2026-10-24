# 영양제 첫걸음

다이소 영양제를 처음 고르는 성인을 위한 **설문 후보 추천·제품 비교·AI 대화·제품 찾기** 서비스다. 공식 표시와 일반 영양 지식을 검색해 선택을 돕는다. 다이소의 공식/제휴 서비스가 아닌 학습 프로젝트이며 진단·처방·개인별 복용량 조절·병용 안전성 판단을 제공하지 않는다.

**[운영 사이트](https://vitastep-guide.onrender.com/)** · **[최종 제출 문서 전체](docs/final/README.md)** · [공개 저장소](https://github.com/sayknow/M2-1)

문서 기준일2026-10-24 / 운영 코드 `0bc17dc` / 운영 브랜치 `production`. 운영 AI는 **코디세이 COPA의 `gpt-5.4`**다. 이전 Gemini 버전은 진행 이력으로 보존한다.

## 1. 프로젝트 개요

성분·함량·기준량과 비슷한 제품의 차이를 이해하기 어려운 초보자를 대상으로 한다. 모바일 중심 5단계 설문 → 후보 → 표시 근거 → 상세·비교·대화 흐름을 구현했다. 관심 분야는 **일상의 활력, 뼈·근육 건강, 장 건강, 혈당 관리, 다이어트**다.

- 공식 상품88개 중 표시 검수87개를 공개하고 보류1개를 제외한다. 썸네일88개 확보, 공개87개에 연결했다.
- 표시·목적 분류·기존 제품·주의조건·예산·제형으로 최대3개 후보를 고른다. 모름·제한·빈 결과를 구분하며 모두 함께 섭취하라는 뜻은 아니다.
- 같은 성분의 등록 제품 중복과 계산 가능한 하루 표시 합계를 확인한다. 두 제품의 표시표와 선택적 AI 차이 해설을 제공한다.
- **AI Agent + RAG:** GPT가 도구를 선택하고 질의별 SQLite/공식 지식을 검색해 출처를 설명한다. 후보 선정은 서버 규칙이며 임베딩·벡터 DB·사용자 장기 메모리는 사용하지 않는다.
- 가입 계정은 없다. 제품 찾기·상세·표시 비교는 공개이며 추천·대화·AI 비교 해설은 이용 안내에 동의한다. 서버 준비/AI 생성/실패·재시도를 구분한다.

가격·표시는 주로2026-10-19 관찰, 라벨 검수10-19~20, 사진 확인10-21 자료다. 실시간 가격·재고가 아니며 독립 임상 검증이 아니다.

## 2. 팀원 역할

| 팀원 | 배정 역할 | 확인된 기여 근거 |
|---|---|---|
| 이승현 | **주 개발**: 프런트·백엔드·AI 추천 공동 개발 주도, 통합·운영 관리 | 본인 계정`sayknow`, [PR #3](https://github.com/sayknow/M2-1/pull/3)·[PR #4](https://github.com/sayknow/M2-1/pull/4)·[PR #5](https://github.com/sayknow/M2-1/pull/5)·[PR #6](https://github.com/sayknow/M2-1/pull/6) |
| 김재욱 | 자료 수집·검수·RAG 자료 정리 | 역할 배정. 본인 요약·개인 수행 링크 보완 필요 |
| 윤준서 | 기획·요구 명세·설계 문서 | 역할 배정. 본인 요약·개인 수행 링크 보완 필요 |
| 배창민 | 테스트·피드백·진행 문서 | 역할 배정. 본인 요약·개인 수행 링크 보완 필요 |
| 조준수 | **부 개발**: 프런트·백엔드·AI 추천 공동 개발, 구현/검증 보조 | 개발 참여를 팀이 확인. 본인 요약·개인 수행 링크 보완 필요 |

[팀원별 상세 역할·증빙 표](docs/final/team-contributions.md). 역할 배정과 실제 개인 작성 이력을 구분한다. 현재 모든 커밋/PR 계정이sayknow이므로 타인의 개인 작성 이력으로 임의 배정하지 않았다.

## 3. 기술 스택과 구조

| 구성 | 선택 | 이유 |
|---|---|---|
| 프런트 | React·TypeScript·Vite | 모바일 화면·타입 기반 연결·정적 배포 |
| 서버 | Python·FastAPI·Pydantic | 데이터 언어 재사용·입력 검증·비동기 AI |
| 데이터 | SQLite 읽기 전용 + 분류/지식 JSON | 작은 검수 DB를 별도 DB 서버 없이 배포·버전 관리 |
| AI | OpenAI Python SDK → COPA → GPT-5.4 | 제공 키·도구 호출의 실제 호환성 검증 |
| 배포/품질 | Render 정적 사이트·Docker API, GitHub Actions | 소규모 운영·로컬 검증·승격 검사 |

[시스템 구조](docs/final/architecture.md)·[AI 설계와 코드 위치](docs/final/ai-design.md). 핵심 파일은 `backend/main.py`(API/동의), `repository.py`(DB/RAG), `policy.py`(추천/중복), `agent.py`(도구/답변), `comparison.py`(비교 해설), `privacy.py`(정보 경계), `frontend/src/App.tsx`(화면), `services.ts`(HTTP)다.

`main`은 초기 프로토타입 보존, **`canary → dev → production`**으로 승격한다. canary 로컬 검사·CI 뒤 dev, 관리자 확인 후 production으로 병합한다. 별도 시험 서버는 없다. [참여/보호 규칙](CONTRIBUTING.md)·[운영/복구](docs/final/security-and-operations.md)를 따른다.

## 4. 실행 방법과 평가자 접속

평가자는 [운영 주소](https://vitastep-guide.onrender.com/)로 접속한다. 별도 테스트 계정은 필요 없다. 첫 서버 연결이 지연되면 준비 안내를 기다린다. 실제 개인 건강정보 대신 가상 성인 선택지로 확인한다. 결과 안내를 받을 때까지 서비스를 유지한다. [화면별 확인 방법](docs/functional-requirements.md)을 참조한다.

로컬은 Python3.11 이상(검증3.13), Node22.12 이상(검증24)을 사용한다.

```sh
# 루트: 최초 설치
python3 -m venv .venv
.venv/bin/python -m pip install -r backend/requirements.lock
# .env가 없을 때만 예시 복사
cp -n .env.example .env
```

루트 `.env`의 `COPA_API_KEY`에 본인 키를 입력한다. `COPA_BASE_URL=https://copa.codyssey.kr/v1`, `COPA_MODEL=gpt-5.4`를 사용한다. 키는 Git 제외 대상이며 프런트 `VITE_` 변수·채팅·로그에 넣지 않는다. 키가 없어도 공개 조회와 규칙 후보는 가능하지만 실제 AI 기능은 실패 안내를 낸다.

```sh
# 터미널1: 루트
.venv/bin/python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --no-access-log
```

```sh
# 터미널2
cd frontend
npm ci
npm run dev -- --port 5173
# 배포 빌드 미리보기는 별도 실행
# npm run build
# npm run preview -- --port 4173
```

[로컬 개발 화면](http://127.0.0.1:5173/)·[로컬 API 문서](http://127.0.0.1:8000/docs). UI는 로컬8000 API에 연결한다. 포트를 바꾸면 공개 `VITE_API_BASE_URL`과 서버 `ALLOWED_ORIGINS`를 맞춘다. Render의 비밀값은 백엔드 환경변수에만 둔다.

```sh
# 루트: 실제 AI 호출 없이 검사
.venv/bin/python -m pytest -q
python3 scripts/validate_product_database.py
python3 scripts/validate_product_thumbnails.py
python3 scripts/validate_final_docs.py
# frontend에서
npm test
npm run build
```

실제 API3회 확인은 키/운영 사용량을 소비한다. 기존 증빙을 보존하려면 별도 보고서 경로를 지정한다.

```sh
.venv/bin/python scripts/check_submission.py --run-live \
  --base-url https://m2-1-api.onrender.com \
  --report /tmp/m2-1-acceptance-new.json
```

## 5. 구현 결과와 제출 상태

| 항목 | 확인 결과 |
|---|---|
| 핵심 기능 | Must8개 구현, AI 비교 해설 Should1개 구현 |
| 로컬 검사 | 백엔드159개·프런트15개 통과, 배포 빌드 성공 |
| 데이터 |14,587 검사 통과, 사진88개·공개87개 |
| 실제 운영 API | 각 Must3회 검사: 추천 M04 2/3, 나머지3/3. 실제 GPT·도구·출처 확인 |
| 브라우저 | 동의/설문 M01·M02 3/3. 전체 기능3회 UI 검사는 아님 |
| 피드백 개선 | 주소·질문 범위·첫 질문 오류·활력·포장 변형 중복 개선 기록 |
| 남은 제출 증빙 | **실제 사용자5명 원본/타깃 근거·각자의 본인 작성 기여/개인 링크·발표 PDF** |

[검증 상세와 실패 기록](docs/final/test-results.md)·[피드백5항목](docs/final/user-feedback.md)·[최종 제출 목차](docs/final/README.md). 개발자 검사를 실사용자5명으로 세지 않으며5개 개선 항목도 참여자5명 증거로 대체하지 않는다. 발표 PDF는 문서 확인 후 다음 단계에서 제작한다. 시연 영상은 생략한다.

설문·대화 원문은 서비스 서버 DB에 영구 저장하지 않고 임시 메모리를 사용한다. 외부 COPA/모델 제공자의 처리는 서버 내부 삭제와 별개다. AI 생성 표시·동의·철회·정보 최소화를 구현했으며 [보안/개인정보 범위](docs/final/security-and-operations.md)에 한계를 명시했다.
