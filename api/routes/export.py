"""FastAPI high-performance streaming export router for STF Lakehouse datasets.

Supports chunked streaming exports:
- CSV (text/csv)
- JSON Lines (application/x-ndjson)
- Parquet (application/vnd.apache.parquet)
"""

from __future__ import annotations

import io
import json
from pathlib import Path
from typing import Generator
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse

import duckdb
import polars as pl

router = APIRouter(prefix="/export", tags=["Streaming Export Services"])

ALLOWED_DATASETS = {
    "processes": "fact_processes",
    "decisions": "fact_decisions",
    "appeals": "fact_appeals",
    "budget": "fact_budget",
    "remuneration": "fact_remuneration",
    "personnel": "dim_personnel",
}


def _get_parquet_path(table_name: str) -> Path:
    project_root = Path(__file__).resolve().parent.parent.parent
    path = project_root / "data" / "curated" / f"{table_name}.parquet"
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Dataset {table_name} not available in curated lakehouse.")
    return path


def _stream_csv(table_name: str) -> Generator[bytes, None, None]:
    p = _get_parquet_path(table_name)
    df = pl.read_parquet(p)
    # Output header
    header = ",".join(f'"{c}"' for c in df.columns) + "\n"
    yield header.encode("utf-8")

    # Stream batches
    chunk_size = 500
    for i in range(0, df.height, chunk_size):
        chunk = df.slice(i, chunk_size)
        buffer = io.StringIO()
        chunk.write_csv(buffer, include_header=False)
        yield buffer.getvalue().encode("utf-8")


def _stream_jsonl(table_name: str) -> Generator[bytes, None, None]:
    p = _get_parquet_path(table_name)
    df = pl.read_parquet(p)
    for row in df.iter_rows(named=True):
        # Convert date/datetime to string for JSON serialization
        clean_row = {
            k: (v.isoformat() if hasattr(v, "isoformat") else v)
            for k, v in row.items()
        }
        line = json.dumps(clean_row, ensure_ascii=False) + "\n"
        yield line.encode("utf-8")


def _stream_parquet_file(table_name: str) -> Generator[bytes, None, None]:
    p = _get_parquet_path(table_name)
    with open(p, "rb") as f:
        while chunk := f.read(65536):
            yield chunk


@router.get("/{dataset}")
def export_dataset(
    dataset: str,
    format: str = Query("csv", pattern="^(csv|jsonl|parquet)$", description="Format: csv, jsonl, or parquet"),
):
    """Streams the requested STF Lakehouse table in the chosen format."""
    table_name = ALLOWED_DATASETS.get(dataset.lower())
    if not table_name:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid dataset '{dataset}'. Choose from: {list(ALLOWED_DATASETS.keys())}",
        )

    filename = f"stf_{dataset}.{format}"

    if format == "csv":
        return StreamingResponse(
            _stream_csv(table_name),
            media_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    elif format == "jsonl":
        return StreamingResponse(
            _stream_jsonl(table_name),
            media_type="application/x-ndjson",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    elif format == "parquet":
        return StreamingResponse(
            _stream_parquet_file(table_name),
            media_type="application/vnd.apache.parquet",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
