"""Run the observation-date Cox model on one YTsaurus worker, then export its small result."""
import sys,json,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from src.paths import latest_file
from dotenv import load_dotenv
import yt.wrapper as yt
from src.config import load_config
from src.server_pipeline.source import CHYTSource
load_dotenv();s=CHYTSource(load_config('config/server.yaml'));c=s.client
out=Path(latest_file('history').read_text().strip());m=json.loads((out/'manifest.json').read_text());root=m['root'];target=root+'/cox_summary'
if c.exists(target):raise FileExistsError(target)
c.config['remote_temp_files_directory']=root+'/model_job_files';c.config['remote_temp_tables_directory']=root+'/model_temp'
schema=[{'name':k,'type':t} for k,t in [('factor','string'),('coef','double'),('hazard_ratio','double'),('ci_low','double'),('ci_high','double'),('p_value','double'),('n','int64'),('events','int64'),('ridge','double'),('iterations','int64'),('reference_category','string'),('reference_district','string'),('model','string')]]
c.create('table',target,attributes={'schema':schema,'optimize_for':'scan'})
start=time.perf_counter();op=c.run_map('python3 cox_worker.py',root+'/cohort_model',target,
 local_files=['src/server_pipeline/workers/cox_worker.py'],format=yt.JsonFormat(encode_utf8=False),job_count=1,memory_limit=256*1024**2,sync=False,
 spec={'title':'Foodservice observation-date Cox PH with ridge and Breslow ties','mapper':{'cpu_limit':1},'max_failed_job_count':1})
m['cox_operation']={'operation_id':op.id,'target':target};(out/'manifest.json').write_text(json.dumps(m,ensure_ascii=False,indent=2));print('OPERATION',op.id,flush=True)
op.wait();f=s.query('cox_summary',f'SELECT * FROM "{target}"');f.to_csv(out/'tables/cox_summary.csv',index=False);m['tables']['cox_summary']=target;m['cox_operation'].update(status='completed',wall_seconds=time.perf_counter()-start);m['queries'].extend(s.audit);(out/'manifest.json').write_text(json.dumps(m,ensure_ascii=False,indent=2));print(f[['factor','hazard_ratio','n','events','iterations']].to_string(index=False),flush=True)
