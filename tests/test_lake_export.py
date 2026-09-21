"""Tests for Lakehouse Format Exporter (Delta Lake & Apache Iceberg)."""

import json
import tempfile
from pathlib import Path
import polars as pl
import pytest

from pipelines.export.lake_formats import LakehouseExporter


@pytest.fixture
def mock_curated_dir():
    with tempfile.TemporaryDirectory() as tmp_dir:
        data_dir = Path(tmp_dir)
        curated_dir = data_dir / "curated"
        curated_dir.mkdir(parents=True, exist_ok=True)

        # Create dummy curated parquet
        df = pl.DataFrame({
            "process_id": ["PROC-1", "PROC-2", "PROC-3"],
            "numero_processo": [1001, 1002, 1003],
            "classe_sigla": ["ADI", "HC", "RE"],
            "valor_recurso": [100.5, 250.0, 50.0],
            "is_active": [True, False, True],
        })
        df.write_parquet(curated_dir / "dim_test_processes.parquet")
        yield data_dir


def test_list_available_tables(mock_curated_dir):
    exporter = LakehouseExporter(data_dir=mock_curated_dir)
    tables = exporter.list_available_tables()
    assert "dim_test_processes" in tables


def test_export_to_delta(mock_curated_dir):
    exporter = LakehouseExporter(data_dir=mock_curated_dir)
    target_path = exporter.export_to_delta("dim_test_processes")

    assert target_path.exists()
    delta_log = target_path / "_delta_log"
    assert delta_log.exists()
    
    commit_file = delta_log / "00000000000000000000.json"
    assert commit_file.exists()

    # Read commit actions
    lines = [json.loads(line) for line in commit_file.read_text(encoding="utf-8").strip().splitlines()]
    assert len(lines) == 4
    
    keys = [list(entry.keys())[0] for entry in lines]
    assert "commitInfo" in keys
    assert "protocol" in keys
    assert "metaData" in keys
    assert "add" in keys

    # Verify parquet part file referenced in add action exists
    add_action = next(entry["add"] for entry in lines if "add" in entry)
    part_path = target_path / add_action["path"]
    assert part_path.exists()
    assert add_action["stats"] is not None


def test_export_to_iceberg(mock_curated_dir):
    exporter = LakehouseExporter(data_dir=mock_curated_dir)
    target_path = exporter.export_to_iceberg("dim_test_processes")

    assert target_path.exists()
    data_dir = target_path / "data"
    metadata_dir = target_path / "metadata"
    assert data_dir.exists()
    assert metadata_dir.exists()

    v1_meta = metadata_dir / "v1.metadata.json"
    assert v1_meta.exists()

    meta_content = json.loads(v1_meta.read_text(encoding="utf-8"))
    assert meta_content["format-version"] == 2
    assert "schemas" in meta_content
    assert "snapshots" in meta_content
    assert len(meta_content["snapshots"]) == 1
    assert meta_content["snapshots"][0]["summary"]["operation"] == "append"

    # Verify data file exists
    data_files = list(data_dir.glob("*.parquet"))
    assert len(data_files) == 1
    df_read = pl.read_parquet(data_files[0])
    assert df_read.height == 3
