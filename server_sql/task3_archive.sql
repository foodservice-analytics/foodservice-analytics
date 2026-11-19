{base}, observations AS (
 SELECT firm_id,parseDateTimeOrNull(timestamp,'%Y%m%d%H%i%s') AS observed_at
 FROM {wayback} WHERE error IS NULL OR error=''),
 firsts AS (SELECT firm_id,min(observed_at) AS first_seen FROM observations WHERE observed_at IS NOT NULL GROUP BY firm_id),
 yearly AS (SELECT firm_id, toYear(observed_at) AS year,count() AS snapshots FROM observations
 WHERE observed_at>=toDateTime('2018-01-01') AND observed_at<toDateTime(addDays(toDate({date}),1)) GROUP BY firm_id,year)
SELECT year,count() AS observed_firms,sum(snapshots) AS snapshots,
 countIf(toYear(f.first_seen)=year) AS first_observed_firms,
 countIf(b.id IS NOT NULL AND b.id!='') AS matched_scoped_firms,
 'archive_observations_not_openings; current attributes' AS semantics
FROM yearly y LEFT JOIN firsts f ON y.firm_id=f.firm_id
LEFT JOIN scoped b ON y.firm_id=b.id GROUP BY year ORDER BY year
