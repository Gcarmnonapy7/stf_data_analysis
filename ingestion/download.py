"""Downloader and ingestion manager for STF Corte Aberta datasets.

Features:
- Resilient streaming downloads with retry backoff.
- Automatic SHA-256 computation and metadata provenance registration.
- Fallback / sample mode for offline development and continuous integration.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Dict, Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from ingestion.fixtures import generate_fixtures
from ingestion.metadata import DatasetMetadata, IngestionMetadataTracker

# Official STF Corte Aberta download endpoints / catalog references
CORTE_ABERTA_ENDPOINTS = {
    "processos": "https://transparencia.stf.jus.br/dados_abertos/processos_stf.csv",
    "decisoes": "https://transparencia.stf.jus.br/dados_abertos/decisoes_stf.csv",
    "recursos": "https://transparencia.stf.jus.br/dados_abertos/recursos_stf.csv",
    "repercussao_geral": "https://transparencia.stf.jus.br/dados_abertos/repercussao_geral_stf.csv",
    "pessoal": "https://transparencia.stf.jus.br/dados_abertos/pessoal_stf.csv",
    "remuneracao": "https://transparencia.stf.jus.br/dados_abertos/remuneracao_stf.csv",
    "orcamento": "https://transparencia.stf.jus.br/dados_abertos/orcamento_stf.csv",
}


class DatasetDownloader:
    """Manages raw dataset acquisition and provenance logging."""

    def __init__(self, raw_data_dir: Optional[Path | str] = None) -> None:
        self.project_root = Path(__file__).resolve().parent.parent
        self.raw_data_dir = (
            Path(raw_data_dir) if raw_data_dir else self.project_root / "data" / "raw"
        )
        self.raw_data_dir.mkdir(parents=True, exist_ok=True)
        self.tracker = IngestionMetadataTracker(self.project_root / "data" / "metadata")

        # Configure session with retries and realistic headers
        self.session = requests.Session()
        retries = Retry(
            total=3,
            backoff_factor=1.0,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retries)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        self.session.headers.update({
            "User-Agent": "STF-Transparency-Platform/1.0.0 (+https://github.com/Gcarmnonapy7/stf_data_analysis)",
            "Accept": "text/csv,application/octet-stream,*/*",
        })

    def download_file(
        self,
        url: str,
        dest_path: Path,
        verify_ssl: bool = False,
    ) -> int:
        """Streams a remote file to destination and counts rows."""
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        row_count = 0
        with self.session.get(url, stream=True, timeout=60, verify=verify_ssl) as response:
            response.raise_for_status()
            with open(dest_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=65536):
                    if chunk:
                        f.write(chunk)
                        row_count += chunk.count(b"\n")
        return row_count

    def ingest_dataset(
        self,
        dataset_name: str,
        url: Optional[str] = None,
        use_sample: bool = False,
        sample_rows: int = 500,
    ) -> DatasetMetadata:
        """Ingests a dataset either via HTTP or fixture generator, registering provenance."""
        target_dir = self.raw_data_dir / dataset_name
        target_dir.mkdir(parents=True, exist_ok=True)
        target_file = target_dir / f"{dataset_name}_raw.csv"

        effective_url = url or CORTE_ABERTA_ENDPOINTS.get(dataset_name, "https://portal.stf.jus.br/transparencia/")

        if use_sample:
            # Generate reproducible fixture
            fixtures = generate_fixtures(self.raw_data_dir, n_processes=sample_rows)
            # Find generated file for this dataset
            generated = fixtures.get(dataset_name)
            if generated and generated.exists() and generated != target_file:
                target_file.write_bytes(generated.read_bytes())

            with open(target_file, "rb") as f:
                row_count = max(0, sum(1 for _ in f) - 1)

            return self.tracker.record_ingestion(
                dataset_name=dataset_name,
                source_url=f"synthetic://corte_aberta_fixture/{dataset_name}",
                file_path=target_file,
                row_count=row_count,
                dataset_version="v0.1-sample",
                extra={"mode": "sample", "synthetic": True},
            )

        # Attempt remote HTTP download
        try:
            row_count = self.download_file(effective_url, target_file, verify_ssl=False)
            return self.tracker.record_ingestion(
                dataset_name=dataset_name,
                source_url=effective_url,
                file_path=target_file,
                row_count=row_count,
                dataset_version="v0.1-live",
                extra={"mode": "http_live"},
            )
        except Exception as err:
            print(f"Warning: Live download from {effective_url} failed ({err}). Falling back to reproducible fixture.")
            return self.ingest_dataset(dataset_name, use_sample=True, sample_rows=sample_rows)

    def ingest_all(self, use_sample: bool = True, sample_rows: int = 500) -> Dict[str, DatasetMetadata]:
        """Ingests all core STF datasets."""
        results = {}
        for name in ["processos", "decisoes", "recursos", "repercussao_geral"]:
            meta = self.ingest_dataset(name, use_sample=use_sample, sample_rows=sample_rows)
            results[name] = meta
        return results


def main() -> None:
    parser = argparse.ArgumentParser(description="STF Open Data Ingestion Engine")
    parser.add_argument("--sample", action="store_true", default=True, help="Use sample fixture mode")
    parser.add_argument("--live", action="store_true", help="Force live HTTP download from STF")
    parser.add_argument("--rows", type=int, default=1000, help="Number of rows for sample generation")
    args = parser.parse_args()

    use_sample = not args.live
    downloader = DatasetDownloader()
    print(f"Starting STF dataset ingestion (mode: {'sample' if use_sample else 'live'})...")
    manifests = downloader.ingest_all(use_sample=use_sample, sample_rows=args.rows)
    for name, meta in manifests.items():
        print(f"✓ [{name}] {meta.row_count} rows | Hash: {meta.file_hash_sha256[:12]}... | Path: {meta.file_path}")


if __name__ == "__main__":
    main()

