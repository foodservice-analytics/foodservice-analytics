{base}
SELECT city, status,count() AS branches FROM category_scope GROUP BY city,status ORDER BY branches DESC
