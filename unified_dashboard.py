import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import time
import os
from typing import Optional

from unified_data_service import UnifiedDataService

# Page configuration
st.set_page_config(
    page_title="Unified Shipping Dashboard",
    page_icon="🚢",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS with sage + ming + indigo dye color scheme
st.markdown("""
<style>
    .main-header {
        text-align: center;
        padding: 1.5rem;
        background: linear-gradient(135deg, #033f63, #28666e);
        color: #fedc97;
        border-radius: 12px;
        margin-bottom: 2rem;
        box-shadow: 0 4px 6px rgba(3, 63, 99, 0.15);
    }
    
    .service-section {
        border: 1.5px solid #7c9885;
        border-radius: 12px;
        padding: 1rem;
        margin: 1rem 0;
        background: #f5f7f3;
    }
    
    .freightview-section { border-left: 4px solid #033f63; }
    .shipstation-section { border-left: 4px solid #28666e; }
    
    .metric-card {
        background: linear-gradient(to bottom, #f5f7f3, #e8ede5);
        padding: 1rem;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(124, 152, 133, 0.15);
        text-align: center;
        border: 1px solid #b5b682;
    }
    
    .status-indicator {
        width: 12px;
        height: 12px;
        border-radius: 50%;
        display: inline-block;
        margin-right: 5px;
    }
    
    .status-connected { background-color: #7c9885; }
    .status-error { background-color: #033f63; }
    .status-warning { background-color: #fedc97; }
    
    .refresh-info {
        background-color: rgba(181, 182, 130, 0.15);
        padding: 0.5rem;
        border-radius: 8px;
        margin-bottom: 1rem;
        font-size: 0.85rem;
        color: #b5b682;
        border: 1px solid #b5b682;
    }
    
    /* Button styling */
    .stButton > button {
        background-color: #033f63 !important;
        color: #fedc97 !important;
        border: none !important;
        transition: all 0.3s ease !important;
        font-weight: 500 !important;
    }
    
    .stButton > button:hover {
        background-color: #28666e !important;
        transform: translateY(-2px);
        box-shadow: 0 4px 8px rgba(40, 102, 110, 0.3);
    }
    
    /* ShipStation card components */
    .shipstation-container {
        background: linear-gradient(to bottom right, #f5f7f3, #e8ede5);
        border: 1.5px solid #7c9885;
        border-left: 4px solid #28666e;
        border-radius: 12px;
        padding: 1.2rem;
        box-shadow: 0 2px 8px rgba(40, 102, 110, 0.08);
    }
    
    .shipstation-header {
        display: flex;
        align-items: center;
        padding-bottom: 0.5rem;
        margin-bottom: 1rem;
        border-bottom: 2px solid #28666e;
    }
    
    .store-metric-card {
        background: linear-gradient(to bottom right, #f5f7f3, #e8ede5);
        border: 1.5px solid #7c9885;
        border-radius: 8px;
        padding: 0.75rem;
        text-align: center;
        box-shadow: 0 2px 4px rgba(124, 152, 133, 0.1);
        height: 100%;
        transition: transform 0.2s ease;
    }
    
    .store-metric-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 3px 6px rgba(40, 102, 110, 0.15);
    }
    
    .store-name {
        color: #033f63;
        font-size: 0.85rem;
        font-weight: 500;
        margin-bottom: 0.3rem;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
    }
    
    .store-count {
        color: #28666e;
        font-size: 1.5rem;
        font-weight: 700;
    }
</style>
""", unsafe_allow_html=True)

def get_config():
    """Get configuration from environment."""
    try:
        # Try environment variables first
        fv_client_id = os.getenv('FREIGHTVIEW_CLIENT_ID')
        fv_client_secret = os.getenv('FREIGHTVIEW_CLIENT_SECRET')
        ss_api_key = os.getenv('SS_CLIENT_ID')
        ss_api_secret = os.getenv('SS_CLIENT_SECRET')
        
        # Fallback to config file for FreightView
        if not fv_client_id or not fv_client_secret:
            try:
                import freightviewslack.config as config
                fv_client_id = config.CLIENT_ID
                fv_client_secret = config.CLIENT_SECRET
            except ImportError:
                pass
        
        # Check if we have all required credentials
        missing = []
        if not fv_client_id: missing.append('FREIGHTVIEW_CLIENT_ID')
        if not fv_client_secret: missing.append('FREIGHTVIEW_CLIENT_SECRET')
        if not ss_api_key: missing.append('SS_CLIENT_ID')
        if not ss_api_secret: missing.append('SS_CLIENT_SECRET')
        
        if missing:
            st.error(f"⚠️ Missing configuration: {', '.join(missing)}")
            st.stop()
        
        return fv_client_id, fv_client_secret, ss_api_key, ss_api_secret
        
    except Exception as e:
        st.error(f"Configuration error: {str(e)}")
        st.stop()

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

def create_freight_view_column(data: dict, summary: dict):
    """Create FreightView information column."""
    status = summary["freightview"]["status"]
    status_icon = "✅" if status == "connected" else "⚠️"
    
    # Get shipment counts
    inbound_count = summary["freightview"].get("inbound_count", 0)
    outbound_count = summary["freightview"].get("outbound_count", 0)
    total_count = summary["freightview"].get("total_shipments", 0)
    
    st.markdown(f"""
    <div style="
        background: linear-gradient(to bottom right, #f5f7f3, #e8ede5);
        border: 1.5px solid #7c9885;
        border-left: 4px solid #033f63;
        border-radius: 12px;
        padding: 1.2rem;
        height: 100%;
        box-shadow: 0 2px 8px rgba(3, 63, 99, 0.08);
    ">
        <div style="display: flex; align-items: center; margin-bottom: 1rem; padding-bottom: 0.5rem; border-bottom: 2px solid #033f63;">
            <span style="font-size: 1.5rem; margin-right: 0.5rem;">🚛</span>
            <span style="font-size: 1.1rem; font-weight: 600; color: #033f63;">FreightView</span>
            <span style="margin-left: auto; font-size: 0.9rem;">{status_icon}</span>
        </div>
        <div style="padding-left: 0.5rem;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.8rem;">
                <span style="color: #28666e; font-size: 0.95rem; font-weight: 500;">📥 Inbound:</span>
                <span style="font-weight: 700; color: #033f63; font-size: 1.8rem;">{inbound_count}</span>
            </div>
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <span style="color: #28666e; font-size: 0.95rem; font-weight: 500;">📤 Outbound:</span>
                <span style="font-weight: 700; color: #033f63; font-size: 1.8rem;">{outbound_count}</span>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

def create_shipstation_column(data: dict, summary: dict):
    """Create ShipStation information column with store breakdown."""
    status = summary["shipstation"]["status"]
    status_icon = "✅" if status == "connected" else "⚠️"
    
    # Get order counts
    pending_orders = summary["shipstation"].get("pending_orders", 0)
    
    # Store name abbreviation dictionary
    STORE_ABBREVIATIONS = {
        'Bala': 'Bala',
        'Body Nutrition - Wholesale': 'Wholesale',
        'Gym Molly Store': 'Gym Molly',
        'MWL Buyside Store': 'MWL',
        'Manual Orders': 'Manual',
        'MediWeight OLD Orders': 'MWL OLD',
        'New Amazon Store': 'Amazon',
        'Rate Browser': 'Unused',
        'Shopify Store': 'Shopify',
        'TestRateShopping': 'TEST'
    }
    
    # Build store ID to name mapping from stores API
    store_id_to_name = {}
    if data["shipstation"].get("stores"):
        for store in data["shipstation"]["stores"]:
            if isinstance(store, dict):
                store_id = store.get('storeId')
                store_name = store.get('storeName')
                if store_id and store_name:
                    store_id_to_name[str(store_id)] = store_name
    
    # Extract store breakdown
    store_breakdown = {}
    
    if data["shipstation"]["orders"] and data["shipstation"]["orders"].orders:
        for order in data["shipstation"]["orders"].orders:
            store_id = None
            
            # Check advancedOptions for store ID
            if order.advancedOptions:
                store_id = order.advancedOptions.get('storeId')
            
            # Get the store name from our mapping
            if store_id and str(store_id) in store_id_to_name:
                store_key = store_id_to_name[str(store_id)]
            elif store_id:
                store_key = f"Store {store_id}"
            else:
                store_key = "Unknown Store"
            
            # Clean up the store name and ensure it's a string
            store_key = str(store_key).strip()
            
            # Apply abbreviation with fallback to original name
            store_key = STORE_ABBREVIATIONS.get(store_key, store_key)
            
            store_breakdown[store_key] = store_breakdown.get(store_key, 0) + 1
    
    # Sort stores by order count
    sorted_stores = sorted(store_breakdown.items(), key=lambda x: x[1], reverse=True)
    
    # Create the main container with header and metric inside
    st.markdown(f"""
    <div class="shipstation-container">
        <div class="shipstation-header">
            <span style="font-size: 1.5rem; margin-right: 0.5rem;">📦</span>
            <span style="font-size: 1.1rem; font-weight: 600; color: #033f63;">ShipStation</span>
            <span style="margin-left: auto; font-size: 0.9rem;">{status_icon}</span>
        </div>
        <div style="padding-left: 0.5rem;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem;">
                <span style="color: #28666e; font-weight: 500; font-size: 0.95rem;">Total Pending:</span>
                <span style="font-weight: 700; color: #033f63; font-size: 2.2rem;">{pending_orders}</span>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Add spacing before store cards
    st.markdown("<div style='margin-top: 1.5rem;'></div>", unsafe_allow_html=True)
    
    # Create store breakdown using small metric cards
    if sorted_stores:
        # Create rows of 3 columns each for store cards
        num_stores_to_show = min(12, len(sorted_stores))  # Show up to 12 stores
        for i in range(0, num_stores_to_show, 3):
            cols = st.columns(3, gap="medium")
            for j in range(3):
                if i + j < num_stores_to_show:
                    store_name, count = sorted_stores[i + j]
                    with cols[j]:
                        # Truncate store name if too long
                        display_name = store_name[:15] + "..." if len(store_name) > 15 else store_name
                        
                        # Create a small metric card for each store
                        st.markdown(f"""
                        <div class="store-metric-card">
                            <div class="store-name" title="{store_name}">{display_name}</div>
                            <div class="store-count">{count}</div>
                        </div>
                        """, unsafe_allow_html=True)
        
        # Show remaining stores count if there are more
        if len(sorted_stores) > num_stores_to_show:
            remaining = len(sorted_stores) - num_stores_to_show
            st.markdown(f"""
            <div style="color: #28666e; font-size: 0.85rem; font-style: italic; margin-top: 0.5rem; opacity: 0.7; text-align: center;">
                ...and {remaining} more stores
            </div>
            """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div style="color: #28666e; font-size: 0.9rem; opacity: 0.7;">
            No pending orders
        </div>
        """, unsafe_allow_html=True)

# Chart functions removed per user request - keeping space for cleaner layout

def style_old_orders(df: pd.DataFrame) -> pd.DataFrame:
    """Apply styling to highlight old orders (>3 days)."""
    def highlight_old_rows(row):
        """Highlight rows where order date is over 3 days old."""
        if '_order_date_raw' in row and row['_order_date_raw']:
            try:
                # Parse the ISO date
                order_date_str = str(row['_order_date_raw'])
                order_date = datetime.fromisoformat(order_date_str.replace('Z', '+00:00').split('.')[0])
                
                # Calculate age in days
                days_old = (datetime.now() - order_date).days
                
                # Apply yellow background with red text if over 3 days old
                if days_old > 3:
                    return ['background-color: #fedc97; color: #d32f2f'] * len(row)
            except:
                pass
        
        return [''] * len(row)
    
    # Apply the styling
    styled_df = df.style.apply(highlight_old_rows, axis=1)
    return styled_df


def create_data_table(df: pd.DataFrame, title: str, service_type: str):
    """Create data table with service-specific styling."""
    if df.empty:
        st.info(f"No {title.lower()} data available")
        return
    
    section_class = "freightview-section" if "FreightView" in title else "shipstation-section"
    
    st.markdown(f'<div class="service-section {section_class}">', unsafe_allow_html=True)
    st.subheader(f"📋 {title}")
    
    # Add filters
    col1, col2, col3 = st.columns(3)
    
    with col1:
        # Service-specific filters
        if service_type == "freightview":
            if "Carrier Name" in df.columns:
                carriers = ['All'] + sorted(df['Carrier Name'].dropna().unique().tolist())
                selected_carrier = st.selectbox(f"Filter by Carrier", carriers, key=f"carrier_{title}")
            else:
                selected_carrier = 'All'
        else:
            if "Carrier" in df.columns:
                carriers = ['All'] + sorted(df['Carrier'].dropna().unique().tolist())
                selected_carrier = st.selectbox(f"Filter by Carrier", carriers, key=f"carrier_{title}")
            else:
                selected_carrier = 'All'
    
    with col2:
        if "Status" in df.columns:
            statuses = ['All'] + sorted(df['Status'].dropna().unique().tolist())
            selected_status = st.selectbox(f"Filter by Status", statuses, key=f"status_{title}")
        else:
            selected_status = 'All'
    
    with col3:
        search_term = st.text_input(f"Search {title}", key=f"search_{title}")
    
    # Apply filters
    filtered_df = df.copy()
    
    if selected_carrier != 'All':
        carrier_col = "Carrier Name" if "Carrier Name" in df.columns else "Carrier"
        if carrier_col in filtered_df.columns:
            filtered_df = filtered_df[filtered_df[carrier_col] == selected_carrier]
    
    if selected_status != 'All' and 'Status' in filtered_df.columns:
        filtered_df = filtered_df[filtered_df['Status'] == selected_status]
    
    if search_term:
        mask = filtered_df.astype(str).apply(lambda x: x.str.contains(search_term, case=False, na=False)).any(axis=1)
        filtered_df = filtered_df[mask]
    
    # Display table
    if not filtered_df.empty:
        # Create display dataframe and remove the raw date column for display
        display_df = filtered_df.copy()
        
        # Check if this is ShipStation Orders table and apply row highlighting
        if "ShipStation Pending Orders" in title and '_order_date_raw' in display_df.columns:
            # Apply styling for old orders
            styled_df = style_old_orders(display_df)
            
            # Format currency columns in the styled dataframe
            for col in display_df.columns:
                if col != '_order_date_raw' and ('Cost' in col or 'Price' in col or 'Total' in col or 'Value' in col):
                    styled_df = styled_df.format({col: lambda x: f"${x:,.2f}" if pd.notna(x) and x != 0 else "N/A"})
            
            # Hide the raw date column from display
            styled_df = styled_df.hide(axis='columns', subset=['_order_date_raw'])
            
            # Display the styled dataframe
            st.dataframe(styled_df, use_container_width=True, height=400)
        else:
            # Standard display for other tables
            # Remove raw date column if present
            if '_order_date_raw' in display_df.columns:
                display_df = display_df.drop('_order_date_raw', axis=1)
            
            # Format currency columns
            for col in display_df.columns:
                if 'Cost' in col or 'Price' in col or 'Total' in col or 'Value' in col:
                    display_df[col] = display_df[col].apply(lambda x: f"${x:,.2f}" if pd.notna(x) and x != 0 else "N/A")
            
            st.dataframe(display_df, use_container_width=True, height=400)
        
        # Export button - use original filtered_df for export
        export_df = filtered_df.copy()
        if '_order_date_raw' in export_df.columns:
            export_df = export_df.drop('_order_date_raw', axis=1)
        csv = export_df.to_csv(index=False)
        st.download_button(
            label=f"📥 Download {title} Data",
            data=csv,
            file_name=f"{title.lower().replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv"
        )
    else:
        st.info("No data matches the current filters")
    
    st.markdown('</div>', unsafe_allow_html=True)

def main():
    initialize_session_state()
    
    # Header
    st.markdown("""
    <div class="main-header">
        <h1 style="margin: 0; font-size: 2rem; text-shadow: 1px 1px 2px rgba(0, 0, 0, 0.2);">🚢 Unified Shipping Dashboard</h1>
        <p style="margin: 0.5rem 0 0 0; opacity: 0.95; font-size: 1rem; color: #fedc97;">FreightView + ShipStation Integration</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Get configuration and initialize service
    try:
        fv_client_id, fv_client_secret, ss_api_key, ss_api_secret = get_config()
        unified_service = UnifiedDataService(fv_client_id, fv_client_secret, ss_api_key, ss_api_secret)
    except Exception as e:
        st.error(f"Service initialization error: {str(e)}")
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
    
    with col2:
        if st.button("🔄 Refresh All Data", type="primary"):
            st.session_state.last_update = None
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
        with st.spinner("🔄 Loading data from both services..."):
            try:
                all_data = unified_service.fetch_all_data()
                summary = unified_service.get_unified_summary(all_data)
                
                # Store in session state
                st.session_state.all_data = all_data
                st.session_state.summary = summary
                st.session_state.last_update = datetime.now()
                st.session_state.data_loaded = True
                
                st.success("✅ Data loaded from both services!")
                time.sleep(1)
                st.rerun()
                
            except Exception as e:
                st.session_state.error_message = f"Error loading data: {str(e)}"
                st.session_state.data_loaded = False
    
    # Display service status in two clean columns
    if st.session_state.data_loaded:
        # Add inbound/outbound counts to summary
        if st.session_state.all_data["freightview"]["shipments"]:
            fv_inbound = unified_service.freight_service.process_inbound_data(st.session_state.all_data["freightview"]["shipments"])
            fv_outbound = unified_service.freight_service.process_outbound_data(st.session_state.all_data["freightview"]["shipments"])
            st.session_state.summary["freightview"]["inbound_count"] = len(fv_inbound)
            st.session_state.summary["freightview"]["outbound_count"] = len(fv_outbound)
        
        # Create two-column layout
        col1, col2 = st.columns(2)
        
        with col1:
            create_freight_view_column(st.session_state.all_data, st.session_state.summary)
        
        with col2:
            create_shipstation_column(st.session_state.all_data, st.session_state.summary)
        
        st.markdown("---")
        
        # Data tables in tabs
        tab1, tab2, tab3, tab4 = st.tabs([
            "🚛 FreightView Inbound", 
            "🚛 FreightView Outbound", 
            "📦 ShipStation Orders",
            "📤 ShipStation Shipments"
        ])
        
        # Process and display FreightView data
        if st.session_state.all_data["freightview"]["shipments"]:
            fv_inbound = unified_service.freight_service.process_inbound_data(st.session_state.all_data["freightview"]["shipments"])
            fv_outbound = unified_service.freight_service.process_outbound_data(st.session_state.all_data["freightview"]["shipments"])
            
            with tab1:
                create_data_table(pd.DataFrame(fv_inbound), "FreightView Inbound Freight", "freightview")
            
            with tab2:
                create_data_table(pd.DataFrame(fv_outbound), "FreightView Outbound Freight", "freightview")
        else:
            with tab1:
                st.error("❌ FreightView inbound data unavailable")
            with tab2:
                st.error("❌ FreightView outbound data unavailable")
        
        # Process and display ShipStation data
        if st.session_state.all_data["shipstation"]["orders"]:
            ss_orders = unified_service.process_shipstation_orders(st.session_state.all_data["shipstation"]["orders"])
            
            with tab3:
                create_data_table(pd.DataFrame(ss_orders), "ShipStation Pending Orders", "shipstation")
        else:
            with tab3:
                st.error("❌ ShipStation orders data unavailable")
        
        if st.session_state.all_data["shipstation"]["shipments"]:
            ss_shipments = unified_service.process_shipstation_shipments(st.session_state.all_data["shipstation"]["shipments"])
            
            with tab4:
                create_data_table(pd.DataFrame(ss_shipments), "ShipStation Recent Shipments", "shipstation")
        else:
            with tab4:
                st.error("❌ ShipStation shipments data unavailable")
    
    else:
        st.info("👆 Click 'Refresh All Data' to load shipping data from both services")
    
    # Auto-refresh logic
    if st.session_state.auto_refresh_enabled and st.session_state.data_loaded:
        time.sleep(60)
        st.rerun()

if __name__ == "__main__":
    main()