"""Automated test suite for analytics service, reconciliation, and HTML case study generation."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from research_agent.models import (
    ApiBreadth,
    ApiType,
    AppCategory,
    AppResearchRecord,
    AuthMethod,
    BuildabilityVerdict,
    ConfidenceLevel,
    EvidenceItem,
    ExecutionMode,
    ExecutionSource,
    McpAvailability,
    PrimaryBlocker,
    ResearchProvenance,
    ResearchStatus,
    SelfServiceAccess,
    VerificationStatus,
)
from research_agent.services.analytics_service import (
    CATEGORY_DISPLAY_NAMES,
    compute_category_analytics,
    compute_overall_analytics,
    generate_analytical_insights,
    generate_html_case_study,
    reconcile_research_data,
    run_full_analytics,
    safe_div,
)
from research_agent.services.research_service import load_seed_dataset


def _make_dummy_record(
    app_name: str,
    category: AppCategory,
    verdict: BuildabilityVerdict,
    mode: ExecutionMode = ExecutionMode.LIVE,
    live_verified: bool = True,
    toolkit_found: bool = True,
    mcp_created: bool = True,
    blocker: PrimaryBlocker = PrimaryBlocker.NONE,
) -> AppResearchRecord:
    """Construct a valid AppResearchRecord fixture for testing."""
    return AppResearchRecord(
        app_name=app_name,
        category=category,
        description=f"Test description for {app_name}",
        auth_methods=[AuthMethod.OAUTH2],
        self_service_access=SelfServiceAccess.FREE_SELF_SERVICE,
        developer_access_tier=SelfServiceAccess.FREE_SELF_SERVICE,
        production_access_tier=SelfServiceAccess.PAID_SUBSCRIPTION,
        access_requirements="Free self-service",
        api_types=[ApiType.REST],
        api_breadth=ApiBreadth.COMPREHENSIVE,
        mcp_availability=McpAvailability.OFFICIAL if toolkit_found else McpAvailability.NONE,
        has_composio_integration=toolkit_found,
        composio_toolkit_slug=app_name.lower() if toolkit_found else None,
        buildability_verdict=verdict,
        primary_blocker=blocker,
        blocker_details=None,
        evidence_urls=["https://example.com/api"],
        evidence_excerpts=["Official API endpoint documented."],
        evidence_items=[
            EvidenceItem(
                url="https://example.com/api",
                excerpt="Official API endpoint documented.",
            )
        ],
        research_status=ResearchStatus.COMPLETED,
        confidence_level=ConfidenceLevel.HIGH,
        uncertainty_notes=None,
        llm_execution_source=ExecutionSource.REAL_NETWORK if live_verified else ExecutionSource.SIMULATED,
        provenance=ResearchProvenance(
            execution_mode=mode,
            doc_execution_source=ExecutionSource.REAL_NETWORK,
            llm_execution_source=ExecutionSource.REAL_NETWORK,
            composio_execution_source=ExecutionSource.REAL_NETWORK,
            documentation_live_fetched=True,
            documentation_urls_attempted=["https://example.com/api"],
            documentation_urls_succeeded=["https://example.com/api"],
            documentation_truncated=False,
            documentation_truncation_notes=None,
            llm_inference_attempted=True,
            llm_inference_executed=True,
            llm_model="openai/gpt-oss-120b",
            llm_error=None,
            composio_adapter_configured=True,
            composio_discovery_attempted=True,
            composio_discovery_succeeded=True,
            composio_toolkit_found=toolkit_found,
            composio_discovery_error=None,
            composio_mcp_session_attempted=toolkit_found,
            composio_mcp_session_created=mcp_created,
            composio_mcp_endpoint_returned=mcp_created,
            composio_mcp_endpoint="https://example.com/mcp" if mcp_created else None,
            composio_mcp_session_error=None,
            live_verified=live_verified,
            notes="Test record provenance",
        ),
        verification_status=VerificationStatus.UNVERIFIED,
        verification_notes=None,
    )


def test_safe_div():
    """Verify safe division with zero denominator handling."""
    assert safe_div(10, 20) == 50.0
    assert safe_div(0, 100) == 0.0
    assert safe_div(5, 0, default=99.9) == 99.9


def test_empty_dataset_handling():
    """Ensure analytics functions handle empty record lists gracefully without crashing."""
    empty_stats = compute_overall_analytics([], total_target=100)
    assert empty_stats["total_target_applications"] == 100
    assert empty_stats["researched_count"] == 0
    assert empty_stats["coverage_percentage"] == 0.0

    empty_cats = compute_category_analytics([])
    assert len(empty_cats) == 10
    for cat_data in empty_cats.values():
        assert cat_data["researched_count"] == 0
        assert cat_data["buildability_rate"] == 0.0


def test_reconciliation_accuracy_and_missing_ids(tmp_path: Path):
    """Verify reconciliation detects missing IDs and cross-references sources correctly."""
    seed_file = tmp_path / "seed.json"
    seed_payload = {
        "version": "1.0",
        "total_apps": 3,
        "apps": [
            {"id": 1, "name": "AppOne", "category": "CRM and Sales", "website": "https://one.com", "documentation_hint": "https://docs.one.com"},
            {"id": 2, "name": "AppTwo", "category": "Support and Helpdesk", "website": "https://two.com", "documentation_hint": "https://docs.two.com"},
            {"id": 3, "name": "AppThree", "category": "Communications and Messaging", "website": "https://three.com", "documentation_hint": "https://docs.three.com"},
        ],
    }
    seed_file.write_text(json.dumps(seed_payload), encoding="utf-8")

    # Dataset contains AppOne
    ds_file = tmp_path / "research_dataset.json"
    rec1 = _make_dummy_record("AppOne", AppCategory.CRM, BuildabilityVerdict.BUILDABLE)
    ds_file.write_text(json.dumps({"records": [rec1.model_dump(mode="json")]}), encoding="utf-8")

    # Files contain AppOne and AppTwo
    results_dir = tmp_path / "results"
    results_dir.mkdir()
    rec2 = _make_dummy_record("AppTwo", AppCategory.CUSTOMER_SUPPORT, BuildabilityVerdict.BLOCKED)
    (results_dir / "001_appone.json").write_text(rec1.model_dump_json(), encoding="utf-8")
    (results_dir / "002_apptwo.json").write_text(rec2.model_dump_json(), encoding="utf-8")

    # Summary reports AppThree failed
    summary_file = tmp_path / "summary.json"
    summary_file.write_text(json.dumps({
        "failed_apps": [{"app_id": 3, "app_name": "AppThree", "error": "Simulated rate limit"}]
    }), encoding="utf-8")

    reconcil = reconcile_research_data(
        seed_path=seed_file,
        dataset_path=ds_file,
        results_dir=results_dir,
        summary_path=summary_file,
    )

    assert reconcil["seed_applications_count"] == 3
    assert reconcil["consolidated_dataset_records_count"] == 1
    assert reconcil["individual_result_files_count"] == 2
    assert reconcil["discrepancies"]["file_ids_not_in_consolidated"] == [2]
    assert reconcil["failed_applications_count"] == 1
    assert reconcil["unattempted_applications_count"] == 0
    assert reconcil["duplicate_ids_in_consolidated"] == 0
    assert reconcil["duplicate_ids_in_files"] == 0


def test_invalid_json_handling(tmp_path: Path):
    """Verify that corrupt or invalid JSON files in results_dir are captured as errors without aborting."""
    seed_file = tmp_path / "seed.json"
    seed_file.write_text(json.dumps({
        "version": "1.0",
        "total_apps": 1,
        "apps": [{"id": 1, "name": "AppOne", "category": "CRM and Sales", "website": "https://one.com", "documentation_hint": "https://docs.one.com"}]
    }), encoding="utf-8")

    results_dir = tmp_path / "results"
    results_dir.mkdir()
    (results_dir / "001_corrupt.json").write_text("NOT_VALID_JSON{", encoding="utf-8")

    reconcil = reconcile_research_data(
        seed_path=seed_file,
        dataset_path=tmp_path / "nonexistent.json",
        results_dir=results_dir,
    )

    assert reconcil["individual_result_files_count"] == 1
    assert reconcil["valid_records_in_files"] == 0
    assert reconcil["invalid_records_in_files"] == 1
    assert len(reconcil["invalid_file_errors"]) == 1


def test_verdict_distribution_and_category_totals():
    """Verify aggregation of buildability verdicts and category-specific counters."""
    r1 = _make_dummy_record("AppCRM", AppCategory.CRM, BuildabilityVerdict.BUILDABLE)
    r2 = _make_dummy_record("AppCRM2", AppCategory.CRM, BuildabilityVerdict.CONDITIONALLY_BUILDABLE)
    r3 = _make_dummy_record("AppComm", AppCategory.COMMUNICATION, BuildabilityVerdict.BLOCKED)

    records = [r1, r2, r3]
    overall = compute_overall_analytics(records, total_target=10)

    summary = overall["buildability_summary"]
    assert summary["buildable_count"] == 1
    assert summary["conditionally_buildable_count"] == 1
    assert summary["blocked_count"] == 1
    assert summary["unknown_count"] == 0
    assert summary["percentages"]["buildable"] == 33.3

    # Check category breakdown
    cat_analysis = compute_category_analytics(records)
    assert cat_analysis["crm"]["researched_count"] == 2
    assert cat_analysis["crm"]["verdicts"]["buildable"] == 1
    assert cat_analysis["crm"]["verdicts"]["conditionally_buildable"] == 1
    assert cat_analysis["communication"]["verdicts"]["blocked"] == 1


def test_provenance_classification_and_verification_proportions():
    """Verify live vs partial_live vs mocked provenance accounting."""
    r_live = _make_dummy_record("AppLive", AppCategory.CRM, BuildabilityVerdict.BUILDABLE, mode=ExecutionMode.LIVE, live_verified=True)
    r_partial = _make_dummy_record("AppPartial", AppCategory.MARKETING, BuildabilityVerdict.BLOCKED, mode=ExecutionMode.PARTIAL_LIVE, live_verified=False)

    records = [r_live, r_partial]
    overall = compute_overall_analytics(records, total_target=10)
    prov = overall["provenance_and_verification"]

    assert prov["live_verified_count"] == 1
    assert prov["live_verified_percentage"] == 50.0
    assert prov["partial_live_count"] == 1
    assert prov["partial_live_percentage"] == 50.0
    assert prov["unverified_or_mocked_count"] == 0


def test_toolkit_and_mcp_statistics():
    """Verify Composio discovery and MCP session success metrics."""
    # Toolkit found & MCP created
    r1 = _make_dummy_record("App1", AppCategory.CRM, BuildabilityVerdict.BUILDABLE, toolkit_found=True, mcp_created=True)
    # Toolkit found but MCP failed (e.g. auth config required)
    r2 = _make_dummy_record("App2", AppCategory.CRM, BuildabilityVerdict.BUILDABLE, toolkit_found=True, mcp_created=False)
    # Toolkit not found
    r3 = _make_dummy_record("App3", AppCategory.CRM, BuildabilityVerdict.BLOCKED, toolkit_found=False, mcp_created=False)

    records = [r1, r2, r3]
    overall = compute_overall_analytics(records, total_target=10)
    comp = overall["composio_ecosystem"]

    assert comp["discovery_succeeded"] == 3
    assert comp["toolkits_found_count"] == 2
    assert comp["toolkit_discovery_rate"] == 66.7
    assert comp["mcp_sessions_attempted"] == 2
    assert comp["mcp_sessions_created"] == 1
    assert comp["mcp_session_success_rate_of_discovered"] == 50.0


def test_generate_analytical_insights():
    """Verify that insights structure generates all 9 questions with empirical evidence."""
    r1 = _make_dummy_record("Slack", AppCategory.COMMUNICATION, BuildabilityVerdict.BUILDABLE)
    overall = compute_overall_analytics([r1], total_target=10)
    cat_analysis = compute_category_analytics([r1])
    reconcil = {
        "unique_ids_across_all_outputs": [1],
        "failed_applications": [],
    }

    insights = generate_analytical_insights(overall, cat_analysis, reconcil)

    for i in range(1, 10):
        key = f"q{i}_"
        matching_keys = [k for k in insights.keys() if k.startswith(key)]
        assert len(matching_keys) == 1, f"Missing insight for question #{i}"
        val = insights[matching_keys[0]]
        assert "finding" in val
        assert "evidence" in val
        assert "fact_vs_interpretation" in val


def test_html_case_study_generation(tmp_path: Path):
    """Verify that generate_html_case_study creates valid standalone HTML, CSS, and JS assets."""
    out_dir = tmp_path / "output"
    rep_dir = tmp_path / "reports"
    out_dir.mkdir()
    rep_dir.mkdir()

    r1 = _make_dummy_record("Slack", AppCategory.COMMUNICATION, BuildabilityVerdict.BUILDABLE)
    records = [r1]

    overall = compute_overall_analytics(records, total_target=10)
    cat_analysis = compute_category_analytics(records)
    reconcil = {
        "seed_applications_count": 10,
        "consolidated_dataset_records_count": 1,
        "individual_result_files_count": 1,
        "unique_ids_across_all_outputs": [1],
        "failed_applications_count": 0,
        "unattempted_applications_count": 9,
    }
    insights = generate_analytical_insights(overall, cat_analysis, reconcil)

    html_file, css_file, js_file = generate_html_case_study(
        output_dir=out_dir,
        reports_dir=rep_dir,
        reconciliation=reconcil,
        overall_stats=overall,
        category_stats=cat_analysis,
        insights=insights,
        explorer_records=records,
    )

    assert html_file.exists()
    assert css_file.exists()
    assert js_file.exists()

    content = html_file.read_text(encoding="utf-8")
    assert "<!DOCTYPE html>" in content
    assert "Composio SaaS Research Agent" in content
    assert "Executive Summary" in content
    assert "Evaluation Rubric" in content
    assert "Application Research Explorer" in content
    assert '<script id="analytics-data" type="application/json">' in content


def test_run_full_analytics_no_network_calls(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Verify run_full_analytics executes completely offline without network requests."""
    # Mock httpx and socket to ensure zero outbound calls
    mock_get = Mock(side_effect=RuntimeError("NETWORK_CALL_FORBIDDEN"))
    monkeypatch.setattr("httpx.get", mock_get)
    monkeypatch.setattr("httpx.Client.get", mock_get)

    out_dir = tmp_path / "output"
    rep_dir = tmp_path / "reports"
    out_dir.mkdir()
    rep_dir.mkdir()

    # Create dummy seed and record
    seed_file = tmp_path / "seed.json"
    seed_file.write_text(json.dumps({
        "version": "1.0",
        "total_apps": 1,
        "apps": [{"id": 1, "name": "AppOne", "category": "CRM and Sales", "website": "https://one.com", "documentation_hint": "https://docs.one.com"}]
    }), encoding="utf-8")

    rec1 = _make_dummy_record("AppOne", AppCategory.CRM, BuildabilityVerdict.BUILDABLE)
    (out_dir / "research_dataset.json").write_text(json.dumps({"records": [rec1.model_dump(mode="json")]}), encoding="utf-8")

    results_dir = out_dir / "research_results"
    results_dir.mkdir()
    (results_dir / "001_appone.json").write_text(rec1.model_dump_json(), encoding="utf-8")

    res = run_full_analytics(
        output_dir=out_dir,
        reports_dir=rep_dir,
        seed_path=seed_file,
    )

    assert "reconciliation" in res
    assert "overall_summary" in res
    assert "category_analysis" in res
    assert "insights" in res
    assert "generated_files" in res
    mock_get.assert_not_called()


def test_cli_analytics_command(tmp_path: Path):
    """Verify executing CLI analytics subcommand returns 0 and produces expected outputs."""
    from research_agent.cli import main

    out_dir = tmp_path / "output"
    rep_dir = tmp_path / "reports"
    out_dir.mkdir()
    rep_dir.mkdir()

    seed_file = tmp_path / "seed.json"
    seed_file.write_text(json.dumps({
        "version": "1.0",
        "total_apps": 1,
        "apps": [{"id": 1, "name": "AppOne", "category": "CRM and Sales", "website": "https://one.com", "documentation_hint": "https://docs.one.com"}]
    }), encoding="utf-8")

    rec1 = _make_dummy_record("AppOne", AppCategory.CRM, BuildabilityVerdict.BUILDABLE)
    (out_dir / "research_dataset.json").write_text(json.dumps({"records": [rec1.model_dump(mode="json")]}), encoding="utf-8")

    exit_code = main([
        "analytics",
        "--output-dir", str(out_dir),
        "--reports-dir", str(rep_dir),
        "--seed-path", str(seed_file),
    ])

    assert exit_code == 0
    assert (out_dir / "analytics" / "data_reconciliation.json").exists()
    assert (rep_dir / "case_study.html").exists()


def test_category_and_overall_aggregation_consistency():
    """Regression test: Verify category sums match overall statistics without double-counting."""
    r1 = _make_dummy_record("AppCRM", AppCategory.CRM, BuildabilityVerdict.BUILDABLE, live_verified=True)
    r2 = _make_dummy_record("AppCRM2", AppCategory.CRM, BuildabilityVerdict.CONDITIONALLY_BUILDABLE, live_verified=True)
    r3 = _make_dummy_record("AppComm", AppCategory.COMMUNICATION, BuildabilityVerdict.BLOCKED, live_verified=False, mode=ExecutionMode.PARTIAL_LIVE)

    records = [r1, r2, r3]
    overall = compute_overall_analytics(records, total_target=10)
    cat_analysis = compute_category_analytics(records)

    # Reconcile counts across categories vs overall
    sum_researched = sum(c["researched_count"] for c in cat_analysis.values())
    sum_live = sum(c["live_verified_count"] for c in cat_analysis.values())
    sum_buildable = sum(c["verdicts"]["buildable"] for c in cat_analysis.values())
    sum_cond = sum(c["verdicts"]["conditionally_buildable"] for c in cat_analysis.values())
    sum_blocked = sum(c["verdicts"]["blocked"] for c in cat_analysis.values())
    sum_unknown = sum(c["verdicts"]["unknown"] for c in cat_analysis.values())

    assert sum_researched == overall["total_researched_applications"] == 3
    assert sum_live == overall["provenance_and_verification"]["live_verified_count"] == 2
    assert sum_buildable == overall["buildability_summary"]["buildable_count"] == 1
    assert sum_cond == overall["buildability_summary"]["conditionally_buildable_count"] == 1
    assert sum_blocked == overall["buildability_summary"]["blocked_count"] == 1
    assert sum_unknown == overall["buildability_summary"]["unknown_count"] == 0


def test_production_output_data_exact_consistency():
    """Verify live verification counts across actual production outputs reconcile to 59."""
    from research_agent.config import DATA_DIR, OUTPUT_DIR

    results_dir = OUTPUT_DIR / "research_results"
    seed_path = DATA_DIR / "raw" / "seed_apps.json"

    if not results_dir.exists() or not seed_path.exists():
        pytest.skip("Production output files not found; skipping production data check.")

    records = [
        AppResearchRecord.model_validate_json(p.read_text(encoding="utf-8"))
        for p in sorted(results_dir.glob("*.json"))
    ]

    seed_apps = load_seed_dataset(seed_path)
    overall = compute_overall_analytics(records, total_target=len(seed_apps))
    cat_analysis = compute_category_analytics(records, seed_apps=seed_apps)

    total_records = len(records)
    assert total_records == 63

    # Overall live verification: exactly 59
    assert overall["provenance_and_verification"]["live_verified_count"] == 59
    assert overall["provenance_and_verification"]["partial_live_count"] == 4
    assert overall["provenance_and_verification"]["unverified_or_mocked_count"] == 0

    # Category analysis sum must equal exactly 59 (eliminating 59 vs 58 discrepancy)
    sum_cat_live = sum(c["live_verified_count"] for c in cat_analysis.values())
    assert sum_cat_live == 59

    # Category researched sum must equal exactly 63
    sum_cat_researched = sum(c["researched_count"] for c in cat_analysis.values())
    assert sum_cat_researched == 63

    # Category verdict sums must equal overall verdict counts
    assert sum(c["verdicts"]["buildable"] for c in cat_analysis.values()) == 33
    assert sum(c["verdicts"]["conditionally_buildable"] for c in cat_analysis.values()) == 14
    assert sum(c["verdicts"]["blocked"] for c in cat_analysis.values()) == 12
    assert sum(c["verdicts"]["unknown"] for c in cat_analysis.values()) == 4
