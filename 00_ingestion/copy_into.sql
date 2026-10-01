-- Create a CSV file format here:

-- Specify the file format below:
CREATE OR REPLACE STAGE tasty_bytes.public.s3load
url = 's3://sfquickstarts/tasty-bytes-builder-education/';

-- country table build
CREATE OR REPLACE TABLE tasty_bytes.raw_pos.country
(
   country_id NUMBER(18,0),
   country VARCHAR(16777216),
   iso_currency VARCHAR(3),
   iso_country VARCHAR(2),
   city_id NUMBER(19,0),
   city VARCHAR(16777216),
   city_population VARCHAR(16777216)
);

-- Use the COPY INTO command to load data into the country table:
