# enerated by datamodel-codegen:
#   filename:  data.json
#   timestamp: 2023-09-25T02:53:29+00:00

from __future__ import annotations
from logging import warn

from typing import List, Optional

from pydantic import BaseModel
from datetime import datetime

class RefNum(BaseModel):
    # type: str
    value: str | None = None


class Location(BaseModel):
    company: str
    address: str
    # address2: str
    # city: str
    # state: str
    # postalCode: str
    # country: str
    # stopDate: Optional[str] = None
    # stopDateType: str
    # stopType: str
    # sequence: int
    # accessorials: List
    refNums: List[RefNum]
    # type: str
    # lat: float
    # lng: float
    # timezone: str
    # opensAt: str
    # closesAt: str
    # contactName: str
    contactEmail: str | None = None
    # contactPhone: str
    # instructions: str


# class BillTo(BaseModel):
    # company: str
    # address: str
    # city: str
    # state: str
    # address2: str
    # postalCode: str
    # country: str
    # contactName: str
    # contactPhone: str
    # contactEmail: str


class Equipment(BaseModel):
#     alternateTypes: List
#     mode: str
#     type: str
#     accessorials: List
#     description: str
    weight: int
    weightUOM: str
#     isHazardous: bool


# class Contain(BaseModel):
#     type: str
#     description: str
#     declaredValueCurrency: str
#     quantity: int


# class Item(BaseModel):
    # declaredValueCurrency: str
    # freightClass: int
    # height: int
    # length: int
    # quantity: int
    # width: int
    # pickupLocationSequence: int
    # dropLocationSequence: int
    # weight: int | None = None
    # weightUOM: str
    # description: str
    # type: str
    # contains: List[Contain]


# class Charge(BaseModel):
#     name: str
#     amount: float
#     code: str
#     currency: str


class SelectedQuote(BaseModel):
    assetCarrierName: str | None = None
    quoteId: str
    # carrierId: str
    # createdDate: str
    # assetCarrierCode: str
    # providerName: str
    # providerCode: str
    # equipmentType: str
    # serviceId: str
    # serviceDescription: str
    # pricingMethod: str
    # pricingType: str
    amount: float | None = None
    # currency: str
    # refNums: List[RefNum]
    status: str
    # method: str
    # source: str
    # charges: List[Charge]
    # transitDaysMin: int
    # transitDaysMax: int
    # interline: bool
    # mode: str
    # paymentTerms: str
    # quoteNum: Optional[str] = None


class Tracking(BaseModel):
    deliveryDateActual: datetime | None = None
    deliveryDateEstimate: datetime | None = None
    lastUpdatedDate: datetime | None = None
    pickupDateActual: datetime | None = None
    status: str
    trackingNumber: str | None = None

class Document(BaseModel):
    fileName: str
    mimeType: str
    source: str
    type: str
    uploadDate: str
    url: str


class Pickup(BaseModel):
    status: str
#     confirmationNumber: str
#     requestedDate: str
#     confirmedDate: Optional[str] = None


class Bol(BaseModel):
    status: str
#     bolNumber: str


class Shipment(BaseModel):
    # bookedDate: str
    # createdDate: str
    shipmentId: str
    # pickupDate: str
    status: str
    locations: List[Location]
    # billTo: BillTo
    equipment: Equipment
    # isLiveLoad: bool
    # isArchived: bool
    # items: List[Item]
    direction: str
    refNums: List
    selectedQuote: SelectedQuote
    tracking: Tracking
    # documents: List[Document]
    # pickup: Pickup
    # bol: Bol
    # quotedBy: str


class Model(BaseModel):
    shipments: List[Shipment]
