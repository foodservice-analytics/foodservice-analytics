"""Launch the text kernel on YT; CHYT consumes only the small per-branch counters."""
from pathlib import Path
from time import perf_counter
import json
import yt.wrapper as yt
from .queries import TOPICS

def start_review_mapreduce(source,root,out):
    client=source.client
    if not root.startswith('//home/team/foodservice_analytics/') or '..' in root:raise ValueError('Unsafe MR output root')
    target=root+'/review_topic_counters'
    if client.exists(target):raise FileExistsError(target)
    client.create('map_node',root,recursive=True,ignore_existing=True)
    client.config['remote_temp_files_directory']=root+'/job_files'
    client.config['remote_temp_tables_directory']=root+'/temp_tables'
    schema=[{'name':'branch_id','type':'string'}]+[{'name':'c'+str(i),'type':'int64'} for i in range(14)]
    client.create('table',target,attributes={'schema':schema,'optimize_for':'scan'})
    rules=Path(out)/'topic_rules.json';rules.write_text(json.dumps(TOPICS,ensure_ascii=False))
    workers=Path(__file__).resolve().parent/'workers'
    start=perf_counter()
    op=client.run_map_reduce(
        mapper='python3 review_mapper.py '+source.cfg['analysis']['date_to'],
        reducer='python3 review_reducer.py',
        source_table=yt.TablePath(source.cfg['tables']['reviews']['path'],columns=['branch_id','review_id','rating','text','is_hidden','date_created']),
        destination_table=target,
        map_local_files=[str(workers/'review_mapper.py'),yt.LocalFile(str(rules),file_name='topic_rules.json')],
        reduce_local_files=[str(workers/'review_reducer.py')],
        format=yt.JsonFormat(encode_utf8=False),reduce_by=['branch_id'],
        mapper_memory_limit=256*1024**2,reducer_memory_limit=128*1024**2,
        spec={'title':'Foodservice review topics: server streaming counters',
              'map_job_count':16,'partition_count':4,'max_failed_job_count':1,
              'resource_limits':{'cpu':2},'mapper':{'cpu_limit':1},'reducer':{'cpu_limit':1}},sync=False)
    return op,target,start
