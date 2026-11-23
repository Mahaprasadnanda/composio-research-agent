"""Unit tests for independent verification audit service and reporting."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from unittest.mock import Mock

import pytest

from research_agent.services.verification_service import (
    AUDIT_SAMPLE_APP_IDS,
    GROUND_TRUTH_BENCHMARKS,
    VerificationService,
)


def test_verification_sample_coverage():
    """Verify that the verification benchmark covers 15 apps across at least 6 categories."""
    assert len(AUDIT_SAMPLE_APP_IDS) == 15
    assert len(GROUND_TRUTH_BENCHMARKS) == 15

    categories = {b.category for b in GROUND_TRUTH_BENCHMARKS.values()}
    assert len(categories) >= 6  # Spans 9 categories

    # Verify verdicts include all 3 main classes
    verdicts = {b.buildability_verdict for b in GROUND_TRUTH_BENCHMARKS.values()}
    assert "buildable" in verdicts
    assert "conditionally_buildable" in verdicts
    assert "blocked" in verdicts


def test_verification_evaluation_statistics():
    """Verify field evaluations calculate 105 fields and expected accuracy metrics."""
    svc = VerificationService()
    audit = svc.evaluate_audit()

    stats = audit["summary_statistics"]
    assert stats["sample_size"] == 15
    assert stats["total_evaluated_fields"] == 105  # 15 apps * 7 dimensions

    # Assert accuracy invariants
    assert stats["overall_field_exact_match_rate"] > 50.0
    assert stats["overall_post_correction_accuracy"] >= 90.0
    assert stats["composio_discovery_agreement_rate"] == 100.0
    assert stats["verdict_agreement_rate"] >= 70.0

    # Assert 3 error patterns are documented
    assert len(stats["error_patterns"]) == 3


def test_verification_save_reports(tmp_path: Path):
    """Verify report persistence to custom output and docs directories."""
    out_dir = tmp_path / "verification"
    docs_dir = tmp_path / "docs"

    svc = VerificationService()
    files = svc.save_reports(output_dir=out_dir, docs_dir=docs_dir)

    for path in files.values():
        assert path.exists()
        assert path.stat().st_size > 0

    # Verify JSON report structure
    report_data = json.loads(files["verification_report_json"].read_text(encoding="utf-8"))
    assert "summary_statistics" in report_data
    assert len(report_data["applications"]) == 15

    # Verify CSV report rows
    with open(files["verification_report_csv"], mode="r", encoding="utf-8") as f:
        reader = list(csv.DictReader(f))
        assert len(reader) == 105  # 105 field comparisons
        assert "agreement_status" in reader[0]
        assert "evidence_url" in reader[0]

    # Verify Markdown summary headings
    md_text = files["verification_audit_summary_md"].read_text(encoding="utf-8")
    assert "# Independent Verification Audit Summary" in md_text
    assert "## 1. Executive Summary & Purpose" in md_text
    assert "## 2. The 15-Application Audit Sample" in md_text


def test_verification_zero_network_calls(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Verify verification audit executes completely offline without network requests."""
    mock_get = Mock(side_effect=RuntimeError("NETWORK_CALL_FORBIDDEN"))
    monkeypatch.setattr("httpx.get", mock_get)
    monkeypatch.setattr("httpx.Client.get", mock_get)

    svc = VerificationService()
    files = svc.save_reports(output_dir=tmp_path / "verif", docs_dir=tmp_path / "docs")
    assert files["verification_report_json"].exists()


def test_verification_cli(tmp_path: Path):
    """Verify CLI subcommand 'verify' runs cleanly."""
    from research_agent.cli import main

    exit_code = main([
        "verify",
        "--output-dir", str(tmp_path / "out_verif"),
        "--docs-dir", str(tmp_path / "out_docs"),
    ])
    assert exit_code == 0
    assert (tmp_path / "out_verif" / "verification_report.json").exists()
