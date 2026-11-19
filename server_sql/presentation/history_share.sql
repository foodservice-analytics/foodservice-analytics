{history}, grid AS (SELECT arrayJoin(range(2018,2027)) AS year)
SELECT year,ownership,count() AS numerator,
 sum(count()) OVER(PARTITION BY year) AS denominator,numerator/denominator AS share
FROM wb CROSS JOIN grid
WHERE opened_estimate<=least(toDate(concat(toString(year),'-12-31')),toDate({date}))
 AND (event=0 OR ended_estimate>least(toDate(concat(toString(year),'-12-31')),toDate({date})))
GROUP BY year,ownership ORDER BY year,ownership
