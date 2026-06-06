from __future__ import annotations

import os
from enum import Enum
from pathlib import PurePosixPath
from typing import Any, Optional
import structlog

logger = structlog.get_logger(__name__)


class MedallionLayer(str, Enum):
    BRONZE = "bronze"
    SILVER = "silver"
    GOLD = "gold"


class LakehouseClient:
    """
    Abstraction over Microsoft Fabric OneLake / Lakehouse operations.
    In Fabric notebooks use mssparkutils; outside use the ADLS Gen2 SDK.
    """

    ONELAKE_ENDPOINT = "https://onelake.dfs.fabric.microsoft.com"

    def __init__(
        self,
        workspace_id: str,
        layer: MedallionLayer,
        lakehouse_id: str,
        credential: Optional[Any] = None,
    ) -> None:
        self.workspace_id = workspace_id
        self.layer = layer
        self.lakehouse_id = lakehouse_id
        self._credential = credential
        self._spark = None
        self._fs_client = None

    @classmethod
    def from_config(cls, config: dict, layer: MedallionLayer) -> "LakehouseClient":
        layer_cfg = config["lakehouse"][layer.value]
        return cls(
            workspace_id=config["workspace"]["id"],
            layer=layer,
            lakehouse_id=os.path.expandvars(layer_cfg["id"]),
        )

    def _base_path(self) -> str:
        return (
            f"{self.ONELAKE_ENDPOINT}/{self.workspace_id}/"
            f"{self.lakehouse_id}/Files"
        )

    def _table_path(self, table_name: str, database: Optional[str] = None) -> str:
        return (
            f"{self.ONELAKE_ENDPOINT}/{self.workspace_id}/"
            f"{self.lakehouse_id}/Tables/{database or ''}/{table_name}"
        )

    def get_spark(self):
        """Returns active SparkSession (available inside Fabric notebooks)."""
        if self._spark is None:
            try:
                from pyspark.sql import SparkSession
                self._spark = SparkSession.getActiveSession()
                if self._spark is None:
                    self._spark = SparkSession.builder.getOrCreate()
            except ImportError:
                logger.warning("PySpark not available outside Fabric environment")
        return self._spark

    def read_delta(
        self,
        table_name: str,
        filters: Optional[list] = None,
        columns: Optional[list[str]] = None,
    ):
        """Read a Delta table from the lakehouse."""
        spark = self.get_spark()
        path = self._table_path(table_name)
        df = spark.read.format("delta").load(path)
        if filters:
            from pyspark.sql.functions import col
            for f in filters:
                df = df.filter(f)
        if columns:
            df = df.select(columns)
        logger.info("read_delta", layer=self.layer, table=table_name)
        return df

    def write_delta(
        self,
        df,
        table_name: str,
        mode: str = "append",
        partition_by: Optional[list[str]] = None,
        merge_schema: bool = False,
        optimize_write: bool = True,
    ) -> None:
        """Write a DataFrame as Delta to the lakehouse."""
        path = self._table_path(table_name)
        writer = (
            df.write.format("delta")
            .mode(mode)
            .option("overwriteSchema", str(merge_schema).lower())
            .option("optimizeWrite", str(optimize_write).lower())
        )
        if partition_by:
            writer = writer.partitionBy(*partition_by)
        writer.save(path)
        logger.info("write_delta", layer=self.layer, table=table_name, mode=mode, rows=df.count())

    def upsert_delta(
        self,
        new_df,
        table_name: str,
        merge_keys: list[str],
        partition_by: Optional[list[str]] = None,
    ) -> None:
        """MERGE INTO for SCD Type 1 upserts."""
        from delta.tables import DeltaTable
        spark = self.get_spark()
        path = self._table_path(table_name)

        if not DeltaTable.isDeltaTable(spark, path):
            self.write_delta(new_df, table_name, mode="overwrite", partition_by=partition_by)
            return

        dt = DeltaTable.forPath(spark, path)
        merge_condition = " AND ".join(
            f"target.{k} = source.{k}" for k in merge_keys
        )
        (
            dt.alias("target")
            .merge(new_df.alias("source"), merge_condition)
            .whenMatchedUpdateAll()
            .whenNotMatchedInsertAll()
            .execute()
        )
        logger.info("upsert_delta", layer=self.layer, table=table_name, keys=merge_keys)

    def optimize_table(self, table_name: str, zorder_columns: Optional[list[str]] = None) -> None:
        """Run OPTIMIZE + optional ZORDER on a Delta table."""
        spark = self.get_spark()
        path = self._table_path(table_name)
        zorder_clause = ""
        if zorder_columns:
            cols = ", ".join(zorder_columns)
            zorder_clause = f" ZORDER BY ({cols})"
        spark.sql(f"OPTIMIZE delta.`{path}`{zorder_clause}")
        logger.info("optimize_table", layer=self.layer, table=table_name)

    def vacuum_table(self, table_name: str, retention_hours: int = 168) -> None:
        spark = self.get_spark()
        path = self._table_path(table_name)
        spark.sql(f"VACUUM delta.`{path}` RETAIN {retention_hours} HOURS")

    def table_exists(self, table_name: str) -> bool:
        spark = self.get_spark()
        path = self._table_path(table_name)
        try:
            from delta.tables import DeltaTable
            return DeltaTable.isDeltaTable(spark, path)
        except Exception:
            return False

    def get_table_stats(self, table_name: str) -> dict[str, Any]:
        spark = self.get_spark()
        df = self.read_delta(table_name)
        return {
            "table": table_name,
            "layer": self.layer.value,
            "row_count": df.count(),
            "schema": df.schema.simpleString(),
        }
