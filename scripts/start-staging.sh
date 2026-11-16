#!/usr/bin/env bash
set -euo pipefail
# 호스팅 서비스가 제공한 PORT 사용. 접근 로그에 사용자 검색·기록 URL을 남기지 않는다.
# 빌드 때만 쓰는 Release 토큰은 실행 중인 서버 환경에 남기지 않는다.
unset NOURISHON_FOOD_RELEASE_TOKEN
exec python -m uvicorn backend.web:app --host 0.0.0.0 --port "${PORT:-8000}" --workers 1 --no-access-log
