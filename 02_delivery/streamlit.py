# Import Python packages

import streamlit as st
import altair as alt
from snowflake.snowpark.context import get_active_session
import pandas as pd
from snowflake.snowpark.functions import col

# Get the current credentials
session = get_active_session()

st.title('Weather and Sales Trends for Hamburg, Germany')

# Load the view and create a pandas dataframe 
hamburg_weather = session.table("tasty_bytes.harmonized.weather_hamburg").select(
    col("DATE"),
    col("DAILY_SALES"),
    col("AVG_TEMPERATURE_FAHRENHEIT"),
    col("AVG_PRECIPITATION_INCHES"),
    col("MAX_WIND_SPEED_100M_MPH")
).to_pandas()

# Create a copy of the dataframe with sales in millions
hamburg_weather['DAILY_SALES_MILLIONS'] = hamburg_weather['DAILY_SALES'] / 1000000

# Prepare data for sales chart (primary Y-axis)
sales_df = pd.DataFrame({
    'DATE': hamburg_weather['DATE'],
    'Measure': 'Daily Sales ($ millions)',
    'Value': hamburg_weather['DAILY_SALES_MILLIONS']
})

# Prepare data for weather metrics (secondary Y-axis) using melt for proper reshaping
weather_df = pd.melt(
    hamburg_weather,
    id_vars=['DATE'],
    value_vars=['AVG_TEMPERATURE_FAHRENHEIT', 'AVG_PRECIPITATION_INCHES', 'MAX_WIND_SPEED_100M_MPH'],
    var_name='Measure',
    value_name='Value'
)

# Map column names to desired legend titles
weather_df['Measure'] = weather_df['Measure'].replace({
    'AVG_TEMPERATURE_FAHRENHEIT': 'Avg Temperature (°F)',
    'AVG_PRECIPITATION_INCHES': 'Avg Precipitation (in)',
    'MAX_WIND_SPEED_100M_MPH': 'Max Wind Speed (mph)'
})

# Combine the dataframes
combined_df = pd.concat([sales_df, weather_df], ignore_index=True)

# Create the base chart
base = alt.Chart(combined_df).encode(
    x=alt.X('DATE:T', title='Date')
).properties(
    width=700,
    height=400,
    title='Daily Sales, Temperature, Precipitation, and Wind Speed in Hamburg'
)

# Create the sales chart with its own y-axis
sales_chart = base.transform_filter(
    alt.datum.Measure == 'Daily Sales ($ millions)'
).mark_line(color='#29B5E8', point=True).encode(
    y=alt.Y('Value:Q', title='Daily Sales ($ millions)', axis=alt.Axis(titleColor='#29B5E8')),
    tooltip=['DATE:T', 'Measure:N', 'Value:Q']
)

# Create the weather metrics chart with its own y-axis
weather_chart = base.transform_filter(
    alt.datum.Measure != 'Daily Sales ($ millions)'
).mark_line(point=True).encode(
    y=alt.Y('Value:Q', title='Weather Metrics', axis=alt.Axis(titleColor='#FF6F61')),
    color=alt.Color('Measure:N', 
                   scale=alt.Scale(range=['#FF6F61', '#0072CE', '#FFC300']),
                   legend=alt.Legend(title='Weather Metrics')),
    tooltip=['DATE:T', 'Measure:N', 'Value:Q']
)

# Layer the charts together
chart = alt.layer(sales_chart, weather_chart).resolve_scale(
    y='independent'
).configure_title(
    fontSize=20,
    font='Arial'
).configure_axis(
    grid=True
).configure_view(
    strokeWidth=0
).interactive()

# Display the chart in the Streamlit app
st.altair_chart(chart, use_container_width=True)
