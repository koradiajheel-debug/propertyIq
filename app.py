import streamlit as st
import pandas as pd
import numpy as np

st.set_page_config(page_title='PropertyIQ Energy Dashboard', layout='centered')

st.title('🏡 PropertyIQ – Home Energy Dashboard')

# Sample placeholder data
@st.cache_data
def load_sample_data():
    dates = pd.date_range(start='2023-01-01', periods=12, freq='MS')
    consumption = np.random.uniform(200, 500, size=12)
    df = pd.DataFrame({"Month": dates.strftime('%b %Y'), "kWh": consumption.round(1)})
    return df

df = load_sample_data()

st.subheader('Monthly Energy Consumption (kWh)')
st.line_chart(df.set_index('Month')['kWh'])

st.subheader('Data Table')
st.dataframe(df)

st.markdown('---')
st.caption('*This is a demo. Replace the sample data with real property‑wise energy usage.*')
