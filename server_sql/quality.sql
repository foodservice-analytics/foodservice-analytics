{base}
SELECT category, district, ownership, status, count() AS branches,
 countIf(rating BETWEEN 1 AND 5) AS valid_rating,
 countIf(review_count >= 0) AS valid_review_count,
 countIf(lat BETWEEN -90 AND 90 AND lon BETWEEN -180 AND 180) AS valid_coordinates,
 countIf(notEmpty(ifNull(deleted_at,''))) AS has_deletion_timestamp
FROM scoped GROUP BY category, district, ownership, status
