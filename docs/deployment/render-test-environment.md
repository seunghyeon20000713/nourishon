# 외부 테스트 서버·DB 준비 · Render 후보

확인일: 2026-11-09. 아직 Render 계정 연결·서버·DB 생성·식품 데이터 업로드·외부 배포는 하지 않았다. 이번 단계는 배포 설정과 로컬 단일 주소 재현이다. 기존 공개 Sites 가상 체험판은 그대로다.

## 준비할 구성

| 대상 | 검토 설정 | 역할 |
| --- | --- | --- |
| GitHub | 기존 `seunghyeon20000713/nourishon`, `main` | 코드·문서만 제공 |
| Web Service | `nourishon-staging`, Python, Free, Singapore | React 빌드 + FastAPI `/api` |
| Postgres | Neon `nourishon-staging`, Free, AWS Singapore, PostgreSQL 18 (2026-11-16 변경: Render 30일 만료 회피) | 새 테스트 계정·가상 신체·식사 기록 |
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

**데이터 배치 방식 결정(2026-11-16):** 비공개 GitHub 저장소의 Release 첨부 + 그 저장소만 읽는 만료일 있는 세분화 토큰 + 빌드 시 SHA-256 검증. 무료 Render에는 SSH/웹 Shell이 없어 SCP로 파일을 넣을 수 없기 때문이다. 구현과 검증은 [식품 정제본 비공개 배포](food-data-release.md)를 본다. 파일 조회용 임시 SQLite 약 177MiB를 생성할 디스크도 필요하다. 재시작 시 임시 조회 파일은 다시 만든다. DB는 30일 만료가 없는 Neon 무료 플랜으로 정했다.

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

## Neon 외부 DB 준비 (2026-11-16)

DB는 Render 무료 Postgres(30일 만료) 대신 Neon 무료 플랜을 쓴다. 프로젝트 `nourishon-staging`, AWS Asia Pacific (Singapore). Neon 온보딩의 CLI(`neon init`, `neon env pull`)와 Data API는 사용하지 않는다. 소유자 연결 정보를 프로젝트 파일로 남기지 않고, 브라우저용 HTTP DB 접근 경로를 열지 않기 위해서다.

`scripts/prepare-staging-db.py`를 개발자 터미널에서 실행한다. 소유자 연결은 `read -s`로 입력해 환경변수로만 전달한다.

1. 접속 후 PostgreSQL 버전·DB 이름 출력. CI로 검증한 16·18이 아니면 변경 없이 종료
2. 앱 역할 `nourishon_app` 생성(무작위 32바이트 비밀번호, LOGIN만, SUPERUSER·CREATEDB·CREATEROLE 없음)
3. 기존 마이그레이션 적용 → `grant_app_role()`로 스키마 사용·테이블 읽기/쓰기만 허용
4. 앱 역할로 접속해 테이블 조회 가능·스키마 생성 불가 확인
5. 앱 연결 문자열을 터미널에 한 번만 출력 → Render `NOURISHON_DATABASE_URL`에만 입력. 재실행 시 비밀번호 유지, `--rotate-password`로 교체

로컬 검증: 비밀번호 인증 임시 PostgreSQL 16 서버(DB 이름 `neondb`, 소유자 `neondb_owner`)에서 위 흐름, 재실행, 비밀번호 교체 후 이전 비밀번호 거부, 앱 역할 테이블 생성 거부, 버전 불일치 시 무변경을 확인했다. 입력 검사 단위 테스트 3개(SSL 없음·로컬·앱 역할 연결 거부, 오류에 비밀값 미노출). 실제 Neon 실행 결과는 아래에 추가한다.

### 실제 Neon 1차 실행: 버전 불일치로 무변경 종료 (2026-11-16)

Neon 온보딩이 버전 선택 없이 PostgreSQL 18로 프로젝트를 만들었다. 준비 스크립트는 당시 16만 허용했으므로 `접속 성공: PostgreSQL 18, DB 이름 neondb` 출력 후 **아무것도 바꾸지 않고 종료**했다. 풀링 주소는 직접 연결 주소로 자동 변환됐다.

결정: Neon을 16으로 다시 만들지 않고 18을 사용한다. 대신 CI를 PostgreSQL 16(로컬 개발)·18(외부 테스트) 두 버전에서 모두 실행하고, 두 결과가 통과한 뒤에만 Neon에 마이그레이션을 적용한다. 스크립트는 CI로 검증한 16·18만 허용한다.

### 실제 Neon 2차 실행: 준비 완료 (2026-11-16)

CI(PostgreSQL 16.16·18.7, 각 131개 통과·건너뜀 0) 확인 후 개발자 터미널에서 실행했다. 출력: 풀링 주소 → 직접 연결 주소 변환, `PostgreSQL 18, DB 이름 neondb` 접속, 앱 역할 `nourishon_app` 생성, 마이그레이션 적용, 스키마 사용·테이블 읽기/쓰기 권한만 부여, 앱 역할로 접속해 테이블 조회 가능·스키마 생성 불가 확인. 앱 연결 문자열은 개발자가 별도 보관했고 채팅·Git에는 남기지 않았다. 소유자 연결 문자열은 저장하지 않았다.

## Render 실제 배포와 외부 확인 (2026-11-16)

Render 무료 Web Service `nourishon-staging`(Singapore, Python 3, Free 0.1 CPU·512MB), Auto-Deploy Off, Health Check `/api/ready`. 커밋 `f1015f6` 첫 배포. 주소: https://nourishon-staging.onrender.com

- 시간: 배포 시작 16:01:20 → 외부에서 `/api/ready` 200 첫 확인 16:08:20(빌드 + 첫 시작 합계 약 7분, 20~40초 간격 확인이라 실제 완료는 그 사이). 절전 후 재시작 시간은 아직 측정하지 않았다.
- 외부 확인(개발자 PC에서 요청): `/`·`/api/health`·`/api/ready` 200(`{"status":"ready"}`), 식품 검색 "두부" 3,218건, `/.env`·`/.git/config`·`/data/food/foods.json`·`/backend/settings.py`·`/api/docs` 404, 허용하지 않은 Host 403, `/api/auth/me` 응답 `cache-control: no-store`·`x-content-type-options: nosniff`.
- 개발자 브라우저 확인: 가상 계정으로 사용 흐름이 정상 동작한다고 보고받음.
- 식품 정제본: 빌드 중 비공개 Release에서 내려받아 SHA-256 일치 후 배치(검색 결과로 간접 확인).

### 지인 공유 전 보완 필요 (2026-11-16 발견)

1. 화면에 테스트 서버·가상 데이터 전용 안내가 없다(Sites 체험판에만 있음).
2. 회원 탈퇴(계정·기록 삭제) 기능이 없다.
3. 로그인 시도 제한이 `request.client.host` 기준인데, Render 프록시 뒤에서 uvicorn이 프록시 IP를 사용자 IP로 볼 가능성이 있다(추정, 미검증). 그러면 모든 사용자가 한 IP 묶음(15분 40회)을 공유한다.

### 보완 ③ 로그인 시도 제한의 사용자 IP (2026-11-16)

문제: 로그인·가입 시도 제한(IP별 15분 40회, 아이디별 10회)이 `request.client.host`를 썼다. Render는 Cloudflare와 로드밸런서를 거쳐 요청을 전달하므로 이 값은 프록시 주소다. 그러면 여러 사용자가 한 묶음을 공유해, 몇 명이 비밀번호를 틀리면 모두가 15분 동안 막힐 수 있다. Render 문서와 서버 설정으로 판단한 것이며, 실제 Render에서 묶임 현상을 재현하지는 않았다.

선택: `NOURISHON_CLIENT_IP_HEADER=cf-connecting-ip`를 설정한 경우에만 `CF-Connecting-IP`를 사용자 IP로 쓴다. Render 문서에 따르면 Cloudflare가 이 헤더를 요청마다 덮어써서 사용자가 위조할 수 없다. 값이 IP 형식이 아니면 직접 연결 주소를 쓴다.

버린 대안:
- `X-Forwarded-For` 맨 앞 값: Render 프록시는 사용자가 보낸 값을 지우지 않고 뒤에 덧붙인다. 그래서 맨 앞 값은 위조할 수 있고, 위조 IP를 바꿔 가며 제한을 우회할 수 있다.
- uvicorn `--forwarded-allow-ips='*'`: 결국 같은 헤더를 믿게 되어 위와 같은 위조 문제가 있다.
- 헤더를 기본으로 켜기: Cloudflare가 없는 곳에서는 위조할 수 있으므로 명시적으로 설정할 때만 쓴다.

검증(로컬): 단위 테스트 5개(기본값은 직접 주소, 설정 시 헤더 사용, `X-Forwarded-For` 무시, 잘못된 값이면 직접 주소, 허용하지 않은 헤더 이름은 설정 오류). DB 통합 테스트 1개: 같은 사용자 IP가 41번째에 429가 되어도 다른 IP는 401(제한 안 걸림), `X-Forwarded-For`를 위조해도 429 유지.

Render 반영: 환경변수 `NOURISHON_CLIENT_IP_HEADER=cf-connecting-ip` 추가 후 Manual Deploy.

출처: [Render: How Render handles DDoS attacks](https://render.com/articles/how-render-handles-ddos-attacks), [Render: Host PocketBase on Render(CF-Connecting-IP 권장)](https://render.com/articles/host-pocketbase-on-render), [Render 커뮤니티: X-Forwarded-For 덧붙임](https://community.render.com/t/accessing-client-ips-in-a-node-express-app/36282)

### 보완 ① 테스트 서버 안내 띠 (2026-11-16)

문제: 공개 Sites 체험판에는 "가상 데이터·실제 개인정보 입력 금지" 안내 띠가 있었다. 실제 가입·저장이 되는 테스트 서버 화면에는 안내가 없었다. 건강정보는 민감정보이므로, 지인이 실제 체중·식사를 입력하지 않도록 막아야 한다.

선택:
- 체험판 안내 띠를 공통 함수 `frontend/src/siteNotice.ts`와 `site-notice.css`로 분리했다(기존 `demo.css`를 이름만 바꿔 이동). 체험판과 테스트 서버가 같은 모양을 쓴다.
- 테스트 서버 빌드에서만 켠다. `scripts/build-staging.sh`가 `VITE_NOURISHON_STAGING_NOTICE=1`로 빌드하므로, 로컬 일반 빌드에는 안내 띠가 없다.
- 문구: "테스트 서버입니다 · 실제 개인정보·건강정보 대신 가상 정보만 입력하세요. 무료 서버라 첫 접속이 느릴 수 있고, 기록은 장기 보관을 보장하지 않습니다."
- 회원가입 안내 문구도 테스트 서버에서는 "테스트 서버용 계정, 가상 아이디 사용"으로 바뀐다.
- 체험판 문구(`화면 체험판 · 식품`)를 넣지 않았다. 이 문구가 있으면 `backend/web.py`가 체험판 빌드로 판단해 시작을 거부하기 때문이다.

버린 대안: 서버 API에서 운영 모드를 받아 화면이 판단하는 방식. 첫 화면 표시 전에 요청이 하나 더 필요하고, 서버가 절전 중이면 안내가 늦게 뜬다. 빌드 시점 플래그는 화면이 뜨는 즉시 표시된다.

검증(로컬): 같은 소스로 세 가지를 빌드해 비교했다. 테스트 서버 빌드에는 안내 문구가 있고 체험판 문구는 없다. 일반 빌드에는 안내 문구가 없다. 체험판 빌드에는 체험판 문구와 공통 CSS가 있다. TypeScript 검사·Vite 빌드 통과. 브라우저 캡처로 겹침을 확인하려 했으나 이 PC의 브라우저 실행이 시간 초과로 실패해, 레이아웃은 기존 체험판 안내 띠와 같은 CSS를 쓰는 것으로 대신 판단했다. 실제 배포 후 화면에서 확인한다.

### 보완 ② 회원 탈퇴 (2026-11-16)

문제: 가입·기록 저장은 되는데 본인이 계정과 기록을 지울 방법이 없었다. 건강정보 서비스라면 삭제 요청에 바로 응할 수 있어야 한다.

선택:
- `POST /api/account/delete`: 로그인 세션, CSRF 토큰, 허용 Origin을 확인한 뒤 **비밀번호를 다시 확인**한다. 화면이 열려 있는 것만으로는 탈퇴할 수 없게 하기 위해서다. 비밀번호 시도는 로그인과 같은 제한(아이디별 15분 10회, IP별 40회)을 받는다.
- 계정 행 하나를 지우면 세션·프로필·신체 측정·식사가 DB의 `ON DELETE CASCADE`로 한 트랜잭션에서 함께 삭제된다. 운동·활동 계획은 프로필 행 안에 있다. 그 아이디의 로그인 시도 기록(해시)도 지우고 세션 쿠키를 삭제한다. DB 구조 변경·마이그레이션은 없다.
- 틀린 비밀번호는 403으로 응답한다. 화면은 401을 "로그인 만료"로 처리하므로 둘을 구분했다.
- 화면: "내 계정" 패널 아래 접힌 "회원 탈퇴". 삭제 항목을 안내하고, 비밀번호와 "영구 삭제 이해" 체크를 받은 뒤 브라우저 확인 창으로 한 번 더 묻는다. 완료되면 로그아웃 상태로 바뀌고 완료 안내가 나온다.
- 안내 문구에 Neon 무료 플랜의 복원용 변경 기록 보관 기간(최대 6시간)을 적었다. 출처: [Neon History window](https://neon.com/docs/introduction/history-window), [Neon plans](https://neon.com/docs/introduction/plans)

버린 대안: 30일 유예 후 삭제(soft delete). 실수로 탈퇴했을 때 복구할 수 있지만, 테스트 서버에는 과하다. 즉시 삭제가 "지워 달라"는 요청에 바로 응하는 방식이다.

검증(로컬 DB): 통합 테스트 3개.
1. 기록이 있는 A만 탈퇴하면 A의 users·sessions·profiles·meals·body_measurements가 모두 0건이 된다. B의 기록 수는 그대로다. 지운 세션 쿠키는 401이 되고, 재로그인도 401이다.
2. 틀린 비밀번호(403), 삭제 동의 없음(422), CSRF 없음(403), 다른 Origin(403), 비로그인(401)이면 계정이 남아 있다.
3. 비밀번호를 연속으로 틀리면 429가 되고, 그 뒤에는 맞는 비밀번호로도 막힌다.

백엔드 전체 140개 통과. 화면은 TypeScript 검사·빌드 통과. 이 PC의 헤드리스 Chromium이 빈 페이지조차 띄우지 못하고 멈춰서, 브라우저 동작 확인은 배포 후 실제 화면에서 한다.
