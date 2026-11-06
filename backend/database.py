"""개발용 PostgreSQL 설정·연결·명시적 마이그레이션. 설정값은 출력하지 않는다."""
import argparse
import os
from pathlib import Path

import psycopg
from psycopg.rows import dict_row

ROOT = Path(__file__).resolve().parents[1]


def database_url() -> str | None:
    if os.environ.get('NOURISHON_DATABASE_URL'):
        return os.environ['NOURISHON_DATABASE_URL']
    path = ROOT / '.env.database'
    if not path.exists():
        return None
    for line in path.read_text().splitlines():
        if line.startswith('NOURISHON_DATABASE_URL='):
            return line.split('=', 1)[1].strip().strip('\"\'')
    return None


def connect(dsn: str):
    return psycopg.connect(dsn, row_factory=dict_row, connect_timeout=5)


def migrate(dsn: str):
    with connect(dsn) as conn:
        for path in sorted((ROOT / 'backend/migrations').glob('*.sql')):
            conn.execute(path.read_text())


def setup_local():
    socket = f'/tmp/nourishon-postgres-{os.getuid()}'
    owner = f'host={socket} port=55432 user=nourishon_owner'
    with psycopg.connect(f'{owner} dbname=postgres', autocommit=True) as conn:
        if not conn.execute("SELECT 1 FROM pg_roles WHERE rolname='nourishon_app'").fetchone():
            conn.execute('CREATE ROLE nourishon_app LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE')
        for name in ('nourishon', 'nourishon_test'):
            if not conn.execute('SELECT 1 FROM pg_database WHERE datname=%s', (name,)).fetchone():
                conn.execute(psycopg.sql.SQL('CREATE DATABASE {}').format(psycopg.sql.Identifier(name)))
    for name in ('nourishon', 'nourishon_test'):
        dsn = f'{owner} dbname={name}'
        migrate(dsn)
        with connect(dsn) as conn:
            conn.execute('REVOKE CREATE ON SCHEMA public FROM PUBLIC')
            conn.execute('GRANT USAGE ON SCHEMA public TO nourishon_app')
            conn.execute('GRANT SELECT,INSERT,UPDATE,DELETE ON ALL TABLES IN SCHEMA public TO nourishon_app')
    config = ROOT / '.env.database'
    if not config.exists():
        config.write_text(f'NOURISHON_DATABASE_URL=host={socket} port=55432 user=nourishon_app dbname=nourishon\n')
        config.chmod(0o600)
    print('로컬 개발 DB·별도 테스트 DB와 스키마를 준비했습니다. 설정값은 출력하지 않습니다.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['setup-local', 'migrate'])
    args = parser.parse_args()
    if args.command == 'setup-local':
        setup_local()
    else:
        dsn = database_url()
        if not dsn:
            parser.exit(1, 'DB 설정이 필요합니다.\n')
        migrate(dsn)
        print('스키마 마이그레이션 완료')
