"""Dimensional Model (Gold Layer) Builder for STF Transparency Platform.

Builds a Star Schema:
Facts:
- fact_processes
- fact_decisions
- fact_appeals
- fact_repercussion_general

Dimensions:
- dim_date
- dim_process_type
- dim_rapporteur
- dim_origin
- dim_subject
"""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path
from typing import Dict, Optional

import duckdb
import polars as pl

# Brazilian Region Mapping
UF_TO_REGION = {
    "SP": "Sudeste", "RJ": "Sudeste", "MG": "Sudeste", "ES": "Sudeste",
    "RS": "Sul", "PR": "Sul", "SC": "Sul",
    "BA": "Nordeste", "PE": "Nordeste", "CE": "Nordeste", "MA": "Nordeste",
    "PB": "Nordeste", "RN": "Nordeste", "AL": "Nordeste", "PI": "Nordeste", "SE": "Nordeste",
    "DF": "Centro-Oeste", "GO": "Centro-Oeste", "MT": "Centro-Oeste", "MS": "Centro-Oeste",
    "PA": "Norte", "AM": "Norte", "RO": "Norte", "TO": "Norte", "AC": "Norte", "AP": "Norte", "RR": "Norte",
}


class GoldModelBuilder:
    """Constructs star-schema Gold Parquet models and populates the DuckDB lakehouse."""

    def __init__(self, data_dir: Optional[Path | str] = None) -> None:
        self.project_root = Path(__file__).resolve().parent.parent.parent
        self.data_dir = Path(data_dir) if data_dir else self.project_root / "data"
        self.silver_dir = self.data_dir / "silver"
        self.curated_dir = self.data_dir / "curated"
        self.curated_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = self.curated_dir / "stf_warehouse.duckdb"

    def build_dim_date(self, start_year: int = 2000, end_year: int = 2030) -> pl.DataFrame:
        """Generates a rich calendar dimension."""
        start_date = date(start_year, 1, 1)
        end_date = date(end_year, 12, 31)
        total_days = (end_date - start_date).days + 1

        dates = [start_date + timedelta(days=i) for i in range(total_days)]
        month_names = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
                       "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]
        day_names = ["Segunda-feira", "Terça-feira", "Quarta-feira", "Quinta-feira", "Sexta-feira", "Sábado", "Domingo"]

        dim_date = pl.DataFrame({
            "date_key": [int(d.strftime("%Y%m%d")) for d in dates],
            "full_date": dates,
            "year": [d.year for d in dates],
            "month": [d.month for d in dates],
            "month_name": [month_names[d.month - 1] for d in dates],
            "quarter": [(d.month - 1) // 3 + 1 for d in dates],
            "day": [d.day for d in dates],
            "day_of_week": [day_names[d.weekday()] for d in dates],
            "is_weekend": [d.weekday() >= 5 for d in dates],
        })
        return dim_date

    def build_all_models(self) -> Dict[str, pl.DataFrame]:
        """Constructs all fact and dimension tables and outputs Parquet."""
        # 1. Dimension: Date
        dim_date = self.build_dim_date()
        dim_date.write_parquet(self.curated_dir / "dim_date.parquet", compression="zstd")

        # Load Silver tables
        df_proc = pl.read_parquet(self.silver_dir / "processos.parquet")
        df_dec = pl.read_parquet(self.silver_dir / "decisoes.parquet")

        # 2. Dimension: Process Type
        dim_proc_type = (
            df_proc.select(["classe_sigla", "classe_descricao"])
            .unique()
            .with_columns(
                pl.int_range(1, pl.len() + 1).alias("process_type_key")
            )
        )
        dim_proc_type.write_parquet(self.curated_dir / "dim_process_type.parquet", compression="zstd")

        # 3. Dimension: Rapporteur (Relator)
        all_relatores = (
            pl.concat([
                df_proc.select(pl.col("relator")),
                df_dec.select(pl.col("relator")),
            ])
            .drop_nulls()
            .unique()
            .with_columns(
                pl.int_range(1, pl.len() + 1).alias("rapporteur_key"),
                pl.lit(True).alias("ativo"),
            )
        )
        all_relatores.write_parquet(self.curated_dir / "dim_rapporteur.parquet", compression="zstd")

        # 4. Dimension: Origin (UF & Região)
        ufs = df_proc.select("uf_origem").drop_nulls().unique()
        dim_origin = ufs.with_columns([
            pl.col("uf_origem").replace(UF_TO_REGION, default="Indeterminado").alias("regiao"),
            pl.int_range(1, pl.len() + 1).alias("origin_key"),
        ])
        dim_origin.write_parquet(self.curated_dir / "dim_origin.parquet", compression="zstd")

        # 5. Dimension: Subject
        subjects = df_proc.select("assunto").drop_nulls().unique()
        dim_subject = subjects.with_columns([
            pl.col("assunto").str.split("|").list.first().str.strip_chars().alias("ramo_direito"),
            pl.int_range(1, pl.len() + 1).alias("subject_key"),
        ])
        dim_subject.write_parquet(self.curated_dir / "dim_subject.parquet", compression="zstd")

        # 6. Fact: Processes
        fact_proc = df_proc.with_columns([
            pl.col("data_distribuicao").dt.strftime("%Y%m%d").cast(pl.Int64).alias("date_distribuicao_key"),
            pl.col("data_autuacao").dt.strftime("%Y%m%d").cast(pl.Int64).alias("date_autuacao_key"),
        ])
        fact_proc.write_parquet(self.curated_dir / "fact_processes.parquet", compression="zstd")

        # 7. Fact: Decisions
        fact_dec = df_dec.with_columns([
            pl.col("data_decisao").dt.strftime("%Y%m%d").cast(pl.Int64).alias("date_decisao_key"),
        ])
        fact_dec.write_parquet(self.curated_dir / "fact_decisions.parquet", compression="zstd")

        # 8. Fact: Appeals (if available)
        rec_silver = self.silver_dir / "recursos.parquet"
        if rec_silver.exists():
            df_rec = pl.read_parquet(rec_silver)
            fact_rec = df_rec.with_columns([
                pl.col("data_interposicao").dt.strftime("%Y%m%d").cast(pl.Int64, strict=False).alias("date_interposicao_key"),
                pl.col("data_julgamento").dt.strftime("%Y%m%d").cast(pl.Int64, strict=False).alias("date_julgamento_key"),
            ])
            fact_rec.write_parquet(self.curated_dir / "fact_appeals.parquet", compression="zstd")

        # Populate DuckDB Catalog
        self.register_duckdb_views()

        return {
            "dim_date": dim_date,
            "dim_process_type": dim_proc_type,
            "dim_rapporteur": all_relatores,
            "dim_origin": dim_origin,
            "dim_subject": dim_subject,
            "fact_processes": fact_proc,
            "fact_decisions": fact_dec,
        }

    def register_duckdb_views(self) -> None:
        """Registers all Parquet files as persistent views/tables in DuckDB."""
        con = duckdb.connect(str(self.db_path))
        parquet_files = list(self.curated_dir.glob("*.parquet"))
        for p in parquet_files:
            table_name = p.stem
            con.execute(f"CREATE OR REPLACE TABLE {table_name} AS SELECT * FROM read_parquet('{p.resolve()}');")
        con.close()


if __name__ == "__main__":
    builder = GoldModelBuilder()
    models = builder.build_all_models()
    print("Gold dimensional models built successfully in Parquet and DuckDB.")

