{base}, metrics AS (
 SELECT category,district,ownership,'rating' AS metric,rating AS value FROM active WHERE rating BETWEEN 1 AND 5
 UNION ALL
 SELECT category,district,ownership,'review_count' AS metric,toFloat64(review_count) AS value FROM active WHERE review_count >= 0)
SELECT category,ownership,metric,count() AS n,avg(value) AS mean,
 quantileExactInclusive(0.5)(value) AS median,
 quantileExactInclusive(0.25)(value) AS q25,
 quantileExactInclusive(0.75)(value) AS q75,
 min(value) AS minimum,max(value) AS maximum,
 'all_districts_fixed_scope' AS statistical_scope
FROM metrics GROUP BY category,ownership,metric ORDER BY metric,category,ownership
