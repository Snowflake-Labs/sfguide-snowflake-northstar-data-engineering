# Enhanced Streamlit Application with Interactive Features

import streamlit as st
import altair as alt
from snowflake.snowpark.context import get_active_session
import pandas as pd
from snowflake.snowpark.functions import col
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta

# Get the current credentials
session = get_active_session()

st.title('🌤️ Weather and Sales Analytics Dashboard')
st.markdown('### Hamburg, Germany - Interactive Data Exploration')

# Add sidebar for filters
st.sidebar.header('📊 Dashboard Filters')

# Load the view and create a pandas dataframe 
hamburg_weather = session.table("tasty_bytes.harmonized.weather_hamburg").select(
    col("DATE"),
    col("DAILY_SALES"),
    col("AVG_TEMPERATURE_FAHRENHEIT"),
    col("AVG_PRECIPITATION_INCHES"),
    col("MAX_WIND_SPEED_100M_MPH")
).to_pandas()

# Date range filter
min_date = hamburg_weather['DATE'].min()
max_date = hamburg_weather['DATE'].max()

start_date = st.sidebar.date_input(
    'Start Date',
    value=min_date,
    min_value=min_date,
    max_value=max_date
)

end_date = st.sidebar.date_input(
    'End Date',
    value=max_date,
    min_value=min_date,
    max_value=max_date
)

# Filter data based on date selection
hamburg_weather_filtered = hamburg_weather[
    (hamburg_weather['DATE'] >= pd.to_datetime(start_date)) & 
    (hamburg_weather['DATE'] <= pd.to_datetime(end_date))
]

# Weather metric selector
weather_metrics = {
    'Temperature (°F)': 'AVG_TEMPERATURE_FAHRENHEIT',
    'Precipitation (in)': 'AVG_PRECIPITATION_INCHES', 
    'Wind Speed (mph)': 'MAX_WIND_SPEED_100M_MPH'
}

selected_metrics = st.sidebar.multiselect(
    'Select Weather Metrics',
    options=list(weather_metrics.keys()),
    default=list(weather_metrics.keys())
)

# Display key metrics
col1, col2, col3, col4 = st.columns(4)

with col1:
    avg_sales = hamburg_weather_filtered['DAILY_SALES'].mean()
    st.metric(
        label='Avg Daily Sales',
        value=f'${avg_sales/1000000:.1f}M'
    )

with col2:
    avg_temp = hamburg_weather_filtered['AVG_TEMPERATURE_FAHRENHEIT'].mean()
    st.metric(
        label='Avg Temperature',
        value=f'{avg_temp:.1f}°F'
    )

with col3:
    total_precipitation = hamburg_weather_filtered['AVG_PRECIPITATION_INCHES'].sum()
    st.metric(
        label='Total Precipitation',
        value=f'{total_precipitation:.1f} in'
    )

with col4:
    max_wind = hamburg_weather_filtered['MAX_WIND_SPEED_100M_MPH'].max()
    st.metric(
        label='Max Wind Speed',
        value=f'{max_wind:.1f} mph'
    )

# Create tabs for different visualizations
tab1, tab2, tab3 = st.tabs(['📈 Time Series', '📊 Correlations', '🔍 Detailed Analysis'])

with tab1:
    st.subheader('Sales and Weather Trends Over Time')
    
    # Create a copy of the dataframe with sales in millions
    hamburg_weather_filtered['DAILY_SALES_MILLIONS'] = hamburg_weather_filtered['DAILY_SALES'] / 1000000

    # Prepare data for sales chart (primary Y-axis)
    sales_df = pd.DataFrame({
        'DATE': hamburg_weather_filtered['DATE'],
        'Measure': 'Daily Sales ($ millions)',
        'Value': hamburg_weather_filtered['DAILY_SALES_MILLIONS']
    })

    # Prepare data for weather metrics (secondary Y-axis) using melt for proper reshaping
    weather_df = pd.melt(
        hamburg_weather_filtered,
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

with tab2:
    st.subheader('Weather Impact on Sales')
    
    # Correlation analysis
    correlation_data = hamburg_weather_filtered[['DAILY_SALES', 'AVG_TEMPERATURE_FAHRENHEIT', 'AVG_PRECIPITATION_INCHES', 'MAX_WIND_SPEED_100M_MPH']].corr()
    
    # Create correlation heatmap using plotly
    fig_corr = px.imshow(
        correlation_data,
        text_auto=True,
        aspect='auto',
        color_continuous_scale='RdBu',
        title='Correlation Matrix: Sales vs Weather Metrics'
    )
    st.plotly_chart(fig_corr, use_container_width=True)
    
    # Scatter plots for each weather metric vs sales
    for metric_name, metric_col in weather_metrics.items():
        if metric_name.replace(' (°F)', '').replace(' (in)', '').replace(' (mph)', '') in [m.replace(' (°F)', '').replace(' (in)', '').replace(' (mph)', '') for m in selected_metrics]:
            fig_scatter = px.scatter(
                hamburg_weather_filtered,
                x=metric_col,
                y='DAILY_SALES',
                title=f'Sales vs {metric_name}',
                labels={'DAILY_SALES': 'Daily Sales ($)', metric_col: metric_name},
                trendline='ols'
            )
            fig_scatter.update_traces(marker=dict(color='lightblue', size=8))
            st.plotly_chart(fig_scatter, use_container_width=True)

with tab3:
    st.subheader('Detailed Data Analysis')
    
    # Sales distribution
    col1, col2 = st.columns(2)
    
    with col1:
        st.write('**Sales Distribution**')
        fig_hist = px.histogram(
            hamburg_weather_filtered,
            x='DAILY_SALES',
            nbins=20,
            title='Distribution of Daily Sales',
            labels={'DAILY_SALES': 'Daily Sales ($)'}
        )
        st.plotly_chart(fig_hist, use_container_width=True)
    
    with col2:
        st.write('**Temperature Distribution**')
        fig_temp_hist = px.histogram(
            hamburg_weather_filtered,
            x='AVG_TEMPERATURE_FAHRENHEIT',
            nbins=20,
            title='Distribution of Daily Temperature',
            labels={'AVG_TEMPERATURE_FAHRENHEIT': 'Temperature (°F)'}
        )
        st.plotly_chart(fig_temp_hist, use_container_width=True)
    
    # Data table with filtering options
    st.subheader('Raw Data Table')
    
    # Allow users to filter by sales range
    min_sales, max_sales = st.slider(
        'Filter by Sales Range ($M)',
        min_value=float(hamburg_weather_filtered['DAILY_SALES'].min()/1000000),
        max_value=float(hamburg_weather_filtered['DAILY_SALES'].max()/1000000),
        value=(float(hamburg_weather_filtered['DAILY_SALES'].min()/1000000), 
               float(hamburg_weather_filtered['DAILY_SALES'].max()/1000000)),
        step=0.1
    )
    
    # Filter data based on sales range
    filtered_table_data = hamburg_weather_filtered[
        (hamburg_weather_filtered['DAILY_SALES']/1000000 >= min_sales) & 
        (hamburg_weather_filtered['DAILY_SALES']/1000000 <= max_sales)
    ]
    
    # Display filtered data
    st.dataframe(
        filtered_table_data.style.format({
            'DAILY_SALES': '${:,.0f}',
            'AVG_TEMPERATURE_FAHRENHEIT': '{:.1f}°F',
            'AVG_PRECIPITATION_INCHES': '{:.2f}"',
            'MAX_WIND_SPEED_100M_MPH': '{:.1f} mph'
        }),
        use_container_width=True
    )
    
    # Download button for filtered data
    csv = filtered_table_data.to_csv(index=False)
    st.download_button(
        label='📥 Download Filtered Data as CSV',
        data=csv,
        file_name=f'hamburg_weather_sales_{start_date}_{end_date}.csv',
        mime='text/csv'
    )