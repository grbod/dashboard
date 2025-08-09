"""
Pydantic data models for ShipStation API responses.
"""

from __future__ import annotations
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

class ShipStationAddress(BaseModel):
    name: Optional[str] = None
    company: Optional[str] = None
    street1: Optional[str] = None
    street2: Optional[str] = None
    street3: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    postalCode: Optional[str] = None
    country: Optional[str] = None
    phone: Optional[str] = None
    residential: Optional[bool] = None

class ShipStationWeight(BaseModel):
    value: Optional[float] = None
    units: Optional[str] = None

class ShipStationDimensions(BaseModel):
    units: Optional[str] = None
    length: Optional[float] = None
    width: Optional[float] = None
    height: Optional[float] = None

class ShipStationOrderItem(BaseModel):
    orderItemId: Optional[int] = None
    lineItemKey: Optional[str] = None
    sku: Optional[str] = None
    name: Optional[str] = None
    imageUrl: Optional[str] = None
    weight: Optional[ShipStationWeight] = None
    quantity: Optional[int] = None
    unitPrice: Optional[float] = None
    taxAmount: Optional[float] = None
    shippingAmount: Optional[float] = None
    warehouseLocation: Optional[str] = None
    options: List = []
    productId: Optional[int] = None
    fulfillmentSku: Optional[str] = None
    adjustment: Optional[bool] = None
    upc: Optional[str] = None
    createDate: Optional[str] = None
    modifyDate: Optional[str] = None

class ShipStationOrder(BaseModel):
    orderId: Optional[int] = None
    orderNumber: Optional[str] = None
    orderKey: Optional[str] = None
    orderDate: Optional[str] = None
    createDate: Optional[str] = None
    modifyDate: Optional[str] = None
    paymentDate: Optional[str] = None
    shipByDate: Optional[str] = None
    orderStatus: Optional[str] = None
    customerId: Optional[int] = None
    customerUsername: Optional[str] = None
    customerEmail: Optional[str] = None
    billTo: Optional[ShipStationAddress] = None
    shipTo: Optional[ShipStationAddress] = None
    items: List[ShipStationOrderItem] = []
    orderTotal: Optional[float] = None
    amountPaid: Optional[float] = None
    taxAmount: Optional[float] = None
    shippingAmount: Optional[float] = None
    customerNotes: Optional[str] = None
    internalNotes: Optional[str] = None
    gift: Optional[bool] = None
    giftMessage: Optional[str] = None
    paymentMethod: Optional[str] = None
    requestedShippingService: Optional[str] = None
    carrierCode: Optional[str] = None
    serviceCode: Optional[str] = None
    packageCode: Optional[str] = None
    confirmation: Optional[str] = None
    shipDate: Optional[str] = None
    holdUntilDate: Optional[str] = None
    weight: Optional[ShipStationWeight] = None
    dimensions: Optional[ShipStationDimensions] = None
    insuranceOptions: Optional[dict] = None
    internationalOptions: Optional[dict] = None
    advancedOptions: Optional[dict] = None
    tagIds: Optional[List] = None

class ShipStationOrdersResponse(BaseModel):
    orders: List[ShipStationOrder] = []
    total: Optional[int] = None
    page: Optional[int] = None
    pages: Optional[int] = None

class ShipStationShipment(BaseModel):
    shipmentId: Optional[int] = None
    orderId: Optional[int] = None
    orderKey: Optional[str] = None
    userId: Optional[str] = None
    customerEmail: Optional[str] = None
    orderNumber: Optional[str] = None
    createDate: Optional[str] = None
    shipDate: Optional[str] = None
    shipmentCost: Optional[float] = None
    insuranceCost: Optional[float] = None
    trackingNumber: Optional[str] = None
    isReturnLabel: Optional[bool] = None
    batchNumber: Optional[str] = None
    carrierCode: Optional[str] = None
    serviceCode: Optional[str] = None
    packageCode: Optional[str] = None
    confirmation: Optional[str] = None
    warehouseId: Optional[int] = None
    voided: Optional[bool] = None
    voidDate: Optional[str] = None
    marketplaceNotified: Optional[bool] = None
    notifyErrorMessage: Optional[str] = None
    shipTo: Optional[ShipStationAddress] = None
    weight: Optional[ShipStationWeight] = None
    dimensions: Optional[ShipStationDimensions] = None
    insuranceOptions: Optional[dict] = None
    advancedOptions: Optional[dict] = None
    shipmentItems: Optional[List] = None
    labelData: Optional[str] = None
    formData: Optional[str] = None

class ShipStationShipmentsResponse(BaseModel):
    shipments: List[ShipStationShipment] = []
    total: Optional[int] = None
    page: Optional[int] = None
    pages: Optional[int] = None