"""가상 식품으로 메모리/디스크 조회 동등성과 스트림 파서·자원 정리를 검증한다."""
import json
import sqlite3
from pathlib import Path
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from fastapi.testclient import TestClient
from backend.api import FoodCatalog, create_app
from backend.food_catalog import DiskFoodCatalog, iter_food_rows
from tests.test_api import practice_row

class DiskCatalogTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.path=Path(self.temp.name)/'foods.json'
        self.rows=[practice_row('a','ＡＢＣ  연습 두부'),practice_row('b','다른 두부'),practice_row('c','연습 두부'),practice_row('d','100%_두부')]
        for row,protein,fiber,sodium in zip(self.rows,[10,20,None,10],[None,0,5,0],[500,0,None,500]):
            row.update(PROT=protein,FIBTG=fiber,NAT=sodium)
        self.write(self.rows)
        self.catalog=DiskFoodCatalog(self.path,len(self.rows))
        self.reference=FoodCatalog(self.rows)

    def write(self,rows):
        self.path.write_text(json.dumps(rows,ensure_ascii=False),encoding='utf-8')

    def tearDown(self):
        self.catalog.close()
        self.temp.cleanup()

    def test_search_comparison_meal_exact_results(self):
        for query in ['두부',' abc  연습 ','없음','%','_','ＡＢＣ']:
            for offset in [0,1,3,99]:
                self.assertEqual(self.catalog.search(query,offset,2),self.reference.search(query,offset,2))
                for focus in ['protein','fiber','sodium']:
                    self.assertEqual(self.catalog.compare(query,focus,offset,2),self.reference.compare(query,focus,offset,2))
        entries=[{'food_code':'c','intake_g':0},{'food_code':'a','intake_g':150},{'food_code':'c','intake_g':37.5}]
        self.assertEqual(self.catalog.meal(entries),self.reference.meal(entries))
        for catalog in [self.catalog,self.reference]:
            with self.assertRaises(LookupError):catalog.meal([{'food_code':'없는 코드','intake_g':1}])
            with self.assertRaises(ValueError):catalog.search('   ',0,1)

    def test_threaded_requests(self):
        def query(_):
            return self.catalog.search('두부',0,2),self.catalog.compare('두부','sodium',0,2)
        expected=query(0)
        with ThreadPoolExecutor(max_workers=4) as pool:
            self.assertEqual(list(pool.map(query,range(12))),[expected]*12)

    def test_fail_closed_and_cleanup(self):
        for rows,count in [([],0),(self.rows,999),([self.rows[0],self.rows[0]],2),([dict(self.rows[0],NUT_CON_SRTR_QUA='1회')],1)]:
            self.write(rows)
            with self.assertRaises((ValueError,sqlite3.IntegrityError)):DiskFoodCatalog(self.path,count)
        directory=self.catalog.path.parent
        self.catalog.close()
        self.assertFalse(directory.exists())

    def test_stream_boundaries_and_invalid_arrays(self):
        large=dict(self.rows[0],FOOD_NM='가'*70000)
        self.write([large,self.rows[1]])
        self.assertEqual(list(iter_food_rows(self.path)),[large,self.rows[1]])
        for raw in ['','{}','[','[{}','[{},]','[{} {}]','[1]','[] trailing','[] []','[{}, null]']:
            self.path.write_text(raw)
            with self.subTest(raw=raw),self.assertRaises(ValueError):list(iter_food_rows(self.path))
        self.path.write_text('  [ ] \n')
        self.assertEqual(list(iter_food_rows(self.path)),[])

    def test_file_api_uses_disk_catalog_and_closes(self):
        self.path.with_name('report.json').write_text(json.dumps({'status':'completed','output_count':len(self.rows)}))
        with TestClient(create_app(data_path=self.path)) as client:
            catalog=client.app.state.catalog
            self.assertIsInstance(catalog,DiskFoodCatalog)
            directory=catalog.path.parent
            self.assertEqual(client.get('/health').json()['food_count'],len(self.rows))
            self.assertEqual(client.get('/foods',params={'q':'두부'}).json(),self.reference.search('두부',0,20))
            self.assertEqual(client.get('/foods/compare',params={'q':'두부','focus':'sodium'}).json(),self.reference.compare('두부','sodium',0,8))
            self.assertEqual(client.post('/meals/calculate',json={'entries':[{'food_code':'a','intake_g':150}]}).json(),self.reference.meal([{'food_code':'a','intake_g':150}]))
        self.assertFalse(directory.exists())
