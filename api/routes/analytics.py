"""Aggregated Analytics endpoints for charts and research insights."""

from __future__ import annotations

from typing import Any, Dict, List
from fastapi import APIRouter

from analytics.duckdb_client import STFLakehouseClient
from api.schemas.models import KPIOverview

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
