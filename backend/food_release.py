"""식품 정제본을 비공개 GitHub Release로 옮기는 도구. 토큰·다운로드 주소는 출력하지 않는다.

package: 로컬 정제본(foods.json + report.json)을 재현 가능한 tar.gz로 묶고 SHA-256을 출력한다.
fetch:   배포 빌드에서 비공개 Release 첨부 파일을 읽기 전용 토큰으로 내려받아
         SHA-256이 미리 기록한 값과 같을 때만 지정 폴더에 배치한다.
"""
import argparse
import gzip
import hashlib
import hmac
import json
import os
import re
import shutil
import sys
import tarfile
import tempfile
import urllib.error
import urllib.request
from pathlib import Path

MEMBERS = ('foods.json', 'report.json')
GITHUB_API = 'https://api.github.com'
MAX_ASSET_BYTES = 1 << 30  # 1GiB: 예상 크기(수십 MiB)보다 훨씬 크면 잘못된 파일로 본다.
CHUNK = 1 << 20
_REPO = re.compile(r'^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$')
_NAME = re.compile(r'^[A-Za-z0-9_.-]+$')
_SHA = re.compile(r'^[0-9a-f]{64}$')


class FoodReleaseError(Exception):
    """사용자에게 보여줄 수 있는 오류. 토큰·서명 주소를 담지 않는다."""


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    # 자동 리다이렉트를 끈다. 다운로드 주소로 이동할 때 GitHub 토큰을 다른 서버에 보내지 않기 위해서다.
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _open(url: str, headers: dict, timeout: int = 60):
    opener = urllib.request.build_opener(_NoRedirect)
    try:
        return opener.open(urllib.request.Request(url, headers=headers), timeout=timeout)
    except urllib.error.HTTPError as error:
        if error.code in (301, 302, 303, 307, 308):
            return error
        error.close()
        raise FoodReleaseError(f'GitHub 응답 오류: HTTP {error.code}') from None
    except (urllib.error.URLError, TimeoutError, OSError):
        raise FoodReleaseError('GitHub에 연결하지 못했습니다.') from None


def package(source: Path, output: Path) -> str:
    """같은 입력이면 항상 같은 바이트(같은 SHA-256)가 나오도록 시간·소유자 정보를 고정해 묶는다."""
    for name in MEMBERS:
        if not (source / name).is_file():
            raise FoodReleaseError(f'{name} 파일이 없습니다.')
    json.loads((source / 'report.json').read_text())
    output.parent.mkdir(parents=True, exist_ok=True)
    with open(output, 'wb') as raw, gzip.GzipFile(filename='', mode='wb', fileobj=raw, mtime=0) as gz:
        with tarfile.open(fileobj=gz, mode='w', format=tarfile.PAX_FORMAT) as tar:
            for name in MEMBERS:
                info = tarfile.TarInfo(name)
                info.size = (source / name).stat().st_size
                info.mtime = 0
                info.mode = 0o644
                info.uid = info.gid = 0
                info.uname = info.gname = ''
                with open(source / name, 'rb') as handle:
                    tar.addfile(info, handle)
    return _sha256(output)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, 'rb') as handle:
        for block in iter(lambda: handle.read(CHUNK), b''):
            digest.update(block)
    return digest.hexdigest()


def _download(response, target: Path, limit: int) -> str:
    digest = hashlib.sha256()
    total = 0
    with open(target, 'wb') as handle:
        for block in iter(lambda: response.read(CHUNK), b''):
            total += len(block)
            if total > limit:
                raise FoodReleaseError('첨부 파일이 예상 크기를 넘었습니다.')
            digest.update(block)
            handle.write(block)
    return digest.hexdigest()


def _extract(archive: Path, staging: Path):
    """정해진 두 파일만 꺼낸다. 경로 조작(../)·링크·추가 파일이 있으면 거부한다."""
    with tarfile.open(archive, 'r:gz') as tar:
        members = tar.getmembers()
        if sorted(m.name for m in members) != sorted(MEMBERS) or not all(m.isreg() for m in members):
            raise FoodReleaseError('첨부 파일 구성이 foods.json·report.json과 다릅니다.')
        for member in members:
            source = tar.extractfile(member)
            with open(staging / member.name, 'wb') as handle:
                shutil.copyfileobj(source, handle, CHUNK)
    try:
        json.loads((staging / 'report.json').read_text())
    except ValueError:
        raise FoodReleaseError('report.json 형식이 올바르지 않습니다.') from None


def fetch(repo: str, tag: str, asset: str, sha256: str, token: str, dest: Path, api: str = GITHUB_API) -> dict:
    sha256 = sha256.strip().lower()
    if not _REPO.match(repo) or not _NAME.match(tag) or not _NAME.match(asset):
        raise FoodReleaseError('저장소·태그·파일 이름 형식을 확인하세요.')
    if not _SHA.match(sha256):
        raise FoodReleaseError('SHA-256은 64자리 16진수여야 합니다.')
    if not token:
        raise FoodReleaseError('읽기 전용 토큰이 필요합니다.')
    auth = {'Authorization': f'Bearer {token}', 'X-GitHub-Api-Version': '2022-11-28', 'User-Agent': 'nourishon-build'}

    with _open(f'{api}/repos/{repo}/releases/tags/{tag}', auth | {'Accept': 'application/vnd.github+json'}) as response:
        try:
            release = json.load(response)
        except ValueError:
            raise FoodReleaseError('Release 정보를 읽지 못했습니다.') from None
    matches = [a for a in release.get('assets', []) if a.get('name') == asset]
    if len(matches) != 1:
        raise FoodReleaseError('Release에서 지정한 첨부 파일을 찾지 못했습니다.')
    size = int(matches[0].get('size') or 0)
    if not 0 < size <= MAX_ASSET_BYTES:
        raise FoodReleaseError('첨부 파일 크기가 허용 범위를 벗어났습니다.')

    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    work = Path(tempfile.mkdtemp(prefix='.food-release-', dir=dest.parent))
    try:
        archive = work / 'asset.tar.gz'
        first = _open(f"{api}/repos/{repo}/releases/assets/{int(matches[0]['id'])}", auth | {'Accept': 'application/octet-stream'})
        if isinstance(first, urllib.error.HTTPError):
            location = first.headers.get('Location')
            first.close()
            local_test = api.startswith('http://127.0.0.1') and (location or '').startswith('http://127.0.0.1')
            if not location or not (location.startswith('https://') or local_test):
                raise FoodReleaseError('다운로드 주소가 올바르지 않습니다.')
            # 서명된 다운로드 주소에는 GitHub 토큰을 보내지 않는다.
            response = _open(location, {'User-Agent': 'nourishon-build'}, timeout=300)
            if isinstance(response, urllib.error.HTTPError):
                raise FoodReleaseError('다운로드 주소가 다시 이동했습니다.')
        else:
            response = first
        with response:
            actual = _download(response, archive, size)
        if not hmac.compare_digest(actual, sha256):
            raise FoodReleaseError('SHA-256이 기록한 값과 다릅니다. 파일을 배치하지 않았습니다.')

        staging = work / 'food'
        staging.mkdir()
        _extract(archive, staging)
        archive.unlink()
        # 기존 폴더는 새 파일 준비가 끝난 뒤에만 교체한다.
        old = work / 'previous'
        if dest.exists():
            dest.rename(old)
        staging.rename(dest)
        return {'sha256': actual, 'bytes': size, 'files': list(MEMBERS)}
    finally:
        shutil.rmtree(work, ignore_errors=True)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest='command', required=True)
    p = sub.add_parser('package', help='로컬 정제본을 tar.gz로 묶고 SHA-256 출력')
    p.add_argument('source', type=Path)
    p.add_argument('output', type=Path)
    f = sub.add_parser('fetch', help='환경변수 설정대로 비공개 Release에서 내려받기')
    f.add_argument('dest', type=Path)
    args = parser.parse_args(argv)
    try:
        if args.command == 'package':
            digest = package(args.source, args.output)
            print(f'묶음 완료: {args.output.name}, {args.output.stat().st_size} bytes')
            print(f'SHA-256: {digest}')
        else:
            env = os.environ
            names = ['NOURISHON_FOOD_RELEASE_REPO', 'NOURISHON_FOOD_RELEASE_TAG', 'NOURISHON_FOOD_RELEASE_ASSET',
                     'NOURISHON_FOOD_RELEASE_SHA256', 'NOURISHON_FOOD_RELEASE_TOKEN']
            missing = [n for n in names if not env.get(n)]
            if missing:
                raise FoodReleaseError('필요한 환경변수가 없습니다: ' + ', '.join(missing))
            result = fetch(env[names[0]], env[names[1]], env[names[2]], env[names[3]], env[names[4]], args.dest)
            print(f"식품 정제본 배치 완료: {result['bytes']} bytes, SHA-256 일치")
    except FoodReleaseError as error:
        print(f'오류: {error}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
