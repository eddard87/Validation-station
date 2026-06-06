from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class ClaimStatus(str, Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    PENDING_INFO = "pending_info"
    UNDER_INVESTIGATION = "under_investigation"
    RESERVED = "reserved"
    CLOSED_PAID = "closed_paid"
    CLOSED_NO_PAYMENT = "closed_no_payment"
    REOPENED = "reopened"
    LITIGATED = "litigated"


class LossType(str, Enum):
    FIRE = "fire"
    WATER = "water"
    THEFT = "theft"
    NATURAL_CATASTROPHE = "natural_catastrophe"
    BODILY_INJURY = "bodily_injury"
    PROPERTY_DAMAGE = "property_damage"
    FINANCIAL_LOSS = "financial_loss"
    CYBER_INCIDENT = "cyber_incident"
    CARGO_DAMAGE = "cargo_damage"
    LIABILITY_CLAIM = "liability_claim"
    BUSINESS_INTERRUPTION = "business_interruption"


class ReserveType(str, Enum):
    OUTSTANDING_LOSS = "outstanding_loss"
    IBNR = "ibnr"
    EXPENSES = "expenses"
    RECOVERY = "recovery"
    LEGAL = "legal"


class Reserve(BaseModel):
    reserve_id: str
    claim_id: str
    exposure_id: str
    reserve_type: ReserveType
    amount: Decimal
    currency: str = Field(default="EUR")
    effective_date: date
    created_by: str
    created_at: datetime
    updated_at: datetime
    comment: Optional[str] = None


class Exposure(BaseModel):
    exposure_id: str
    claim_id: str
    coverage_id: str
    loss_type: LossType
    status: ClaimStatus
    total_incurred: Decimal
    total_paid: Decimal
    total_reserve: Decimal
    currency: str = Field(default="EUR")
    reserves: list[Reserve] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    @property
    def outstanding_reserve(self) -> Decimal:
        return self.total_reserve - self.total_paid


class ClaimPayment(BaseModel):
    payment_id: str
    claim_id: str
    exposure_id: str
    amount: Decimal
    currency: str = Field(default="EUR")
    payment_date: date
    payment_type: str
    payee_name: str
    payee_bank_iban: Optional[str] = None
    approved_by: str
    created_at: datetime


class Claim(BaseModel):
    claim_id: str
    claim_number: str
    policy_id: str
    policy_number: str
    client_id: str
    status: ClaimStatus
    loss_type: LossType
    loss_date: date
    reported_date: date
    closed_date: Optional[date] = None
    loss_description: str
    loss_location_country: str = Field(pattern=r"^[A-Z]{2}$")
    loss_location_city: Optional[str] = None
    currency: str = Field(default="EUR")
    total_incurred: Decimal = Decimal("0")
    total_paid: Decimal = Decimal("0")
    total_reserve: Decimal = Decimal("0")
    exposures: list[Exposure] = Field(default_factory=list)
    payments: list[ClaimPayment] = Field(default_factory=list)
    handler_id: str
    litigation: bool = False
    catastrophe_event_id: Optional[str] = None
    reinsurance_recoverable: Decimal = Decimal("0")
    source_system: str = Field(default="guidewire_cc")
    source_system_id: str
    created_at: datetime
    updated_at: datetime

    @property
    def days_open(self) -> int:
        end = self.closed_date or date.today()
        return (end - self.reported_date).days

    @property
    def loss_ratio_contribution(self) -> Optional[Decimal]:
        return None
