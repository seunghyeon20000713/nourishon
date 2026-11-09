"""정제 JSON을 순차적으로 읽어 임시 SQLite 조회 파일을 만든다. 개인 기록 DB와 무관하다."""
import json
import sqlite3
import tempfile
from contextlib import closing
from itertools import tee
from pathlib import Path

from backend.food_search import _normalize_name
from backend.food_comparison import compare_foods
from backend.meal import calculate_meal


def iter_food_rows(path: Path):
    """최상위 JSON 배열을 한 행씩 읽는다. 잘린 배열·후행 문자·잘못된 구분자를 거부한다."""
    decoder = json.JSONDecoder()
    with path.open(encoding='utf-8') as source:
        buffer, eof = '', False

        def more():
            nonlocal buffer, eof
            chunk = source.read(65536)
            buffer += chunk
            eof = not chunk

        def trim():
            nonlocal buffer
            buffer = buffer.lstrip()
            while not buffer and not eof:
                more()
                buffer = buffer.lstrip()

        trim()
        if not buffer.startswith('['):
            raise ValueError('식품 배열이 필요합니다.')
        buffer = buffer[1:]
        trim()
        if buffer.startswith(']'):
            buffer = buffer[1:]
        else:
            while True:
                trim()
                while True:
                    try:
                        row, end = decoder.raw_decode(buffer)
                        break
                    except json.JSONDecodeError:
                        if eof:
                            raise ValueError('식품 JSON이 완전하지 않습니다.') from None
                        more()
                if not isinstance(row, dict):
                    raise ValueError('식품 행은 객체여야 합니다.')
                buffer = buffer[end:]
                yield row
                trim()
                if buffer.startswith(']'):
                    buffer = buffer[1:]
                    break
                if not buffer.startswith(','):
                    raise ValueError('식품 행 구분자가 잘못됐습니다.')
                buffer = buffer[1:]
        trim()
        if buffer:
            raise ValueError('식품 배열 뒤에 다른 내용이 있습니다.')


class DiskFoodCatalog:
    """원본 순서·문자열 정규화·계산 함수를 보존하며 요청 단위로 행을 읽는다."""
    def __init__(self, path: Path, expected_count: int):
        self._temporary = tempfile.TemporaryDirectory(prefix='nourishon-food-')
        self.path = Path(self._temporary.name)/'catalog.sqlite3'
        self.count = 0
        try:
            with closing(sqlite3.connect(self.path)) as connection:
                connection.execute('PRAGMA cache_size=-2048')
                connection.execute('CREATE TABLE foods (position INTEGER PRIMARY KEY, code TEXT UNIQUE NOT NULL, name TEXT NOT NULL, payload TEXT NOT NULL)')
                with connection:
                    for index, row in enumerate(iter_food_rows(path), 1):
                        code = row['FOOD_CD']
                        if not isinstance(code, str) or not code or row['NUT_CON_SRTR_QUA'] != '100g':
                            raise ValueError('식품코드 또는 기준량이 잘못됐습니다.')
                        connection.execute('INSERT INTO foods VALUES (?,?,?,?)',
                                           (index, code, _normalize_name(row['FOOD_NM']), json.dumps(row, ensure_ascii=False, allow_nan=False)))
                        self.count = index
                if not self.count or self.count != expected_count:
                    raise ValueError('식품 개수가 완료 보고서와 다릅니다.')
        except BaseException:
            self.close()
            raise

    def close(self):
        self._temporary.cleanup()

    def _connect(self):
        connection = sqlite3.connect(self.path)
        connection.execute('PRAGMA query_only=ON')
        connection.execute('PRAGMA cache_size=-2048')
        return connection

    @staticmethod
    def _keyword(query):
        keyword = _normalize_name(query)
        if not keyword:
            raise ValueError('검색어를 입력해주세요.')
        return keyword

    def search(self, query: str, offset: int, limit: int) -> dict:
        keyword = self._keyword(query)
        with closing(self._connect()) as connection:
            total = connection.execute('SELECT count(*) FROM foods WHERE instr(name,?)>0', (keyword,)).fetchone()[0]
            selected = connection.execute('SELECT payload FROM foods WHERE instr(name,?)>0 ORDER BY position LIMIT ? OFFSET ?', (keyword, limit, offset))
            items = []
            for (payload,) in selected:
                row = json.loads(payload)
                items.append({'food_code':row['FOOD_CD'], 'food_name':row['FOOD_NM'], 'basis':'100g',
                              'source_name':row['SRC_NM'], 'reference_date':row['CRTR_YMD'], 'updated_date':row.get('UPDATE_DATE')})
        return {'total':total, 'offset':offset, 'limit':limit, 'items':items}

    def compare(self, query: str, focus: str, offset: int, limit: int):
        keyword = self._keyword(query)
        with closing(self._connect()) as connection:
            # 기존 비교 함수를 재사용해 숫자·결측·동점 순서 규칙을 유지한다.
            cursor = connection.execute('SELECT payload,name FROM foods WHERE instr(name,?)>0 ORDER BY position', (keyword,))
            left, right = tee(cursor)
            result = compare_foods((json.loads(row[0]) for row in left), (row[1] for row in right), query, focus, offset, limit)
            for food in result['items']:
                food['source_row_number'] = connection.execute('SELECT position FROM foods WHERE code=?', (food['food_code'],)).fetchone()[0]
        return result

    def meal(self, entries: list[dict]):
        selected, positions = {}, {}
        with closing(self._connect()) as connection:
            for entry in entries:
                code = entry['food_code']
                if code in selected:
                    continue
                item = connection.execute('SELECT position,payload FROM foods WHERE code=?', (code,)).fetchone()
                if item is None:
                    raise LookupError('해당 식품코드가 없습니다.')
                positions[code], payload = item
                selected[code] = json.loads(payload)
        result = calculate_meal(list(selected.values()), entries)
        for food in result['foods']:
            food['source_row_number'] = positions[food['food_code']]
        return result
