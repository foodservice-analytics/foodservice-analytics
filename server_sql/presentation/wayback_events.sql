{history}
SELECT year,category,ownership,event_kind,count() AS establishments,'Wayback' AS source
FROM (
 SELECT toYear(opened_estimate) AS year,category,ownership,'Открытия' AS event_kind FROM wb WHERE opened_estimate>=toDate('2018-01-01')
 UNION ALL
 SELECT toYear(ended_estimate),category,ownership,'Закрытия' FROM wb WHERE event=1 AND ended_estimate>=toDate('2023-01-01'))
GROUP BY year,category,ownership,event_kind ORDER BY year,category,ownership,event_kind
