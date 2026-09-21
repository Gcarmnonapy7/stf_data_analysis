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
            total_judges = con.execute("SELECT COUNT(DISTINCT relator) FROM fact_processes WHERE relator IS NOT NULL").fetchone()[0]
            year_range = con.execute("SELECT MIN(ano_distribuicao), MAX(ano_distribuicao) FROM fact_processes").fetchone()
            temporal_range = f"{year_range[0]} - {year_range[1]}" if year_range and year_range[0] else "2018 - 2026"

        return {
            "total_processes": total_proc,
            "total_decisions": total_dec,
            "active_processes": active_proc,
            "archived_processes": archived_proc,
            "total_appeals": total_appeals,
            "total_judges": total_judges,
            "temporal_range": temporal_range,
        }

    def get_judges_caseload(self) -> List[Dict[str, Any]]:
        """Calculates workload, case breakdown, decisions, and lead times per Justice/Rapporteur."""
        sql = """
            WITH proc_stats AS (
                SELECT 
                    relator,
                    COUNT(*) AS total_cases,
                    COUNT(CASE WHEN situacao = 'EM TRAMITAÇÃO' THEN 1 END) AS active_cases,
                    COUNT(CASE WHEN situacao = 'BAIXADO' THEN 1 END) AS archived_cases,
                    COUNT(CASE WHEN situacao = 'JULGADO' THEN 1 END) AS judged_cases
                FROM fact_processes
                WHERE relator IS NOT NULL
                GROUP BY relator
            ),
            dec_stats AS (
                SELECT 
                    d.relator,
                    COUNT(*) AS total_decisions,
                    COUNT(CASE WHEN d.categoria_decisao = 'MONOCRATICA' THEN 1 END) AS monocratic_decisions,
                    COUNT(CASE WHEN d.categoria_decisao = 'COLEGIADA' THEN 1 END) AS collegial_decisions,
                    ROUND(AVG(DATEDIFF('day', p.data_distribuicao, d.data_decisao)), 1) AS avg_lead_time_days
                FROM fact_decisions d
                LEFT JOIN fact_processes p ON d.process_id = p.process_id
                WHERE d.relator IS NOT NULL
                GROUP BY d.relator
            ),
            total_court AS (
                SELECT COUNT(*) AS court_total FROM fact_processes
            )
            SELECT 
                p.relator,
                p.total_cases,
                p.active_cases,
                p.archived_cases,
                p.judged_cases,
                COALESCE(d.total_decisions, 0) AS total_decisions,
                COALESCE(d.monocratic_decisions, 0) AS monocratic_decisions,
                COALESCE(d.collegial_decisions, 0) AS collegial_decisions,
                ROUND(p.total_cases * 100.0 / tc.court_total, 2) AS pct_caseload,
                COALESCE(d.avg_lead_time_days, 0) AS avg_lead_time_days
            FROM proc_stats p
            CROSS JOIN total_court tc
            LEFT JOIN dec_stats d ON p.relator = d.relator
            ORDER BY p.total_cases DESC
        """
        return self.query(sql)

    def table_exists(self, table_name: str) -> bool:
        with self.get_connection(read_only=True) as con:
            res = con.execute(
                "SELECT COUNT(*) FROM information_schema.tables WHERE table_name = ?",
                [table_name],
            ).fetchone()
            return bool(res and res[0] > 0)

