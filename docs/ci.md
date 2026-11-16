# 백엔드 자동 테스트(CI) · 2026-11-16

## CI란

CI(Continuous Integration, 지속적 통합)는 코드를 GitHub에 올릴 때마다 클라우드의 임시 컴퓨터가 테스트를 대신 실행해 주는 장치다. 사람이 로컬에서 테스트를 깜빡해도, 깨진 코드가 `main`에 들어가면 바로 빨간 표시가 뜬다.

## 구성

파일: [`.github/workflows/backend-tests.yml`](../.github/workflows/backend-tests.yml)

```
push(main) 또는 PR
  → GitHub 임시 Ubuntu 24.04 시작
  → PostgreSQL 16 서비스 컨테이너(일회용 DB, 이름 nourishon_test)
  → Python 3.12.3 + requirements.txt 설치(pip 캐시 사용)
  → scripts/ci-prepare-db.py: 소유자로 마이그레이션 → 앱 역할 생성·권한 부여 → 앱 역할에 스키마 생성 권한이 없는지 확인
  → 앱 역할(nourishon_app)로 백엔드 테스트 118개 실행
  → 건너뜀이 1개라도 있으면 실패
  → 작업 종료 시 컴퓨터와 DB 폐기
```

- 비용: 공개 저장소의 GitHub 기본 실행기는 무료다. 결제 수단·외부 계정·비밀값을 사용하지 않는다.
- 권한: 워크플로에는 `contents: read`만 준다. checkout은 인증 정보를 작업 폴더에 남기지 않는다(`persist-credentials: false`).
- Action 고정: `actions/checkout` v7.0.1, `actions/setup-python` v7.1.0을 태그가 아니라 커밋 SHA로 고정했다. 태그가 다른 코드로 옮겨져도 CI가 영향을 받지 않는다.
- 같은 브랜치에서 새 push가 오면 이전 실행을 취소한다(`concurrency`).

## 설계 선택

| 선택 | 이유 | 대안과 버린 이유 |
| --- | --- | --- |
| 테스트를 권한이 좁은 앱 역할로 실행 | 실제 서버도 앱 역할로 접속한다. "권한이 좁아도 앱이 동작한다"를 매번 검증한다 | 소유자(superuser)로 실행: 설정은 간단하지만 권한 부족 문제를 놓친다 |
| 건너뜀 0 강제 | unittest는 건너뜀이 있어도 성공으로 끝난다. 환경변수 이름 오타만으로 보안 테스트 12개가 조용히 빠질 수 있다 | 건너뜀 허용: 초록 표시가 실제 검증 범위를 숨긴다 |
| DB 비밀번호를 YAML에 가짜 값으로 고정 | 실행기 안에서만 접속 가능하고 몇 분 뒤 사라지는 빈 DB다 | GitHub Secrets: 지킬 비밀이 없는데 구성만 복잡해진다 |
| 권한 부여 코드를 `backend.database.grant_app_role()`로 분리 | 로컬 `setup-local`과 CI가 같은 함수를 써서 권한 규칙이 두 벌로 갈라지지 않는다 | CI 전용 SQL을 따로 작성: 규칙이 어긋날 위험 |
| `CREATE ROLE`은 `psycopg.sql.Identifier/Literal`로 조립 | 관리 명령은 `%s` 바인딩을 지원하지 않는다. 문자열 이어붙이기 대신 라이브러리의 안전한 따옴표 처리를 쓴다 | f-string: SQL 주입 위험 |

`scripts/ci-prepare-db.py`는 테스트 코드와 같이 DB 이름이 `nourishon_test`가 아니면 멈춘다.

## 검증 (로컬, 2026-11-16)

- 기존 로컬 테스트 DB에 앱 역할로 접속: 백엔드 **118개 통과, 건너뜀 0**.
- CI 재현: 로컬 PostgreSQL 16 프로그램으로 비밀번호 인증·TCP 접속을 켠 **새 임시 DB 서버**를 만들어 워크플로 단계를 그대로 실행. DB 준비 2회 연속 성공(재실행 안전), **118개 통과, 건너뜀 0**. 확인 후 임시 서버·데이터 삭제.
  - Docker `postgres:16` 이미지로 재현하려 했으나 이 PC의 Docker 로그인 정보 도우미 오류로 이미지를 받지 못해 위 방법으로 대체했다. 실제 GitHub 실행 결과는 push 후 Actions 화면에서 확인한다.
- 안전장치 확인: DB 이름이 다르면 준비 스크립트 종료 코드 1. 테스트 DB 설정을 빼면 `OK (skipped=12)`가 나와 건너뜀 검사에 걸린다.

## 범위 밖

- Playwright 브라우저 테스트: API·화면 서버와 DB를 함께 띄워야 해서 배포 후 별도 작업으로 다룬다.
- 프론트엔드 빌드·타입 검사: 필요하면 같은 워크플로에 별도 작업으로 추가한다.
