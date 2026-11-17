"""Behavioral checks for source/output boundaries and server streaming workers."""
import unittest,json,subprocess,tempfile,sys
from pathlib import Path
from src.config import load_config
from src.server_pipeline.queries import TOPICS,table_path
from src.server_pipeline.source import CHYTSource

class ServerPipelineTests(unittest.TestCase):
    def setUp(self):self.cfg=load_config('config/server.yaml')
    def test_publish_cannot_write_source_or_escape_workspace(self):
        s=CHYTSource(self.cfg,client=object(),executor=lambda *a,**kw:iter([]))
        for root in ['//home/spb_food/stg','//home/team','//home/team/../spb_food','//home/team/foodservice_analytics/../../raw']:
            with self.assertRaises(ValueError):s.publish('test',None,root)
    def test_result_overflow_throws_instead_of_silently_truncating(self):
        self.cfg['data_source']['chyt']['max_result_rows']=1
        s=CHYTSource(self.cfg,client=object(),executor=lambda *a,**kw:iter([{'a':1},{'a':2}]))
        with self.assertRaises(RuntimeError):s.query('test','SELECT 1')
        self.assertEqual(s.audit[0]['status'],'failed')
    def test_sql_source_path_rejects_injection(self):
        with self.assertRaises(ValueError):table_path('//home/spb_food/stg/reviews"; DROP TABLE x')
    def test_mapper_keeps_empty_text_and_rejects_invalid_ratings_dates_hidden(self):
        worker=Path('src/server_pipeline/workers/review_mapper.py').resolve()
        base=dict(branch_id='a',review_id='r',rating=1,text='ГРУБЫЙ ОФИЦИАНТ, НЕВКУСНАЯ ЕДА',is_hidden=False,date_created='2024-08-31T00:53:12.08921+07:00')
        rows=[base,{**base,'review_id':'r2','text':''},{**base,'review_id':'r3','rating':None},
              {**base,'review_id':'r4','is_hidden':True},{**base,'review_id':'r5','date_created':'bad'},
              {**base,'review_id':'r6','date_created':'2027-01-01T12:00:00+03:00'}]
        with tempfile.TemporaryDirectory() as folder:
            Path(folder,'topic_rules.json').write_text(json.dumps(TOPICS,ensure_ascii=False))
            result=subprocess.run([sys.executable,str(worker),'2026-10-31'],cwd=folder,
                input='\n'.join(json.dumps(r,ensure_ascii=False) for r in rows)+'\n',text=True,capture_output=True,check=True)
        out=json.loads(result.stdout)
        self.assertEqual((out['c0'],out['c1'],out['c2']),(2,2,1))
        self.assertEqual((out['c3'],out['c4'],out['c8']),(1,1,1))
    def test_reducer_preserves_reviews_split_between_map_jobs(self):
        worker=Path('src/server_pipeline/workers/review_reducer.py').resolve()
        records=[dict(branch_id='a',**{'c'+str(i):1 for i in range(14)}),dict(branch_id='a',**{'c'+str(i):2 for i in range(14)}),dict(branch_id='b',**{'c'+str(i):4 for i in range(14)})]
        result=subprocess.run([sys.executable,str(worker)],input='\n'.join(json.dumps(r) for r in records)+'\n',text=True,capture_output=True,check=True)
        out=[json.loads(x) for x in result.stdout.splitlines()]
        self.assertEqual([(r['branch_id'],r['c0']) for r in out],[('a',3),('b',4)])
if __name__=='__main__':unittest.main()
