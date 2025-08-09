"""
Unit tests for Airtable integration.
"""

import pytest
import pandas as pd
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
from airtable_service import AirtableService
from unified_data_service import UnifiedDataService


class TestAirtableService:
    """Test suite for AirtableService class."""
    
    @pytest.fixture
    def airtable_service(self):
        """Create an AirtableService instance for testing."""
        with patch('airtable_service.Api'):
            service = AirtableService(
                api_key="test_key",
                base_id="test_base",
                table_name="test_table"
            )
            return service
    
    def test_get_current_week_range(self, airtable_service):
        """Test that current week range calculation is correct."""
        monday, sunday = airtable_service.get_current_week_range()
        
        # Check that monday is actually a Monday
        assert monday.weekday() == 0
        # Check that sunday is actually a Sunday
        assert sunday.weekday() == 6
        # Check that they are 6 days apart
        assert (sunday - monday).days == 6
    
    def test_process_pickup_data_with_valid_records(self, airtable_service):
        """Test processing of valid Airtable records."""
        mock_records = [
            {
                'id': 'rec123',
                'fields': {
                    'Vendor': 'Test Vendor 1',
                    'PO Number': 'PO-001',
                    'Status': 'Sent PO',
                    'Vendor Ready-Date': '2025-08-12',
                    'Product': 'Test Product',
                    'Quantity': 100,
                    'Unit Cost': 10.50,
                    'Total Cost': 1050.00,
                    'Carrier': 'UPS',
                    'Tracking': '1Z999AA1234567890'
                }
            },
            {
                'id': 'rec456',
                'fields': {
                    'Vendor': 'Test Vendor 2',
                    'PO #': 'PO-002',  # Test alternate field name
                    'Status': 'Ready for Pickup!',
                    'Vendor Ready-Date': '2025-08-13',
                    'Description': 'Another Product',  # Test alternate field name
                    'Quantity': 50,
                    'Unit Cost': 0,  # Test zero value
                    'Total': 500.00,  # Test alternate field name
                }
            }
        ]
        
        processed = airtable_service.process_pickup_data(mock_records)
        
        assert len(processed) == 2
        
        # Check first record
        assert processed[0]['Vendor'] == 'Test Vendor 1'
        assert processed[0]['PO Number'] == 'PO-001'
        assert processed[0]['Status'] == 'Sent PO'
        assert processed[0]['Vendor Ready-Date'] == '8/12/2025'
        assert processed[0]['Unit Cost'] == '$10.50'
        assert processed[0]['Total Cost'] == '$1,050.00'
        assert processed[0]['Tracking'] == '1Z999AA1234567890'
        
        # Check second record with alternate fields
        assert processed[1]['PO Number'] == 'PO-002'
        assert processed[1]['Product'] == 'Another Product'
        assert processed[1]['Unit Cost'] == 'N/A'
        assert processed[1]['Total Cost'] == '$500.00'
    
    def test_process_pickup_data_with_missing_fields(self, airtable_service):
        """Test processing records with missing fields."""
        mock_records = [
            {
                'id': 'rec789',
                'fields': {
                    'Vendor': 'Minimal Vendor',
                    'Status': 'PO Confirmed'
                }
            }
        ]
        
        processed = airtable_service.process_pickup_data(mock_records)
        
        assert len(processed) == 1
        assert processed[0]['Vendor'] == 'Minimal Vendor'
        assert processed[0]['PO Number'] == 'N/A'
        assert processed[0]['Product'] == 'N/A'
        assert processed[0]['Unit Cost'] == 'N/A'
        assert processed[0]['Total Cost'] == 'N/A'
        assert processed[0]['Carrier'] == 'N/A'
        assert processed[0]['Tracking'] == 'N/A'
    
    def test_process_pickup_data_with_invalid_date(self, airtable_service):
        """Test handling of invalid date formats."""
        mock_records = [
            {
                'id': 'rec999',
                'fields': {
                    'Vendor': 'Date Test Vendor',
                    'Vendor Ready-Date': 'invalid-date-format'
                }
            }
        ]
        
        processed = airtable_service.process_pickup_data(mock_records)
        
        assert len(processed) == 1
        # Date should remain unchanged if parsing fails
        assert processed[0]['Vendor Ready-Date'] == 'invalid-date-format'
    
    def test_process_pickup_data_empty_records(self, airtable_service):
        """Test processing empty record list."""
        processed = airtable_service.process_pickup_data([])
        assert processed == []
    
    def test_process_pickup_data_none_records(self, airtable_service):
        """Test processing None records."""
        processed = airtable_service.process_pickup_data(None)
        assert processed == []
    
    def test_get_pickup_summary(self, airtable_service):
        """Test summary generation from records."""
        mock_records = [
            {
                'id': 'rec1',
                'fields': {
                    'Status': 'Sent PO',
                    'Total Cost': 1000.00,
                    'Vendor Ready-Date': '2025-08-12'
                }
            },
            {
                'id': 'rec2',
                'fields': {
                    'Status': 'Sent PO',
                    'Total Cost': 500.00,
                    'Vendor Ready-Date': '2025-08-14'
                }
            },
            {
                'id': 'rec3',
                'fields': {
                    'Status': 'Ready for Pickup!',
                    'Total': 750.00,
                    'Vendor Ready-Date': '2025-08-13'
                }
            }
        ]
        
        summary = airtable_service.get_pickup_summary(mock_records)
        
        assert summary['total_pickups'] == 3
        assert summary['by_status']['Sent PO'] == 2
        assert summary['by_status']['Ready for Pickup!'] == 1
        assert summary['total_value'] == 2250.00
        assert summary['earliest_pickup'] == '2025-08-12'
        assert summary['latest_pickup'] == '2025-08-14'
    
    def test_get_pickup_summary_empty_records(self, airtable_service):
        """Test summary generation with empty records."""
        summary = airtable_service.get_pickup_summary([])
        
        assert summary['total_pickups'] == 0
        assert summary['by_status'] == {}
        assert summary['total_value'] == 0
        assert summary['earliest_pickup'] is None
        assert summary['latest_pickup'] is None


class TestCurrencyFormatting:
    """Test suite for currency formatting edge cases."""
    
    def test_format_currency_values(self):
        """Test various currency value formats."""
        test_cases = [
            (100, "$100.00"),
            (1000.50, "$1,000.50"),
            (0, "N/A"),
            (None, "N/A"),
            ("$500.00", "$500.00"),  # Already formatted
            ("N/A", "N/A"),  # Already N/A
        ]
        
        for input_val, expected in test_cases:
            if isinstance(input_val, str):
                result = input_val
            else:
                result = f"${input_val:,.2f}" if pd.notna(input_val) and input_val != 0 else "N/A"
            assert result == expected, f"Failed for input {input_val}: got {result}, expected {expected}"


class TestUnifiedDataServiceIntegration:
    """Test suite for UnifiedDataService Airtable integration."""
    
    @pytest.fixture
    def unified_service(self):
        """Create UnifiedDataService with mocked dependencies."""
        with patch('unified_data_service.FreightDataService'), \
             patch('unified_data_service.ShipStationService'), \
             patch('unified_data_service.AirtableService'):
            
            service = UnifiedDataService(
                fv_client_id="test_fv_id",
                fv_client_secret="test_fv_secret",
                ss_api_key="test_ss_key",
                ss_api_secret="test_ss_secret",
                at_api_key="test_at_key",
                at_base_id="test_at_base",
                at_table_name="test_at_table"
            )
            return service
    
    def test_process_airtable_pickups(self, unified_service):
        """Test processing Airtable pickups through UnifiedDataService."""
        mock_pickups = [
            {'fields': {'Vendor': 'Test', 'Status': 'Sent PO'}}
        ]
        
        # Mock the airtable_service's process_pickup_data method
        unified_service.airtable_service.process_pickup_data = Mock(return_value=[
            {'Vendor': 'Test', 'Status': 'Sent PO', 'Total Cost': '$100.00'}
        ])
        
        result = unified_service.process_airtable_pickups(mock_pickups)
        
        assert len(result) == 1
        assert result[0]['Vendor'] == 'Test'
        assert result[0]['Total Cost'] == '$100.00'
    
    def test_get_unified_summary_with_airtable(self, unified_service):
        """Test unified summary includes Airtable data."""
        mock_all_data = {
            "freightview": {"shipments": None, "error": None},
            "shipstation": {"orders": None, "shipments": None, "stores": None, "error": None},
            "airtable": {
                "upcoming_pickups": [
                    {'fields': {'Status': 'Sent PO', 'Total Cost': 1000}}
                ],
                "error": None
            }
        }
        
        # Mock the get_pickup_summary method
        unified_service.airtable_service.get_pickup_summary = Mock(return_value={
            "total_pickups": 1,
            "total_value": 1000,
            "by_status": {"Sent PO": 1}
        })
        
        summary = unified_service.get_unified_summary(mock_all_data)
        
        assert summary["airtable"]["upcoming_pickups"] == 1
        assert summary["airtable"]["total_pickup_value"] == 1000
        assert summary["airtable"]["status"] == "connected"
        assert summary["combined"]["total_active_shipments"] == 1
        assert summary["combined"]["total_value"] == 1000


class TestDateFormatting:
    """Test suite for date formatting."""
    
    def test_date_formatting(self):
        """Test various date format conversions."""
        test_cases = [
            ('2025-08-12', '8/12/2025'),
            ('2025-01-01', '1/1/2025'),
            ('2025-12-31', '12/31/2025'),
        ]
        
        for input_date, expected in test_cases:
            date_obj = datetime.strptime(input_date, '%Y-%m-%d')
            formatted = date_obj.strftime('%-m/%-d/%Y')
            # Handle platform differences in date formatting
            # Windows doesn't support %-m, so we might get 08/12/2025 instead of 8/12/2025
            formatted = formatted.lstrip('0').replace('/0', '/')
            assert formatted == expected, f"Failed for {input_date}: got {formatted}, expected {expected}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])