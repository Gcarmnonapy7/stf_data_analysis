"""Tests for data quality engine and lineage."""

from pathlib import Path
import pytest

from quality.lineage import LineageEngine
from quality.runner import DataQualityEngine


def test_quality_engine():
    project_root = Path(__file__).resolve().parent.parent
    data_dir = project_root / "data"

    if not (data_dir / "silver" / "processos.parquet").exists():
        pytest.skip("Data not yet generated, run pipeline first.")

    engine = DataQualityEngine(data_dir)
    report = engine.run_all_checks()

    assert report.total_checks > 0
    assert report.overall_status == "PASS"
    assert report.failed_checks == 0


def test_lineage_engine():
    project_root = Path(__file__).resolve().parent.parent
    data_dir = project_root / "data"

    if not (data_dir / "curated" / "fact_decisions.parquet").exists():
        pytest.skip("Gold tables not yet generated.")

    engine = LineageEngine(data_dir)
    trace = engine.trace_entity("fact_decisions")

    assert trace.target_entity == "fact_decisions"
    assert len(trace.lineage_nodes) >= 3
    assert any(n.layer == "SOURCE" for n in trace.lineage_nodes)
    assert any(n.layer == "GOLD_ANALYTICAL" for n in trace.lineage_nodes)

    md = trace.to_markdown()
    assert "Data Lineage for `fact_decisions`" in md

