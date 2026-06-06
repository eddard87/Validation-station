from __future__ import annotations

from enum import Enum
from typing import Any, Optional
import httpx
import structlog
from tenacity import retry, stop_after_attempt, wait_exponential

logger = structlog.get_logger(__name__)


class PipelineStatus(str, Enum):
    QUEUED = "Queued"
    IN_PROGRESS = "InProgress"
    SUCCEEDED = "Succeeded"
    FAILED = "Failed"
    CANCELLED = "Cancelled"


class PipelineClient:
    """
    Interacts with Microsoft Fabric Data Factory pipelines via REST API.
    """

    FABRIC_API_BASE = "https://api.fabric.microsoft.com/v1"

    def __init__(
        self,
        workspace_id: str,
        access_token: str,
    ) -> None:
        self.workspace_id = workspace_id
        self._token = access_token
        self._http = httpx.Client(
            base_url=self.FABRIC_API_BASE,
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=60.0,
        )

    def _url(self, path: str) -> str:
        return f"/workspaces/{self.workspace_id}{path}"

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def trigger_pipeline(
        self,
        pipeline_name: str,
        parameters: Optional[dict[str, Any]] = None,
    ) -> str:
        """Trigger a pipeline run and return the run ID."""
        payload = {"parameters": parameters or {}}
        resp = self._http.post(
            self._url(f"/items/{pipeline_name}/jobs/instances?jobType=Pipeline"),
            json=payload,
        )
        resp.raise_for_status()
        run_id = resp.headers.get("x-ms-job-id", resp.json().get("id"))
        logger.info("pipeline_triggered", pipeline=pipeline_name, run_id=run_id)
        return run_id

    def get_pipeline_status(self, pipeline_name: str, run_id: str) -> PipelineStatus:
        resp = self._http.get(
            self._url(f"/items/{pipeline_name}/jobs/instances/{run_id}")
        )
        resp.raise_for_status()
        status_str = resp.json().get("status", "Unknown")
        return PipelineStatus(status_str)

    def wait_for_completion(
        self,
        pipeline_name: str,
        run_id: str,
        poll_interval_seconds: int = 30,
        timeout_seconds: int = 3600,
    ) -> PipelineStatus:
        import time
        elapsed = 0
        while elapsed < timeout_seconds:
            status = self.get_pipeline_status(pipeline_name, run_id)
            if status in (PipelineStatus.SUCCEEDED, PipelineStatus.FAILED, PipelineStatus.CANCELLED):
                logger.info("pipeline_completed", pipeline=pipeline_name, run_id=run_id, status=status)
                return status
            time.sleep(poll_interval_seconds)
            elapsed += poll_interval_seconds
        raise TimeoutError(f"Pipeline {pipeline_name} run {run_id} timed out after {timeout_seconds}s")

    def list_pipelines(self) -> list[dict[str, Any]]:
        resp = self._http.get(self._url("/items?type=DataPipeline"))
        resp.raise_for_status()
        return resp.json().get("value", [])

    def get_run_details(self, pipeline_name: str, run_id: str) -> dict[str, Any]:
        resp = self._http.get(
            self._url(f"/items/{pipeline_name}/jobs/instances/{run_id}")
        )
        resp.raise_for_status()
        return resp.json()
