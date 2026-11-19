"""Versioned SQL contracts. Every filter, join, topic and statistic executes in CHYT."""
from pathlib import Path
import re

TOPICS = {
    'сервис': ['обслуживан','официант','персонал','ждать','долго','медленн','хамств','груб','невнимательн','очередь'],
    'еда': ['вкусн','невкусн','еда','блюдо','кухн','свеж','несвеж','порци','сыр','мясо','рыб'],
    'цена': ['дорого','цена','чек','переплат','стоимост','дешев','наценк'],
    'чистота': ['грязн','чист','туалет','пыль','запах','санитар'],
    'атмосфера': ['шумн','атмосфер','интерьер','музык','тесно','душн','уютн'],
}
RULE_VERSION = 'substring-ru-v2'


def literal(value):
    return "'" + str(value).replace('\\', '\\\\').replace("'", "\\'") + "'"


def table_path(value):
    if not re.fullmatch(r'//home/spb_food/stg/[a-z_]+', value):
        raise ValueError('Source must be a known read-only staging path')
    return '"' + value + '"'


def context(cfg):
    a = cfg['analysis']
    categories = a.get('categories') or []
    city_filter = ' AND city = ' + literal(a['city']) if a.get('city') else ''
    category_filter = ' AND category IN (' + ','.join(map(literal,categories)) + ')' if categories else ''
    threshold = int(a.get('chain_min_branches',2))
    if threshold < 2: raise ValueError('chain_min_branches must be >=2')
    date_to = a['date_to']
    if not re.fullmatch(r'\d{4}-\d{2}-\d{2}',date_to): raise ValueError('Invalid date_to')
    branches = table_path(cfg['tables']['establishments']['path'])
    reviews = table_path(cfg['tables']['reviews']['path'])
    wayback = table_path(cfg['tables']['wayback']['path'])
    osm = table_path(cfg['tables']['osm']['path'])
    normalized = f'''WITH
      branch_raw AS (SELECT *, YPathExtract(rubrics, '',
          'Array(Tuple(name String, kind String))') AS rubric_list FROM {branches}),
      branches AS (SELECT id, org_id, city, lat, lon, rating, review_count, deleted_at,
        if(empty(arrayFirst(x -> x.2 = 'primary', rubric_list).1),
           ifNull(nullIf(rubric_list[1].1, ''), 'Неизвестно'),
           arrayFirst(x -> x.2 = 'primary', rubric_list).1) AS category,
        ifNull(nullIf(trimBoth(district), ''), 'Неизвестно') AS district,
        multiIf(empty(ifNull(org_id,'')) OR org_branch_count IS NULL OR org_branch_count < 1,
          'unknown', org_branch_count >= {threshold}, 'chain', 'independent') AS ownership,
        multiIf(is_deleted = 1 OR source = 'closed', 'deleted',
          is_deleted = 0 AND source = 'active', 'active', 'unknown') AS status
        FROM branch_raw),
      category_scope AS (SELECT * FROM branches WHERE 1 {category_filter}),
      scoped AS (SELECT * FROM category_scope WHERE 1 {city_filter}),
      active AS (SELECT * FROM scoped WHERE status = 'active')'''
    return dict(base=normalized, reviews=reviews, wayback=wayback, osm=osm,
                date=literal(date_to), rules=literal(RULE_VERSION),
                topic_array='[' + ','.join(
                    f'({literal(t)}, toUInt8(multiSearchAnyUTF8(lowerUTF8(ifNull(text,\'\')), [' +
                    ','.join(literal(k) for k in keys) + '])))'
                    for t,keys in TOPICS.items()) + ']')


def build_queries(task,cfg):
    ctx = context(cfg)
    names = {
        0: ['quality','overview','geography','quality_coverage','quality_homogeneity'],
        1: ['task1_structure','task1_overview'],
        2: ['task2_summary','task2_distribution','task2_tests','task2_intervals'],
        3: ['task3_archive','task3_deletions','task3_osm'],
        4: ['task4_audit','task4_ratings','task4_topics','task4_overview','task4_topic_overview'],
    }[task]
    root = Path(__file__).resolve().parents[2] / 'server_sql'
    counter_path = cfg.get('_review_counters_path','//home/team/foodservice_analytics/fixture/review_topic_counters')
    if not re.fullmatch(r'//home/team/foodservice_analytics/[A-Za-z0-9_-]+/review_topic_counters',counter_path):
        raise ValueError('Unsafe counter table path')
    ctx['counters'] = '"'+counter_path+'"'
    ctx['negative_cte'] = (root/'negative_cte.sql').read_text().format(**ctx)
    ctx['review_cte'] = (root/'reviews_cte.sql').read_text().format(**ctx)
    return {name: (root/(name+'.sql')).read_text().format(**ctx) for name in names}
