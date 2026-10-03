-- Intermediate model joining sales transactions with product metadata
WITH sales AS (
    SELECT * FROM {{ ref('stg_sales') }}
),

products AS (
    SELECT * FROM {{ ref('stg_products') }}
)

SELECT
    s.sale_id,
    s.sale_date,
    DATE_TRUNC('month', s.sale_date) AS sale_month,
    s.product_key,
    p.product_name,
    p.category AS product_category,
    s.region_key,
    s.channel,
    s.units_sold,
    s.gross_revenue,
    s.discounts,
    s.net_sales,
    (s.gross_revenue - s.net_sales) AS total_deductions,
    CASE
        WHEN s.gross_revenue > 0 THEN (s.net_sales / s.gross_revenue) * 100
        ELSE 0
    END AS net_realization_rate
FROM sales s
LEFT JOIN products p ON s.product_key = p.product_key
