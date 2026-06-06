from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Optional, Any
from pydantic import BaseModel, Field


class RiskGrade(str, Enum):
    PREFERRED = "preferred"
    STANDARD = "standard"
    SUBSTANDARD = "substandard"
    DECLINE = "decline"
    REFER = "refer"


class PricingBasis(str, Enum):
    RATE_ON_LINE = "rate_on_line"
    BURNING_COST = "burning_cost"
    EXPOSURE_BASED = "exposure_based"
    MARKET_RATE = "market_rate"
    ACTUARIAL = "actuarial"


class RiskFactor(BaseModel):
    factor_name: str
    factor_value: Any
    factor_weight: Decimal = Field(ge=Decimal("0"), le=Decimal("1"))
    impact: str = Field(description="positive|negative|neutral")
    commentary: Optional[str] = None


class LossHistory(BaseModel):
    year: int
    earned_premium: Decimal
    incurred_losses: Decimal
    loss_ratio: Decimal
    claim_count: int
    currency: str = Field(default="EUR")

    @property
    def is_profitable(self) -> bool:
        return self.loss_ratio < Decimal("0.7")


class PricingModel(BaseModel):
    model_id: str
    policy_id: str
    line_of_business: str
    pricing_basis: PricingBasis
    base_rate: Decimal
    technical_rate: Decimal
    market_rate: Decimal
    final_rate: Decimal
    total_insured_value: Decimal
    calculated_premium: Decimal
    currency: str = Field(default="EUR")
    rate_factors: list[RiskFactor] = Field(default_factory=list)
    loss_history: list[LossHistory] = Field(default_factory=list)
    model_version: str
    calculated_at: datetime
    calculated_by: str
    approved_by: Optional[str] = None

    @property
    def rate_adequacy(self) -> Decimal:
        if self.technical_rate == 0:
            return Decimal("0")
        return self.final_rate / self.technical_rate


class RiskLocation(BaseModel):
    location_id: str
    assessment_id: str
    street_address: str
    city: str
    region: Optional[str] = None
    country: str = Field(pattern=r"^[A-Z]{2}$")
    postal_code: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    total_insured_value: Decimal
    construction_type: Optional[str] = None
    construction_year: Optional[int] = None
    floor_area_sqm: Optional[float] = None
    flood_zone: Optional[str] = None
    earthquake_zone: Optional[str] = None
    fire_protection_class: Optional[str] = None


class RiskAssessment(BaseModel):
    assessment_id: str
    policy_id: str
    client_id: str
    line_of_business: str
    assessment_date: date
    valid_until: date
    risk_grade: RiskGrade
    risk_score: Decimal = Field(ge=Decimal("0"), le=Decimal("100"))
    risk_factors: list[RiskFactor] = Field(default_factory=list)
    risk_locations: list[RiskLocation] = Field(default_factory=list)
    maximum_probable_loss: Optional[Decimal] = None
    probable_maximum_loss: Optional[Decimal] = None
    currency: str = Field(default="EUR")
    underwriter_notes: Optional[str] = None
    engineering_survey_required: bool = False
    engineering_survey_date: Optional[date] = None
    pricing_model: Optional[PricingModel] = None
    created_by: str
    created_at: datetime
    updated_at: datetime

    @property
    def is_acceptable(self) -> bool:
        return self.risk_grade not in (RiskGrade.DECLINE,)

    @property
    def needs_referral(self) -> bool:
        return self.risk_grade == RiskGrade.REFER or self.risk_score >= Decimal("75")
