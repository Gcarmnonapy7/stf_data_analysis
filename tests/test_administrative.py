"""Tests for STF Administrative domain transformations."""

import tempfile
from pathlib import Path
import polars as pl
import pytest

from ingestion.fixtures import generate_fixtures
from transformations.administrative import clean_personnel, clean_remuneration, clean_budget


@pytest.fixture(scope="module")
def admin_raw_dir():
    with tempfile.TemporaryDirectory() as tmp_dir:
        generate_fixtures(tmp_dir, n_processes=50, seed=42)
        yield Path(tmp_dir)


def test_clean_personnel(admin_raw_dir):
    raw_file = admin_raw_dir / "pessoal" / "pessoal_stf.csv"
    assert raw_file.exists()

    with tempfile.TemporaryDirectory() as out_dir:
        out_parquet = Path(out_dir) / "dim_personnel.parquet"
        df = clean_personnel(raw_file, out_parquet)

        assert out_parquet.exists()
        assert df.height > 0
        assert "matricula_hash" in df.columns
        assert "cargo" in df.columns
        assert "lotacao" in df.columns
        assert df.schema["data_admissao"] == pl.Date
        # Deduplication check
        assert df.height == df.select("matricula_hash").n_unique()


def test_clean_remuneration(admin_raw_dir):
    raw_file = admin_raw_dir / "remuneracao" / "remuneracao_stf.csv"
    assert raw_file.exists()

    with tempfile.TemporaryDirectory() as out_dir:
        out_parquet = Path(out_dir) / "fact_remuneration.parquet"
        df = clean_remuneration(raw_file, out_parquet)

        assert out_parquet.exists()
        assert df.height > 0
        assert "remuneracao_id" in df.columns
        assert "remuneracao_bruta" in df.columns
        assert "remuneracao_liquida" in df.columns
        assert df.schema["remuneracao_bruta"] == pl.Float64
        # Verify gross is sum of components
        first = df.row(0, named=True)
        expected_gross = round(
            first["remuneracao_paradigma"] + first["vantagens_pessoais"] + first["subsidio"] + first["indenizacoes"], 2
        )
        assert abs(first["remuneracao_bruta"] - expected_gross) < 0.01


def test_clean_budget(admin_raw_dir):
    raw_file = admin_raw_dir / "orcamento" / "orcamento_stf.csv"
    assert raw_file.exists()

    with tempfile.TemporaryDirectory() as out_dir:
        out_parquet = Path(out_dir) / "fact_budget.parquet"
        df = clean_budget(raw_file, out_parquet)

        assert out_parquet.exists()
        assert df.height > 0
        assert "orcamento_id" in df.columns
        assert "taxa_execucao_pct" in df.columns
        assert df.schema["taxa_execucao_pct"] == pl.Float64
        assert df.schema["dotacao_atualizada"] == pl.Float64

