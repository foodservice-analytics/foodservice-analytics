{base}, archived AS (SELECT DISTINCT firm_id FROM {wayback}
 WHERE (error IS NULL OR error='') AND parseDateTimeOrNull(timestamp,'%Y%m%d%H%i%s') < toDateTime(addDays(toDate({date}),1))),
 cells AS (SELECT category,toUInt8(a.firm_id IS NOT NULL AND a.firm_id!='') AS matched,count() AS observed
 FROM active b LEFT JOIN archived a ON b.id=a.firm_id GROUP BY category,matched),
 grid AS (SELECT c.category,m.matched FROM (SELECT DISTINCT category FROM active) c CROSS JOIN (SELECT arrayJoin([0,1]) AS matched) m),
 complete AS (SELECT g.category,g.matched,ifNull(c.observed,0) AS observed FROM grid g LEFT JOIN cells c ON g.category=c.category AND g.matched=c.matched),
 margins AS (SELECT *,sum(observed) OVER (PARTITION BY category) AS row_n,
 sum(observed) OVER (PARTITION BY matched) AS col_n,sum(observed) OVER () AS total FROM complete),
 expected AS (SELECT *,row_n*col_n/toFloat64(total) AS expected FROM margins)
SELECT sum(pow(observed-expected,2)/nullIf(expected,0)) AS chi_square,
 uniqExact(category)-1 AS degrees_of_freedom,any(total) AS n,
 sqrt(chi_square/n) AS cramers_v,countIf(expected<5) AS cells_expected_below_5,
 'Descriptive archive coverage heterogeneity by category; no proof of city-market completeness' AS interpretation
FROM expected
