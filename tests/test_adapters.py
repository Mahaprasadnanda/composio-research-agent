"""Unit tests with mocks for external service adapters (Groq, Composio, Documentation)."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import httpx
import pytest

from research_agent.adapters.composio_client import (
    ComposioAdapter,
    ComposioToolkitDiscovery,
    normalize_app_slug,
)
from research_agent.adapters.documentation_search import (
    DocumentationResult,
    DocumentationSearchAdapter,
    clean_html_to_text,
    extract_relevant_snippet,
)
from research_agent.adapters.groq_client import (
    DEFAULT_GROQ_MODEL,
    GroqAdapter,
)
from research_agent.models import (
    ApiBreadth,
    ApiType,
    AppCategory,
    AppResearchRecord,
    AuthMethod,
    BuildabilityVerdict,
    ConfidenceLevel,
    McpAvailability,
    PrimaryBlocker,
    SelfServiceAccess,
)


# ============================================================================
# DocumentationSearchAdapter Tests
# ============================================================================


def test_clean_html_to_text():
    """Verify HTML stripping, title extraction, and length bounds."""
    raw_html = """
    <!DOCTYPE html>
    <html>
    <head><title>Test API Documentation &amp; Reference</title></head>
    <body>
        <nav><a href="/home">Home</a></nav>
        <h1>Authentication Overview</h1>
        <p>You can authenticate using <b>OAuth2</b> or an <b>API key</b>.</p>
        <script>console.log("secret");</script>
        <footer>Copyright 2026</footer>
    </body>
    </html>
    """
    title, text = clean_html_to_text(raw_html, max_chars=500)
    assert title == "Test API Documentation & Reference"
    assert "Home" not in text  # nav removed
    assert "secret" not in text  # script removed
    assert "Copyright" not in text  # footer removed
    assert "Authentication Overview" in text
    assert "OAuth2" in text


def test_extract_relevant_snippet():
    """Verify high-relevance excerpt selection using keywords."""
    body = (
        "Welcome to the platform overview. This is generic introductory text.\n\n"
        "To access the REST API, authenticate using an OAuth2 bearer token in the Authorization header. Rate limits are 1000/min.\n\n"
        "Billing details are managed in the user settings console."
    )
    snippet = extract_relevant_snippet(body)
    assert "OAuth2 bearer token" in snippet
    assert "REST API" in snippet


@patch("httpx.Client")
def test_fetch_url_success(mock_client_class):
    """Verify successful documentation retrieval."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.url = "https://example.com/api/docs"
    mock_resp.headers = {"content-type": "text/html"}
    mock_resp.text = "<html><head><title>Doc Title</title></head><body><p>OAuth2 API details</p></body></html>"

    mock_client = MagicMock()
    mock_client.get.return_value = mock_resp
    mock_client_class.return_value.__enter__.return_value = mock_client

    adapter = DocumentationSearchAdapter(timeout=5.0)
    result = adapter.fetch_url("https://example.com/api/docs")

    assert result.is_accessible is True
    assert result.status_code == 200
    assert result.title == "Doc Title"
    assert "OAuth2 API details" in result.content
    assert result.error_message is None


@patch("httpx.Client")
def test_fetch_url_http_error(mock_client_class):
    """Verify HTTP 404 response handling."""
    mock_resp = MagicMock()
    mock_resp.status_code = 404
    mock_resp.url = "https://example.com/notfound"

    mock_client = MagicMock()
    mock_client.get.return_value = mock_resp
    mock_client_class.return_value.__enter__.return_value = mock_client

    adapter = DocumentationSearchAdapter()
    result = adapter.fetch_url("https://example.com/notfound")

    assert result.is_accessible is False
    assert result.status_code == 404
    assert "HTTP 404" in result.error_message


@patch("httpx.Client")
def test_fetch_url_timeout(mock_client_class):
    """Verify network timeout handling."""
    mock_client = MagicMock()
    mock_client.get.side_effect = httpx.TimeoutException("Connection timed out")
    mock_client_class.return_value.__enter__.return_value = mock_client

    adapter = DocumentationSearchAdapter()
    result = adapter.fetch_url("https://example.com/slow")

    assert result.is_accessible is False
    assert "timed out" in result.error_message


# ============================================================================
# ComposioAdapter Tests
# ============================================================================


def test_normalize_app_slug():
    """Verify slug generation for canonical apps and messy strings."""
    assert normalize_app_slug("Salesforce") == "salesforce"
    assert normalize_app_slug("Slack") == "slack"
    assert normalize_app_slug("GitHub") == "github"
    assert normalize_app_slug("Zoho CRM") == "zoho_crm"
    assert normalize_app_slug("Some App (Cloud)") == "some_app"


def test_composio_adapter_unconfigured():
    """Verify behavior when no API key is provided."""
    adapter = ComposioAdapter(api_key=None)
    assert adapter.is_configured is False

    discovery = adapter.discover_toolkit("Slack")
    assert discovery.is_integrated is False
    assert discovery.slug == "slack"
    assert discovery.discovery_attempted is False
    assert discovery.discovery_succeeded is False
    assert discovery.toolkit_found is False
    assert "not configured" in discovery.error


def test_composio_adapter_discover_toolkit_mocked():
    """Verify Composio discovery when toolkit and tools are found and MCP session is created."""
    adapter = ComposioAdapter(api_key="mock_valid_key")
    adapter.is_configured = True

    mock_client = MagicMock()
    # Mock toolkit
    mock_toolkit = MagicMock()
    mock_toolkit.name = "Slack Platform"
    mock_toolkit.description = "Team messaging toolkit"
    mock_toolkit.category = "communication"
    mock_toolkit.auth_schemes = ["oauth2"]
    mock_client.toolkits.get.return_value = mock_toolkit

    # Mock tools
    mock_tool1 = MagicMock()
    mock_tool1.name = "SLACK_POST_MESSAGE"
    mock_tool1.description = "Post message to channel"
    mock_client.tools.get.return_value = [mock_tool1]

    # Mock session
    mock_session = MagicMock()
    mock_session.mcp = MagicMock()
    mock_session.mcp.url = "https://mcp.composio.dev/session/123"
    mock_client.sessions.create.return_value = mock_session

    adapter._client = mock_client

    discovery = adapter.discover_toolkit("Slack")

    assert discovery.is_integrated is True
    assert discovery.slug == "slack"
    assert discovery.toolkit_name == "Slack Platform"
    assert discovery.available_tools_count == 1
    assert discovery.discovery_attempted is True
    assert discovery.discovery_succeeded is True
    assert discovery.toolkit_found is True
    assert discovery.session_creation_attempted is True
    assert discovery.session_created is True
    assert discovery.mcp_supported is True
    assert discovery.mcp_endpoint == "https://mcp.composio.dev/session/123"


def test_composio_adapter_toolkit_not_found():
    """Verify behavior when app is looked up in Composio catalog but not found (404).

    Lookup succeeded over network, but toolkit is absent.
    """
    adapter = ComposioAdapter(api_key="mock_key")
    adapter.is_configured = True

    mock_client = MagicMock()
    mock_client.toolkits.get.side_effect = Exception("404 Toolkit not found")
    adapter._client = mock_client

    discovery = adapter.discover_toolkit("NonExistentSaaSApp")
    assert discovery.is_integrated is False
    assert discovery.discovery_attempted is True
    assert discovery.discovery_succeeded is True
    assert discovery.toolkit_found is False
    assert discovery.session_creation_attempted is False


def test_composio_adapter_mcp_session_failure():
    """Verify handling when toolkit is found but MCP session creation fails."""
    adapter = ComposioAdapter(api_key="mock_key")
    adapter.is_configured = True

    mock_client = MagicMock()
    mock_toolkit = MagicMock()
    mock_toolkit.name = "Custom App"
    mock_client.toolkits.get.return_value = mock_toolkit
    mock_client.tools.get.return_value = []
    mock_client.sessions.create.side_effect = Exception("Connected account required to start MCP")
    adapter._client = mock_client

    discovery = adapter.discover_toolkit("Custom App")
    assert discovery.is_integrated is True
    assert discovery.discovery_succeeded is True
    assert discovery.toolkit_found is True
    assert discovery.session_creation_attempted is True
    assert discovery.session_created is False
    assert discovery.mcp_supported is False
    assert discovery.mcp_endpoint is None
    assert "Connected account required" in str(discovery.session_error)


def test_composio_adapter_network_or_auth_failure():
    """Verify handling when network or authentication to Composio fails (e.g. 401)."""
    adapter = ComposioAdapter(api_key="mock_key")
    adapter.is_configured = True

    mock_client = MagicMock()
    mock_client.toolkits.get.side_effect = Exception("401 Unauthorized API key")
    adapter._client = mock_client

    discovery = adapter.discover_toolkit("Slack")
    assert discovery.is_integrated is False
    assert discovery.discovery_attempted is True
    assert discovery.discovery_succeeded is False
    assert discovery.toolkit_found is False
    assert "Unauthorized" in str(discovery.error)


# ============================================================================
# GroqAdapter Tests
# ============================================================================


def test_groq_adapter_model_configuration():
    """Verify default and customized Groq model selection."""
    from research_agent.config import DEFAULT_GROQ_MODEL

    adapter = GroqAdapter(api_key=None)
    assert adapter.model == "openai/gpt-oss-120b"
    assert adapter.model == DEFAULT_GROQ_MODEL

    custom_adapter = GroqAdapter(api_key=None, model="openai/gpt-oss-20b")
    assert custom_adapter.model == "openai/gpt-oss-20b"


def test_groq_adapter_unconfigured_raises():
    """Verify error when attempting extraction without valid credentials."""
    adapter = GroqAdapter(api_key=None)
    assert adapter.is_configured is False

    with pytest.raises(RuntimeError, match="Groq client is not configured"):
        adapter.extract_app_research(
            app_name="Salesforce",
            category_hint="CRM",
            documentation_snippets=[],
        )


def test_groq_adapter_extraction_success():
    """Verify structured parsing and validation from Groq LLM completion."""
    adapter = GroqAdapter(api_key="mock_groq_key")
    adapter.is_configured = True

    mock_json_response = {
        "app_name": "Salesforce",
        "category": "crm",
        "description": "Enterprise cloud customer relationship management platform.",
        "auth_methods": ["oauth2", "bearer_token"],
        "self_service_access": "free_self_service",
        "developer_access_tier": "free_self_service",
        "production_access_tier": "paid_subscription",
        "access_requirements": "Requires Enterprise Edition org for production.",
        "api_types": ["rest", "graphql"],
        "api_breadth": "comprehensive",
        "mcp_availability": "community",
        "has_composio_integration": True,
        "composio_toolkit_slug": "salesforce",
        "buildability_verdict": "buildable",
        "primary_blocker": "none",
        "blocker_details": None,
        "evidence_urls": ["https://developer.salesforce.com/docs"],
        "evidence_excerpts": ["Salesforce REST APIs support CRM object querying."],
        "confidence_level": "high",
        "uncertainty_notes": None,
    }

    mock_message = MagicMock()
    mock_message.content = json.dumps(mock_json_response)
    mock_choice = MagicMock()
    mock_choice.message = mock_message
    mock_completion = MagicMock()
    mock_completion.choices = [mock_choice]

    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = mock_completion
    adapter._client = mock_client

    record = adapter.extract_app_research(
        app_name="Salesforce",
        category_hint="CRM and Sales",
        documentation_snippets=[{
            "url": "https://developer.salesforce.com/docs",
            "title": "Salesforce Dev",
            "content": "Docs content",
            "excerpt": "Salesforce REST APIs support CRM object querying.",
        }],
    )

    assert isinstance(record, AppResearchRecord)
    assert record.app_name == "Salesforce"
    assert record.category == AppCategory.CRM
    assert AuthMethod.OAUTH2 in record.auth_methods
    assert record.self_service_access == SelfServiceAccess.FREE_SELF_SERVICE
    assert record.developer_access_tier == SelfServiceAccess.FREE_SELF_SERVICE
    assert record.production_access_tier == SelfServiceAccess.PAID_SUBSCRIPTION
    assert record.api_breadth == ApiBreadth.COMPREHENSIVE
    assert record.mcp_availability == McpAvailability.COMMUNITY
    assert record.has_composio_integration is True
    assert record.composio_toolkit_slug == "salesforce"
    assert record.buildability_verdict == BuildabilityVerdict.BUILDABLE
    assert record.confidence_level == ConfidenceLevel.HIGH
    assert len(record.evidence_items) == 1
