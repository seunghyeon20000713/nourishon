# 개인 기록장 디자인 QA · 2026-11-06

- source visual truth: `docs/design/personal-journal-reference.png` (선택한 2번째 이미지)
- implementation: `http://127.0.0.1:5173/#dashboard`
- implementation screenshot: `/tmp/nourishon-journal-v2-desktop.png`
- mobile screenshot: `/tmp/nourishon-journal-v2-mobile.png`, 빈 상태 `/tmp/nourishon-journal-v2-empty-mobile.png`
- viewport: desktop 1440×1024 CSS px, mobile 390×844 CSS px, deviceScaleFactor 1.
- source pixels: 1487×1058. 구현: 1440×1024. 전체 비교에서 각 이미지를 720×512 영역에 비율 유지하여 정규화했다. 사진·브라우저 프레임 없음.
- state: 비로그인 로컬 프로필, 2026-11-06 선택, 메뉴 펼침. 시안과 같은 가상 체중·체성분 5개 측정일과 식사 합계를 주입. 초기 제품에는 이 수치가 채워지지 않는다.
- full-view comparison evidence: `/tmp/nourishon-journal-v2-comparison.png` 상단에 시안과 최종 화면을 나란히 배치해 직접 확인.
- focused comparison evidence: 같은 이미지 하단에 몸의 기록·그래프·체성분 영역을 확대하여 나란히 비교. 글자·단위·배치·구분선을 확인.

## Findings / comparison history

1. [P2, 수정 완료] 모바일의 표 최소 너비가 그리드 전체 너비를 늘림. `min-width:0`과 표 내부 스크롤로 수정. 이후 두 신규 브라우저 검증에서 390px 문서 너비가 뷰포트 이내임을 확인. 빈 화면도 별도 촬영·확인했다.
2. [P2, 수정 완료] 첫 비교에서 상단과 일기 영역의 세로 간격 때문에 측정표가 첫 화면에서 밀림. 수정 전 `/tmp/nourishon-journal-v2-desktop-before-spacing.png`, 비교 `/tmp/nourishon-journal-v2-comparison-before-spacing.png`. 상단 높이·여백·그래프 높이·일기 간격을 줄였고 위 최종 스크린샷과 합성 비교에서 최근 다섯 측정일이 첫 화면에 보임을 확인했다.
3. 최종 비교: 몸의 기록→체중 추이→체성분→측정표의 순서, 오른쪽 일기, 종이색 바탕·초록 강조·구분선 구성이 선택 시안과 일치한다. 수치와 단위가 분리되고 표와 그래프에 겹침이 없다. 해결하지 않은 P0/P1/P2 항목 없음.

## Intentional adaptations

- 기존 요청인 N→소개/NourishOn→메인, 접고 펴는 양쪽 메뉴, 로그인·내 정보 도구를 보존했다. 시안의 로고 위치·상단과 다르다. 메뉴를 펼친 상태를 시안과 비교했으며 기본 상태는 이전처럼 접힘이다.
- 실제 기능을 위한 식사 추가 버튼·미기록 안내·BMI 프로필 기준 설명을 추가했다. 실제 기록에서 그래프 축 범위와 식사 건수가 시안과 달라지는 것은 데이터에 따른 동작이다.
- 체중 차이에 건강 평가 의미가 생기지 않도록 시안의 주황색 대신 중립적인 회녹색을 사용했다.
- 장식 가지는 별도 생성한 PNG를 일기 우측 모서리에 사용했고, 좌측 메뉴 바닥의 추가 장식은 생략했다.

## Interaction / accessibility checks

브라우저 전체 26개 통과. 최종 간격 조정 후 대시보드 두 검증 재통과. 주요 흐름은 날짜 변경·기록 필터·식사 추가·운동 기록·내 정보·메뉴·계정·프로필 전환·N/워드마크 이동·모바일 이동. 새 대시보드 시나리오의 pageerror 0건. 없는 값/0/단일 측정/미래 제외를 구분했다. 표는 자체 가로 스크롤과 키보드 포커스를 지원한다. 그래프와 측정표를 함께 제공하며 초록만으로 좋음·나쁨을 전달하지 않는다.

## Follow-up polish

P3: 장식 PNG의 용량과 글자 간격은 다음 시각 피드백에 맞춰 추가로 다듬을 수 있다. 별도 보조기기 사용자의 실제 사용성 평가는 아직 수행하지 않았다.

final result: passed
