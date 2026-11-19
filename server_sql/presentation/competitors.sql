{base}, points AS (SELECT id,lat,lon,status,toInt32(floor(lat/0.003)) AS gy,toInt32(floor(lon/0.006)) AS gx
 FROM scoped WHERE lat BETWEEN 58.5 AND 61 AND lon BETWEEN 28 AND 33),
 neighbors AS (SELECT *,arrayJoin([-1,0,1]) AS dy,arrayJoin([-1,0,1]) AS dx FROM points)
SELECT p.id,countIf(r.status='active' AND r.id!=p.id AND geoDistance(p.lon,p.lat,r.lon,r.lat)<=300) AS competitors_300m
FROM neighbors p LEFT JOIN points r ON p.gy+p.dy=r.gy AND p.gx+p.dx=r.gx
GROUP BY p.id
