"""DuckDB Lakehouse connection manager and analytical query executor."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

import duckdb


class STFLakehouseClient:
    """Provides high-performance analytical queries against the DuckDB STF warehouse."""

    def __init__(self, db_path: Optional[Path | str] = None) -> None:
        if db_path is None:
            project_root = Path(__file__).resolve().parent.parent
            self.db_path = project_root / "data" / "curated" / "stf_warehouse.duckdb"
        else:
            self.db_path = Path(db_path)

        if not self.db_path.exists():
            # In memory or empty if not yet built
            self.db_path.parent.mkdir(parents=True, exist_ok=True)

    def get_connection(self, read_only: bool = True) -> duckdb.DuckDBPyConnection:
        """Returns a DuckDB connection."""
        return duckdb.connect(str(self.db_path), read_only=read_only)

    def query(self, sql: str, params: Optional[List[Any]] = None) -> List[Dict[str, Any]]:
        """Executes a SQL query and returns records as dictionaries."""
        with self.get_connection(read_only=True) as con:
            if params:
                cursor = con.execute(sql, params)
            else:
                cursor = con.execute(sql)
            columns = [desc[0] for desc in cursor.description]
            rows = cursor.fetchall()
            return [dict(zip(columns, row)) for row in rows]

    def get_kpi_overview(self) -> Dict[str, Any]:
        """Calculates core macro KPIs across processes and decisions."""
        with self.get_connection(read_only=True) as con:
            total_proc = con.execute("SELECT COUNT(*) FROM fact_processes").fetchone()[0]
            total_dec = con.execute("SELECT COUNT(*) FROM fact_decisions").fetchone()[0]
            active_proc = con.execute("SELECT COUNT(*) FROM fact_processes WHERE situacao = 'EM TRAMITAÇÃO'").fetchone()[0]
            archived_proc = con.execute("SELECT COUNT(*) FROM fact_processes WHERE situacao = 'BAIXADO'").fetchone()[0]
            total_appeals = con.execute("SELECT COUNT(*) FROM fact_appeals").fetchone()[0] if self.table_exists("fact_appeals") else 0

        return {
            "total_processes": total_proc,
            "total_decisions": total_dec,
            "active_processes": active_proc,
            "archived_processes": archived_proc,
            "total_appeals": total_appeals,
        }

    def table_exists(self, table_name: str) -> bool:
        with self.get_connection(read_only=True) as con:
            res = con.execute(
                "SELECT COUNT(*) FROM information_schema.tables WHERE table_name = ?",
                [table_name],
            ).fetchone()
            return bool(res and res[0] > 0)

