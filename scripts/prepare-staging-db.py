"""외부 테스트 DB(Neon 등) 준비: 마이그레이션 적용 + 권한이 좁은 앱 역할 생성.

개발자가 자기 터미널에서 직접 실행한다. 소유자 연결 문자열은 환경변수로만 받고 저장하지 않는다.
  NOURISHON_MIGRATION_DATABASE_URL  소유자 연결(마이그레이션·역할 생성에만 사용)

출력: Postgres 버전·DB 이름·진행 결과. 앱 역할 비밀번호는 새로 만들 때(또는 --rotate-password) 한 번만
앱 연결 문자열로 출력한다. 이 값은 Render 비밀 설정에만 입력하고 채팅·Git·스크린샷에 남기지 않는다.
"""
import argparse
import os
import secrets
import sys
from pathlib import Path

import psycopg
from psycopg import sql
from psycopg.conninfo import conninfo_to_dict, make_conninfo

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backend.database import connect, grant_app_role, migrate  # noqa: E402

APP_ROLE = 'nourishon_app'
# CI가 두 버전 모두에서 전체 테스트를 실행한다(.github/workflows/backend-tests.yml).
SUPPORTED_MAJORS = (16, 18)


class PrepareError(Exception):
    """비밀값을 담지 않는 오류."""


def direct_connection(dsn: str) -> tuple[str, bool]:
    """Neon 풀링 주소(엔드포인트 이름 뒤 -pooler)를 직접 연결 주소로 바꾼다.

    마이그레이션·역할 생성과 worker 1개 서버에는 중계기(PgBouncer) 없는 직접 연결이 단순하고 확실하다.
    """
    options = conninfo_to_dict(dsn)
    host = options.get('host') or ''
    first, _, rest = host.partition('.')
    if first.endswith('-pooler') and rest.endswith('neon.tech'):
        return make_conninfo(dsn, host=f"{first.removesuffix('-pooler')}.{rest}"), True
    return dsn, False


def check_owner_dsn(dsn: str, require_remote: bool = True) -> dict:
    try:
        options = conninfo_to_dict(dsn)
    except Exception:
        raise PrepareError('연결 문자열 형식을 확인하세요.') from None
    if require_remote:
        if options.get('sslmode') not in {'require', 'verify-ca', 'verify-full'}:
            raise PrepareError('외부 DB는 sslmode=require 이상이 필요합니다. Neon 연결 문자열을 그대로 복사했는지 확인하세요.')
        host = options.get('host') or ''
        if not host or host.startswith('/') or host in {'localhost', '127.0.0.1', '::1'}:
            raise PrepareError('로컬 DB가 아닌 외부 DB 연결 문자열이 필요합니다.')
    if options.get('user') == APP_ROLE:
        raise PrepareError('앱 역할이 아니라 소유자(예: neondb_owner) 연결 문자열이 필요합니다.')
    return options


def prepare(owner_dsn: str, role: str = APP_ROLE, rotate: bool = False, require_remote: bool = True,
            supported: tuple[int, ...] | None = SUPPORTED_MAJORS, out=print) -> str | None:
    """마이그레이션·역할·권한을 적용한다. 새 비밀번호를 만들었으면 앱 연결 문자열을 돌려준다."""
    check_owner_dsn(owner_dsn, require_remote)
    owner_dsn, changed = direct_connection(owner_dsn)
    if changed:
        out('풀링 주소를 직접 연결 주소로 바꿔 사용합니다.')
    try:
        with psycopg.connect(owner_dsn, autocommit=True, connect_timeout=15) as conn:
            info = conn.execute('SELECT current_setting(%s)::int AS num, current_database() AS db',
                                ('server_version_num',)).fetchone()
            major = info[0] // 10000
            out(f'접속 성공: PostgreSQL {major}, DB 이름 {info[1]}')
            if supported and major not in supported:
                versions = '·'.join(map(str, supported))
                raise PrepareError(f'CI로 검증한 PostgreSQL {versions}만 허용합니다(현재 {major}). 변경 없이 종료합니다.')
            exists = conn.execute('SELECT 1 FROM pg_roles WHERE rolname=%s', (role,)).fetchone()
            password = None
            if not exists or rotate:
                password = secrets.token_urlsafe(32)
                # CREATE/ALTER ROLE은 %s 바인딩을 지원하지 않아 psycopg.sql로 안전하게 조립한다.
                verb = 'ALTER ROLE {} WITH LOGIN PASSWORD {}' if exists else \
                    'CREATE ROLE {} LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE PASSWORD {}'
                conn.execute(sql.SQL(verb).format(sql.Identifier(role), sql.Literal(password)))
                out(f"앱 역할 {role}: {'비밀번호 교체' if exists else '생성'}")
            else:
                out(f'앱 역할 {role}: 이미 있음(비밀번호 유지)')
    except psycopg.Error as error:
        raise PrepareError(f'DB 작업 실패: {type(error).__name__}') from None

    try:
        migrate(owner_dsn)
        out('마이그레이션 적용 완료')
        grant_app_role(owner_dsn, role)
        out('앱 역할 권한: 스키마 사용 + 테이블 읽기·쓰기만')
    except psycopg.Error as error:
        raise PrepareError(f'마이그레이션·권한 적용 실패: {type(error).__name__}') from None

    if password is None:
        return None
    app_dsn = make_conninfo(owner_dsn, user=role, password=password)
    try:
        with connect(app_dsn) as conn:
            can_create = conn.execute("SELECT has_schema_privilege(current_user, 'public', 'CREATE') AS ok").fetchone()['ok']
            conn.execute('SELECT count(*) FROM users').fetchone()
    except psycopg.Error as error:
        raise PrepareError(f'앱 역할 접속 확인 실패: {type(error).__name__}') from None
    if can_create:
        raise PrepareError('앱 역할에 스키마 생성 권한이 남아 있습니다.')
    out('앱 역할 접속 확인: 테이블 조회 가능, 스키마 생성 불가')
    return app_dsn


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--rotate-password', action='store_true', help='이미 있는 앱 역할의 비밀번호를 새로 만든다')
    args = parser.parse_args(argv)
    owner = os.environ.get('NOURISHON_MIGRATION_DATABASE_URL')
    if not owner:
        print('NOURISHON_MIGRATION_DATABASE_URL이 필요합니다.', file=sys.stderr)
        return 1
    try:
        app_dsn = prepare(owner, rotate=args.rotate_password)
    except PrepareError as error:
        print(f'오류: {error}', file=sys.stderr)
        return 1
    if app_dsn:
        print('\n아래 한 줄이 Render의 NOURISHON_DATABASE_URL 값입니다. 지금 복사해 안전한 곳에 보관하세요.')
        print('채팅·Git·스크린샷에 남기지 마세요. 다시 볼 수 없으며, 잃어버리면 --rotate-password로 새로 만듭니다.\n')
        print(app_dsn)
    else:
        print('\n앱 역할 비밀번호는 바꾸지 않았습니다. 새 연결 문자열이 필요하면 --rotate-password로 다시 실행하세요.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
