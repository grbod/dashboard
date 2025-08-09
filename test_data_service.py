"""
Unit tests for FreightView data service.
"""

import pytest
import requests_mock
from unittest.mock import patch, MagicMock
from datetime import datetime
import json

# Import the modules to test
from data_service import FreightDataService
from freightviewslack.pydatamodel import Model
from test_data import get_mock_api_responses

class TestFreightDataService:
    
    def setup_method(self):
        """Set up test fixtures before each test method."""
        self.client_id = "test_client_id"
        self.client_secret = "test_client_secret"
        self.service = FreightDataService(self.client_id, self.client_secret)
        self.mock_responses = get_mock_api_responses()
    
    @requests_mock.Mocker()
    def test_get_auth_headers_success(self, m):
        """Test successful authentication."""
        # Mock the auth endpoint
        m.post(
            "https://api.freightview.com/v2.0/auth/token",
            json=self.mock_responses["auth"],
            status_code=200
        )
        
        headers = self.service.get_auth_headers()
        
        assert headers is not None
        assert headers["Authorization"] == "Bearer mock_access_token_12345"
        
        # Verify the request was made with correct payload
        assert m.last_request.json() == {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "grant_type": "client_credentials"
        }
    
    @requests_mock.Mocker()
    def test_get_auth_headers_failure(self, m):
        """Test authentication failure."""
        # Mock failed auth response
        m.post(
            "https://api.freightview.com/v2.0/auth/token",
            json={"error": "invalid_client"},
            status_code=401
        )
        
        headers = self.service.get_auth_headers()
        
        assert headers is None
    
    @requests_mock.Mocker()
    @patch('streamlit.cache_data')
    def test_fetch_shipments_success(self, mock_cache, m):
        """Test successful shipment fetching."""
        # Mock cache decorator to not interfere with testing
        mock_cache.return_value = lambda func: func
        
        # Mock auth endpoint
        m.post(
            "https://api.freightview.com/v2.0/auth/token", 
            json=self.mock_responses["auth"],
            status_code=200
        )
        
        # Mock shipments endpoint
        m.get(
            "https://api.freightview.com/v2.0/shipments?status=picked-up",
            json=self.mock_responses["shipments"],
            status_code=200
        )
        
        model = self.service.fetch_shipments("picked-up")
        
        assert model is not None
        assert isinstance(model, Model)
        assert len(model.shipments) == 3
        assert model.shipments[0].shipmentId == "SHIP001"
        assert model.shipments[1].direction == "outbound"
    
    @requests_mock.Mocker()
    @patch('streamlit.cache_data')
    def test_fetch_shipments_api_failure(self, mock_cache, m):
        """Test shipment fetching when API returns error."""
        mock_cache.return_value = lambda func: func
        
        # Mock auth endpoint
        m.post(
            "https://api.freightview.com/v2.0/auth/token",
            json=self.mock_responses["auth"],
            status_code=200
        )
        
        # Mock failed shipments endpoint
        m.get(
            "https://api.freightview.com/v2.0/shipments?status=picked-up",
            json={"error": "server_error"},
            status_code=500
        )
        
        model = self.service.fetch_shipments("picked-up")
        
        assert model is None
    
    def test_process_inbound_data(self):
        """Test processing inbound shipment data."""
        # Create model from mock data
        model = Model.model_validate(self.mock_responses["shipments"])
        
        inbound_data = self.service.process_inbound_data(model)
        
        # Should have 2 inbound shipments (SHIP001 and SHIP003)
        assert len(inbound_data) == 2
        
        # Check first inbound shipment
        ship1 = inbound_data[0]
        assert ship1["Shipment ID"] == "SHIP001"
        assert ship1["Consignee"] == "ABC Manufacturing Co"
        assert ship1["PO Number"] == "PO12345"
        assert ship1["Carrier Name"] == "FastFreight Logistics"
        assert ship1["Price"] == 750.50
        assert ship1["Weight"] == 1500
        assert ship1["Cost per lb"] == 0.50  # 750.50 / 1500 = 0.50
        
        # Check second inbound shipment (edge case with missing email)
        ship2 = inbound_data[1]
        assert ship2["Shipment ID"] == "SHIP003"
        assert ship2["Consignee"] == "Steel Works LLC"
        assert ship2["Cost per lb"] == 0.42  # 2100 / 5000 = 0.42
    
    def test_process_outbound_data(self):
        """Test processing outbound shipment data."""
        model = Model.model_validate(self.mock_responses["shipments"])
        
        outbound_data = self.service.process_outbound_data(model)
        
        # Should have 1 outbound shipment (SHIP002)
        assert len(outbound_data) == 1
        
        ship = outbound_data[0]
        assert ship["Shipment ID"] == "SHIP002"
        assert ship["Consignor"] == "Our Warehouse"
        assert ship["Inv Number"] == "INV98765"
        assert ship["Carrier Name"] == "Reliable Transport"
        assert ship["Email"] == "shipping@ourcompany.com"
        assert ship["Price"] == 1250.75
        assert ship["Weight"] == 2800
        assert ship["Cost per lb"] == 0.45  # 1250.75 / 2800 ≈ 0.45
    
    def test_process_edge_cases(self):
        """Test processing shipments with missing/null data."""
        model = Model.model_validate(self.mock_responses["edge_cases"])
        
        inbound_data = self.service.process_inbound_data(model)
        
        assert len(inbound_data) == 1
        
        ship = inbound_data[0]
        assert ship["Shipment ID"] == "EDGE001"
        assert ship["Consignee"] == "Company With No Email"
        assert ship["PO Number"] == "N/A"  # Empty refNums
        assert ship["Carrier Name"] == "Unknown"  # Null carrier name
        assert ship["Price"] is None  # Null amount
        assert ship["Cost per lb"] is None  # Can't calculate with null price
        assert ship["Tracking"] == "N/A"  # Null tracking number
    
    def test_get_summary_metrics(self):
        """Test calculation of summary metrics."""
        model = Model.model_validate(self.mock_responses["shipments"])
        
        inbound_data = self.service.process_inbound_data(model)
        outbound_data = self.service.process_outbound_data(model)
        
        metrics = self.service.get_summary_metrics(inbound_data, outbound_data)
        
        assert metrics["total_shipments"] == 3
        assert metrics["inbound_count"] == 2
        assert metrics["outbound_count"] == 1
        assert metrics["total_cost"] == 4101.25  # 750.50 + 1250.75 + 2100.00
        assert metrics["total_weight"] == 9300  # 1500 + 2800 + 5000
        assert metrics["avg_cost_per_lb"] == 0.46  # Average of 0.50, 0.45, 0.42
    
    def test_empty_shipments(self):
        """Test handling empty shipment responses."""
        empty_model = Model(shipments=[])
        
        inbound_data = self.service.process_inbound_data(empty_model)
        outbound_data = self.service.process_outbound_data(empty_model)
        metrics = self.service.get_summary_metrics(inbound_data, outbound_data)
        
        assert len(inbound_data) == 0
        assert len(outbound_data) == 0
        assert metrics["total_shipments"] == 0
        assert metrics["avg_cost_per_lb"] == 0
        assert metrics["total_cost"] == 0

def run_tests():
    """Run all tests manually without pytest."""
    test_instance = TestFreightDataService()
    
    test_methods = [
        method for method in dir(test_instance) 
        if method.startswith('test_') and callable(getattr(test_instance, method))
    ]
    
    passed = 0
    failed = 0
    
    for method_name in test_methods:
        try:
            test_instance.setup_method()
            method = getattr(test_instance, method_name)
            method()
            print(f"✅ {method_name} - PASSED")
            passed += 1
        except Exception as e:
            print(f"❌ {method_name} - FAILED: {str(e)}")
            failed += 1
    
    print(f"\n📊 Test Results: {passed} passed, {failed} failed")
    return failed == 0

if __name__ == "__main__":
    # Run tests
    success = run_tests()
    exit(0 if success else 1)