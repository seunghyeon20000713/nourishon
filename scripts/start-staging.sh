#!/usr/bin/env bash
set -euo pipefail
# 호스팅 서비스가 제공한 PORT 사용. 접근 로그에 사용자 검색·기록 URL을 남기지 않는다.
exec python -m uvicorn backend.web:app --host 0.0.0.0 --port "${PORT:-8000}" --workers 1 --no-access-log
