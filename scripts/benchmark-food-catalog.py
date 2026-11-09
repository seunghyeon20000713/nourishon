"""같은 정제본으로 기존 메모리 방식과 파일 조회를 각각 새 프로세스에서 측정한다."""
import argparse
import hashlib
import json
from pathlib import Path
import resource
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backend.api import DEFAULT_DATA, FoodCatalog
from backend.food_catalog import DiskFoodCatalog


def rss_mib():
    for line in Path('/proc/self/status').read_text().splitlines():
        if line.startswith('VmRSS:'):
            return round(int(line.split()[1])/1024, 2)


def benchmark(mode, source):
    started = time.perf_counter()
    report = json.loads(source.with_name('report.json').read_text())
    if report.get('status') != 'completed':
        raise ValueError('완료된 정제본이 필요합니다.')
    catalog = (FoodCatalog(json.loads(source.read_text(encoding='utf-8'))) if mode == 'memory'
               else DiskFoodCatalog(source, report['output_count']))
    result = {'mode':mode, 'food_count':catalog.count, 'startup_seconds':round(time.perf_counter()-started,3),
              'startup_rss_mib':rss_mib(), 'catalog_file_mib':round(catalog.path.stat().st_size/1024**2,2) if isinstance(catalog,DiskFoodCatalog) else None, 'checks':{}}
    try:
        for query in ['두부','현미밥','닭가슴살','사과','가','존재하지않는연습음식','%','ＤＵＢＵ']:
            for offset in [0,8]:
                value = catalog.search(query, offset, 8)
                key = f'search:{query}:{offset}'
                result['checks'][key] = hashlib.sha256(json.dumps(value,ensure_ascii=False,sort_keys=True,allow_nan=False).encode()).hexdigest()
        for query in ['두부','가','%']:
            for focus in ['protein','fiber','sodium']:
                for offset in [0,8,10000]:
                    value = catalog.compare(query, focus, offset, 8)
                    result['checks'][f'compare:{query}:{focus}:{offset}'] = hashlib.sha256(json.dumps(value,ensure_ascii=False,sort_keys=True,allow_nan=False).encode()).hexdigest()
        chosen = catalog.search('두부',0,3)['items']
        entries = [{'food_code':item['food_code'],'intake_g':grams} for item,grams in zip(chosen,[0,150,37.5])]
        if not entries:
            raise ValueError('비교할 식품이 없습니다.')
        entries.append(dict(entries[-1]))
        value = catalog.meal(entries)
        result['checks']['meal:zero-fraction-repeat'] = hashlib.sha256(json.dumps(value,ensure_ascii=False,sort_keys=True,allow_nan=False).encode()).hexdigest()
        result.update(final_rss_mib=rss_mib(), peak_rss_mib=round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024,2), total_seconds=round(time.perf_counter()-started,3))
        return result
    finally:
        if isinstance(catalog,DiskFoodCatalog):
            catalog.close()

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode',choices=['memory','disk'],required=True)
    parser.add_argument('--source',type=Path,default=DEFAULT_DATA)
    args=parser.parse_args()
    print(json.dumps(benchmark(args.mode,args.source),ensure_ascii=False,indent=2))
