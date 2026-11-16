#!/usr/bin/env bash
set -euo pipefail
# 저장소 루트 기준. 실제 식품·비밀값을 빌드 산출물에 복사하지 않는다.
project_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$project_root"
python -m pip install -r requirements.txt
npm ci --prefix frontend
# 테스트 서버 화면에 "가상 정보만 입력" 안내 띠를 켠다(로컬 일반 빌드에는 없음).
VITE_NOURISHON_STAGING_NOTICE=1 npm run build --prefix frontend
# 식품 정제본: 비공개 GitHub Release에서 읽기 전용 토큰으로 내려받고 SHA-256이 같을 때만 배치한다.
# data/는 Git에서 제외되며, 화면 빌드(frontend/dist)에는 복사하지 않는다.
if [ -n "${NOURISHON_FOOD_RELEASE_REPO:-}" ]; then
  python -B -m backend.food_release fetch "$project_root/data/food"
else
  echo '식품 Release 설정이 없어 내려받기를 건너뜁니다(로컬 빌드).'
fi
