"""Extend history estimates with source-separated events and survival inputs in CHYT."""
import sys,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from src.paths import latest_file
from dotenv import load_dotenv
from src.config import load_config
from src.server_pipeline.source import CHYTSource
from src.server_pipeline.queries import context
load_dotenv();s=CHYTSource(load_config('config/server.yaml'))
out=Path(latest_file('history').read_text().strip());m=json.loads((out/'manifest.json').read_text());root=m['root']
queries={'competitors_active':Path('server_sql/presentation/competitors.sql').read_text().format(**context(s.cfg)),
'all_events':f'''SELECT year,event_kind,source,sum(establishments) AS establishments FROM
 (SELECT year,event_kind,source,establishments FROM "{root}/wayback_events"
 UNION ALL SELECT year,event_kind,source,establishments FROM "{root}/osm_events")
 GROUP BY year,event_kind,source ORDER BY year,event_kind,source''',
'cohort_model':f'''SELECT c.*,ifNull(p.competitors_300m,0) AS competitors_300m
 FROM (SELECT * FROM "{root}/cohort") c INNER JOIN (SELECT * FROM "{root}/competitors_active") p ON c.id=p.id''',
'survival':f'''WITH counts AS (SELECT ownership,duration,count() AS n,sum(event) AS events FROM "{root}/cohort" GROUP BY ownership,duration),
 risk AS (SELECT *,sum(n) OVER(PARTITION BY ownership ORDER BY duration DESC ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS at_risk FROM counts),
 curve AS (SELECT *,exp(sum(log(greatest(1e-15,1-events/at_risk))) OVER(PARTITION BY ownership ORDER BY duration ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW)) AS survival FROM risk)
 SELECT ownership,duration/30. AS month,survival*100 AS survival_pct,at_risk,events FROM curve
 UNION ALL SELECT ownership,0. AS month,100. AS survival_pct,count() AS at_risk,toInt64(0) AS events FROM \"{root}/cohort\" GROUP BY ownership
 ORDER BY ownership,month''',
'cohort_summary':f'''SELECT ownership,count() AS establishments,sum(event) AS events,quantileExact(0.5)(duration) AS median_observation_days
 FROM "{root}/cohort" GROUP BY ownership''',
}
for name,sql in queries.items():
 if s.client.exists(root+'/'+name):
  m['tables'][name]=root+'/'+name;print('Reusing',name,flush=True);continue
 f=s.query(name,sql);f.to_csv(out/'tables'/(name+'.csv'),index=False);(out/'sql'/(name+'.sql')).write_text(sql);m['tables'][name]=s.publish(name,f,root);print(name,len(f),f.head(3).to_dict('records'),flush=True)
m['queries'].extend(s.audit);(out/'manifest.json').write_text(json.dumps(m,ensure_ascii=False,indent=2))
