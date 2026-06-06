from __future__ import annotations

from typing import Any, Optional
import structlog

from agents.base_agent import BaseAgent

logger = structlog.get_logger(__name__)


class VisualizationAgent(BaseAgent):

    def __init__(self, config: dict, fabric_config: dict) -> None:
        super().__init__(
            name="VisualizationAgent",
            description="Manages Power BI semantic models and auto-generates InsureCo insurance reports",
            config=config,
        )
        self._fabric_cfg = fabric_config

    @property
    def system_prompt(self) -> str:
        return """You are an expert Power BI and data visualisation engineer for Corporate Insurance Platform.
You are the VISUALIZATION AGENT, responsible for the BI and reporting layer on Microsoft Fabric.

Key dashboards and reports for Corporate Insurance Platform:
1. UNDERWRITING DASHBOARD - written premium, GWP by LoB, new business vs renewal, rate changes
2. CLAIMS DASHBOARD - loss ratio by LoB/country, large losses, catastrophe events, IBNR trends
3. PORTFOLIO DASHBOARD - TIV concentration, geographic exposure, industry concentration
4. FINANCIAL DASHBOARD - combined ratio, expense ratio, profit/loss by segment
5. BROKER PERFORMANCE - production by broker, loss ratio by broker, retention rates
6. REGULATORY REPORTING - Solvency II QRTs, IVASS statistical returns

KPIs to always include:
- Gross Written Premium (GWP)
- Net Written Premium (NWP) after reinsurance
- Loss Ratio (incurred losses / earned premium)
- Combined Ratio (loss ratio + expense ratio)
- Large Loss Frequency (claims > EUR 500K per 1000 policies)
- Renewal Retention Rate
- New Business Hit Rate
- Average Premium per Policy

Semantic model conventions:
- All monetary measures in EUR by default with currency slicer
- All dates use the dim_date table with fiscal year (Jan-Dec)
- Line of business hierarchy: LoB Group > Line > Sub-line
- Geography hierarchy: Region > Country > City
- Always use CALCULATE with proper FILTER context
- Use USERELATIONSHIP for role-playing dimensions (e.g., inception_date vs expiration_date)

When generating DAX measures, always:
- Use DIVIDE() instead of / to handle divide-by-zero
- Add format strings for currency: "#,0.0,, EUR M"
- Add format strings for percentages: "0.0%"
- Include prior period comparison measures with _PY suffix
"""

    def get_tools(self) -> list[dict]:
        return [
            {
                "name": "refresh_semantic_model",
                "description": "Trigger a full or partial refresh of the Power BI semantic model",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "dataset_id": {"type": "string"},
                        "tables": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Specific tables to refresh; omit for full refresh"
                        },
                        "notify_option": {
                            "type": "string",
                            "enum": ["NoNotification", "MailOnFailure", "MailOnCompletion"],
                            "default": "MailOnFailure"
                        },
                    },
                    "required": ["dataset_id"],
                },
            },
            {
                "name": "generate_dax_measure",
                "description": "Generate a DAX measure for a given KPI",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "kpi_name": {
                            "type": "string",
                            "enum": [
                                "gross_written_premium",
                                "net_written_premium",
                                "loss_ratio",
                                "combined_ratio",
                                "large_loss_frequency",
                                "renewal_retention_rate",
                                "new_business_hit_rate",
                                "average_premium",
                                "ibnr_reserve",
                                "reinsurance_recoverable",
                            ]
                        },
                        "time_grain": {
                            "type": "string",
                            "enum": ["day", "month", "quarter", "year"],
                            "default": "month"
                        },
                        "include_py_comparison": {"type": "boolean", "default": True},
                    },
                    "required": ["kpi_name"],
                },
            },
            {
                "name": "execute_dax_query",
                "description": "Execute a DAX query against the semantic model and return results",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "dataset_id": {"type": "string"},
                        "dax_query": {"type": "string"},
                    },
                    "required": ["dataset_id", "dax_query"],
                },
            },
            {
                "name": "check_report_freshness",
                "description": "Check when each report was last refreshed and flag stale data",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "max_stale_hours": {"type": "integer", "default": 24},
                    },
                },
            },
            {
                "name": "generate_regulatory_extract",
                "description": "Generate a regulatory data extract (Solvency II / IVASS format)",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "report_type": {
                            "type": "string",
                            "enum": ["solvency_ii_qrt", "ivass_statistical", "ifrs17_csg"]
                        },
                        "reference_period": {
                            "type": "string",
                            "description": "YYYY-MM accounting period"
                        },
                        "currency": {"type": "string", "default": "EUR"},
                    },
                    "required": ["report_type", "reference_period"],
                },
            },
        ]

    def execute_tool(self, tool_name: str, tool_input: dict) -> Any:
        match tool_name:
            case "refresh_semantic_model":
                return self._refresh_model(**tool_input)
            case "generate_dax_measure":
                return self._generate_dax(**tool_input)
            case "execute_dax_query":
                return self._execute_dax(**tool_input)
            case "check_report_freshness":
                return self._check_freshness(**tool_input)
            case "generate_regulatory_extract":
                return self._regulatory_extract(**tool_input)
            case _:
                raise ValueError(f"Unknown tool: {tool_name}")

    def _refresh_model(
        self, dataset_id: str, tables: Optional[list[str]] = None, notify_option: str = "MailOnFailure"
    ) -> dict:
        logger.info("refresh_semantic_model", dataset_id=dataset_id, tables=tables)
        return {"refresh_id": "ref-001", "status": "Completed", "duration_seconds": 187}

    def _generate_dax(
        self, kpi_name: str, time_grain: str = "month", include_py_comparison: bool = True
    ) -> dict:
        dax_templates = {
            "gross_written_premium": (
                "[GWP EUR M] = \n"
                "DIVIDE(\n"
                "    CALCULATE(SUM(fact_premium[written_premium_eur])),\n"
                "    1000000\n"
                ")"
            ),
            "loss_ratio": (
                "[Loss Ratio] = \n"
                "DIVIDE(\n"
                "    CALCULATE(SUM(fact_claim[total_incurred_eur])),\n"
                "    CALCULATE(SUM(fact_premium[earned_premium_eur])),\n"
                "    BLANK()\n"
                ")"
            ),
            "combined_ratio": (
                "[Combined Ratio] = \n"
                "DIVIDE(\n"
                "    CALCULATE(SUM(fact_claim[total_incurred_eur]))\n"
                "    + CALCULATE(SUM(fact_expense[total_expenses_eur])),\n"
                "    CALCULATE(SUM(fact_premium[earned_premium_eur])),\n"
                "    BLANK()\n"
                ")"
            ),
            "renewal_retention_rate": (
                "[Renewal Retention Rate] = \n"
                "DIVIDE(\n"
                "    COUNTROWS(FILTER(dim_policy, dim_policy[is_renewal] = TRUE())),\n"
                "    COUNTROWS(FILTER(dim_policy, dim_policy[prior_period_id] <> BLANK())),\n"
                "    BLANK()\n"
                ")"
            ),
        }
        dax_code = dax_templates.get(kpi_name, f"-- DAX for {kpi_name} to be generated")
        py_measure = ""
        if include_py_comparison:
            py_measure = f"[{kpi_name} PY] = CALCULATE([{kpi_name}], SAMEPERIODLASTYEAR(dim_date[date]))"
        return {
            "kpi_name": kpi_name,
            "dax_measure": dax_code,
            "py_comparison_measure": py_measure if include_py_comparison else None,
            "format_string": "0.0%" if "ratio" in kpi_name or "rate" in kpi_name else "#,0.0,, EUR M",
        }

    def _execute_dax(self, dataset_id: str, dax_query: str) -> dict:
        return {
            "dataset_id": dataset_id,
            "query": dax_query[:100] + "...",
            "rows": [],
            "note": "Connect live semantic model to execute real DAX",
        }

    def _check_freshness(self, max_stale_hours: int = 24) -> dict:
        from datetime import datetime, timedelta
        reports = [
            {"name": "Underwriting Dashboard", "last_refresh": (datetime.utcnow() - timedelta(hours=6)).isoformat(), "is_stale": False},
            {"name": "Claims Dashboard", "last_refresh": (datetime.utcnow() - timedelta(hours=3)).isoformat(), "is_stale": False},
            {"name": "Portfolio Dashboard", "last_refresh": (datetime.utcnow() - timedelta(hours=26)).isoformat(), "is_stale": True},
        ]
        stale = [r for r in reports if r["is_stale"]]
        return {"reports": reports, "stale_count": len(stale), "stale_reports": [r["name"] for r in stale]}

    def _regulatory_extract(self, report_type: str, reference_period: str, currency: str = "EUR") -> dict:
        return {
            "report_type": report_type,
            "reference_period": reference_period,
            "currency": currency,
            "status": "generated",
            "output_path": f"onelake/regulatory/{report_type}/{reference_period}/extract.xlsx",
            "validation_status": "passed",
        }
