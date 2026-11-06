#!/usr/bin/env bash
set -eu
project_dir="$(cd "$(dirname "$0")/.." && pwd)"
pg_root="$project_dir/.tools/postgres"
pg_bin="$pg_root/usr/lib/postgresql/16/bin"
pg_data="$project_dir/.tools/pgdata"
pg_socket="/tmp/nourishon-postgres-$(id -u)"
export LD_LIBRARY_PATH="$pg_root/usr/lib/x86_64-linux-gnu${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
if [ ! -x "$pg_bin/pg_ctl" ]; then
  echo 'PostgreSQL 도구가 없습니다. docs/accounts-and-storage.md의 설치 안내를 확인하세요.' >&2
  exit 1
fi
case "${1:-status}" in
 start)
  mkdir -p "$pg_socket"
  chmod 700 "$pg_socket"
  if [ ! -f "$pg_data/PG_VERSION" ]; then
    "$pg_bin/initdb" -D "$pg_data" -L "$pg_root/usr/share/postgresql/16" --username=nourishon_owner --encoding=UTF8 --no-locale --auth-local=trust --auth-host=reject > "$project_dir/.tools/postgres-init.log"
  fi
  if "$pg_bin/pg_ctl" -D "$pg_data" status >/dev/null 2>&1; then
    echo '로컬 PostgreSQL이 이미 실행 중입니다.'
  else
    "$pg_bin/pg_ctl" -D "$pg_data" -l "$project_dir/.tools/postgres.log" -o "-k $pg_socket -p 55432 -c listen_addresses='' -c unix_socket_permissions=0700" -w start
  fi
  ;;
 stop) "$pg_bin/pg_ctl" -D "$pg_data" -m fast -w stop ;;
 status) "$pg_bin/pg_ctl" -D "$pg_data" status ;;
 *) echo '사용법: bash scripts/postgres.sh start|stop|status' >&2; exit 1 ;;
esac
