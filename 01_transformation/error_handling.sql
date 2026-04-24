-- These procedures provide comprehensive error handling and logging capabilities

-- Create logging table for pipeline execution tracking
CREATE OR REPLACE TABLE pipeline_logs (
    log_id STRING DEFAULT UUID_STRING(),
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
    pipeline_name STRING,
    step_name STRING,
    log_level STRING,
    message STRING,
    error_code NUMBER,
    execution_time_ms NUMBER,
    records_processed NUMBER
);

-- Procedure to log pipeline events
CREATE OR REPLACE PROCEDURE log_pipeline_event(
    pipeline_name STRING,
    step_name STRING,
    log_level STRING,
    message STRING,
    error_code NUMBER DEFAULT NULL,
    execution_time_ms NUMBER DEFAULT NULL,
    records_processed NUMBER DEFAULT NULL
)
RETURNS STRING
LANGUAGE SQL
AS
$$
BEGIN
    INSERT INTO pipeline_logs (
        pipeline_name, step_name, log_level, message, 
        error_code, execution_time_ms, records_processed
    )
    VALUES (
        pipeline_name, step_name, log_level, message,
        error_code, execution_time_ms, records_processed
    );
    
    RETURN 'Event logged successfully';
EXCEPTION
    WHEN OTHER THEN
        RETURN 'Failed to log event: ' || SQLERRM;
END;
$$;

-- Procedure with built-in error handling for data transformations
CREATE OR REPLACE PROCEDURE safe_transform_data(
    source_table STRING,
    target_table STRING,
    transformation_sql STRING
)
RETURNS STRING
LANGUAGE SQL
AS
$$
DECLARE
    start_time TIMESTAMP;
    end_time TIMESTAMP;
    execution_time NUMBER;
    records_affected NUMBER;
    error_message STRING;
BEGIN
    start_time := CURRENT_TIMESTAMP();
    
    -- Log start of transformation
    CALL log_pipeline_event(
        'DATA_TRANSFORMATION',
        'TRANSFORM_' || target_table,
        'INFO',
        'Starting transformation from ' || source_table || ' to ' || target_table
    );
    
    -- Execute the transformation
    EXECUTE IMMEDIATE transformation_sql;
    GET DIAGNOSTICS records_affected = ROW_COUNT;
    
    end_time := CURRENT_TIMESTAMP();
    execution_time := DATEDIFF('millisecond', start_time, end_time);
    
    -- Log successful completion
    CALL log_pipeline_event(
        'DATA_TRANSFORMATION',
        'TRANSFORM_' || target_table,
        'SUCCESS',
        'Transformation completed successfully',
        NULL,
        execution_time,
        records_affected
    );
    
    RETURN 'Transformation completed. Records affected: ' || records_affected;
    
EXCEPTION
    WHEN OTHER THEN
        error_message := SQLERRM;
        end_time := CURRENT_TIMESTAMP();
        execution_time := DATEDIFF('millisecond', start_time, end_time);
        
        -- Log error
        CALL log_pipeline_event(
            'DATA_TRANSFORMATION',
            'TRANSFORM_' || target_table,
            'ERROR',
            'Transformation failed: ' || error_message,
            SQLCODE,
            execution_time,
            0
        );
        
        RETURN 'Transformation failed: ' || error_message;
END;
$$;

-- Procedure to validate prerequisites before pipeline execution
CREATE OR REPLACE PROCEDURE validate_pipeline_prerequisites(
    required_tables ARRAY,
    required_schemas ARRAY
)
RETURNS STRING
LANGUAGE SQL
AS
$$
DECLARE
    table_name STRING;
    schema_name STRING;
    validation_errors ARRAY DEFAULT ARRAY_CONSTRUCT();
    error_count NUMBER DEFAULT 0;
BEGIN
    -- Check if required tables exist
    FOR i IN 0 TO ARRAY_SIZE(required_tables) - 1 DO
        table_name := required_tables[i]::STRING;
        
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.tables 
            WHERE table_name = UPPER(table_name)
        ) THEN
            validation_errors := ARRAY_APPEND(validation_errors, 'Missing table: ' || table_name);
            error_count := error_count + 1;
        END IF;
    END FOR;
    
    -- Check if required schemas exist
    FOR i IN 0 TO ARRAY_SIZE(required_schemas) - 1 DO
        schema_name := required_schemas[i]::STRING;
        
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.schemata 
            WHERE schema_name = UPPER(schema_name)
        ) THEN
            validation_errors := ARRAY_APPEND(validation_errors, 'Missing schema: ' || schema_name);
            error_count := error_count + 1;
        END IF;
    END FOR;
    
    IF error_count > 0 THEN
        CALL log_pipeline_event(
            'PREREQUISITE_VALIDATION',
            'VALIDATE_PREREQUISITES',
            'ERROR',
            'Validation failed: ' || ARRAY_TO_STRING(validation_errors, ', '),
            -1
        );
        RETURN 'Validation failed with ' || error_count || ' errors: ' || ARRAY_TO_STRING(validation_errors, ', ');
    ELSE
        CALL log_pipeline_event(
            'PREREQUISITE_VALIDATION',
            'VALIDATE_PREREQUISITES',
            'SUCCESS',
            'All prerequisites validated successfully'
        );
        RETURN 'All prerequisites validated successfully';
    END IF;
END;
$$;

-- Function to get pipeline execution summary
CREATE OR REPLACE FUNCTION get_pipeline_summary(pipeline_name STRING, days_back NUMBER DEFAULT 7)
RETURNS TABLE (
    pipeline_name STRING,
    total_executions NUMBER,
    successful_executions NUMBER,
    failed_executions NUMBER,
    success_rate NUMBER,
    avg_execution_time_ms NUMBER,
    total_records_processed NUMBER
)
AS
$$
SELECT 
    pipeline_name,
    COUNT(*) as total_executions,
    SUM(CASE WHEN log_level = 'SUCCESS' THEN 1 ELSE 0 END) as successful_executions,
    SUM(CASE WHEN log_level = 'ERROR' THEN 1 ELSE 0 END) as failed_executions,
    ROUND((successful_executions / total_executions) * 100, 2) as success_rate,
    AVG(execution_time_ms) as avg_execution_time_ms,
    SUM(records_processed) as total_records_processed
FROM pipeline_logs 
WHERE pipeline_name = pipeline_name
    AND timestamp >= DATEADD('day', -days_back, CURRENT_TIMESTAMP())
GROUP BY pipeline_name
$$;