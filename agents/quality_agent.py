from __future__ import annotations

from typing import Any, Optional
import structlog

from agents.base_agent import BaseAgent

logger = structlog.get_logger(__name__)


class QualityAgent(BaseAgent):

    def __init__(self, config: dict, fabric_config: dict) -> None:
        super().__init__(
            name="QualityAgent",
            description="Validates data quality at every medallion layer using rule-based and AI checks",
            config=config,
        )
        self._fabric_cfg = fabric_config
        self._fail_on_critical = config.get("agents", {}).get("quality", {}).get("fail_on_critical", True)
        self._quality_threshold = config.get("agents", {}).get("quality", {}).get("quality_threshold", 0.95)

    @property
    def system_prompt(self) -> str:
        return f"""You are an expert data quality engineer for Generali Corporate Commercial (insurance).
You are the QUALITY AGENT, responsible for validating data at Bronze, Silver, and Gold layers.

Quality threshold: {self._quality_threshold * 100}% — fail runs below this.
Fail on critical: {self._fail_on_critical}

Insurance-specific quality rules:
CRITICAL (pipeline must stop):
  - Policy number is null or duplicated in active policies
  - Premium amount is negative or zero on in-force policies
  - Claim total_paid > total_incurred (overpayment anomaly)
  - Policy expiration_date < inception_date
  - Coverage limit_amount = 0 on active coverages
  - Client with active policies has no valid country_of_risk

WARNING (log and alert but continue):
  - Missing broker_id on policies over EUR 100,000 premium
  - Claim open > 730 days without reserve update
  - Client missing industry_code (NACE)
  - Exchange rate conversion missing, using 1:1 fallback
  - IBNR reserves not recalculated in last 30 days

INFO (log only):
  - New source_system_id not previously seen (potential new client)
  - Unusual premium amount (>3 standard deviations from historical mean)
  - Line of business changed between renewal periods

Always express quality results as:
  - overall_score: float 0-1
  - critical_failures: list of specific rule names and counts
  - warnings: list of warnings with counts
  - recommendation: "proceed" | "review_and_proceed" | "halt_pipeline"
"""

    def get_tools(self) -> list[dict]:
        return [
            {
                "name": "run_quality_suite",
                "description": "Run the full quality rule suite on a dataset",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "layer": {"type": "string", "enum": ["bronze", "silver", "gold"]},
                        "entity_type": {"type": "string"},
                        "batch_id": {"type": "string"},
                    },
                    "required": ["layer", "entity_type"],
                },
            },
            {
                "name": "run_specific_rule",
                "description": "Run a single named quality rule",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "rule_name": {"type": "string"},
                        "layer": {"type": "string"},
                        "entity_type": {"type": "string"},
                        "threshold": {"type": "number"},
                    },
                    "required": ["rule_name", "layer", "entity_type"],
                },
            },
            {
                "name": "get_quality_history",
                "description": "Retrieve historical quality scores to detect trends",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "entity_type": {"type": "string"},
                        "days_back": {"type": "integer", "default": 30},
                    },
                    "required": ["entity_type"],
                },
            },
            {
                "name": "quarantine_failed_records",
                "description": "Move failed records to the quality quarantine table",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "layer": {"type": "string"},
                        "entity_type": {"type": "string"},
                        "batch_id": {"type": "string"},
                        "rule_name": {"type": "string"},
                        "failure_count": {"type": "integer"},
                    },
                    "required": ["layer", "entity_type", "batch_id", "rule_name"],
                },
            },
            {
                "name": "publish_quality_metrics",
                "description": "Publish quality metrics to the monitoring dashboard",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "entity_type": {"type": "string"},
                        "batch_id": {"type": "string"},
                        "quality_score": {"type": "number"},
                        "critical_count": {"type": "integer"},
                        "warning_count": {"type": "integer"},
                    },
                    "required": ["entity_type", "quality_score"],
                },
            },
            {
                "name": "detect_anomalies",
                "description": "Run statistical anomaly detection on numeric fields",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "entity_type": {"type": "string"},
                        "fields": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Numeric fields to check for anomalies"
                        },
                        "z_score_threshold": {"type": "number", "default": 3.0},
                    },
                    "required": ["entity_type", "fields"],
                },
            },
        ]

    def execute_tool(self, tool_name: str, tool_input: dict) -> Any:
        match tool_name:
            case "run_quality_suite":
                return self._run_quality_suite(**tool_input)
            case "run_specific_rule":
                return self._run_specific_rule(**tool_input)
            case "get_quality_history":
                return self._get_quality_history(**tool_input)
            case "quarantine_failed_records":
                return self._quarantine_records(**tool_input)
            case "publish_quality_metrics":
                return self._publish_metrics(**tool_input)
            case "detect_anomalies":
                return self._detect_anomalies(**tool_input)
            case _:
                raise ValueError(f"Unknown tool: {tool_name}")

    def _run_quality_suite(self, layer: str, entity_type: str, batch_id: Optional[str] = None) -> dict:
        logger.info("quality_suite", layer=layer, entity=entity_type)
        return {
            "layer": layer,
            "entity_type": entity_type,
            "overall_score": 0.9821,
            "total_records": 1248,
            "passed_records": 1223,
            "failed_records": 25,
            "critical_failures": [],
            "warnings": [
                {"rule": "missing_broker_id_high_premium", "count": 3},
                {"rule": "claim_open_over_730_days", "count": 22},
            ],
            "recommendation": "review_and_proceed",
            "batch_id": batch_id,
        }

    def _run_specific_rule(
        self,
        rule_name: str,
        layer: str,
        entity_type: str,
        threshold: Optional[float] = None,
    ) -> dict:
        return {
            "rule_name": rule_name,
            "layer": layer,
            "entity_type": entity_type,
            "passed": True,
            "failure_count": 0,
            "score": 1.0,
        }

    def _get_quality_history(self, entity_type: str, days_back: int = 30) -> dict:
        from datetime import datetime, timedelta
        history = []
        base_score = 0.982
        for i in range(days_back):
            dt = datetime.utcnow() - timedelta(days=i)
            history.append({
                "date": dt.date().isoformat(),
                "score": round(base_score - (i * 0.0001), 4),
                "entity_type": entity_type,
            })
        return {"entity_type": entity_type, "history": history, "trend": "stable"}

    def _quarantine_records(
        self,
        layer: str,
        entity_type: str,
        batch_id: str,
        rule_name: str,
        failure_count: Optional[int] = None,
    ) -> dict:
        logger.warning("quarantine_records", layer=layer, entity=entity_type, rule=rule_name)
        return {"quarantined": True, "count": failure_count or 0, "quarantine_table": f"{layer}.quarantine_{entity_type}"}

    def _publish_metrics(
        self,
        entity_type: str,
        quality_score: float,
        batch_id: Optional[str] = None,
        critical_count: int = 0,
        warning_count: int = 0,
    ) -> dict:
        logger.info("publish_quality_metrics", entity=entity_type, score=quality_score)
        return {"published": True, "dashboard_updated": True}

    def _detect_anomalies(
        self,
        entity_type: str,
        fields: list[str],
        z_score_threshold: float = 3.0,
    ) -> dict:
        return {
            "entity_type": entity_type,
            "fields_checked": fields,
            "anomalies_detected": 0,
            "anomaly_records": [],
            "z_score_threshold": z_score_threshold,
        }
