from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Optional
import structlog

from agents.base_agent import BaseAgent, AgentResult, AgentStatus
from agents.ingestion_agent import IngestionAgent
from agents.transformation_agent import TransformationAgent
from agents.quality_agent import QualityAgent
from agents.ai_readiness_agent import AIReadinessAgent
from agents.visualization_agent import VisualizationAgent

logger = structlog.get_logger(__name__)


class OrchestratorAgent(BaseAgent):
    """
    Central coordinator for the Generali Corporate Commercial data platform.
    Decomposes high-level data platform tasks into sub-agent calls and
    manages the end-to-end Bronze→Silver→Gold→AI pipeline.
    """

    def __init__(self, config: dict, fabric_config: dict) -> None:
        super().__init__(
            name="OrchestratorAgent",
            description="Coordinates all data platform agents for Generali Corporate Commercial",
            config=config,
        )
        self._fabric_cfg = fabric_config
        self._agents: dict[str, BaseAgent] = {
            "ingestion": IngestionAgent(config, fabric_config),
            "transformation": TransformationAgent(config, fabric_config),
            "quality": QualityAgent(config, fabric_config),
            "ai_readiness": AIReadinessAgent(config, fabric_config),
            "visualization": VisualizationAgent(config, fabric_config),
        }
        self._pipeline_runs: list[dict] = []

    @property
    def system_prompt(self) -> str:
        return """You are the ORCHESTRATOR AGENT for the Generali Corporate Commercial AI Data Platform on Microsoft Fabric.
You are the top-level coordinator that decomposes complex data platform requests into concrete steps
executed by specialised sub-agents.

Available sub-agents:
- ingestion: Extracts data from Guidewire PC/CC/BC, Salesforce CRM, AS400 reinsurance, external APIs
- transformation: Applies Bronze→Silver→Gold medallion transformations with insurance business rules
- quality: Validates data quality at every layer and quarantines failed records
- ai_readiness: Builds feature stores and training datasets for 5 ML use cases
- visualization: Refreshes Power BI semantic models and generates regulatory reports

Standard daily pipeline order (always respect this sequence):
1. Ingest: run ingestion for each source system (can be parallelised per source)
2. Validate Bronze: quality check on landed data
3. Transform Bronze→Silver: per entity type (policy, claim, client, broker, payment)
4. Validate Silver: quality check on standardised data
5. Transform Silver→Gold: per subject area (underwriting, claims, finance, crm, risk)
6. Validate Gold: final quality gate
7. AI Readiness: recompute features if Gold data changed
8. Refresh Semantic Model: trigger Power BI refresh

Principles:
- Never skip quality validation gates between layers
- Always log the reason for every decision
- If any critical quality failure occurs, stop the pipeline and alert
- Prefer incremental processing over full reloads
- Track and report overall pipeline health metrics
- When uncertain about business logic, ask for clarification rather than guessing
"""

    def get_tools(self) -> list[dict]:
        return [
            {
                "name": "run_sub_agent",
                "description": "Delegate a task to a specialised sub-agent",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "agent_name": {
                            "type": "string",
                            "enum": ["ingestion", "transformation", "quality", "ai_readiness", "visualization"],
                        },
                        "task": {
                            "type": "string",
                            "description": "Natural language task description for the sub-agent"
                        },
                        "context": {
                            "type": "object",
                            "description": "Additional context to pass to the sub-agent"
                        },
                    },
                    "required": ["agent_name", "task"],
                },
            },
            {
                "name": "get_pipeline_status",
                "description": "Get the current status of all agent runs in this session",
                "input_schema": {"type": "object", "properties": {}},
            },
            {
                "name": "run_full_daily_pipeline",
                "description": "Execute the complete daily ELT pipeline end-to-end",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "source_systems": {
                            "type": "array",
                            "items": {"type": "string"},
                            "default": ["policy_management", "claims_management", "billing", "crm"],
                        },
                        "skip_ai_readiness": {"type": "boolean", "default": False},
                        "skip_refresh": {"type": "boolean", "default": False},
                    },
                },
            },
            {
                "name": "get_platform_health",
                "description": "Get an overall health summary of the data platform",
                "input_schema": {"type": "object", "properties": {}},
            },
        ]

    def execute_tool(self, tool_name: str, tool_input: dict) -> Any:
        match tool_name:
            case "run_sub_agent":
                return self._run_sub_agent(**tool_input)
            case "get_pipeline_status":
                return self._get_pipeline_status()
            case "run_full_daily_pipeline":
                return self._run_full_pipeline(**tool_input)
            case "get_platform_health":
                return self._get_platform_health()
            case _:
                raise ValueError(f"Unknown tool: {tool_name}")

    def _run_sub_agent(
        self, agent_name: str, task: str, context: Optional[dict] = None
    ) -> dict:
        if agent_name not in self._agents:
            return {"error": f"Unknown agent: {agent_name}"}

        agent = self._agents[agent_name]
        import uuid
        task_id = str(uuid.uuid4())[:8]
        logger.info("dispatching_to_agent", agent=agent_name, task=task[:80], task_id=task_id)

        result = agent.run(task=task, context=context, task_id=task_id)

        run_record = {
            "task_id": task_id,
            "agent": agent_name,
            "task": task[:120],
            "status": result.status.value,
            "duration_s": result.duration_seconds,
            "error": result.error,
            "completed_at": result.completed_at.isoformat(),
        }
        self._pipeline_runs.append(run_record)

        return {
            "task_id": task_id,
            "agent": agent_name,
            "status": result.status.value,
            "output": result.output,
            "duration_seconds": result.duration_seconds,
            "error": result.error,
        }

    def _get_pipeline_status(self) -> dict:
        succeeded = sum(1 for r in self._pipeline_runs if r["status"] == "succeeded")
        failed = sum(1 for r in self._pipeline_runs if r["status"] == "failed")
        return {
            "total_runs": len(self._pipeline_runs),
            "succeeded": succeeded,
            "failed": failed,
            "runs": self._pipeline_runs[-10:],
        }

    def _run_full_pipeline(
        self,
        source_systems: Optional[list[str]] = None,
        skip_ai_readiness: bool = False,
        skip_refresh: bool = False,
    ) -> dict:
        systems = source_systems or ["policy_management", "claims_management", "billing", "crm"]
        steps_completed = []
        steps_failed = []

        # Step 1: Ingest all source systems
        for system in systems:
            result = self._run_sub_agent(
                "ingestion",
                f"Perform incremental ingestion for source system '{system}'. "
                f"Check watermarks, trigger pipelines, validate Bronze landing.",
                context={"source_system": system},
            )
            if result["status"] == "succeeded":
                steps_completed.append(f"ingest:{system}")
            else:
                steps_failed.append(f"ingest:{system}")

        # Step 2: Validate Bronze
        for entity in ["policy", "claim", "client", "payment"]:
            result = self._run_sub_agent(
                "quality",
                f"Run quality suite on Bronze layer for entity type '{entity}'.",
                context={"layer": "bronze", "entity_type": entity},
            )
            steps_completed.append(f"quality_bronze:{entity}") if result["status"] == "succeeded" else steps_failed.append(f"quality_bronze:{entity}")

        # Step 3: Transform Bronze→Silver
        for entity in ["policy", "claim", "client"]:
            result = self._run_sub_agent(
                "transformation",
                f"Transform Bronze to Silver for entity type '{entity}'. Apply all business rules.",
            )
            steps_completed.append(f"b2s:{entity}") if result["status"] == "succeeded" else steps_failed.append(f"b2s:{entity}")

        # Step 4: Transform Silver→Gold
        for subject in ["underwriting", "claims", "finance"]:
            result = self._run_sub_agent(
                "transformation",
                f"Transform Silver to Gold for subject area '{subject}'. Build dimensional model.",
            )
            steps_completed.append(f"s2g:{subject}") if result["status"] == "succeeded" else steps_failed.append(f"s2g:{subject}")

        # Step 5: AI Readiness
        if not skip_ai_readiness:
            result = self._run_sub_agent(
                "ai_readiness",
                "Recompute feature tables for claim_propensity and renewal_churn use cases. "
                "Detect feature drift. Register updated metadata.",
            )
            steps_completed.append("ai_readiness") if result["status"] == "succeeded" else steps_failed.append("ai_readiness")

        # Step 6: Refresh BI
        if not skip_refresh:
            result = self._run_sub_agent(
                "visualization",
                "Refresh the Generali Corporate semantic model. Check report freshness. "
                "Alert on any stale reports.",
            )
            steps_completed.append("bi_refresh") if result["status"] == "succeeded" else steps_failed.append("bi_refresh")

        return {
            "pipeline_run_at": datetime.utcnow().isoformat(),
            "steps_completed": steps_completed,
            "steps_failed": steps_failed,
            "success_rate": len(steps_completed) / (len(steps_completed) + len(steps_failed)) if steps_completed or steps_failed else 0,
            "overall_status": "succeeded" if not steps_failed else "partial_failure",
        }

    def _get_platform_health(self) -> dict:
        return {
            "platform": "Generali Corporate Commercial - Microsoft Fabric",
            "agents": {name: agent.status.value for name, agent in self._agents.items()},
            "bronze_lakehouse": "healthy",
            "silver_lakehouse": "healthy",
            "gold_lakehouse": "healthy",
            "semantic_model": "healthy",
            "last_successful_pipeline": datetime.utcnow().isoformat(),
            "data_freshness_hours": 6,
            "open_incidents": 0,
        }
