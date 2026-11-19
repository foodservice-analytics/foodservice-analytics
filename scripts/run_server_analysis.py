"""CHYT-only CLI. All analytics run remotely; local output contains completed aggregate tables."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import logging
from pathlib import Path
import sys
import uuid
from time import perf_counter
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from src.paths import output_dir, latest_file
from dotenv import load_dotenv
from src.config import load_config
from src.server_pipeline.source import CHYTSource
from src.server_pipeline.queries import build_queries


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--task',required=True,choices=['all','0','1','2','3','4'])
    parser.add_argument('--config',default='config/server.yaml')
    parser.add_argument('--publish',action='store_true',help='Write new run-scoped BI tables under //home/team only')
    args=parser.parse_args()
    logging.basicConfig(level=logging.INFO,format='%(asctime)s %(levelname)s %(message)s')
    load_dotenv()
    cfg=load_config(args.config)
    if cfg['data_source']['type']!='chyt':
        raise RuntimeError('This pipeline requires the CHYT data source')
    run_id=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'_'+uuid.uuid4().hex[:6]
    out=output_dir(cfg)/'runs'/run_id
    (out/'tables').mkdir(parents=True)
    (out/'sql').mkdir()
    source=CHYTSource(cfg)
    manifest={'run_id':run_id,'started_utc':datetime.now(timezone.utc).isoformat(),
              'engine':'YTsaurus MapReduce + CHYT','status':'running','local_analytics':False,
              'published':{},'date_to_semantics':'upper bound, not source acquisition date',
              'config_sha256':hashlib.sha256(Path(args.config).read_bytes()).hexdigest()}
    started=perf_counter()
    try:
        preflight=source.preflight()
        manifest['preflight']=preflight.to_dict('records')
        tasks=range(5) if args.task=='all' else sorted({0,int(args.task)})
        for task in tasks:
            logging.info('Server task %s',task)
            if task==4:
                from src.server_pipeline.mapreduce import start_review_mapreduce
                op,target,mr_start=start_review_mapreduce(source,'//home/team/foodservice_analytics/'+run_id,out)
                manifest['mapreduce']={'operation_id':op.id,'target':target,'status':'running'}
                (out/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2))
                op.wait()
                manifest['mapreduce'].update(status='completed',client_wall_seconds=perf_counter()-mr_start)
                cfg['_review_counters_path']=target
            for name,sql in build_queries(task,cfg).items():
                frame=source.query(name,sql)
                frame.to_csv(out/'tables'/(name+'.csv'),index=False)
                if args.publish:
                    path=source.publish(name,frame,'//home/team/foodservice_analytics/'+run_id)
                    if path: manifest['published'][name]=path
        if '_review_counters_path' in cfg:
            from src.server_pipeline.validation import reconcile_reviews
            reconciliation=reconcile_reviews(source)
            reconciliation.to_csv(out/'tables'/'review_reconciliation.csv',index=False)
            manifest['review_counter_reconciliation']=reconciliation.to_dict('records')
        # Check revisions after the run; mixed source versions must not look like a coherent snapshot.
        manifest['sources_unchanged']=all(source.client.get(cfg['tables'][k]['path']+'/@revision')==v['revision'] for k,v in source.versions.items())
        if not manifest['sources_unchanged']:
            raise RuntimeError('Source revision changed during run; rerun for a coherent snapshot')
        manifest['status']='complete'
        latest_file('analysis',cfg).write_text(str(out.resolve()))
        logging.info('Result: %s',out.resolve())
    except Exception as exc:
        manifest['status']='failed'
        manifest['error_type']=type(exc).__name__
        raise
    finally:
        for name,sql in source.queries.items():
            (out/'sql'/(name+'.sql')).write_text(sql)
        manifest.update(queries=source.audit,sources=source.versions,
                        client_total_seconds=perf_counter()-started,
                        timing_note='client wall includes server, network and deserialization; not isolated server CPU time')
        (out/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2))
        logging.info('Manifest: %s',out/'manifest.json')

if __name__=='__main__': main()
