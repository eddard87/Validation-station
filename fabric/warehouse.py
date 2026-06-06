from __future__ import annotations

from typing import Any, Optional
import structlog

logger = structlog.get_logger(__name__)


class WarehouseClient:
    """
    Interacts with Fabric Warehouse (T-SQL endpoint) for Gold layer serving.
    Uses pyodbc or the Fabric SQL endpoint connection string.
    """

    def __init__(self, connection_string: str) -> None:
        self._conn_str = connection_string
        self._conn = None

    def _get_connection(self):
        if self._conn is None:
            try:
                import pyodbc
                self._conn = pyodbc.connect(self._conn_str, autocommit=True)
            except ImportError:
                raise RuntimeError("pyodbc is required for Fabric Warehouse connectivity")
        return self._conn

    def execute_query(self, sql: str, params: Optional[tuple] = None) -> list[dict[str, Any]]:
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(sql, params or ())
        columns = [col[0] for col in cursor.description] if cursor.description else []
        rows = cursor.fetchall()
        return [dict(zip(columns, row)) for row in rows]

    def execute_non_query(self, sql: str, params: Optional[tuple] = None) -> int:
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(sql, params or ())
        return cursor.rowcount

    def bulk_insert(
        self,
        table_name: str,
        records: list[dict[str, Any]],
        batch_size: int = 1000,
    ) -> int:
        if not records:
            return 0
        columns = list(records[0].keys())
        placeholders = ", ".join("?" * len(columns))
        cols_str = ", ".join(f"[{c}]" for c in columns)
        sql = f"INSERT INTO {table_name} ({cols_str}) VALUES ({placeholders})"
        conn = self._get_connection()
        cursor = conn.cursor()
        total = 0
        for i in range(0, len(records), batch_size):
            batch = records[i:i + batch_size]
            values = [tuple(r[c] for c in columns) for r in batch]
            cursor.executemany(sql, values)
            total += len(batch)
        logger.info("bulk_insert", table=table_name, rows=total)
        return total

    def get_table_row_count(self, schema: str, table: str) -> int:
        result = self.execute_query(
            f"SELECT COUNT(1) AS cnt FROM [{schema}].[{table}]"
        )
        return result[0]["cnt"] if result else 0

    def create_or_replace_view(self, view_name: str, view_sql: str) -> None:
        self.execute_non_query(f"CREATE OR ALTER VIEW {view_name} AS {view_sql}")
        logger.info("view_created", view=view_name)

    def close(self) -> None:
        if self._conn:
            self._conn.close()
            self._conn = None
