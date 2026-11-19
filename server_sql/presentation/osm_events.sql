WITH obs AS (SELECT osm_type,osm_id,toDateOrNull(substring(snapshot,1,10)) AS seen,
 amenity,brand FROM {osm}),
 latest AS (SELECT max(seen) AS last_snapshot FROM obs),
 hist AS (SELECT osm_type,osm_id,min(seen) AS first_seen,max(seen) AS last_seen,
 argMax(ifNull(amenity,'other'),seen) AS amenity,argMax(ifNull(brand,''),seen) AS brand FROM obs WHERE seen IS NOT NULL GROUP BY osm_type,osm_id),
 events AS (
 SELECT toYear(first_seen) AS year,'Открытия' AS event_kind,amenity,brand FROM hist WHERE first_seen>=toDate('2018-01-01')
 UNION ALL
 SELECT toYear(last_seen),'Закрытия',amenity,brand FROM hist WHERE last_seen<(SELECT last_snapshot FROM latest) AND last_seen>=toDate('2023-01-01'))
SELECT year,event_kind,amenity,count() AS establishments,'OSM' AS source
FROM events GROUP BY year,event_kind,amenity ORDER BY year,event_kind,amenity
