import requests
import logging
import os
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from pydantic import ValidationError
import streamlit as st

# Import the existing models
from freightviewslack.pydatamodel import Model

# Load environment variables from .env file if available
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # dotenv not installed, skip

class FreightDataService:
    """Service class for handling FreightView API interactions and data processing."""
    
    def __init__(self, client_id: str, client_secret: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self.base_url = "https://api.freightview.com/v2.0"
        self.logger = logging.getLogger(__name__)
        
    def get_auth_headers(self) -> Optional[Dict[str, str]]:
        """Get authentication headers for API requests."""
        token_url = f"{self.base_url}/auth/token"
        
        payload = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "grant_type": "client_credentials"
        }
        
        try:
            response = requests.post(token_url, json=payload)
            if response.status_code == 200:
                token_data = response.json()
                access_token = token_data.get("access_token")
                return {"Authorization": f"Bearer {access_token}"}
            else:
                self.logger.error(f"Auth failed: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            self.logger.error(f"Auth error: {str(e)}")
            return None
    
    @st.cache_data(ttl=900)  # Cache for 15 minutes
    def fetch_shipments(_self, status: str = "picked-up") -> Optional[Model]:
        """Fetch shipments from FreightView API with caching."""
        headers = _self.get_auth_headers()
        if not headers:
            return None
            
        url = f"{_self.base_url}/shipments?status={status}"
        
        try:
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                data = response.json()
                return Model.model_validate(data)
            else:
                _self.logger.error(f"API request failed: {response.status_code}")
                return None
        except ValidationError as e:
            _self.logger.error(f"Data validation error: {str(e)}")
            return None
        except Exception as e:
            _self.logger.error(f"Request error: {str(e)}")
            return None
    
    def process_inbound_data(self, model: Model) -> List[Dict]:
        """Process inbound shipment data for dashboard display."""
        table_data = []
        
        if not model or not model.shipments:
            return table_data
            
        for shipment in model.shipments:
            if shipment.direction == "inbound":
                try:
                    # Extract basic shipment info
                    consignee = shipment.locations[0].company[:50] if shipment.locations else "N/A"
                    po_number = "N/A"
                    
                    # Safely extract PO number
                    try:
                        if shipment.locations and len(shipment.locations) > 1 and shipment.locations[1].refNums:
                            po_number = shipment.locations[1].refNums[0].value or "N/A"
                    except (IndexError, AttributeError):
                        pass
                    
                    # Extract dates
                    delivery_est = shipment.tracking.deliveryDateEstimate.date() if shipment.tracking.deliveryDateEstimate else "N/A"
                    last_update = shipment.tracking.lastUpdatedDate.date() if shipment.tracking.lastUpdatedDate else "N/A"
                    
                    # Extract carrier and tracking
                    carrier_name = "Unknown"
                    if shipment.selectedQuote and shipment.selectedQuote.assetCarrierName:
                        carrier_name = shipment.selectedQuote.assetCarrierName[:30]
                    
                    tracking_number = shipment.tracking.trackingNumber or "N/A"
                    
                    # Calculate cost metrics
                    price = None
                    weight = None
                    cost_per_lb = None
                    
                    try:
                        if shipment.selectedQuote and shipment.selectedQuote.amount:
                            price = shipment.selectedQuote.amount
                        if shipment.equipment and shipment.equipment.weight:
                            weight = shipment.equipment.weight
                        
                        if price and weight and weight > 0:
                            cost_per_lb = round(price / weight, 2)
                    except (AttributeError, ZeroDivisionError):
                        pass
                    
                    table_data.append({
                        "Shipment ID": shipment.shipmentId,
                        "Consignee": consignee,
                        "PO Number": po_number,
                        "Delivery Est": delivery_est,
                        "Last Update": last_update,
                        "Carrier Name": carrier_name,
                        "Tracking": tracking_number,
                        "Price": price,
                        "Weight": weight,
                        "Cost per lb": cost_per_lb,
                        "Status": shipment.status
                    })
                    
                except Exception as e:
                    self.logger.error(f"Error processing inbound shipment {shipment.shipmentId}: {str(e)}")
                    continue
                    
        return table_data
    
    def process_outbound_data(self, model: Model) -> List[Dict]:
        """Process outbound shipment data for dashboard display."""
        table_data = []
        
        if not model or not model.shipments:
            return table_data
            
        for shipment in model.shipments:
            if shipment.direction == "outbound":
                try:
                    # Extract basic shipment info
                    consignor = "N/A"
                    if shipment.locations and len(shipment.locations) > 1:
                        consignor = shipment.locations[1].company[:50]
                    
                    # Safely extract invoice number
                    inv_number = "N/A"
                    try:
                        if shipment.locations and shipment.locations[0].refNums:
                            inv_number = shipment.locations[0].refNums[0].value or "N/A"
                    except (IndexError, AttributeError):
                        pass
                    
                    # Extract dates
                    delivery_est = shipment.tracking.deliveryDateEstimate.date() if shipment.tracking.deliveryDateEstimate else "N/A"
                    last_update = shipment.tracking.lastUpdatedDate.date() if shipment.tracking.lastUpdatedDate else "N/A"
                    
                    # Extract carrier and tracking
                    carrier_name = "Unknown"
                    if shipment.selectedQuote and shipment.selectedQuote.assetCarrierName:
                        carrier_name = shipment.selectedQuote.assetCarrierName[:30]
                    
                    tracking_number = shipment.tracking.trackingNumber or "N/A"
                    
                    # Extract contact email
                    email = "N/A"
                    if shipment.locations and len(shipment.locations) > 1:
                        email = shipment.locations[1].contactEmail or "N/A"
                    
                    # Calculate cost metrics
                    price = None
                    weight = None
                    cost_per_lb = None
                    
                    try:
                        if shipment.selectedQuote and shipment.selectedQuote.amount:
                            price = shipment.selectedQuote.amount
                        if shipment.equipment and shipment.equipment.weight:
                            weight = shipment.equipment.weight
                        
                        if price and weight and weight > 0:
                            cost_per_lb = round(price / weight, 2)
                    except (AttributeError, ZeroDivisionError):
                        pass
                    
                    table_data.append({
                        "Shipment ID": shipment.shipmentId,
                        "Consignor": consignor,
                        "Inv Number": inv_number,
                        "Delivery Est": delivery_est,
                        "Last Update": last_update,
                        "Carrier Name": carrier_name,
                        "Tracking": tracking_number,
                        "Email": email,
                        "Price": price,
                        "Weight": weight,
                        "Cost per lb": cost_per_lb,
                        "Status": shipment.status
                    })
                    
                except Exception as e:
                    self.logger.error(f"Error processing outbound shipment {shipment.shipmentId}: {str(e)}")
                    continue
                    
        return table_data
    
    def get_summary_metrics(self, inbound_data: List[Dict], outbound_data: List[Dict]) -> Dict:
        """Calculate summary metrics for the dashboard."""
        total_shipments = len(inbound_data) + len(outbound_data)
        
        # Calculate average cost per lb
        costs_per_lb = []
        total_cost = 0
        total_weight = 0
        
        for data in inbound_data + outbound_data:
            if data.get("Cost per lb") is not None:
                costs_per_lb.append(data["Cost per lb"])
            if data.get("Price") is not None:
                total_cost += data["Price"]
            if data.get("Weight") is not None:
                total_weight += data["Weight"]
        
        avg_cost_per_lb = sum(costs_per_lb) / len(costs_per_lb) if costs_per_lb else 0
        
        # Count delivered shipments (this would need more status analysis in real implementation)
        delivered_count = sum(1 for data in inbound_data + outbound_data if data.get("Status") == "delivered")
        delivery_rate = (delivered_count / total_shipments * 100) if total_shipments > 0 else 0
        
        return {
            "total_shipments": total_shipments,
            "inbound_count": len(inbound_data),
            "outbound_count": len(outbound_data),
            "avg_cost_per_lb": round(avg_cost_per_lb, 2),
            "total_cost": round(total_cost, 2),
            "total_weight": total_weight,
            "delivery_rate": round(delivery_rate, 1)
        }