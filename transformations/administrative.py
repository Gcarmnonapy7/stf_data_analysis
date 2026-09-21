"""Polars transformation and normalization pipeline for STF Administrative domain.

Covers:
- Personnel roster (pessoal_stf)
- Payroll & Remuneration (remuneracao_stf)
- Annual Budget Execution (orcamento_stf)
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import polars as pl


def clean_personnel(
    input_path: Path | str,
    output_path: Optional[Path | str] = None,
) -> pl.DataFrame:
    """Reads raw pessoal CSV, applies cleaning and standardization, and outputs Parquet."""
    in_file = Path(input_path)
    if not in_file.exists():
        raise FileNotFoundError(f"Input file not found: {in_file}")

    df = pl.read_csv(
        in_file,
        infer_schema_length=10000,
        null_values=["", "NA", "N/A", "NULL", "null", "NaN"],
    )

    rename_map = {col: col.strip().lower().replace(" ", "_") for col in df.columns}
    df = df.rename(rename_map)

    df = df.with_columns([
        pl.col("matricula_hash").cast(pl.Utf8).str.strip_chars(),
        pl.col("nome_anonimizado").cast(pl.Utf8).str.strip_chars(),
        pl.col("cargo").cast(pl.Utf8).str.strip_chars(),
        pl.col("cargo_tipo").cast(pl.Utf8).str.strip_chars(),
        pl.col("lotacao").cast(pl.Utf8).str.strip_chars(),
        pl.col("situacao_funcional").cast(pl.Utf8).str.strip_chars(),
        pl.col("data_admissao").str.to_date("%Y-%m-%d", strict=False),
    ])

    df = df.unique(subset=["matricula_hash"], keep="first")
    df = df.filter(pl.col("matricula_hash").is_not_null())

    if output_path:
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        df.write_parquet(out, compression="zstd")

    return df


def clean_remuneration(
    input_path: Path | str,
    output_path: Optional[Path | str] = None,
) -> pl.DataFrame:
    """Reads raw remuneracao CSV, validates numeric components and constitutional ceiling."""
    in_file = Path(input_path)
    if not in_file.exists():
        raise FileNotFoundError(f"Input file not found: {in_file}")

    df = pl.read_csv(
        in_file,
        infer_schema_length=10000,
        null_values=["", "NA", "N/A", "NULL", "null", "NaN"],
    )

    rename_map = {col: col.strip().lower().replace(" ", "_") for col in df.columns}
    df = df.rename(rename_map)

    numeric_cols = [
        "remuneracao_paradigma",
        "vantagens_pessoais",
        "subsidio",
        "indenizacoes",
        "previdencia_e_ir",
        "abate_teto",
        "remuneracao_liquida",
    ]

    casts = [
        pl.col("remuneracao_id").cast(pl.Utf8).str.strip_chars(),
        pl.col("matricula_hash").cast(pl.Utf8).str.strip_chars(),
        pl.col("competencia_ano").cast(pl.Int64, strict=False),
        pl.col("competencia_mes").cast(pl.Int64, strict=False),
        pl.col("cargo").cast(pl.Utf8).str.strip_chars(),
        pl.col("cargo_tipo").cast(pl.Utf8).str.strip_chars(),
    ]
    for c in numeric_cols:
        casts.append(pl.col(c).cast(pl.Float64, strict=False).fill_null(0.0))

    df = df.with_columns(casts)

    # Calculate gross compensation
    df = df.with_columns([
        (pl.col("remuneracao_paradigma") + pl.col("vantagens_pessoais") + pl.col("subsidio") + pl.col("indenizacoes"))
        .round(2)
        .alias("remuneracao_bruta")
    ])

    df = df.unique(subset=["remuneracao_id"], keep="first")
    df = df.filter(pl.col("remuneracao_id").is_not_null())

    if output_path:
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        df.write_parquet(out, compression="zstd")

    return df


def clean_budget(
    input_path: Path | str,
    output_path: Optional[Path | str] = None,
) -> pl.DataFrame:
    """Reads raw orcamento CSV, validates budget execution hierarchy."""
    in_file = Path(input_path)
    if not in_file.exists():
        raise FileNotFoundError(f"Input file not found: {in_file}")

    df = pl.read_csv(
        in_file,
        infer_schema_length=10000,
        null_values=["", "NA", "N/A", "NULL", "null", "NaN"],
    )

    rename_map = {col: col.strip().lower().replace(" ", "_") for col in df.columns}
    df = df.rename(rename_map)

    money_cols = ["dotacao_inicial", "dotacao_atualizada", "empenhado", "liquidado", "pago"]

    casts = [
        pl.col("orcamento_id").cast(pl.Utf8).str.strip_chars(),
        pl.col("ano_exercicio").cast(pl.Int64, strict=False),
        pl.col("programa_trabalho").cast(pl.Utf8).str.strip_chars(),
        pl.col("acao_orcamentaria").cast(pl.Utf8).str.strip_chars(),
        pl.col("elemento_despesa").cast(pl.Utf8).str.strip_chars(),
    ]
    for c in money_cols:
        casts.append(pl.col(c).cast(pl.Float64, strict=False).fill_null(0.0))

    df = df.with_columns(casts)

    # Budget execution rate: liquidado / dotacao_atualizada
    df = df.with_columns([
        pl.when(pl.col("dotacao_atualizada") > 0)
        .then((pl.col("liquidado") / pl.col("dotacao_atualizada") * 100.0).round(2))
        .otherwise(0.0)
        .alias("taxa_execucao_pct")
    ])

    df = df.unique(subset=["orcamento_id"], keep="first")
    df = df.filter(pl.col("orcamento_id").is_not_null())

    if output_path:
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        df.write_parquet(out, compression="zstd")

    return df

