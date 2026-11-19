{history}
SELECT id,category,district,ownership,lat,lon,opened_estimate,ended_estimate,event,
 greatest(1,dateDiff('day',opened_estimate,ended_estimate)) AS duration,
 'first_last_observation_proxy_v1' AS date_rule
FROM wb WHERE opened_estimate>=toDate('2023-01-01') AND ownership!='unknown'
 AND ended_estimate>=opened_estimate
