SELECT *
FROM (
    SELECT 
        nameOfClient, 
        brand,
        daytime,
        unique_row_id,
        count,
        EXTRACT(HOUR FROM daytime) AS hour_of_day
    FROM public.local_oltp_raw_data
)
