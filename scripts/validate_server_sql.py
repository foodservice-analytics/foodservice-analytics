"""Small live CHYT fixtures plus independent counter reconciliation; no raw texts downloaded."""
import sys,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from src.paths import latest_file
from dotenv import load_dotenv
from scipy.stats import mannwhitneyu
from src.config import load_config
from src.server_pipeline.source import CHYTSource
from src.server_pipeline.queries import build_queries,context,literal
from src.server_pipeline.validation import reconcile_reviews
load_dotenv()
cfg=load_config('config/server.yaml');source=CHYTSource(cfg)
# Compare the actual SQL statistic with SciPy's independent implementation on tied values.
chain=[1,2,2,3,4,5];independent=[1,1,2,2,3,4]
rows=[]
for ownership,values in [('chain',chain),('independent',independent)]:
    for i,value in enumerate(values):
        rows.append(f"SELECT 'fixture' AS category,{literal(ownership)} AS ownership,{float(value)} AS rating,{value} AS review_count,{literal(ownership+str(i))} AS org_id")
fixture='WITH active AS ('+' UNION ALL '.join(rows)+')'
base=context(cfg)['base']
query=build_queries(2,cfg)['task2_tests'].replace(base,fixture)
result=source.query('fixture_mannwhitney',query)
expected=mannwhitneyu(chain,independent,alternative='two-sided',method='asymptotic',use_continuity=True)
for r in result.itertuples():
    assert abs(r.u_stat-expected.statistic)<1e-12
    assert abs(r.p_value-expected.pvalue)<1e-12
print('PASS SQL Mann-Whitney vs SciPy (ties + continuity, both metrics)')
# Primary rubric past index four, unknown ownership/status, missing district.
rubrics='[{name="x";kind="additional"};{name="x";kind="additional"};{name="x";kind="additional"};{name="x";kind="additional"};{name="x";kind="additional"};{name="Кафе";kind="primary"}]'
raw=f'''(SELECT 'a' AS id,'org' AS org_id,'Санкт-Петербург' AS city,60. AS lat,30. AS lon,
 4. AS rating,10 AS review_count,cast(NULL AS Nullable(String)) AS deleted_at,
 cast(NULL AS Nullable(String)) AS district,0 AS is_deleted,'active' AS source,
 cast(NULL AS Nullable(Int64)) AS org_branch_count,{literal(rubrics)} AS rubrics)'''
sql=base.replace('"//home/spb_food/stg/branches"',raw)+' SELECT id,category,ownership,status,district FROM branches'
r=source.query('fixture_normalization',sql).iloc[0]
assert (r.category,r.ownership,r.status,r.district)==('Кафе','unknown','active','Неизвестно')
print('PASS primary rubric beyond index 4; unknown owner; missing district')
consistency=source.query('org_group_consistency',base+" SELECT count() AS conflicts FROM (SELECT org_id FROM active WHERE ownership!='unknown' GROUP BY org_id HAVING uniqExact(ownership)>1)")
assert consistency.iloc[0]['conflicts']==0,'Ownership groups overlap by org_id; covariance must be included'
print('PASS ownership groups disjoint by org_id in the analysis scope')
latest=latest_file('analysis')
if latest.exists():
    out=Path(latest.read_text().strip());manifest=json.loads((out/'manifest.json').read_text())
    if manifest.get('mapreduce',{}).get('status')=='completed':
        cfg['_review_counters_path']=manifest['mapreduce']['target']
        frame=reconcile_reviews(source)
        frame.to_csv(out/'tables/review_reconciliation.csv',index=False)
        manifest['review_counter_reconciliation']=frame.to_dict('records')
        manifest['validation_queries']=source.audit
        (out/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2))
        print('PASS MR/SQL reconciliation',frame.to_dict('records'))
        (out/'validation.json').write_text(json.dumps({'status':'passed','checks':4,'queries':source.audit},ensure_ascii=False,indent=2))
