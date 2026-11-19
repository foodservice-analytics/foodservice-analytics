{base}, negative_scoped AS (
 SELECT b.category,b.district,b.ownership,r.c1 AS negative_n,
 r.c3 AS service_n,r.c4 AS food_n,r.c5 AS price_n,r.c6 AS cleanliness_n,r.c7 AS atmosphere_n,r.c8 AS unmatched_n
 FROM {counters} r INNER JOIN active b ON r.branch_id=b.id WHERE r.c1>0),
 expanded AS (SELECT category,district,ownership,negative_n,
 arrayJoin([('сервис',service_n),('еда',food_n),('цена',price_n),('чистота',cleanliness_n),('атмосфера',atmosphere_n),('без совпадений',unmatched_n)]) AS entry FROM negative_scoped)
