"""Data Lineage and Audit Engine for STF Transparency Platform.

Enables end-to-end traceability for any dashboard metric, analytical query,
or gold/silver dataset:
"Where did this number come from?"
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from ingestion.metadata import IngestionMetadataTracker


@dataclass
class LineageNode:
    layer: str  # "SOURCE", "BRONZE_RAW", "SILVER_CLEAN", "GOLD_ANALYTICAL", "QUERY_METRIC"
    name: str
    description: str
    timestamp: str
    version: str
    hash_or_checksum: Optional[str] = None
    row_count: Optional[int] = None
    properties: Dict[str, Any] = field(default_factory=dict)


@dataclass
class LineageTrace:
    target_entity: str
    query_or_metric: Optional[str]
    traced_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    validation_status: str = "PASS"
    lineage_nodes: List[LineageNode] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_markdown(self) -> str:
        lines = [
            f"### Data Lineage for `{self.target_entity}`",
            f"**Validation Status:** `{self.validation_status}` | **Traced at:** `{self.traced_at}`\n",
            "| Layer | Stage | Version | Records / Rows | Checksum / Hash | Notes |",
            "| :--- | :--- | :--- | :--- | :--- | :--- |",
        ]
        for n in reversed(self.lineage_nodes):
            h = f"`{n.hash_or_checksum[:10]}...`" if n.hash_or_checksum else "-"
            cnt = f"{n.row_count:,}" if n.row_count is not None else "-"
            lines.append(f"| {n.layer} | {n.name} | {n.version} | {cnt} | {h} | {n.description} |")
        return "\n".join(lines)


class LineageEngine:
    """Computes and exposes data lineage graphs for analytical entities."""

    def __init__(self, data_dir: Optional[Path | str] = None) -> None:
        self.project_root = Path(__file__).resolve().parent.parent
        self.data_dir = Path(data_dir) if data_dir else self.project_root / "data"
        self.tracker = IngestionMetadataTracker(self.data_dir / "metadata")
        self.quality_report_path = self.data_dir / "quality" / "validation_report.json"

    def get_validation_status(self) -> str:
        """Reads overall status from latest validation report."""
        if not self.quality_report_path.exists():
            return "UNKNOWN"
        try:
            with open(self.quality_report_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("overall_status", "PASS")
        except Exception:
            return "UNKNOWN"

    def trace_entity(self, entity_name: str) -> LineageTrace:
        """Traces an analytical entity (e.g. 'fact_processes', 'decisions_by_year') back to STF source."""
        val_status = self.get_validation_status()

        dataset_mapping = {
            "fact_processes": "processos",
            "processos": "processos",
            "dim_process_type": "processos",
            "dim_origin": "processos",
            "dim_rapporteur": "processos",
            "fact_decisions": "decisoes",
            "decisoes": "decisoes",
            "fact_appeals": "recursos",
            "recursos": "recursos",
            "repercussao_geral": "repercussao_geral",
        }

        dataset_key = dataset_mapping.get(entity_name.lower(), "processos")
        manifest = self.tracker.get_latest_manifest(dataset_key)

        nodes: List[LineageNode] = []

        # 1. Source (STF Corte Aberta)
        nodes.append(LineageNode(
            layer="SOURCE",
            name="STF Corte Aberta",
            description="Portal do Supremo Tribunal Federal / Resolução 774/2022",
            timestamp=manifest.download_timestamp if manifest else datetime.now(timezone.utc).isoformat(),
            version="Official Portal",
            properties={"endpoint": manifest.source_url if manifest else "https://portal.stf.jus.br/transparencia/"},
        ))

        # 2. Bronze (Raw CSV)
        if manifest:
            nodes.append(LineageNode(
                layer="BRONZE_RAW",
                name=f"raw/{dataset_key}/{manifest.original_filename}",
                description="Immutable raw extracted file",
                timestamp=manifest.download_timestamp,
                version=manifest.dataset_version,
                hash_or_checksum=manifest.file_hash_sha256,
                row_count=manifest.row_count,
                properties={"file_size_bytes": manifest.file_size_bytes},
            ))

        # 3. Silver (Clean Parquet)
        silver_file = self.data_dir / "silver" / f"{dataset_key}.parquet"
        silver_rows = None
        if silver_file.exists():
            import polars as pl
            try:
                silver_rows = pl.read_parquet(silver_file).height
            except Exception:
                pass

        nodes.append(LineageNode(
            layer="SILVER_CLEAN",
            name=f"silver/{dataset_key}.parquet",
            description="Polars normalized and type-enforced dataset",
            timestamp=datetime.now(timezone.utc).isoformat(),
            version="v0.1.0-clean",
            row_count=silver_rows,
            properties={"compression": "zstd"},
        ))

        # 4. Gold (Dimensional Lakehouse)
        gold_name = entity_name if entity_name.startswith(("fact_", "dim_")) else f"fact_{dataset_key}"
        nodes.append(LineageNode(
            layer="GOLD_ANALYTICAL",
            name=gold_name,
            description="Star-schema dimensional model optimized for DuckDB OLAP",
            timestamp=datetime.now(timezone.utc).isoformat(),
            version="v0.1.0-star",
            row_count=silver_rows,
            properties={"engine": "DuckDB"},
        ))

        return LineageTrace(
            target_entity=entity_name,
            query_or_metric=f"SELECT * FROM {gold_name}",
            validation_status=val_status,
            lineage_nodes=nodes,
        )

