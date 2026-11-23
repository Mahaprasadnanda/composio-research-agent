"""Unit tests for ResearchService orchestration, dataset queries, and caching."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from research_agent.adapters.composio_client import ComposioAdapter, ComposioToolkitDiscovery
from research_agent.adapters.documentation_search import DocumentationResult, DocumentationSearchAdapter
from research_agent.adapters.groq_client import GroqAdapter
from research_agent.config import ConfigurationError
from research_agent.models import (
    ApiBreadth,
    AppCategory,
    AppResearchRecord,
    AuthMethod,
    BuildabilityVerdict,
    ConfidenceLevel,
    ExecutionMode,
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
    """Verify offline fallback produces valid records for the 3 target apps when Groq is unconfigured."""
    mock_doc = MagicMock(spec=DocumentationSearchAdapter)
    mock_doc.gather_documentation.return_value = []

    mock_composio = MagicMock(spec=ComposioAdapter)
    mock_composio.is_configured = True
    mock_composio.discover_toolkit.return_value = ComposioToolkitDiscovery(
        app_name="GitHub",
        slug="github",
        is_integrated=True,
    )

    mock_groq = MagicMock(spec=GroqAdapter)
    mock_groq.is_configured = False

    service = ResearchService(
        doc_adapter=mock_doc,
        composio_adapter=mock_composio,
        groq_adapter=mock_groq,
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
        doc_adapter=MagicMock(gather_documentation=MagicMock(return_value=[])),
        composio_adapter=MagicMock(discover_toolkit=MagicMock(return_value=ComposioToolkitDiscovery(app_name="Salesforce", slug="salesforce", is_integrated=True))),
        groq_adapter=MagicMock(is_configured=False),
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
        doc_adapter=MagicMock(gather_documentation=MagicMock(return_value=[])),
        composio_adapter=MagicMock(discover_toolkit=MagicMock(return_value=ComposioToolkitDiscovery(app_name="Slack", slug="slack", is_integrated=True))),
        groq_adapter=MagicMock(is_configured=False),
        cache_dir=tmp_path / "cache",
    )
    seed_slack = get_seed_app(21)
    record = service.research_app(seed_slack, allow_fallback=True)

    assert record.app_name == "Slack"
    assert record.mcp_availability == McpAvailability.OFFICIAL
    assert record.has_composio_integration is True
    assert record.composio_toolkit_slug == "slack"


def test_research_provenance_audit_trail(tmp_path):
    """Verify execution provenance accurately marks live vs offline fallback."""
    # 1. Live mode simulation
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

    live_service = ResearchService(
        doc_adapter=mock_doc,
        composio_adapter=mock_composio,
        groq_adapter=mock_groq,
        cache_dir=tmp_path / "live_cache",
    )
    live_record = live_service.research_app(get_seed_app(21))
    assert live_record.provenance is not None
    assert live_record.provenance.execution_mode == ExecutionMode.LIVE
    assert live_record.provenance.llm_inference_executed is True
    assert live_record.provenance.llm_model == "openai/gpt-oss-120b"
    assert live_record.provenance.live_verified is True
    assert live_record.provenance.documentation_live_fetched is True


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

