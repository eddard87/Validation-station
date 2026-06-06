from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field, EmailStr


class ClientSegment(str, Enum):
    LARGE_CORPORATE = "large_corporate"
    MID_MARKET = "mid_market"
    SME = "sme"
    MULTINATIONAL = "multinational"
    FINANCIAL_INSTITUTION = "financial_institution"
    PUBLIC_ENTITY = "public_entity"


class ClientType(str, Enum):
    POLICYHOLDER = "policyholder"
    BROKER = "broker"
    REINSURER = "reinsurer"
    CO_INSURER = "co_insurer"


class Contact(BaseModel):
    contact_id: str
    client_id: str
    first_name: str
    last_name: str
    role: str
    email: Optional[str] = None
    phone: Optional[str] = None
    is_primary: bool = False
    created_at: datetime
    updated_at: datetime


class Broker(BaseModel):
    broker_id: str
    broker_name: str
    broker_code: str
    network: Optional[str] = None
    country: str = Field(pattern=r"^[A-Z]{2}$")
    license_number: Optional[str] = None
    license_expiry: Optional[date] = None
    commission_rate: Decimal = Field(ge=Decimal("0"), le=Decimal("1"))
    is_active: bool = True
    contacts: list[Contact] = Field(default_factory=list)
    source_system_id: str
    created_at: datetime
    updated_at: datetime


class Client(BaseModel):
    client_id: str
    client_name: str
    legal_name: str
    client_type: ClientType
    segment: ClientSegment
    industry_code: str = Field(description="NACE/ATECO industry classification code")
    industry_description: str
    country_of_incorporation: str = Field(pattern=r"^[A-Z]{2}$")
    country_of_domicile: str = Field(pattern=r"^[A-Z]{2}$")
    vat_number: Optional[str] = None
    fiscal_code: Optional[str] = None
    annual_revenue: Optional[Decimal] = None
    revenue_currency: str = Field(default="EUR")
    employee_count: Optional[int] = None
    credit_rating: Optional[str] = None
    credit_rating_agency: Optional[str] = None
    is_group: bool = False
    parent_client_id: Optional[str] = None
    group_id: Optional[str] = None
    broker_id: Optional[str] = None
    contacts: list[Contact] = Field(default_factory=list)
    aml_cleared: bool = False
    sanctions_checked: bool = False
    sanctions_check_date: Optional[date] = None
    source_system: str = Field(default="guidewire_pc")
    source_system_id: str
    created_at: datetime
    updated_at: datetime

    @property
    def is_large_corporate(self) -> bool:
        if self.annual_revenue and self.annual_revenue >= Decimal("250_000_000"):
            return True
        if self.employee_count and self.employee_count >= 1000:
            return True
        return self.segment == ClientSegment.LARGE_CORPORATE
