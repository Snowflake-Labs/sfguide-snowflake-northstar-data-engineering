-- Automated Data Profiling Script for Snowflake Tables
-- Generates comprehensive data profiles including statistics, distributions, and patterns
-- Create table to store data profiling results
CREATE OR REPLACE TABLE data_profile_results (
    profile_id STRING DEFAULT UUID_STRING(),
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
    table_name STRING,
    column_name STRING,
    data_type STRING,
    total_count NUMBER,
    null_count NUMBER,
    null_percentage NUMBER,
    distinct_count NUMBER,
    distinct_percentage NUMBER,
    min_value VARIANT,
    max_value VARIANT,
    avg_value NUMBER,
    std_dev NUMBER,
    min_length NUMBER,
    max_length NUMBER,
    avg_length NUMBER,
    pattern_analysis VARIANT
);

-- Procedure to profile a specific table
CREATE OR REPLACE PROCEDURE profile_table(table_name STRING)
RETURNS STRING
LANGUAGE SQL
AS
$$
DECLARE
    column_cursor CURSOR FOR 
        SELECT column_name, data_type 
        FROM information_schema.columns 
        WHERE table_name = UPPER(table_name);
    
    col_name STRING;
    col_type STRING;
    profile_sql STRING;
    result_cursor CURSOR FOR SELECT * FROM TABLE(RESULT_SCAN(LAST_QUERY_ID()));
    
    total_count NUMBER;
    null_count NUMBER;
    null_percentage NUMBER;
    distinct_count NUMBER;
    distinct_percentage NUMBER;
    min_value VARIANT;
    max_value VARIANT;
    avg_value NUMBER;
    std_dev NUMBER;
    min_length NUMBER;
    max_length NUMBER;
    avg_length NUMBER;
BEGIN
    -- Clear existing profile results for this table
    DELETE FROM data_profile_results WHERE table_name = table_name;
    
    -- Loop through each column
    FOR record IN column_cursor DO
        col_name := record.column_name;
        col_type := record.data_type;
        
        -- Build dynamic SQL based on data type
        IF col_type IN ('NUMBER', 'DECIMAL', 'NUMERIC', 'INT', 'INTEGER', 'BIGINT', 'SMALLINT', 'TINYINT', 'FLOAT', 'DOUBLE') THEN
            profile_sql := 'SELECT 
                COUNT(*) as total_count,
                COUNT(CASE WHEN ' || col_name || ' IS NULL THEN 1 END) as null_count,
                ROUND((null_count / total_count) * 100, 2) as null_percentage,
                COUNT(DISTINCT ' || col_name || ') as distinct_count,
                ROUND((distinct_count / total_count) * 100, 2) as distinct_percentage,
                MIN(' || col_name || ') as min_value,
                MAX(' || col_name || ') as max_value,
                AVG(' || col_name || ') as avg_value,
                STDDEV(' || col_name || ') as std_dev,
                NULL as min_length,
                NULL as max_length,
                NULL as avg_length
                FROM ' || table_name;
                
        ELSIF col_type IN ('VARCHAR', 'CHAR', 'TEXT', 'STRING') THEN
            profile_sql := 'SELECT 
                COUNT(*) as total_count,
                COUNT(CASE WHEN ' || col_name || ' IS NULL THEN 1 END) as null_count,
                ROUND((null_count / total_count) * 100, 2) as null_percentage,
                COUNT(DISTINCT ' || col_name || ') as distinct_count,
                ROUND((distinct_count / total_count) * 100, 2) as distinct_percentage,
                MIN(' || col_name || ') as min_value,
                MAX(' || col_name || ') as max_value,
                NULL as avg_value,
                NULL as std_dev,
                MIN(LENGTH(' || col_name || ')) as min_length,
                MAX(LENGTH(' || col_name || ')) as max_length,
                AVG(LENGTH(' || col_name || ')) as avg_length
                FROM ' || table_name;
                
        ELSIF col_type IN ('DATE', 'TIMESTAMP', 'TIMESTAMP_NTZ', 'TIMESTAMP_LTZ', 'TIMESTAMP_TZ') THEN
            profile_sql := 'SELECT 
                COUNT(*) as total_count,
                COUNT(CASE WHEN ' || col_name || ' IS NULL THEN 1 END) as null_count,
                ROUND((null_count / total_count) * 100, 2) as null_percentage,
                COUNT(DISTINCT ' || col_name || ') as distinct_count,
                ROUND((distinct_count / total_count) * 100, 2) as distinct_percentage,
                MIN(' || col_name || ') as min_value,
                MAX(' || col_name || ') as max_value,
                NULL as avg_value,
                NULL as std_dev,
                NULL as min_length,
                NULL as max_length,
                NULL as avg_length
                FROM ' || table_name;
        ELSE
            -- Generic profiling for other data types
            profile_sql := 'SELECT 
                COUNT(*) as total_count,
                COUNT(CASE WHEN ' || col_name || ' IS NULL THEN 1 END) as null_count,
                ROUND((null_count / total_count) * 100, 2) as null_percentage,
                COUNT(DISTINCT ' || col_name || ') as distinct_count,
                ROUND((distinct_count / total_count) * 100, 2) as distinct_percentage,
                NULL as min_value,
                NULL as max_value,
                NULL as avg_value,
                NULL as std_dev,
                NULL as min_length,
                NULL as max_length,
                NULL as avg_length
                FROM ' || table_name;
        END IF;
        
        -- Execute the profiling query
        EXECUTE IMMEDIATE profile_sql;
        
        -- Get results from last query
        OPEN result_cursor;
        FETCH result_cursor INTO total_count, null_count, null_percentage, distinct_count, 
                                distinct_percentage, min_value, max_value, avg_value, std_dev,
                                min_length, max_length, avg_length;
        CLOSE result_cursor;
        
        -- Insert profile results
        INSERT INTO data_profile_results (
            table_name, column_name, data_type, total_count, null_count, null_percentage,
            distinct_count, distinct_percentage, min_value, max_value, avg_value, std_dev,
            min_length, max_length, avg_length
        ) VALUES (
            table_name, col_name, col_type, total_count, null_count, null_percentage,
            distinct_count, distinct_percentage, min_value, max_value, avg_value, std_dev,
            min_length, max_length, avg_length
        );
    END FOR;
    
    RETURN 'Table profiling completed for ' || table_name;
END;
$$;

-- Function to get data quality score for a table
CREATE OR REPLACE FUNCTION get_data_quality_score(table_name STRING)
RETURNS TABLE (
    table_name STRING,
    overall_quality_score NUMBER,
    completeness_score NUMBER,
    uniqueness_score NUMBER,
    validity_score NUMBER,
    recommendations VARIANT
)
AS
$$
WITH quality_metrics AS (
    SELECT 
        table_name,
        AVG(100 - null_percentage) as completeness_score,
        AVG(CASE WHEN distinct_percentage > 95 THEN 100 
                 WHEN distinct_percentage > 80 THEN 80
                 WHEN distinct_percentage > 50 THEN 60
                 ELSE 40 END) as uniqueness_score,
        AVG(CASE WHEN data_type IN ('NUMBER', 'VARCHAR', 'DATE', 'TIMESTAMP') AND null_percentage < 20 THEN 100
                 WHEN null_percentage < 50 THEN 70
                 ELSE 30 END) as validity_score
    FROM data_profile_results
    WHERE table_name = table_name
    GROUP BY table_name
),
recommendations AS (
    SELECT 
        table_name,
        ARRAY_CONSTRUCT_COMPACT(
            CASE WHEN AVG(null_percentage) > 20 THEN 'High null percentage detected - consider data validation rules' END,
            CASE WHEN AVG(distinct_percentage) < 50 THEN 'Low uniqueness detected - investigate potential duplicates' END,
            CASE WHEN COUNT(*) < 5 THEN 'Limited columns profiled - ensure all important columns are included' END
        ) as recommendations
    FROM data_profile_results
    WHERE table_name = table_name
    GROUP BY table_name
)
SELECT 
    qm.table_name,
    ROUND((completeness_score + uniqueness_score + validity_score) / 3, 2) as overall_quality_score,
    ROUND(completeness_score, 2) as completeness_score,
    ROUND(uniqueness_score, 2) as uniqueness_score,
    ROUND(validity_score, 2) as validity_score,
    r.recommendations
FROM quality_metrics qm
JOIN recommendations r ON qm.table_name = r.table_name
$$;

-- View to display latest profiling summary
CREATE OR REPLACE VIEW data_profile_summary AS
SELECT 
    table_name,
    COUNT(*) as columns_profiled,
    AVG(null_percentage) as avg_null_percentage,
    AVG(distinct_percentage) as avg_distinct_percentage,
    MIN(timestamp) as profile_date,
    SUM(CASE WHEN null_percentage > 50 THEN 1 ELSE 0 END) as high_null_columns,
    SUM(CASE WHEN distinct_percentage < 10 THEN 1 ELSE 0 END) as low_distinct_columns
FROM data_profile_results
WHERE timestamp = (SELECT MAX(timestamp) FROM data_profile_results)
GROUP BY table_name
ORDER BY avg_null_percentage DESC;

-- Procedure to profile all tables in current database
CREATE OR REPLACE PROCEDURE profile_all_tables()
RETURNS STRING
LANGUAGE SQL
AS
$$
DECLARE
    table_cursor CURSOR FOR 
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = CURRENT_SCHEMA()
          AND table_type = 'BASE TABLE';
    
    table_name STRING;
    processed_count NUMBER DEFAULT 0;
BEGIN
    FOR record IN table_cursor DO
        table_name := record.table_name;
        CALL profile_table(table_name);
        processed_count := processed_count + 1;
    END FOR;
    RETURN 'Profiling completed for ' || processed_count || ' tables';
END;
$$;