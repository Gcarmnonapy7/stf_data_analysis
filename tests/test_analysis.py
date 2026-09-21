"""Unit tests for the statistical analysis runner."""

import tempfile
from pathlib import Path
import pytest

from analytics.run_analysis import generate_executive_report


def test_generate_executive_report():
    with tempfile.TemporaryDirectory() as tmp_dir:
        report_path = Path(tmp_dir) / "test_report.md"
        content = generate_executive_report(report_path)

        assert report_path.exists()
        assert "STF Transparency Platform — Executive Analytical Report" in content
        assert "Annual Case Inflow & Backlog Dynamics" in content
        assert "Decision Profile: Monocratic vs. Collegiate Rulings" in content
        assert "Top Procedural Classes" in content
        assert "Judicial Lead Time" in content
        assert "Decision Outcomes" in content
