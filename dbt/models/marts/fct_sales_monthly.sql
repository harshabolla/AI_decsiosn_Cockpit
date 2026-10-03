-- Mart model: Monthly aggregated sales by product, region, and channel
WITH enriched_sales AS (
    SELECT * FROM {{ ref('int_sales_enriched') }}
)

SELECT
    sale_month,
    product_key,
    product_name,
    product_category,
    region_key,
    channel,
    SUM(units_sold) AS total_units_sold,
    SUM(gross_revenue) AS total_gross_revenue,
    SUM(discounts) AS total_discounts,
    SUM(net_sales) AS total_net_sales,
    AVG(net_realization_rate) AS avg_net_realization_rate,
    COUNT(DISTINCT sale_id) AS total_transactions
FROM enriched_sales
GROUP BY
    sale_month,
    product_key,
    product_name,
    product_category,
    region_key,
    channel
