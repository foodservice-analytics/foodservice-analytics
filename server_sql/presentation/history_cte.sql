{base}, captures AS (
 SELECT firm_id,toDate(parseDateTimeOrNull(timestamp,'%Y%m%d%H%i%s')) AS seen
 FROM {wayback} WHERE (error IS NULL OR error='') AND notEmpty(ifNull(firm_id,''))),
 archive_history AS (SELECT firm_id,min(seen) AS opened_estimate,max(seen) AS last_seen,count() AS captures
 FROM captures WHERE seen IS NOT NULL AND seen<=toDate({date}) GROUP BY firm_id),
 wb AS (SELECT b.id,b.category,b.district,b.ownership,b.status,b.lat,b.lon,
 h.opened_estimate,h.last_seen,h.captures,
 toUInt8(b.status='deleted') AS event,
 if(b.status='deleted',h.last_seen,toDate({date})) AS ended_estimate
 FROM archive_history h INNER JOIN scoped b ON h.firm_id=b.id)
