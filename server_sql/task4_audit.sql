{review_cte}
SELECT 'raw_rows' AS stage,count() AS n FROM {reviews}
UNION ALL SELECT 'nonempty_id_rows',count() FROM {reviews} WHERE notEmpty(ifNull(branch_id,'')) AND notEmpty(ifNull(review_id,''))
UNION ALL SELECT 'deduplicated_branch_review_provider',count() FROM dedup
UNION ALL SELECT 'matched_active_scope',count() FROM matched
UNION ALL SELECT 'matched_hidden',count() FROM matched WHERE is_hidden=1
UNION ALL SELECT 'matched_hidden_unknown',count() FROM matched WHERE is_hidden IS NULL
UNION ALL SELECT 'matched_invalid_rating',count() FROM matched WHERE review_rating IS NULL OR review_rating NOT BETWEEN 1 AND 5
UNION ALL SELECT 'matched_missing_date',count() FROM matched WHERE created_at IS NULL
UNION ALL SELECT 'eligible_valid_visible_dated',count() FROM eligible
