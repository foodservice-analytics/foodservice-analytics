{base}
SELECT 'staging_branches' AS metric,count() AS n FROM branches
UNION ALL SELECT 'scoped_branches',count() FROM scoped
UNION ALL SELECT 'active_scoped',count() FROM active
UNION ALL SELECT 'unknown_ownership_active',count() FROM active WHERE ownership='unknown'
UNION ALL SELECT 'current_deleted_scoped',count() FROM scoped WHERE status='deleted'
UNION ALL SELECT 'staging_reviews',count() FROM {reviews}
UNION ALL SELECT 'excluded_city_filter',count() FROM category_scope WHERE id NOT IN (SELECT id FROM scoped)
