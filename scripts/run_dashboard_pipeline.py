"""Reproduce the final server analysis and observation-date history/model marts."""
import argparse,subprocess,sys,json,hashlib
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from src.paths import latest_file
parser=argparse.ArgumentParser()
parser.add_argument('--reuse-analysis',action='store_true',help='Use the last completed and verified descriptive run')
args=parser.parse_args()
def execute(name):
 subprocess.run([sys.executable,'scripts/'+name],check=True)
if not args.reuse_analysis:
 subprocess.run([sys.executable,'scripts/run_server_analysis.py','--task','all','--publish'],check=True)
base=Path(latest_file('analysis').read_text().strip())
manifest=json.loads((base/'manifest.json').read_text())
if manifest['status']!='complete':raise RuntimeError('A completed base run is required')
execute('build_history_marts.py')
out=Path(latest_file('history').read_text().strip())
def update(**values):
 m=json.loads((out/'manifest.json').read_text());m.update(values)
 (out/'manifest.json').write_text(json.dumps(m,ensure_ascii=False,indent=2))
update(status='running')
try:
 for script in ['finish_history_marts.py','run_cox_model.py','build_bi_metrics.py']:execute(script)
 update(status='complete',parent_analysis_run=str(base),source_versions=manifest['sources'],
  worker_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in Path('src/server_pipeline/workers').glob('*.py')})
except BaseException:
 update(status='failed');raise
print('ANALYSIS',base);print('HISTORY_MODEL',out)
