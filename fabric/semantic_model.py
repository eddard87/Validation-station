from __future__ import annotations

from typing import Any, Optional
import httpx
import structlog

logger = structlog.get_logger(__name__)


class SemanticModelClient:
    """
    Manages Power BI / Fabric semantic models via XMLA and REST endpoints.
    """

    POWERBI_API = "https://api.powerbi.com/v1.0/myorg"

    def __init__(self, workspace_id: str, access_token: str) -> None:
        self.workspace_id = workspace_id
        self._http = httpx.Client(
            base_url=self.POWERBI_API,
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=120.0,
        )

    def refresh_dataset(
        self,
        dataset_id: str,
        notify_option: str = "NoNotification",
        objects: Optional[list[dict]] = None,
    ) -> str:
        payload: dict[str, Any] = {"notifyOption": notify_option}
        if objects:
            payload["objects"] = objects
        resp = self._http.post(
            f"/groups/{self.workspace_id}/datasets/{dataset_id}/refreshes",
            json=payload,
        )
        resp.raise_for_status()
        refresh_id = resp.headers.get("x-ms-request-id", "unknown")
        logger.info("semantic_model_refresh", dataset_id=dataset_id, refresh_id=refresh_id)
        return refresh_id

    def get_refresh_history(self, dataset_id: str, top: int = 10) -> list[dict[str, Any]]:
        resp = self._http.get(
            f"/groups/{self.workspace_id}/datasets/{dataset_id}/refreshes",
            params={"$top": top},
        )
        resp.raise_for_status()
        return resp.json().get("value", [])

    def list_datasets(self) -> list[dict[str, Any]]:
        resp = self._http.get(f"/groups/{self.workspace_id}/datasets")
        resp.raise_for_status()
        return resp.json().get("value", [])

    def execute_dax(self, dataset_id: str, dax_query: str) -> list[dict[str, Any]]:
        """Execute a DAX query against a semantic model and return rows."""
        resp = self._http.post(
            f"/groups/{self.workspace_id}/datasets/{dataset_id}/executeQueries",
            json={
                "queries": [{"query": dax_query}],
                "serializerSettings": {"includeNulls": True},
            },
        )
        resp.raise_for_status()
        results = resp.json()
        tables = results.get("results", [{}])[0].get("tables", [{}])
        return tables[0].get("rows", []) if tables else []

    def push_rows(
        self,
        dataset_id: str,
        table_name: str,
        rows: list[dict[str, Any]],
    ) -> None:
        resp = self._http.post(
            f"/groups/{self.workspace_id}/datasets/{dataset_id}/tables/{table_name}/rows",
            json={"rows": rows},
        )
        resp.raise_for_status()
        logger.info("push_rows", dataset_id=dataset_id, table=table_name, rows=len(rows))
