
import streamlit as st
import pandas as pd
import plotly.express as px
from test_data import get_mock_api_responses
from data_service import FreightDataService
from freightviewslack.pydatamodel import Model

st.set_page_config(page_title="FreightView Dashboard (Test Mode)", page_icon="🚛", layout="wide")

st.title("🚛 FreightView Dashboard - Test Mode")
st.info("Running with mock data for testing purposes")

# Load mock data
mock_responses = get_mock_api_responses()
model = Model.model_validate(mock_responses["shipments"])

# Process data
service = FreightDataService("test_id", "test_secret")
inbound_data = service.process_inbound_data(model)
outbound_data = service.process_outbound_data(model)
metrics = service.get_summary_metrics(inbound_data, outbound_data)

# Display metrics
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("🚛 Total Shipments", metrics['total_shipments'])

with col2:
    st.metric("💰 Avg Cost/lb", f"${metrics['avg_cost_per_lb']:.2f}")

with col3:
    st.metric("📦 Total Weight", f"{metrics['total_weight']:,} lbs")

with col4:
    st.metric("💵 Total Cost", f"${metrics['total_cost']:,.2f}")

# Display data tables
st.subheader("📊 Sample Data")

tab1, tab2 = st.tabs(["📥 Inbound Freight", "📤 Outbound Freight"])

with tab1:
    if inbound_data:
        inbound_df = pd.DataFrame(inbound_data)
        st.dataframe(inbound_df, use_container_width=True)
    else:
        st.info("No inbound data available")

with tab2:
    if outbound_data:
        outbound_df = pd.DataFrame(outbound_data)
        st.dataframe(outbound_df, use_container_width=True)
    else:
        st.info("No outbound data available")

# Simple chart
if inbound_data or outbound_data:
    st.subheader("📈 Shipment Distribution")
    chart_data = pd.DataFrame({
        'Type': ['Inbound', 'Outbound'],
        'Count': [len(inbound_data), len(outbound_data)]
    })
    
    fig = px.pie(chart_data, values='Count', names='Type')
    st.plotly_chart(fig, use_container_width=True)

st.success("✅ Mock dashboard running successfully!")
