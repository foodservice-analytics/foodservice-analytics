"""Server-only source-history estimates for the final DataLens dashboard."""
import sys,json,uuid
from datetime import datetime,timezone
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from src.paths import output_dir, latest_file
from dotenv import load_dotenv
from src.config import load_config
from src.server_pipeline.source import CHYTSource
from src.server_pipeline.queries import context
load_dotenv();cfg=load_config('config/server.yaml');s=CHYTSource(cfg)
run_id=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'_presentation_'+uuid.uuid4().hex[:4]
out=(output_dir()/'presentation')/run_id;(out/'tables').mkdir(parents=True);(out/'sql').mkdir()
root='//home/team/foodservice_analytics/'+run_id
ctx=context(cfg);sqlroot=Path('server_sql/presentation');ctx['history']=(sqlroot/'history_cte.sql').read_text().format(**ctx)
manifest={'run_id':run_id,'root':root,'date_rule':'first_last_observation_proxy_v1','status':'running','tables':{}}
try:
 for name in ['wayback_events','osm_events','history_share','competitors','cohort']:
  sql=(sqlroot/(name+'.sql')).read_text().format(**ctx)
  frame=s.query(name,sql);frame.to_csv(out/'tables'/(name+'.csv'),index=False);(out/'sql'/(name+'.sql')).write_text(sql)
  manifest['tables'][name]=s.publish(name,frame,root)
  print(name,len(frame),flush=True)
 manifest['status']='complete';latest_file('history').write_text(str(out.resolve()))
except BaseException:
 manifest['status']='failed';raise
finally:
 manifest['queries']=s.audit;(out/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2))
print('RESULT',out,flush=True)
