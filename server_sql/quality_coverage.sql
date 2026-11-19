{base}, archived AS (SELECT DISTINCT firm_id FROM {wayback}
 WHERE (error IS NULL OR error='') AND parseDateTimeOrNull(timestamp,'%Y%m%d%H%i%s') < toDateTime(addDays(toDate({date}),1)))
SELECT category,ownership,count() AS branches,
 countIf(a.firm_id IS NOT NULL AND a.firm_id!='') AS archived_branches,
 archived_branches/branches AS coverage
FROM active b LEFT JOIN archived a ON b.id=a.firm_id GROUP BY category,ownership ORDER BY category,ownership
