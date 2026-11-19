{base}, metrics AS (
 SELECT category,org_id,ownership,'rating' AS metric,assumeNotNull(rating) AS value FROM active WHERE rating BETWEEN 1 AND 5 AND ownership!='unknown'
 UNION ALL
 SELECT category,org_id,ownership,'review_count' AS metric,toFloat64(assumeNotNull(review_count)) AS value FROM active WHERE review_count>=0 AND ownership!='unknown'),
 clusters AS (SELECT category,metric,ownership,org_id,sum(value) AS sx,count() AS nx
 FROM metrics GROUP BY category,metric,ownership,org_id),
 totals AS (SELECT *,sum(sx) OVER (PARTITION BY category,metric,ownership) AS total,
 sum(nx) OVER (PARTITION BY category,metric,ownership) AS n FROM clusters),
 variances AS (SELECT category,metric,ownership,count() AS g,any(n) AS sample_n,
 any(total)/any(n) AS mean_value,
 if(g>=2, g/(g-1.)*sum(pow(sx-total/n*nx,2))/pow(any(n),2),NULL) AS cluster_variance
 FROM totals GROUP BY category,metric,ownership),
 paired AS (SELECT category,metric,
 anyIf(g,ownership='chain') AS chain_clusters,
 anyIf(g,ownership='independent') AS independent_clusters,
 anyIf(mean_value,ownership='chain')-anyIf(mean_value,ownership='independent') AS mean_diff,
 sqrt(sum(cluster_variance)) AS standard_error,
 count() AS groups
 FROM variances GROUP BY category,metric HAVING groups=2 AND chain_clusters>=2 AND independent_clusters>=2)
SELECT *,mean_diff-1.96*standard_error AS mean_diff_ci_low,
 mean_diff+1.96*standard_error AS mean_diff_ci_high,
 'org-cluster sandwich variance, normal 95% CI; groups disjoint; all districts fixed; exploratory' AS method
FROM paired ORDER BY metric,category
