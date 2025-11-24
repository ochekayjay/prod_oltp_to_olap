{{ config(materialized='table') }}

WITH timeWindowBreakDown AS (
        SELECT nameOfClient, 
        brand,daytime,
        unique_row_id ,
        count,
        EXTRACT(HOUR FROM daytime) AS hour_of_day
        FROM public.local_oltp_raw_data

),

 structcall AS (SELECT 
    nameOfClient, 
    brand,
    daytime,
    unique_row_id,
    count,
    hour_of_day,
	CASE
	  WHEN hour_of_day >= 6  AND hour_of_day < 9  THEN '6am-9am'
	  WHEN hour_of_day >= 9  AND hour_of_day < 12 THEN '9am-12pm'
	  WHEN hour_of_day >= 12 AND hour_of_day < 15 THEN '12pm-3pm'
	  WHEN hour_of_day >= 15 AND hour_of_day < 18 THEN '3pm-6pm'
	  WHEN hour_of_day >= 18 AND hour_of_day < 21 THEN '6pm-9pm'
	  WHEN hour_of_day >= 21 AND hour_of_day < 24 THEN '9pm-12am'
	END AS time_window
    

FROM timeWindowBreakDown)
,
 base AS (SELECT 
    * ,  
    -- compute items sold per brand/time_window
    SUM(count) OVER (
        PARTITION BY brand, time_window
    ) AS items_sold

FROM structcall

),

ranked AS (
    SELECT 
        brand,
        daytime,
        time_window,
        items_sold,
        ROW_NUMBER() OVER (
            PARTITION BY brand,time_window
            ORDER BY items_sold DESC
        ) AS rn
    FROM base
),

reselect AS (
	SELECT *
	FROM ranked
	WHERE rn = 1
),

newrank AS (
SELECT *,
ROW_NUMBER() OVER (
            PARTITION BY brand
            ORDER BY items_sold DESC
        ) AS sales_rank
FROM reselect

)

SELECT brand,daytime,time_window,items_sold,sales_rank
FROM newrank
WHERE sales_rank <= 3
ORDER BY brand ASC, items_sold DESC 