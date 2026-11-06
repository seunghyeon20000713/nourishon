# 세 번째 시안 적용 · 2026-11-06

## 선택한 방향

사용자가 선택한 세 번째 이미지 ‘기록으로 보는 나의 영양’을 기존 React 앱에 적용했습니다. 새 앱을 만들거나 DB·계산 로직을 교체하지 않았습니다. 기준 이미지는 [승인 시안](design/nutrition-journal-reference.png)입니다.

- 흰색·짙은 초록, 좁은 아이콘 메뉴, 상단 브랜드·기록 버튼·프로필/계정 메뉴.
- 첫 화면은 기록된 열량·유지 에너지 참고, 탄수화물·단백질·지방의 비율/참고 범위 차트.
- 왼쪽은 분석과 주간 기록, 오른쪽은 기록 해석·다음 식사·나트륨·판단 근거.
- 식사 입력은 기존 음식 검색·섭취량 계산 화면으로 이동합니다. 가입·설정 폼은 메뉴 안에 보존합니다.
- 390px 모바일은 상단 아이콘 메뉴와 1열로 재배치합니다.

## 실제 데이터 연결

디자인의 1,500kcal·55/18/27% 같은 예시를 기본 데이터로 넣지 않았습니다. 기록이 없으면 비어 있는 상태, 누락·불일치는 평가 보류를 표시합니다. 미래 날짜는 ‘예정’, 과거 미기록은 ‘미기록’입니다. 나트륨과 소금을 같은 이름으로 표시하지 않습니다.

비율은 기존 Python 영양 검토 API 응답을 사용합니다. Recharts 3.10.1의 실제 데이터 차트로 표시하며 정적인 시안 이미지를 웹 화면으로 붙이지 않습니다. 주간 차트는 기록된 값만 표시하고, 읽을 수 있는 날짜·기록 수·설명과 키보드 탐색을 제공합니다.

대시보드 코드는 지연 로딩합니다. 로그인·DB·프로필별 기록 분리·운동 계획·브라우저 보관은 기존 동작을 유지합니다. 메뉴는 바깥 클릭/Escape로 닫히며, 저장 오류는 메뉴를 닫아도 보입니다.

## 자산과 생성 기록

- 선택 시안: `docs/design/nutrition-journal-reference.png` (가상 데이터가 표시된 원본).
- 실제 UI 로고 자산: `frontend/public/brand/nourishon-mark.png`.
- 기존 Lucide 아이콘과 로컬 Noto Sans KR/Manrope 폰트를 유지합니다.
- 로고는 기본 제공 Image Gen 도구로 생성했고 별도 API 키·CLI를 쓰지 않았습니다. 사용자 기록이나 인증키를 전송하지 않았습니다. 원본 모형을 참고해 N·잎 모양 자산만 추출했습니다.

최종 로고 생성 프롬프트:

```text
Extract and faithfully reproduce ONLY the small NourishOn brand symbol at the extreme top-left of the supplied approved dashboard image: a bold compact uppercase geometric N in dark forest green #174B3B with one small green leaf attached near its top right. A single isolated transparent-background logo asset, square 256x256 canvas, centered with generous even transparent padding. Preserve that reference mark's shape and clean flat rendering. No other text, no wordmark, no interface, no background, no shadow, no gradients. This is a precise logo asset extraction for the existing dashboard, not a redesign.
```

실제 생성 파일은 1280px 캔버스의 투명 PNG였으며, 원본을 보존하고 표시 크기를 CSS에서 조정했습니다. 시안의 원본 글자 오류나 식품 예시를 사용자 데이터로 복사하지 않았습니다.

## 검증·오류 해결

- TypeScript 검사와 Vite 빌드 통과, 전체 브라우저 12개 시나리오 통과.
- 시안과 1440×1024 구현을 같은 크기로 전체·차트 확대 비교했고 390px 모바일의 가로 넘침도 검사했습니다. [디자인 QA](../design-qa.md)에 수정 이력을 남겼습니다.
- 첫 실행 때 로컬 API가 꺼져 연결 검사가 실패한 것은 API를 시작해 해결했습니다.
- 비율 차트에 데이터 시리즈가 없어 축만 보인 것은 실제 시리즈와 축 연결을 수정해 해결했습니다. 선·지점이 실제로 렌더링되는지도 검사합니다.
- 초기 단일 JS 번들 크기 경고는 대시보드 지연 로딩으로 해소했습니다.
- 테스트의 버튼 경로는 새 메뉴에 맞춰 갱신하되 가입·저장·계산·개인 기록 보호에 대한 기존 검증은 유지했습니다.

로컬 서버만 실행하며 외부 배포는 하지 않았습니다. QA 스크린샷은 가상 기록으로 생성해 `/tmp`에만 보관하고 실제 계정·신체 정보·DB는 업로드하지 않습니다.
