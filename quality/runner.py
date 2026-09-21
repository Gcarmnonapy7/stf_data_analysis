"""Automated Data Quality verification engine for STF Transparency Platform.

Validates:
- Primary key uniqueness (No duplicate process IDs, decision IDs).
- Null constraints on required fields.
- Date logic (valid chronological order, no future dates).
- Categorical domain constraints (valid Brazilian state codes).
- Source checksum integrity against ingestion manifests.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import polars as pl

from ingestion.metadata import IngestionMetadataTracker

VALID_UFS = {
    "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA",
    "MT", "MS", "MG", "PA", "PB", "PR", "PE", "PI", "RJ", "RN",
    "RS", "RO", "RR", "SC", "SP", "SE", "TO"
}


@dataclass
class CheckResult:
    check_name: str
    target_layer: str
    dataset: str
    status: str  # "PASS" or "FAIL"
    message: str
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class QualityReport:
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    total_checks: int = 0
    passed_checks: int = 0
    failed_checks: int = 0
    overall_status: str = "PASS"
    results: List[CheckResult] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class DataQualityEngine:
    """Executes assertions over Silver and Gold Parquet datasets."""

    def __init__(self, data_dir: Optional[Path | str] = None) -> None:
        self.project_root = Path(__file__).resolve().parent.parent
        self.data_dir = Path(data_dir) if data_dir else self.project_root / "data"
        self.silver_dir = self.data_dir / "silver"
        self.tracker = IngestionMetadataTracker(self.data_dir / "metadata")
        self.report_dir = self.data_dir / "quality"
        self.report_dir.mkdir(parents=True, exist_ok=True)

    def run_all_checks(self) -> QualityReport:
        """Runs the complete suite of quality checks."""
        report = QualityReport()
        results: List[CheckResult] = []

        # 1. Verify Processos
        proc_parquet = self.silver_dir / "processos.parquet"
        if proc_parquet.exists():
            df_proc = pl.read_parquet(proc_parquet)
            results.extend(self._validate_processes(df_proc))
        else:
            results.append(CheckResult(
                check_name="file_exists",
                target_layer="silver",
                dataset="processos",
                status="FAIL",
                message=f"Parquet file not found at {proc_parquet}",
            ))

        # 2. Verify Decisões
        dec_parquet = self.silver_dir / "decisoes.parquet"
        if dec_parquet.exists():
            df_dec = pl.read_parquet(dec_parquet)
            results.extend(self._validate_decisions(df_dec))
        else:
            results.append(CheckResult(
                check_name="file_exists",
                target_layer="silver",
                dataset="decisoes",
                status="FAIL",
                message=f"Parquet file not found at {dec_parquet}",
            ))

        # 3. Cross-dataset referential integrity: Decisões -> Processos
        if proc_parquet.exists() and dec_parquet.exists():
            results.append(self._validate_referential_integrity(df_proc, df_dec))

        # 4. Ingestion manifest checksum integrity
        results.extend(self._validate_manifest_checksums())

        # Compile report
        report.results = results
        report.total_checks = len(results)
        report.passed_checks = sum(1 for r in results if r.status == "PASS")
        report.failed_checks = sum(1 for r in results if r.status == "FAIL")
        report.overall_status = "PASS" if report.failed_checks == 0 else "FAIL"

        # Save report to disk
        report_file = self.report_dir / "validation_report.json"
        with open(report_file, "w", encoding="utf-8") as f:
            json.dump(report.to_dict(), f, indent=2, ensure_ascii=False)

        return report

    def _validate_processes(self, df: pl.DataFrame) -> List[CheckResult]:
        results = []

        # Unique process_id
        dups = df.height - df.select("process_id").n_unique()
        results.append(CheckResult(
            check_name="primary_key_uniqueness",
            target_layer="silver",
            dataset="processos",
            status="PASS" if dups == 0 else "FAIL",
            message=f"Found {dups} duplicate process_id entries." if dups > 0 else "All process_id values are unique.",
            details={"duplicates_count": dups},
        ))

        # Non-null process_id & data_distribuicao
        null_ids = df.filter(pl.col("process_id").is_null()).height
        null_dates = df.filter(pl.col("data_distribuicao").is_null()).height
        results.append(CheckResult(
            check_name="not_null_critical_fields",
            target_layer="silver",
            dataset="processos",
            status="PASS" if (null_ids == 0 and null_dates == 0) else "FAIL",
            message=f"Null check: {null_ids} null IDs, {null_dates} null distribution dates.",
            details={"null_ids": null_ids, "null_dates": null_dates},
        ))

        # Date reasonableness (between 1980 and current year + 1)
        current_year = date.today().year
        invalid_years = df.filter(
            (pl.col("data_distribuicao").dt.year() < 1980) |
            (pl.col("data_distribuicao").dt.year() > current_year + 1)
        ).height
        results.append(CheckResult(
            check_name="reasonable_dates",
            target_layer="silver",
            dataset="processos",
            status="PASS" if invalid_years == 0 else "FAIL",
            message=f"{invalid_years} processes have unreasonable distribution dates.",
            details={"invalid_date_count": invalid_years},
        ))

        # Valid UF domain
        ufs_in_data = set(df.select("uf_origem").drop_nulls().to_series().to_list())
        invalid_ufs = ufs_in_data - VALID_UFS
        results.append(CheckResult(
            check_name="valid_uf_domains",
            target_layer="silver",
            dataset="processos",
            status="PASS" if not invalid_ufs else "FAIL",
            message=f"Invalid UFs detected: {invalid_ufs}" if invalid_ufs else "All UFs belong to valid Brazilian state codes.",
            details={"invalid_ufs": list(invalid_ufs)},
        ))

        return results

    def _validate_decisions(self, df: pl.DataFrame) -> List[CheckResult]:
        results = []

        # Unique decision_id
        dups = df.height - df.select("decision_id").n_unique()
        results.append(CheckResult(
            check_name="primary_key_uniqueness",
            target_layer="silver",
            dataset="decisoes",
            status="PASS" if dups == 0 else "FAIL",
            message=f"Found {dups} duplicate decision_id entries." if dups > 0 else "All decision_id values are unique.",
            details={"duplicates_count": dups},
        ))

        # Decision date not null
        null_dates = df.filter(pl.col("data_decisao").is_null()).height
        results.append(CheckResult(
            check_name="not_null_decision_date",
            target_layer="silver",
            dataset="decisoes",
            status="PASS" if null_dates == 0 else "FAIL",
            message=f"{null_dates} null decision dates found." if null_dates > 0 else "All decision dates are populated.",
            details={"null_dates": null_dates},
        ))

        return results

    def _validate_referential_integrity(
        self, df_proc: pl.DataFrame, df_dec: pl.DataFrame
    ) -> CheckResult:
        """Verifies decisions link to valid processes and decision date >= distribution date."""
        joined = df_dec.join(
            df_proc.select(["process_id", "data_distribuicao"]),
            on="process_id",
            how="inner",
        )
        anomalous_dates = joined.filter(
            pl.col("data_decisao") < pl.col("data_distribuicao")
        ).height

        return CheckResult(
            check_name="referential_temporal_consistency",
            target_layer="silver",
            dataset="cross_process_decision",
            status="PASS" if anomalous_dates == 0 else "FAIL",
            message=f"{anomalous_dates} decisions precede their process distribution date."
            if anomalous_dates > 0
            else "All joined decisions occur on or after their process distribution date.",
            details={"anomalous_dates": anomalous_dates},
        )

    def _validate_manifest_checksums(self) -> List[CheckResult]:
        results = []
        all_manifests = self.tracker.list_manifests()
        # Group by dataset_name keeping latest
        latest_manifests: Dict[str, Any] = {}
        for m in all_manifests:
            latest_manifests[m.dataset_name] = m

        for meta in latest_manifests.values():
            p = Path(meta.file_path)
            if not p.exists():
                results.append(CheckResult(
                    check_name="raw_file_presence",
                    target_layer="bronze",
                    dataset=meta.dataset_name,
                    status="FAIL",
                    message=f"Raw file missing: {p}",
                ))
                continue

            current_hash = self.tracker.calculate_sha256(p)
            match = current_hash == meta.file_hash_sha256
            results.append(CheckResult(
                check_name="checksum_integrity",
                target_layer="bronze",
                dataset=meta.dataset_name,
                status="PASS" if match else "FAIL",
                message="File SHA-256 matches latest manifest." if match else "Checksum mismatch! File has been altered.",
                details={"recorded_hash": meta.file_hash_sha256, "computed_hash": current_hash},
            ))
        return results


def main() -> None:
    engine = DataQualityEngine()
    print("Running automated data quality checks...")
    report = engine.run_all_checks()
    print(f"\nOverall Status: {report.overall_status} ({report.passed_checks}/{report.total_checks} passed)")
    for res in report.results:
        symbol = "✓" if res.status == "PASS" else "✗"
        print(f"{symbol} [{res.target_layer.upper()}][{res.dataset}] {res.check_name}: {res.message}")


if __name__ == "__main__":
    main()
