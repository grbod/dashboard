"""
Mock data and test fixtures for FreightView Dashboard testing.
"""

from datetime import datetime, timedelta
import json

# Sample API auth response
MOCK_AUTH_RESPONSE = {
    "access_token": "mock_access_token_12345",
    "token_type": "Bearer",
    "expires_in": 3600
}

# Sample shipments API response
MOCK_SHIPMENTS_RESPONSE = {
    "shipments": [
        {
            "shipmentId": "SHIP001",
            "status": "picked-up",
            "direction": "inbound",
            "locations": [
                {
                    "company": "ABC Manufacturing Co",
                    "address": "123 Industrial Blvd",
                    "refNums": [{"value": "PO12345"}],
                    "contactEmail": "shipping@abc.com"
                },
                {
                    "company": "XYZ Warehouse",
                    "address": "456 Storage Way",
                    "refNums": [{"value": "REF67890"}],
                    "contactEmail": "receiving@xyz.com"
                }
            ],
            "equipment": {
                "weight": 1500,
                "weightUOM": "LBS"
            },
            "selectedQuote": {
                "quoteId": "Q001",
                "assetCarrierName": "FastFreight Logistics",
                "amount": 750.50,
                "status": "selected"
            },
            "tracking": {
                "deliveryDateEstimate": (datetime.now() + timedelta(days=3)).isoformat(),
                "lastUpdatedDate": datetime.now().isoformat(),
                "trackingNumber": "1Z999AA1234567890",
                "status": "in-transit"
            },
            "refNums": []
        },
        {
            "shipmentId": "SHIP002", 
            "status": "picked-up",
            "direction": "outbound",
            "locations": [
                {
                    "company": "Customer Solutions Inc",
                    "address": "789 Business Park",
                    "refNums": [{"value": "INV98765"}],
                    "contactEmail": "orders@customer.com"
                },
                {
                    "company": "Our Warehouse",
                    "address": "321 Distribution Center",
                    "refNums": [{"value": "OUT54321"}],
                    "contactEmail": "shipping@ourcompany.com"
                }
            ],
            "equipment": {
                "weight": 2800,
                "weightUOM": "LBS"
            },
            "selectedQuote": {
                "quoteId": "Q002",
                "assetCarrierName": "Reliable Transport",
                "amount": 1250.75,
                "status": "selected"
            },
            "tracking": {
                "deliveryDateEstimate": (datetime.now() + timedelta(days=2)).isoformat(),
                "lastUpdatedDate": (datetime.now() - timedelta(hours=2)).isoformat(),
                "trackingNumber": "1Z888BB9876543210",
                "status": "in-transit"
            },
            "refNums": []
        },
        {
            "shipmentId": "SHIP003",
            "status": "picked-up", 
            "direction": "inbound",
            "locations": [
                {
                    "company": "Steel Works LLC",
                    "address": "555 Heavy Industry Dr",
                    "refNums": [{"value": "PO55555"}],
                    # Note: Missing contactEmail to test validation fix
                },
                {
                    "company": "Main Warehouse",
                    "address": "100 Central Ave",
                    "refNums": [{"value": "REC33333"}],
                    "contactEmail": "receiving@main.com"
                }
            ],
            "equipment": {
                "weight": 5000,
                "weightUOM": "LBS"
            },
            "selectedQuote": {
                "quoteId": "Q003",
                "assetCarrierName": "Heavy Haul Express",
                "amount": 2100.00,
                "status": "selected"
            },
            "tracking": {
                "deliveryDateEstimate": (datetime.now() + timedelta(days=5)).isoformat(),
                "lastUpdatedDate": (datetime.now() - timedelta(minutes=30)).isoformat(),
                "trackingNumber": "HH777CC5555666777",
                "status": "in-transit"
            },
            "refNums": []
        }
    ]
}

# Test data with edge cases
MOCK_EDGE_CASES_RESPONSE = {
    "shipments": [
        {
            "shipmentId": "EDGE001",
            "status": "picked-up",
            "direction": "inbound",
            "locations": [
                {
                    "company": "Company With No Email",
                    "address": "No Email Street",
                    "refNums": [],  # Empty refNums
                },
                {
                    "company": "Second Location",
                    "address": "Second Address",
                    "refNums": [{"value": "REF123"}],
                    "contactEmail": "test@email.com"
                }
            ],
            "equipment": {
                "weight": 100,
                "weightUOM": "LBS"
            },
            "selectedQuote": {
                "quoteId": "EDGE_Q001",
                "assetCarrierName": None,  # Null carrier name
                "amount": None,  # Null amount
                "status": "selected"
            },
            "tracking": {
                "deliveryDateEstimate": None,  # Null delivery date
                "lastUpdatedDate": datetime.now().isoformat(),
                "trackingNumber": None,  # Null tracking number
                "status": "unknown"
            },
            "refNums": []
        }
    ]
}

def get_mock_api_responses():
    """Return dictionary of mock API responses for testing."""
    return {
        "auth": MOCK_AUTH_RESPONSE,
        "shipments": MOCK_SHIPMENTS_RESPONSE,
        "edge_cases": MOCK_EDGE_CASES_RESPONSE
    }

def save_test_data_to_files():
    """Save test data to JSON files for external testing."""
    responses = get_mock_api_responses()
    
    for name, data in responses.items():
        filename = f"test_{name}_response.json"
        with open(filename, 'w') as f:
            json.dump(data, f, indent=2, default=str)
        print(f"Saved {filename}")

if __name__ == "__main__":
    save_test_data_to_files()