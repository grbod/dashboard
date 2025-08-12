"""
Unified data service for both FreightView and ShipStation APIs.
"""

import requests
import logging
import os
import base64
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from pydantic import ValidationError
import streamlit as st

# Import existing models and services
from data_service import FreightDataService
from shipstation_models import ShipStationOrdersResponse, ShipStationShipmentsResponse
from freightviewslack.pydatamodel import Model
from airtable_service import AirtableService

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

class ShipStationService:
    """Service class for ShipStation API interactions."""
    
    def __init__(self, api_key: str, api_secret: str):
        self.api_key = api_key
        self.api_secret = api_secret
        self.base_url = "https://ssapi.shipstation.com"
        self.logger = logging.getLogger(__name__)
        
        # Create basic auth header
        credentials = f"{api_key}:{api_secret}"
        encoded_credentials = base64.b64encode(credentials.encode()).decode()
        self.headers = {
            "Authorization": f"Basic {encoded_credentials}",
            "Content-Type": "application/json"
        }
    
    @st.cache_data(ttl=900)  # Cache for 15 minutes
    def fetch_orders(_self, status: str = "awaiting_shipment", days_back: int = 30) -> Optional[ShipStationOrdersResponse]:
        """Fetch orders from ShipStation API."""
        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)
        
        params = {
            "orderStatus": status,
            "createDateStart": start_date.strftime("%Y-%m-%d"),
            "createDateEnd": end_date.strftime("%Y-%m-%d"),
            "pageSize": 500  # Max page size
        }
        
        try:
            url = f"{_self.base_url}/orders"
            response = requests.get(url, headers=_self.headers, params=params)
            
            if response.status_code == 200:
                data = response.json()
                return ShipStationOrdersResponse.model_validate(data)
            else:
                _self.logger.error(f"ShipStation API request failed: {response.status_code}")
                return None
                
        except ValidationError as e:
            _self.logger.error(f"ShipStation data validation error: {str(e)}")
            return None
        except Exception as e:
            _self.logger.error(f"ShipStation request error: {str(e)}")
            return None
    
    @st.cache_data(ttl=900)
    def fetch_stores(_self) -> Optional[dict]:
        """Fetch all stores from ShipStation API."""
        try:
            url = f"{_self.base_url}/stores"
            response = requests.get(url, headers=_self.headers)
            
            if response.status_code == 200:
                return response.json()
            else:
                _self.logger.error(f"ShipStation stores API failed: {response.status_code}")
                return None
                
        except Exception as e:
            _self.logger.error(f"ShipStation stores fetch error: {str(e)}")
            return None
    
    @st.cache_data(ttl=900)
    def fetch_shipments(_self, days_back: int = 30) -> Optional[ShipStationShipmentsResponse]:
        """Fetch shipments from ShipStation API."""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)
        
        params = {
            "createDateStart": start_date.strftime("%Y-%m-%d"),
            "createDateEnd": end_date.strftime("%Y-%m-%d"),
            "pageSize": 500
        }
        
        try:
            url = f"{_self.base_url}/shipments"
            response = requests.get(url, headers=_self.headers, params=params)
            
            if response.status_code == 200:
                data = response.json()
                return ShipStationShipmentsResponse.model_validate(data)
            else:
                _self.logger.error(f"ShipStation shipments API failed: {response.status_code}")
                return None
                
        except Exception as e:
            _self.logger.error(f"ShipStation shipments error: {str(e)}")
            return None

class UnifiedDataService:
    """Unified service for FreightView, ShipStation, and Airtable data."""
    
    def __init__(self, fv_client_id: str, fv_client_secret: str, ss_api_key: str, ss_api_secret: str,
                 at_api_key: Optional[str] = None, at_base_id: Optional[str] = None, at_table_name: Optional[str] = None):
        self.freight_service = FreightDataService(fv_client_id, fv_client_secret)
        self.shipstation_service = ShipStationService(ss_api_key, ss_api_secret)
        
        # Initialize Airtable service if credentials provided
        self.airtable_service = None
        if at_api_key and at_base_id and at_table_name:
            self.airtable_service = AirtableService(at_api_key, at_base_id, at_table_name)
        
        self.logger = logging.getLogger(__name__)
    
    def fetch_all_data(self) -> Dict:
        """Fetch data from all services."""
        data = {
            "freightview": {
                "shipments": None,
                "error": None
            },
            "shipstation": {
                "orders": None,
                "shipments": None,
                "stores": None,
                "error": None
            },
            "airtable": {
                "upcoming_pickups": None,
                "error": None
            }
        }
        
        # Fetch FreightView data
        try:
            fv_shipments = self.freight_service.fetch_shipments("picked-up")
            data["freightview"]["shipments"] = fv_shipments
        except Exception as e:
            data["freightview"]["error"] = str(e)
            self.logger.error(f"FreightView fetch error: {e}")
        
        # Fetch ShipStation data
        try:
            ss_orders = self.shipstation_service.fetch_orders("awaiting_shipment")
            ss_shipments = self.shipstation_service.fetch_shipments()
            ss_stores = self.shipstation_service.fetch_stores()
            data["shipstation"]["orders"] = ss_orders
            data["shipstation"]["shipments"] = ss_shipments
            data["shipstation"]["stores"] = ss_stores
        except Exception as e:
            data["shipstation"]["error"] = str(e)
            self.logger.error(f"ShipStation fetch error: {e}")
        
        # Fetch Airtable data
        if self.airtable_service:
            try:
                upcoming_pickups = self.airtable_service.fetch_upcoming_pickups()
                data["airtable"]["upcoming_pickups"] = upcoming_pickups
            except Exception as e:
                data["airtable"]["error"] = str(e)
                self.logger.error(f"Airtable fetch error: {e}")
        
        return data
    
    def process_shipstation_orders(self, orders_response: ShipStationOrdersResponse, stores_data: Optional[dict] = None) -> List[Dict]:
        """Process ShipStation orders for display."""
        if not orders_response or not orders_response.orders:
            return []
        
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
        if stores_data:
            for store in stores_data:
                if isinstance(store, dict):
                    store_id = store.get('storeId')
                    store_name = store.get('storeName')
                    if store_id and store_name:
                        store_id_to_name[str(store_id)] = store_name
        
        processed_orders = []
        
        for order in orders_response.orders:
            try:
                # Calculate total items
                total_items = sum(item.quantity or 0 for item in order.items) if order.items else 0
                
                # Get store information
                store_name = "Unknown Store"
                store_id = None
                
                # Check advancedOptions for store ID
                if order.advancedOptions:
                    store_id = order.advancedOptions.get('storeId')
                
                # Get the store name from our mapping
                if store_id and str(store_id) in store_id_to_name:
                    store_name = store_id_to_name[str(store_id)]
                elif store_id:
                    store_name = f"Store {store_id}"
                
                # Clean up and apply abbreviation
                store_name = str(store_name).strip()
                store_name = STORE_ABBREVIATIONS.get(store_name, store_name)
                
                # Process weight - convert to oz/lbs display
                weight_display = "N/A"
                if order.weight and order.weight.value:
                    weight_value = order.weight.value
                    weight_unit = order.weight.units or "LBS"
                    
                    # Convert to ounces first if needed
                    if weight_unit.upper() in ["LBS", "LB", "POUNDS"]:
                        weight_in_oz = weight_value * 16
                    elif weight_unit.upper() in ["OZ", "OUNCES"]:
                        weight_in_oz = weight_value
                    else:
                        # Default to showing original value with unit
                        weight_display = f"{weight_value:.1f} {weight_unit}"
                        weight_in_oz = None
                    
                    # Format based on weight
                    if weight_in_oz is not None:
                        if weight_in_oz >= 16:
                            # Display in pounds
                            weight_in_lbs = weight_in_oz / 16
                            weight_display = f"{weight_in_lbs:.1f} lbs"
                        else:
                            # Display in ounces
                            weight_display = f"{weight_in_oz:.1f} oz"
                
                # Format order date to MM/DD/YYYY
                order_date_formatted = order.orderDate
                if order.orderDate:
                    try:
                        # Parse ISO date format
                        date_obj = datetime.fromisoformat(order.orderDate.replace('Z', '+00:00').split('.')[0])
                        order_date_formatted = date_obj.strftime("%-m/%-d/%Y")
                    except:
                        # Fallback to original if parsing fails
                        order_date_formatted = order.orderDate
                
                # Get shipping info
                ship_to_company = ""
                ship_to_city = ""
                if order.shipTo:
                    ship_to_company = order.shipTo.company or order.shipTo.name or ""
                    ship_to_city = order.shipTo.city or ""
                
                processed_orders.append({
                    "Order ID": order.orderNumber,
                    "Store": store_name,  # Add store column
                    "Status": order.orderStatus,
                    "Customer": order.customerEmail or "N/A",
                    "Ship To": f"{ship_to_company} ({ship_to_city})",
                    "Items": total_items,
                    "Order Total": order.orderTotal or 0,
                    "Weight": weight_display,
                    "Order Date": order_date_formatted,
                    "Ship Date": order.shipDate or "Not Shipped",
                    "Carrier": order.carrierCode or "Not Assigned",
                    "Service": order.requestedShippingService or "N/A",
                    "_order_date_raw": order.orderDate  # Keep raw date for age calculation
                })
                
            except Exception as e:
                self.logger.error(f"Error processing ShipStation order {order.orderId}: {str(e)}")
                continue
        
        return processed_orders
    
    def process_shipstation_shipments(self, shipments_response: ShipStationShipmentsResponse) -> List[Dict]:
        """Process ShipStation shipments for display."""
        if not shipments_response or not shipments_response.shipments:
            return []
        
        processed_shipments = []
        
        for shipment in shipments_response.shipments:
            try:
                # Get weight info
                weight = 0
                weight_unit = "LBS"
                if shipment.weight:
                    weight = shipment.weight.value or 0
                    weight_unit = shipment.weight.units or "LBS"
                
                # Get shipping address
                ship_to = ""
                if shipment.shipTo:
                    company = shipment.shipTo.company or shipment.shipTo.name or ""
                    city = shipment.shipTo.city or ""
                    ship_to = f"{company} ({city})"
                
                processed_shipments.append({
                    "Shipment ID": shipment.shipmentId,
                    "Order Number": shipment.orderNumber,
                    "Customer": shipment.customerEmail or "N/A",
                    "Ship To": ship_to,
                    "Tracking": shipment.trackingNumber or "No Tracking",
                    "Carrier": shipment.carrierCode or "Unknown",
                    "Service": shipment.serviceCode or "N/A",
                    "Weight": weight,
                    "Weight Unit": weight_unit,
                    "Cost": shipment.shipmentCost or 0,
                    "Ship Date": shipment.shipDate,
                    "Voided": shipment.voided or False
                })
                
            except Exception as e:
                self.logger.error(f"Error processing ShipStation shipment {shipment.shipmentId}: {str(e)}")
                continue
        
        return processed_shipments
    
    def process_airtable_pickups(self, pickups_data: Optional[List]) -> List[Dict]:
        """Process Airtable upcoming pickups for display."""
        if not pickups_data or not self.airtable_service:
            return []
        
        return self.airtable_service.process_pickup_data(pickups_data)
    
    def get_unified_summary(self, all_data: Dict) -> Dict:
        """Calculate unified summary metrics."""
        summary = {
            "freightview": {
                "total_shipments": 0,
                "total_cost": 0,
                "avg_cost_per_lb": 0,
                "status": "disconnected"
            },
            "shipstation": {
                "pending_orders": 0,
                "shipped_orders": 0,
                "total_order_value": 0,
                "avg_order_value": 0,
                "status": "disconnected"
            },
            "airtable": {
                "upcoming_pickups": 0,
                "total_pickup_value": 0,
                "status": "disconnected"
            },
            "combined": {
                "total_active_shipments": 0,
                "total_value": 0
            }
        }
        
        # Process FreightView data
        if all_data["freightview"]["shipments"] and not all_data["freightview"]["error"]:
            fv_inbound = self.freight_service.process_inbound_data(all_data["freightview"]["shipments"])
            fv_outbound = self.freight_service.process_outbound_data(all_data["freightview"]["shipments"])
            fv_metrics = self.freight_service.get_summary_metrics(fv_inbound, fv_outbound)
            
            summary["freightview"] = {
                "total_shipments": fv_metrics["total_shipments"],
                "total_cost": fv_metrics["total_cost"],
                "avg_cost_per_lb": fv_metrics["avg_cost_per_lb"],
                "status": "connected"
            }
        
        # Process ShipStation data
        if all_data["shipstation"]["orders"] and not all_data["shipstation"]["error"]:
            ss_orders = self.process_shipstation_orders(all_data["shipstation"]["orders"], all_data["shipstation"]["stores"])
            ss_shipped = self.process_shipstation_shipments(all_data["shipstation"]["shipments"]) if all_data["shipstation"]["shipments"] else []
            
            pending_orders = len(ss_orders)
            shipped_orders = len(ss_shipped)
            total_order_value = sum(order.get("Order Total", 0) for order in ss_orders)
            avg_order_value = total_order_value / pending_orders if pending_orders > 0 else 0
            
            summary["shipstation"] = {
                "pending_orders": pending_orders,
                "shipped_orders": shipped_orders,
                "total_order_value": total_order_value,
                "avg_order_value": avg_order_value,
                "status": "connected"
            }
        
        # Process Airtable data
        if all_data["airtable"]["upcoming_pickups"] and not all_data["airtable"]["error"]:
            pickups_summary = self.airtable_service.get_pickup_summary(all_data["airtable"]["upcoming_pickups"]) if self.airtable_service else {}
            
            summary["airtable"] = {
                "upcoming_pickups": pickups_summary.get("total_pickups", 0),
                "unique_pos": pickups_summary.get("unique_pos", 0),
                "total_pickup_value": pickups_summary.get("total_value", 0),
                "by_status": pickups_summary.get("by_status", {}),
                "status": "connected"
            }
        
        # Combined metrics
        summary["combined"]["total_active_shipments"] = (
            summary["freightview"]["total_shipments"] + 
            summary["shipstation"]["pending_orders"] +
            summary["airtable"]["upcoming_pickups"]
        )
        summary["combined"]["total_value"] = (
            summary["freightview"]["total_cost"] + 
            summary["shipstation"]["total_order_value"] +
            summary["airtable"]["total_pickup_value"]
        )
        
        return summary