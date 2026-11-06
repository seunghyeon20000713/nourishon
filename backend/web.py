"""배포용 단일 주소: React 정적 화면 + /api FastAPI. 루트 파일 탐색 금지."""
from contextlib import asynccontextmanager
from pathlib import Path
import re
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from backend.api import create_app
from backend.settings import load_settings
from starlette.middleware.trustedhost import TrustedHostMiddleware


def create_web_app(api=None, frontend_path: Path | None = None):
    settings = load_settings()
    api = api or create_app(settings=settings)
    directory = (frontend_path or settings.frontend_path or Path(__file__).resolve().parents[1]/'frontend/dist').resolve()
    if not (directory/'index.html').is_file() or not (directory/'assets').is_dir():
        raise RuntimeError('일반 프런트엔드 빌드가 필요합니다. 체험판 빌드를 배포하지 마세요.')

    if settings.mode == 'staging':
        bundles = list((directory/'assets').glob('*.js'))
        if not bundles or any('화면 체험판 · 식품' in path.read_text() for path in bundles):
            raise RuntimeError('체험판이 아닌 일반 프런트엔드 빌드가 필요합니다.')

    @asynccontextmanager
    async def lifespan(app):
        async with api.router.lifespan_context(api):
            yield

    web = FastAPI(lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)
    if settings.mode == 'staging':
        web.add_middleware(TrustedHostMiddleware, allowed_hosts=list(settings.allowed_hosts))
    web.mount('/api', api)

    @web.get('/assets/{filename}')
    def asset(filename: str):
        if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]*\.(js|css|woff2)', filename):
            raise HTTPException(404)
        target = directory/'assets'/filename
        if not target.is_file() or not target.resolve().is_relative_to(directory/'assets'):
            raise HTTPException(404)
        return FileResponse(target, headers={'X-Content-Type-Options':'nosniff'})

    @web.get('/brand/nourishon-mark.png')
    def logo():
        return FileResponse(directory/'brand/nourishon-mark.png')

    @web.get('/decoration/journal-sprig.png')
    def journal_decoration():
        return FileResponse(directory/'decoration/journal-sprig.png', headers={'X-Content-Type-Options':'nosniff'})

    @web.get('/{path:path}')
    def page(path: str):
        if path and (path.startswith(('.', 'data/', 'backend/', 'private/', 'uploads/', 'assets/')) or '.' in path.split('/')[-1]):
            raise HTTPException(404)
        return FileResponse(directory/'index.html', headers={'Cache-Control':'no-store','X-Content-Type-Options':'nosniff'})
    return web


app = create_web_app()
