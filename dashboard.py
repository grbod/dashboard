import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import time
import os
from typing import Optional

from data_service import FreightDataService

# Page configuration
st.set_page_config(
    page_title="FreightView Dashboard",
    page_icon="🚛",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        text-align: center;
        padding: 1rem;
        background: linear-gradient(90deg, #1f4e79, #2e6da4);
        color: white;
        border-radius: 10px;
        margin-bottom: 2rem;
    }
    
    .metric-card {
        background: white;
        padding: 1rem;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        text-align: center;
    }
    
    .status-indicator {
        width: 12px;
        height: 12px;
        border-radius: 50%;
        display: inline-block;
        margin-right: 5px;
    }
    
    .status-connected { background-color: #28a745; }
    .status-error { background-color: #dc3545; }
    .status-warning { background-color: #ffc107; }
    
    .data-table {
        font-size: 0.9rem;
    }
    
    .refresh-info {
        background-color: #f8f9fa;
        padding: 0.5rem;
        border-radius: 5px;
        margin-bottom: 1rem;
        font-size: 0.85rem;
        color: #6c757d;
    }
</style>
""", unsafe_allow_html=True)

def get_config():
    """Get configuration from environment or config file."""
    try:
        # Try to import from existing config file first
        import freightviewslack.config as config
        return config.CLIENT_ID, config.CLIENT_SECRET
    except ImportError:
        # Fall back to environment variables
        client_id = os.getenv('FREIGHTVIEW_CLIENT_ID')
        client_secret = os.getenv('FREIGHTVIEW_CLIENT_SECRET')
        
        if not client_id or not client_secret:
            st.error("⚠️ Missing configuration! Please set FREIGHTVIEW_CLIENT_ID and FREIGHTVIEW_CLIENT_SECRET environment variables or ensure config.py exists.")
            st.stop()
        
        return client_id, client_secret

def initialize_session_state():
    """Initialize session state variables."""
    if 'last_update' not in st.session_state:
        st.session_state.last_update = None
    if 'data_loaded' not in st.session_state:
        st.session_state.data_loaded = False
    if 'error_message' not in st.session_state:
        st.session_state.error_message = None
    if 'auto_refresh_enabled' not in st.session_state:
        st.session_state.auto_refresh_enabled = True

def create_metrics_cards(metrics):
    """Create metric cards for the dashboard."""
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            label="🚛 Total Shipments",
            value=metrics['total_shipments'],
            delta=f"In: {metrics['inbound_count']} | Out: {metrics['outbound_count']}"
        )
    
    with col2:
        st.metric(
            label="💰 Avg Cost/lb",
            value=f"${metrics['avg_cost_per_lb']:.2f}",
            delta=None
        )
    
    with col3:
        st.metric(
            label="📦 Total Weight",
            value=f"{metrics['total_weight']:,} lbs",
            delta=None
        )
    
    with col4:
        st.metric(
            label="💵 Total Cost",
            value=f"${metrics['total_cost']:,.2f}",
            delta=None
        )

def create_shipment_charts(inbound_df, outbound_df):
    """Create charts for shipment analysis."""
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📊 Shipment Distribution")
        
        # Pie chart of inbound vs outbound
        if not inbound_df.empty or not outbound_df.empty:
            shipment_counts = pd.DataFrame({
                'Type': ['Inbound', 'Outbound'],
                'Count': [len(inbound_df), len(outbound_df)]
            })
            
            fig = px.pie(
                shipment_counts, 
                values='Count', 
                names='Type',
                color_discrete_sequence=['#FF6B6B', '#4ECDC4']
            )
            fig.update_traces(textposition='inside', textinfo='percent+label')
            st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.subheader("💰 Cost Analysis")
        
        # Cost per carrier analysis
        all_data = []
        if not inbound_df.empty:
            all_data.extend(inbound_df[['Carrier Name', 'Cost per lb']].dropna().values.tolist())
        if not outbound_df.empty:
            all_data.extend(outbound_df[['Carrier Name', 'Cost per lb']].dropna().values.tolist())
        
        if all_data:
            cost_df = pd.DataFrame(all_data, columns=['Carrier', 'Cost_per_lb'])
            carrier_costs = cost_df.groupby('Carrier')['Cost_per_lb'].mean().reset_index()
            carrier_costs = carrier_costs.sort_values('Cost_per_lb', ascending=False).head(10)
            
            fig = px.bar(
                carrier_costs,
                x='Cost_per_lb',
                y='Carrier',
                orientation='h',
                color='Cost_per_lb',
                color_continuous_scale='RdYlBu_r'
            )
            fig.update_layout(showlegend=False)
            st.plotly_chart(fig, use_container_width=True)

def create_data_table(df, title):
    """Create a formatted data table."""
    if df.empty:
        st.info(f"No {title.lower()} data available")
        return
    
    st.subheader(f"📋 {title}")
    
    # Add filters
    col1, col2, col3 = st.columns(3)
    
    with col1:
        carriers = ['All'] + sorted(df['Carrier Name'].dropna().unique().tolist())
        selected_carrier = st.selectbox(f"Filter by Carrier ({title})", carriers, key=f"carrier_{title}")
    
    with col2:
        if 'Status' in df.columns:
            statuses = ['All'] + sorted(df['Status'].dropna().unique().tolist())
            selected_status = st.selectbox(f"Filter by Status ({title})", statuses, key=f"status_{title}")
        else:
            selected_status = 'All'
    
    with col3:
        # Search box
        search_term = st.text_input(f"Search {title}", key=f"search_{title}")
    
    # Apply filters
    filtered_df = df.copy()
    
    if selected_carrier != 'All':
        filtered_df = filtered_df[filtered_df['Carrier Name'] == selected_carrier]
    
    if selected_status != 'All' and 'Status' in filtered_df.columns:
        filtered_df = filtered_df[filtered_df['Status'] == selected_status]
    
    if search_term:
        # Search across all string columns
        mask = filtered_df.astype(str).apply(lambda x: x.str.contains(search_term, case=False, na=False)).any(axis=1)
        filtered_df = filtered_df[mask]
    
    # Display table with formatting
    if not filtered_df.empty:
        # Format numeric columns
        display_df = filtered_df.copy()
        if 'Price' in display_df.columns:
            display_df['Price'] = display_df['Price'].apply(lambda x: f"${x:,.2f}" if pd.notna(x) else "N/A")
        if 'Cost per lb' in display_df.columns:
            display_df['Cost per lb'] = display_df['Cost per lb'].apply(lambda x: f"${x:.2f}" if pd.notna(x) else "N/A")
        if 'Weight' in display_df.columns:
            display_df['Weight'] = display_df['Weight'].apply(lambda x: f"{x:,}" if pd.notna(x) else "N/A")
        
        st.dataframe(display_df, use_container_width=True, height=400)
        
        # Export button
        csv = filtered_df.to_csv(index=False)
        st.download_button(
            label=f"📥 Download {title} Data (CSV)",
            data=csv,
            file_name=f"{title.lower().replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv"
        )
    else:
        st.info("No data matches the current filters")

def main():
    # Initialize session state
    initialize_session_state()
    
    # Header
    st.markdown("""
    <div class="main-header">
        <h1>🚛 FreightView Dashboard</h1>
        <p>Real-time freight tracking and analytics</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Get configuration
    try:
        client_id, client_secret = get_config()
        data_service = FreightDataService(client_id, client_secret)
    except Exception as e:
        st.error(f"Configuration error: {str(e)}")
        st.stop()
    
    # Control panel
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        if st.session_state.last_update:
            next_update = st.session_state.last_update + timedelta(minutes=15)
            time_until_next = next_update - datetime.now()
            if time_until_next.total_seconds() > 0:
                minutes_left = int(time_until_next.total_seconds() / 60)
                st.markdown(f"""
                <div class="refresh-info">
                    ⏰ Next auto-refresh in: {minutes_left} minutes | 
                    Last updated: {st.session_state.last_update.strftime('%Y-%m-%d %H:%M:%S')}
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown("""
                <div class="refresh-info">
                    🔄 Auto-refresh due - refreshing...
                </div>
                """, unsafe_allow_html=True)
    
    with col2:
        if st.button("🔄 Refresh Now", type="primary"):
            st.session_state.last_update = None  # Force refresh
            st.rerun()
    
    with col3:
        auto_refresh = st.toggle("🔄 Auto-refresh", value=st.session_state.auto_refresh_enabled)
        st.session_state.auto_refresh_enabled = auto_refresh
    
    # Check if we need to refresh data
    should_refresh = (
        st.session_state.last_update is None or
        (st.session_state.auto_refresh_enabled and 
         datetime.now() - st.session_state.last_update > timedelta(minutes=15))
    )
    
    if should_refresh:
        with st.spinner("🔄 Loading freight data..."):
            try:
                # Fetch data
                model = data_service.fetch_shipments("picked-up")
                
                if model:
                    # Process data
                    inbound_data = data_service.process_inbound_data(model)
                    outbound_data = data_service.process_outbound_data(model)
                    metrics = data_service.get_summary_metrics(inbound_data, outbound_data)
                    
                    # Store in session state
                    st.session_state.inbound_data = inbound_data
                    st.session_state.outbound_data = outbound_data
                    st.session_state.metrics = metrics
                    st.session_state.last_update = datetime.now()
                    st.session_state.data_loaded = True
                    st.session_state.error_message = None
                    
                    st.success("✅ Data loaded successfully!")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.session_state.error_message = "Failed to fetch data from FreightView API"
                    st.session_state.data_loaded = False
                    
            except Exception as e:
                st.session_state.error_message = f"Error loading data: {str(e)}"
                st.session_state.data_loaded = False
    
    # Display connection status
    if st.session_state.data_loaded and not st.session_state.error_message:
        st.markdown('<span class="status-indicator status-connected"></span> **Connected to FreightView API**', unsafe_allow_html=True)
    elif st.session_state.error_message:
        st.markdown('<span class="status-indicator status-error"></span> **API Connection Error**', unsafe_allow_html=True)
        st.error(st.session_state.error_message)
    else:
        st.markdown('<span class="status-indicator status-warning"></span> **No Data Loaded**', unsafe_allow_html=True)
    
    # Display dashboard content
    if st.session_state.data_loaded:
        # Metrics cards
        create_metrics_cards(st.session_state.metrics)
        
        st.markdown("---")
        
        # Convert data to DataFrames
        inbound_df = pd.DataFrame(st.session_state.inbound_data)
        outbound_df = pd.DataFrame(st.session_state.outbound_data)
        
        # Charts section
        if not inbound_df.empty or not outbound_df.empty:
            st.subheader("📈 Analytics")
            create_shipment_charts(inbound_df, outbound_df)
            st.markdown("---")
        
        # Data tables in tabs
        tab1, tab2 = st.tabs(["📥 Inbound Freight", "📤 Outbound Freight"])
        
        with tab1:
            create_data_table(inbound_df, "Inbound Freight")
        
        with tab2:
            create_data_table(outbound_df, "Outbound Freight")
    
    else:
        st.info("👆 Click 'Refresh Now' to load freight data")
    
    # Auto-refresh logic
    if st.session_state.auto_refresh_enabled and st.session_state.data_loaded:
        time.sleep(60)  # Check every minute
        st.rerun()

if __name__ == "__main__":
    main()