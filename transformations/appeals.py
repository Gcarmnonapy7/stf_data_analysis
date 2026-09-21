"""Polars transformation and cleaning pipeline for STF Recursos and Repercussão Geral."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import polars as pl


def clean_appeals(
    input_path: Path | str,
    output_path: Optional[Path | str] = None,
) -> pl.DataFrame:
    """Cleans recursos (appeals) dataset."""
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
        pl.col("recurso_id").cast(pl.Utf8).str.strip_chars(),
        pl.col("process_id").cast(pl.Utf8).str.strip_chars(),
        pl.col("tipo_recurso").cast(pl.Utf8).str.strip_chars(),
        pl.col("data_interposicao").str.to_date("%Y-%m-%d", strict=False),
        pl.col("data_julgamento").str.to_date("%Y-%m-%d", strict=False),
        pl.col("resultado_recurso").cast(pl.Utf8).str.strip_chars(),
        pl.col("relator").cast(pl.Utf8).str.strip_chars(),
    ])

    df = df.unique(subset=["recurso_id"], keep="first")
    df = df.filter(pl.col("recurso_id").is_not_null())

    if output_path:
        out_p = Path(output_path)
        out_p.parent.mkdir(parents=True, exist_ok=True)
        df.write_parquet(out_p, compression="zstd")

    return df


def clean_repercussao_geral(
    input_path: Path | str,
    output_path: Optional[Path | str] = None,
) -> pl.DataFrame:
    """Cleans repercussão geral dataset."""
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
        pl.col("tema_numero").cast(pl.Int64, strict=False),
        pl.col("titulo").cast(pl.Utf8).str.strip_chars(),
        pl.col("data_reconhecimento").str.to_date("%Y-%m-%d", strict=False),
        pl.col("status").cast(pl.Utf8).str.strip_chars(),
        pl.col("relator").cast(pl.Utf8).str.strip_chars(),
        pl.col("tese_fixada").cast(pl.Utf8).str.strip_chars(),
    ])

    df = df.unique(subset=["tema_numero"], keep="first")

    if output_path:
        out_p = Path(output_path)
        out_p.parent.mkdir(parents=True, exist_ok=True)
        df.write_parquet(out_p, compression="zstd")

    return df
