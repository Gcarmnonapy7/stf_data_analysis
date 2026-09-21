"""Polars transformation and cleaning pipeline for STF Decisões.

Handles:
- Missing values and type conversions.
- Date parsing and validation.
- Classification into decision categories (Monocrática vs Colegiada vs Presidência).
- Outcome classification.
- Output to Parquet format.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import polars as pl


def clean_decisions(
    input_path: Path | str,
    output_path: Optional[Path | str] = None,
) -> pl.DataFrame:
    """Reads raw decisões CSV, normalizes schema and categories, outputs Parquet."""
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

    # Cast types and sanitize strings
    df = df.with_columns([
        pl.col("decision_id").cast(pl.Utf8).str.strip_chars(),
        pl.col("process_id").cast(pl.Utf8).str.strip_chars(),
        pl.col("numero_processo").cast(pl.Int64, strict=False),
        pl.col("classe_sigla").cast(pl.Utf8).str.strip_chars().str.to_uppercase(),
        pl.col("data_decisao").str.to_date("%Y-%m-%d", strict=False),
        pl.col("tipo_decisao").cast(pl.Utf8).str.strip_chars(),
        pl.col("resultado").cast(pl.Utf8).str.strip_chars(),
        pl.col("relator").cast(pl.Utf8).str.strip_chars(),
        pl.col("orgao_colegiado").cast(pl.Utf8).str.strip_chars(),
        pl.col("texto_resumo").cast(pl.Utf8).str.strip_chars(),
    ])

    # Deduplicate by decision_id
    df = df.unique(subset=["decision_id"], keep="first")

    # Drop records with null decision_id or data_decisao
    df = df.filter(pl.col("decision_id").is_not_null() & pl.col("data_decisao").is_not_null())

    # Add macro decision category
    df = df.with_columns([
        pl.when(pl.col("tipo_decisao").str.contains("Monocrática"))
        .then(pl.lit("MONOCRATICA"))
        .when(pl.col("tipo_decisao").str.contains("Presidência"))
        .then(pl.lit("PRESIDENCIA"))
        .otherwise(pl.lit("COLEGIADA"))
        .alias("categoria_decisao"),
        pl.col("data_decisao").dt.year().alias("ano_decisao"),
        pl.col("data_decisao").dt.month().alias("mes_decisao"),
    ])

    if output_path:
        out_p = Path(output_path)
        out_p.parent.mkdir(parents=True, exist_ok=True)
        df.write_parquet(out_p, compression="zstd")

    return df


if __name__ == "__main__":
    project_root = Path(__file__).resolve().parent.parent
    raw_csv = project_root / "data" / "raw" / "decisoes" / "decisoes_raw.csv"
    silver_parquet = project_root / "data" / "silver" / "decisoes.parquet"
    if raw_csv.exists():
        cleaned = clean_decisions(raw_csv, silver_parquet)
        print(f"Cleaned {cleaned.height} decisões -> {silver_parquet}")

