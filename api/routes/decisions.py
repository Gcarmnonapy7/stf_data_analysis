"""Endpoints for court decisions."""

from __future__ import annotations

from typing import Optional
from fastapi import APIRouter, Query

from analytics.duckdb_client import STFLakehouseClient
from api.schemas.models import PaginatedResponse

router = APIRouter(prefix="/decisions", tags=["Decisions"])
client = STFLakehouseClient()


@router.get("", response_model=PaginatedResponse)
def list_decisions(
    year: Optional[int] = Query(None, description="Filter by decision year"),
    categoria: Optional[str] = Query(None, description="Filter by category (MONOCRATICA, COLEGIADA, PRESIDENCIA)"),
    resultado: Optional[str] = Query(None, description="Filter by outcome substring (e.g. Provido)"),
    relator: Optional[str] = Query(None, description="Filter by rapporteur"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """Retrieves paginated decisions with analytical categories."""
    where_clauses = []
    params = []

    if year:
        where_clauses.append("ano_decisao = ?")
        params.append(year)
    if categoria:
        where_clauses.append("categoria_decisao = ?")
        params.append(categoria.upper())
    if resultado:
        where_clauses.append("resultado ILIKE ?")
        params.append(f"%{resultado}%")
    if relator:
        where_clauses.append("relator ILIKE ?")
        params.append(f"%{relator}%")

    where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

    count_sql = f"SELECT COUNT(*) FROM fact_decisions {where_sql}"
    with client.get_connection(read_only=True) as con:
        total = con.execute(count_sql, params).fetchone()[0]

    data_sql = f"""
        SELECT 
            decision_id, process_id, numero_processo, classe_sigla,
            strftime(data_decisao, '%Y-%m-%d') AS data_decisao,
            tipo_decisao, categoria_decisao, resultado, relator,
            orgao_colegiado, ano_decisao
        FROM fact_decisions
        {where_sql}
        ORDER BY data_decisao DESC
        LIMIT ? OFFSET ?
    """
    items = client.query(data_sql, params + [limit, offset])

    return PaginatedResponse(total=total, limit=limit, offset=offset, items=items)
