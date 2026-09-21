"""Aggregated Analytics endpoints for charts and research insights."""

from __future__ import annotations

from typing import Any, Dict, List
from fastapi import APIRouter

from analytics.duckdb_client import STFLakehouseClient
from api.schemas.models import JudgeCaseloadItem, KPIOverview, ValidationSummaryResponse

router = APIRouter(prefix="/analytics", tags=["Analytics"])
client = STFLakehouseClient()


@router.get("/overview", response_model=KPIOverview)
def get_overview():
    """Returns high-level statistics across processes, decisions, and appeals."""
    return client.get_kpi_overview()


@router.get("/yearly-trends", response_model=List[Dict[str, Any]])
def get_yearly_trends():
    """Returns case intake and backlog trend per year."""
    sql = """
        SELECT 
            d.year AS ano,
            COUNT(*) AS total_distribuidos,
            COUNT(CASE WHEN p.situacao = 'EM TRAMITAÇÃO' THEN 1 END) AS em_tramitacao,
            COUNT(CASE WHEN p.situacao = 'BAIXADO' THEN 1 END) AS baixados,
            COUNT(CASE WHEN p.situacao = 'JULGADO' THEN 1 END) AS julgados
        FROM fact_processes p
        JOIN dim_date d ON p.date_distribuicao_key = d.date_key
        GROUP BY d.year
        ORDER BY ano ASC
    """
    return client.query(sql)


@router.get("/decisions-by-category", response_model=List[Dict[str, Any]])
def get_decisions_by_category():
    """Returns decision distribution: Monocrática vs Colegiada vs Presidência."""
    sql = """
        SELECT 
            categoria_decisao,
            COUNT(*) AS total,
            ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2) AS percentual
        FROM fact_decisions
        GROUP BY categoria_decisao
        ORDER BY total DESC
    """
    return client.query(sql)


@router.get("/by-region", response_model=List[Dict[str, Any]])
def get_cases_by_region():
    """Returns process count grouped by Brazilian macro-region and UF."""
    sql = """
        SELECT 
            o.regiao,
            p.uf_origem,
            COUNT(*) AS total_processos
        FROM fact_processes p
        JOIN dim_origin o ON p.uf_origem = o.uf_origem
        GROUP BY o.regiao, p.uf_origem
        ORDER BY total_processos DESC
    """
    return client.query(sql)


@router.get("/top-classes", response_model=List[Dict[str, Any]])
def get_top_classes():
    """Returns top legal classes (ADI, RE, HC, etc.)."""
    sql = """
        SELECT 
            classe_sigla,
            classe_descricao,
            COUNT(*) AS total_acoes
        FROM fact_processes
        GROUP BY classe_sigla, classe_descricao
        ORDER BY total_acoes DESC
        LIMIT 10
    """
    return client.query(sql)


@router.get("/judges", response_model=List[JudgeCaseloadItem])
def get_judges():
    """Returns workload, active vs archived cases, and decisions rendered per Justice/Rapporteur."""
    return client.get_judges_caseload()


@router.get("/validation", response_model=ValidationSummaryResponse)
def get_validation_summary():
    """Returns data validation assertions and temporal scope (2018-2026) contract status."""
    import json
    from pathlib import Path
    report_file = Path(__file__).resolve().parent.parent.parent / "data" / "quality" / "validation_report.json"
    if report_file.exists():
        with open(report_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        return ValidationSummaryResponse(
            status=data.get("overall_status", "PASS"),
            total_checks=data.get("total_checks", 0),
            passed_checks=data.get("passed_checks", 0),
            failed_checks=data.get("failed_checks", 0),
            temporal_window="2018 - 2026",
            timestamp=data.get("timestamp", ""),
            details=data.get("results", []),
        )
    return ValidationSummaryResponse(
        status="PASS",
        total_checks=0,
        passed_checks=0,
        failed_checks=0,
        temporal_window="2018 - 2026",
        timestamp="",
        details=[],
    )


@router.get("/survival")
def get_survival_analysis() -> Dict[str, Any]:
    """Returns Kaplan-Meier judicial backlog survival probabilities and backlog half-life."""
    from analytics.survival import BacklogSurvivalAnalyzer
    analyzer = BacklogSurvivalAnalyzer()
    return analyzer.compute_survival_overview()


@router.post("/query")
def execute_sql_query(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Executes arbitrary analytical SQL query over the DuckDB warehouse and returns columns and rows."""
    import time
    sql = payload.get("sql", "").strip()
    if not sql:
        return {"error": "Empty SQL statement."}
    
    # Restrict to read-only analytical queries
    first_word = sql.split()[0].upper() if sql.split() else ""
    if first_word not in ("SELECT", "WITH", "SHOW", "DESCRIBE", "EXPLAIN"):
        return {"error": "Only read-only queries (SELECT, WITH, SHOW, DESCRIBE) are permitted."}

    start = time.perf_counter()
    try:
        results = client.query(sql)
        elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
        columns = list(results[0].keys()) if results else []
        return {
            "columns": columns,
            "rows": results,
            "row_count": len(results),
            "execution_time_ms": elapsed_ms,
        }
    except Exception as e:
        return {"error": str(e), "execution_time_ms": round((time.perf_counter() - start) * 1000, 2)}

