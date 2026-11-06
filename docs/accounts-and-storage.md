# PostgreSQL·회원·개인 활동 계획 · 2026-11-06

## 구현 범위

PostgreSQL 16.15에 회원·세션·개인 프로필·측정·식사를 저장하고, 가입·로그인·로그아웃 화면을 연결했습니다. 로컬 개발 환경이며 외부 공개 서비스로 배포하지 않았습니다.

| 저장 테이블 | 역할 |
| --- | --- |
| users | 아이디와 Argon2id 비밀번호 해시 |
| sessions | 세션 토큰의 SHA-256 해시, 사용자, CSRF 토큰, 8시간 만료 |
| profiles | 사용자 소유 프로필, 계산 기준·참고값, 활동 계획, 변경 리비전 |
| body_measurements | 프로필별 측정일·체중·선택 체성분 |
| meals | 프로필별 식사일·식사 구분·당시 식품/섭취량/출처/영양 계산 스냅샷 |
| auth_attempts | 원문 아이디·IP 대신 해시로 관리하는 시도 제한 |
| schema_migrations | 소스 스키마 버전 |

큰 식품 원본·정제본은 기존 `data/` 파일에 두며 DB나 GitHub에 전체 업로드하지 않습니다. 식사에 선택된 식품 스냅샷만 개인 DB 기록으로 저장합니다.

## 실행

Ubuntu 24.04 x86_64 기준, 이번 환경은 Docker Desktop의 WSL 연결이 없어 공식 Ubuntu 패키지를 프로젝트의 `.tools/`에 풀어 실행했습니다. 시스템 패키지·서비스 설정은 변경하지 않았습니다.

처음 도구를 준비할 때:

```bash
bash scripts/setup_postgres.sh
.venv/bin/python -m pip install -r requirements.txt
```

DB 시작과 초기 스키마 준비:

```bash
bash scripts/postgres.sh start
.venv/bin/python -B -m backend.database setup-local
```

`setup-local`은 개발 DB `nourishon`과 별도 테스트 DB `nourishon_test`, 슈퍼유저가 아닌 앱 역할을 준비합니다. 기존 DB를 삭제·초기화하지 않습니다. `.env.database`가 없을 때만 로컬 연결 설정을 생성하며 설정값을 출력하지 않습니다. 외부 DB는 `NOURISHON_DATABASE_URL` 환경변수로 별도 지정할 수 있습니다. 비밀값은 소스나 명령 출력에 넣지 마세요.

DB는 TCP 포트를 열지 않고 소유자 전용 0700 디렉터리의 Unix 소켓으로만 접근합니다. 같은 OS 사용자 권한의 로컬 도구는 신뢰하는 개발 구성입니다. 데이터와 DB 로그는 Git 제외 `.tools/`에 보관하며, 데이터 디렉터리는 0700입니다.

백엔드와 프론트엔드는 각각 실행합니다.

```bash
.venv/bin/python -B -m uvicorn backend.api:app --host 127.0.0.1 --port 8000 --no-access-log
bash scripts/frontend.sh dev
```

브라우저: http://localhost:5173/
DB 상태·종료: `bash scripts/postgres.sh status`, `bash scripts/postgres.sh stop`.

## 사용 흐름과 저장 구분

1. 화면 위에서 회원가입으로 전환합니다. 가입 아이디는 영문·숫자·밑줄 4~40자, 비밀번호는 4~128자입니다. 실명·이메일은 수집하지 않습니다.
2. 로그인 계정의 프로필을 선택하고 신체 정보를 적용합니다. DB 저장 완료 상태를 확인합니다.
3. 식사를 계산한 뒤 기록에 추가하면 계정 DB에 저장됩니다. 날짜별 분석과 측정 이력을 다시 조회할 수 있습니다.
4. 운동 계획에서 경험·가능 요일 수·시간·현재 활동량·제한 사항을 입력합니다.
5. 로그아웃·재로그인하면 서버에 저장한 기록을 다시 불러옵니다.

기존 로컬 임시 모드는 유지했습니다. 로그인해도 브라우저에 있던 다른 프로필을 자동 전송하지 않습니다. 로컬 임시 기록 가져오기는 아직 없습니다. 로그인 상태의 기록은 브라우저 localStorage에 새로 복사하지 않으며, 세션 쿠키로 사용자 계정을 확인합니다.

저장은 프로필별 리비전으로 충돌을 검사합니다. 다른 창의 최신 기록을 조용히 덮어쓰지 않습니다. 실패 시 완료로 표시하지 않고 임시 입력이 화면에만 남았다고 안내합니다. 다시 불러오기는 확인 후 서버 기록으로 돌아갑니다. 저장 대기 중에는 로그아웃을 막습니다.

저장할 때 신체 참고값·새 식사 합계·운동 계획은 서버에서 다시 계산합니다. 클라이언트가 보내는 합계는 신뢰하지 않습니다. 이미 저장된 동일 식품·섭취량 기록은 공공 데이터가 바뀌어도 당시 출처와 값을 유지합니다. 프로필별 측정·식사 변경은 하나의 트랜잭션으로 저장합니다.

## 로그인·기록 보호

- Argon2id: 메모리 19MiB, 반복 2, 병렬도 1, 개별 salt. 비밀번호 원문은 저장하지 않습니다.
- 세션은 무작위 32바이트 토큰, DB에는 SHA-256 해시로 저장합니다. 토큰은 localStorage에 저장하지 않습니다.
- HttpOnly·SameSite=Strict 쿠키, 세션 만료, 로그인 시 토큰 갱신, 로그아웃 시 서버 세션 삭제를 적용했습니다.
- 변경 요청은 허용된 로컬 Origin·사용자 정의 헤더·세션별 CSRF 토큰을 검사합니다.
- 로그인/가입 시도 제한: 15분 동안 아이디 기준 10회, IP 기준 40회. 반복 실패만이 아닌 모든 인증 시도를 셉니다.
- 모든 개인 조회·변경에서 로그인 사용자 소유권을 검사합니다. 다른 계정의 프로필 ID를 알아도 변경하거나 운동 계획을 생성할 수 없습니다.
- 개인 응답은 `Cache-Control: no-store`, 입력 검증·DB 오류는 개인 입력이나 연결 비밀값을 복사하지 않습니다. 개인 요청 본문은 2MB로 제한합니다.
- SQL 값은 매개변수로 바인딩합니다. 스키마 변경은 별도 명령으로 수행합니다.

HTTP localhost 개발용이므로 쿠키 Secure 플래그는 끈 상태입니다. 외부 서비스는 HTTPS·Secure 쿠키·운영 Origin·운영 DB 접근 정책을 별도로 갖춰야 합니다. 현재 비밀번호 재설정·이메일 확인·MFA·회원 탈퇴·백업/복구 운영 체계는 없습니다. DB 파일 자체의 암호화를 구현한 상태도 아닙니다.

근거: [OWASP 비밀번호 저장](https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html), [세션 관리](https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html), [CSRF 방어](https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html), [Psycopg 매개변수](https://www.psycopg.org/psycopg3/docs/basic/params.html), [트랜잭션](https://www.psycopg.org/psycopg3/docs/basic/transactions.html).

## 개인 활동 계획의 범위와 규칙

의료적 운동 처방·재활·인바디 기반 중량/심박수 처방이 아닌 일반 성인의 시작 계획입니다. 19~64세와 기존 프로필 적용 범위를 사용합니다. 질환·부상·통증·의사의 제한 또는 현재 증상이 있거나 잘 모르면 자동 일정을 만들지 않고 평가를 안내합니다.

정상 범위의 입력에 대해 경험·현재 활동량·가능 일수·시간·선호 활동을 반영합니다. 입문 또는 주 활동량 60분 미만이면 가능한 시간 안에서 하루 최대 10분으로 시작합니다. 기존 운동자는 현재 주간 시간/가능 일수를 참고하되 가능 시간과 기존 강도 안에서 계획합니다. 7일에 활동일을 분산하고 두 날에는 근력 활동 시간을 포함합니다. 준비·유산소·근력·정리 시간의 합이 하루 가능 시간을 넘지 않습니다.

이는 서비스의 보수적인 시작 규칙이며 공식 개인 처방식은 아닙니다. 목표는 안내 문구에 반영하며 감량을 이유로 강도를 자동 올리거나 섭취 열량 상쇄·건강 성과를 약속하지 않습니다. 낮은 강도 활동 시간을 WHO 중강도 권고량 충족으로 표시하지 않습니다. 근력 동작의 중량·세트·반복수는 자동 산출하지 않습니다.

근거: [WHO 2020 성인 신체활동](https://www.who.int/europe/news-room/fact-sheets/item/physical-activity), [NIDDK 안전한 활동 시작·중단 신호](https://www.niddk.nih.gov/health-information/weight-management/tips-get-active/tips-keep-moving).

## 검증과 오류 해결

- 백엔드 전체 검증은 별도 테스트 DB를 명시해 실행합니다. DB 설정이 없으면 DB 통합 9개는 건너뛰며 나머지를 검사합니다. 개발 DB를 테스트 초기화 대상으로 쓰지 않습니다.

```bash
NOURISHON_TEST_DATABASE_URL="host=/tmp/nourishon-postgres-$(id -u) port=55432 user=nourishon_app dbname=nourishon_test" .venv/bin/python -B -m unittest discover -s tests -q
```

- 회원·해시·쿠키·CSRF·세션 만료·로그아웃·다른 계정 접근 차단·리비전 충돌·요청 크기·스냅샷 유지와 활동 중단 조건을 검사합니다.
- 실제 브라우저에서 가입 → 프로필·식사 DB 저장 → 활동 계획 → 새로고침 → 다른 계정의 빈 기록 확인 → 첫 계정 재로그인 → 계획 유지 → 제한 사항 입력 시 자동 계획 중단을 검사합니다. 브라우저 검사가 만든 `e2e_` 연습 계정만 정리합니다.
- PostgreSQL 재시작 검증: 별도 테스트 DB에 가상 70kg 측정값을 넣고 DB를 재시작한 뒤 값이 남아 있음을 확인했습니다. 이 검증용 계정만 정리했습니다.
- 운동 제한 선택 필드의 브라우저 접근성 이름이 모호해 시나리오가 멈춘 문제는 명시적인 입력 이름으로 해결했습니다.
- 의료적 정확도·개인 운동 효과·감량 효과는 측정하지 않았습니다.

최종 실행 결과: 별도 PostgreSQL을 포함한 백엔드 82개 테스트 통과(DB 통합 9개 포함), 전체 브라우저 10개 시나리오 통과, TypeScript 검사·Vite 빌드 통과. PostgreSQL 재시작 후 가상 측정값 보존도 확인했습니다. 사용한 Python은 프로젝트 `.venv/bin/python`입니다. 스크린샷·브라우저 산출물·DB 파일은 커밋하지 않습니다.

가입 최소 길이를 아이디·비밀번호 각각 4자로 변경했습니다. 기존 3자 아이디는 로그인할 수 있도록 유지합니다. 비밀번호 Argon2id 해시 저장, 중복 아이디 거절, 시도 제한과 세션 보호는 유지합니다. 이 설정은 현재 로컬 개발용 기준입니다.

길이 변경 검증 결과: 인증 관련 Python 검사 12개 통과(2.325초), 프런트엔드 빌드 통과, 실제 브라우저 계정 시나리오 1개 통과(8.4초). 테스트 전용 DB에서 3자 가입 거절, 4자 아이디·비밀번호 가입 및 재로그인, 중복 아이디 거절을 확인했다. 브라우저에서는 4자 비밀번호 입력·가입·재로그인 및 계정 분리까지 확인했다. 테스트가 만든 가상 계정만 정리했다.
