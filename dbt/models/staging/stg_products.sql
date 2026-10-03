-- Staging model for product master data
WITH source AS (
    SELECT * FROM {{ source('raw_mdm', 'product_master') }}
),

renamed AS (
    SELECT
        CAST(product_id AS INTEGER) AS product_key,
        TRIM(product_name) AS product_name,
        TRIM(therapeutic_area) AS category,
        CAST(global_launch_year AS INTEGER) AS launch_year,
        is_active,
        _updated_at
    FROM source
)

SELECT * FROM renamed
