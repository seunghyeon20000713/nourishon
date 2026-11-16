# 식품 정제본 비공개 배포 · 2026-11-16

## 왜 필요한가

식품 정제본(`foods.json` + `report.json`)은 Git에서 제외한다. 그래서 Render가 GitHub 코드를 받아 빌드할 때 이 파일이 없다. 무료 Render는 SSH가 없어 직접 넣을 수도 없다. 비공개 위치에서 빌드 중에 안전하게 받아 오는 방법이 필요하다.

## 결정과 대안

| 방식 | 판단 |
| --- | --- |
| **비공개 GitHub 저장소 Release 첨부 + 세분화 토큰 + SHA-256 검증 (선택)** | 새 서비스 가입·결제 없음. 토큰은 그 저장소만, Contents 읽기 전용, 만료일 지정 |
| 비공개 객체 저장소(R2/S3) | 외부 계정·결제 수단 등록 가능성. 무료 원칙에 비해 관리 부담 |
| 빌드 때 식약처 API 재수집 | 느리고 호출 한도 위험, 검증한 정제본과 같다는 보장이 없음 |

Release 첨부는 커밋과 달리 파일당 100MB 제한이 적용되지 않는다. 그래도 압축해 크기를 줄였다.

## 동작

`backend/food_release.py` (표준 라이브러리만 사용)

- `package`: `foods.json`·`report.json`만 tar.gz로 묶는다. 시간·소유자 정보를 고정해 같은 입력이면 항상 같은 SHA-256이 나온다. `quarantine.jsonl` 등 다른 파일은 넣지 않는다.
- `fetch`: 환경변수의 저장소·태그·파일 이름으로 Release 정보를 조회한다 → 첨부 파일을 받는다 → SHA-256을 비교한다 → 일치할 때만 `data/food/`에 배치한다.
  - GitHub은 첨부 파일을 서명된 임시 주소로 돌려보낸다(리다이렉트). 자동 리다이렉트를 끄고, 그 주소에는 **GitHub 토큰을 보내지 않는다.**
  - 해시 불일치·파일 구성 이상(`../` 경로, 링크, 추가 파일, 한 파일 누락)이면 아무것도 배치하지 않고 임시 파일을 지운다. 기존 데이터는 새 파일 준비가 끝난 뒤에만 교체한다.
  - 오류 메시지에 토큰·서명 주소를 넣지 않는다. 크기는 Release 정보의 값과 1GiB 상한을 넘으면 중단한다.
- `scripts/build-staging.sh`: `NOURISHON_FOOD_RELEASE_REPO`가 있으면 `fetch`를 실행한다. 없으면(로컬 빌드) 건너뛴다고 출력한다.
- `scripts/start-staging.sh`: 서버 시작 직전에 `NOURISHON_FOOD_RELEASE_TOKEN`을 환경에서 지운다. Render는 빌드와 실행에 같은 환경변수를 주기 때문에, 실행 중인 서버에는 토큰을 남기지 않는다.

## 검증 (로컬)

- 가짜 GitHub 서버 테스트 9개 통과: 정상 배치, 서명 주소에 토큰 미전송, 해시 불일치 시 미배치, 실패 시 기존 데이터 유지, 성공 시 교체, 오류에 토큰·서명 주소 미노출, 경로 조작·누락·추가 파일 거부, 잘못된 입력은 네트워크 전에 거부, 묶음 재현성.
- 실제 정제본 묶음: 원본 `foods.json` 149,361,969 bytes → 묶음 11,149,575 bytes. 두 번 묶어 같은 SHA-256 `f8e6b1ce6f92e31ebd6271311b6a1c3bf0b07fe917228a4502d6f74e55656657`. 묶음 안의 두 파일이 원본과 SHA-256 일치.
- 묶음은 `data/release/`(Git 제외)에 있다.
- 실제 GitHub 확인(2026-11-16, 로컬 PC에서 실행): 비공개 저장소 `nourishon-food-data`(PRIVATE 확인)에 Release `food-20261105`를 만들고 묶음(11,149,575 bytes)을 첨부했다. `fetch`로 실제 내려받아 SHA-256 일치·`foods.json` 원본과 바이트 동일을 확인했다. 해시를 틀리게 주면 미배치, 잘못된 토큰은 HTTP 401로 중단하고 비밀값을 출력하지 않았다. 이 확인에는 개발자 PC의 `gh` 로그인 토큰을 사용했다. Render용 세분화 토큰과 Render 빌드 환경에서의 실행은 아직이다.

## 개발자가 직접 할 일 (계정 작업)

1. ~~비공개 저장소 생성~~ 완료: `seunghyeon20000713/nourishon-food-data` (PRIVATE)
2. ~~Release 생성·첨부~~ 완료: 태그 `food-20261105`, 첨부 `food-data-20261105.tar.gz`
3. GitHub Settings → Developer settings → Personal access tokens → **Fine-grained tokens**에서 토큰을 만든다.
   - Repository access: **Only select repositories** → 위 비공개 저장소 하나만
   - Permissions: Repository permissions → **Contents: Read-only** (Metadata: Read-only는 자동 포함). 나머지는 모두 No access
   - Expiration: 만료일 지정(예: 90일). 만료 전에 새로 발급해 Render 설정만 바꾼다.
4. 토큰 값은 채팅·GitHub·문서에 붙여넣지 않는다. Render 환경변수 화면에만 입력한다.
