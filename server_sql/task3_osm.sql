SELECT snapshot,count() AS rows,uniqExact(tuple(osm_type,osm_id)) AS unique_objects,
 'OSM mapping coverage; not openings or closures; not matched to 2GIS' AS semantics
FROM {osm} GROUP BY snapshot ORDER BY snapshot
