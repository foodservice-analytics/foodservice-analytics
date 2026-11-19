{negative_cte}
SELECT category,district,ownership,entry.1 AS topic,
 sum(entry.2) AS numerator,sum(negative_n) AS denominator,numerator/denominator AS share,
 {rules} AS rule_version,'negative reviews rated 1-2; topics overlap; mentions not proven causes' AS semantics
FROM expanded GROUP BY category,district,ownership,topic
