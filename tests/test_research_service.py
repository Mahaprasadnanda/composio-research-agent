"""Unit tests for ResearchService orchestration, dataset queries, and caching."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from research_agent.adapters.composio_client import ComposioAdapter, ComposioToolkitDiscovery
from research_agent.adapters.documentation_search import DocumentationResult, DocumentationSearchAdapter
from research_agent.adapters.groq_client import GroqAdapter, LLMExecutionReceipt
from research_agent.config import ConfigurationError
from research_agent.models import (
    ApiBreadth,
    ApiType,
    AppCategory,
    AppResearchRecord,
    AuthMethod,
    BuildabilityVerdict,
    ConfidenceLevel,
    ExecutionMode,
    ExecutionSource,
    McpAvailability,
    OriginalCategory,
    ResearchProvenance,
    SeedAppRecord,
    SelfServiceAccess,
)
from research_agent.services.research_service import (
    ResearchService,
    get_seed_app,
    load_seed_dataset,
    map_original_category,
)


# ============================================================================
# Test Doubles for Simulated / Non-Network Provenance Testing
# ============================================================================


class SimulatedDocAdapter(DocumentationSearchAdapter):
    """Concrete test adapter simulating documentation retrieval without network access."""

    def __init__(self, succeeds: bool = True) -> None:
        super().__init__()
        self.succeeds = succeeds

    def gather_documentation(self, candidate_urls: list[str], max_pages: int = 2) -> list[DocumentationResult]:
        if not self.succeeds or not candidate_urls:
            return []
        return [
            DocumentationResult(
                url=candidate_urls[0],
                title="Official API Documentation",
                content="Comprehensive REST API with OAuth2 authentication and 200 endpoints.",
                excerpt="OAuth2 Bearer authentication supported for all API operations.",
                status_code=200,
                is_accessible=True,
                execution_source=ExecutionSource.SIMULATED,
                is_live_network=False,
            )
        ]


class SimulatedComposioAdapter(ComposioAdapter):
    """Concrete test adapter simulating Composio SDK catalog interactions without network access."""

    is_configured: bool = True

    def __init__(
        self,
        toolkit_found: bool = True,
        mcp_succeeds: bool = True,
        lookup_succeeds: bool = True,
    ) -> None:
        super().__init__(api_key="simulated_key")
        self.toolkit_found = toolkit_found
        self.mcp_succeeds = mcp_succeeds
        self.lookup_succeeds = lookup_succeeds

    def discover_toolkit(self, app_name: str) -> ComposioToolkitDiscovery:
        if not self.lookup_succeeds:
            return ComposioToolkitDiscovery(
                app_name=app_name,
                slug="test_slug",
                is_integrated=False,
                discovery_attempted=True,
                discovery_succeeded=False,
                toolkit_found=False,
                error="Network timeout reaching Composio API endpoint",
                execution_source=ExecutionSource.SIMULATED,
                is_live_network=False,
            )
        if not self.toolkit_found:
            return ComposioToolkitDiscovery(
                app_name=app_name,
                slug="test_slug",
                is_integrated=False,
                discovery_attempted=True,
                discovery_succeeded=True,
                toolkit_found=False,
                execution_source=ExecutionSource.SIMULATED,
                is_live_network=False,
            )
        return ComposioToolkitDiscovery(
            app_name=app_name,
            slug="test_slug",
            is_integrated=True,
            toolkit_name="Test Platform",
            discovery_attempted=True,
            discovery_succeeded=True,
            toolkit_found=True,
            session_creation_attempted=True,
            session_created=self.mcp_succeeds,
            mcp_endpoint="https://mcp.composio.dev/session/123" if self.mcp_succeeds else None,
            mcp_supported=self.mcp_succeeds,
            session_error=None if self.mcp_succeeds else "Connected account required to start MCP",
            execution_source=ExecutionSource.SIMULATED,
            is_live_network=False,
        )


class SimulatedGroqAdapter(GroqAdapter):
    """Concrete test adapter simulating Groq LLM extraction without network access."""

    is_configured: bool = True
    model: str = "openai/gpt-oss-120b"

    def __init__(self, succeeds: bool = True) -> None:
        super().__init__(api_key="simulated_key")
        self.succeeds = succeeds

    def extract_app_research(
        self,
        app_name: str,
        category_hint: str,
        documentation_snippets: list[dict[str, str]],
        composio_info: Optional[dict[str, Any]] = None,
    ) -> AppResearchRecord:
        if not self.succeeds:
            self.last_execution_receipt = LLMExecutionReceipt(
                execution_source=ExecutionSource.SIMULATED,
                is_live_network=False,
                model=self.model,
                error="Groq API 500 Internal Server Error",
            )
            raise RuntimeError("Groq API 500 Internal Server Error")

        self.last_execution_receipt = LLMExecutionReceipt(
            execution_source=ExecutionSource.SIMULATED,
            is_live_network=False,
            model=self.model,
            response_id="simulated_response_id",
        )
        return AppResearchRecord(
            app_name=app_name,
            category=AppCategory.COMMUNICATION,
            description=f"{app_name} communication platform",
            auth_methods=[AuthMethod.OAUTH2],
            self_service_access=SelfServiceAccess.FREE_SELF_SERVICE,
            developer_access_tier=SelfServiceAccess.FREE_SELF_SERVICE,
            production_access_tier=SelfServiceAccess.FREE_SELF_SERVICE,
            api_types=[ApiType.REST],
            api_breadth=ApiBreadth.COMPREHENSIVE,
            mcp_availability=McpAvailability.OFFICIAL,
            has_composio_integration=bool(composio_info and composio_info.get("toolkit_found")),
            composio_toolkit_slug=composio_info.get("slug") if composio_info else None,
            buildability_verdict=BuildabilityVerdict.BUILDABLE,
            confidence_level=ConfidenceLevel.HIGH,
            llm_execution_source=ExecutionSource.SIMULATED,
        )


# ============================================================================
# Unit Tests
# ============================================================================


def test_load_seed_dataset_loads_all_100_apps():
    """Verify loading seed dataset parses exactly 100 SeedAppRecord objects."""
    apps = load_seed_dataset()
    assert len(apps) == 100
    assert all(isinstance(a, SeedAppRecord) for a in apps)


def test_get_seed_app_by_id_and_name():
    """Verify lookup by numeric ID and case-insensitive name."""
    app_1 = get_seed_app(1)
    assert app_1.name == "Salesforce"
    assert app_1.category == OriginalCategory.CRM_AND_SALES

    app_21 = get_seed_app("slack")
    assert app_21.id == 21
    assert app_21.name == "Slack"

    app_61 = get_seed_app("GitHub")
    assert app_61.id == 61
    assert app_61.name == "GitHub"


def test_get_seed_app_not_found():
    """Verify error when querying nonexistent app."""
    with pytest.raises(ValueError, match="No seed application found"):
        get_seed_app(999)

    with pytest.raises(ValueError, match="No seed application found"):
        get_seed_app("NonExistentApp12345")


def test_map_original_category():
    """Verify mapping of all 10 assignment categories."""
    assert map_original_category(OriginalCategory.CRM_AND_SALES) == AppCategory.CRM
    assert map_original_category(OriginalCategory.SUPPORT_AND_HELPDESK) == AppCategory.CUSTOMER_SUPPORT
    assert map_original_category(OriginalCategory.COMMUNICATIONS_AND_MESSAGING) == AppCategory.COMMUNICATION
    assert map_original_category(OriginalCategory.DEVELOPER_INFRA_DATA_PLATFORMS) == AppCategory.DEVELOPER_TOOLS
    assert map_original_category(OriginalCategory.FINANCE_AND_FINTECH) == AppCategory.FINANCE_ACCOUNTING


def test_research_service_orchestration_mocked(tmp_path):
    """Verify end-to-end research execution with mocked adapters."""
    mock_doc = MagicMock(spec=DocumentationSearchAdapter)
    mock_doc.gather_documentation.return_value = [
        DocumentationResult(
            url="https://api.slack.com",
            title="Slack API",
            content="Slack Web API documentation and OAuth.",
            excerpt="OAuth2 bot tokens.",
            status_code=200,
            is_accessible=True,
        )
    ]

    mock_composio = MagicMock(spec=ComposioAdapter)
    mock_composio.is_configured = True
    mock_composio.discover_toolkit.return_value = ComposioToolkitDiscovery(
        app_name="Slack",
        slug="slack",
        is_integrated=True,
        toolkit_name="Slack",
        available_tools_count=5,
        mcp_supported=True,
    )

    mock_record = AppResearchRecord(
        app_name="Slack",
        category=AppCategory.COMMUNICATION,
        description="Team communication platform.",
        auth_methods=[AuthMethod.OAUTH2],
        self_service_access=SelfServiceAccess.FREE_SELF_SERVICE,
        access_requirements="Free workspace setup.",
        api_types=[],
        api_breadth=ApiBreadth.COMPREHENSIVE,
        mcp_availability=McpAvailability.COMPOSIO,
        buildability_verdict=BuildabilityVerdict.BUILDABLE,
        confidence_level=ConfidenceLevel.HIGH,
    )

    mock_groq = MagicMock(spec=GroqAdapter)
    mock_groq.is_configured = True
    mock_groq.extract_app_research.return_value = mock_record

    service = ResearchService(
        doc_adapter=mock_doc,
        composio_adapter=mock_composio,
        groq_adapter=mock_groq,
        cache_dir=tmp_path / "cache",
    )

    seed_app = get_seed_app(21)
    result = service.research_app(seed_app)

    assert result.app_name == "Slack"
    assert result.buildability_verdict == BuildabilityVerdict.BUILDABLE

    # Verify cache file was written
    cache_file = tmp_path / "cache" / "021_slack.json"
    assert cache_file.exists()

    # Second call should read from cache without re-invoking LLM
    mock_groq.extract_app_research.reset_mock()
    cached_result = service.research_app(seed_app)
    assert cached_result.app_name == "Slack"
    mock_groq.extract_app_research.assert_not_called()


def test_research_service_offline_fallback(tmp_path):
    """Verify offline fallback produces valid records when Groq and Composio are unconfigured."""
    doc_adapter = SimulatedDocAdapter(succeeds=False)
    composio_adapter = ComposioAdapter(api_key=None)
    groq_adapter = GroqAdapter(api_key=None)

    service = ResearchService(
        doc_adapter=doc_adapter,
        composio_adapter=composio_adapter,
        groq_adapter=groq_adapter,
        cache_dir=tmp_path / "cache",
    )

    seed_github = get_seed_app(61)
    record = service.research_app(seed_github, allow_fallback=True)

    assert record.app_name == "GitHub"
    assert record.category == AppCategory.DEVELOPER_TOOLS
    assert AuthMethod.BEARER_TOKEN in record.auth_methods
    assert record.self_service_access == SelfServiceAccess.FREE_SELF_SERVICE
    assert record.buildability_verdict == BuildabilityVerdict.BUILDABLE
    assert record.confidence_level == ConfidenceLevel.HIGH
    assert record.has_composio_integration is True
    assert record.composio_toolkit_slug == "github"
    assert record.mcp_availability == McpAvailability.COMMUNITY
    assert record.provenance is not None
    assert record.provenance.execution_mode == ExecutionMode.OFFLINE_FALLBACK
    assert record.provenance.llm_inference_executed is False
    assert record.provenance.live_verified is False


def test_salesforce_access_tier_distinction(tmp_path):
    """Verify Salesforce distinguishes developer free self-service from production paid subscription."""
    service = ResearchService(
        doc_adapter=SimulatedDocAdapter(succeeds=False),
        composio_adapter=ComposioAdapter(api_key=None),
        groq_adapter=GroqAdapter(api_key=None),
        cache_dir=tmp_path / "cache",
    )
    seed_sf = get_seed_app(1)
    record = service.research_app(seed_sf, allow_fallback=True)

    assert record.app_name == "Salesforce"
    assert record.developer_access_tier == SelfServiceAccess.FREE_SELF_SERVICE
    assert record.production_access_tier == SelfServiceAccess.PAID_SUBSCRIPTION
    assert record.has_composio_integration is True
    assert record.composio_toolkit_slug == "salesforce"
    assert record.mcp_availability == McpAvailability.COMMUNITY


def test_slack_official_mcp_distinction(tmp_path):
    """Verify Slack distinguishes official vendor MCP server from Composio toolkit."""
    service = ResearchService(
        doc_adapter=SimulatedDocAdapter(succeeds=False),
        composio_adapter=ComposioAdapter(api_key=None),
        groq_adapter=GroqAdapter(api_key=None),
        cache_dir=tmp_path / "cache",
    )
    seed_slack = get_seed_app(21)
    record = service.research_app(seed_slack, allow_fallback=True)

    assert record.app_name == "Slack"
    assert record.mcp_availability == McpAvailability.OFFICIAL
    assert record.has_composio_integration is True
    assert record.composio_toolkit_slug == "slack"


def test_research_provenance_mocked_adapters_flagged_as_mocked(tmp_path):
    """Verify adapters using MagicMock are strictly flagged as mocked and NEVER live."""
    mock_doc = MagicMock(spec=DocumentationSearchAdapter)
    mock_doc.gather_documentation.return_value = [
        DocumentationResult(
            url="https://api.slack.com",
            title="Slack API",
            content="Content",
            excerpt="Excerpt",
            status_code=200,
            is_accessible=True,
        )
    ]
    mock_composio = MagicMock(spec=ComposioAdapter)
    mock_composio.is_configured = True
    mock_composio.discover_toolkit.return_value = ComposioToolkitDiscovery(
        app_name="Slack",
        slug="slack",
        is_integrated=True,
        toolkit_found=True,
        discovery_attempted=True,
        discovery_succeeded=True,
        mcp_supported=True,
    )
    mock_groq = MagicMock(spec=GroqAdapter)
    mock_groq.is_configured = True
    mock_groq.model = "openai/gpt-oss-120b"
    mock_groq.extract_app_research.return_value = AppResearchRecord(
        app_name="Slack",
        category=AppCategory.COMMUNICATION,
        description="Slack team communication platform",
        buildability_verdict=BuildabilityVerdict.BUILDABLE,
    )

    mock_service = ResearchService(
        doc_adapter=mock_doc,
        composio_adapter=mock_composio,
        groq_adapter=mock_groq,
        cache_dir=tmp_path / "mock_cache",
    )
    mock_record = mock_service.research_app(get_seed_app(21))
    assert mock_record.provenance is not None
    assert mock_record.provenance.execution_mode == ExecutionMode.MOCKED
    assert mock_record.provenance.live_verified is False
    assert "mock adapters" in mock_record.provenance.notes


def test_concrete_simulated_subclasses_cannot_produce_live(tmp_path):
    """Verify concrete simulated subclasses cannot produce LIVE or live_verified=True."""
    service = ResearchService(
        doc_adapter=SimulatedDocAdapter(succeeds=True),
        composio_adapter=SimulatedComposioAdapter(toolkit_found=True, mcp_succeeds=True),
        groq_adapter=SimulatedGroqAdapter(succeeds=True),
        cache_dir=tmp_path / "sim_cache",
    )
    record = service.research_app(get_seed_app(21))

    assert record.provenance is not None
    assert record.provenance.execution_mode == ExecutionMode.MOCKED
    assert record.provenance.live_verified is False
    assert record.provenance.doc_execution_source == ExecutionSource.SIMULATED
    assert record.provenance.llm_execution_source == ExecutionSource.SIMULATED
    assert record.provenance.composio_execution_source == ExecutionSource.SIMULATED
    assert "simulated or mock adapters" in record.provenance.notes


def test_magicmock_adapters_cannot_produce_live(tmp_path):
    """Verify MagicMock adapters cannot produce LIVE or live_verified=True."""
    mock_doc = MagicMock(spec=DocumentationSearchAdapter)
    mock_doc.gather_documentation.return_value = [
        DocumentationResult(
            url="https://api.slack.com",
            status_code=200,
            is_accessible=True,
            content="Mocked documentation content",
            excerpt="Mocked excerpt",
            execution_source=ExecutionSource.MOCKED,
            is_live_network=False,
        )
    ]
    mock_comp = MagicMock(spec=ComposioAdapter)
    mock_comp.is_configured = True
    mock_comp.discover_toolkit.return_value = ComposioToolkitDiscovery(
        app_name="Slack",
        slug="slack",
        is_integrated=True,
        discovery_attempted=True,
        discovery_succeeded=True,
        toolkit_found=True,
        execution_source=ExecutionSource.MOCKED,
        is_live_network=False,
    )
    mock_groq = MagicMock(spec=GroqAdapter)
    mock_groq.is_configured = True
    mock_groq.model = "openai/gpt-oss-120b"
    mock_groq.last_execution_receipt = LLMExecutionReceipt(
        execution_source=ExecutionSource.MOCKED,
        is_live_network=False,
        model="openai/gpt-oss-120b",
    )
    mock_groq.extract_app_research.return_value = AppResearchRecord(
        app_name="Slack",
        category=AppCategory.COMMUNICATION,
        description="Slack communication platform",
        auth_methods=[AuthMethod.OAUTH2],
        self_service_access=SelfServiceAccess.FREE_SELF_SERVICE,
        api_types=[ApiType.REST],
        api_breadth=ApiBreadth.COMPREHENSIVE,
        mcp_availability=McpAvailability.OFFICIAL,
        buildability_verdict=BuildabilityVerdict.BUILDABLE,
        confidence_level=ConfidenceLevel.HIGH,
        llm_execution_source=ExecutionSource.MOCKED,
    )

    service = ResearchService(
        doc_adapter=mock_doc,
        composio_adapter=mock_comp,
        groq_adapter=mock_groq,
        cache_dir=tmp_path / "mock_cache",
    )
    record = service.research_app(get_seed_app(21))

    assert record.provenance is not None
    assert record.provenance.execution_mode == ExecutionMode.MOCKED
    assert record.provenance.live_verified is False
    assert record.provenance.doc_execution_source == ExecutionSource.MOCKED
    assert record.provenance.llm_execution_source == ExecutionSource.MOCKED
    assert record.provenance.composio_execution_source == ExecutionSource.MOCKED


def test_offline_fixtures_cannot_produce_live(tmp_path):
    """Verify offline fallback fixtures cannot produce LIVE."""
    doc_adapter = SimulatedDocAdapter(succeeds=False)
    service = ResearchService(
        doc_adapter=doc_adapter,
        composio_adapter=ComposioAdapter(api_key=None),
        groq_adapter=GroqAdapter(api_key=None),
        cache_dir=tmp_path / "offline_cache",
    )
    record = service.research_app(get_seed_app(21), allow_fallback=True)

    assert record.provenance is not None
    assert record.provenance.execution_mode == ExecutionMode.OFFLINE_FALLBACK
    assert record.provenance.live_verified is False
    assert record.provenance.llm_execution_source == ExecutionSource.FIXTURE


def test_missing_or_ambiguous_provenance_fails_closed(tmp_path):
    """Verify missing or ambiguous provenance fails closed to live_verified=False."""
    class AmbiguousDocAdapter(DocumentationSearchAdapter):
        def gather_documentation(self, candidate_urls: list[str], max_pages: int = 2) -> list[DocumentationResult]:
            return [
                DocumentationResult(
                    url="https://api.slack.com",
                    status_code=200,
                    is_accessible=True,
                    content="Ambiguous content",
                    excerpt="Ambiguous excerpt",
                    execution_source=ExecutionSource.UNKNOWN,
                    is_live_network=False,
                )
            ]

    service = ResearchService(
        doc_adapter=AmbiguousDocAdapter(),
        composio_adapter=SimulatedComposioAdapter(toolkit_found=True),
        groq_adapter=SimulatedGroqAdapter(succeeds=True),
        cache_dir=tmp_path / "ambiguous_cache",
    )
    record = service.research_app(get_seed_app(21))

    assert record.provenance is not None
    assert record.provenance.live_verified is False
    assert record.provenance.execution_mode != ExecutionMode.LIVE


def test_partial_real_execution_produces_partial_live(tmp_path):
    """Verify PARTIAL_LIVE when genuine HTTP documentation succeeds but Groq/Composio are unconfigured."""
    class RealNetworkDocAdapter(DocumentationSearchAdapter):
        def gather_documentation(self, candidate_urls: list[str], max_pages: int = 2) -> list[DocumentationResult]:
            return [
                DocumentationResult(
                    url=candidate_urls[0],
                    title="Real Docs",
                    content="Real fetched content",
                    excerpt="Real excerpt",
                    status_code=200,
                    is_accessible=True,
                    execution_source=ExecutionSource.REAL_NETWORK,
                    is_live_network=True,
                )
            ]

    service = ResearchService(
        doc_adapter=RealNetworkDocAdapter(),
        composio_adapter=ComposioAdapter(api_key=None),
        groq_adapter=GroqAdapter(api_key=None),
        cache_dir=tmp_path / "partial_cache",
    )
    record = service.research_app(get_seed_app(21), allow_fallback=True)

    assert record.provenance is not None
    assert record.provenance.execution_mode == ExecutionMode.PARTIAL_LIVE
    assert record.provenance.live_verified is False
    assert record.provenance.documentation_live_fetched is True
    assert record.provenance.doc_execution_source == ExecutionSource.REAL_NETWORK
    assert record.provenance.llm_execution_source == ExecutionSource.FIXTURE
    assert record.provenance.composio_execution_source == ExecutionSource.FIXTURE


def test_simulated_composio_toolkit_not_found_is_mocked(tmp_path):
    """Verify simulated catalog lookup resulting in toolkit-not-found preserves mocked mode."""
    service = ResearchService(
        doc_adapter=SimulatedDocAdapter(succeeds=True),
        composio_adapter=SimulatedComposioAdapter(toolkit_found=False),
        groq_adapter=SimulatedGroqAdapter(succeeds=True),
        cache_dir=tmp_path / "sim_cache",
    )
    record = service.research_app(get_seed_app(21))

    assert record.provenance is not None
    assert record.provenance.execution_mode == ExecutionMode.MOCKED
    assert record.provenance.live_verified is False
    assert record.provenance.composio_discovery_attempted is True
    assert record.provenance.composio_discovery_succeeded is True
    assert record.provenance.composio_toolkit_found is False
    assert record.has_composio_integration is False


def test_simulated_mcp_session_failure_is_mocked(tmp_path):
    """Verify simulated MCP session failure is tracked distinctly without claiming live."""
    service = ResearchService(
        doc_adapter=SimulatedDocAdapter(succeeds=True),
        composio_adapter=SimulatedComposioAdapter(toolkit_found=True, mcp_succeeds=False),
        groq_adapter=SimulatedGroqAdapter(succeeds=True),
        cache_dir=tmp_path / "sim_cache",
    )
    record = service.research_app(get_seed_app(21))

    assert record.provenance is not None
    assert record.provenance.execution_mode == ExecutionMode.MOCKED
    assert record.provenance.live_verified is False
    assert record.provenance.composio_discovery_succeeded is True
    assert record.provenance.composio_toolkit_found is True
    assert record.provenance.composio_mcp_session_attempted is True
    assert record.provenance.composio_mcp_session_created is False
    assert record.provenance.composio_mcp_endpoint_returned is False
    assert record.provenance.composio_mcp_endpoint is None
    assert "Connected account required" in str(record.provenance.composio_mcp_session_error)


def test_research_service_unconfigured_without_fallback_raises(tmp_path):
    """Verify ConfigurationError is raised when unconfigured and fallback is disallowed."""
    mock_doc = MagicMock(spec=DocumentationSearchAdapter)
    mock_doc.gather_documentation.return_value = []

    mock_composio = MagicMock(spec=ComposioAdapter)
    mock_composio.is_configured = True
    mock_composio.discover_toolkit.return_value = ComposioToolkitDiscovery(
        app_name="Salesforce",
        slug="salesforce",
        is_integrated=False,
    )

    mock_groq = MagicMock(spec=GroqAdapter)
    mock_groq.is_configured = False

    service = ResearchService(
        doc_adapter=mock_doc,
        composio_adapter=mock_composio,
        groq_adapter=mock_groq,
        cache_dir=tmp_path / "cache",
    )

    seed_sf = get_seed_app(1)
    with pytest.raises(ConfigurationError, match="GROQ_API_KEY is not configured"):
        service.research_app(seed_sf, allow_fallback=False)


def test_research_dataset_container_with_test_targets():
    """Verify loading output test targets into a ResearchDataset container."""
    from research_agent.config import OUTPUT_DIR
    from research_agent.models import ResearchDataset

    cache_dir = OUTPUT_DIR / "research_results"
    records = []
    for app_id, slug in [(1, "salesforce"), (21, "slack"), (61, "github")]:
        p = cache_dir / f"{app_id:03d}_{slug}.json"
        if p.exists():
            records.append(AppResearchRecord.model_validate_json(p.read_text(encoding="utf-8")))

    if len(records) == 3:
        dataset = ResearchDataset(records=records, target_count=3)
        summary = dataset.summary_by_verdict()
        assert summary.get("buildability_verdict", {}).get("buildable") == 3 or summary.get("buildable") == 3
        cat_summary = dataset.summary_by_category()
        assert "crm" in cat_summary
        assert "communication" in cat_summary
        assert "developer_tools" in cat_summary

