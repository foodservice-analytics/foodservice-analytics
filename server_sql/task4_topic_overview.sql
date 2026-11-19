{negative_cte}
SELECT ownership,entry.1 AS topic,sum(entry.2) AS numerator,sum(negative_n) AS denominator,
 numerator/denominator AS share,{rules} AS rule_version
FROM expanded GROUP BY ownership,topic ORDER BY topic,ownership
