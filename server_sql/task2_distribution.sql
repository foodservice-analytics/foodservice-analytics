{base}, metrics AS (
 SELECT category,ownership,'rating' AS metric,rating AS value FROM active WHERE rating BETWEEN 1 AND 5
 UNION ALL
 SELECT category,ownership,'review_count' AS metric,toFloat64(review_count) AS value FROM active WHERE review_count >= 0)
SELECT category,ownership,metric,value,count() AS n
FROM metrics GROUP BY category,ownership,metric,value ORDER BY metric,category,ownership,value
