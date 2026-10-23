# 브랜치와 참여 방법

이 저장소는 소유자 `sayknow`가 통합과 운영 배포를 관리하고, 팀원이 `canary`에서 개발에 참여한다. 별도 시험 서버는 운영하지 않는다.

## 브랜치

| 브랜치 | 역할 | 변경 권한 |
|---|---|---|
| `main` | 구조 전환 전 프로토타입의 기준 커밋 `1e44b76` 보관 | 소유자 관리, 평소 수정하지 않음 |
| `production` | 기본 브랜치, 실제 Render 운영 배포 | 소유자만 PR 병합 |
| `dev` | 통합과 안정화 | 소유자만 PR 병합 |
| `canary` | 새 기능 개발·실험 | 쓰기 권한을 받은 팀원과 소유자 |

최초 생성은 `main → production → dev → canary`, 이후 반영은 **`canary → dev → production`** 순서다. 현재 기준 커밋에서 차례로 분기했으며, 네 브랜치는 별개의 저장소나 서버가 아니다. 여기서 `canary`는 실험 브랜치 이름이고 사용자 트래픽을 나누는 카나리 배포는 구현하지 않는다.

## 팀원 작업

```sh
git fetch origin
git switch canary
git pull --ff-only origin canary
# 수정하고 로컬에서 확인한 뒤
git add <변경한-파일>
git commit -m "변경 내용"
git push origin canary
```

같은 브랜치를 함께 사용하므로 푸시가 거절되면 다른 팀원의 커밋을 먼저 확인하고 합친다. 강제 푸시로 덮어쓰지 않는다. 여러 실험을 한꺼번에 통합하지 않도록 변경 범위를 조율한다. 다른 브랜치가 필요하면 소유자가 생성·관리한다.

팀원은 GitHub의 `canary → dev` PR에 설명과 로컬 검증 결과를 작성할 수 있다. 소유자가 변경 내용을 검토하고 병합한다. 팀원 승인은 필수 조건이 아니며 작성자가 본인인 PR도 소유자가 병합할 수 있다. 저장소가 공개이므로 누구나 코드를 읽거나 포크할 수 있지만, 공개라는 이유만으로 `canary`에 푸시할 수 있는 것은 아니다. 소유자가 별도로 collaborator 쓰기 권한을 부여해야 한다. 새 계정을 초대하거나 기존 참여자를 늘리는 작업은 이 구성에 포함하지 않는다.

## 자동 검사와 병합

GitHub Actions의 `CI`는 `canary`·`dev`·`production` 푸시와 `dev`·`production` 대상 PR에서 실행한다. 필수 검사 이름은 다음과 같다.

- `Promotion policy`: 같은 저장소의 `canary → dev`, `dev → production` 방향 확인
- `Backend checks`: 잠근 Python 의존성을 설치하고 백엔드 테스트
- `Frontend checks`: 잠근 Node 의존성 설치, 테스트, TypeScript·배포 빌드
- `Product data checks`: 검수 DB·원문 근거·사진·공개 데이터의 무결성 검사

검사는 GitHub의 임시 실행 환경에서 수행하며 Render 시험 서버나 실제 Gemini 키를 사용하지 않는다. 실제 Gemini 동작은 필요할 때 소유자가 로컬에서 가상 입력으로 확인한다. 자동 검사 통과가 의료·영양학 검증을 의미하지 않는다.

소유자는 `dev`로 통합한 뒤 로컬에서 연결 동작을 확인한다. 준비되면 `dev → production` PR을 만들고 필수 검사 통과 후 병합한다. 장기 브랜치의 공통 이력을 유지하도록 단계 간 PR은 **merge commit** 방식으로 병합한다. 완료된 `canary`·`dev`를 삭제하지 않는다. 운영 반영 후 소유자가 `production`을 `canary`에 정상 병합해 다음 작업의 기준을 맞춘다. 다음 `canary → dev` PR이 운영 반영 이력도 함께 전달하므로 이후 `dev → production`의 최신 기준 검사를 통과할 수 있다. 강제 동기화는 하지 않는다.

## 적용하는 GitHub Rulesets

규칙 설정 원본은 [docs/branch-rules](docs/branch-rules/)에 저장한다. 공개 저장소의 활성 branch rulesets를 사용한다.

| 규칙 | 대상 | 효과 |
|---|---|---|
| `core-history` | `main`, `dev`, `production` | 삭제·강제 푸시 차단. 소유자도 예외 없음 |
| `owner-managed-branches` | `canary`를 제외한 모든 브랜치 | 생성·변경·삭제는 관리자 역할만 예외 허용 |
| `integration-checks` | `dev`, `production` | PR 필수, 승인 인원0, 필수 검사4개 통과. 소유자도 예외 없음 |

현재 개인 계정 저장소의 관리자 역할은 소유자 `sayknow`다. 쓰기 권한의 참여자는 `canary` 외 브랜치를 직접 변경하거나 병합하지 못한다. **관리자 우회는 변경 권한 제한에만 허용**하고 이력 보호·필수 검사에는 허용하지 않는다. 추후 관리자 권한이나 GitHub App 예외를 추가하면 같은 보장이 유지되는지 다시 확인한다. 저장소 소유자는 설정 자체를 수정할 권한을 가진다.

## 운영 배포와 복구

Render의 새·기존 홈페이지와 백엔드는 `production`에 연결한다. 자동 배포는 CI 통과 후 진행하며 기존 경로 필터를 유지한다. 문서·CI 변경만으로 런타임이 재배포되지 않을 수 있다. GitHub에서 실행되는 검사와 별도로 운영 접속을 확인한다. GitHub PR 승인0과 Render 자동 배포는 팀원 승인 요청 절차를 만들지 않는다.

운영 장애의 긴급 수정도 `production` 기준 코드를 로컬에서 확인하고 `canary → dev → production`으로 반영한다. 안정화 변경은 `dev`와 `canary`에도 반영한다. 급한 복구는 소유자가 Render에서 이전 정상 배포를 선택하고 자동 배포 상태를 확인한 뒤, 원인 수정이나 revert를 같은 PR 흐름으로 기록한다. 삭제·강제 푸시로 기록을 되돌리지 않는다.

기존 [README 실행·검증 방법](README.md), [배포 설정](docs/deployment.md)을 함께 확인한다. 비밀키는 서버 환경변수에만 두고 실제 사용자 건강정보를 PR이나 검사 입력으로 올리지 않는다.
