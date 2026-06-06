from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Optional
import structlog

logger = structlog.get_logger(__name__)


class PipelineMonitor:
    """
    Collects and exposes metrics for the InsureCo data platform pipeline runs.
    In production connects to Azure Monitor / Fabric monitoring APIs.
    """

    def __init__(self) -> None:
        self._metrics: list[dict[str, Any]] = []
        self._alerts: list[dict[str, Any]] = []

    def record_run(
        self,
        pipeline_name: str,
        status: str,
        duration_seconds: float,
        records_processed: int = 0,
        layer: Optional[str] = None,
        entity_type: Optional[str] = None,
        dq_score: Optional[float] = None,
        error: Optional[str] = None,
    ) -> None:
        metric = {
            "timestamp": datetime.utcnow().isoformat(),
            "pipeline_name": pipeline_name,
            "status": status,
            "duration_seconds": duration_seconds,
            "records_processed": records_processed,
            "layer": layer,
            "entity_type": entity_type,
            "dq_score": dq_score,
            "error": error,
        }
        self._metrics.append(metric)
        logger.info("metric_recorded", **{k: v for k, v in metric.items() if v is not None})

        if status == "failed":
            self.raise_alert(
                severity="critical",
                title=f"Pipeline failed: {pipeline_name}",
                message=error or "Unknown error",
                pipeline_name=pipeline_name,
            )
        if dq_score is not None and dq_score < 0.95:
            self.raise_alert(
                severity="warning",
                title=f"Low DQ score: {pipeline_name}",
                message=f"Data quality score {dq_score:.3f} is below threshold 0.95",
                pipeline_name=pipeline_name,
            )

    def raise_alert(
        self,
        severity: str,
        title: str,
        message: str,
        pipeline_name: Optional[str] = None,
    ) -> None:
        alert = {
            "alert_id": f"ALT-{len(self._alerts):04d}",
            "timestamp": datetime.utcnow().isoformat(),
            "severity": severity,
            "title": title,
            "message": message,
            "pipeline_name": pipeline_name,
            "acknowledged": False,
        }
        self._alerts.append(alert)
        logger.warning("alert_raised", severity=severity, title=title)
        # In production: send to Teams webhook / PagerDuty / Azure Monitor

    def get_platform_metrics(self, hours_back: int = 24) -> dict[str, Any]:
        cutoff = datetime.utcnow() - timedelta(hours=hours_back)
        recent = [
            m for m in self._metrics
            if datetime.fromisoformat(m["timestamp"]) >= cutoff
        ]
        if not recent:
            return {"period_hours": hours_back, "runs": 0, "metrics": []}

        succeeded = [m for m in recent if m["status"] == "succeeded"]
        failed = [m for m in recent if m["status"] == "failed"]
        dq_scores = [m["dq_score"] for m in recent if m.get("dq_score") is not None]

        return {
            "period_hours": hours_back,
            "runs": len(recent),
            "succeeded": len(succeeded),
            "failed": len(failed),
            "success_rate": len(succeeded) / len(recent) if recent else 0,
            "avg_duration_seconds": sum(m["duration_seconds"] for m in recent) / len(recent),
            "total_records_processed": sum(m["records_processed"] for m in recent),
            "avg_dq_score": sum(dq_scores) / len(dq_scores) if dq_scores else None,
            "open_alerts": len([a for a in self._alerts if not a["acknowledged"]]),
            "metrics": recent[-50:],
        }

    def get_sla_report(self) -> dict[str, Any]:
        """Check if daily pipeline completed within SLA window (by 08:00 CET)."""
        today = datetime.utcnow().date()
        today_runs = [
            m for m in self._metrics
            if m["timestamp"].startswith(today.isoformat())
        ]
        pipeline_completed = any(
            m["status"] == "succeeded" and m["pipeline_name"] == "daily_full_pipeline"
            for m in today_runs
        )
        return {
            "date": today.isoformat(),
            "sla_window": "08:00 CET",
            "pipeline_completed_today": pipeline_completed,
            "sla_breached": not pipeline_completed,
            "runs_today": len(today_runs),
        }
