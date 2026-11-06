"""로컬/외부 테스트 설정. 비밀값을 오류·repr로 출력하지 않는다."""
import os
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlsplit
from psycopg.conninfo import conninfo_to_dict

LOCAL_ORIGINS = ('http://localhost:5173', 'http://127.0.0.1:5173', 'http://localhost:8000', 'http://127.0.0.1:8000')

@dataclass(frozen=True)
class Settings:
    mode: str = 'local'
    allowed_origins: tuple[str, ...] = LOCAL_ORIGINS
    database_url: str | None = field(default=None, repr=False)
    food_path: Path | None = None
    frontend_path: Path | None = None

    @property
    def secure_cookie(self):
        return self.mode == 'staging'

    @property
    def cookie_name(self):
        return '__Host-nourishon_session' if self.secure_cookie else 'nourishon_session'

    @property
    def allowed_hosts(self):
        return tuple(dict.fromkeys(urlsplit(origin).hostname for origin in self.allowed_origins))


def load_settings():
    mode = os.environ.get('NOURISHON_ENV', 'local')
    if mode not in {'local', 'staging'}:
        raise ValueError('NOURISHON_ENV는 local 또는 staging이어야 합니다.')
    raw_origins = os.environ.get('NOURISHON_ALLOWED_ORIGINS')
    origins = tuple(value.strip() for value in raw_origins.split(',') if value.strip()) if raw_origins is not None else LOCAL_ORIGINS
    if not origins:
        raise ValueError('NOURISHON_ALLOWED_ORIGINS가 필요합니다.')
    for origin in origins:
        parsed = urlsplit(origin)
        if (parsed.scheme not in {'http','https'} or not parsed.hostname or '*' in origin or
                parsed.username or parsed.password or parsed.path or parsed.query or parsed.fragment):
            raise ValueError('NOURISHON_ALLOWED_ORIGINS는 경로·인증정보 없는 정확한 Origin이어야 합니다.')
        if mode == 'staging' and (parsed.scheme != 'https' or parsed.hostname in {'localhost','127.0.0.1','::1'}):
            raise ValueError('외부 테스트 Origin은 로컬이 아닌 HTTPS 주소여야 합니다.')
    db = os.environ.get('NOURISHON_DATABASE_URL') or None
    food = os.environ.get('NOURISHON_FOOD_DATA_PATH')
    frontend = os.environ.get('NOURISHON_FRONTEND_DIST')
    if mode == 'staging':
        if raw_origins is None or not db or not food or not frontend:
            raise ValueError('외부 테스트에 필요한 Origin·DB·식품 경로·화면 경로 환경변수가 필요합니다.')
        try:
            options = conninfo_to_dict(db)
        except Exception:
            raise ValueError('NOURISHON_DATABASE_URL 형식을 확인하세요.') from None
        if options.get('sslmode') not in {'require','verify-ca','verify-full'}:
            raise ValueError('외부 테스트 DB는 SSL 연결 설정이 필요합니다.')
        if not options.get('host') or options['host'].startswith('/') or options['host'] in {'localhost','127.0.0.1','::1'}:
            raise ValueError('외부 테스트용 별도 PostgreSQL 호스트가 필요합니다.')
    return Settings(mode, origins, db, Path(food).resolve() if food else None, Path(frontend).resolve() if frontend else None)
