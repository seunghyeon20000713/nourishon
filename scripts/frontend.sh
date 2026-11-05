#!/usr/bin/env bash
set -euo pipefail
project_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
if ! command -v node >/dev/null 2>&1; then
  node_bin="$project_root/.tools/node-v24.22.2-linux-x64/bin"
  if [[ ! -x "$node_bin/node" ]]; then
    echo "Node.js 24 LTS를 설치한 뒤 다시 실행해주세요." >&2
    exit 1
  fi
  export PATH="$node_bin:$PATH"
fi
cd "$project_root/frontend"
if [[ $# -eq 0 ]]; then set -- dev; fi
exec npm run "$@"
