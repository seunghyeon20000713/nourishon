# 외부 테스트 서버·DB 준비 · Render 후보

확인일: 2026-11-09. 아직 Render 계정 연결·서버·DB 생성·식품 데이터 업로드·외부 배포는 하지 않았다. 이번 단계는 배포 설정과 로컬 단일 주소 재현이다. 기존 공개 Sites 가상 체험판은 그대로다.

## 준비할 구성

| 대상 | 검토 설정 | 역할 |
| --- | --- | --- |
| GitHub | 기존 `seunghyeon20000713/nourishon`, `main` | 코드·문서만 제공 |
| Web Service | `nourishon-staging`, Python, Free, Singapore | React 빌드 + FastAPI `/api` |
| Postgres | `nourishon-staging-db`, Free, Singapore, PostgreSQL 16 | 새 테스트 계정·가상 신체·식사 기록 |
| 앱 DB 역할 | 소유자와 분리, 필요한 테이블 읽기·쓰기만 | 실행 중 스키마 생성·권한 관리 방지 |
| 식품 데이터 | 승인한 정제본을 별도 비공개 경로로 제공 | GitHub·웹 정적 파일로 공개하지 않음 |

웹과 DB는 같은 리전을 선택한다. 현재는 리소스를 생성하지 않았으므로 실제 이름·주소는 확정되지 않았다. DB 소유자 연결을 앱 환경변수에 그대로 넣지 않는다. 기존 개인용 로컬 DB를 외부로 복제하지 않는다.

## 파일과 생성 전 입력값

- `scripts/build-staging.sh`: 고정된 Python 의존성 설치 → `npm ci` → 일반 화면 빌드. 실제 식품·`.env`·DB 파일을 화면 빌드에 복사하지 않는다.
- `deploy/render.yaml.example`: Render 웹 서버의 검토용 설정이다. 자동 적용되는 루트 `render.yaml`이 아니며, 현재 그대로 배포하면 식품 경로·DB·Origin이 없어 실행되지 않는다. 자동 배포는 꺼 두어 커밋할 때마다 외부 서버가 바뀌지 않게 한다.
- `scripts/start-staging.sh`: 화면과 API를 한 주소에서 실행. `PORT`, worker 1개, 접근 로그 비활성화.
- `scripts/check-staging.py --check-food --check-db`: 전체 식품 파일의 읽기·개수·기준량과 임시 조회 파일 생성을 확인하고, 별도 DB의 연결·스키마·앱 역할을 확인한다. 임시 파일은 검사 후 지운다. `--check-db`를 생략하면 실제 DB를 검사하지 않았음을 출력한다.

Render 생성 화면에서 Root Directory는 저장소 루트로 두고 다음을 사용한다.

| 항목 | 값 |
| --- | --- |
| Build Command | `bash scripts/build-staging.sh` |
| Start Command | `bash scripts/start-staging.sh` |
| Health Check | `/api/ready` |
| Auto Deploy | Off |
| PYTHON_VERSION | `3.12.3` (검증한 로컬 버전) |
| NODE_VERSION | `24.22.2` (검증한 로컬 버전) |
| NOURISHON_ENV | `staging` |
| NOURISHON_ALLOWED_ORIGINS | 새 서버의 정확한 `https://...onrender.com` 주소 |
| NOURISHON_DATABASE_URL | 제한된 앱 역할의 SSL DB 연결. Render 비밀 설정에만 입력 |
| NOURISHON_FOOD_DATA_PATH | 별도 승인·배치한 `foods.json` 절대 경로 |
| NOURISHON_FRONTEND_DIST | `/opt/render/project/src/frontend/dist` |

이 경로는 Render 기본 네이티브 빌드의 저장소 루트를 전제로 한다. `NOURISHON_MIGRATION_DATABASE_URL`은 명시적 마이그레이션 작업에만 사용하고 실행 서버에는 남기지 않는다. 소유자 연결을 제공할 세부 작업은 계정 연결 후 실제 DB 지원 권한을 확인해 정한다.

## 연결 후 실제로 진행할 순서

1. Render 가입·연결 상태와 무료 플랜 선택 가능 여부 확인. GitHub에는 이 저장소에 필요한 권한만 연결한다.
2. 외부 테스트 구성·공개 접근 범위·가상 계정 사용을 사용자에게 구체적으로 확인한 뒤 DB를 만든다. 무료 외 사용이나 결제 등록이 필요하면 먼저 비용을 확인한다.
3. 별도 DB에 기존 마이그레이션을 명시적으로 적용하고 제한된 앱 역할을 준비한다. 비밀번호·연결 문자열은 채팅·GitHub·빌드 로그에 붙여넣지 않는다.
4. 식품 파일의 비공개 배치 방법을 확정하고 전송을 확인받는다. 현재 API 키를 Render에 복사할 필요는 없다. 전체 정제본과 완료 보고서만 있으면 된다.
5. 웹 서버 생성·비밀 설정·HTTPS를 확인하고 `/api/ready`가 통과한 뒤 가상 계정으로 가입·검색·150g 계산·기록·재로그인을 검증한다. 실제 건강정보를 입력받는 운영 사이트로 안내하지 않는다.

**데이터 배치는 아직 미해결이다.** Git에 없는 정제본을 서버가 자동으로 얻을 수는 없다. 무료 Render에는 SSH/웹 Shell이 없어 SCP로 파일을 넣는 방식을 쓸 수 없다. 승인된 비공개 다운로드나 빌드 시 별도 수집 중 재현 가능한 방법을 정해야 한다. 이번에는 공개 파일 링크를 만들거나 원본·인증키를 업로드하지 않았다. 파일 조회용 임시 SQLite 약 177MiB를 생성할 디스크도 필요하다. 재시작 시 임시 조회 파일은 다시 만든다.

## 무료 제약과 실제 검증의 경계

공식 문서 확인 결과 무료 웹 서버는 15분 미사용 시 절전되고, 재시작·절전·재배포 때 실행 중 파일 변경이 사라진다. 무료 Postgres는 1GB, 워크스페이스당 하나, 생성 후 30일에 만료된다. 테스트 기록도 만료될 수 있으므로 장기 보관 환경으로 사용하지 않는다. 무료 웹 서버에는 SSH/웹 Shell과 one-off job이 없다. 제한·요금은 실제 생성 화면에서 다시 확인한다.

로컬에서는 일반 프런트엔드 빌드를 `backend.web`으로 8001 포트에서 제공하고, 별도 `nourishon_test` DB와 정확한 `http://127.0.0.1:8001` Origin을 사용했다. 이는 실제 클라우드 HTTPS·무료 플랜의 자원 한도·원격 DB 검증을 대체하지 않는다. 첫 계정 검사는 테스트 포트가 허용 Origin에 없어 실패했다. 로컬 QA 설정을 바로잡아 다시 검사했고, 공개 Origin 검사를 느슨하게 바꾸지 않았다.

실제 전체 정제본·일반 빌드·예시 HTTPS/DB 주소로 `--check-food`가 통과했다. 이 검사는 외부 DB에 접속하지 않았다. 전용 사전 검사 테스트는 가상 식품의 정상·개수 불일치와 오류에 비밀 문자열이 노출되지 않음을 확인했다. 배포 설정/경로 검사와 합쳐 4개 통과했다. Render 빌드 스크립트는 구문 검사했으며 외부 런타임에서 패키지를 새로 내려받는 빌드는 아직 실행하지 않았다.

## 공식 근거

- [Render 무료 제한](https://render.com/docs/free)
- [지원 언어와 버전 설정](https://render.com/docs/language-support)
- [Python 런타임에서 Node/npm 등 사용 가능](https://render.com/docs/native-runtimes)
- [Postgres 생성·같은 리전 연결](https://render.com/docs/postgresql-creating-connecting)
- [Blueprint 설정·자동 배포 Off](https://render.com/docs/blueprint-spec)

최종 단일 주소 브라우저 검증은 **12개 통과(14.4초)**였다. 가입·재로그인·DB 기록·음식 비교·섭취량 계산·모바일 흐름을 포함한다. 이 검증 뒤 QA 전용 8001 서버는 종료했다. 기존 개발 서버와 실제 로컬 개인 DB는 유지했다.
