from __future__ import annotations

from datetime import datetime
from typing import Any, Optional
from pydantic import BaseModel, Field
import hashlib
import json


class BronzeRecord(BaseModel):
    """
    Raw ingestion envelope - wraps every record landing in the Bronze layer.
    Preserves the original payload without transformation.
    """
    _ingestion_id: str = Field(description="UUID generated at ingestion time")
    _source_system: str = Field(description="Identifier of the source system")
    _source_table: str = Field(description="Table/endpoint name in source system")
    _source_record_id: str = Field(description="Primary key from source system")
    _ingestion_timestamp: datetime = Field(description="UTC timestamp of ingestion")
    _ingestion_batch_id: str = Field(description="Batch/pipeline run identifier")
    _ingestion_year: int
    _ingestion_month: int
    _ingestion_day: int
    _record_hash: str = Field(description="SHA-256 hash of payload for deduplication")
    _schema_version: str = Field(default="1.0")
    _is_deleted: bool = Field(default=False, description="Soft-delete flag for CDC")
    _payload: dict[str, Any] = Field(description="Original record payload as-is")
    _payload_format: str = Field(default="json", description="json|avro|parquet|csv")
    _row_number: Optional[int] = None

    @classmethod
    def from_source_record(
        cls,
        source_system: str,
        source_table: str,
        source_record_id: str,
        payload: dict[str, Any],
        batch_id: str,
        ingestion_id: Optional[str] = None,
    ) -> "BronzeRecord":
        import uuid
        now = datetime.utcnow()
        payload_json = json.dumps(payload, sort_keys=True, default=str)
        record_hash = hashlib.sha256(payload_json.encode()).hexdigest()

        return cls(
            _ingestion_id=ingestion_id or str(uuid.uuid4()),
            _source_system=source_system,
            _source_table=source_table,
            _source_record_id=str(source_record_id),
            _ingestion_timestamp=now,
            _ingestion_batch_id=batch_id,
            _ingestion_year=now.year,
            _ingestion_month=now.month,
            _ingestion_day=now.day,
            _record_hash=record_hash,
            _payload=payload,
        )

    def delta_partition_values(self) -> dict[str, Any]:
        return {
            "year": self._ingestion_year,
            "month": self._ingestion_month,
            "day": self._ingestion_day,
            "source_system": self._source_system,
        }
