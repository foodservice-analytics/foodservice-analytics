"""Independent SQL-to-MapReduce reconciliation; fail closed on any lost review."""
from .queries import context

def reconcile_reviews(source):
    cfg=source.cfg
    ctx=context(cfg)
    from pathlib import Path
    cte=(Path(__file__).resolve().parents[2]/'server_sql/reviews_cte.sql').read_text().format(**ctx)
    path=cfg['_review_counters_path']
    if not path.startswith('//home/team/foodservice_analytics/') or '..' in path:raise ValueError('Unsafe counter path')
    sql=cte+f''', sql_totals AS (SELECT count() AS sql_total,countIf(review_rating<=2) AS sql_negative FROM eligible),
        mr_totals AS (SELECT sum(r.c0) AS mr_total,sum(r.c1) AS mr_negative
        FROM "{path}" r INNER JOIN active b ON r.branch_id=b.id)
        SELECT * FROM sql_totals CROSS JOIN mr_totals'''
    frame=source.query('review_counter_reconciliation',sql)
    r=frame.iloc[0]
    if r.sql_total!=r.mr_total or r.sql_negative!=r.mr_negative:
        raise RuntimeError('MapReduce and CHYT counts differ; outputs must not be used')
    return frame
