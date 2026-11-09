#!/usr/bin/env bash
set -euo pipefail
# 저장소 루트 기준. 실제 식품·비밀값을 빌드 산출물에 복사하지 않는다.
project_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$project_root"
python -m pip install -r requirements.txt
npm ci --prefix frontend
npm run build --prefix frontend
