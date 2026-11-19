{base}, grouped AS (
 SELECT 'category' AS dimension,category AS label,ownership,count() AS numerator FROM active GROUP BY category,ownership
 UNION ALL SELECT 'district',district,ownership,count() FROM active GROUP BY district,ownership
 UNION ALL SELECT 'all','Вся выборка',ownership,count() FROM active GROUP BY ownership)
SELECT *,sum(numerator) OVER (PARTITION BY dimension,label) AS denominator,
 numerator/denominator AS share_all FROM grouped ORDER BY dimension,label,ownership
