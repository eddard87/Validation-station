from __future__ import annotations

from datetime import datetime
from typing import Any, Optional
from pydantic import BaseModel, Field


class DataQualityResult(BaseModel):
    rule_name: str
    passed: bool
    severity: str = Field(description="critical|warning|info")
    failed_count: int = 0
    details: Optional[str] = None


class SilverRecord(BaseModel):
    """
    Cleansed, standardized, and conformed record in the Silver layer.
    Applies business rules, type coercion, and joins with reference data.
    """
    _silver_id: str
    _bronze_ingestion_id: str
    _source_system: str
    _source_table: str
    _entity_type: str = Field(description="policy|claim|client|broker|payment")
    _entity_id: str = Field(description="Canonical business key")
    _processing_timestamp: datetime
    _processing_batch_id: str
    _schema_version: str = Field(default="1.0")
    _data_quality_results: list[DataQualityResult] = Field(default_factory=list)
    _dq_score: float = Field(ge=0.0, le=1.0, description="Overall DQ score 0-1")
    _is_valid: bool = True
    _year: int
    _month: int
    _line_of_business: Optional[str] = None
    _payload: dict[str, Any] = Field(description="Standardized and enriched payload")
    _change_type: str = Field(default="upsert", description="insert|update|delete|upsert")
    _effective_from: datetime
    _effective_to: Optional[datetime] = None
    _is_current: bool = True

    def delta_partition_values(self) -> dict[str, Any]:
        return {
            "year": self._year,
            "month": self._month,
            "line_of_business": self._line_of_business or "unknown",
            "entity_type": self._entity_type,
        }

    @property
    def is_high_quality(self) -> bool:
        return self._is_valid and self._dq_score >= 0.95
