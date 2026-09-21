"""FastAPI router for STF Administrative domain (Personnel, Remuneration, Budget)."""

from __future__ import annotations

from typing import Any, Dict, List
from fastapi import APIRouter

from analytics.duckdb_client import STFLakehouseClient

router = APIRouter(prefix="/administrative", tags=["Administrative & Transparency"])


@router.get("/budget/summary")
def get_budget_summary() -> List[Dict[str, Any]]:
    """Returns annual STF budget execution totals (Dotação, Empenhado, Liquidado, Pago)."""
    client = STFLakehouseClient()
    sql = """
        SELECT 
            ano_exercicio,
            ROUND(SUM(dotacao_inicial) / 1e6, 2) AS dotacao_inicial_milhoes,
            ROUND(SUM(dotacao_atualizada) / 1e6, 2) AS dotacao_atualizada_milhoes,
            ROUND(SUM(empenhado) / 1e6, 2) AS empenhado_milhoes,
            ROUND(SUM(liquidado) / 1e6, 2) AS liquidado_milhoes,
            ROUND(SUM(pago) / 1e6, 2) AS pago_milhoes,
            ROUND(SUM(liquidado) / NULLIF(SUM(dotacao_atualizada), 0) * 100, 1) AS taxa_execucao_pct
        FROM fact_budget
        GROUP BY ano_exercicio
        ORDER BY ano_exercicio ASC;
    """
    return client.query(sql)


@router.get("/remuneration/summary")
def get_remuneration_summary() -> Dict[str, Any]:
    """Returns aggregated payroll transparency metrics and constitutional ceiling stats."""
    client = STFLakehouseClient()
    sql = """
        SELECT 
            COUNT(*) AS total_registros_folha,
            ROUND(AVG(remuneracao_liquida), 2) AS media_remuneracao_liquida,
            ROUND(MAX(remuneracao_liquida), 2) AS max_remuneracao_liquida,
            ROUND(SUM(abate_teto), 2) AS total_abate_teto_retido,
            ROUND(SUM(remuneracao_liquida) / 1e6, 2) AS total_folha_paga_milhoes
        FROM fact_remuneration;
    """
    res = client.query(sql)
    return res[0] if res else {}


@router.get("/personnel")
def get_personnel_stats() -> Dict[str, Any]:
    """Returns personnel distribution across categories and key administrative departments."""
    client = STFLakehouseClient()
    cat_sql = """
        SELECT 
            cargo_tipo,
            COUNT(*) AS total_colaboradores
        FROM dim_personnel
        GROUP BY cargo_tipo
        ORDER BY total_colaboradores DESC;
    """
    dept_sql = """
        SELECT 
            lotacao,
            COUNT(*) AS total_colaboradores
        FROM dim_personnel
        GROUP BY lotacao
        ORDER BY total_colaboradores DESC
        LIMIT 10;
    """
    return {
        "by_category": client.query(cat_sql),
        "top_departments": client.query(dept_sql),
    }

