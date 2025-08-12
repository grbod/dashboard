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
    
    def get_two_week_range(self) -> tuple:
        """Get the start and end dates for current week and previous week (2 weeks total).
        Treats Sunday as the start of the week."""
        today = datetime.now().date()
        
        # Calculate days since Sunday (Sunday = 0, Monday = 1, ... Saturday = 6)
        # Python's weekday() returns Monday = 0, so we adjust
        days_since_sunday = (today.weekday() + 1) % 7
        
        # Find Sunday of this week (start of current week)
        sunday_this_week = today - timedelta(days=days_since_sunday)
        
        # Find Sunday of previous week (start of previous week) 
        sunday_last_week = sunday_this_week - timedelta(days=7)
        
        # Find Saturday of this week (end of current week)
        saturday_this_week = sunday_this_week + timedelta(days=6)
        
        return sunday_last_week, saturday_this_week
    
    @st.cache_data(ttl=900)  # Cache for 15 minutes
    def fetch_upcoming_pickups(_self) -> Optional[List[Dict]]:
        """
        Fetch upcoming pickups from Airtable with the following criteria:
        - Status in ['Sent PO', 'PO Confirmed', 'Ready for Pickup!', 'Pickup Scheduled']
        - Vendor Ready-Date is within the current week or previous week (2 weeks total)
        """
        if not _self.table:
            _self.logger.error("Airtable table not initialized")
            return None
        
        try:
            # Get two week range (previous week + current week)
            start_date, end_date = _self.get_two_week_range()
            
            # Build the Airtable formula for filtering
            # Status filter
            status_conditions = [
                "{Status}='Sent PO'",
                "{Status}='PO Confirmed'",
                "{Status}='Ready for Pickup!'",
                "{Status}='Pickup Scheduled'"
            ]
            status_formula = f"OR({','.join(status_conditions)})"
            
            # Date filter - Vendor Ready-Date within the two week period
            # Using ISO date format for comparison
            date_formula = f"AND(IS_AFTER({{Vendor Ready-Date}}, '{start_date.isoformat()}'), IS_BEFORE({{Vendor Ready-Date}}, DATEADD('{end_date.isoformat()}', 1, 'days')))"
            
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
                
                # Extract only the requested fields - using correct Airtable column names
                processed_record = {
                    'Name': fields.get('Name', 'N/A'),  # Product item code
                    'Supplier': fields.get('Supplier', 'N/A'),
                    'Notes/PO': fields.get('Notes/PO', 'N/A'),
                    'Status': fields.get('Status', 'N/A'),
                    'Vendor Ready-Date': fields.get('Vendor Ready-Date', 'N/A'),
                }
                
                # Format date if available
                if processed_record['Vendor Ready-Date'] != 'N/A':
                    try:
                        date_obj = datetime.strptime(processed_record['Vendor Ready-Date'], '%Y-%m-%d')
                        processed_record['Vendor Ready-Date'] = date_obj.strftime('%-m/%-d/%Y')
                        processed_record['_ready_date_raw'] = fields.get('Vendor Ready-Date')  # Keep raw for sorting
                    except:
                        pass
                
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
                'unique_pos': 0,
                'by_status': {},
                'total_value': 0,
                'earliest_pickup': None,
                'latest_pickup': None
            }
        
        summary = {
            'total_pickups': len(records),
            'unique_pos': 0,
            'by_status': {},
            'total_value': 0,
            'earliest_pickup': None,
            'latest_pickup': None
        }
        
        dates = []
        unique_po_set = set()
        
        for record in records:
            fields = record.get('fields', {})
            
            # Count by status
            status = fields.get('Status', 'Unknown')
            summary['by_status'][status] = summary['by_status'].get(status, 0) + 1
            
            # Track unique POs
            po = fields.get('Notes/PO', '')
            # Count any non-empty PO value (including 'CS')
            if po and po.strip():
                unique_po_set.add(po.strip())
            
            # Sum total value
            total_cost = fields.get('Total Cost', fields.get('Total', 0))
            if isinstance(total_cost, (int, float)):
                summary['total_value'] += total_cost
            
            # Track dates
            ready_date = fields.get('Vendor Ready-Date')
            if ready_date:
                dates.append(ready_date)
        
        # Set the unique POs count
        summary['unique_pos'] = len(unique_po_set)
        
        # Find earliest and latest dates
        if dates:
            dates.sort()
            summary['earliest_pickup'] = dates[0]
            summary['latest_pickup'] = dates[-1]
        
        return summary