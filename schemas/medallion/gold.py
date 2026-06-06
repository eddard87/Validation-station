from __future__ import annotations

from datetime import datetime
from typing import Any, Optional
from pydantic import BaseModel, Field


class GoldRecord(BaseModel):
    """
    Business-ready aggregated and dimensionally-modelled record in the Gold layer.
    Powers Power BI semantic models and AI/ML feature stores.
    """
    _gold_id: str
    _subject_area: str = Field(description="underwriting|claims|finance|crm|risk")
    _table_name: str = Field(description="Target Gold table name")
    _entity_id: str
    _year: int
    _line_of_business: str
    _processing_timestamp: datetime
    _batch_id: str
    _schema_version: str = Field(default="1.0")
    _payload: dict[str, Any]
    _is_current: bool = True
    _feature_ready: bool = Field(
        default=False,
        description="True when record has been prepared for ML feature store"
    )
    _ai_embeddings_ready: bool = Field(
        default=False,
        description="True when text fields have been vectorized"
    )

    def delta_partition_values(self) -> dict[str, Any]:
        return {
            "year": self._year,
            "line_of_business": self._line_of_business,
            "subject_area": self._subject_area,
        }
