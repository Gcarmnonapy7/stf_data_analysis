"""Pydantic request and response schemas for REST API."""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ProcessItem(BaseModel):
    process_id: str
    numero_processo: Optional[int] = None
    classe_sigla: str
    classe_descricao: str
    assunto: str
    relator: str
    data_autuacao: Optional[str] = None
    data_distribuicao: str
    uf_origem: str
    orgao_julgador: str
    situacao: str
    ano_distribuicao: int


class DecisionItem(BaseModel):
    decision_id: str
    process_id: str
    numero_processo: Optional[int] = None
    classe_sigla: str
    data_decisao: str
    tipo_decisao: str
    categoria_decisao: str
    resultado: str
    relator: str
    orgao_colegiado: str
    ano_decisao: int


class PaginatedResponse(BaseModel):
    total: int
    limit: int
    offset: int
    items: List[Dict[str, Any]]


class KPIOverview(BaseModel):
    total_processes: int
    total_decisions: int
    active_processes: int
    archived_processes: int
    total_appeals: int


class LineageNodeItem(BaseModel):
    layer: str
    name: str
    description: str
    timestamp: str
    version: str
    hash_or_checksum: Optional[str] = None
    row_count: Optional[int] = None
    properties: Dict[str, Any] = Field(default_factory=dict)


class LineageResponse(BaseModel):
    target_entity: str
    query_or_metric: Optional[str] = None
    traced_at: str
    validation_status: str
    lineage_nodes: List[LineageNodeItem]
    markdown_lineage: str
