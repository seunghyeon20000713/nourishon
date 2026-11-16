"""CI 전용: 일회용 PostgreSQL에 앱 역할을 만들고 마이그레이션·권한을 적용한다.

GitHub Actions의 서비스 컨테이너(테스트 동안만 존재하는 임시 DB)에서만 사용한다.
로컬 개발 DB는 `python -B -m backend.database setup-local`을 사용한다.
설정값(연결 문자열·비밀번호)은 출력하지 않는다.
"""
import os
import sys
from pathlib import Path

import psycopg
from psycopg import sql
from psycopg.conninfo import conninfo_to_dict

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backend.database import connect, grant_app_role, migrate  # noqa: E402

APP_ROLE = 'nourishon_app'


def main() -> int:
    owner_dsn = os.environ.get('NOURISHON_CI_OWNER_DATABASE_URL')
    app_password = os.environ.get('NOURISHON_CI_APP_PASSWORD')
    if not owner_dsn or not app_password:
        print('NOURISHON_CI_OWNER_DATABASE_URL과 NOURISHON_CI_APP_PASSWORD가 필요합니다.', file=sys.stderr)
        return 1
    # 테스트 코드와 같은 안전장치: 테스트 전용 DB 이름이 아니면 멈춘다.
    if conninfo_to_dict(owner_dsn).get('dbname') != 'nourishon_test':
        print('CI 준비는 nourishon_test DB에서만 실행합니다.', file=sys.stderr)
        return 1

    with psycopg.connect(owner_dsn, autocommit=True) as conn:
        exists = conn.execute('SELECT 1 FROM pg_roles WHERE rolname=%s', (APP_ROLE,)).fetchone()
        if not exists:
            # CREATE ROLE 같은 관리 명령은 %s 바인딩을 지원하지 않는다.
            # 그래서 psycopg.sql로 이름·값을 안전하게 따옴표 처리해 조립한다(문자열 이어붙이기 아님).
            conn.execute(sql.SQL('CREATE ROLE {} LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE PASSWORD {}').format(
                sql.Identifier(APP_ROLE), sql.Literal(app_password)))

    migrate(owner_dsn)
    grant_app_role(owner_dsn, APP_ROLE)

    # 앱 역할이 실제로 접속되고, 스키마를 바꿀 권한은 없는지 확인한다.
    app_dsn = psycopg.conninfo.make_conninfo(owner_dsn, user=APP_ROLE, password=app_password)
    with connect(app_dsn) as conn:
        can_create = conn.execute("SELECT has_schema_privilege(current_user, 'public', 'CREATE') AS ok").fetchone()['ok']
    if can_create:
        print('앱 역할에 스키마 생성 권한이 남아 있습니다.', file=sys.stderr)
        return 1
    print('CI 테스트 DB 준비 완료: 마이그레이션 적용, 앱 역할은 테이블 읽기·쓰기만 허용')
    return 0


if __name__ == '__main__':
    sys.exit(main())
