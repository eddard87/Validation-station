from __future__ import annotations

import uuid
from collections import deque
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Optional
import structlog

logger = structlog.get_logger(__name__)


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    SKIPPED = "skipped"
    CANCELLED = "cancelled"


class Task:
    def __init__(
        self,
        name: str,
        agent_name: str,
        task_description: str,
        context: Optional[dict] = None,
        depends_on: Optional[list[str]] = None,
        retry_on_failure: bool = True,
        max_retries: int = 2,
    ) -> None:
        self.task_id = str(uuid.uuid4())
        self.name = name
        self.agent_name = agent_name
        self.task_description = task_description
        self.context = context or {}
        self.depends_on = depends_on or []
        self.retry_on_failure = retry_on_failure
        self.max_retries = max_retries
        self.status = TaskStatus.PENDING
        self.attempt_count = 0
        self.result: Optional[Any] = None
        self.error: Optional[str] = None
        self.created_at = datetime.utcnow()
        self.started_at: Optional[datetime] = None
        self.completed_at: Optional[datetime] = None

    @property
    def duration_seconds(self) -> Optional[float]:
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None

    def to_dict(self) -> dict:
        return {
            "task_id": self.task_id,
            "name": self.name,
            "agent_name": self.agent_name,
            "status": self.status.value,
            "attempt_count": self.attempt_count,
            "depends_on": self.depends_on,
            "duration_seconds": self.duration_seconds,
            "error": self.error,
            "created_at": self.created_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }


class TaskManager:
    """
    Manages a DAG of tasks for the InsureCo data platform pipeline.
    Handles dependency resolution, retries, and execution tracking.
    """

    def __init__(self) -> None:
        self._tasks: dict[str, Task] = {}
        self._execution_log: list[dict] = []

    def add_task(self, task: Task) -> str:
        self._tasks[task.name] = task
        logger.info("task_added", name=task.name, agent=task.agent_name, depends_on=task.depends_on)
        return task.task_id

    def add_daily_pipeline_tasks(self, source_systems: Optional[list[str]] = None) -> None:
        """Pre-populate the standard daily pipeline task graph."""
        systems = source_systems or ["policy_management", "claims_management", "billing", "crm"]

        # Ingestion tasks (no dependencies, can run in parallel)
        for system in systems:
            self.add_task(Task(
                name=f"ingest_{system}",
                agent_name="ingestion",
                task_description=f"Incremental ingestion from {system}",
                context={"source_system": system},
            ))

        # Bronze quality checks (depend on ingestion)
        ingest_tasks = [f"ingest_{s}" for s in systems]
        for entity in ["policy", "claim", "client", "payment"]:
            self.add_task(Task(
                name=f"quality_bronze_{entity}",
                agent_name="quality",
                task_description=f"Validate Bronze layer for {entity}",
                context={"layer": "bronze", "entity_type": entity},
                depends_on=ingest_tasks,
            ))

        # Bronze→Silver transformations
        bronze_quality_tasks = [f"quality_bronze_{e}" for e in ["policy", "claim", "client", "payment"]]
        for entity in ["policy", "claim", "client", "broker", "payment"]:
            self.add_task(Task(
                name=f"transform_b2s_{entity}",
                agent_name="transformation",
                task_description=f"Bronze to Silver transformation for {entity}",
                depends_on=bronze_quality_tasks,
            ))

        # Silver quality checks
        b2s_tasks = [f"transform_b2s_{e}" for e in ["policy", "claim", "client", "broker", "payment"]]
        for entity in ["policy", "claim", "client"]:
            self.add_task(Task(
                name=f"quality_silver_{entity}",
                agent_name="quality",
                task_description=f"Validate Silver layer for {entity}",
                context={"layer": "silver", "entity_type": entity},
                depends_on=b2s_tasks,
            ))

        # Silver→Gold transformations
        silver_quality_tasks = [f"quality_silver_{e}" for e in ["policy", "claim", "client"]]
        for subject in ["underwriting", "claims", "finance", "crm"]:
            self.add_task(Task(
                name=f"transform_s2g_{subject}",
                agent_name="transformation",
                task_description=f"Silver to Gold for {subject} subject area",
                depends_on=silver_quality_tasks,
            ))

        # Gold quality
        s2g_tasks = [f"transform_s2g_{s}" for s in ["underwriting", "claims", "finance", "crm"]]
        self.add_task(Task(
            name="quality_gold",
            agent_name="quality",
            task_description="Validate Gold layer across all subject areas",
            context={"layer": "gold"},
            depends_on=s2g_tasks,
        ))

        # AI Readiness (depends on Gold quality)
        self.add_task(Task(
            name="ai_features_claim_propensity",
            agent_name="ai_readiness",
            task_description="Recompute claim propensity feature table",
            depends_on=["quality_gold"],
        ))
        self.add_task(Task(
            name="ai_features_renewal_churn",
            agent_name="ai_readiness",
            task_description="Recompute renewal churn feature table",
            depends_on=["quality_gold"],
        ))

        # BI Refresh (depends on Gold quality)
        self.add_task(Task(
            name="bi_refresh",
            agent_name="visualization",
            task_description="Refresh Power BI semantic model and check report freshness",
            depends_on=["quality_gold"],
        ))

    def _get_ready_tasks(self) -> list[Task]:
        """Return tasks whose dependencies have all succeeded."""
        ready = []
        for task in self._tasks.values():
            if task.status != TaskStatus.PENDING:
                continue
            deps_ok = all(
                self._tasks[dep].status == TaskStatus.SUCCEEDED
                for dep in task.depends_on
                if dep in self._tasks
            )
            if deps_ok:
                ready.append(task)
        return ready

    def get_dag_summary(self) -> dict:
        status_counts: dict[str, int] = {}
        for t in self._tasks.values():
            status_counts[t.status.value] = status_counts.get(t.status.value, 0) + 1
        return {
            "total_tasks": len(self._tasks),
            "status_counts": status_counts,
            "tasks": [t.to_dict() for t in self._tasks.values()],
        }

    def execute(self, dispatcher: Callable[[str, str, dict], Any]) -> dict:
        """
        Execute all tasks respecting dependency order.
        dispatcher(agent_name, task_description, context) -> result dict
        """
        max_iterations = len(self._tasks) * 2
        iteration = 0

        while iteration < max_iterations:
            iteration += 1
            ready = self._get_ready_tasks()
            if not ready:
                pending = [t for t in self._tasks.values() if t.status == TaskStatus.PENDING]
                if not pending:
                    break
                # Pending tasks with unresolvable dependencies → mark skipped
                for t in pending:
                    failed_deps = [
                        dep for dep in t.depends_on
                        if dep in self._tasks and self._tasks[dep].status == TaskStatus.FAILED
                    ]
                    if failed_deps:
                        t.status = TaskStatus.SKIPPED
                        logger.warning("task_skipped_due_to_dep_failure", task=t.name, failed_deps=failed_deps)
                break

            for task in ready:
                task.status = TaskStatus.RUNNING
                task.started_at = datetime.utcnow()
                task.attempt_count += 1
                logger.info("task_running", task=task.name, agent=task.agent_name, attempt=task.attempt_count)

                try:
                    result = dispatcher(task.agent_name, task.task_description, task.context)
                    task.result = result
                    task.status = TaskStatus.SUCCEEDED
                    logger.info("task_succeeded", task=task.name)
                except Exception as exc:
                    task.error = str(exc)
                    if task.retry_on_failure and task.attempt_count <= task.max_retries:
                        task.status = TaskStatus.PENDING
                        logger.warning("task_retrying", task=task.name, attempt=task.attempt_count, error=str(exc))
                    else:
                        task.status = TaskStatus.FAILED
                        logger.error("task_failed", task=task.name, error=str(exc))
                finally:
                    task.completed_at = datetime.utcnow()
                    self._execution_log.append(task.to_dict())

        return self.get_dag_summary()
