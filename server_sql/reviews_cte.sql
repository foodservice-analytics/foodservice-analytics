{base},
 dedup AS (SELECT branch_id,review_id,provider,rating AS review_rating,text,
 is_hidden,parseDateTimeBestEffortOrNull(date_created) AS created_at
 FROM {reviews} WHERE notEmpty(ifNull(branch_id,'')) AND notEmpty(ifNull(review_id,''))),
 matched AS (SELECT r.*,b.category,b.district,b.ownership FROM dedup r INNER JOIN active b ON r.branch_id=b.id),
 eligible AS (SELECT * FROM matched WHERE is_hidden=0 AND review_rating BETWEEN 1 AND 5
 AND created_at<toDateTime(addDays(toDate({date}),1)))
