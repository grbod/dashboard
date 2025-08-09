# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

FreightViewDash is a unified shipping management system that integrates both FreightView and ShipStation APIs. The system provides both Slack notifications and a modern Streamlit web dashboard for comprehensive shipping analytics across freight and package shipping services.

## Commands

### Running the Unified Dashboard (Recommended)
```bash
pip install -r requirements.txt
streamlit run unified_dashboard.py --server.port 8502
```
The unified dashboard will be available at http://localhost:8502

### Running Individual Dashboards
```bash
# FreightView only
streamlit run dashboard.py --server.port 8501

# Test dashboard with mock data
streamlit run dashboard_test.py --server.port 8503
```

### Running the Original Slack Bot
```bash
cd freightviewslack
python freight4.py
```

### Dependencies
Install from requirements.txt:
```bash
pip install -r requirements.txt
```

Core dependencies:
- `streamlit` - Web dashboard framework
- `requests` - HTTP API calls
- `pandas` - Data manipulation
- `plotly` - Interactive charts
- `pydantic` - Data validation and parsing
- `slack-sdk` - Slack integration (for original bot)
- `tabulate` - Table formatting (for original bot)

## Architecture

### Core Files
- `unified_dashboard.py` - **Main unified dashboard (FreightView + ShipStation)**
- `unified_data_service.py` - **Unified service for both APIs**
- `dashboard.py` - FreightView-only dashboard
- `data_service.py` - FreightView API service layer
- `shipstation_models.py` - **Pydantic models for ShipStation API**
- `freightviewslack/freight4.py` - Original Slack bot application
- `freightviewslack/pydatamodel.py` - Pydantic models for FreightView API responses
- `requirements.txt` - Python dependencies
- `test_*.py` - Test files and mock data

### Key Components

**Streamlit Dashboard (`dashboard.py`)**
- Modern web interface with auto-refresh every 15 minutes
- Real-time metrics cards (total shipments, cost analysis, weights)
- Interactive charts using Plotly (shipment distribution, carrier cost analysis)
- Tabbed interface for inbound/outbound freight data
- Advanced filtering and search capabilities
- CSV export functionality
- Connection status indicators

**Data Service Layer (`data_service.py`)**
- `FreightDataService` class handles all API interactions
- OAuth2 authentication with FreightView API
- Data caching with Streamlit's `@st.cache_data` (15-minute TTL)
- Robust error handling and data validation
- Structured data processing for dashboard consumption

**Legacy Slack Bot (`freightviewslack/`)**
- `get_API_auth()` - Handles OAuth2 client credentials flow
- `extract_inbound()` / `extract_outbound()` - Process shipment data for Slack
- `post_to_slack()` / `write_to_slack()` - Slack channel integration
- Posts to #shipping channel by default

**Data Models**
- Pydantic models in `pydatamodel.py` validate API responses
- Main models: `Model`, `Shipment`, `Location`, `Equipment`, `SelectedQuote`, `Tracking`
- Many fields commented out indicating full API response available

### API Endpoints Used
- `/v2.0/auth/token` - Authentication
- `/v2.0/shipments?status=picked-up` - Main shipment data
- `/v2.0/shipments?status=pending&status=awarded` - Scheduled pickups (partial implementation)

### Error Handling
- Pydantic validation errors are logged to `error.log`
- Slack API errors are caught and printed
- Missing data fields are handled with try/except blocks and default values

## Configuration Required

### Option 1: Environment Variables (Recommended for Dashboard)
Create a `.env` file in the root directory:
```bash
FREIGHTVIEW_CLIENT_ID=your_freightview_client_id
FREIGHTVIEW_CLIENT_SECRET=your_freightview_client_secret
SS_CLIENT_ID=your_shipstation_api_key
SS_CLIENT_SECRET=your_shipstation_api_secret
```

### Option 2: Config File (Required for Slack Bot)
Create a `freightviewslack/config.py` file:
```python
CLIENT_ID = "your_freightview_client_id"
CLIENT_SECRET = "your_freightview_client_secret" 
SLACK_TOKEN = "your_slack_bot_token"
```

The dashboard will automatically try the config file first, then fall back to environment variables.

## Current State

The main functionality for processing picked-up shipments is working but partially commented out in the main() function. The `other_sched_pickups()` function is incomplete. The application appears to be in active development with some experimental code sections.