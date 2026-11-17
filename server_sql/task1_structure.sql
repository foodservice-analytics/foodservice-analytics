{base}, counts AS (
 SELECT category, district, ownership, count() AS numerator
 FROM active GROUP BY category, district, ownership)
SELECT *, sum(numerator) OVER (PARTITION BY category,district) AS denominator,
 numerator / denominator AS share_all,
 'current_snapshot' AS period_semantics
FROM counts ORDER BY category,district,ownership
