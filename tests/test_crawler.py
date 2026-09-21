"""Tests for Incremental Crawler and Watermark Management."""

import tempfile
from pathlib import Path
import pytest

from ingestion.crawler import WatermarkManager, IncrementalCrawler


def test_watermark_manager_lifecycle():
    with tempfile.TemporaryDirectory() as tmp_dir:
        wm = WatermarkManager(tmp_dir)
        
        # Test default when no file exists
        default_wm = wm.get_watermark("processos")
        assert default_wm["last_ingested_date"] == "2018-01-01"
        assert default_wm["max_id"] == 0
        assert default_wm["batches_count"] == 0

        # Update watermark
        wm.update_watermark("processos", max_date="2022-06-15", max_id=150)
        updated = wm.get_watermark("processos")
        assert updated["last_ingested_date"] == "2022-06-15"
        assert updated["max_id"] == 150
        assert updated["batches_count"] == 1
        assert updated["last_run_utc"] is not None

        # Reinstantiate manager to verify persistence on disk
        wm2 = WatermarkManager(tmp_dir)
        loaded = wm2.get_watermark("processos")
        assert loaded["last_ingested_date"] == "2022-06-15"
        assert loaded["max_id"] == 150
        assert loaded["batches_count"] == 1


def test_incremental_crawler_execution():
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        crawler = IncrementalCrawler(data_dir=tmp_path)

        # First incremental run for processos
        res1 = crawler.crawl_incremental(dataset="processos", batch_size=20, use_sample=True)
        assert res1["status"] == "SUCCESS"
        assert res1["rows_added"] == 20
        assert res1["max_id"] == 20
        assert res1["dataset"] == "processos"

        # Verify watermark was incremented
        wm1 = crawler.watermark_mgr.get_watermark("processos")
        assert wm1["max_id"] == 20
        assert wm1["batches_count"] == 1

        # Second incremental run should continue from max_id
        res2 = crawler.crawl_incremental(dataset="processos", batch_size=15, use_sample=True)
        assert res2["status"] == "SUCCESS"
        assert res2["rows_added"] == 15
        assert res2["max_id"] == 35

        wm2 = crawler.watermark_mgr.get_watermark("processos")
        assert wm2["max_id"] == 35
        assert wm2["batches_count"] == 2

        # Verify raw CSV file exists and contains appended records
        raw_csv = tmp_path / "raw" / "processos" / "processos_raw.csv"
        assert raw_csv.exists()
        lines = raw_csv.read_text(encoding="utf-8").strip().splitlines()
        # Header + 20 + 15 = 36 lines
        assert len(lines) == 36

