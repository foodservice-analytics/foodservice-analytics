{base}, dated AS (SELECT *,parseDateTimeBestEffortOrNull(deleted_at) AS deletion_time FROM scoped WHERE status='deleted')
SELECT category,ownership,
 toYear(deletion_time) AS year,count() AS cards,
 'card_deletion_timestamp_not_verified_business_closure' AS semantics
FROM dated WHERE deletion_time>=toDateTime('2023-01-01')
 AND deletion_time<toDateTime(addDays(toDate({date}),1))
GROUP BY category,ownership,year ORDER BY year,category,ownership
