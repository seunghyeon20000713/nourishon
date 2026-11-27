# 건강 비서 — Gemini API 무료 등급 연결 (2026-11-17)

개발자 결정(2026-11-17): **무료로 진행.** 가짜 AI로 전체 흐름을 먼저 완성했고(`413bdb2`, `46bdeec`), Gemini 무료 등급을 설정으로 켤 수 있게 했다. 유료 API는 나중에 같은 구조로 추가한다.

## 1. 약관·정책 확인 (공식 페이지, 2026-11-17)

출처: Gemini API Additional Terms of Service(https://aistudio.google.com/docs/terms, "Effective March 23, 2026"), 가격 페이지(https://aistudio.google.com/docs/pricing), 사용 가능 지역(https://aistudio.google.com/docs/available-regions). `ai.google.dev` 주소는 모두 `aistudio.google.com/docs`로 이동한다.

### 무료 등급(Unpaid Services)의 데이터 사용
- "Google uses the content you submit to the Services and any generated responses to provide, improve, and develop" — 무료 등급에서 보낸 질문과 답변을 Google이 제품 개선·개발에 쓴다.
- "To help with quality and improve our products, human reviewers may read, annotate, and process your API input and output." — **사람 검토자가 읽을 수 있다.**
- "Do not submit sensitive, confidential, or personal information to the Unpaid Services." — **민감·기밀·개인 정보를 보내지 말 것.**
- 유료 등급은 "Google doesn't use your prompts (...) or responses to improve our products"(악용 감지용 기록은 제한 기간 보관).
- 가격 페이지 표: 무료 "Content used to improve our products", 유료 "Content not used to improve our products".

### 건강·의료 관련 제한
- "You may not use the Services in clinical practice, to provide medical advice, or in any manner that is overseen by or requires clearance or approval from a medical device regulatory agency." — 임상·의료 조언 용도 금지.
- "Don't rely on the Services for medical, mental health, legal, financial, or other professional advice." — 전문 조언으로 의존하지 말 것.

### 그 밖의 조건
- "Use of Google AI Studio and Gemini API is for developers building with Google AI models for professional or business purposes, not for consumer use." — 개발자의 업무 목적 사용, 소비자용 아님.
- "You must be 18 years of age or older to use the APIs."
- 사용 가능 지역에 **South Korea가 포함**된다(무료·유료 구분 없이 표시).
- 유럽경제지역·스위스·영국 사용자에게는 유료 서비스만 제공해야 한다(서비스 대상 아님).
- 무료 등급의 모델별 분당·하루 요청 수는 로그인 후 AI Studio에서만 보인다(공식 문서에 수치 없음). 그래서 서버에 하루 질문 수 제한(사용자 20·전체 200)을 따로 둔다.

### 이 서비스에 주는 의미 (개발자가 알고 결정해야 할 위험)
| 약관 내용 | 우리 대응 | 남는 위험 |
| --- | --- | --- |
| 무료 등급 입력은 개선·사람 검토에 쓰임, 개인정보 금지 | 질문·도구 숫자만 전송(아이디·닉네임·프로필 ID·음식 이름 제외, 테스트로 확인). 질문 속 아이디·닉네임은 '사용자'로 치환. 입력창에 전송 안내. 테스트 서버는 가상 정보만 쓰도록 안내 중 | 사용자가 질문에 실제 증상·이름을 직접 쓰면 막을 수 없다(안내만 가능). 기록 숫자 자체도 건강 관련 정보다 |
| 의료 조언 제공 금지 | 진단·처방·약·질환 질문은 AI 호출 없이 거절, 안내문에 "진단·치료 아님" | 영양 설명이 의료 조언으로 받아들여질 여지 |
| 소비자용 아님(개발자 업무 목적) | 포트폴리오 테스트 서버, 지인 소수, 가상 정보 | **지인에게 공개하는 것이 '소비자 사용'에 해당할 수 있다.** 약관 해석은 이 문서가 판단할 수 없다 |

권장 운영: 테스트 서버의 기본값은 **가짜 AI(`fake`)** 로 두고, Gemini는 개발자가 가상 데이터로 시연할 때만 켠다. 지인 공개 중 Gemini를 켤지는 위 위험을 보고 개발자가 결정한다. 실제 서비스로 확장하면 유료 등급(개선에 쓰지 않음)으로 바꾼다.

## 2. 구현 요약

- 방식: `POST https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent`(공식 문서상 계속 지원, 새 개발에는 Interactions API를 권장하는 "legacy"). 표준 라이브러리 `urllib`만 써서 새 의존성 없음. → 추후 Interactions API로 옮길 수 있음(백로그).
- 모델: 기본 `gemini-3.1-flash-lite`(공식 모델 페이지: 함수 호출 지원, 가격 페이지: 무료 등급 "Free of charge"). `NOURISHON_GEMINI_MODEL`로 변경.
- API 키는 URL이 아니라 `x-goog-api-key` 헤더로 보낸다(로그·오류에 남지 않게).
- Gemini 3의 `thoughtSignature`: 모델 응답 부분을 그대로 다시 보내고, 함수 결과에 같은 `id`를 붙인다(공식 문서 요구, 테스트로 확인).
- 실패(키 없음·429 사용량 초과·네트워크·형식 오류)나 도구 결과에 없는 숫자 → 가짜 AI 답변으로 자동 전환하고 "AI 응답을 받지 못해 기본 설명으로 답했어요" 안내.

## 3. 설정 (Render 환경변수 — 비밀값은 Render에만)

| 이름 | 값 | 비고 |
| --- | --- | --- |
| `NOURISHON_AI_PROVIDER` | `fake`(기본) 또는 `gemini` | 이 값 하나로 전환 |
| `NOURISHON_GEMINI_API_KEY` | (AI Studio에서 발급한 키) | **Git·채팅·스크린샷 금지.** Render Environment에만 입력 |
| `NOURISHON_GEMINI_MODEL` | `gemini-3.1-flash-lite` | 생략 가능 |
| `NOURISHON_AI_DAILY_LIMIT` | `20` | 사용자별 하루 질문 수 |
| `NOURISHON_AI_SERVICE_DAILY_LIMIT` | `200` | 서비스 전체 하루 질문 수 |

## 4. 배포 순서 (중요)

`/api/ready`가 DB 마이그레이션 3(`assistant_usage`)을 요구한다. **Render 배포 전에** Neon DB를 먼저 준비해야 한다(안 하면 새 버전 상태 확인이 실패하고 Render는 이전 버전을 유지한다).
1. `git push` → GitHub Actions(PostgreSQL 16·18) 통과 확인
2. WSL, 프로젝트 루트, `.venv/bin/python -B scripts/prepare-staging-db.py` → 소유자 연결 문자열을 숨김 입력(마이그레이션 3 적용, 앱 역할 권한 갱신, 앱 비밀번호 유지)
3. Render → Manual Deploy → Deploy latest commit
4. (Gemini를 켤 때만) Render 환경변수 추가 → 저장 후 재배포

## 5. API 키 발급 (개발자 직접 — 여기서 멈춤)

결제수단 없이 무료 등급으로 시작한다. **"결제 설정(Set up billing)"·"유료 등급으로 업그레이드" 버튼은 누르지 않는다**(누르면 유료 조건·최소 $5 선불이 된다).
1. 브라우저에서 https://aistudio.google.com 접속 → Google 계정으로 로그인(만 18세 이상 계정).
2. 처음이면 약관 동의 화면이 나온다 → 위 1장의 무료 등급 조건을 확인하고 동의.
3. 왼쪽 메뉴(또는 오른쪽 위)의 **"Get API key"** → **"Create API key"**.
   - 프로젝트를 고르라고 하면 새 프로젝트(예: `nourishon-dev`)를 만든다. 결제 계정은 연결하지 않는다.
4. 만들어진 키 옆 복사 버튼을 누른다. **채팅·메모 앱·Git에 붙여넣지 않는다.**
5. Render 대시보드 → `nourishon-staging` → Environment → Add Environment Variable
   - `NOURISHON_GEMINI_API_KEY` = 복사한 키 → Save
   - `NOURISHON_AI_PROVIDER` = `gemini`(지금 켤 때만. 기본은 `fake`로 두는 것을 권장)
6. 키가 유출됐다고 생각되면 AI Studio의 API keys 화면에서 해당 키를 삭제하고 새로 만든다.
7. 확인: 스테이징에서 가상 계정으로 "이번 주 나트륨 어때?" → 답변 옆 표시가 **Google AI**이면 연결 성공, **기본 설명** + "AI 응답을 받지 못해…" 안내면 키·모델 이름·사용량을 확인.

## 6. 스테이징 배포 확인 (2026-11-27, `6c70fc5`)

- 순서: GitHub 푸시 → CI(PostgreSQL 16·18) 통과 → 개발자가 Neon에 마이그레이션 3 적용(`prepare-staging-db.py`, 앱 역할 비밀번호 유지) → Render 수동 배포.
- 결과(가상 계정으로 확인 후 탈퇴, 제공자 `fake`):
  - `/api/ready` 200(마이그레이션 3 포함 확인), `/api/assistant/status` 비로그인 401
  - "이번 주 나트륨 어때?" → 도구 2개 호출, "5일 중 2일 기록" 기준 합계·기록일 평균·WHO 기준 설명
  - "어제 단백질 충분해?" → 날짜 하나로 표시, 단백질 참고값 비교
  - "당뇨인지 진단해줘" → 거절, 도구 호출 0회
  - 하루 남은 질문 20 → 17로 차감(DB 기록 정상), 탈퇴 시 정리
- 캡처: [staging/](design/assistant/staging/) — 대시보드·건강 비서(데스크톱·모바일)
- Gemini 실제 호출은 아직 하지 않았다(키 미발급, 기본값 `fake` 유지).
