-- These functions provide comprehensive data quality checks
-- Function to check for null values in critical columns
CREATE OR REPLACE FUNCTION check_null_values(table_name STRING, column_name STRING)
RETURNS TABLE (
    table_name STRING,
    column_name STRING,
    null_count NUMBER,
    total_count NUMBER,
    null_percentage NUMBER
)
AS
$$
SELECT 
    table_name,
    column_name,
    SUM(CASE WHEN column_name IS NULL THEN 1 ELSE 0 END) as null_count,
    COUNT(*) as total_count,
    ROUND((null_count / total_count) * 100, 2) as null_percentage
FROM IDENTIFIER(table_name)
GROUP BY table_name, column_name
$$;

-- Function to validate data freshness
CREATE OR REPLACE FUNCTION check_data_freshness(table_name STRING, date_column STRING, max_age_hours NUMBER)
RETURNS TABLE (
    table_name STRING,
    latest_record TIMESTAMP,
    hours_since_latest NUMBER,
    is_fresh BOOLEAN
)
AS
$$
SELECT 
    table_name,
    MAX(IDENTIFIER(date_column)) as latest_record,
    DATEDIFF('hour', latest_record, CURRENT_TIMESTAMP()) as hours_since_latest,
    CASE WHEN hours_since_latest <= max_age_hours THEN TRUE ELSE FALSE END as is_fresh
FROM IDENTIFIER(table_name)
GROUP BY table_name
$$;

-- Function to detect duplicate records
CREATE OR REPLACE FUNCTION check_duplicates(table_name STRING, key_columns ARRAY)
RETURNS TABLE (
    table_name STRING,
    duplicate_count NUMBER,
    total_records NUMBER,
    duplicate_percentage NUMBER
)
AS
$$
WITH duplicate_check AS (
    SELECT COUNT(*) as record_count
    FROM IDENTIFIER(table_name)
    GROUP BY ARRAY_TO_STRING(key_columns, ',')
    HAVING COUNT(*) > 1
)
SELECT 
    table_name,
    COALESCE(SUM(record_count - 1), 0) as duplicate_count,
    (SELECT COUNT(*) FROM IDENTIFIER(table_name)) as total_records,
    ROUND((duplicate_count / total_records) * 100, 2) as duplicate_percentage
FROM duplicate_check
$$;

-- Function to validate referential integrity
CREATE OR REPLACE FUNCTION check_referential_integrity(
    child_table STRING, 
    child_column STRING,
    parent_table STRING,
    parent_column STRING
)
RETURNS TABLE (
    child_table STRING,
    orphaned_records NUMBER,
    total_child_records NUMBER,
    integrity_percentage NUMBER
)
AS
$$
SELECT 
    child_table,
    COUNT(c.*) - COUNT(p.*) as orphaned_records,
    COUNT(c.*) as total_child_records,
    ROUND(((total_child_records - orphaned_records) / total_child_records) * 100, 2) as integrity_percentage
FROM IDENTIFIER(child_table) c
LEFT JOIN IDENTIFIER(parent_table) p ON c.IDENTIFIER(child_column) = p.IDENTIFIER(parent_column)
$$;

-- Function to validate data ranges
CREATE OR REPLACE FUNCTION check_data_ranges(
    table_name STRING,
    column_name STRING,
    min_value NUMBER,
    max_value NUMBER
)
RETURNS TABLE (
    table_name STRING,
    column_name STRING,
    out_of_range_count NUMBER,
    total_count NUMBER,
    compliance_percentage NUMBER
)
AS
$$
SELECT 
    table_name,
    column_name,
    SUM(CASE WHEN IDENTIFIER(column_name) < min_value OR IDENTIFIER(column_name) > max_value THEN 1 ELSE 0 END) as out_of_range_count,
    COUNT(*) as total_count,
    ROUND(((total_count - out_of_range_count) / total_count) * 100, 2) as compliance_percentage
FROM IDENTIFIER(table_name)
WHERE IDENTIFIER(column_name) IS NOT NULL
GROUP BY table_name, column_name
$$;