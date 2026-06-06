from __future__ import annotations

from typing import Any, Optional
import structlog

from agents.base_agent import BaseAgent

logger = structlog.get_logger(__name__)


class TransformationAgent(BaseAgent):

    def __init__(self, config: dict, fabric_config: dict) -> None:
        super().__init__(
            name="TransformationAgent",
            description="Transforms Bronze→Silver and Silver→Gold applying insurance business rules",
            config=config,
        )
        self._fabric_cfg = fabric_config

    @property
    def system_prompt(self) -> str:
        return """You are an expert AI data engineer for Generali Corporate Commercial (insurance).
You are the TRANSFORMATION AGENT responsible for the Bronze→Silver→Gold medallion pipeline.

Bronze→Silver rules:
- Standardise all dates to ISO 8601 UTC
- Normalise currency codes to ISO 4217 (EUR, USD, GBP...)
- Map source-system status codes to canonical enums (e.g. 'IN_FORCE', 'OPEN')
- Deduplicate using record_hash; apply SCD Type 2 for slowly changing dimensions
- Join with reference tables: line_of_business_mapping, country_codes, currency_rates
- Flag PII fields (name, email, phone, fiscal_code) for masking in non-prod
- Calculate data quality score per record based on completeness and consistency rules

Silver→Gold rules:
- Build star schema: dim_policy, dim_client, dim_broker, dim_date, dim_lob, fact_premium, fact_claim
- Calculate derived KPIs: loss_ratio, combined_ratio, earned_premium, IBNR estimates
- Apply reinsurance netting to claim amounts where applicable
- Aggregate at policy_period level for underwriting analytics
- Build AI feature tables: policy risk features, claim propensity features, churn signals

Always write idempotent transformations using MERGE/upsert patterns.
Always partition output by year/month/line_of_business for query efficiency.
"""

    def get_tools(self) -> list[dict]:
        return [
            {
                "name": "run_bronze_to_silver",
                "description": "Execute Bronze to Silver transformation for a given entity type",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "entity_type": {
                            "type": "string",
                            "enum": ["policy", "claim", "client", "broker", "payment", "reserve"]
                        },
                        "source_system": {"type": "string"},
                        "batch_id": {"type": "string"},
                        "incremental": {"type": "boolean", "default": True},
                    },
                    "required": ["entity_type", "source_system"],
                },
            },
            {
                "name": "run_silver_to_gold",
                "description": "Execute Silver to Gold transformation building the dimensional model",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "subject_area": {
                            "type": "string",
                            "enum": ["underwriting", "claims", "finance", "crm", "risk"]
                        },
                        "reference_date": {
                            "type": "string",
                            "description": "ISO date for point-in-time snapshots"
                        },
                    },
                    "required": ["subject_area"],
                },
            },
            {
                "name": "apply_business_rules",
                "description": "Apply a specific set of insurance business rules to Silver data",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "rule_set": {
                            "type": "string",
                            "enum": [
                                "loss_ratio_calculation",
                                "earned_premium_proration",
                                "ibnr_estimation",
                                "reinsurance_netting",
                                "currency_conversion",
                                "large_risk_flagging",
                            ]
                        },
                        "entity_type": {"type": "string"},
                        "period": {"type": "string", "description": "YYYY-MM accounting period"},
                    },
                    "required": ["rule_set", "entity_type"],
                },
            },
            {
                "name": "check_transformation_quality",
                "description": "Validate output counts and referential integrity after transformation",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "source_layer": {"type": "string", "enum": ["bronze", "silver"]},
                        "target_layer": {"type": "string", "enum": ["silver", "gold"]},
                        "entity_type": {"type": "string"},
                        "batch_id": {"type": "string"},
                    },
                    "required": ["source_layer", "target_layer", "entity_type"],
                },
            },
            {
                "name": "get_spark_job_status",
                "description": "Check the status of a Spark transformation job",
                "input_schema": {
                    "type": "object",
                    "properties": {"job_id": {"type": "string"}},
                    "required": ["job_id"],
                },
            },
        ]

    def execute_tool(self, tool_name: str, tool_input: dict) -> Any:
        match tool_name:
            case "run_bronze_to_silver":
                return self._bronze_to_silver(**tool_input)
            case "run_silver_to_gold":
                return self._silver_to_gold(**tool_input)
            case "apply_business_rules":
                return self._apply_rules(**tool_input)
            case "check_transformation_quality":
                return self._check_quality(**tool_input)
            case "get_spark_job_status":
                return self._get_job_status(**tool_input)
            case _:
                raise ValueError(f"Unknown tool: {tool_name}")

    def _bronze_to_silver(
        self,
        entity_type: str,
        source_system: str,
        batch_id: Optional[str] = None,
        incremental: bool = True,
    ) -> dict:
        import uuid
        job_id = str(uuid.uuid4())
        logger.info("bronze_to_silver", entity=entity_type, system=source_system, incremental=incremental)
        # In production: submit Spark notebook via Fabric REST API or mssparkutils
        return {
            "job_id": job_id,
            "entity_type": entity_type,
            "source_system": source_system,
            "status": "Submitted",
            "records_read": 1250,
            "records_written": 1248,
            "records_rejected": 2,
            "dq_score": 0.9984,
        }

    def _silver_to_gold(self, subject_area: str, reference_date: Optional[str] = None) -> dict:
        import uuid
        job_id = str(uuid.uuid4())
        logger.info("silver_to_gold", subject_area=subject_area, reference_date=reference_date)
        return {
            "job_id": job_id,
            "subject_area": subject_area,
            "status": "Submitted",
            "tables_updated": [
                f"gold.dim_{subject_area}",
                f"gold.fact_{subject_area}",
            ],
        }

    def _apply_rules(self, rule_set: str, entity_type: str, period: Optional[str] = None) -> dict:
        logger.info("apply_rules", rule_set=rule_set, entity=entity_type, period=period)
        return {"rule_set": rule_set, "entity_type": entity_type, "status": "applied", "rows_affected": 8432}

    def _check_quality(
        self,
        source_layer: str,
        target_layer: str,
        entity_type: str,
        batch_id: Optional[str] = None,
    ) -> dict:
        return {
            "source_layer": source_layer,
            "target_layer": target_layer,
            "entity_type": entity_type,
            "source_count": 1250,
            "target_count": 1248,
            "match_rate": 0.9984,
            "referential_integrity_passed": True,
            "null_pk_count": 0,
        }

    def _get_job_status(self, job_id: str) -> dict:
        return {"job_id": job_id, "status": "Succeeded", "duration_seconds": 142}
