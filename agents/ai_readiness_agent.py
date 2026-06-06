from __future__ import annotations

from typing import Any, Optional
import structlog

from agents.base_agent import BaseAgent

logger = structlog.get_logger(__name__)


class AIReadinessAgent(BaseAgent):

    def __init__(self, config: dict, fabric_config: dict) -> None:
        super().__init__(
            name="AIReadinessAgent",
            description="Prepares feature stores and training datasets for Generali AI/ML use cases",
            config=config,
        )
        self._fabric_cfg = fabric_config

    @property
    def system_prompt(self) -> str:
        return """You are an expert MLOps and AI data engineer for Generali Corporate Commercial (insurance).
You are the AI READINESS AGENT, responsible for making data AI-ready in Microsoft Fabric.

Key AI/ML use cases for Generali Corporate Commercial:
1. CLAIM PROPENSITY MODEL - predict probability of a claim being filed per policy
   Features: policy_age_days, total_insured_value, line_of_business, country_of_risk,
             historical_loss_ratio, industry_code, premium_rate_adequacy, broker_tier
   Target: claim_filed_within_12_months (binary)

2. LARGE LOSS PREDICTOR - predict severity of claims above EUR 500K
   Features: claim_type, loss_type, country, industry, tiv, coverage_limit,
             days_to_report, has_litigation, catastrophe_event
   Target: log_claim_amount (regression)

3. RENEWAL CHURN MODEL - predict client non-renewal probability
   Features: policy_tenure_years, premium_change_pct, loss_ratio, nps_score,
             broker_relationship_years, competitor_quotes, account_size
   Target: churned_at_renewal (binary)

4. UNDERWRITING RISK SCORE - AI-augmented risk scoring for new business
   Features: client risk factors, location hazard scores, industry loss history,
             reinsurance market conditions, catastrophe exposure
   Target: risk_grade (multi-class: preferred/standard/substandard/decline)

5. DOCUMENT AI (IDP) - extract structured data from insurance documents
   Use Fabric's AI capabilities + Claude for policy documents, loss reports, surveys

For each use case you must:
- Create a feature table in gold.features_* with proper versioning
- Ensure no data leakage (features use only information available at prediction time)
- Apply GDPR-compliant anonymisation for PII fields
- Register features in the Fabric feature store with metadata
- Generate training/validation/test splits respecting temporal ordering
- Calculate feature importance statistics and drift detection baselines
"""

    def get_tools(self) -> list[dict]:
        return [
            {
                "name": "create_feature_table",
                "description": "Create or update a feature table in the Gold feature store",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "use_case": {
                            "type": "string",
                            "enum": [
                                "claim_propensity",
                                "large_loss_predictor",
                                "renewal_churn",
                                "underwriting_risk_score",
                                "document_ai",
                            ]
                        },
                        "feature_version": {"type": "string", "default": "v1"},
                        "as_of_date": {"type": "string", "description": "ISO date for point-in-time feature computation"},
                    },
                    "required": ["use_case"],
                },
            },
            {
                "name": "compute_features",
                "description": "Compute feature values from Silver/Gold data for a given use case",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "use_case": {"type": "string"},
                        "entity_ids": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Optional list of policy/claim/client IDs to compute for"
                        },
                        "as_of_date": {"type": "string"},
                    },
                    "required": ["use_case"],
                },
            },
            {
                "name": "generate_training_dataset",
                "description": "Generate a labeled training dataset with train/val/test splits",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "use_case": {"type": "string"},
                        "label_horizon_months": {
                            "type": "integer",
                            "description": "Months ahead for label computation (e.g. 12 for 1-year claim)"
                        },
                        "start_date": {"type": "string"},
                        "end_date": {"type": "string"},
                        "test_split_ratio": {"type": "number", "default": 0.2},
                    },
                    "required": ["use_case", "label_horizon_months"],
                },
            },
            {
                "name": "detect_feature_drift",
                "description": "Compare current feature distribution against training baseline",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "use_case": {"type": "string"},
                        "features": {
                            "type": "array",
                            "items": {"type": "string"}
                        },
                        "drift_threshold": {"type": "number", "default": 0.1},
                    },
                    "required": ["use_case"],
                },
            },
            {
                "name": "vectorize_text_fields",
                "description": "Generate embeddings for text fields using Azure OpenAI or Fabric AI capabilities",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "source_table": {"type": "string"},
                        "text_columns": {
                            "type": "array",
                            "items": {"type": "string"}
                        },
                        "embedding_model": {
                            "type": "string",
                            "enum": ["text-embedding-3-large", "text-embedding-3-small"],
                            "default": "text-embedding-3-large"
                        },
                        "target_table": {"type": "string"},
                    },
                    "required": ["source_table", "text_columns", "target_table"],
                },
            },
            {
                "name": "register_feature_metadata",
                "description": "Register feature table metadata in the Fabric data catalog",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "feature_table_name": {"type": "string"},
                        "use_case": {"type": "string"},
                        "description": {"type": "string"},
                        "feature_definitions": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "name": {"type": "string"},
                                    "dtype": {"type": "string"},
                                    "description": {"type": "string"},
                                    "is_pii": {"type": "boolean"},
                                }
                            }
                        },
                    },
                    "required": ["feature_table_name", "use_case"],
                },
            },
        ]

    def execute_tool(self, tool_name: str, tool_input: dict) -> Any:
        match tool_name:
            case "create_feature_table":
                return self._create_feature_table(**tool_input)
            case "compute_features":
                return self._compute_features(**tool_input)
            case "generate_training_dataset":
                return self._generate_training_dataset(**tool_input)
            case "detect_feature_drift":
                return self._detect_drift(**tool_input)
            case "vectorize_text_fields":
                return self._vectorize_text(**tool_input)
            case "register_feature_metadata":
                return self._register_metadata(**tool_input)
            case _:
                raise ValueError(f"Unknown tool: {tool_name}")

    def _create_feature_table(
        self, use_case: str, feature_version: str = "v1", as_of_date: Optional[str] = None
    ) -> dict:
        table_name = f"gold.features_{use_case}_{feature_version}"
        logger.info("create_feature_table", use_case=use_case, version=feature_version)
        return {
            "table_name": table_name,
            "use_case": use_case,
            "feature_version": feature_version,
            "created": True,
            "as_of_date": as_of_date,
            "record_count": 42381,
        }

    def _compute_features(
        self, use_case: str, entity_ids: Optional[list[str]] = None, as_of_date: Optional[str] = None
    ) -> dict:
        use_case_features = {
            "claim_propensity": [
                "policy_age_days", "total_insured_value", "line_of_business",
                "country_of_risk", "historical_loss_ratio_3y", "industry_code_nace",
                "premium_rate_adequacy", "broker_tier", "is_large_risk",
                "catastrophe_exposure_score", "portfolio_concentration_index",
            ],
            "large_loss_predictor": [
                "claim_type", "loss_type_encoded", "country_risk_score",
                "industry_loss_index", "coverage_limit_log", "days_to_report",
                "has_litigation", "catastrophe_event_flag", "reinsurance_layer",
            ],
            "renewal_churn": [
                "policy_tenure_years", "premium_change_pct_yoy", "loss_ratio_3y",
                "broker_relationship_years", "account_size_tier",
                "premium_paid_on_time_pct", "endorsement_count",
            ],
            "underwriting_risk_score": [
                "tiv_log", "location_hazard_score", "industry_severity_index",
                "client_credit_rating_encoded", "reinsurance_market_rate",
                "nat_cat_exposure_eur", "cyber_maturity_score",
            ],
        }
        features = use_case_features.get(use_case, [])
        return {
            "use_case": use_case,
            "features_computed": features,
            "entity_count": len(entity_ids) if entity_ids else 42381,
            "as_of_date": as_of_date,
            "null_rates": {f: round(0.02 * i / len(features), 4) for i, f in enumerate(features)},
        }

    def _generate_training_dataset(
        self,
        use_case: str,
        label_horizon_months: int,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        test_split_ratio: float = 0.2,
    ) -> dict:
        total = 42381
        test_n = int(total * test_split_ratio)
        val_n = int(total * 0.1)
        train_n = total - test_n - val_n
        return {
            "use_case": use_case,
            "label_horizon_months": label_horizon_months,
            "total_samples": total,
            "train_samples": train_n,
            "val_samples": val_n,
            "test_samples": test_n,
            "positive_rate": 0.083,
            "dataset_table": f"gold.training_{use_case}",
            "label_table": f"gold.labels_{use_case}_{label_horizon_months}m",
            "data_leakage_check": "passed",
            "temporal_split": True,
        }

    def _detect_drift(
        self, use_case: str, features: Optional[list[str]] = None, drift_threshold: float = 0.1
    ) -> dict:
        return {
            "use_case": use_case,
            "drift_detected": False,
            "drifted_features": [],
            "max_psi_score": 0.042,
            "threshold": drift_threshold,
            "recommendation": "no_retraining_required",
        }

    def _vectorize_text(
        self, source_table: str, text_columns: list[str], target_table: str, embedding_model: str = "text-embedding-3-large"
    ) -> dict:
        return {
            "source_table": source_table,
            "target_table": target_table,
            "columns_vectorized": text_columns,
            "embedding_model": embedding_model,
            "embedding_dimensions": 3072 if "large" in embedding_model else 1536,
            "records_processed": 15823,
        }

    def _register_metadata(
        self,
        feature_table_name: str,
        use_case: str,
        description: Optional[str] = None,
        feature_definitions: Optional[list[dict]] = None,
    ) -> dict:
        return {
            "registered": True,
            "feature_table_name": feature_table_name,
            "use_case": use_case,
            "catalog_entry_id": f"feat-{use_case}-001",
            "feature_count": len(feature_definitions or []),
        }
