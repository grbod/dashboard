"""
Airtable service for fetching upcoming pickups from the Procurement table.
"""

import logging
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import streamlit as st
from pyairtable import Api

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

class AirtableService:
    """Service class for Airtable API interactions."""
    
    def __init__(self, api_key: str, base_id: str, table_name: str):
        self.api_key = api_key
        self.base_id = base_id
        self.table_name = table_name
        self.logger = logging.getLogger(__name__)
        
        # Initialize pyairtable API
        try:
            self.api = Api(api_key)
            self.table = self.api.table(base_id, table_name)
        except Exception as e:
            self.logger.error(f"Failed to initialize Airtable API: {str(e)}")
            self.api = None
            self.table = None
    
    def get_current_week_range(self) -> tuple:
        """Get the start and end dates of the current week (Monday to Sunday)."""
        today = datetime.now().date()
        # Find Monday of this week
        monday = today - timedelta(days=today.weekday())
        # Find Sunday of this week
        sunday = monday + timedelta(days=6)
        return monday, sunday
    
    @st.cache_data(ttl=900)  # Cache for 15 minutes
    def fetch_upcoming_pickups(_self) -> Optional[List[Dict]]:
        """
        Fetch upcoming pickups from Airtable with the following criteria:
        - Status in ['Sent PO', 'PO Confirmed', 'Ready for Pickup!', 'Pickup Scheduled']
        - Vendor Ready-Date is within the current week
        """
        if not _self.table:
            _self.logger.error("Airtable table not initialized")
            return None
        
        try:
            # Get current week range
            monday, sunday = _self.get_current_week_range()
            
            # Build the Airtable formula for filtering
            # Status filter
            status_conditions = [
                "{Status}='Sent PO'",
                "{Status}='PO Confirmed'",
                "{Status}='Ready for Pickup!'",
                "{Status}='Pickup Scheduled'"
            ]
            status_formula = f"OR({','.join(status_conditions)})"
            
            # Date filter - Vendor Ready-Date within current week
            # Using ISO date format for comparison
            date_formula = f"AND(IS_AFTER({{Vendor Ready-Date}}, '{monday.isoformat()}'), IS_BEFORE({{Vendor Ready-Date}}, DATEADD('{sunday.isoformat()}', 1, 'days')))"
            
            # Combine conditions
            formula = f"AND({status_formula}, {date_formula})"
            
            _self.logger.info(f"Fetching records with formula: {formula}")
            
            # Fetch records from Airtable
            records = _self.table.all(formula=formula)
            
            _self.logger.info(f"Fetched {len(records)} upcoming pickups from Airtable")
            return records
            
        except Exception as e:
            _self.logger.error(f"Error fetching Airtable data: {str(e)}")
            return None
    
    def process_pickup_data(self, records: List[Dict]) -> List[Dict]:
        """Process raw Airtable records into formatted data for dashboard display."""
        processed_data = []
        
        if not records:
            return processed_data
        
        for record in records:
            try:
                fields = record.get('fields', {})
                
                # Extract relevant fields with safe defaults
                processed_record = {
                    'Record ID': record.get('id', 'N/A'),
                    'Vendor': fields.get('Vendor', 'N/A'),
                    'PO Number': fields.get('PO Number', fields.get('PO #', 'N/A')),
                    'Status': fields.get('Status', 'N/A'),
                    'Vendor Ready-Date': fields.get('Vendor Ready-Date', 'N/A'),
                    'Product': fields.get('Product', fields.get('Description', 'N/A')),
                    'Quantity': fields.get('Quantity', 'N/A'),
                    'Unit Cost': fields.get('Unit Cost', 0),
                    'Total Cost': fields.get('Total Cost', fields.get('Total', 0)),
                    'Carrier': fields.get('Carrier', 'N/A'),
                    'Tracking': fields.get('Tracking', fields.get('Tracking Number', 'N/A')),
                    'Notes': fields.get('Notes', ''),
                }
                
                # Format date if available
                if processed_record['Vendor Ready-Date'] != 'N/A':
                    try:
                        date_obj = datetime.strptime(processed_record['Vendor Ready-Date'], '%Y-%m-%d')
                        processed_record['Vendor Ready-Date'] = date_obj.strftime('%-m/%-d/%Y')
                        processed_record['_ready_date_raw'] = fields.get('Vendor Ready-Date')  # Keep raw for sorting
                    except:
                        pass
                
                # Format currency fields
                if isinstance(processed_record['Unit Cost'], (int, float)) and processed_record['Unit Cost'] > 0:
                    processed_record['Unit Cost'] = f"${processed_record['Unit Cost']:,.2f}"
                else:
                    processed_record['Unit Cost'] = 'N/A'
                
                if isinstance(processed_record['Total Cost'], (int, float)) and processed_record['Total Cost'] > 0:
                    processed_record['Total Cost'] = f"${processed_record['Total Cost']:,.2f}"
                else:
                    processed_record['Total Cost'] = 'N/A'
                
                processed_data.append(processed_record)
                
            except Exception as e:
                self.logger.error(f"Error processing Airtable record {record.get('id', 'unknown')}: {str(e)}")
                continue
        
        # Sort by Vendor Ready-Date
        processed_data.sort(key=lambda x: x.get('_ready_date_raw', '9999-12-31'))
        
        return processed_data
    
    def get_pickup_summary(self, records: List[Dict]) -> Dict:
        """Generate summary metrics for upcoming pickups."""
        if not records:
            return {
                'total_pickups': 0,
                'by_status': {},
                'total_value': 0,
                'earliest_pickup': None,
                'latest_pickup': None
            }
        
        summary = {
            'total_pickups': len(records),
            'by_status': {},
            'total_value': 0,
            'earliest_pickup': None,
            'latest_pickup': None
        }
        
        dates = []
        
        for record in records:
            fields = record.get('fields', {})
            
            # Count by status
            status = fields.get('Status', 'Unknown')
            summary['by_status'][status] = summary['by_status'].get(status, 0) + 1
            
            # Sum total value
            total_cost = fields.get('Total Cost', fields.get('Total', 0))
            if isinstance(total_cost, (int, float)):
                summary['total_value'] += total_cost
            
            # Track dates
            ready_date = fields.get('Vendor Ready-Date')
            if ready_date:
                dates.append(ready_date)
        
        # Find earliest and latest dates
        if dates:
            dates.sort()
            summary['earliest_pickup'] = dates[0]
            summary['latest_pickup'] = dates[-1]
        
        return summary