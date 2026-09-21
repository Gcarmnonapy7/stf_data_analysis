"""Data lineage traceability endpoint: 'Where did this number come from?'"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from api.schemas.models import LineageNodeItem, LineageResponse
from quality.lineage import LineageEngine

router = APIRouter(prefix="/lineage", tags=["Data Lineage & Provenance"])
engine = LineageEngine()


@router.get("/{entity_name}", response_model=LineageResponse)
def get_entity_lineage(entity_name: str):
    """Traces an analytical entity back through Gold, Silver, Bronze raw file, and STF Corte Aberta."""
    try:
        trace = engine.trace_entity(entity_name)
        nodes = [
            LineageNodeItem(
                layer=n.layer,
                name=n.name,
                description=n.description,
                timestamp=n.timestamp,
                version=n.version,
                hash_or_checksum=n.hash_or_checksum,
                row_count=n.row_count,
                properties=n.properties,
            )
            for n in trace.lineage_nodes
        ]
        return LineageResponse(
            target_entity=trace.target_entity,
            query_or_metric=trace.query_or_metric,
            traced_at=trace.traced_at,
            validation_status=trace.validation_status,
            lineage_nodes=nodes,
            markdown_lineage=trace.to_markdown(),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
