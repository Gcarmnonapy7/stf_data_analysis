"""Tests for ingestion and metadata tracking."""

import tempfile
from pathlib import Path
import pytest

from ingestion.fixtures import generate_fixtures
from ingestion.metadata import IngestionMetadataTracker


def test_metadata_tracker_sha256_and_manifest():
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        tracker = IngestionMetadataTracker(metadata_dir=tmp_path / "meta")

        # Create a dummy raw file
        test_file = tmp_path / "test.csv"
        test_file.write_text("process_id,val\nADI-100,1\nADI-200,2\n", encoding="utf-8")

        meta = tracker.record_ingestion(
            dataset_name="processos",
            source_url="https://test.stf.jus.br",
            file_path=test_file,
            row_count=2,
            dataset_version="v0.1-test",
        )

        assert meta.dataset_name == "processos"
        assert meta.row_count == 2
        assert len(meta.file_hash_sha256) == 64
        assert meta.file_size_bytes > 0

        manifests = tracker.list_manifests()
        assert len(manifests) == 1
        assert manifests[0].file_hash_sha256 == meta.file_hash_sha256

        latest = tracker.get_latest_manifest("processos")
        assert latest is not None
        assert latest.file_hash_sha256 == meta.file_hash_sha256


def test_fixtures_generation():
    with tempfile.TemporaryDirectory() as tmp_dir:
        files = generate_fixtures(tmp_dir, n_processes=50, seed=123)

        assert "processos" in files
        assert "decisoes" in files
        assert "recursos" in files
        assert "repercussao_geral" in files

        for name, p in files.items():
            assert p.exists()
            assert p.stat().st_size > 0

