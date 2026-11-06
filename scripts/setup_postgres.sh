#!/usr/bin/env bash
# Ubuntu 24.04 x86_64용 프로젝트 전용 도구 설치. sudo·시스템 서비스 변경 없음.
set -euo pipefail
project_dir="$(cd "$(dirname "$0")/.." && pwd)"
mkdir -p "$project_dir/.tools/postgres-download" "$project_dir/.tools/postgres"
cd "$project_dir/.tools/postgres-download"
apt-get download postgresql-16 postgresql-client-16 libpq5 libllvm17t64 libldap2
for package in *.deb; do
  dpkg-deb -x "$package" "$project_dir/.tools/postgres"
done
printf '%s\n' 'PostgreSQL 로컬 도구 준비 완료. bash scripts/postgres.sh start로 시작하세요.'
