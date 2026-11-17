{review_cte}
SELECT category,district,ownership,review_rating AS rating,count() AS reviews
FROM eligible GROUP BY category,district,ownership,rating
