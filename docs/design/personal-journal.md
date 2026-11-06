# 개인 기록장 디자인 적용 · 2026-11-06

사용자가 선택한 두 번째 시안을 기준으로 로컬 대시보드를 수정했다. 밝은 종이색 바탕과 짙은 초록, 구분선과 숫자 중심의 구성으로 반복되는 상단 카드 세 개를 대체했다. 기능 추가보다 몸의 기록과 식사 요약을 먼저 읽을 수 있게 하는 것이 이번 범위다.

## 화면과 데이터

- 왼쪽: 최근 체중, 직전의 다른 측정일 대비 차이, 최근 12개 측정일의 체중 추이, 최근 측정의 골격근량·체지방량·체지방률.
- 오른쪽: 선택일의 기록된 열량·단백질·식이섬유·나트륨, 식사·운동 기록과 내 정보 수정 바로가기.
- 아래: 최근 5개 측정일 표, 현재 프로필 기준 BMI와 계산에 사용한 키·체중. 기존 영양 비율·주간 기록·근거 설명은 그 아래 유지했다.
- 기존 N 로고→소개, NourishOn→메인, 양쪽 햄버거 메뉴와 로그인·프로필 전환을 유지했다. 따라서 상단 계정 도구와 기본 접힌 메뉴는 시안과 차이가 있다. 펼친 메뉴의 너비는 210px이다.
- 850px 이하에서는 본문을 한 열로 바꾸며, 측정 표만 내부에서 가로 스크롤한다. 모바일 하단 메뉴는 유지한다.

선택일까지의 측정만 표시하며 같은 날 여러 기록은 배열의 마지막 항목을 표시한다. 이 규칙은 측정 원본을 합치거나 삭제하지 않는다. 최신 측정에서 빠진 체성분은 과거 값으로 채우지 않는다. 체지방량·체지방률 0은 `0.0`, 없는 값은 `미등록`으로 구분한다. 다른 날짜의 비교값이 없으면 변화량을 만들지 않는다. 그래프의 가로축은 실제 측정 날짜 간격이다.

BMI는 현재 프로필의 기존 계산 결과이므로 선택일의 이력과 같다고 가정하지 않는다. 프로필 기준임과 키·체중을 함께 표시한다. 변화량에 좋음·나쁨이나 건강 점수를 붙이지 않는다. 식사 합계는 기록된 양이며 전체 섭취량으로 단정하지 않는다. 서버 저장 구조·영양 공식은 변경하지 않았다.

## 파일 역할

- `frontend/src/BodyOverview.tsx`: 측정 이력·식사 요약과 바로가기. 기존 사용자 데이터만 읽는다.
- `frontend/src/personal-journal.css`: 선택 시안의 색·타이포그래피·간격과 반응형 배치. 기존 CSS 뒤에서 적용한다.
- `frontend/src/Dashboard.tsx`: 새 요약을 기존 영양 분석보다 앞에 배치한다.
- `backend/web.py`: 배포 진입점에서 새 장식 PNG 하나만 명시적으로 제공한다. 저장소 폴더 전체를 공개하지 않는다.

## 이미지

[선택한 시안](personal-journal-reference.png)은 built-in Image Gen으로 만든 미리보기다. 모든 수치·측정 기록은 가상이며 제품의 초기값이나 실제 이용자 정보가 아니다.

장식 파일: `frontend/public/decoration/journal-sprig.png`. built-in Image Gen으로 별도 생성한 투명 배경 수채화 가지다. 생성 프롬프트: “A single delicate botanical olive-sage leafy twig with three tiny muted terracotta berries, watercolor botanical illustration for NourishOn nutrition personal journal UI. Isolated transparent background. Branch curves diagonally lower-left to upper-right, about 8 slender sage leaves, tasteful soft restrained ink and wash, light olive green, no text, no frame, no shadow. Small decorative corner asset, airy elegant, not a logo. Transparent PNG.” 기존 브랜드 로고·로컬 글꼴·아이콘 라이브러리는 재사용했다.

## 실제 검증

- 프런트엔드 일반 빌드 성공.
- 전체 Playwright 브라우저 테스트 26개 통과, 42.6초. 계정·검색·영양·식사·운동·기록 관리의 기존 흐름 포함.
- 마지막 간격 조정 후 대시보드 두 검증 재통과, 5.2초. 가상 기록으로 날짜 선택, 변화량, 최신 값·미등록·0 구분, 미래 제외, 같은 날 마지막 항목, 식사 이동, 390px 가로 넘침과 JS 오류 없음 확인.
- 배포 경로 테스트 3개 통과. 장식 이미지 응답, 다른 이미지 경로·비공개 파일 접근 차단 포함.
- 최초 검증에서 모바일 측정 표가 본문 너비를 늘린 문제를 찾았다. 그리드 자식의 최소 너비를 0으로 하고 표 내부 스크롤로 수정했다.
- 시안 비교에서 측정 표가 첫 화면 아래로 밀린 문제를 찾아 상단·본문 간격을 줄이고 재촬영했다. 최종 비교는 프로젝트 루트 `design-qa.md`에 기록했다.

로그인하지 않은 새 브라우저와 가상 데이터만 사용했다. 실제 개인정보·인증키·식품 원본은 추가하거나 공개하지 않았다. 공개 Sites 체험판은 이번 작업에서 갱신하지 않았다.
