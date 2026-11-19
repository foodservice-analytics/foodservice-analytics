{base}, metrics AS (
 SELECT category,ownership,'rating' AS metric,rating AS value FROM active WHERE rating BETWEEN 1 AND 5 AND ownership != 'unknown'
 UNION ALL
 SELECT category,ownership,'review_count' AS metric,toFloat64(review_count) AS value FROM active WHERE review_count >= 0 AND ownership != 'unknown'),
 histogram AS (SELECT category,metric,value,countIf(ownership='chain') AS nc,
 countIf(ownership='independent') AS ni FROM metrics GROUP BY category,metric,value),
 ranks AS (SELECT *, sum(ni) OVER (PARTITION BY category,metric ORDER BY value ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) - ni AS below
 FROM histogram),
 totals AS (SELECT category,metric,sum(nc) AS n_chain,sum(ni) AS n_independent,
 sum(nc*(below+ni/2.)) AS u_stat,sum(pow(nc+ni,3)-(nc+ni)) AS tie_sum FROM ranks GROUP BY category,metric),
 inference AS (SELECT *,n_chain+n_independent AS n,
 sqrt(n_chain*n_independent/12.*((n+1)-tie_sum/nullIf(n*(n-1),0))) AS sd,
 2*u_stat/nullIf(n_chain*n_independent,0)-1 AS cliffs_delta,
 if(n_chain>=5 AND n_independent>=5 AND sd>0,
  erfc(greatest(0.,abs(u_stat-n_chain*n_independent/2.)-0.5)/sd/sqrt(2)),NULL) AS p_value FROM totals),
 ordered AS (SELECT *,row_number() OVER (ORDER BY p_value,metric,category) AS rn,
 count() OVER () AS tests_in_family FROM inference WHERE p_value IS NOT NULL)
SELECT category,metric,n_chain,n_independent,u_stat,cliffs_delta,p_value,
 least(1.,max((tests_in_family-rn+1)*p_value) OVER (ORDER BY p_value,metric,category ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW)) AS p_holm,
 'Mann-Whitney asymptotic, ties+continuity; branches not independent within org' AS method,
 'all_districts_fixed_scope' AS statistical_scope
FROM ordered
