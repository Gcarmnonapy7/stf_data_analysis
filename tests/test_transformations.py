"""Tests for Polars data transformations."""

import tempfile
from pathlib import Path
import polars as pl
import pytest

from ingestion.fixtures import generate_fixtures
from transformations.decisions import clean_decisions
from transformations.processes import clean_processes


@pytest.fixture(scope="module")
def raw_data_dir():
    with tempfile.TemporaryDirectory() as tmp_dir:
        fixtures = generate_fixtures(tmp_dir, n_processes=100, seed=42)
        yield Path(tmp_dir)


def test_clean_processes(raw_data_dir):
    raw_proc = raw_data_dir / "processos" / "processos_stf.csv"
    assert raw_proc.exists()

    with tempfile.TemporaryDirectory() as out_dir:
        out_parquet = Path(out_dir) / "processos.parquet"
        df = clean_processes(raw_proc, out_parquet)

        assert out_parquet.exists()
        assert df.height > 0
        assert "process_id" in df.columns
        assert "ano_distribuicao" in df.columns
        assert df.schema["data_distribuicao"] == pl.Date
        assert df.schema["numero_processo"] == pl.Int64
        # Verify deduplication
        assert df.height == df.select("process_id").n_unique()


def test_clean_decisions(raw_data_dir):
    raw_dec = raw_data_dir / "decisoes" / "decisoes_stf.csv"
    assert raw_dec.exists()

    with tempfile.TemporaryDirectory() as out_dir:
        out_parquet = Path(out_dir) / "decisoes.parquet"
        df = clean_decisions(raw_dec, out_parquet)

        assert out_parquet.exists()
        assert df.height > 0
        assert "categoria_decisao" in df.columns
        assert set(df["categoria_decisao"].unique().to_list()).issubset(
            {"MONOCRATICA", "COLEGIADA", "PRESIDENCIA"}
        )
