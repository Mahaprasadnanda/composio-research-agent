"""Unit and integration tests for BatchResearchRunner, error handling, checkpoints, and CLI."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional
from unittest.mock import MagicMock

import pytest

from research_agent.adapters.composio_client import ComposioAdapter, ComposioToolkitDiscovery
from research_agent.adapters.documentation_search import DocumentationResult, DocumentationSearchAdapter
from research_agent.adapters.groq_client import GroqAdapter, LLMExecutionReceipt
from research_agent.cli import build_parser, main
from research_agent.config import ConfigurationError
from research_agent.models import (
    ApiBreadth,
    ApiType,
    AppCategory,
    AppResearchRecord,
    AuthMethod,
    BatchRunSummary,
    BuildabilityVerdict,
    ConfidenceLevel,
    ExecutionMode,
    ExecutionSource,
    McpAvailability,
    ResearchDataset,
    ResearchProvenance,
    SeedAppRecord,
    SelfServiceAccess,
)
from research_agent.services.batch_runner import (
    BatchResearchRunner,
    is_transient_error,
)
from research_agent.services.research_service import ResearchService, get_seed_app, load_seed_dataset
from research_agent.use_cases.run_batch_research import parse_id_list, parse_name_list


# ============================================================================
# Reusable Test Adapters
# ============================================================================


class StubSimulatedDocAdapter(DocumentationSearchAdapter):
    """Simulated doc adapter returning reproducible results without network access."""

    def __init__(self, succeeds: bool = True) -> None:
        super().__init__()
        self.succeeds = succeeds

    def gather_documentation(self, candidate_urls: list[str], max_pages: int = 2) -> list[DocumentationResult]:
        if not self.succeeds or not candidate_urls:
            return []
        return [
            DocumentationResult(
                url=candidate_urls[0],
                title="API Documentation",
                content="REST API documentation excerpt for testing.",
                excerpt="OAuth2 Bearer token authentication.",
                status_code=200,
                is_accessible=True,
                execution_source=ExecutionSource.SIMULATED,
                is_live_network=False,
            )
        ]


class StubSimulatedComposioAdapter(ComposioAdapter):
    """Simulated Composio adapter returning reproducible discoveries without network access."""

    is_configured: bool = True

    def __init__(self, toolkit_found: bool = True) -> None:
        super().__init__(api_key="simulated_key")
        self.toolkit_found = toolkit_found

    def discover_toolkit(self, app_name: str) -> ComposioToolkitDiscovery:
        return ComposioToolkitDiscovery(
            app_name=app_name,
            slug="test_slug",
            is_integrated=self.toolkit_found,
            toolkit_name=f"{app_name} Toolkit",
            discovery_attempted=True,
            discovery_succeeded=True,
            toolkit_found=self.toolkit_found,
            execution_source=ExecutionSource.SIMULATED,
            is_live_network=False,
        )


class StubSimulatedGroqAdapter(GroqAdapter):
    """Simulated Groq adapter returning valid AppResearchRecord without network access."""

    is_configured: bool = True
    model: str = "openai/gpt-oss-120b"

    def __init__(self, succeeds: bool = True, fail_apps: Optional[set[str]] = None) -> None:
        super().__init__(api_key="simulated_key")
        self.succeeds = succeeds
        self.fail_apps = fail_apps or set()
        self.call_count = 0

    def extract_app_research(
        self,
        app_name: str,
        category_hint: str,
        documentation_snippets: list[dict[str, str]],
        composio_info: Optional[dict[str, Any]] = None,
    ) -> AppResearchRecord:
        self.call_count += 1
        if not self.succeeds or app_name in self.fail_apps:
            self.last_execution_receipt = LLMExecutionReceipt(
                execution_source=ExecutionSource.SIMULATED,
                is_live_network=False,
                model=self.model,
                error="Simulated extraction failure",
            )
            raise RuntimeError(f"Simulated extraction failure for {app_name}")

        self.last_execution_receipt = LLMExecutionReceipt(
            execution_source=ExecutionSource.SIMULATED,
            is_live_network=False,
            model=self.model,
            response_id="sim_receipt_123",
        )
        return AppResearchRecord(
            app_name=app_name,
            category=AppCategory.COMMUNICATION,
            description=f"{app_name} cloud platform",
            auth_methods=[AuthMethod.OAUTH2],
            self_service_access=SelfServiceAccess.FREE_SELF_SERVICE,
            developer_access_tier=SelfServiceAccess.FREE_SELF_SERVICE,
            production_access_tier=SelfServiceAccess.FREE_SELF_SERVICE,
            api_breadth=ApiBreadth.COMPREHENSIVE,
            mcp_availability=McpAvailability.COMMUNITY,
            has_composio_integration=bool(composio_info and composio_info.get("toolkit_found")),
            composio_toolkit_slug="test_slug",
            buildability_verdict=BuildabilityVerdict.BUILDABLE,
            confidence_level=ConfidenceLevel.HIGH,
            llm_execution_source=ExecutionSource.SIMULATED,
        )


# ============================================================================
# Unit Tests
# ============================================================================


def test_batch_runner_loads_all_100_seed_apps(tmp_path):
    """1. Verify runner loads all 100 applications from seed dataset and preserves 1-100 ordering."""
    service = ResearchService(
        doc_adapter=StubSimulatedDocAdapter(),
        composio_adapter=StubSimulatedComposioAdapter(),
        groq_adapter=StubSimulatedGroqAdapter(),
        cache_dir=tmp_path / "cache",
    )
    runner = BatchResearchRunner(research_service=service, output_dir=tmp_path)
    assert len(runner.all_seed_apps) == 100
    target_apps = runner.resolve_target_apps()
    assert len(target_apps) == 100
    assert [a.id for a in target_apps] == list(range(1, 101))


def test_batch_runner_resolve_target_apps_filtering(tmp_path):
    """Verify target app filtering by explicit IDs and names."""
    service = ResearchService(
        doc_adapter=StubSimulatedDocAdapter(),
        composio_adapter=StubSimulatedComposioAdapter(),
        groq_adapter=StubSimulatedGroqAdapter(),
        cache_dir=tmp_path / "cache",
    )
    runner = BatchResearchRunner(research_service=service, output_dir=tmp_path)

    # Filter by IDs
    selected_by_id = runner.resolve_target_apps(app_ids=[61, 1, 21])
    assert [a.id for a in selected_by_id] == [1, 21, 61]
    assert [a.name for a in selected_by_id] == ["Salesforce", "Slack", "GitHub"]

    # Filter by Names
    selected_by_name = runner.resolve_target_apps(app_names=["github", "salesforce"])
    assert [a.id for a in selected_by_name] == [1, 61]

    # No match raises ValueError
    with pytest.raises(ValueError, match="No matching applications found"):
        runner.run_batch(target_app_ids=[999])


def test_batch_processing_simulated_subset(tmp_path):
    """2. Verify batch processing with a small simulated subset."""
    service = ResearchService(
        doc_adapter=StubSimulatedDocAdapter(),
        composio_adapter=StubSimulatedComposioAdapter(),
        groq_adapter=StubSimulatedGroqAdapter(),
        cache_dir=tmp_path / "cache",
    )
    runner = BatchResearchRunner(
        research_service=service,
        batch_size=2,
        output_dir=tmp_path,
    )

    dataset, summary = runner.run_batch(target_app_ids=[1, 21, 61])

    assert summary.total_applications == 3
    assert summary.newly_researched_count == 3
    assert summary.cached_count == 0
    assert summary.failed_count == 0
    assert len(dataset.records) == 3
    assert [r.app_name for r in dataset.records] == ["Salesforce", "Slack", "GitHub"]


def test_batch_resume_and_cache_behavior(tmp_path):
    """3. Verify resume loads pre-existing records from cache without re-executing."""
    cache_dir = tmp_path / "cache"
    service = ResearchService(
        doc_adapter=StubSimulatedDocAdapter(),
        composio_adapter=StubSimulatedComposioAdapter(),
        groq_adapter=StubSimulatedGroqAdapter(),
        cache_dir=cache_dir,
    )

    # Pre-populate App 1 (Salesforce) in cache
    seed_1 = get_seed_app(1)
    pre_record = service.research_app(seed_1)
    assert cache_dir.exists()

    # Create a fresh runner with a groq adapter that fails if App 1 is called
    groq_adapter = StubSimulatedGroqAdapter(fail_apps={"Salesforce"})
    service_resumed = ResearchService(
        doc_adapter=StubSimulatedDocAdapter(),
        composio_adapter=StubSimulatedComposioAdapter(),
        groq_adapter=groq_adapter,
        cache_dir=cache_dir,
    )
    runner = BatchResearchRunner(
        research_service=service_resumed,
        output_dir=tmp_path,
    )

    # Run batch on App 1 and App 21 with resume=True
    dataset, summary = runner.run_batch(target_app_ids=[1, 21], resume=True)

    # App 1 was loaded from cache (and thus did not trigger groq fail_apps)
    assert summary.cached_count == 1
    assert summary.newly_researched_count == 1
    assert summary.failed_count == 0
    assert len(dataset.records) == 2


def test_batch_force_refresh_bypasses_cache(tmp_path):
    """4. Verify force_refresh=True re-executes research even if valid cache exists."""
    cache_dir = tmp_path / "cache"
    groq_adapter = StubSimulatedGroqAdapter()
    service = ResearchService(
        doc_adapter=StubSimulatedDocAdapter(),
        composio_adapter=StubSimulatedComposioAdapter(),
        groq_adapter=groq_adapter,
        cache_dir=cache_dir,
    )

    # Pre-populate App 1 in cache
    seed_1 = get_seed_app(1)
    service.research_app(seed_1)
    assert groq_adapter.call_count == 1

    runner = BatchResearchRunner(research_service=service, output_dir=tmp_path)

    # Run batch with force_refresh=True
    dataset, summary = runner.run_batch(target_app_ids=[1], force_refresh=True)

    assert summary.cached_count == 0
    assert summary.newly_researched_count == 1
    assert groq_adapter.call_count == 2


def test_batch_continues_when_one_app_fails(tmp_path):
    """5. Verify that when one app fails, the batch logs the failure and continues."""
    cache_dir = tmp_path / "cache"
    # App 21 (Slack) will fail extraction
    groq_adapter = StubSimulatedGroqAdapter(fail_apps={"Slack"})
    service = ResearchService(
        doc_adapter=StubSimulatedDocAdapter(),
        composio_adapter=StubSimulatedComposioAdapter(),
        groq_adapter=groq_adapter,
        cache_dir=cache_dir,
    )
    runner = BatchResearchRunner(
        research_service=service,
        output_dir=tmp_path,
        max_retries_per_app=1,
    )

    dataset, summary = runner.run_batch(
        target_app_ids=[1, 21, 61],
        allow_fallback=False,  # Force hard failure on error
    )

    assert summary.total_applications == 3
    assert summary.newly_researched_count == 2  # App 1 and App 61 succeeded
    assert summary.failed_count == 1  # App 21 failed
    assert len(summary.failed_apps) == 1
    assert summary.failed_apps[0].app_id == 21
    assert summary.failed_apps[0].app_name == "Slack"
    assert "Simulated extraction failure" in summary.failed_apps[0].error
    assert len(dataset.records) == 2


def test_retry_limits_transient_vs_permanent_errors(tmp_path):
    """6. Verify retry limits and distinguishing transient vs permanent errors."""
    # Test transient error detection helper
    assert is_transient_error(TimeoutError("Connection timed out")) is True
    assert is_transient_error(RuntimeError("HTTP 429 rate limit exceeded")) is True
    assert is_transient_error(RuntimeError("503 Service Unavailable")) is True

    assert is_transient_error(ConfigurationError("Missing GROQ_API_KEY")) is False
    assert is_transient_error(RuntimeError("401 Unauthorized: invalid api key")) is False
    assert is_transient_error(ValueError("Schema validation error")) is False

    # Test transient error retry behavior on runner
    attempts = 0

    class TransientFailService(ResearchService):
        def research_app(self, *args, **kwargs):
            nonlocal attempts
            attempts += 1
            if attempts < 3:
                raise TimeoutError("Simulated socket timeout")
            return AppResearchRecord(
                app_name="Salesforce",
                category=AppCategory.CRM,
                description="CRM platform",
                buildability_verdict=BuildabilityVerdict.BUILDABLE,
            )

    doc_adapter = StubSimulatedDocAdapter()
    comp_adapter = StubSimulatedComposioAdapter()
    groq_adapter = StubSimulatedGroqAdapter()

    failing_service = TransientFailService(
        doc_adapter=doc_adapter,
        composio_adapter=comp_adapter,
        groq_adapter=groq_adapter,
        cache_dir=tmp_path / "cache",
    )

    runner = BatchResearchRunner(
        research_service=failing_service,
        max_retries_per_app=3,
        initial_backoff_seconds=0.01,
        output_dir=tmp_path,
    )

    dataset, summary = runner.run_batch(target_app_ids=[1])
    assert attempts == 3  # Succeeded on 3rd attempt
    assert summary.newly_researched_count == 1
    assert summary.failed_count == 0


def test_batch_checkpoint_persistence(tmp_path):
    """7. Verify checkpoint persistence after batch chunks."""
    output_dir = tmp_path / "batch_out"
    cache_dir = output_dir / "research_results"
    service = ResearchService(
        doc_adapter=StubSimulatedDocAdapter(),
        composio_adapter=StubSimulatedComposioAdapter(),
        groq_adapter=StubSimulatedGroqAdapter(),
        cache_dir=cache_dir,
    )
    runner = BatchResearchRunner(
        research_service=service,
        batch_size=2,
        output_dir=output_dir,
    )

    runner.run_batch(target_app_ids=[1, 21, 61])

    # Check individual cached JSON records
    assert (cache_dir / "001_salesforce.json").exists()
    assert (cache_dir / "021_slack.json").exists()
    assert (cache_dir / "061_github.json").exists()

    # Check consolidated files
    assert (output_dir / "research_dataset.json").exists()
    assert (output_dir / "batch_run_summary.json").exists()


def test_consolidated_dataset_validity_against_pydantic(tmp_path):
    """8. Verify consolidated dataset conforms strictly to ResearchDataset Pydantic model."""
    output_dir = tmp_path / "batch_out"
    service = ResearchService(
        doc_adapter=StubSimulatedDocAdapter(),
        composio_adapter=StubSimulatedComposioAdapter(),
        groq_adapter=StubSimulatedGroqAdapter(),
        cache_dir=output_dir / "research_results",
    )
    runner = BatchResearchRunner(research_service=service, output_dir=output_dir)
    runner.run_batch(target_app_ids=[1, 21])

    dataset_file = output_dir / "research_dataset.json"
    content = dataset_file.read_text(encoding="utf-8")
    dataset = ResearchDataset.model_validate_json(content)

    assert dataset.target_count == 2
    assert len(dataset.records) == 2
    assert dataset.version == "0.1.0"


def test_batch_summary_counts_and_aggregations(tmp_path):
    """9. Verify summary counts and aggregations across execution modes, verdicts, categories."""
    output_dir = tmp_path / "batch_out"
    service = ResearchService(
        doc_adapter=StubSimulatedDocAdapter(),
        composio_adapter=StubSimulatedComposioAdapter(),
        groq_adapter=StubSimulatedGroqAdapter(),
        cache_dir=output_dir / "research_results",
    )
    runner = BatchResearchRunner(research_service=service, output_dir=output_dir)
    _, summary = runner.run_batch(target_app_ids=[1, 21])

    summary_file = output_dir / "batch_run_summary.json"
    validated_summary = BatchRunSummary.model_validate_json(summary_file.read_text(encoding="utf-8"))

    assert validated_summary.total_applications == 2
    assert validated_summary.newly_researched_count == 2
    assert validated_summary.cached_count == 0
    assert validated_summary.failed_count == 0
    assert validated_summary.counts_by_execution_mode.get("mocked", 0) == 2
    assert validated_summary.counts_by_buildability_verdict.get("buildable", 0) == 2
    assert validated_summary.duration_seconds >= 0.0


def test_simulated_and_fixture_records_never_live_verified_in_batch(tmp_path):
    """10. Verify that batch runs with simulated test adapters NEVER produce live_verified=True."""
    output_dir = tmp_path / "batch_out"
    service = ResearchService(
        doc_adapter=StubSimulatedDocAdapter(),
        composio_adapter=StubSimulatedComposioAdapter(),
        groq_adapter=StubSimulatedGroqAdapter(),
        cache_dir=output_dir / "research_results",
    )
    runner = BatchResearchRunner(research_service=service, output_dir=output_dir)
    dataset, summary = runner.run_batch(target_app_ids=[1, 21])

    for record in dataset.records:
        assert record.provenance is not None
        assert record.provenance.live_verified is False
        assert record.provenance.execution_mode == ExecutionMode.MOCKED


def test_cached_records_retain_original_provenance_and_timestamps(tmp_path):
    """11. Verify cached records retain their exact original created_at and provenance."""
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir(parents=True, exist_ok=True)

    past_time = datetime(2025, 6, 15, 12, 0, 0, tzinfo=timezone.utc)
    original_provenance = ResearchProvenance(
        execution_mode=ExecutionMode.OFFLINE_FALLBACK,
        documentation_live_fetched=False,
        llm_inference_executed=False,
        composio_discovery_succeeded=False,
        live_verified=False,
        notes="Historical record",
    )
    historical_record = AppResearchRecord(
        app_name="Salesforce",
        category=AppCategory.CRM,
        description="Historical Salesforce Record",
        buildability_verdict=BuildabilityVerdict.BUILDABLE,
        provenance=original_provenance,
        created_at=past_time,
        updated_at=past_time,
    )

    # Save historical record
    (cache_dir / "001_salesforce.json").write_text(historical_record.model_dump_json(indent=2), encoding="utf-8")

    service = ResearchService(
        doc_adapter=StubSimulatedDocAdapter(),
        composio_adapter=StubSimulatedComposioAdapter(),
        groq_adapter=StubSimulatedGroqAdapter(),
        cache_dir=cache_dir,
    )
    runner = BatchResearchRunner(research_service=service, output_dir=tmp_path)

    dataset, summary = runner.run_batch(target_app_ids=[1], resume=True)

    loaded = dataset.records[0]
    assert loaded.created_at == past_time
    assert loaded.updated_at == past_time
    assert loaded.provenance.notes == "Historical record"
    assert loaded.provenance.execution_mode == ExecutionMode.OFFLINE_FALLBACK


def test_cli_argument_parsing_batch_command():
    """12. Verify CLI argument parsing for batch subcommands and helper parsers."""
    # Test id parser
    assert parse_id_list("1,21, 61") == [1, 21, 61]
    assert parse_id_list(None) is None
    with pytest.raises(Exception):
        parse_id_list("0")
    with pytest.raises(Exception):
        parse_id_list("101")
    with pytest.raises(Exception):
        parse_id_list("not_a_number")

    # Test name parser
    assert parse_name_list("Slack, GitHub, ") == ["Slack", "GitHub"]
    assert parse_name_list(None) is None

    # Test argparse structure
    parser = build_parser()
    args = parser.parse_args(["batch", "--batch-size", "15", "--ids", "1,21", "--no-resume", "--force-refresh"])
    assert args.command == "batch"
    assert args.batch_size == 15
    assert args.ids == "1,21"
    assert args.resume is False
    assert args.force_refresh is True
