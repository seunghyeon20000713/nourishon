"""외부 테스트 배포 설정 확인. 실제 비밀값은 출력하지 않는다."""
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from backend.settings import load_settings
from backend.database import connect

parser=argparse.ArgumentParser(description='외부 테스트 배포 설정을 확인합니다. 비밀값은 출력하지 않습니다.')
parser.add_argument('--check-db',action='store_true',help='별도 테스트 DB 연결·스키마 확인')
args=parser.parse_args()
try:
    settings=load_settings()
    if settings.mode!='staging':raise ValueError('NOURISHON_ENV=staging 설정이 필요합니다.')
    assert settings.food_path is not None and settings.frontend_path is not None
    if not settings.food_path.is_file():raise ValueError('승인된 식품 파일이 지정 경로에 필요합니다.')
    report=json.loads(settings.food_path.with_name('report.json').read_text())
    if report.get('status')!='completed':raise ValueError('완료된 식품 데이터 보고서가 필요합니다.')
    if not (settings.frontend_path/'index.html').is_file():raise ValueError('일반 프런트엔드 빌드가 필요합니다.')
    scripts=list((settings.frontend_path/'assets').glob('*.js'))
    if not scripts or any('화면 체험판 · 식품' in path.read_text() for path in scripts):raise ValueError('체험판이 아닌 일반 프런트엔드 빌드가 필요합니다.')
    if args.check_db:
        with connect(settings.database_url) as conn:
            versions={row['version'] for row in conn.execute('SELECT version FROM schema_migrations')}
            if not {1,2}.issubset(versions):raise ValueError('DB 마이그레이션이 필요합니다.')
            role=conn.execute('SELECT rolsuper,rolcreatedb,rolcreaterole FROM pg_roles WHERE rolname=current_user').fetchone()
            if any(role.values()):raise ValueError('제한된 권한의 앱 DB 역할을 사용하세요.')
    print('설정·경로 확인 통과'+(' · DB 연결·스키마 확인 통과' if args.check_db else ' · 실제 DB 연결은 검사하지 않았습니다.'))
except ValueError as error:
    # 위 검증에서 만든 정해진 메시지만 표시한다. 드라이버 오류/DSN은 출력하지 않는다.
    if type(error) is ValueError and str(error).startswith(('NOURISHON_','외부 테스트','승인된','완료된','일반 프런트','체험판이','DB 마이그레이션','제한된')):
        parser.exit(1,str(error)+'\n')
    parser.exit(1,'배포 설정 또는 파일을 확인하세요. 비밀값은 출력하지 않습니다.\n')
except Exception:
    parser.exit(1,'경로·데이터 보고서·DB 연결을 확인하세요. 비밀값은 출력하지 않습니다.\n')
