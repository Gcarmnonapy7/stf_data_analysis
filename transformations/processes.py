"""Polars transformation and cleaning pipeline for STF Processos.

Handles:
- Missing values and type conversions.
- Date parsing and sanity constraints.
- Deduplication of process IDs.
- Categorical standardization (UFs, class codes, status).
- Column renaming to standard snake_case.
- Output to partitioned/compressed Parquet format.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import polars as pl


def clean_processes(
    input_path: Path | str,
    output_path: Optional[Path | str] = None,
) -> pl.DataFrame:
    """Reads raw processos CSV, applies cleaning/normalization, and outputs Parquet."""
    in_file = Path(input_path)
    if not in_file.exists():
        raise FileNotFoundError(f"Input file not found: {in_file}")

    # Read raw CSV with Polars
    df = pl.read_csv(
        in_file,
        infer_schema_length=10000,
        null_values=["", "NA", "N/A", "NULL", "null", "NaN"],
    )

    # Standardize column names
    rename_map = {col: col.strip().lower().replace(" ", "_") for col in df.columns}
    df = df.rename(rename_map)

    # Normalize data types and string hygiene
    df = df.with_columns([
        pl.col("process_id").cast(pl.Utf8).str.strip_chars(),
        pl.col("numero_processo").cast(pl.Int64, strict=False),
        pl.col("classe_sigla").cast(pl.Utf8).str.strip_chars().str.to_uppercase(),
        pl.col("classe_descricao").cast(pl.Utf8).str.strip_chars(),
        pl.col("assunto").cast(pl.Utf8).str.strip_chars(),
        pl.col("relator").cast(pl.Utf8).str.strip_chars(),
        pl.col("data_autuacao").str.to_date("%Y-%m-%d", strict=False),
        pl.col("data_distribuicao").str.to_date("%Y-%m-%d", strict=False),
        pl.col("uf_origem").cast(pl.Utf8).str.strip_chars().str.to_uppercase(),
        pl.col("orgao_julgador").cast(pl.Utf8).str.strip_chars(),
        pl.col("situacao").cast(pl.Utf8).str.strip_chars().str.to_uppercase(),
    ])

    # Deduplicate by process_id keeping first
    df = df.unique(subset=["process_id"], keep="first")

    # Filter out records where process_id or distribution_date is null
    df = df.filter(pl.col("process_id").is_not_null() & pl.col("data_distribuicao").is_not_null())

    # Add analytical derived fields
    df = df.with_columns([
        pl.col("data_distribuicao").dt.year().alias("ano_distribuicao"),
        pl.col("data_distribuicao").dt.month().alias("mes_distribuicao"),
    ])

    # Save to Parquet if output_path is specified
    if output_path:
        out_p = Path(output_path)
        out_p.parent.mkdir(parents=True, exist_ok=True)
        df.write_parquet(out_p, compression="zstd")

    return df


if __name__ == "__main__":
    project_root = Path(__file__).resolve().parent.parent
    raw_csv = project_root / "data" / "raw" / "processos" / "processos_raw.csv"
    silver_parquet = project_root / "data" / "silver" / "processos.parquet"
    if raw_csv.exists():
        cleaned = clean_processes(raw_csv, silver_parquet)
        print(f"Cleaned {cleaned.height} processos -> {silver_parquet}")

