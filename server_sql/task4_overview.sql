{base}
SELECT b.category,b.ownership,sum(r.c0) AS total,sum(r.c1) AS negative,
 negative/total AS negative_share,sum(r.c2) AS negative_with_text
FROM {counters} r INNER JOIN active b ON r.branch_id=b.id
GROUP BY b.category,b.ownership ORDER BY b.category,b.ownership
