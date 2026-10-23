# Render 외부 배포

최초 배포일: 2026-10-21. 기본 홈페이지 주소 변경: 2026-10-22. 홈페이지·백엔드 모두 Render의 `live` 상태와 실제 외부 응답을 확인했다. 최초에는 GitHub 비공개 저장소 `sayknow/M2-1`의 `main`을 연결했다. 이후 소유자가 저장소를 공개했고, 2026-10-23 브랜치 구조 전환 후 운영 연결 기준은 `production`이다. 홈페이지 공개와 저장소 공개 여부는 별개다.

## 서비스 구성

| 구분 | 홈페이지 | 백엔드 |
|---|---|---|
| 주소 | https://vitastep-guide.onrender.com | https://m2-1-api.onrender.com |
| Render ID | `srv-dbcsntavcj2c73fofdpg` | `srv-dbc2hefavr4c73ekh06g` |
| 유형 | 무료 Static Site | Free Docker Web Service |
| 경로 | `frontend` | 저장소 루트 |
| 빌드 | `npm ci && npm run build` | 루트 `Dockerfile` |
| 공개 폴더 | `dist` | 해당 없음 |
| 실행 | 정적 파일 제공 | Dockerfile의 Uvicorn, 워커 1개 |
| 서버 지역 | 전역 CDN | Singapore |
| 상태 확인 | 홈페이지 접속 | `/api/health` |

홈페이지는 실제 상품 이미지 87개를 포함한다. 백엔드는 검수 SQLite를 배포 이미지에 포함해 읽기 전용으로 조회한다. 상품 원본 수집·검수는 배포 중 다시 실행하지 않는다. 별도 Postgres·유료 디스크·맞춤 도메인은 생성하지 않았다.

## 환경 설정

홈페이지의 공개 설정:

- `VITE_API_BASE_URL=https://m2-1-api.onrender.com`
- `NODE_VERSION=24.19.0`
- `SKIP_INSTALL_DEPS=true` — 빌드 명령의 `npm ci` 한 번으로 설치한다.

백엔드 설정:

- `GEMINI_API_KEY` — 사용자가 별도로 승인한 로컬 키를 Render 서버 환경변수로 등록. 값은 이 문서·Git·프런트·명령행 인자·검사 보고서에 기록하지 않는다.
- `GEMINI_MODEL=gemini-3.5-flash-lite`
- `ALLOWED_ORIGINS=https://vitastep-guide.onrender.com,https://m2-1-itfc.onrender.com`
- `PORT` — Render가 제공하는 값을 Dockerfile에서 사용한다.

홈페이지 주소를 바꿀 때 백엔드 허용 출처와 문서 링크를 갱신한다. 백엔드 주소가 그대로라면 홈페이지의 API 주소는 유지한다. 환경 설정을 바꾼 서비스는 다시 배포한다. 키 변경도 백엔드에 다시 적용해야 한다. 로컬 `.env`는 계속 Git 제외 대상이다.

## 갱신과 복구

소유자가 필수 검사를 통과한 PR을 `production`에 병합하면 Render가 CI 완료 후 해당 서비스를 자동 배포한다. `canary`·`dev`는 Render 서비스에 연결하지 않는다. 불필요한 문서 빌드를 줄이도록 다음 경로를 지정했다.

- 홈페이지: `frontend/**`
- 백엔드: `backend/**`, `data/products/products.sqlite3`, `Dockerfile`, `.dockerignore`

설정 또는 다른 의존 경로를 추가할 때 배포 경로 필터도 함께 검토한다. 문서만 변경하면 실행 중인 앱은 이전 코드 커밋을 유지할 수 있다. 배포 실패 시 해당 서비스의 Deploys·Logs에서 실패한 단계부터 확인하며, 기존 정상 배포가 있는 경우 그 버전 유지 여부를 확인한다.

무료 백엔드는 요청이 없으면 대기 상태가 되며 재기동에 약 1분이 걸릴 수 있다. 홈페이지는 독립적으로 열리고 서버 준비 안내·자동 재시도를 제공한다. 재시작 시 메모리 동의 세션은 만료되므로 다시 동의해야 한다. 사용자의 컴퓨터를 계속 켜둘 필요는 없다.

배포 파일로 제공하는 상품 DB는 재시작 시 복원되지만, 서버가 실행 중에 새로 쓴 파일은 영구 보존되지 않는다. 현재는 사용자 설문·대화를 영구 저장하지 않는다. 향후 피드백 저장 기능은 별도 영구 저장소를 사용해야 한다.

## 무료 이용과 사용량

Free 컴퓨트와 무료 정적 사이트만 생성했다. 기존 `econscope-api`도 같은 워크스페이스에 있어 월 무료 서버 시간·전송량·빌드 분량을 공유한다. 750시간이 M2-1에 따로 배정되는 것은 아니다. Billing 화면에서 남은 사용량을 확인한다. 기존 서비스의 중지나 요금제 변경은 수행하지 않았다.

Gemini 사용량은 Render와 별개다. Gemini 실패 시 규칙 기반 추천 후보는 유지하고 AI 설명 불가를 알리며, 대화는 실패 안내를 제공한다. Render 백엔드 자체가 중지되면 상품 조회·추천 등 서버 기능도 영향을 받는다.

공식 안내: [무료 서비스와 한도](https://render.com/docs/free), [환경변수](https://render.com/docs/configure-environment-variables), [전송량](https://render.com/docs/outbound-bandwidth), [빌드 시간](https://render.com/docs/build-pipeline).

## 외부 검증과 평가자 접속

평가자는 홈페이지 주소로 접속한다. 로그인 계정은 필요 없으며 추천·대화 전 성인·정보 처리·AI 전송 동의가 필요하다. 개인의 실제 진단·복용 내역·연락처 등 민감한 정보를 입력하지 않는다.

외부 API 검사는 가상 선택지와 공개 상품만 사용한다. 아래 명령은 실제 Gemini 사용량을 소비한다.

```sh
.venv/bin/python scripts/check_backend.py \
  --base-url https://m2-1-api.onrender.com \
  --report docs/deployment-api-check.json
```

검사 결과는 `deployment-api-check.json`에 기록하고, 브라우저에서 화면·사진·동의·추천·대화·오류 상태를 추가 확인한다. 실제 타깃 사용자 5명의 피드백과 모바일 실기기 검증은 별도 단계이며, 개발자의 가상 입력 검사를 실사용자 테스트로 세지 않는다. 결과 안내를 받을 때까지 배포를 유지하고 한도·키 만료·접속 상태를 확인한다.

## 배포 검증 결과

- 최초 배포 실행 앱 커밋: `fb2cce091f495581ffdb60b7c43117f7a9168f35`. 이후 배포 문서·검사 스크립트 커밋은 경로 필터에 따라 앱 재배포를 생략할 수 있다.
- 백엔드 최종 배포: `dep-dbc2ip1srm7s739e9gmg` (`live`). 정적 사이트 배포: `dep-dbc2hmrbc2fs73b29p00` (`live`).
- [외부 API 실행 기록](deployment-api-check.json): 동의·검수 게이트·상품87개·실제 Gemini 추천·비교·중복·추천 제한·정보 부족·실제 대화·철회 확인. 추천+AI 약7.8초, 제품 대화 약5.2초는 단일 사례이며 성능 보장값이 아니다.
- 홈페이지·제품 사진 HTTP200, 보류 품번404, 홈페이지 출처에 대한 CORS·동의 사전 요청 허용 확인.
- 실제 공개 홈페이지에서 준비 안내 이후 정상 홈, 이용 동의, 5단계 가상 설문, 장 건강 후보3개·AI 설명·공식 표시 출처, 실제 Gemini 대화를 확인했다.
- 화면 기록: [홈](screenshots/deployed-home.png), [추천](screenshots/deployed-recommendation.png), [실제 대화](screenshots/deployed-chat.png).
- 이번 배포 검증에서 실제 사용자 건강정보는 사용하지 않았다. 모바일 실기기·다수 사용자 부하·15분 유휴 후 전체 재기동 시간은 아직 측정하지 않았다.
- 후속 수정: 첫 질문의 함량·기준량 개념 설명 누락을 수정한 `c8fa914`를 재배포했다. [최신 수정·외부 검증](chat-label-reading-fix.md)을 참고한다.
- 상담가 확장: `b1185bf` 백엔드 배포 `dep-dbcalltg1s2s738kfppg`와 홈페이지 배포 `dep-dbcalltg1s2s738kfpt0`가 `live`임을 확인했다. 공식 일반 지식 검색·후속 대화·서버 안내·기존 기능 회귀와 화면을 확인했다. [상담가 구현·최신 검증](ai-counselor.md)을 참고한다.

## 2026-10-22 홈페이지 주소 이전

- 새 대표 주소: **https://vitastep-guide.onrender.com/**. Render에서 정확한 `vitastep-guide` 서브도메인을 확보했다.
- 새 무료 Static Site: `srv-dbcsntavcj2c73fofdpg`, 서비스 이름 `vitastep-guide`. 초기 배포 `dep-dbcsntivcj2c73foff90`는 `795a23c`로 배포했다.
- 기존 홈페이지 `srv-dbc2hmbbc2fs73b29o00`와 https://m2-1-itfc.onrender.com/ 은 이전 링크의 접속을 위해 유지한다. 자동 이동은 설정하지 않았다. 두 홈페이지는 같은 `main`과 기존 백엔드를 사용한다.
- 새로운 홈페이지에도 기존과 같은 `frontend` 경로, 빌드·공개 폴더, 공개 환경변수3개, `frontend/**` 배포 필터를 적용했다. 저장소·사이트 한글 이름·추천 정책·상품 DB·Gemini 키는 변경하지 않았다.
- 백엔드 `ALLOWED_ORIGINS`에 새 주소를 추가하고 기존 주소도 유지했다. `dep-dbcso9mq1p3s73d6qha0`로 설정을 재배포했다. 백엔드 URL은 https://m2-1-api.onrender.com 그대로다.
- 별도 유료 도메인·백엔드·디스크를 추가하지 않았다. 새 정적 사이트도 워크스페이스의 빌드·전송량을 공유한다.
- 주소를 되돌릴 경우 기존 홈페이지 링크를 사용하고 README의 대표 링크를 되돌린다. 백엔드의 기존 출처 허용은 그대로 유지되어 있다.
- 외부 확인: 홈페이지·빌드 자산·제품 사진 HTTP200, 상품87개, 새 주소와 이전 주소의 CORS 허용, 임의 출처 거부, 가상 설문 실제 Gemini 추천·비교·철회를 확인했다. 새 주소의 브라우저에서도 동의와 실제 AI 답변·출처 표시를 확인했다. [이전 검증 기록](vitastep-migration-check.json), [새 홈 화면](screenshots/vitastep-home.png), [새 주소 AI 대화](screenshots/vitastep-chat.png).
- 새 홈페이지와 백엔드 설정 배포 모두 `live`로 확인했다. 이 변경의 검증은 기능 연결 확인이며 실제 타깃 사용자 피드백이 아니다.

## 2026-10-23 브랜치 운영 구조 전환

- `main`의 기준 커밋 `1e44b76`에서 `production → dev → canary`를 차례로 생성했다. `main`은 프로토타입 기준으로 보존하고 기본 브랜치는 `production`으로 바꾼다.
- 두 정적 홈페이지(`vitastep-guide`, 이전 `m2-1`)와 `m2-1-api` 모두 연결 브랜치를 `production`으로 맞춘다. 자동 배포는 `checksPass`이며 기존 경로 필터·환경변수·서비스 ID·주소·요금제를 유지한다.
- 새 서버나 PR Preview는 만들지 않는다. 팀원은 로컬에서 개발하고 GitHub Actions의 임시 실행 환경으로 검사한다. CI에는 실제 Gemini 키를 전달하지 않는다.
- 브랜치 통합과 운영 병합은 소유자만 수행한다. GitHub Rulesets와 검사 구성은 [기여 안내](../CONTRIBUTING.md), [규칙 설정 원본](branch-rules/)을 따른다.
- 문서만의 변경은 경로 필터에 따라 배포를 생략할 수 있다. 연결 브랜치 변경을 확인하는 최초 운영 배포는 소유자가 명시적으로 수행한다.
