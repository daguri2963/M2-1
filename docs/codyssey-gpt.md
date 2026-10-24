> **과거 단계 기록 보존 / 2026-10-24:** 이 문서에는 당시 Gemini·main·canary 또는 이전 정책 설명이 포함될 수 있습니다. 현재 운영은 production의 COPA GPT-5.4입니다. 최종 제출 기준은 [최종 문서 목차](final/README.md), [현재 구조](final/architecture.md), [AI 설계](final/ai-design.md), [현재 검증](final/test-results.md)을 확인하세요. 아래 날짜·이전 실행 결과는 원래 이력으로 보존합니다.

# 코디세이 GPT 연결 (canary)

현재 canary는 Gemini 전용 호출을 코디세이의 OpenAI 호환 Chat Completions로 전환했다. **2026-10-23 실제 가상 키로 소규모 호환 검증과 canary 로컬 통합 검사를 통과했다.** 검증 후 dev PR로 통합하며 production 전환·Render 환경변수 등록은 별도 단계다. 운영 서버는 기존 Gemini 버전을 유지한다.

## 키 입력 위치

프로젝트 루트의 `/Users/voanic/codyssey/M2-1/.env`를 연다. `backend/`나 `frontend/` 안에 새로 만들지 않는다.

```dotenv
COPA_API_KEY=여기에_코디세이에서_발급한_가상키
COPA_BASE_URL=https://copa.codyssey.kr/v1
COPA_MODEL=gpt-5.4
AI_TIMEOUT_SECONDS=45
```

로컬 파일에는 위 설정 항목이 준비되어 있다. **`COPA_API_KEY=` 오른쪽만 실제 값으로 채우고 저장**한다. 키를 따옴표로 감쌀 필요는 없다. 남겨둔 `GEMINI_API_KEY`와 `GEMINI_MODEL`은 새 코드가 사용하지 않는다. 기존 키를 지우거나 덮어쓸 필요가 없다. API 기본 주소는 `/v1`까지만 적는다.

`.env`는 Git에서 제외되며 권한은600이다. `.env.example`에는 비어 있는 키와 공개 설정만 제공한다. 가상 키는 코디세이 주소로만 보낸다. 다른 호스트·HTTP·URL 내 인증정보·추가 경로를 거부하고 HTTP 리디렉션도 따르지 않는다. OpenAI 기본 서버로 재시도하거나 Gemini 키를 대신 사용하는 동작은 없다.

## 구현

- `backend/copa.py`: 공식 OpenAI SDK의 비동기 Chat Completions. 기본 주소는 코디세이이며 `store=false`, SDK 재시도0회, 제한된 출력 토큰을 사용한다. 실측에서 거부된 `reasoning_effort`는 보내지 않는다.
- `backend/agent.py`: 기존7개 도구·검색·추천 제한·출처 검증은 유지한다. 도구 정의는 strict JSON Schema, 결과 전달은 assistant tool_calls와 tool_call_id로 연결한다. 지원되는 `tool_choice=auto`로 모델이 도구를 선택하며 첫 응답에 실제 도구 호출이 없으면 실패로 처리한다. 최종 응답 스키마는 메시지로 전달하고 JSON을 서버의 Pydantic과 출처·제품·금지 표현 검사로 검증한다. 공급자가 최종 응답 형식을 강제한다고 표현하지 않는다.
- API의 성공 모드는 공급자에 독립적인 `ai`, 제공자는 `codyssey`다. 화면의 성공 판정·전송 안내·동의 버전도 함께 변경한다. 동의 요청은 `provider=codyssey`를 명시해야 하며, 이전 화면이 새 동의 버전만 자동 수용해 다른 제공자로 전송하는 것을 막는다. 새 화면도 health의 제공자가 일치해야 동의할 수 있다. 모든 공급자 실패가 성공한 답변으로 표시되지는 않는다.
- 개인 건강정보 필터·설문 최소화·세션·추천 규칙은 유지한다. `store=false`는 중계 서버까지 포함한 무보관을 뜻하지 않는다. 코디세이의 로그·보관 정책, 키의 공개 서비스 사용 범위·한도·만료는 별도로 확인해야 한다. 실제 검증에는 가상 입력·공개 지식·공개 상품만 사용했으며 운영 변경은 아직 하지 않는다.

사용자가 제공한 안내에는 `https://copa.codyssey.kr/v1/chat/completions`, 예제 모델 `gpt-5-mini`, 사용 가능 목록의 `gpt-5.4`가 있다. 실제 목록을 기준으로 `gpt-5.4`를 선택했다. OpenAI 공식 API와 중계 API의 지원 범위는 다르며 아래는 이 키·모델·확인일의 실제 결과다.

| 요청 기능 | 실제 확인 결과 |
|---|---|
| 기본 대화, `store=false`, `max_completion_tokens` | 정상 응답 |
| 기본 도구, `strict=true` 도구 스키마, `tool_choice=auto` | 실제 도구 호출 정상 |
| assistant tool_calls → tool_call_id 결과 전달 | 도구 결과에 근거한 최종 답변 정상 |
| `reasoning_effort=none` | HTTP 400 `unsupported_feature` |
| `tool_choice=required`·특정 함수 지정 | HTTP 400 `unsupported_feature` |
| `response_format=json_schema`·`json_object` | HTTP 400 `unsupported_feature` |

따라서 지원되지 않는 옵션을 제거했다. 잘못된 JSON·추가 필드·없는 출처·없는 제품·허용되지 않는 수치는 서버가 실패로 처리하며 실패를 임의의 성공 답변으로 바꾸지 않는다. 다른 공급자나 Gemini로 자동 전환하지 않는다.

## 검증

키 없는 자동 검사는 SDK의 실제 HTTP 요청을 가짜 전송 계층으로 받아 도구 ID·JSON 스키마·출처·민감정보 차단·오류를 확인한다. CI에는 `COPA_API_KEY`를 넣지 않는다.

```sh
.venv/bin/python -m pytest -q
cd frontend
npm test
npm run build
```

실제 키를 저장한 뒤 프로젝트 루트에서 수행한다. 첫 명령은 키 존재 여부만 확인하며 요청하지 않는다. 두 번째는 사용량을 소비하고 가상 공개 입력으로 일반 채팅 → 함수 호출 → 도구 결과의 JSON 응답·서버 검증 → 일반 영양 Agent → 제품 Agent 순서로 확인한다. 키·인증 헤더·원문 오류는 출력하지 않는다.

```sh
.venv/bin/python scripts/check_copa_compatibility.py
.venv/bin/python scripts/check_copa_compatibility.py --run-live
```

실제 확인 결과는 `docs/copa-compatibility-check.json`으로 저장한다. 실행하지 않았다면 통과로 기록하지 않는다. 기존 Gemini 검증 JSON들은 과거 결과이므로 새 공급자 성공 증거로 사용하거나 덮어쓰지 않는다.

호환 검증과 canary CI 통과 → canary 로컬 API·화면 통합 검사 → canary에서 dev로 PR 병합 → 충돌 해결·추가 변경이 있었다면 dev에서 관련 검사 → production PR·서버 환경변수·화면 동의 전환 → 운영 확인 순서로 진행한다. 운영 전환 시 키 등록은 실제 서버와 데이터 전송 대상을 확인한 뒤 수행한다.

공식 참고: [GPT-5.4](https://developers.openai.com/api/docs/models/gpt-5.4), [함수 호출](https://developers.openai.com/api/docs/guides/function-calling), [Chat Completions 호환 조건](https://developers.openai.com/api/docs/guides/migrate-to-responses), [구조화 출력](https://developers.openai.com/api/docs/guides/structured-outputs). 코디세이 중계 구현과 계정 한도는 OpenAI 공식 문서만으로 확정할 수 없다.

## 실제 확인 결과

이전 키 입력 전 단계에서 백엔드94개·프런트10개 검사와 빌드가 통과했고, 새 제공자 동의·GPT 표시·키 미설정 오류를 로컬 화면에서 확인했다. 당시의 임시 화면 검증 서버는 종료했다.

키 입력 후 호환 옵션을 수정해 실행한 [실제 호출 보고서](copa-compatibility-check.json)는 전체 20.1초에 통과했다. 기본 대화·실제 함수 호출·도구 결과 전달·JSON의 서버 검증·일반 영양 Agent·제품 Agent를 확인했다. 일반 질문은 `search_nutrition_knowledge`, 제품 질문은 `get_product_details`와 `search_evidence`를 GPT가 선택했다. 공개 지식과 제품 출처가 실제 응답에 포함됐다. 이 소규모 결과는 운영 배포나 모든 질문의 품질 검증을 의미하지 않는다.

수정 후 백엔드100개 검사가 통과했다. 공급자의 `response_format` 없이도 코드 블록·배열·추가 필드·존재하지 않는 출처와 제품·금지된 수치를 거부하는 회귀 검사를 포함한다.
