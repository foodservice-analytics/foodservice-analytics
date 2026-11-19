"""CHYT-only executor with bounded result transport and immutable run outputs."""
import hashlib,json,os,re
from time import perf_counter
import pandas as pd
import yt.wrapper as yt
import yt.clickhouse as chyt
from src.config import resolve_env
from .queries import build_queries,table_path

class CHYTSource:
    is_chyt=True
    def __init__(self,cfg,*,client=None,executor=None):
        self.cfg=cfg
        opt=cfg['data_source']['yt']
        if client is None:
            token=os.environ.get(opt.get('token_env','YT_TOKEN'))
            if not token: raise RuntimeError('Set YT_TOKEN in environment/local .env')
            client=yt.YtClient(proxy=resolve_env(opt.get('proxy')) or opt['proxy_default'],token=token,
                config={'proxy':{'enable_proxy_discovery':False,'prefer_https':True,
                                'connect_timeout':15000,'request_timeout':20000,'retries':{'count':2}}})
        self.client=client;self.execute=executor or chyt.execute
        self.audit=[];self.versions={};self.queries={};self.validated=False

    def query(self,name,sql):
        opt=self.cfg['data_source'].get('chyt',{})
        cap=int(opt.get('max_result_rows',50000))
        settings={'max_execution_time':int(opt.get('timeout_seconds',180)),
                  'max_threads':1,'max_block_size':1024,
                  'max_memory_usage':int(opt.get('max_memory_bytes',500000000)),
                  'max_query_size':4000000,'max_ast_elements':300000,'max_result_rows':cap,'result_overflow_mode':'throw',
                  'output_format_json_quote_64bit_integers':False}
        start=perf_counter();rows=[]
        self.queries[name]=sql
        try:
            for row in self.execute(sql,alias=opt.get('alias','*ch_public'),settings=settings,client=self.client):
                rows.append(row)
                if len(rows)>cap: raise RuntimeError('Bounded result cap exceeded; no truncation permitted')
        except Exception:
            self.audit.append({'query':name,'status':'failed','client_wall_seconds':perf_counter()-start})
            raise
        self.audit.append({'query':name,'status':'complete','client_wall_seconds':perf_counter()-start,
            'result_rows':len(rows),'result_json_bytes':len(json.dumps(rows,ensure_ascii=False).encode()),
            'sql_sha256':hashlib.sha256(sql.encode()).hexdigest()})
        return pd.DataFrame(rows)

    def preflight(self):
        for name,spec in self.cfg['tables'].items():
            attrs=self.client.get(spec['path']+'/@')
            self.versions[name]={k:attrs.get(k) for k in ('row_count','revision','modification_time')}
        result=self.query('preflight','''SELECT version() AS clickhouse_version,count() AS rows,
            uniqExact(id) AS unique_ids,countIf(empty(ifNull(id,''))) AS missing_ids
            FROM "//home/spb_food/stg/branches"''')
        r=result.iloc[0]
        if r['rows']!=r['unique_ids'] or r['missing_ids']:
            raise RuntimeError('Missing/duplicate branch IDs; resolve identity before running analytics')
        self.query('capabilities', '''SELECT YPathExtract('[{name="Кафе";kind="primary"}]','',
            'Array(Tuple(name String, kind String))') AS rubrics,
            lowerUTF8('ЕДА') AS unicode_lower, erfc(1.) AS erfc_check''')
        # Partition this exact audit so the 858 MiB clique never needs a 1.6M-key hash set.
        for part in range(16):
            review_keys=self.query(f'review_keys_{part:02d}',f'''SELECT count() AS rows,
                uniqExact(tuple(branch_id,review_id,provider)) AS unique_keys
                FROM {table_path(self.cfg['tables']['reviews']['path'])}
                WHERE cityHash64(branch_id)%16={part}''')
            if review_keys.iloc[0]['rows']!=review_keys.iloc[0]['unique_keys']:
                raise RuntimeError('Duplicate review keys detected; remote deduplication must precede analytics')
        self.validated=True
        return result

    def task_tables(self,task):
        if not self.validated: raise RuntimeError('Preflight must pass before analytics')
        return {name:self.query(name,sql) for name,sql in build_queries(task,self.cfg).items()}

    def publish(self,name,frame,root):
        if not re.fullmatch(r'//home/team/foodservice_analytics/[A-Za-z0-9_-]+',root):
            raise ValueError('Only new run-scoped tables under //home/team/foodservice_analytics are writable')
        if not re.fullmatch(r'[a-z0-9_]+',name): raise ValueError('Invalid output table name')
        path=root+'/'+name
        if self.client.exists(path): raise FileExistsError(path)
        records=json.loads(frame.to_json(orient='records',force_ascii=False))
        if not records: return None
        def typ(col):
            values=[r[col] for r in records if r[col] is not None]
            if not values:return 'string'
            if all(isinstance(v,bool) for v in values):return 'boolean'
            if all(isinstance(v,int) for v in values):return 'int64'
            if all(isinstance(v,(int,float)) for v in values):return 'double'
            if all(isinstance(v,str) for v in values):return 'string'
            return 'any'
        schema=[{'name':col,'type':typ(col),'required':False} for col in frame.columns]
        self.client.create('table',path,recursive=True,attributes={
            'schema':schema,'optimize_for':'scan','compression_codec':'zstd_5'})
        self.client.write_table(path,records,format=yt.JsonFormat(encode_utf8=False))
        return path
