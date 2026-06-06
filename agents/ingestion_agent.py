from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Optional
import structlog

from agents.base_agent import BaseAgent
from fabric.lakehouse import LakehouseClient, MedallionLayer
from fabric.pipeline import PipelineClient

logger = structlog.get_logger(__name__)

GENERALI_INSURANCE_DOMAIN = """
You are an expert AI data engineer for Generali Corporate Commercial, a leading corporate insurance company.
You specialise in Microsoft Fabric and the ingestion of insurance data from source systems including
Guidewire PolicyCenter, ClaimCenter, BillingCenter, Salesforce CRM, and AS400 reinsurance systems.

Insurance domain knowledge:
- Lines of business: Property, Liability (GL/PL/D&O/E&O), Marine, Engineering, Credit/Surety, Cyber, Aviation
- Key entities: Policy, PolicyPeriod, Coverage, Claim, Exposure, Reserve, Payment, Client, Broker
- Regulatory context: IVASS (Italian insurance regulator), Solvency II, GDPR
- Data sensitivity: PII in client/contact data must be masked; financial data requires audit trails
- Incremental loads use UpdateTime/LUPDATE watermarks per source system

Medallion architecture on Fabric OneLake:
- Bronze: raw landing zone, partitioned by year/month/day/source_system
- Silver: cleansed, standardised, SCD Type 2
- Gold: dimensional model for BI + feature store for AI/ML
"""


class IngestionAgent(BaseAgent):

    def __init__(self, config: dict, fabric_config: dict) -> None:
        super().__init__(
            name="IngestionAgent",
            description="Extracts data from insurance source systems into Bronze lakehouse",
            config=config,
        )
        self._fabric_cfg = fabric_config
        self._bronze: Optional[LakehouseClient] = None
        self._pipeline: Optional[PipelineClient] = None

    @property
    def system_prompt(self) -> str:
        return f"""{GENERALI_INSURANCE_DOMAIN}

Your role is the INGESTION AGENT. You are responsible for:
1. Determining which source tables need to be ingested (full load vs incremental)
2. Calculating correct watermarks to avoid re-ingesting already processed data
3. Triggering the appropriate Fabric Data Factory pipelines
4. Validating that records landed in Bronze correctly
5. Handling failures with retry logic and alerting

Always prefer incremental ingestion over full loads.
Always record the watermark AFTER successful ingestion, never before.
Log every decision you make with clear reasoning.
"""

    def get_tools(self) -> list[dict]:
        return [
            {
                "name": "get_watermark",
                "description": "Get the last successful ingestion watermark for a source table",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "source_system": {"type": "string"},
                        "source_table": {"type": "string"},
                    },
                    "required": ["source_system", "source_table"],
                },
            },
            {
                "name": "trigger_ingestion_pipeline",
                "description": "Trigger a Fabric Data Factory pipeline to ingest a source table",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "pipeline_name": {"type": "string"},
                        "source_system": {"type": "string"},
                        "source_table": {"type": "string"},
                        "watermark_value": {
                            "type": "string",
                            "description": "ISO8601 timestamp for incremental load"
                        },
                        "load_type": {
                            "type": "string",
                            "enum": ["full", "incremental"],
                        },
                    },
                    "required": ["pipeline_name", "source_system", "source_table", "load_type"],
                },
            },
            {
                "name": "check_pipeline_status",
                "description": "Check the status of a running pipeline",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "pipeline_name": {"type": "string"},
                        "run_id": {"type": "string"},
                    },
                    "required": ["pipeline_name", "run_id"],
                },
            },
            {
                "name": "validate_bronze_landing",
                "description": "Validate that records landed correctly in Bronze lakehouse",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "source_system": {"type": "string"},
                        "source_table": {"type": "string"},
                        "batch_id": {"type": "string"},
                        "expected_record_count": {"type": "integer"},
                    },
                    "required": ["source_system", "source_table", "batch_id"],
                },
            },
            {
                "name": "update_watermark",
                "description": "Update the ingestion watermark after successful load",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "source_system": {"type": "string"},
                        "source_table": {"type": "string"},
                        "new_watermark": {"type": "string"},
                        "batch_id": {"type": "string"},
                        "records_ingested": {"type": "integer"},
                    },
                    "required": ["source_system", "source_table", "new_watermark", "batch_id"],
                },
            },
            {
                "name": "send_alert",
                "description": "Send an alert for ingestion failures or anomalies",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "severity": {"type": "string", "enum": ["critical", "warning", "info"]},
                        "message": {"type": "string"},
                        "source_system": {"type": "string"},
                        "source_table": {"type": "string"},
                    },
                    "required": ["severity", "message"],
                },
            },
        ]

    def execute_tool(self, tool_name: str, tool_input: dict) -> Any:
        match tool_name:
            case "get_watermark":
                return self._get_watermark(**tool_input)
            case "trigger_ingestion_pipeline":
                return self._trigger_pipeline(**tool_input)
            case "check_pipeline_status":
                return self._check_pipeline(**tool_input)
            case "validate_bronze_landing":
                return self._validate_landing(**tool_input)
            case "update_watermark":
                return self._update_watermark(**tool_input)
            case "send_alert":
                return self._send_alert(**tool_input)
            case _:
                raise ValueError(f"Unknown tool: {tool_name}")

    def _get_watermark(self, source_system: str, source_table: str) -> dict:
        # In production: query bronze.watermarks Delta table
        default_wm = (datetime.utcnow() - timedelta(days=1)).isoformat()
        logger.info("get_watermark", system=source_system, table=source_table)
        return {
            "source_system": source_system,
            "source_table": source_table,
            "last_watermark": default_wm,
            "last_batch_id": None,
            "records_last_run": 0,
        }

    def _trigger_pipeline(
        self,
        pipeline_name: str,
        source_system: str,
        source_table: str,
        load_type: str,
        watermark_value: Optional[str] = None,
    ) -> dict:
        import uuid
        batch_id = str(uuid.uuid4())
        logger.info(
            "pipeline_triggered",
            pipeline=pipeline_name,
            system=source_system,
            table=source_table,
            load_type=load_type,
        )
        # In production: self._pipeline.trigger_pipeline(pipeline_name, {...})
        return {
            "run_id": f"mock-run-{batch_id[:8]}",
            "batch_id": batch_id,
            "pipeline_name": pipeline_name,
            "status": "Queued",
            "triggered_at": datetime.utcnow().isoformat(),
        }

    def _check_pipeline(self, pipeline_name: str, run_id: str) -> dict:
        # In production: self._pipeline.get_pipeline_status(pipeline_name, run_id)
        return {"run_id": run_id, "status": "Succeeded", "records_written": 1250}

    def _validate_landing(
        self,
        source_system: str,
        source_table: str,
        batch_id: str,
        expected_record_count: Optional[int] = None,
    ) -> dict:
        # In production: query Bronze Delta table filtering on _ingestion_batch_id
        actual_count = expected_record_count or 1250
        return {
            "table": f"bronze.{source_system}_{source_table}",
            "batch_id": batch_id,
            "actual_count": actual_count,
            "expected_count": expected_record_count,
            "validation_passed": True,
            "schema_valid": True,
            "null_pk_count": 0,
            "duplicate_count": 0,
        }

    def _update_watermark(
        self,
        source_system: str,
        source_table: str,
        new_watermark: str,
        batch_id: str,
        records_ingested: int = 0,
    ) -> dict:
        logger.info(
            "watermark_updated",
            system=source_system,
            table=source_table,
            watermark=new_watermark,
        )
        return {"status": "updated", "watermark": new_watermark, "records_ingested": records_ingested}

    def _send_alert(
        self,
        severity: str,
        message: str,
        source_system: Optional[str] = None,
        source_table: Optional[str] = None,
    ) -> dict:
        logger.warning("alert_sent", severity=severity, message=message)
        # In production: send to Teams/PagerDuty/Azure Monitor
        return {"alert_sent": True, "severity": severity}
