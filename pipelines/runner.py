"""Unified pipeline orchestrator for STF Transparency Platform.

Orchestrates the full Medallion lifecycle:
1. Bronze (Raw Ingestion & SHA-256 Provenance)
2. Silver (Polars Cleaning, Type Enforcement, Parquet Serialization)
3. Data Quality Gate (Automatic Assertion Contracts)
4. Gold (Star-Schema Dimensional Modeling & DuckDB Lakehouse Catalog)
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from ingestion.download import DatasetDownloader
from pipelines.gold.builder import GoldModelBuilder
from quality.runner import DataQualityEngine
from transformations.appeals import clean_appeals, clean_repercussao_geral
from transformations.decisions import clean_decisions
from transformations.processes import clean_processes

console = Console()


def run_pipeline(use_sample: bool = True, rows: int = 1000, enforce_quality_gate: bool = True) -> bool:
    start_time = time.time()
    console.print(Panel.fit("[bold blue]STF Transparency Platform[/bold blue] — Automated Pipeline Execution", border_style="blue"))

    project_root = Path(__file__).resolve().parent.parent
    raw_dir = project_root / "data" / "raw"
    silver_dir = project_root / "data" / "silver"
    silver_dir.mkdir(parents=True, exist_ok=True)

    # -------------------------------------------------------------
    # Stage 1: Bronze (Ingestion)
    # -------------------------------------------------------------
    console.print("\n[bold yellow]► Stage 1: Ingestion (Bronze Layer)[/bold yellow]")
    downloader = DatasetDownloader(raw_dir)
    manifests = downloader.ingest_all(use_sample=use_sample, sample_rows=rows)

    ingest_table = Table(title="Bronze Ingestion Summary", show_lines=True)
    ingest_table.add_column("Dataset", style="cyan")
    ingest_table.add_column("Rows", justify="right", style="green")
    ingest_table.add_column("Bytes", justify="right")
    ingest_table.add_column("SHA-256 (Truncated)", style="magenta")

    for name, meta in manifests.items():
        ingest_table.add_row(
            name,
            f"{meta.row_count:,}",
            f"{meta.file_size_bytes:,}",
            f"{meta.file_hash_sha256[:16]}...",
        )
    console.print(ingest_table)

    # -------------------------------------------------------------
    # Stage 2: Silver (Cleaning & Normalization)
    # -------------------------------------------------------------
    console.print("\n[bold yellow]► Stage 2: Normalization (Silver Layer)[/bold yellow]")

    proc_raw = raw_dir / "processos" / "processos_raw.csv"
    proc_silver = silver_dir / "processos.parquet"
    df_proc = clean_processes(proc_raw, proc_silver)
    console.print(f"✓ Processed [bold]processos[/bold]: {df_proc.height:,} rows -> {proc_silver.name}")

    dec_raw = raw_dir / "decisoes" / "decisoes_raw.csv"
    dec_silver = silver_dir / "decisoes.parquet"
    df_dec = clean_decisions(dec_raw, dec_silver)
    console.print(f"✓ Processed [bold]decisões[/bold]: {df_dec.height:,} rows -> {dec_silver.name}")

    rec_raw = raw_dir / "recursos" / "recursos_raw.csv"
    rec_silver = silver_dir / "recursos.parquet"
    if rec_raw.exists():
        df_rec = clean_appeals(rec_raw, rec_silver)
        console.print(f"✓ Processed [bold]recursos[/bold]: {df_rec.height:,} rows -> {rec_silver.name}")

    rg_raw = raw_dir / "repercussao_geral" / "repercussao_geral_raw.csv"
    rg_silver = silver_dir / "repercussao_geral.parquet"
    if rg_raw.exists():
        df_rg = clean_repercussao_geral(rg_raw, rg_silver)
        console.print(f"✓ Processed [bold]repercussão geral[/bold]: {df_rg.height:,} rows -> {rg_silver.name}")

    # -------------------------------------------------------------
    # Stage 3: Data Quality Gate
    # -------------------------------------------------------------
    console.print("\n[bold yellow]► Stage 3: Data Quality & Integrity Contracts[/bold yellow]")
    dq = DataQualityEngine(project_root / "data")
    report = dq.run_all_checks()

    dq_table = Table(title=f"Quality Checks ({report.passed_checks}/{report.total_checks} passed)", show_lines=True)
    dq_table.add_column("Dataset", style="cyan")
    dq_table.add_column("Contract / Rule", style="white")
    dq_table.add_column("Result", justify="center")
    dq_table.add_column("Message", style="italic")

    for r in report.results:
        status_badge = "[bold green]PASS[/bold green]" if r.status == "PASS" else "[bold red]FAIL[/bold red]"
        dq_table.add_row(r.dataset, r.check_name, status_badge, r.message)

    console.print(dq_table)

    if enforce_quality_gate and report.overall_status != "PASS":
        console.print("[bold red]Pipeline HALTED: Data quality gate failed.[/bold red]")
        return False

    # -------------------------------------------------------------
    # Stage 4: Gold (Star Schema & DuckDB Lakehouse)
    # -------------------------------------------------------------
    console.print("\n[bold yellow]► Stage 4: Dimensional Modeling (Gold Lakehouse)[/bold yellow]")
    builder = GoldModelBuilder(project_root / "data")
    models = builder.build_all_models()

    gold_table = Table(title="Gold Analytical Models", show_lines=True)
    gold_table.add_column("Model Name", style="cyan")
    gold_table.add_column("Model Type", style="white")
    gold_table.add_column("Rows", justify="right", style="green")

    for name, df in models.items():
        m_type = "Fact" if name.startswith("fact_") else "Dimension"
        gold_table.add_row(name, m_type, f"{df.height:,}")
    console.print(gold_table)

    elapsed = time.time() - start_time
    console.print(f"\n[bold green]✓ Pipeline completed successfully in {elapsed:.2f} seconds.[/bold green]")
    console.print(f"DuckDB Lakehouse ready at: [bold]{builder.db_path}[/bold]\n")
    return True


def main() -> None:
    parser = argparse.ArgumentParser(description="STF Pipeline Master Runner")
    parser.add_argument("--sample", action="store_true", default=True, help="Use sample data mode")
    parser.add_argument("--live", action="store_true", help="Use live STF extraction")
    parser.add_argument("--rows", type=int, default=1000, help="Row count for sample mode")
    parser.add_argument("--skip-quality-gate", action="store_true", help="Don't stop on quality failures")
    args = parser.parse_args()

    success = run_pipeline(
        use_sample=not args.live,
        rows=args.rows,
        enforce_quality_gate=not args.skip_quality_gate,
    )
    if not success:
        sys.exit(1)


if __name__ == "__main__":
    main()
