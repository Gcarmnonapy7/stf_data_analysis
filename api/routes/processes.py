"""Endpoints for judicial processes."""

from __future__ import annotations

from typing import Optional
from fastapi import APIRouter, Query

from analytics.duckdb_client import STFLakehouseClient
from api.schemas.models import PaginatedResponse

router = APIRouter(prefix="/processes", tags=["Processes"])
client = STFLakehouseClient()


@router.get("", response_model=PaginatedResponse)
def list_processes(
    year: Optional[int] = Query(None, description="Filter by distribution year"),
    classe: Optional[str] = Query(None, description="Filter by process class (e.g. ADI, RE)"),
    relator: Optional[str] = Query(None, description="Filter by minister/relator name substring"),
    uf: Optional[str] = Query(None, description="Filter by state of origin (e.g. SP, RJ, DF)"),
    situacao: Optional[str] = Query(None, description="Filter by status (e.g. 'EM TRAMITAÇÃO', 'BAIXADO')"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """Retrieves paginated STF processes matching analytical filters."""
    where_clauses = []
    params = []

    if year:
        where_clauses.append("ano_distribuicao = ?")
        params.append(year)
    if classe:
        where_clauses.append("classe_sigla = ?")
        params.append(classe.upper())
    if relator:
        where_clauses.append("relator ILIKE ?")
        params.append(f"%{relator}%")
    if uf:
        where_clauses.append("uf_origem = ?")
        params.append(uf.upper())
    if situacao:
        where_clauses.append("situacao = ?")
        params.append(situacao.upper())

    where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

    count_sql = f"SELECT COUNT(*) FROM fact_processes {where_sql}"
    with client.get_connection(read_only=True) as con:
        total = con.execute(count_sql, params).fetchone()[0]

    data_sql = f"""
        SELECT 
            process_id, numero_processo, classe_sigla, classe_descricao,
            assunto, relator, 
            strftime(data_autuacao, '%Y-%m-%d') AS data_autuacao,
            strftime(data_distribuicao, '%Y-%m-%d') AS data_distribuicao,
            uf_origem, orgao_julgador, situacao, ano_distribuicao
        FROM fact_processes
        {where_sql}
        ORDER BY data_distribuicao DESC
        LIMIT ? OFFSET ?
    """
    items = client.query(data_sql, params + [limit, offset])

    return PaginatedResponse(total=total, limit=limit, offset=offset, items=items)

