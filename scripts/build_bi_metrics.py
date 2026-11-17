"""Presentation percentages derived in CHYT; credentials come from env/local .env."""
import sys,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from src.paths import latest_file
from dotenv import load_dotenv
from src.server_pipeline.source import CHYTSource
from src.config import load_config
load_dotenv();s=CHYTSource(load_config('config/server.yaml'));out=Path(latest_file('history').read_text().strip());m=json.loads((out/'manifest.json').read_text());base=Path(latest_file('analysis').read_text().strip()).name
name='topics_display';target=m['root']+'/'+name
if not s.client.exists(target):
 sql=f'''SELECT ownership,topic,numerator,denominator,100.*numerator/denominator AS share_pct,rule_version FROM "//home/team/foodservice_analytics/{base}/task4_topic_overview"'''
 f=s.query(name,sql);f.to_csv(out/'tables'/f'{name}.csv',index=False);(out/'sql'/f'{name}.sql').write_text(sql);s.publish(name,f,m['root']);m['queries'].extend(s.audit)
m['tables'][name]=target;(out/'manifest.json').write_text(json.dumps(m,ensure_ascii=False,indent=2))
print(target)
