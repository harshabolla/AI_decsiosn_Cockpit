-- Staging model for raw sales transactions
WITH source AS (
    SELECT * FROM {{ source('raw_erp', 'sales_transactions') }}
),

renamed AS (
    SELECT
        transaction_id AS sale_id,
        CAST(transaction_date AS DATE) AS sale_date,
        CAST(product_id AS INTEGER) AS product_key,
        CAST(region_id AS INTEGER) AS region_key,
        TRIM(LOWER(channel)) AS channel,
        CAST(units AS INTEGER) AS units_sold,
        CAST(gross_amount AS DOUBLE PRECISION) AS gross_revenue,
        CAST(COALESCE(discount_amount, 0) AS DOUBLE PRECISION) AS discounts,
        CAST(net_amount AS DOUBLE PRECISION) AS net_sales,
        _loaded_at
    FROM source
)

SELECT * FROM renamed
