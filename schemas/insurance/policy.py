from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field, field_validator


class LineOfBusiness(str, Enum):
    PROPERTY = "property"
    LIABILITY = "liability"
    MARINE = "marine"
    ENGINEERING = "engineering"
    CREDIT_SURETY = "credit_surety"
    CYBER = "cyber"
    AVIATION = "aviation"
    ACCIDENT_HEALTH = "accident_health"
    FINANCIAL_LINES = "financial_lines"


class PolicyStatus(str, Enum):
    DRAFT = "draft"
    BOUND = "bound"
    IN_FORCE = "in_force"
    EXPIRED = "expired"
    CANCELLED = "cancelled"
    RENEWED = "renewed"


class CoverageType(str, Enum):
    BUILDING = "building"
    CONTENTS = "contents"
    BUSINESS_INTERRUPTION = "business_interruption"
    GENERAL_LIABILITY = "general_liability"
    PRODUCT_LIABILITY = "product_liability"
    DIRECTORS_OFFICERS = "directors_officers"
    ERRORS_OMISSIONS = "errors_omissions"
    CYBER_LIABILITY = "cyber_liability"
    CARGO = "cargo"
    HULL = "hull"


class Coverage(BaseModel):
    coverage_id: str
    policy_period_id: str
    coverage_type: CoverageType
    line_of_business: LineOfBusiness
    limit_amount: Decimal
    deductible_amount: Decimal
    premium_amount: Decimal
    currency: str = Field(default="EUR", pattern=r"^[A-Z]{3}$")
    inception_date: date
    expiration_date: date
    sublimits: dict[str, Decimal] = Field(default_factory=dict)
    exclusions: list[str] = Field(default_factory=list)
    endorsements: list[str] = Field(default_factory=list)
    is_active: bool = True
    created_at: datetime
    updated_at: datetime

    @field_validator("expiration_date")
    @classmethod
    def expiration_after_inception(cls, v: date, info) -> date:
        if "inception_date" in info.data and v <= info.data["inception_date"]:
            raise ValueError("expiration_date must be after inception_date")
        return v


class PolicyPeriod(BaseModel):
    period_id: str
    policy_id: str
    period_start: date
    period_end: date
    status: PolicyStatus
    total_premium: Decimal
    written_premium: Decimal
    earned_premium: Optional[Decimal] = None
    currency: str = Field(default="EUR", pattern=r"^[A-Z]{3}$")
    coverages: list[Coverage] = Field(default_factory=list)
    change_reason: Optional[str] = None
    is_renewal: bool = False
    prior_period_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class Policy(BaseModel):
    policy_id: str
    policy_number: str = Field(description="Human-readable policy number, e.g. GCC-2024-00123")
    client_id: str
    broker_id: Optional[str] = None
    underwriter_id: str
    line_of_business: LineOfBusiness
    status: PolicyStatus
    product_code: str
    country_of_risk: str = Field(pattern=r"^[A-Z]{2}$")
    currency: str = Field(default="EUR", pattern=r"^[A-Z]{3}$")
    inception_date: date
    expiration_date: date
    policy_periods: list[PolicyPeriod] = Field(default_factory=list)
    total_insured_value: Optional[Decimal] = None
    source_system: str = Field(default="guidewire_pc")
    source_system_id: str
    created_at: datetime
    updated_at: datetime
    is_large_risk: bool = Field(
        default=False,
        description="True if total_insured_value > 5M EUR or premium > 500K EUR"
    )
    reinsurance_required: bool = False
    tags: dict[str, str] = Field(default_factory=dict)

    @field_validator("policy_number")
    @classmethod
    def validate_policy_number_format(cls, v: str) -> str:
        parts = v.split("-")
        if len(parts) < 3:
            raise ValueError("policy_number must follow pattern: PREFIX-YEAR-SEQUENCE")
        return v

    def current_period(self) -> Optional[PolicyPeriod]:
        today = date.today()
        for period in self.policy_periods:
            if period.period_start <= today <= period.period_end:
                return period
        return None
