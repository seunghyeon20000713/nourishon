# 실제 기능 외부 테스트 준비 · 1단계

2026-11-06. 이번 작업은 배포 공통 코드와 로컬 검증이다. 외부 서버·DB 계정/리소스 생성, 비용 발생, 실제 건강정보 또는 식품 데이터의 외부 업로드는 하지 않았다. 공개 Sites 가상 체험판은 그대로 유지했다.

## 서비스 계정이란

Render 같은 호스팅 사이트에 가입하는 회원 계정이다. NourishOn 안의 사용자 로그인과 다르다. 서버·DB를 만들고 GitHub 저장소를 연결하는 데 사용한다. 현재 Render 등 외부 서버 계정 연결은 확인되지 않았다. 비밀번호나 API 키를 채팅에 전달하지 않는다.

## 준비한 실행 구조

실제 기능 테스트용 앱은 React와 FastAPI를 같은 주소에서 제공한다. `/`는 일반 프런트엔드 빌드, `/api/`는 기존 API다. 브라우저가 노트북 localhost나 다른 사이트의 쿠키를 호출하지 않게 한다. 기존 개발 모드의 Vite 5173 + API 8000 구성은 유지한다.

`backend.web:app`은 빌드된 index·해시 JS/CSS/폰트·지정된 브랜드 이미지만 제공한다. 루트 프로젝트 파일, 환경 파일, 식품 JSON, 백엔드 소스, 임의 경로는 제공하지 않는다. API 준비 확인은 `/api/ready`이며 식품 로딩 및 DB 연결·스키마 1/2·운동 기록 컬럼을 확인한다. `/api/health`만으로 DB 정상 동작을 판단하지 않는다.

## 외부 테스트 환경변수

실제 비밀값이 없는 `deploy-settings.example`에 변수 이름을 정리했다. 값은 호스팅 서비스의 비밀 환경변수 화면에서 지정한다. 이 예제 파일을 실제 비밀번호 파일로 바꾸어 Git에 올리지 않는다.

| 이름 | 역할 |
| --- | --- |
| NOURISHON_ENV=staging | 외부 테스트 모드 |
| NOURISHON_ALLOWED_ORIGINS | 허용한 정확한 HTTPS Origin, 쉼표 구분·경로와 와일드카드 금지 |
| NOURISHON_DATABASE_URL | 앱 전용 별도 PostgreSQL 연결. SSL require/verify-ca/verify-full 필요, CA 검증 가능한 환경은 verify-full 권장 |
| NOURISHON_FOOD_DATA_PATH | 승인된 식품 파일 경로. 같은 폴더의 report.json 필요 |
| NOURISHON_FRONTEND_DIST | 일반 Vite 빌드 경로. 가상 체험판 빌드 사용 금지 |
| NOURISHON_MIGRATION_DATABASE_URL | 마이그레이션 시에만 제공하는 별도 소유자 연결. 앱 실행 자격 증명과 분리 |
| PORT | 호스팅 서비스가 제공하는 포트 |

외부 테스트 설정이 누락되면 시작하지 않는다. 로컬 `.env.database`로 몰래 대체하지 않는다. 허용 주소의 Host·Origin을 검사하고 Secure·HttpOnly·SameSite=Strict·Path=/의 `__Host-` 쿠키를 사용한다. Domain은 지정하지 않는다. 로컬 HTTP에서는 기존 쿠키와 개발 주소를 유지한다. 설정 오류·DB 오류에 비밀값을 출력하지 않는다. 외부 테스트에서는 API 문서 엔드포인트를 비활성화한다.

`/api/` 하위로 마운트할 때도 개인정보 응답 캐시 금지와 요청 크기 제한이 유지되도록 경로 처리를 보완했다. 프로필·식사 계산 응답에도 이 처리를 적용했다. 앱 실행에서 스키마를 자동 변경하지 않는다.

## 실행 준비 순서

1. `python -m pip install -r requirements.txt`
2. `bash scripts/frontend.sh build` 또는 Node.js가 있는 호스팅에서 `npm ci --prefix frontend` 후 `npm run build --prefix frontend`. demo 모드 사용 금지.
3. 별도 외부 테스트 DB를 만들고 소유자 역할로 `python -B -m backend.database migrate` 실행. staging에서는 NOURISHON_MIGRATION_DATABASE_URL 지정이 필수다. 실제 운영/로컬 개인 DB 연결을 재사용하지 않는다.
4. 앱 역할에 필요한 테이블 SELECT/INSERT/UPDATE/DELETE와 스키마 USAGE만 제공한다. 역할 생성과 권한 부여 방식은 선택한 PostgreSQL 서비스에서 확인해야 하며, 여기서 외부 역할을 생성하지 않았다.
5. 승인된 식품 파일·완료 보고서를 별도로 배치한다. GitHub에 원본을 올리거나 공개 URL로 임의 배포하는 방식은 사용하지 않는다. 제공 조건·전송 경로를 먼저 확인해야 한다.
6. `python -B scripts/check-staging.py --check-db`로 경로·일반 빌드·DB 연결·스키마와 앱 역할의 과도한 권한을 확인한다. 기본 검사는 설정·파일 경로만 확인하며 전체 식품 로딩은 서버 startup이 수행한다.
7. `bash scripts/start-staging.sh` 실행. HTTPS 종료·프록시 설정은 호스팅 환경에서 구성하고 준비 경로를 `/api/ready`로 지정한다. worker 1개로 시작해 식품 메모리 복제를 피한다.
8. 초대할 테스터 범위·접근 정책을 확정하고, 실제 개인정보 대신 가상 프로필로 시작한다. 공개 배포 전에 데이터 권한·접속 제한·백업/삭제 운영을 별도로 점검한다. 이번 준비만으로 운영 서비스가 완성된 것은 아니다.

## 무료 호스팅과 기존 메모리 확인 (2026-11-06)

[Render 무료 서비스 안내](https://render.com/docs/free)와 [요금표](https://render.com/pricing)를 확인했다. 무료 웹 인스턴스는 512MB, 15분 미사용 시 절전, 무료 PostgreSQL은 생성 후 30일 만료다. 포함 사용량 초과 시 결제 수단 등록 여부 등에 따라 과금/중지가 발생할 수 있어 무료라는 이유만으로 자원을 생성하지 않는다.

현재 전체 식품 290,871개를 읽은 기존 API 프로세스의 RSS는 `550064 KiB`, 약 **537.2 MiB**였다. 이는 프로세스 한 시점의 측정이며 최대 사용량·부하 테스트 결과가 아니다. 이미 512MB 무료 한도를 넘으므로 무료 서버에서 전체 데이터를 그대로 구동할 수 있다고 약속할 수 없다. 데이터 조회 메모리 최적화 또는 명시적으로 승인한 다른 사양이 필요하다. 유료 요금제를 임의 선택하지 않았다.

## 실제 검증

설정 누락·HTTP/로컬/와일드카드 Origin 거절, DB SSL 요구, 비밀값 repr/오류 비노출, 잘못된 Host/Origin 차단, 정적 경로 차단을 가상 주소로 검사했다. 별도 테스트 DB와 가상 HTTPS 주소로 가입·로그인·Secure 호스트 쿠키·로그아웃·ready를 확인했다. 실제 로컬 단일 주소 구성에서도 브라우저로 가입→DB 기록→재로그인과 식품 비교→150g 계산→기록을 검사했다. 테스트가 만든 가상 계정만 정리했다.

공식 구현 참고: [FastAPI 실행](https://fastapi.tiangolo.com/deployment/manually/), [FastAPI 하위 앱](https://fastapi.tiangolo.com/advanced/sub-applications/). 이번에는 Render 계정에 로그인하거나 리소스를 생성하지 않았다.

## 다음 작은 단계

2026-11-09에 식품 파일 조회 방식으로 바꿔 메모리 개선과 44개 응답 동등성 검증을 완료했다. [측정과 한계](../performance/food-catalog-memory.md)를 확인한다. 임시 조회 파일 약 176.78MiB를 만들 수 있는 쓰기 가능한 디스크도 필요하다. 다음은 호스팅 계정 가입·GitHub 연결·외부 테스트용 DB 생성·승인한 식품 파일 배치·HTTPS 주소 설정을 실제 서비스 화면에서 확인하며 진행한다. 기존 Sites 체험판의 공개 범위를 실제 건강정보 서비스에 자동 적용하지 않는다.

최종 실행 결과: 서버 전체 **112개 통과(1.651초)**, 단일 주소 구성의 실제 브라우저 **3개 통과(6.7초)**. 시작 스크립트 구문·Python 구문 검사 통과. 예시 HTTPS 주소와 실제 로컬 식품·일반 화면 경로로 배포 사전 검사의 성공 경로도 확인했다. 이 검사는 외부 DB에 접속하지 않았다고 명시하며, 실제 클라우드 TLS·원격 DB·장기 운영 검증은 아직 수행하지 않았다. 가상 HTTPS 주소의 쿠키 검사는 헤더·세션 동작 검사이지 실제 인증서 통신 검증은 아니다. QA용 8001 서버는 검사 후 종료했다.
